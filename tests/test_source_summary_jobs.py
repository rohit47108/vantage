import json
import os
import io
import time
import hashlib
import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from astropy.table import Table
import astropy.units as u
from backend.science import ROOT,write_json
from backend.product_jobs import create_router


class SourceSummaryJobTests(unittest.TestCase):
    def test_actual_parent_summary_exports_dates_missing_and_dedup(self):
        parent=json.loads((ROOT/'artifacts/native-workflow-public-product.json').read_text())
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'VANTAGE_RUNTIME':directory}),ThreadPoolExecutor(max_workers=1) as pool:
            write_json(Path(directory)/'products'/parent['id']/'manifest.json',parent)
            router,_=create_router(Path(directory)/'jobs.sqlite',pool);app=FastAPI();app.include_router(router);client=TestClient(app)
            request={'product_id':parent['id'],'start_utc':'2025-07-16','end_utc':'2025-07-16','time_bin_days':1}
            response=client.post('/v1/source-summaries',json=request)
            self.assertEqual(response.status_code,202,response.text)
            self.assertEqual(client.post('/v1/source-summaries',json=request).json()['job_id'],response.json()['job_id'])
            deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                state=client.get(response.json()['status_url']).json()
                if state['state'] in ['complete','failed']:break
                time.sleep(.05)
            self.assertEqual(state['state'],'complete',state)
            result=client.get('/v1/products/'+state['result_id']).json()
            self.assertEqual(result['type'],'source_summary');self.assertEqual(result['selected_sample_count'],2)
            self.assertEqual(result['measured_nominal_channels'],1)
            for name,resource in result['exports'].items():
                data=client.get(resource['url']);self.assertEqual(data.status_code,200)
                self.assertEqual(hashlib.sha256(data.content).hexdigest(),resource['sha256'])
                if name=='bins.ecsv':
                    table=Table.read(io.BytesIO(data.content),format='ascii.ecsv')
                    self.assertEqual(table['flux_ujy'].unit,u.uJy)
                    self.assertEqual(table['weighted_wavelength_um'].unit,u.um)
                    self.assertTrue(table['equal_mean_p_value'].mask[0])
                if name=='coverage.ecsv':self.assertEqual(len(Table.read(io.BytesIO(data.content),format='ascii.ecsv')),102)
            self.assertEqual(client.post('/v1/source-summaries',json=request|{'product_id':result['id']}).status_code,422)
            self.assertEqual(client.post('/v1/source-summaries',json=request|{'product_id':'f'*64}).status_code,404)
            self.assertEqual(client.get('/v1/products/'+result['id']+'/arbitrary.ecsv').status_code,422)


if __name__=='__main__':unittest.main()
