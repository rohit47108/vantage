"""Release-specific optical/IR context. Catalog associations are not detections.

https://irsa.ipac.caltech.edu/applications/Gator/GatorAid/irsa/catsearch.html
https://gea.esac.esa.int/archive/documentation/GDR3/Gaia_archive/chap_datamodel/sec_dm_main_source_catalogue/ssec_dm_gaia_source.html
https://irsa.ipac.caltech.edu/data/WISE/docs/release/AllWISE/expsup/sec2_1a.html
"""
import hashlib
import json
import math
import os
import time
import threading
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import quote,urlparse,urljoin
import numpy as np
import requests
import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time
from astropy.wcs import WCS
from backend.science import ROOT,write_json
from backend.archive import votable

POLICY='survey-context-3'
GATOR='https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query'
CONFIG={
    'gaia':{'catalog':'gaia_dr3_source','columns':'source_id,ra,dec,ref_epoch,pmra,pmdec,parallax,radial_velocity,phot_g_mean_mag,ra_error,dec_error,pmra_error,pmdec_error,ruwe,astrometric_params_solved,duplicated_source',
            'documentation':'https://irsa.ipac.caltech.edu/data/Gaia/dr3/gaia_dr3_source_colDescriptions.html',
            'credits':'Data from the ESA Gaia mission, processed by DPAC. DPAC funding is provided by national institutions, particularly those participating in the Gaia Multilateral Agreement. Cite Gaia Collaboration 2016 (The Gaia mission) and Gaia Collaboration 2023 (Gaia DR3 summary). Served by NASA/IPAC IRSA.',
            'acknowledgment_url':'https://gea.esac.esa.int/archive/documentation/GDR3/Miscellaneous/sec_credit_and_citation_instructions/'},
    'wise':{'catalog':'allwise_p3as_psd','columns':'designation,ra,dec,w1mpro,w2mpro,w1mjdmean,w2mjdmean,cc_flags,ph_qual,ext_flg',
            'documentation':'https://irsa.ipac.caltech.edu/data/WISE/docs/release/AllWISE/expsup/sec2_1a.html',
            'credits':'WISE is a joint project of UCLA and JPL/Caltech, funded by NASA. AllWISE combines WISE and NEOWISE observations. Data served by NASA/IPAC IRSA, funded by NASA and operated by Caltech.',
            'acknowledgment_url':'https://irsa.ipac.caltech.edu/docs/knowledgebase/general.html'},
}
slots=threading.BoundedSemaphore(2)
name_slot=threading.BoundedSemaphore(1)

def _number(value):
    if value is None or np.ma.is_masked(value):return None
    try:
        f=float(value)
        return f if math.isfinite(f) else None
    except (ValueError,TypeError):return None

def parse_catalog(content,survey):
    if survey not in CONFIG:raise ValueError('Unknown survey')
    table,_=votable(content)
    required=['ra','dec','source_id','ref_epoch'] if survey=='gaia' else ['ra','dec','designation','w1mjdmean','w2mjdmean']
    if any(n not in table.colnames for n in required):raise ValueError('Catalog schema no longer matches the tested adapter')
    rows=[]
    for row in table:
        ra,dec=_number(row['ra']),_number(row['dec'])
        if ra is None or dec is None or not 0<=ra<360 or not -90<=dec<=90:continue
        identifier=str(row['source_id' if survey=='gaia' else 'designation']).strip()
        if not identifier or len(identifier)>80 or (survey=='gaia' and not identifier.isdigit()):continue
        record={'id':identifier,'ra':ra,'dec':dec}
        columns=CONFIG[survey]['columns'].split(',')
        for name in columns:
            if name not in table.colnames or name in ['source_id','designation','ra','dec']:continue
            record[name]=str(row[name]).strip() if name in ['cc_flags','ph_qual'] else _number(row[name])
        rows.append(record)
    return rows

