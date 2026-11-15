"""Bounded context API. No user-supplied archive URLs or full-cube downloads."""
import hashlib
import json
import os
import threading
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from backend.hips import metadata, render_plane, POLICY
from backend.science import ROOT, write_json

router=APIRouter(prefix='/v1/spectral',tags=['Spectral visualization'])
slots=threading.BoundedSemaphore(2)

def storage():
    p=Path(os.environ.get('VANTAGE_RUNTIME',ROOT/'.runtime'))/'spectral'
    p.mkdir(parents=True,exist_ok=True)
    return p

@router.get('/metadata')
def spectral_metadata():return metadata()

@router.get('/plane')
def spectral_plane(ra:float=Query(ge=0,le=360),dec:float=Query(ge=-90,le=90),
                   fov_arcmin:float=Query(default=30,ge=1,le=120),layer:int=Query(default=62,ge=0,le=101)):
    key=hashlib.sha256(json.dumps([POLICY,metadata()['id'],ra%360,dec,fov_arcmin,layer]).encode()).hexdigest()
    cache=storage()/f'request-{key}.json'
    if cache.exists():return json.loads(cache.read_text(encoding='utf-8'))
    if not slots.acquire(blocking=False):raise HTTPException(429,'Spectral context is busy. Try again shortly.')
    try:
        result=render_plane([ra,dec],fov_arcmin,layer)
        write_json(storage()/f"{result['id']}.json",result)
        write_json(cache,result)
        return result
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    except Exception as exc:raise HTTPException(502,'The spectral cube could not be read. Retry or choose another field.') from exc
    finally:slots.release()

@router.get('/products/{identity}')
def spectral_product(identity:str):
    if len(identity)!=64 or any(c not in '0123456789abcdef' for c in identity):
        raise HTTPException(422,'Invalid spectral result identity')
    path=storage()/f'{identity}.json'
    if not path.is_file():raise HTTPException(404,'Spectral result is unavailable')
    return json.loads(path.read_text(encoding='utf-8'))
