import hashlib
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
from astropy.table import Table
from io import BytesIO
import astropy.units as u
from backend.science import ROOT,write_json
from backend.product_jobs import create_router
from range_fixture import CubeFixtureTransport


class SpectralTraceJobsTests(unittest.TestCase):
    def test_queued_actual_native_trace_exports_and_context_restore(self):
        plane=json.loads((ROOT/'artifacts/hips-real-plane.json').read_text())
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'VANTAGE_RUNTIME':directory}),ThreadPoolExecutor(max_workers=1) as pool:
            write_json(Path(directory)/'spectral'/(plane['id']+'.json'),plane)
            router,_=create_router(Path(directory)/'jobs.sqlite',pool);app=FastAPI();app.include_router(router);client=TestClient(app)
            request={'plane_id':plane['id'],'x':80,'y':80}
            with patch('backend.range_reader.requests.Session',side_effect=CubeFixtureTransport):
                response=client.post('/v1/spectral-traces',json=request);self.assertEqual(response.status_code,202,response.text)
                self.assertEqual(client.post('/v1/spectral-traces',json=request).json()['job_id'],response.json()['job_id'])
                deadline=time.monotonic()+20
                while time.monotonic()<deadline:
                    state=client.get(response.json()['status_url']).json()
                    if state['state'] in ['complete','failed']:break
                    time.sleep(.05)
                self.assertEqual(state['state'],'complete',state)
            result=client.get('/v1/products/'+state['result_id']).json()
            self.assertEqual(result['type'],'visual_spectral_trace');self.assertEqual(result['available_channels'],100)
            for name,resource in result['exports'].items():
                response=client.get(resource['url']);self.assertEqual(response.status_code,200)
                self.assertEqual(hashlib.sha256(response.content).hexdigest(),resource['sha256'])
                if name=='trace.ecsv':
                    table=Table.read(BytesIO(response.content),format='ascii.ecsv')
                    self.assertEqual(len(table),102);self.assertEqual(table['brightness_mjysr'].unit,u.MJy/u.sr)
                    self.assertTrue(table['brightness_mjysr'].mask[50]);self.assertTrue(table['brightness_mjysr'].mask[51])
            fresh,recover=create_router(Path(directory)/'jobs.sqlite',pool);other=FastAPI();other.include_router(fresh)
            self.assertEqual(recover(),0)
            self.assertEqual(TestClient(other).get('/v1/products/'+result['id']).json()['trace_data_id'],result['trace_data_id'])
            self.assertEqual(client.post('/v1/source-summaries',json={'product_id':result['id']}).status_code,422)
            for bad in [{'x':plane['shape'][1]},{'plane_id':'f'*64},{'plane_id':'../bad'},{'y':-1}]:
                self.assertIn(client.post('/v1/spectral-traces',json=request|bad).status_code,[404,422])


if __name__=='__main__':unittest.main()
