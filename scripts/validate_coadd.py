"""Reproducible real-data geometry and conditional statistical-noise checks."""
import json
import time
from datetime import datetime,timezone
import numpy as np
from astropy.io import fits
from reproject import reproject_exact
from backend.science import ROOT,grid
from backend.coadds import build_coadd,native_plane
from backend.operators import weighted_mean

def main():
    sequence=next(s for s in json.loads((ROOT/'public/prepared/catalog.json').read_text()) if s['key']=='m101')
    start=time.perf_counter();p=build_coadd(sequence,[0,1],ROOT/'.runtime/products')
    out,_=grid(sequence['center_deg'],3,32)
    planes=[native_plane(f,out,(32,32)) for f in sequence['frames']]
    joint=np.array(p['mask']).ravel()==0
    for plane in planes:plane['valid']&=joint
    result=weighted_mean(planes)
    v=joint.astype(float)
    expected=float(v@result['covariance']@v)
    diagonal=float(result['covariance'].diagonal()[joint].sum())
    rng=np.random.default_rng(20261114);realizations=np.zeros(2000)
    for i,plane in enumerate(planes):
        estimator=(v*result['weights'][i])@plane['operator']
        variance=np.where(plane['native_good'],plane['native_variance'],0).ravel()
        realizations+=rng.normal(size=(2000,len(estimator)))@(estimator*np.sqrt(variance))
    empirical=float(np.var(realizations,ddof=1))
    source=planes[0]
    reference,footprint=reproject_exact((source['native_values'],source['native_wcs']),out,shape_out=(32,32))
    actual=(source['operator']@source['native_values'].ravel()).reshape(32,32)
    good=(footprint>.999)&np.isfinite(reference)
    scale=np.percentile(source['native_values'],99)-np.percentile(source['native_values'],1)
    error=float(np.max(np.abs(reference[good]-actual[good]))/scale)
    report={'checked_utc':datetime.now(timezone.utc).isoformat(),'product_id':p['id'],
            'benchmark':'Authentic M101 QR2 exposures; conditional narrowband response mixture, not precision photometry.',
            'sources':p['source_ids'],'retained_pixels':int(joint.sum()),'requested_pixels':len(joint),
            'spherical_reference_normalized_max_error':error,'predeclared_geometry_tolerance':.001,
            'full_covariance_region_variance':expected,'diagonal_only_region_variance':diagonal,
            'monte_carlo_region_variance':empirical,'monte_carlo_realizations':2000,
            'predeclared_monte_carlo_relative_tolerance':.1,
            'passed':error<.001 and abs(empirical/expected-1)<.1,
            'processing_seconds_including_validation':time.perf_counter()-start,
            'limitations':p['limitations']}
    (ROOT/'artifacts/coadd-scientific-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)

if __name__=='__main__':main()
