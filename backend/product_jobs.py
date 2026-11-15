"""Single-instance persistent numerical jobs sharing the bounded worker pool."""
import hashlib
import json
import os
import sqlite3
import time
import uuid
import logging
import requests
from pathlib import Path
from typing import Literal
from contextlib import closing
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ConfigDict
from backend.science import ROOT
from backend.coadds import build_coadd, POLICY
from backend.spectra import SpectrumRequest,build_spectrum,target_description,POLICY as SPECTRUM_POLICY,BENCHMARK,PHOTOMETRY_POLICY
from backend.science import digest
from backend.source_fields import SourceFieldRequest,NativeExtractionRequest,build_source_field,POLICY as SOURCE_FIELD_POLICY
from backend.native_extraction import SourcePosition,ExtractionOptions,extract_observations,POLICY as NATIVE_POLICY
from backend.source_summary import SourceSummaryRequest,SummaryOptions,channel_metadata,POLICY as SUMMARY_POLICY
from backend.source_summary_products import build_source_summary


class CoaddRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    sequence_id:str=Field(pattern=r'^[a-f0-9]{64}$')
    frame_indices:list[int]=Field(min_length=2,max_length=8)
    fov_arcmin:float=Field(default=3,ge=.5,le=3.3)
    method:Literal['inverse_variance']='inverse_variance'


