from inspect_fits import *
def remote_native_crop(label,row,ra,dec):
 """Research fixture only: range-read native pixels if IBE is unavailable."""
 key=row['url'].split('/ibe/data/spherex/')[1];url='https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/'+key
 with fits.open(url,use_fsspec=True,fsspec_kwargs={'block_size':65536,'cache_type':'bytes'}) as h:
  x,y=WCS(h['IMAGE'].header).world_to_pixel(SkyCoord(ra,dec,unit='deg'));n=59;x0=max(0,int(round(float(x)))-29);y0=max(0,int(round(float(y)))-29);x1=min(2040,x0+n);y1=min(2040,y0+n)
  hdus=[h[0].copy()]
  for name in ['IMAGE','FLAGS','VARIANCE','ZODI']:
   hdr=h[name].header.copy()
   for k in list(hdr):
    if k.startswith('CRPIX1') and len(k)<=7:hdr[k]=hdr[k]-x0
    if k.startswith('CRPIX2') and len(k)<=7:hdr[k]=hdr[k]-y0
   hdus.append(fits.ImageHDU(data=h[name].section[y0:y1,x0:x1].copy(),header=hdr,name=name))
  for name in ['PSF','EPSF','WCS-WAVE']:
   if name in h:hdus.append(h[name].copy())
  p=FIX/(label+'.fits');fits.HDUList(hdus).writeto(p,overwrite=True)
  (EV/(label+'_download.json')).write_text(json.dumps({'url':url,'mode':'range_read_native_crop_research','parent_pixel_bounds_zero_halfopen':[x0,y0,x1,y1],'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'access_date':'2026-10-12'},indent=2))
 return p