def _at_year(row,year):
    ra=float(row['ra']);dec=float(row['dec'])
    if any(row.get(k) is None for k in ['pmra','pmdec','ref_epoch']):
        return ra,dec,'catalog_position_missing_motion'
    r,d=np.deg2rad([ra,dec]);dt=year-float(row['ref_epoch'])
    factor=np.deg2rad(1/3_600_000)
    tangent_ra=np.array([-np.sin(r),np.cos(r),0.])
    tangent_dec=np.array([-np.cos(r)*np.sin(d),-np.sin(r)*np.sin(d),np.cos(d)])
    unit=np.array([np.cos(r)*np.cos(d),np.sin(r)*np.cos(d),np.sin(d)])
    position=unit+dt*factor*(float(row['pmra'])*tangent_ra+float(row['pmdec'])*tangent_dec)
    position/=np.linalg.norm(position)
    return float(np.rad2deg(np.arctan2(position[1],position[0]))%360),float(np.rad2deg(np.arctan2(position[2],np.hypot(*position[:2])))), 'angular_motion_no_observer_parallax'

def propagate_gaia(row,mjd):
    """Unit-sphere rectilinear angular motion; pmra is mu_alpha*cos(delta).

    Gaia ref_epoch is a Julian year in TCB. UTC exposure MJD is converted by
    Astropy. No distance/RV perspective acceleration or observer parallax is
    modeled. This is an explicit contextual locator, not precision astrometry.
    """
    if not math.isfinite(mjd):raise ValueError('Epoch must be finite')
    return _at_year(row,float(Time(mjd,format='mjd',scale='utc').tcb.jyear))

def project_layer(survey,rows,sequence):
    output=[];height,width=sequence['shape']
    frames=sequence['frames'];grids=[WCS(f.get('grid',sequence['grid'])) for f in frames]
    years=[float(Time(f['mjd_mid'],format='mjd',scale='utc').tcb.jyear) for f in frames]
    for row in rows:
        coordinates=[_at_year(row,y)[:2] for y in years] if survey=='gaia' else [(row['ra'],row['dec'])]*len(frames)
        pixels=[list(map(float,w.world_to_pixel_values(*c))) for c,w in zip(coordinates,grids)]
        if not any(math.isfinite(x) and math.isfinite(y) and -.5<=x<width-.5 and -.5<=y<height-.5 for x,y in pixels):continue
        model=_at_year(row,years[0])[2] if survey=='gaia' else 'catalog_position_no_motion_correction'
        pixels=[p if all(math.isfinite(v) for v in p) else None for p in pixels]
        output.append({**row,'survey':survey,'coordinates_by_frame':coordinates,'pixels_by_frame':pixels,
                       'motion_model':model,'observer_parallax_applied':False})
    return output

def candidate_associations(gaia,wise,radius_arcsec=2.,limit=500):
    pairs=[]
    if not gaia:return pairs
    for w in wise:
        epoch=w.get('w1mjdmean')
        if epoch is None:continue
        year=float(Time(epoch,format='mjd',scale='utc').tcb.jyear)
        coordinates=[_at_year(g,year)[:2] for g in gaia]
        gcoords=SkyCoord([c[0] for c in coordinates]*u.deg,[c[1] for c in coordinates]*u.deg)
        separation=gcoords.separation(SkyCoord(w['ra']*u.deg,w['dec']*u.deg)).arcsec
        for i in np.flatnonzero(separation<=radius_arcsec):
            pairs.append({'gaia_id':gaia[i]['id'],'wise_id':w['id'],'status':'candidate_association',
                          'separation_arcsec':float(separation[i]),'comparison_epoch_mjd':epoch,
                          'epoch_basis':'WISE W1 mean observation MJD used as an approximate positional epoch; no observer parallax.',
                          'gaia_motion_model':_at_year(gaia[i],year)[2]})
    return sorted(pairs,key=lambda p:p['separation_arcsec'])[:limit]