def create_router(database,executor):
    router=APIRouter(tags=['Numerical analysis'])
    def connect():return sqlite3.connect(database,timeout=15)
    with closing(connect()) as db:
        db.execute('CREATE TABLE IF NOT EXISTS product_jobs (id TEXT PRIMARY KEY, request_key TEXT, payload TEXT, state TEXT, result_id TEXT, error TEXT, updated REAL)')
        db.commit()
    def destination():
        path=Path(os.environ.get('VANTAGE_RUNTIME',ROOT/'.runtime'))/'products'
        path.mkdir(parents=True,exist_ok=True)
        return path
    def update(job_id,state,result=None,error=None):
        with closing(connect()) as db:
            db.execute("UPDATE product_jobs SET state=?,result_id=?,error=?,updated=? WHERE id=? AND state!='cancelled'",(state,result,error,time.time(),job_id));db.commit()
        logging.info(json.dumps({'event':'analysis_job_stage','job_id':job_id,'stage':state,'result_id':result}))
    def cancelled(job_id):
        with closing(connect()) as db:return db.execute('SELECT state FROM product_jobs WHERE id=?',(job_id,)).fetchone()[0]=='cancelled'
    def run(job_id,payload):
        try:
            if cancelled(job_id):return
            decoded=json.loads(payload)
            kind=decoded.pop('kind','coadd');decoded.pop('_attempt_nonce',None)
            def check_cancel():
                if cancelled(job_id):raise ValueError('Job cancelled')
            if kind=='source_summary':
                request=SourceSummaryRequest.model_validate(decoded)
                parent=source_parent_for(request.product_id)
                options=SummaryOptions.model_validate(request.model_dump(include=set(SummaryOptions.model_fields)))
                update(job_id,'summarizing_native_source')
                product=build_source_summary(parent,options,destination(),check_cancel)
                if not cancelled(job_id):update(job_id,'complete',product['id'])
                return
            if kind=='source_field':
                request=SourceFieldRequest.model_validate(decoded)
                update(job_id,'discovering_source_observations')
                product=build_source_field(request,destination(),check_cancel)
                if not cancelled(job_id):update(job_id,'complete',product['id'])
                return
            if kind=='native_source_samples':
                request=NativeExtractionRequest.model_validate(decoded)
                try:field=source_field_for(request)
                except HTTPException as exc:raise ValueError(str(exc.detail)) from exc
                options=ExtractionOptions.model_validate(request.model_dump(include=set(ExtractionOptions.model_fields)))
                rows=[field['observations'][i] for i in sorted(request.observation_indices)]
                context={'field_id':field['id'],'observation_indices':sorted(request.observation_indices),
                    'available_observations':len(field['observations']),'search_completeness':field['search_completeness'],
                    'time_bounds_mjd_utc':field['time_bounds_mjd_utc'],'queries':field['discovery']['queries']}
                product=extract_observations(rows,SourcePosition.model_validate(field['source']),options,destination(),
                    check_cancel=check_cancel,progress=lambda stage:update(job_id,stage),
                    selection_context=context,approved_registry=field['approved_calibrations'])
                if not cancelled(job_id):update(job_id,'complete',product['id'])
                return
            if kind=='source_samples':
                request=SpectrumRequest.model_validate(decoded)
                update(job_id,'measuring_native_source')
                product=build_spectrum(request,destination(),check_cancel=check_cancel)
                if not cancelled(job_id):update(job_id,'complete',product['id'])
                return
            request=CoaddRequest.model_validate_json(payload)
            update(job_id,'reading_native_and_reprojecting')
            path=ROOT/'public/prepared'/request.sequence_id/'manifest.json'
            if not path.is_file():raise ValueError('Sequence unavailable. Open an existing prepared or live sequence first.')
            sequence=json.loads(path.read_text(encoding='utf-8'))
            if cancelled(job_id):return
            product=build_coadd(sequence,request.frame_indices,destination(),request.fov_arcmin)
            if cancelled(job_id):return
            update(job_id,'complete',product['id'])
        except ValueError as exc:update(job_id,'failed',error=str(exc))
        except requests.RequestException:
            logging.warning(json.dumps({'event':'archive_request_unavailable','job_id':job_id}))
            update(job_id,'failed',error='The archive discovery service is temporarily unavailable. Retry the search; existing fields and results remain available.')
        except Exception:
            logging.exception('analysis_job_failed',extra={'job_id':job_id})
            update(job_id,'failed',error='Analysis processing failed. Retry this request or choose another selection.')
    def recover():
        with closing(connect()) as db:
            rows=db.execute("SELECT id,payload FROM product_jobs WHERE state NOT IN ('complete','failed','cancelled')").fetchall()
            db.execute("UPDATE product_jobs SET state='queued',updated=? WHERE state NOT IN ('complete','failed','cancelled')",(time.time(),));db.commit()
        for job_id,payload in rows:executor.submit(run,job_id,payload)
        return len(rows)

    def enqueue(normalized,policy):
        payload=json.dumps(normalized,sort_keys=True)
        key=hashlib.sha256((policy+payload).encode()).hexdigest()
        with closing(connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute("SELECT id,state,result_id FROM product_jobs WHERE request_key=? AND state NOT IN ('failed','cancelled') ORDER BY updated DESC LIMIT 1",(key,)).fetchone()
            if row and (row[1]!='complete' or (destination()/row[2]/'manifest.json').is_file()):
                return {'job_id':row[0],'status_url':f'/v1/analysis/jobs/{row[0]}'}
            pending=db.execute("SELECT COUNT(*) FROM product_jobs WHERE state NOT IN ('failed','cancelled','complete')").fetchone()[0]
            if pending>=10:raise HTTPException(429,'Analysis queue is full. Try again shortly.')
            job_id=uuid.uuid4().hex
            db.execute('INSERT INTO product_jobs (id,request_key,payload,state,result_id,error,updated) VALUES (?,?,?,?,?,?,?)',(job_id,key,payload,'queued',None,None,time.time()));db.commit()
        executor.submit(run,job_id,payload)
        return {'job_id':job_id,'status_url':f'/v1/analysis/jobs/{job_id}'}

    @router.post('/v1/coadds',status_code=202)
    def submit(request:CoaddRequest):
        if len(set(request.frame_indices))!=len(request.frame_indices) or any(i<0 or i>7 for i in request.frame_indices):
            raise HTTPException(422,'Choose two to eight distinct frame indices between 0 and 7.')
        normalized=request.model_dump();normalized['frame_indices']=sorted(request.frame_indices)
        return enqueue(normalized,POLICY)

    @router.post('/v1/source-samples',status_code=202)
    def submit_spectrum(request:SpectrumRequest):
        if request.target_revision and request.target_revision!=target_description()['revision']:
            raise HTTPException(409,'The retained target metadata changed. Reload the target before extracting.')
        normalized=request.model_dump();normalized['observation_indices']=sorted(request.observation_indices)
        normalized['kind']='source_samples'
        policy=SPECTRUM_POLICY+PHOTOMETRY_POLICY+digest(BENCHMARK/'benchmark.json')+digest(BENCHMARK/'fixture-manifest.json')
        return enqueue(normalized,policy)

    @router.get('/v1/source-targets/p330e')
    def describe_target():return target_description()

    def source_field_for(request):
        path=destination()/request.field_id/'manifest.json'
        if not path.is_file():raise HTTPException(404,'Source discovery field is unavailable. Search the source again.')
        field=json.loads(path.read_text(encoding='utf-8'))
        if field.get('type')!='source_field':raise HTTPException(422,'Choose a source-discovery field before native extraction.')
        if any(i>=len(field['observations']) for i in request.observation_indices):raise HTTPException(422,'Unknown observation index in this frozen source field.')
        if any(field['observations'][i]['measurement_capability']!='requires_native_checks' for i in request.observation_indices):
            raise HTTPException(422,'The selected release has not passed native calibration approval. Choose supported observations.')
        return field

    @router.post('/v1/source-fields',status_code=202)
    def submit_source_field(request:SourceFieldRequest):
        normalized=request.model_dump(mode='json');normalized['kind']='source_field'
        if request.refresh:normalized['_attempt_nonce']=uuid.uuid4().hex
        return enqueue(normalized,SOURCE_FIELD_POLICY)

    @router.post('/v1/native-source-samples',status_code=202)
    def submit_native_samples(request:NativeExtractionRequest):
        source_field_for(request)
        normalized=request.model_dump(mode='json');normalized['observation_indices']=sorted(request.observation_indices);normalized['kind']='native_source_samples'
        if request.refresh:normalized['_attempt_nonce']=uuid.uuid4().hex
        return enqueue(normalized,NATIVE_POLICY+PHOTOMETRY_POLICY)

    def source_parent_for(identity):
        parent=json.loads(product_path(identity,'manifest.json').read_text(encoding='utf-8'))
        if parent.get('type')!='source_samples':raise HTTPException(422,'Choose native source measurements before building a time/channel summary.')
        return parent

    @router.post('/v1/source-summaries',status_code=202)
    def submit_source_summary(request:SourceSummaryRequest):
        source_parent_for(request.product_id)
        normalized=request.model_dump(mode='json');normalized['kind']='source_summary'
        return enqueue(normalized,SUMMARY_POLICY+channel_metadata()['id'])

    @router.get('/v1/analysis/jobs/{job_id}')
    def status(job_id:str):
        with closing(connect()) as db:row=db.execute('SELECT state,result_id,error,updated FROM product_jobs WHERE id=?',(job_id,)).fetchone()
        if not row:raise HTTPException(404,'Unknown analysis job')
        return {'job_id':job_id,'state':row[0],'result_id':row[1],'error':row[2],'updated':row[3]}

    @router.delete('/v1/analysis/jobs/{job_id}')
    def cancel(job_id:str):
        with closing(connect()) as db:
            row=db.execute('SELECT state FROM product_jobs WHERE id=?',(job_id,)).fetchone()
            if not row:raise HTTPException(404,'Unknown analysis job')
            if row[0]=='complete':return {'state':'complete'}
            db.execute("UPDATE product_jobs SET state='cancelled',updated=? WHERE id=?",(time.time(),job_id));db.commit()
        return {'state':'cancelled'}

    def product_path(identity,name):
        if len(identity)!=64 or any(c not in '0123456789abcdef' for c in identity):raise HTTPException(422,'Invalid product identity')
        path=destination()/identity/name
        if not path.is_file():raise HTTPException(404,'Product unavailable')
        return path
    @router.get('/v1/products/{identity}')
    def product(identity:str):return json.loads(product_path(identity,'manifest.json').read_text(encoding='utf-8'))
    @router.get('/v1/products/{identity}/science.fits')
    def science(identity:str):return FileResponse(product_path(identity,'science.fits'),media_type='application/fits',filename=f'vantage-{identity[:12]}-coadd.fits')
    @router.get('/v1/products/{identity}/samples.ecsv')
    def ecsv(identity:str):return FileResponse(product_path(identity,'samples.ecsv'),media_type='text/plain',filename=f'vantage-{identity[:12]}-samples.ecsv')
    @router.get('/v1/products/{identity}/samples.csv')
    def csv(identity:str):return FileResponse(product_path(identity,'samples.csv'),media_type='text/csv',filename=f'vantage-{identity[:12]}-samples.csv')
    @router.get('/v1/products/{identity}/plot.svg')
    def svg(identity:str):return FileResponse(product_path(identity,'plot.svg'),media_type='image/svg+xml',filename=f'vantage-{identity[:12]}-samples.svg')
    @router.get('/v1/products/{identity}/sample-{index}.json')
    def native_context(identity:str,index:int):
        if not 0<=index<512:raise HTTPException(422,'Native sample index must be between 0 and 511.')
        return FileResponse(product_path(identity,f'sample-{index}.json'),media_type='application/json')
    @router.get('/v1/products/{identity}/{resource}')
    def source_summary_export(identity:str,resource:Literal['coverage.ecsv','coverage.csv','bins.ecsv','bins.csv','limits.ecsv','limits.csv','summary.svg']):
        return FileResponse(product_path(identity,resource),media_type='image/svg+xml' if resource.endswith('.svg') else 'text/csv' if resource.endswith('.csv') else 'text/plain',filename=f'vantage-{identity[:12]}-{resource}')
    return router,recover
