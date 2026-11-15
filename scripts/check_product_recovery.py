"""Controlled queued-request restart test; run --seed with the API stopped."""
import argparse
import hashlib
import json
import sqlite3
import time
import uuid
import requests
from backend.science import ROOT
from backend.coadds import POLICY

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--seed',action='store_true');parser.add_argument('--verify')
    args=parser.parse_args();record=ROOT/'.runtime/recovery-check.json'
    if args.seed:
        sequence=next(s for s in json.loads((ROOT/'public/prepared/catalog.json').read_text()) if s['key']=='m101')
        request={'sequence_id':sequence['id'],'frame_indices':[0,1],'fov_arcmin':2.9,'method':'inverse_variance'}
        payload=json.dumps(request,sort_keys=True);job_id=uuid.uuid4().hex
        with sqlite3.connect(ROOT/'.runtime/jobs.sqlite') as db:
            db.execute('INSERT INTO product_jobs VALUES (?,?,?,?,?,?,?)',(job_id,hashlib.sha256((POLICY+payload).encode()).hexdigest(),payload,'queued',None,None,time.time()))
        record.write_text(json.dumps({'job_id':job_id,'method':'Controlled pending authentic-data request inserted while service stopped, then startup recovery tested.','request':request}),encoding='utf-8')
        print(job_id)
    elif args.verify:
        result=json.loads(record.read_text());deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            r=requests.get(args.verify+'/v1/analysis/jobs/'+result['job_id'],timeout=5);r.raise_for_status();job=r.json()
            if job['state'] in ['complete','failed','cancelled']:break
            time.sleep(.1)
        result['job']=job
        if job['state']=='complete':
            p=requests.get(args.verify+'/v1/products/'+job['result_id'],timeout=5);p.raise_for_status()
            result['restored_result_id']=p.json()['id']
        result['passed']=job['state']=='complete' and result.get('restored_result_id')==job['result_id']
        (ROOT/'artifacts/product-restart-recovery.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result,indent=2))
        if not result['passed']:raise SystemExit(1)
    else:parser.error('Use --seed before starting the API, then --verify http://127.0.0.1:8000')

if __name__=='__main__':main()
