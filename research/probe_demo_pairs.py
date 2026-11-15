from inspect_fits import *
from probe_metadata import probe
from astropy.io.votable import parse
from concurrent.futures import ThreadPoolExecutor
from astropy.time import Time
import io,warnings
__import__('astropy.logger').log.setLevel('ERROR')
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
# Verified M101 pair; download native cutouts around one common celestial coordinate.
scan=json.loads((EV/'m101_d2_precision_scan.json').read_text());pairs=json.loads((EV/'m101_precision_pairs.json').read_text());best=pairs[0]
for label,key in [('m101_epoch_a',best['a']),('m101_epoch_b',best['b'])]:
 row=next(x for x in scan if x['obs_id']==key)
 try:p=download(label,row['url'],{'center':'210.80227,54.34895deg','size':'0.1deg'})
 except requests.HTTPError:p=remote_native_crop(label,row,210.80227,54.34895)
 inspect(label,p,(210.80227,54.34895))
# Fetch all D3 comet URLs by actual observation IDs in one release-scoped TAP query.
ct=read_table(EV/'comet_3i_manifest.vot');cr=ct[ct['spherex_detector']=='D3'];ids=','.join("'"+str(x)+"'" for x in cr['obs_id']);q="SELECT o.observationid,p.productid,'https://irsa.ipac.caltech.edu/' || a.uri AS url FROM spherex.observation o JOIN spherex.plane p ON o.obsid=p.obsid JOIN spherex.artifact a ON a.planeid=p.planeid WHERE o.collection='spherex_qr2' AND p.productid='D3' AND o.observationid IN ("+ids+")";probe('tap_comet_urls','https://irsa.ipac.caltech.edu/TAP/sync',{'QUERY':q,'LANG':'ADQL','FORMAT':'CSV','MAXREC':100})
urls=Table.read(EV/'tap_comet_urls.txt',format='ascii.csv');urlmap={str(r['observationid']):str(r['url']) for r in urls}
with fits.open(FIX/'spectral_wcs_d3.fits') as h:wave,bw=h['CWAVE'].data.copy(),h['CBAND'].data.copy()
def header(r):
 url=urlmap[str(r['obs_id'])];key=url.split('/ibe/data/spherex/')[1];s3='https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/'+key;resp=requests.get(s3,headers={'Range':'bytes=0-65535'},timeout=60);resp.raise_for_status();b=io.BytesIO(resp.content);fits.Header.fromfile(b);hdr=fits.Header.fromfile(b);ra,dec=float(r['comet_ra']),float(r['comet_dec']);x,y=WCS(hdr).world_to_pixel(SkyCoord(ra,dec,unit='deg'));ix,iy=int(round(float(x))),int(round(float(y)));return {'obs_id':str(r['obs_id']),'url':url,'mjd':float((r['t_min']+r['t_max'])/2),'ra_deg':ra,'dec_deg':dec,'xy':[float(x),float(y)],'wave_um':float(wave[iy,ix]),'bandwidth_um':float(bw[iy,ix]),'header':dict(hdr)}
with ThreadPoolExecutor(max_workers=4) as pool:out=list(pool.map(header,cr))
(EV/'comet_d3_precision_scan.json').write_text(json.dumps(out,indent=2,default=str));pairs=[]
for i,a in enumerate(out):
 for b in out[i+1:]:
  sep=SkyCoord(a['ra_deg'],a['dec_deg'],unit='deg').separation(SkyCoord(b['ra_deg'],b['dec_deg'],unit='deg')).arcsec
  mismatch=abs(a['wave_um']-b['wave_um'])/min(a['bandwidth_um'],b['bandwidth_um']);pairs.append({'a':a['obs_id'],'b':b['obs_id'],'mismatch_bandwidths':mismatch,'separation_arcsec':float(sep),'dt_days':abs(a['mjd']-b['mjd'])})
pairs.sort(key=lambda p:(p['mismatch_bandwidths']>=0.1,p['separation_arcsec']>900,p['mismatch_bandwidths']));(EV/'comet_d3_precision_pairs.json').write_text(json.dumps(pairs[:30],indent=2));print('comet pairs',pairs[:6],flush=True)
