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

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.archive import coordinates, discover, native_cutout, calibration
from backend.science import ROOT, build_sequence

RUNTIME = ROOT / '.runtime'
RUNTIME.mkdir(exist_ok=True)
app = FastAPI(title='Vantage scientific service')
pool = ThreadPoolExecutor(max_workers=2)
lock = threading.Lock()
database = RUNTIME / 'jobs.sqlite'


def connect():
    return sqlite3.connect(database, timeout=15)


with closing(connect()) as db:
    db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, state TEXT, result TEXT, error TEXT, request TEXT)')
    db.execute("UPDATE jobs SET state='interrupted',error='Service restarted. Retry the request.' WHERE state NOT IN ('complete','failed','cancelled','interrupted')")
    db.commit()


class Search(BaseModel):
    ra: str | float
    dec: str | float
    fov_arcmin: float = Field(default=6, ge=1, le=30)


class SequenceRequest(Search):
    observations: list[dict] = Field(default_factory=list, max_length=8)
    detector: int = Field(default=6, ge=1, le=6)
    max_frames: int = Field(default=3, ge=1, le=8)


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
        if request.observations:
            wanted = {(r['obs_id'], r['detector']) for r in request.observations}
            rows = [r for r in rows if (r['obs_id'], r['detector']) in wanted]
        visits = []
        for row in rows:
            if not visits or row['mjd_mid'] - visits[-1]['mjd_mid'] >= 1:
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
            path = native_cutout(row, center, request.fov_arcmin)
            url, cal = calibration(row)
            records.append(row | {'fixture': str(path), 'source_calibration': str(cal), 'source_calibration_url': url})
        check_cancel(job_id)
        state(job_id, 'alignment')
        manifest = build_sequence('live', 'Your sky field', center, request.fov_arcmin, records, ROOT/'public/prepared',
                                   note='Bounded live visit selection. Inspect wavelength and defect support before interpretation.', data_status='live')
        check_cancel(job_id)
        state(job_id, 'complete', manifest['id'])
    except Exception as error:
        state(job_id, 'failed', error=str(error))


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
    normalized = request.model_dump_json()
    job_id = hashlib.sha256(normalized.encode()).hexdigest()
    with lock, closing(connect()) as db:
        existing = db.execute('SELECT state FROM jobs WHERE id=?', (job_id,)).fetchone()
        if existing and existing[0] not in ('failed', 'cancelled', 'interrupted'):
            return {'job_id': job_id, 'status_url': f'/v1/jobs/{job_id}'}
        pending = db.execute("SELECT COUNT(*) FROM jobs WHERE state NOT IN ('complete','failed','cancelled','interrupted')").fetchone()[0]
        if pending >= 20:
            raise HTTPException(429, 'Processing queue is full. Try again shortly.')
        db.execute('INSERT OR REPLACE INTO jobs VALUES (?,?,?,?,?)', (job_id, 'queued', None, None, normalized))
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
