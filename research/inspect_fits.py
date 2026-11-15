"""Inspect authentic public products; no application implementation."""
from pathlib import Path
import json,time,sys,hashlib,requests,xml.etree.ElementTree as ET
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
from astropy.table import Table
import astropy.units as u
sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).parent; EV=ROOT/'evidence'; FIX=ROOT/'fixtures'
def read_table(path): return Table.read(path,format='votable',use_names_over_ids=True)
def download(name,url,params=None):
 if (FIX/(name+'.fits')).exists(): return FIX/(name+'.fits')
 t=time.perf_counter()
 for attempt in range(3):
  r=requests.get(url,params=params,headers={'Origin':'https://vantage.example'},timeout=(15,120))
  if r.status_code not in (429,502,503,504): break
  (EV/(name+'_retry_'+str(attempt)+'.json')).write_text(json.dumps({'url':r.url,'status':r.status_code,'headers':dict(r.headers)},indent=2))
  time.sleep(0.5*(attempt+1))
 r.raise_for_status()
 p=FIX/(name+'.fits');p.write_bytes(r.content)
 m={'url':r.url,'status':r.status_code,'bytes':len(r.content),'seconds':round(time.perf_counter()-t,3),'headers':dict(r.headers),'sha256':hashlib.sha256(r.content).hexdigest()}
 (EV/(name+'_download.json')).write_text(json.dumps(m,indent=2)); print(name,m['bytes'],m['seconds'],flush=True)
 return p
def inspect(name,path,coord=None):
 with fits.open(path) as h:
  info=[]
  for hd in h:
   entry={'name':hd.name,'type':type(hd).__name__,'shape':list(hd.data.shape) if hd.data is not None else None,'dtype':str(hd.data.dtype) if hd.data is not None else None,'unit':hd.header.get('BUNIT'),'header':str(hd.header)}
   if isinstance(hd,fits.BinTableHDU):entry['columns']=[{'name':c.name,'format':c.format,'dim':c.dim,'unit':c.unit} for c in hd.columns]
   info.append(entry)
  hdr=h['IMAGE'].header; result={'hdus':info,'image_header':dict(hdr),'flags_header':dict(h['FLAGS'].header)}
  w=WCS(hdr); sw=WCS(hdr,fobj=h,key='W');sw.sip=None
  if coord is None:coord=(float(hdr['CRVAL1']),float(hdr['CRVAL2']))
  x,y=w.world_to_pixel(SkyCoord(*coord,unit='deg')); wave,bw=sw.pixel_to_world(x,y)
  result['coordinate_test']={'ra':coord[0],'dec':coord[1],'pixel_zero_xy':[float(x),float(y)],'parent_zero_xy':[float(1+x-hdr['CRPIX1A']),float(1+y-hdr['CRPIX2A'])],'wavelength_um':float(wave.to_value(u.um)),'bandwidth_um':float(bw.to_value(u.um)),'roundtrip_deg':list(w.pixel_to_world_values(x,y))}
  flags=h['FLAGS'].data.astype(np.uint32); result['flag_counts']={str(i):int(np.count_nonzero(flags&(1<<i))) for i in range(32) if np.any(flags&(1<<i))}
  result['image_stats']={'finite':int(np.isfinite(h['IMAGE'].data).sum()),'min':float(np.nanmin(h['IMAGE'].data)),'max':float(np.nanmax(h['IMAGE'].data)),'median':float(np.nanmedian(h['IMAGE'].data))}
 (EV/(name+'_fits.json')).write_text(json.dumps(result,indent=2,default=str));print(name,json.dumps(result['coordinate_test'],default=str),flush=True)
 return result
if __name__=='__main__':
 t=read_table(EV/'sia_m101_qr2.vot'); row=t[t['energy_bandpassname']=='SPHEREx-D2'][0]
 p=download('m101_qr2_cutout',str(row['access_url']),{'center':'210.80227,54.34895deg','size':'0.1deg'})
 inspect('m101_qr2_cutout',p,(210.80227,54.34895))
 ns={'s':'http://s3.amazonaws.com/doc/2006-03-01/'}; key=ET.parse(EV/'s3_qr3_object.vot').find('.//s:Contents/s:Key',ns).text
 url='https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/'+key
 r=requests.get(url,headers={'Range':'bytes=0-65535','Origin':'https://vantage.example'},timeout=60)
 (EV/'s3_qr3_range.json').write_text(json.dumps({'url':url,'status':r.status_code,'bytes':len(r.content),'headers':dict(r.headers)},indent=2))
 (EV/'s3_qr3_header.bin').write_bytes(r.content)
 if r.status_code!=206: raise RuntimeError('Range response not partial')
 with fits.open(url,use_fsspec=True,fsspec_kwargs={'block_size':2880,'cache_type':'bytes'}) as h:
  hdr=h['IMAGE'].header.copy(); ra,dec=float(hdr['CRVAL1']),float(hdr['CRVAL2'])
 p=download('qr3_cutout','https://irsa.ipac.caltech.edu/ibe/data/spherex/'+key,{'center':f'{ra},{dec}deg','size':'0.1deg'})
 inspect('qr3_cutout',p,(ra,dec))
