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
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

import requests
from astropy.coordinates import Angle
from astropy import units as u
from astropy.io.votable import parse

from backend.science import ROOT, digest

CACHE = ROOT / '.runtime/sources'
CACHE.mkdir(parents=True, exist_ok=True)


def coordinates(ra, dec):
    ra = str(ra).strip().replace('−', '-')
    dec = str(dec).strip().replace('−', '-')
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
    if parsed.scheme != 'https' or parsed.hostname != 'irsa.ipac.caltech.edu' or parsed.port not in (None, 443):
        raise ValueError('Only official HTTPS IRSA artifacts are accepted')
    if not parsed.path.startswith(('/ibe/data/spherex/', '/datalink/links/spherex')):
        raise ValueError('Unsupported archive artifact path')
    return url


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
    temporary.replace(target)
    return target


def votable(content):
    tree = ET.fromstring(content)
    statuses = [node.attrib.get('value') for node in tree.iter() if node.tag.endswith('INFO') and node.attrib.get('name') == 'QUERY_STATUS']
    if 'ERROR' in statuses:
        raise ValueError('Archive returned a VO query error')
    table = parse(BytesIO(content)).get_first_table().to_table(use_names_over_ids=True)
    return table, 'OVERFLOW' in statuses


def discover(center, fov):
    radius = fov / 60 / math.sqrt(2) + 15 / 3600
    observations = []
    limited = False
    queries = []
    for collection in ('spherex_dr1', 'spherex_qr3'):
        with requests.get('https://irsa.ipac.caltech.edu/SIA', params={
            'COLLECTION': collection, 'POS': f'CIRCLE {center[0]} {center[1]} {radius}', 'MAXREC': 500,
        }, timeout=(8, 35), stream=True) as response:
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
                'release': collection.removeprefix('spherex_'), 'ibe': allowed(url),
                'mjd_mid': (float(row['t_min']) + float(row['t_max'])) / 2,
                'em_min_um': float(row['em_min']) * 1e6, 'em_max_um': float(row['em_max']) * 1e6,
                'cloud_access': json.loads(str(row['cloud_access'])) if 'cloud_access' in table.colnames else None,
            })
    observations.sort(key=lambda row: (row['mjd_mid'], row['obs_id'], row['detector']))
    unique = {(r['obs_id'], r['detector']): r for r in observations}
    return {'center_deg': center, 'fov_arcmin': fov, 'observations': list(unique.values()),
            'search_completeness': 'limited' if limited else 'complete', 'queries': queries,
            'data_status': 'live', 'coverage_state': 'empty' if not unique else 'sequence'}


def calibration(row):
    url = 'https://irsa.ipac.caltech.edu/datalink/links/spherex'
    path = retrieve(url, {'ID': row['publisher_id']}, limit=1_000_000)
    table, _ = votable(path.read_bytes())
    matches = [str(record['access_url']) for record in table if 'spectral_wcs' in str(record['access_url'])]
    if len(matches) != 1:
        raise ValueError('An unambiguous spectral calibration association is required')
    return matches[0], retrieve(matches[0])


def native_cutout(row, center, fov):
    params = {'center': f'{center[0]},{center[1]}deg', 'size': f'{fov/60*1.5}deg'}
    try:
        return retrieve(row['ibe'], params)
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
            return target
        # Native sections and adjusted alternate origins follow the verified crop
        # method in research/verify_native_crop.py. EPSF and wavelength tables remain intact.
        with fits.open(cloud_url, use_fsspec=True, fsspec_kwargs={'block_size':65536,'cache_type':'bytes'}) as hdus:
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
            fits.HDUList(result).writeto(temp,overwrite=True)
            temp.replace(target)
        return target
