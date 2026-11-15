"""Live catalog math check, independent of the application's pixel projection.

No centroid-accuracy claim: Gaia observer parallax and perspective are omitted.
Astropy reference: https://docs.astropy.org/en/stable/coordinates/apply_space_motion.html
"""
import json
import math
import warnings
from pathlib import Path
from datetime import datetime,timezone
import requests
import numpy as np
import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time
from backend.science import ROOT


def tangent_pixel(ra,dec,header):
    """Independent analytic gnomonic projection, zero-based pixel centers."""
    r,d=np.deg2rad([ra,dec]);r0,d0=np.deg2rad([header['CRVAL1'],header['CRVAL2']])
    denominator=np.sin(d)*np.sin(d0)+np.cos(d)*np.cos(d0)*np.cos(r-r0)
    xi=np.rad2deg(np.cos(d)*np.sin(r-r0)/denominator)
    eta=np.rad2deg((np.sin(d)*np.cos(d0)-np.cos(d)*np.sin(d0)*np.cos(r-r0))/denominator)
    matrix=np.array([[header.get('PC1_1',1),header.get('PC1_2',0)],
                     [header.get('PC2_1',0),header.get('PC2_2',1)]])
    delta=np.linalg.solve(matrix,np.array([xi/header['CDELT1'],eta/header['CDELT2']]))
    return delta+np.array([header['CRPIX1']-1,header['CRPIX2']-1])


def validate(base='http://127.0.0.1:8000'):
    catalog=json.loads((ROOT/'public/prepared/catalog.json').read_text(encoding='utf-8'))
    checks=[]
    for key in ['m101','barnard']:
        sequence=next(s for s in catalog if s['key']==key)
        for survey in ['gaia','wise']:
            response=requests.get(base+f'/v1/surveys/{survey}',params={'sequence_id':sequence['id']},timeout=100)
            response.raise_for_status();layer=response.json()
            if not layer['sources']:raise AssertionError('Expected real catalog context')
            sources=sorted(layer['sources'],key=lambda s:-math.hypot(s.get('pmra') or 0,s.get('pmdec') or 0))
            errors=[]
            for source in sources[:20]:
                for i,frame in enumerate(sequence['frames']):
                    if source['pixels_by_frame'][i] is None:continue
                    ra,dec=source['ra'],source['dec']
                    if survey=='gaia' and all(source.get(k) is not None for k in ['pmra','pmdec','ref_epoch']):
                        with warnings.catch_warnings():
                            warnings.simplefilter('ignore')
                            reference=SkyCoord(ra=ra*u.deg,dec=dec*u.deg,
                                pm_ra_cosdec=source['pmra']*u.mas/u.yr,pm_dec=source['pmdec']*u.mas/u.yr,
                                obstime=Time(source['ref_epoch'],format='jyear',scale='tcb')).apply_space_motion(
                                    new_obstime=Time(frame['mjd_mid'],format='mjd',scale='utc'))
                        ra,dec=reference.ra.deg,reference.dec.deg
                    expected=tangent_pixel(ra,dec,frame.get('grid',sequence['grid']))
                    errors.append(float(np.max(np.abs(expected-source['pixels_by_frame'][i]))))
            maximum=max(errors)
            # Predeclared tolerance: 1e-4 displayed pixels for the stated angular model.
            if maximum>=1e-4:raise AssertionError(f'{key}/{survey} projection disagreement {maximum}')
            check={'field':key,'survey':survey,'sources':len(layer['sources']),
                   'maximum_reference_error_pixels':maximum,'tolerance_pixels':1e-4,
                   'search_completeness':layer['search_completeness'],'query_urls':layer['query_urls'],
                   'highest_motion_source':sources[0]['id'],
                   'highest_total_motion_mas_yr':math.hypot(sources[0].get('pmra') or 0,sources[0].get('pmdec') or 0)}
            checks.append(check);print(json.dumps(check),flush=True)
    result={'checked_utc':datetime.now(timezone.utc).isoformat(),'checks':checks,
            'interpretation':'Validates catalog coordinate transport and displayed TAN alignment, not measured source centroids or complete associations.',
            'limitations':['Observer parallax, perspective acceleration and binary motion are omitted.',
                           'WISE catalog positions are historical; band mean MJDs are approximate positional epochs.']}
    (ROOT/'artifacts/survey-scientific-validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--base-url',default='http://127.0.0.1:8000')
    validate(parser.parse_args().base_url)
