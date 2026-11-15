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
from backend.product_jobs import create_router
from backend.science import ROOT


class ProductJobsTests(unittest.TestCase):
    def request(self):
        catalog=json.loads((ROOT/'public/prepared/catalog.json').read_text())
        return {'sequence_id':next(s['id'] for s in catalog if s['key']=='m101'),'frame_indices':[0,1],'fov_arcmin':3}

    def test_real_async_coadd_persistence_and_canonical_dedup(self):
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'VANTAGE_RUNTIME':directory}),ThreadPoolExecutor(max_workers=1) as pool:
            database=Path(directory)/'jobs.sqlite';router,recover=create_router(database,pool)
            app=FastAPI();app.include_router(router);c=TestClient(app)
            request=self.request();r=c.post('/v1/coadds',json=request)
            self.assertEqual(r.status_code,202)
            request['frame_indices']=[1,0]
            self.assertEqual(c.post('/v1/coadds',json=request).json()['job_id'],r.json()['job_id'])
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                job=c.get(r.json()['status_url']).json()
                if job['state'] in ['complete','failed']:break
                time.sleep(.05)
            self.assertEqual(job['state'],'complete',job)
            result=c.get('/v1/products/'+job['result_id'])
            self.assertEqual(result.status_code,200)
            self.assertEqual(c.get('/v1/products/'+job['result_id']+'/science.fits').status_code,200)
            # A fresh router/connection sees existing scientific files and jobs.
            fresh,recover=create_router(database,pool);app2=FastAPI();app2.include_router(fresh)
            self.assertEqual(recover(),0)
            self.assertEqual(TestClient(app2).get('/v1/products/'+job['result_id']).json()['id'],result.json()['id'])

    def test_cancelled_attempt_does_not_replace_retry_and_pending_work_recovers(self):
        class Queue:
            def __init__(self):self.calls=[]
            def submit(self,*args):self.calls.append(args)
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'VANTAGE_RUNTIME':directory}):
            q=Queue();router,recover=create_router(Path(directory)/'jobs.sqlite',q)
            app=FastAPI();app.include_router(router);c=TestClient(app)
            request=self.request();a=c.post('/v1/coadds',json=request).json()
            c.delete(a['status_url'])
            b=c.post('/v1/coadds',json=request).json()
            self.assertNotEqual(a['job_id'],b['job_id'])
            q.calls[0][0](*q.calls[0][1:])
            self.assertEqual(c.get(a['status_url']).json()['state'],'cancelled')
            self.assertEqual(recover(),1)

    def test_input_rejection_before_processing(self):
        class Reject:
            def submit(self,*args):raise AssertionError('Invalid requests cannot enqueue work')
        with tempfile.TemporaryDirectory() as directory:
            router,_=create_router(Path(directory)/'jobs.sqlite',Reject());app=FastAPI();app.include_router(router);c=TestClient(app)
            for change in [{'frame_indices':[0,0]},{'fov_arcmin':4},{'method':'unvalidated_median'},{'sequence_id':'../bad'}]:
                self.assertEqual(c.post('/v1/coadds',json=self.request()|change).status_code,422)

    def test_real_source_job_exports_dedup_and_shared_recovery(self):
        class Queue:
            def __init__(self):self.calls=[]
            def submit(self,*args):self.calls.append(args)
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'VANTAGE_RUNTIME':directory}):
            q=Queue();database=Path(directory)/'jobs.sqlite';router,recover=create_router(database,q)
            app=FastAPI();app.include_router(router);client=TestClient(app)
            response=client.post('/v1/source-samples',json={})
            self.assertEqual(response.status_code,202,response.text)
            first=response.json();reverse=client.post('/v1/source-samples',json={'observation_indices':[3,2,1,0]}).json()
            self.assertEqual(first['job_id'],reverse['job_id'])
            self.assertEqual(recover(),1)
            q.calls[-1][0](*q.calls[-1][1:])
            job=client.get(first['status_url']).json()
            self.assertEqual(job['state'],'complete',job)
            result=client.get('/v1/products/'+job['result_id']).json()
            self.assertEqual(result['type'],'source_samples')
            for name in ['samples.ecsv','samples.csv','plot.svg']:
                self.assertEqual(client.get('/v1/products/'+job['result_id']+'/'+name).status_code,200)
            self.assertEqual(client.get('/v1/products/'+job['result_id']+'/samples.ecsv').headers['content-type'],'text/plain; charset=utf-8')
            self.assertEqual(client.post('/v1/source-samples',json={'target_key':'../bad'}).status_code,422)
            self.assertEqual(client.get('/v1/products/not-valid/samples.csv').status_code,422)
            a=client.post('/v1/source-samples',json={'method':'aperture'}).json()
            client.delete(a['status_url']);retry=client.post('/v1/source-samples',json={'method':'aperture'}).json()
            self.assertNotEqual(a['job_id'],retry['job_id'])
            q.calls[-2][0](*q.calls[-2][1:])
            self.assertEqual(client.get(a['status_url']).json()['state'],'cancelled')
            # Coadds and source samples count against the same ten-job bound.
            for mask in range(1,16):
                selected=[i for i in range(4) if mask&(1<<i)]
                client.post('/v1/source-samples',json={'observation_indices':selected})
            self.assertEqual(client.post('/v1/coadds',json=self.request()).status_code,429)

if __name__=='__main__':unittest.main()