def resolve_xml(content):
    tree=ET.fromstring(content)
    for resolver in tree.iter('Resolver'):
        ra,dec=_number(resolver.findtext('jradeg')),_number(resolver.findtext('jdedeg'))
        if ra is not None and dec is not None and 0<=ra<360 and -90<=dec<=90:
            return {'center_deg':[ra,dec],'name':resolver.findtext('oname') or tree.findtext('.//Target/name'),
                    'provider':resolver.attrib.get('name','CDS Sesame'),'frame':'ICRS',
                    'position_reference':resolver.findtext('refPos'),
                    'warning':'Resolved catalog position. No observation epoch or proper-motion correction is inferred from this name lookup.'}
    raise ValueError('No finite catalog position was found for that name. Try another name or enter coordinates.')

def _cache():
    path=Path(os.environ.get('VANTAGE_RUNTIME',ROOT/'.runtime'))/'catalogs';path.mkdir(parents=True,exist_ok=True)
    return path

def _bytes(url,params=None,limit=4_000_000):
    with requests.get(url,params=params,timeout=(8,25),stream=True,allow_redirects=False) as response:
        response.raise_for_status()
        if response.is_redirect:raise ValueError('Unexpected catalog redirect')
        chunks=[];total=0
        for chunk in response.iter_content(65536):
            total+=len(chunk)
            if total>limit:raise ValueError('Catalog response exceeds the work limit')
            chunks.append(chunk)
        return b''.join(chunks),response.url

def fetch_catalog(survey,center,radius):
    config=CONFIG[survey]
    key=hashlib.sha256(json.dumps([POLICY,survey,center,radius],sort_keys=True).encode()).hexdigest()
    path=_cache()/(key+'.json')
    if path.is_file() and time.time()-path.stat().st_mtime<86400:
        return json.loads(path.read_text(encoding='utf-8'))|{'data_status':'cached'}
    if not slots.acquire(blocking=False):raise RuntimeError('Catalog service busy; retry shortly')
    try:
        params={'catalog':config['catalog'],'spatial':'cone','radius':radius,'radunits':'deg',
                'objstr':f'{center[0]} {center[1]}','outfmt':3,'selcols':config['columns'],'outrows':5000}
        reduced=False;deadline=time.monotonic()+45
        for attempt in range(7):
            content,url=_bytes(GATOR,params)
            tree=ET.fromstring(content)
            errors=[(node.text or '') for node in tree.iter() if node.tag.endswith('INFO') and node.attrib.get('value')=='ERROR']
            if any('Exceeding output table size limit' in e for e in errors):
                if attempt==6 or time.monotonic()>deadline:raise ValueError('Dense catalog field exceeds bounded search; choose a smaller field')
                params['radius']/=2;reduced=True;continue
            rows=parse_catalog(content,survey)
            table,overflow=votable(content)
            break
        query_urls=[url];supplemental=[]
        if survey=='gaia' and reduced:
            # A dense central region must not silently remove a high-motion
            # source from the larger epoch-padding cone.
            extra=dict(params,radius=radius,constraints='pm>1000')
            data,extra_url=_bytes(GATOR,extra)
            fast=parse_catalog(data,survey)
            rows=list({row['id']:row for row in rows+fast}.values())
            query_urls.append(extra_url);supplemental.append(hashlib.sha256(data).hexdigest())
        rows.sort(key=lambda row:(-int(math.hypot(row.get('pmra') or 0,row.get('pmdec') or 0)>1000),
                                  SkyCoord(row['ra']*u.deg,row['dec']*u.deg).separation(SkyCoord(center[0]*u.deg,center[1]*u.deg)).deg))
        result={'rows':rows[:500],'limited':reduced or overflow or len(rows)>500,'query_url':url,
                'query_urls':query_urls,'supplemental_sha256':supplemental,
                'queried_radius_deg':params['radius'],'returned_catalog_rows':len(table),
                'raw_sha256':hashlib.sha256(content).hexdigest(),'retrieved_utc':datetime.now(timezone.utc).isoformat(),
                'catalog':config['catalog'],'data_status':'live'}
        write_json(path,result)
        return result
    finally:slots.release()

def sequence_manifest(sequence_id):
    if len(sequence_id)!=64 or any(c not in '0123456789abcdef' for c in sequence_id):raise ValueError('Invalid sequence identity')
    path=ROOT/'public/prepared'/sequence_id/'manifest.json'
    if not path.is_file():raise FileNotFoundError('Sequence unavailable')
    return json.loads(path.read_text(encoding='utf-8'))

