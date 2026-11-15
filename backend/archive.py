"""Bounded access to official IRSA endpoints, refreshed November 14, 2026.

https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/
"""
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
import math
import hashlib
import xml.etree.ElementTree as ET
import tempfile
import json
import time
import re
import os
import threading
import numpy as np
import aiohttp
from astropy.io import fits
from astropy.wcs import WCS
from scipy.ndimage import map_coordinates

import requests
from astropy.coordinates import Angle
from astropy.io.votable import parse

from backend.science import ROOT, write_json

CACHE = ROOT / '.runtime/sources'
CACHE.mkdir(parents=True, exist_ok=True)
S3_OPTIONS={'block_size':65536,'cache_type':'bytes','client_kwargs':{'timeout':aiohttp.ClientTimeout(total=25,connect=8,sock_read=20)}}
cache_lock=threading.Lock()


def publish_cached_file(temporary,target):
    """Single-instance quota and atomic publication; never evict science inputs."""
    temporary,target=Path(temporary),Path(target)
    if temporary.parent.resolve()!=CACHE.resolve() or target.parent.resolve()!=CACHE.resolve():
        raise ValueError('Archive cache publication must remain inside its source directory')
    if temporary.resolve()==target.resolve():raise ValueError('Cache publication requires a distinct temporary file')
    with cache_lock:
        try:
            if target.exists():return target
            limit=int(os.environ.get('VANTAGE_SOURCE_CACHE_BYTES',str(5*1024**3)))
            # Includes in-flight temporary files, so simultaneous writers cannot
            # each spend the same remaining capacity in this service instance.
            current=0
            for path in CACHE.iterdir():
                try:
                    if path.is_file():current+=path.stat().st_size
                except FileNotFoundError:continue  # an atomic metadata temp file was renamed
            if current>limit:raise ValueError('Archive source cache is full. Existing inputs were retained; storage cleanup or expansion is required.')
            temporary.replace(target)
            return target
        finally:temporary.unlink(missing_ok=True)


def coordinates(ra, dec):
    ra = str(ra).strip().replace('−', '-')
    dec = str(dec).strip().replace('−', '-')
    if len(ra) > 128 or len(dec) > 128:
        raise ValueError('Coordinate inputs must be at most 128 characters')
    try:
        # Numeric RA means degrees. Sexagesimal requires an explicit h/d unit.
        try:
            longitude = float(ra)
        except ValueError:
            if not any(unit in ra.lower() for unit in ('h', 'd', '°')):
                raise ValueError('Sexagesimal RA needs h/m/s or explicit degree units')
            longitude = Angle(ra).degree
        try:
            latitude = float(dec)
        except ValueError:
            if not any(unit in dec.lower() for unit in ('d', '°')):
                raise ValueError('Sexagesimal declination needs d/m/s or explicit degree units')
            latitude = Angle(dec).degree
        if not math.isfinite(longitude) or not math.isfinite(latitude) or not -90 <= latitude <= 90:
            raise ValueError('Coordinates must be finite and declination between -90 and +90 degrees')
        return [longitude % 360, latitude]
    except (ValueError, TypeError) as error:
        raise ValueError(str(error)) from error


def allowed(url):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.port not in (None,443) or parsed.username or parsed.password or parsed.fragment or '..' in parsed.path.split('/'):
        raise ValueError('Only official HTTPS IRSA artifacts are accepted')
    if parsed.hostname=='irsa.ipac.caltech.edu' and parsed.path.startswith(('/ibe/data/spherex/','/datalink/links/spherex')):
        return url
    if parsed.hostname=='nasa-irsa-spherex.s3.us-east-1.amazonaws.com' and not parsed.query:
        parts=parsed.path.strip('/').split('/')
        if len(parts)==5:
            release,kind,collection,detector,filename=parts
            prefix={'spectral_wcs':'swcs','solid_angle_pixel_map':'sapm'}.get(kind)
            if (release in ('dr1','qr3') and prefix and detector in '123456' and len(detector)==1
                and re.fullmatch(r'cal-'+prefix+r'-v\d+-\d{4}-\d{3}',collection)
                and filename==f'{kind}_D{detector}_spx_{collection}.fits'):
                return url
    raise ValueError('Unsupported archive artifact host or calibration path')


