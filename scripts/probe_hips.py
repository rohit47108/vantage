"""Retain small live evidence without downloading the 321 MB visualization cube."""
import json
from datetime import datetime, timezone
from pathlib import Path
import requests
from astropy.io import fits
from astropy.wcs import WCS

BASE='https://irsa.ipac.caltech.edu/data/hips/SPHEREx/spherex_allsky_cube'
URL='https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/hips5_cube/hips_20261026/Norder5/Dir0/Npix445_cube.fits'

def main():
    dest=Path('research/updates/2026-11-14')
    dest.mkdir(parents=True,exist_ok=True)
    r=requests.get(BASE+'/properties',timeout=30)
    r.raise_for_status()
    (dest/'hips-properties.txt').write_text(r.text,encoding='utf-8')
    result={'checked_utc':datetime.now(timezone.utc).isoformat(),'properties_url':r.url,
            'properties_headers':dict(r.headers),'fits_url':URL}
    r=requests.get(URL,headers={'Range':'bytes=0-2879'},timeout=30)
    r.raise_for_status()
    result['range_status']=r.status_code
    result['range_headers']=dict(r.headers)
    with fits.open(URL,use_fsspec=True,fsspec_kwargs={'block_size':65536},memmap=False) as hdus:
        result['hdus']=[{'name':h.name,'shape':list(h.shape) if hasattr(h,'shape') else None} for h in hdus]
        result['primary']=dict(hdus[0].header)
        result['image_header']=dict(hdus['IMAGE'].header)
        tab=hdus['SPECTRAL_CHANNELS'].data
        result['channels']=[{n:float(row[n]) for n in tab.names} for row in tab]
        w=WCS(hdus['IMAGE'].header,fobj=hdus).celestial
        x,y=w.world_to_pixel_values(60.8109955,51.3404038)
        result['reference_pixel']=[float(x),float(y)]
        for n in ['IMAGE','NHITS','FLAGS']:
            values=hdus[n].section[:,int(round(float(y))),int(round(float(x)))]
            result[n+'_reference']=[float(v) if float('-inf')<float(v)<float('inf') else None for v in values]
    (dest/'hips-live-probe.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'hdus':result['hdus'],'pixel':result['reference_pixel'],'channel_first':result['channels'][0],'range_status':result['range_status']}))

if __name__=='__main__':main()
