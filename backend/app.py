"""Persistent jobs and validated input. Run uvicorn backend.app:app.

https://fastapi.tiangolo.com/tutorial/static-files/
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import hashlib
import json
import sqlite3
import threading
import os
import uuid
import time
import logging
from astropy.time import Time

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.archive import coordinates, discover, native_cutout, calibration, wavelength_at_center
from backend.science import ROOT, POLICY, build_sequence

RUNTIME = Path(os.environ.get('VANTAGE_RUNTIME', ROOT / '.runtime'))
RUNTIME.mkdir(exist_ok=True)
app = FastAPI(title='Vantage scientific service')


@app.middleware('http')
async def response_headers(request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    if request.url.path.startswith('/v1/'):
        response.headers['Cache-Control'] = 'no-store'
    return response
pool = ThreadPoolExecutor(max_workers=2)
lock = threading.Lock()
database = RUNTIME / 'jobs.sqlite'


def connect():
    return sqlite3.connect(database, timeout=15)


with closing(connect()) as db:
    db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, state TEXT, result TEXT, error TEXT, request TEXT)')
    columns = {row[1] for row in db.execute('PRAGMA table_info(jobs)')}
    if 'request_key' not in columns:
        db.execute('ALTER TABLE jobs ADD COLUMN request_key TEXT')
    db.execute('CREATE INDEX IF NOT EXISTS jobs_request_key ON jobs(request_key)')
    db.execute("UPDATE jobs SET state='interrupted',error='Service restarted. Retry the request.' WHERE state NOT IN ('complete','failed','cancelled','interrupted')")
    db.commit()


class Search(BaseModel):
    ra: str | float
    dec: str | float
    fov_arcmin: float = Field(default=6, ge=1, le=30)


class ObservationSelection(BaseModel):
    obs_id: str = Field(min_length=1,max_length=64)
    detector: int = Field(ge=1,le=6)


class SequenceRequest(Search):
    observations: list[ObservationSelection] = Field(default_factory=list, max_length=8)
    detector: int = Field(default=6, ge=1, le=6)
    max_frames: int = Field(default=3, ge=1, le=8)
    start_utc: str | None = Field(default=None, max_length=32)
    end_utc: str | None = Field(default=None, max_length=32)
    wavelength_goal_um: float | None = Field(default=None, ge=.7, le=5.1)


def state(job_id, status, result=None, error=None):
    with closing(connect()) as db:
        db.execute("UPDATE jobs SET state=?,result=?,error=? WHERE id=? AND state!='cancelled'", (status, result, error, job_id))
        db.commit()


def check_cancel(job_id):
    with closing(connect()) as db:
        row = db.execute('SELECT state FROM jobs WHERE id=?', (job_id,)).fetchone()
    if row[0] == 'cancelled':
        raise ValueError('Job cancelled')


def run(job_id, request):
    try:
        state(job_id, 'discovery')
        center = coordinates(request.ra, request.dec)
        result = discover(center, request.fov_arcmin)
        state(job_id, 'selection')
        rows = [r for r in result['observations'] if r['detector'] == request.detector]
        if request.start_utc:
            start = Time(request.start_utc, scale='utc').mjd
            rows = [row for row in rows if row['mjd_mid'] >= start]
        if request.end_utc:
            end = Time(request.end_utc, scale='utc').mjd + 1
            rows = [row for row in rows if row['mjd_mid'] < end]
        if request.wavelength_goal_um is not None:
            rows = [row for row in rows if row['em_min_um'] <= request.wavelength_goal_um <= row['em_max_um']]
        if request.observations:
            wanted = {(r.obs_id, r.detector) for r in request.observations}
            rows = [r for r in rows if (r['obs_id'], r['detector']) in wanted]
        if request.wavelength_goal_um is not None and rows:
            import numpy as np
            indices=np.unique(np.linspace(0,len(rows)-1,min(20,len(rows))).astype(int))
            matched=[]
            state(job_id,'precision wavelength selection')
            for index in indices:
                check_cancel(job_id)
                local=wavelength_at_center(rows[index],center)
                if local and abs(local[0]-request.wavelength_goal_um)<=.1*local[1]:
                    matched.append(rows[index])
            rows=matched
            if not rows:
                raise ValueError('No precision wavelength match in the bounded 20-header selection. Refine dates, choose another goal or leave the goal empty.')
        visits = []
        for row in rows:
            if request.observations or not visits or row['mjd_mid'] - visits[-1]['mjd_mid'] >= 1:
                visits.append(row)
        if len(visits) > request.max_frames:
            import numpy as np
            visits = [visits[i] for i in np.linspace(0, len(visits)-1, request.max_frames).astype(int)]
        if not visits:
            raise ValueError('No visits for this detector and field. Choose another detector or field.')
        records = []
        for row in visits:
            check_cancel(job_id)
            state(job_id, 'retrieval')
            path, mode = native_cutout(row, center, request.fov_arcmin)
            url, cal = calibration(row)
            records.append(row | {'fixture': str(path), 'source_calibration': str(cal), 'source_calibration_url': url, 'retrieval_mode': mode})
        check_cancel(job_id)
        state(job_id, 'alignment')
        manifest = build_sequence('live', 'Your sky field', center, request.fov_arcmin, records, ROOT/'public/prepared',
                                   note='Bounded live visit selection. Inspect wavelength and defect support before interpretation.', data_status='live')
        check_cancel(job_id)
        state(job_id, 'complete', manifest['id'])
    except Exception as error:
        logging.getLogger('vantage.jobs').exception('Archive job failed: %s',job_id)
        public_error = str(error) if isinstance(error,ValueError) else 'Archive processing failed. Retry or choose a prepared field.'
        state(job_id, 'failed', error=public_error)


@app.get('/v1/targets/resolve')
def resolve(ra: str, dec: str):
    try:
        return {'center_deg': coordinates(ra, dec), 'frame': 'ICRS'}
    except ValueError as error:
        raise HTTPException(422, str(error))


@app.post('/v1/observations/search')
def search(request: Search):
    try:
        return discover(coordinates(request.ra, request.dec), request.fov_arcmin)
    except ValueError as error:
        raise HTTPException(422, str(error))
    except Exception as error:
        raise HTTPException(502, 'IRSA is unavailable. Retry, or choose a prepared example.') from error


@app.post('/v1/sequences', status_code=202)
def sequence(request: SequenceRequest):
    try:
        coordinates(request.ra, request.dec)
    except ValueError as error:
        raise HTTPException(422, str(error))
    normalized_parameters = request.model_dump()
    normalized_parameters['policy'] = POLICY
    normalized_parameters['selection_policy'] = 'precision-goal-1'
    normalized_parameters['archive_cache_day'] = int(time.time() // 86400)
    normalized_parameters['ra'], normalized_parameters['dec'] = coordinates(request.ra, request.dec)
    normalized_parameters['observations'] = sorted(normalized_parameters['observations'], key=lambda row: (row['obs_id'],row['detector']))
    try:
        for value in (request.start_utc, request.end_utc):
            if value:
                Time(value, scale='utc')
        if request.start_utc and request.end_utc and Time(request.start_utc) > Time(request.end_utc):
            raise ValueError('Start date must precede end date')
    except ValueError as error:
        raise HTTPException(422, 'Invalid UTC date range') from error
    normalized = json.dumps(normalized_parameters, sort_keys=True, allow_nan=False)
    request_key = hashlib.sha256(normalized.encode()).hexdigest()
    job_id = uuid.uuid4().hex
    with lock, closing(connect()) as db:
        db.execute('BEGIN IMMEDIATE')
        existing = db.execute("SELECT id FROM jobs WHERE request_key=? AND state NOT IN ('failed','cancelled','interrupted')", (request_key,)).fetchone()
        if existing:
            return {'job_id': existing[0], 'status_url': f'/v1/jobs/{existing[0]}'}
        pending = db.execute("SELECT COUNT(*) FROM jobs WHERE state NOT IN ('complete','failed','cancelled','interrupted')").fetchone()[0]
        if pending >= 20:
            raise HTTPException(429, 'Processing queue is full. Try again shortly.')
        db.execute('INSERT INTO jobs (id,state,result,error,request,request_key) VALUES (?,?,?,?,?,?)', (job_id, 'queued', None, None, normalized, request_key))
        db.commit()
        pool.submit(run, job_id, request)
    return {'job_id': job_id, 'status_url': f'/v1/jobs/{job_id}'}


@app.get('/v1/jobs/{job_id}')
def job(job_id: str):
    with closing(connect()) as db:
        row = db.execute('SELECT state,result,error FROM jobs WHERE id=?', (job_id,)).fetchone()
    if not row:
        raise HTTPException(404, 'Unknown job')
    return {'job_id': job_id, 'state': row[0], 'result_id': row[1], 'error': row[2]}


@app.delete('/v1/jobs/{job_id}')
def cancel(job_id: str):
    with closing(connect()) as db:
        current = db.execute('SELECT state FROM jobs WHERE id=?',(job_id,)).fetchone()
        if not current:
            raise HTTPException(404,'Unknown job')
        if current[0] == 'complete':
            return {'state':'complete'}
        db.execute("UPDATE jobs SET state='cancelled' WHERE id=? AND state!='complete'", (job_id,))
        db.commit()
    return {'state': 'cancelled'}


@app.get('/v1/sequences/{sequence_id}')
def manifest(sequence_id: str):
    if len(sequence_id) != 64 or any(c not in '0123456789abcdef' for c in sequence_id):
        raise HTTPException(422, 'Invalid sequence identity')
    path = ROOT/'public/prepared'/sequence_id/'manifest.json'
    if not path.is_file():
        raise HTTPException(404, 'Sequence unavailable')
    return json.loads(path.read_text())


app.mount('/prepared', StaticFiles(directory=ROOT/'public/prepared'), name='prepared')


@app.get('/v1/health')
def health():
    return {'status': 'ok', 'policy': POLICY}


if (ROOT/'dist/assets').is_dir():
    app.mount('/assets', StaticFiles(directory=ROOT/'dist/assets'), name='frontend-assets')


@app.get('/')
@app.get('/sky')
@app.get('/sequence/{sequence_id}')
def frontend(sequence_id: str | None = None):
    path = ROOT/'dist/index.html'
    if not path.is_file():
        raise HTTPException(503, 'Build the frontend with npm run build before launch.')
    return FileResponse(path)


@app.get('/favicon.svg')
def favicon():
    return FileResponse(ROOT/'public/favicon.svg')
