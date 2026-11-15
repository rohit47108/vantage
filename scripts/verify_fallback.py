"""Force an upstream IBE failure, then verify real S3 pixels against IBE.

This only simulates the IBE HTTP failure. Both scientific files are authentic.
"""
from pathlib import Path
from unittest.mock import patch
import json
import requests
import numpy as np
from backend.archive import discover, native_cutout, calibration
from backend.science import ROOT, grid, plane, write_json


def verify():
    center=[133.79512916666664,-7.245147222222222]
    result=discover(center,6)
    row=next(row for row in result['observations'] if row['obs_id']=='2025W19_1B_0116_1' and row['detector']==6)
    ibe,mode=native_cutout(row,center,6)
    assert mode=='native_ibe_cutout'
    url,cal=calibration(row)
    with patch('backend.archive.retrieve',side_effect=requests.HTTPError('Injected upstream HTTP 503')):
        cloud,cloud_mode=native_cutout(row,center,6)
    assert cloud_mode=='native_s3_section'
    wcs,size=grid(center,6)
    inputs=row|{'source_calibration':str(cal)}
    direct=plane(inputs|{'fixture':str(ibe)},wcs,size)
    fallback=plane(inputs|{'fixture':str(cloud)},wcs,size)
    valid=np.isfinite(direct[0])&np.isfinite(fallback[0])
    max_difference=float(np.max(np.abs(direct[0][valid]-fallback[0][valid])))
    flags_equal=bool(np.array_equal(direct[4][valid],fallback[4][valid]))
    wavelengths_equal=bool(np.allclose(direct[2],fallback[2],atol=1e-9,equal_nan=True))
    report={'obs_id':row['obs_id'],'detector':6,'ibe_url':row['ibe'],'cloud':row['cloud_access'],
            'scope':'Forced IBE 503 followed by actual anonymous S3 native range reads, compared on common TAN grid.',
            'finite_overlap_pixels':int(valid.sum()),'max_brightness_difference_MJy_sr':max_difference,
            'flags_equal':flags_equal,'wavelengths_equal':wavelengths_equal,
            'passed':max_difference<1e-6 and flags_equal and wavelengths_equal}
    write_json(ROOT/'artifacts/s3-fallback-verification.json',report)
    print(json.dumps(report,indent=2))
    assert report['passed']


if __name__=='__main__':
    verify()
