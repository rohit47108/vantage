import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.science import ROOT
from backend.product_jobs import create_router


class NativeJobsTests(unittest.TestCase):
    def test_frozen_discovery_then_actual_native_job_and_lazy_context_export(self):
        acquisition=json.loads((ROOT/'research/updates/2026-11-15/native-extraction/acquisition.json').read_text())
        old=json.loads((ROOT/'research/updates/2026-11-15/photometry/benchmark.json').read_text())
        rows=acquisition['observations']+[old['observations'][1]]
        found={'observations':rows,'search_completeness':'limited','queries':[r['ibe'] for r in rows],'collections':['spherex_dr1'],'data_status':'retained_test_subset'}
        paths={(r['obs_id'],r['detector']):(ROOT/r['path'],r['retrieval_mode']) for r in rows}
        source={'name':'P330E',**{k:old['source'][k] for k in ['ra','dec','pmra','pmdec','ref_epoch']}}
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'VANTAGE_RUNTIME':directory}),ThreadPoolExecutor(max_workers=1) as pool:
            router,_=create_router(Path(directory)/'jobs.sqlite',pool);app=FastAPI();app.include_router(router);client=TestClient(app)
            def complete(response):
                self.assertEqual(response.status_code,202,response.text)
                deadline=time.monotonic()+60
                while time.monotonic()<deadline:
                    state=client.get(response.json()['status_url']).json()
                    if state['state'] in ['complete','failed']:break
                    time.sleep(.1)
                self.assertEqual(state['state'],'complete',state)
                return client.get('/v1/products/'+state['result_id']).json()
            with patch('backend.source_fields.discover',return_value=found):
                field=complete(client.post('/v1/source-fields',json={'source':source,'start_utc':'2025-07-01','end_utc':'2025-07-31'}))
            self.assertEqual(field['type'],'source_field')
            with patch('backend.native_extraction.native_cutout',side_effect=lambda row,position,fov:paths[(row['obs_id'],row['detector'])]):
                request={'field_id':field['id'],'observation_indices':list(range(7))}
                submitted=client.post('/v1/native-source-samples',json=request)
                self.assertEqual(client.post('/v1/native-source-samples',json=request|{'observation_indices':list(reversed(range(7)))}).json()['job_id'],submitted.json()['job_id'])
                product=complete(submitted)
            self.assertEqual(product['type'],'source_samples')
            self.assertEqual(product['request']['field_id'],field['id'])
            self.assertEqual({s['detector'] for s in product['samples'] if s['status']=='accepted'},set(range(1,7)))
            sample=next(s for s in product['samples'] if s['status']=='accepted')
            context=client.get(sample['image_context_url'])
            self.assertEqual(context.status_code,200)
            import hashlib
            self.assertEqual(hashlib.sha256(context.content).hexdigest(),sample['image_context_sha256'])
            self.assertEqual(client.get('/v1/products/'+product['id']+'/sample-999.json').status_code,422)
            self.assertEqual(client.post('/v1/native-source-samples',json=request|{'observation_indices':[999]}).status_code,422)
            self.assertEqual(client.post('/v1/native-source-samples',json=request|{'field_id':product['id']}).status_code,422)


if __name__=='__main__':unittest.main()
