from inspect_fits import *
from probe_metadata import probe
from concurrent.futures import ThreadPoolExecutor
from astropy.io.votable import parse
from astropy.time import Time
import io,warnings
warnings.filterwarnings('ignore'); __import__('astropy.logger').log.setLevel('ERROR')
# Retrieve the specific D2 spectral calibration referenced by the archive.
t=read_table(EV/'sia_m101_qr2.vot');rid=str(t[t['energy_bandpassname']=='SPHEREx-D2'][0]['obs_publisher_did']);probe('m101_d2_datalink','https://irsa.ipac.caltech.edu/datalink/links/spherex',{'ID':rid});dl=read_table(EV/'m101_d2_datalink.vot')
urls={2:str(dl[[('spectral_wcs' in str(r['access_url'])) for r in dl]][0]['access_url'])}
dl3=read_table(EV/'comet_datalink.vot');urls[3]=str(dl3[[('spectral_wcs' in str(r['access_url'])) for r in dl3]][0]['access_url'])
cal={}
for det,url in urls.items():
 p=download('spectral_wcs_d'+str(det),url)
 with fits.open(p) as h:cal[det]=(h['CWAVE'].data.copy(),h['CBAND'].data.copy());print('calibration',det,[(x.name,getattr(x,'shape',None)) for x in h],flush=True)
# Range-only header sampling; science pixels remain untouched here.
def scan(d):
 cloud=json.loads(d['cloud_access'])['aws'];url='https://'+cloud['bucket_name']+'.s3.'+cloud['region']+'.amazonaws.com/'+cloud['key'];start=time.perf_counter();r=requests.get(url,headers={'Range':'bytes=0-65535'},timeout=60);r.raise_for_status()
 if r.status_code!=206:raise RuntimeError('Expected partial content')
 b=io.BytesIO(r.content);fits.Header.fromfile(b);hdr=fits.Header.fromfile(b);x,y=WCS(hdr).world_to_pixel(SkyCoord(d['ra_deg'],d['dec_deg'],unit='deg'));ix,iy=int(round(float(x))),int(round(float(y)));det=int(d['detector']);wave,bw=cal[det];inside=0<=ix<2040 and 0<=iy<2040
 return {k:v for k,v in d.items() if k!='cloud_access'}|{'pixel_xy':[float(x),float(y)],'inside':inside,'wave_um':float(wave[iy,ix]) if inside else None,'bandwidth_um':float(bw[iy,ix]) if inside else None,'header':dict(hdr),'range_bytes':len(r.content),'seconds':round(time.perf_counter()-start,3),'source_url':url}
rows=[]
for row in t[t['energy_bandpassname']=='SPHEREx-D2']:
 rows.append({'target':'m101','obs_id':str(row['obs_id']),'detector':2,'ra_deg':210.80227,'dec_deg':54.34895,'mjd':float((row['t_min']+row['t_max'])/2),'url':str(row['access_url']),'cloud_access':str(row['cloud_access'])})
with ThreadPoolExecutor(max_workers=4) as p:out=list(p.map(scan,rows))
(EV/'m101_d2_precision_scan.json').write_text(json.dumps(out,indent=2,default=str));print('M101 scanned',len(out),flush=True)
pairs=[]
for i,a in enumerate(out):
 for b in out[i+1:]:
  if a['inside'] and b['inside'] and abs(a['mjd']-b['mjd'])>150:
   mismatch=abs(a['wave_um']-b['wave_um'])/min(a['bandwidth_um'],b['bandwidth_um']);pairs.append({'mismatch_bandwidths':mismatch,'a':a['obs_id'],'b':b['obs_id'],'wave_a':a['wave_um'],'wave_b':b['wave_um'],'dt_days':abs(a['mjd']-b['mjd'])})
pairs.sort(key=lambda x:x['mismatch_bandwidths']);(EV/'m101_precision_pairs.json').write_text(json.dumps(pairs[:20],indent=2));print('bestM101',pairs[:3],flush=True)
# Ceres rows: authoritative final match table, not ephemeris samples.
v=parse(EV/'most_ceres_wide.vot');mt=next(v.iter_tables()).to_table(use_names_over_ids=True);(EV/'ceres_matches.json').write_text(json.dumps([{k:str(r[k]) for k in mt.colnames} for r in mt],indent=2));print('Ceres image matches',len(mt),[(str(r['observationid']),str(r['productid']),str(r['mjd_start']),str(r['ra_obj']),str(r['dec_obj']),str(r['uri'])) for r in mt[:6]],flush=True)
