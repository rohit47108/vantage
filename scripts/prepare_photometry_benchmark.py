"""Retain genuine P330E DR1 cutouts and their spectral calibration.

Target: STScI CALSPEC table, cross-checked with actual Gaia DR3 catalog record.
https://www.stsci.edu/hst/instrumentation/reference-data-for-calibration-and-tools/astronomical-catalogs/calspec.html
This calibration-star consistency check cannot independently verify SPHEREx's absolute gain.
"""
import json
import shutil
from pathlib import Path
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from backend.archive import discover,native_cutout,calibration
from backend.surveys import parse_catalog,propagate_gaia
from backend.science import ROOT,digest


def main():
    folder=ROOT/'research/updates/2026-11-15/photometry'
    source=parse_catalog((folder/'p330e_gaia.xml').read_bytes(),'gaia')[0]
    assert source['id']=='1312054926303736704'
    found=discover([source['ra'],source['dec']],2)
    rows=[r for r in found['observations'] if r['release']=='dr1' and r['detector']==2]
    selected=[rows[i] for i in np.linspace(0,len(rows)-1,4,dtype=int)]
    records=[];files=[]
    for i,row in enumerate(selected):
        center=list(propagate_gaia(source,row['mjd_mid'])[:2])
        path,mode=native_cutout(row,center,2.5)
        target=folder/f'p330e_d2_{i}.fits';shutil.copyfile(path,target)
        cal_url,cal_path=calibration(row)
        retained=folder/'spectral_wcs_d2.fits'
        if not retained.is_file():shutil.copyfile(cal_path,retained)
        with fits.open(target,memmap=False) as h:
            x,y=WCS(h['IMAGE'].header).world_to_pixel_values(*center)
            summary={'shape':list(h['IMAGE'].data.shape),'position_pixel':[float(x),float(y)],
                     'processing_version':h[0].header['VERSION']}
        record={**row,**summary,'position_deg':center,'path':str(target.relative_to(ROOT)).replace('\\','/'),
                'sha256':digest(target),'retrieval_mode':mode,'cutout_fov_arcmin':2.5,
                'calibration_url':cal_url,'calibration_path':str(retained.relative_to(ROOT)).replace('\\','/'),
                'calibration_sha256':digest(retained)}
        records.append(record);print(json.dumps(record),flush=True)
        files.append({'path':record['path'],'sha256':record['sha256'],'url':row['ibe'],'bytes':target.stat().st_size})
    files.append({'path':record['calibration_path'],'sha256':record['calibration_sha256'],'url':cal_url,'bytes':retained.stat().st_size})
    manifest={'source':source,'source_position_model':'Gaia angular proper motion; observer parallax and perspective acceleration omitted. P330E catalog parallax is 2.2149 mas.',
              'purpose':'Real native photometry benchmark; partial D2 sampling, not a complete 102-channel spectrum.',
              'discovery_completeness':found['search_completeness'],'observations':records,'files':files}
    (folder/'benchmark.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')

if __name__=='__main__':main()
