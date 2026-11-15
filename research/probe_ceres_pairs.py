from inspect_fits import *
from concurrent.futures import ThreadPoolExecutor
from scipy.ndimage import map_coordinates
from astropy.time import Time
import io
__import__('astropy.logger').log.setLevel('ERROR')
r=json.loads((EV/'ceres_matches.json').read_text());rows=[x for x in r if x['productid']=='D2']
with fits.open(FIX/'spectral_wcs_d2.fits') as h:wave,bw=h['CWAVE'].data.copy(),h['CBAND'].data.copy()
def scan(r):
 url='https://irsa.ipac.caltech.edu/'+r['uri'];s3='https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/'+r['uri'].split('ibe/data/spherex/')[1];resp=requests.get(s3,headers={'Range':'bytes=0-65535'},timeout=60);resp.raise_for_status();b=io.BytesIO(resp.content);fits.Header.fromfile(b);hdr=fits.Header.fromfile(b);ra,dec=float(r['ra_obj']),float(r['dec_obj']);x,y=WCS(hdr).world_to_pixel(SkyCoord(ra,dec,unit='deg'));ix,iy=int(round(float(x))),int(round(float(y)))
 return {'obs_id':r['observationid'],'url':url,'mjd':(float(r['mjd_start'])+float(r['mjd_end']))/2,'ra_deg':ra,'dec_deg':dec,'xy':[float(x),float(y)],'wave_um':float(map_coordinates(wave,[[float(y)],[float(x)]],order=1,mode='constant',cval=np.nan)[0]),'bandwidth_um':float(map_coordinates(bw,[[float(y)],[float(x)]],order=1,mode='constant',cval=np.nan)[0]),'header':dict(hdr)}
with ThreadPoolExecutor(max_workers=4) as p:out=list(p.map(scan,rows))
(EV/'ceres_d2_precision_scan.json').write_text(json.dumps(out,indent=2,default=str));pairs=[]
for i,a in enumerate(out):
 for b in out[i+1:]:
  sep=SkyCoord(a['ra_deg'],a['dec_deg'],unit='deg').separation(SkyCoord(b['ra_deg'],b['dec_deg'],unit='deg')).arcsec;m=abs(a['wave_um']-b['wave_um'])/min(a['bandwidth_um'],b['bandwidth_um'])
  if 10<sep<1500:pairs.append({'a':a['obs_id'],'b':b['obs_id'],'mismatch_bandwidths':m,'separation_arcsec':float(sep),'dt_days':abs(a['mjd']-b['mjd'])})
pairs.sort(key=lambda p:(p['mismatch_bandwidths']>=0.1,p['separation_arcsec']>600,p['mismatch_bandwidths']));(EV/'ceres_d2_precision_pairs.json').write_text(json.dumps(pairs[:25],indent=2));print('Ceres pairs',pairs[:5],flush=True)