def retrieve(url, params=None, limit=40_000_000):
    allowed(url)
    identity = hashlib.sha256((url + repr(sorted((params or {}).items()))).encode()).hexdigest()
    target = CACHE / (identity + '.fits')
    if target.exists():
        return target
    response = None
    for attempt in range(3):
        response = requests.get(url, params=params, timeout=(8, 35), stream=True, allow_redirects=False)
        if response.status_code not in (429, 502, 503, 504):
            break
        response.close()
        if attempt < 2:
            time.sleep(attempt + 1)
    with response:
        response.raise_for_status()
        if response.is_redirect:
            raise ValueError('Archive redirect requires explicit review')
        chunks = []
        total = 0
        for chunk in response.iter_content(1024 * 64):
            total += len(chunk)
            if total > limit:
                raise ValueError('Archive artifact exceeds the work limit')
            chunks.append(chunk)
    content = b''.join(chunks)
    with tempfile.NamedTemporaryFile(dir=CACHE, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    return publish_cached_file(temporary,target)


def votable(content):
    tree = ET.fromstring(content)
    statuses = [node.attrib.get('value') for node in tree.iter() if node.tag.endswith('INFO') and node.attrib.get('name') == 'QUERY_STATUS']
    if 'ERROR' in statuses:
        raise ValueError('Archive returned a VO query error')
    table = parse(BytesIO(content)).get_first_table().to_table(use_names_over_ids=True)
    return table, 'OVERFLOW' in statuses


def discover(center, fov, refresh=False,include_deep=False,time_bounds=None):
    if time_bounds is not None and (len(time_bounds)!=2 or not np.isfinite(time_bounds).all() or time_bounds[0]>=time_bounds[1]):
        raise ValueError('Discovery time bounds must be finite and increasing')
    collections=['spherex_dr1','spherex_qr3']+(['spherex_dr1_deep','spherex_qr3_deep'] if include_deep else [])
    identity = hashlib.sha256(json.dumps([center, fov, 'dr1-qr3-20261115',collections,time_bounds]).encode()).hexdigest()
    cache = CACHE / (identity + '.json')
    if not cache.exists() and not refresh and not include_deep and time_bounds is None:
        legacy=CACHE/(hashlib.sha256(json.dumps([center,fov,'dr1-qr3-20261114']).encode()).hexdigest()+'.json')
        if legacy.is_file():
            saved=json.loads(legacy.read_text(encoding='utf-8'))
            lifetime=86400 if saved['observations'] else 900
            if time.time()-legacy.stat().st_mtime<lifetime:
                return saved|{'data_status':'cached','collections':collections,'time_bounds_mjd_utc':None}
    if cache.exists() and not refresh:
        saved = json.loads(cache.read_text())
        lifetime = 86400 if saved['observations'] else 900
        if time.time() - cache.stat().st_mtime < lifetime:
            return saved | {'data_status': 'cached'}
    radius = fov / 60 / math.sqrt(2) + 15 / 3600
    observations = []
    limited = False
    queries = []
    for collection in collections:
        params={
            'COLLECTION': collection, 'POS': f'CIRCLE {center[0]} {center[1]} {radius}', 'MAXREC': 500,
        }
        if time_bounds is not None:params['TIME']=f'{time_bounds[0]} {time_bounds[1]}'
        for attempt in range(3):
            try:
                response=requests.get('https://irsa.ipac.caltech.edu/SIA',params=params,timeout=(8,35),stream=True)
                if response.status_code not in (429,502,503,504) or attempt==2:break
                response.close()
            except (requests.ConnectionError,requests.Timeout):
                if attempt==2:raise
            time.sleep(attempt+1)
        with response:
            response.raise_for_status()
            chunks = []
            total = 0
            for chunk in response.iter_content(65536):
                total += len(chunk)
                if total > 8_000_000:
                    raise ValueError('Discovery response exceeds work budget')
                chunks.append(chunk)
            table, overflow = votable(b''.join(chunks))
            limited |= overflow
            queries.append(response.url)
        for row in table:
            url = str(row['access_url'])
            if '/level2/' not in url:
                continue
            observations.append({
                'obs_id': str(row['obs_id']), 'publisher_id': str(row['obs_publisher_did']),
                'detector': int(str(row['energy_bandpassname']).split('D')[-1]),
                'release': collection.removeprefix('spherex_').removesuffix('_deep'),
                'survey':'deep' if collection.endswith('_deep') else 'wide','ibe': allowed(url),
                'mjd_mid': (float(row['t_min']) + float(row['t_max'])) / 2,
                'em_min_um': float(row['em_min']) * 1e6, 'em_max_um': float(row['em_max']) * 1e6,
                'cloud_access': json.loads(str(row['cloud_access'])) if 'cloud_access' in table.colnames else None,
            })
    observations.sort(key=lambda row: (row['mjd_mid'], row['obs_id'], row['detector']))
    unique={}
    for row in observations:
        key=(row['obs_id'],row['detector'])
        rank=lambda r:(r['release']!='dr1',r['survey']!='wide')
        if key not in unique or rank(row)<rank(unique[key]):unique[key]=row
    visit_times = []
    for row in unique.values():
        if not visit_times or row['mjd_mid'] - visit_times[-1] >= 1:
            visit_times.append(row['mjd_mid'])
    coverage_state = ('empty', 'single', 'pair')[len(visit_times)] if len(visit_times) < 3 else 'sequence'
    result = {'center_deg': center, 'fov_arcmin': fov, 'observations': list(unique.values()),'collections':collections,'time_bounds_mjd_utc':time_bounds,
            'search_completeness': 'limited' if limited else 'complete', 'queries': queries,
            'data_status': 'live', 'coverage_state': coverage_state, 'visit_count': len(visit_times),
            'retrieved_utc': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()}
    write_json(cache, result)
    return result


def calibration(row):
    url = 'https://irsa.ipac.caltech.edu/datalink/links/spherex'
    path = retrieve(url, {'ID': row['publisher_id']}, limit=1_000_000)
    table, _ = votable(path.read_bytes())
    matches = [str(record['access_url']) for record in table if 'spectral_wcs' in str(record['access_url'])]
    if len(matches) != 1:
        raise ValueError('An unambiguous spectral calibration association is required')
    associated=allowed(matches[0])
    try:return associated,retrieve(associated)
    except requests.RequestException:
        # IRSA documents the NASA S3 bucket as a mirror of these release files.
        # Preserve the actual DataLink association; never choose a newer map.
        # The strict mirror allowlist rejects non-calibration and unknown paths.
        mirror=associated.replace('https://irsa.ipac.caltech.edu/ibe/data/spherex/',
                                  'https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/')
        return associated,retrieve(allowed(mirror))


def wavelength_at_center(row,center):
    """Read only native header metadata before fetching science cutouts."""
    cloud=(row.get('cloud_access') or {}).get('aws')
    if not cloud or cloud.get('bucket_name')!='nasa-irsa-spherex' or cloud.get('region')!='us-east-1':
        raise ValueError('Precision selection requires verified cloud header access')
    key=cloud['key']
    if not key.startswith(row['release']+'/level2/') or '..' in key:
        raise ValueError('Unsupported cloud header path')
    url=f'https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/{key}'
    with fits.open(url,use_fsspec=True,fsspec_kwargs=S3_OPTIONS) as hdus:
        header=hdus['IMAGE'].header.copy()
        shape=hdus['IMAGE'].shape
    x,y=WCS(header).world_to_pixel_values(*center)
    if not np.isfinite([x,y]).all() or not (0<=x<shape[1] and 0<=y<shape[0]):
        return None
    cal_url,path=calibration(row)
    with fits.open(path,memmap=False) as hdus:
        if int(hdus['CWAVE'].header['DETECTOR'])!=row['detector']:
            raise ValueError('Precision calibration detector mismatch')
        wave=float(map_coordinates(hdus['CWAVE'].data,[[y],[x]],order=1,cval=np.nan)[0])
        width=float(map_coordinates(hdus['CBAND'].data,[[y],[x]],order=1,cval=np.nan)[0])
    return [wave,width] if np.isfinite([wave,width]).all() and width>0 else None


def native_cutout(row, center, fov):
    params = {'center': f'{center[0]},{center[1]}deg', 'size': f'{fov/60*1.5}deg'}
    try:
        return retrieve(row['ibe'], params), 'native_ibe_cutout'
    except requests.RequestException:
        cloud = (row.get('cloud_access') or {}).get('aws')
        if not cloud or cloud.get('bucket_name') != 'nasa-irsa-spherex' or cloud.get('region') != 'us-east-1':
            raise ValueError('IBE failed and no verified cloud artifact is available')
        key = cloud['key']
        if not key.startswith(row['release']+'/level2/') or '..' in key:
            raise ValueError('Unexpected cloud artifact key')
        cloud_url = f'https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/{key}'
        identity = hashlib.sha256((cloud_url+repr(center)+str(fov)).encode()).hexdigest()
        target = CACHE/(identity+'.fits')
        if target.exists():
            return target, 'native_s3_section'
        # Native sections and adjusted alternate origins follow the verified crop
        # method in research/verify_native_crop.py. EPSF and wavelength tables remain intact.
        with fits.open(cloud_url, use_fsspec=True, fsspec_kwargs=S3_OPTIONS) as hdus:
            header = hdus['IMAGE'].header
            x,y = WCS(header).world_to_pixel_values(*center)
            if not np.isfinite([x,y]).all():
                raise ValueError('Coordinate outside usable WCS')
            radius = int(np.ceil(fov*60/6.15*1.5/2))+3
            height,width = hdus['IMAGE'].shape
            x0,x1 = max(0,int(x)-radius), min(width,int(x)+radius+1)
            y0,y1 = max(0,int(y)-radius), min(height,int(y)+radius+1)
            if x1<=x0 or y1<=y0:
                raise ValueError('Exposure does not cover requested center')
            result = [hdus[0].copy()]
            for name in ('IMAGE','FLAGS','VARIANCE','ZODI'):
                hdr = hdus[name].header.copy()
                for card in hdr:
                    if card.startswith('CRPIX1') and len(card)<=7:
                        hdr[card] -= x0
                    if card.startswith('CRPIX2') and len(card)<=7:
                        hdr[card] -= y0
                result.append(fits.ImageHDU(data=hdus[name].section[y0:y1,x0:x1].copy(),header=hdr,name=name))
            for name in ('PSF','EPSF','WCS-WAVE'):
                if name in hdus:
                    result.append(hdus[name].copy())
            with tempfile.NamedTemporaryFile(dir=CACHE,delete=False) as handle:
                temp = Path(handle.name)
            try:
                fits.HDUList(result).writeto(temp,overwrite=True)
                publish_cached_file(temp,target)
            finally:temp.unlink(missing_ok=True)
        return target, 'native_s3_section'