def layer(survey,sequence):
    if survey not in CONFIG:raise ValueError('Unknown survey')
    frames=sequence['frames'];center=sequence['center_deg']
    centers=[f.get('grid',sequence['grid']) for f in frames]
    center_coord=SkyCoord(center[0]*u.deg,center[1]*u.deg)
    drift=max(center_coord.separation(SkyCoord(h['CRVAL1']*u.deg,h['CRVAL2']*u.deg)).deg for h in centers)
    years=[float(Time(f['mjd_mid'],format='mjd',scale='utc').tcb.jyear) for f in frames]
    padding=12*max(abs(y-2016) for y in years)/3600 if survey=='gaia' else 0.
    radius=sequence['fov_arcmin']/60/math.sqrt(2)+drift+padding+2/3600
    radius_limited=radius>.75
    radius=min(radius,.75)
    raw=fetch_catalog(survey,center,radius)
    sources=project_layer(survey,raw['rows'],sequence)
    return {'schema_version':'1.0.0','policy':POLICY,'sequence_id':sequence['id'],'survey':survey,
            'sources':sources,'queried_rows':len(raw['rows']),'search_completeness':'limited' if raw['limited'] or radius_limited else 'complete_within_query',
            'query_radius_deg':radius,'motion_search_bound_mas_yr':12000 if survey=='gaia' else None,
            **{k:v for k,v in raw.items() if k!='rows'},**CONFIG[survey],
            'position_semantics':'Gaia angular positions propagated to each acquisition; no observer parallax/perspective acceleration.' if survey=='gaia' else 'AllWISE catalog positions retained at their historical observing epochs, not moved to the SPHEREx dates.',
            'limitations':['Catalog overlays are context, not measured SPHEREx source positions or confirmed cross-identifications.',
                           'Angular motion omits observer parallax, perspective acceleration, binaries and unknown proper motions.',
                           'Gaia search padding assumes total proper motion at most 12 arcsec/year; capped queries can omit sources.',
                           'WISE magnitudes are Vega-system profile fits; W1/W2 mean MJDs describe photometric sampling, not exact source-position reference epochs.']}

def resolve_name(name):
    name=' '.join(name.split())
    if not 1<=len(name)<=128 or any(ord(c)<32 for c in name):raise ValueError('Enter an object name of 1–128 characters')
    key=hashlib.sha256(('name1'+name.casefold()).encode()).hexdigest();path=_cache()/(key+'.json')
    if path.is_file() and time.time()-path.stat().st_mtime<604800:return json.loads(path.read_text(encoding='utf-8'))|{'data_status':'cached'}
    if not name_slot.acquire(blocking=False):raise RuntimeError('Name resolver busy; retry shortly')
    try:
        url='https://cds.unistra.fr/cgi-bin/nph-sesame/-oxp/SNV?'+quote(name,safe='')
        allowed={'cds.unistra.fr','vizier.cds.unistra.fr','vizier.idia.ac.za'}
        for _ in range(3):
            with requests.get(url,timeout=(8,15),stream=True,allow_redirects=False) as r:
                if r.is_redirect:
                    url=urljoin(url,r.headers['Location']);parsed=urlparse(url)
                    if parsed.scheme!='https' or parsed.hostname not in allowed or parsed.port not in (None,443) or parsed.username:
                        raise ValueError('Resolver redirect is not an approved CDS mirror')
                    continue
                r.raise_for_status();content=b''
                for chunk in r.iter_content(8192):
                    content+=chunk
                    if len(content)>200000:raise ValueError('Resolver response exceeds work limit')
                result=resolve_xml(content)|{'query':name,'query_url':url,'retrieved_utc':datetime.now(timezone.utc).isoformat(),'data_status':'live','credits':'CDS Sesame/SIMBAD; CDS, Strasbourg and its official mirror.'}
                write_json(path,result);return result
        raise ValueError('Resolver redirected too many times')
    finally:name_slot.release()
