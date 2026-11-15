from inspect_fits import *
from probe_metadata import probe
from fetch_sources import fetch
from concurrent.futures import ThreadPoolExecutor
from astropy.time import Time
from astropy.io.votable import parse
import importlib.metadata as md
sources={'mission_current':'https://irsa.ipac.caltech.edu/Missions/spherex.html','overview_current':'https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_qr.html','schedule_current':'https://spherex.caltech.edu/page/data-products','spaceapps_faq_current':'https://www.spaceappschallenge.org/resources/participant-faqs/','spaceapps_current':'https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/','api_tap':'https://irsa.ipac.caltech.edu/docs/program_interface/TAP.html','sesame':'https://cds.unistra.fr/cgi-bin/Sesame','simbad_tap_docs':'https://simbad.cds.unistra.fr/simbad/sim-tap','nasa_images_policy':'https://www.nasa.gov/nasa-brand-center/images-and-media/','irsa_ack':'https://irsa.ipac.caltech.edu/ack.html','pyvo_sia2':'https://pyvo.readthedocs.io/en/latest/api/pyvo.dal.SIA2Service.html','astroquery_irsa':'https://astroquery.readthedocs.io/en/latest/ipac/irsa/irsa.html'}
with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(fetch,sources.items()))
(EV/'source_refresh_20261012.json').write_text(json.dumps(results,indent=2))
probe('most_ceres_wide','https://irsa.ipac.caltech.edu/cgi-bin/MOST/nph-most',{'catalog':'spherex','input_type':'naifid_input','obj_naifid':'20000001','obs_begin':'2025 04 01','obs_end':'2026 08 01','output_mode':'VOTable'})
query="SELECT TOP 5 o.collection,o.observationid,p.energy_bandpassname,p.time_bounds_lower,p.time_bounds_upper,p.provenance_version,p.obs_publisher_did,'https://irsa.ipac.caltech.edu/' || a.uri AS access_url FROM spherex.observation o JOIN spherex.plane p ON o.obsid=p.obsid JOIN spherex.artifact a ON a.planeid=p.planeid WHERE 1=CONTAINS(POINT('ICRS',210.80227,54.34895),p.poly) AND p.energy_bandpassname='SPHEREx-D2' AND o.collection='spherex_qr2' ORDER BY p.time_bounds_lower"
probe('tap_m101_join','https://irsa.ipac.caltech.edu/TAP/sync',{'REQUEST':'doQuery','LANG':'ADQL','QUERY':query,'FORMAT':'CSV','MAXREC':'20'})
# Small remote slices establish the real mosaic layout without downloading all planes.
u='https://irsa.ipac.caltech.edu/data/demos/notebooks/spherex/M101_irsa.fits'
with fits.open(u,use_fsspec=True,fsspec_kwargs={'block_size':2880,'cache_type':'bytes'}) as h:
 info=[{'name':x.name,'type':type(x).__name__,'shape':getattr(x,'shape',None),'header':str(x.header),'columns':[{'name':c.name,'format':c.format,'unit':c.unit} for c in x.columns] if isinstance(x,fits.BinTableHDU) else None} for x in h]
 (EV/'m101_mosaic_hdus.json').write_text(json.dumps(info,indent=2,default=str)); print('mosaic',[(x['name'],x['shape']) for x in info],flush=True)
# Authentic comet headers and wavelength lookups: inspect eight D3 images remotely.
t=read_table(EV/'comet_3i_manifest.vot'); rows=t[t['spherex_detector']=='D3'][:10]; out=[]
for i,row in enumerate(rows):
 m=probe('comet_d3_link_'+str(i),str(row['access_url']));lt=read_table(EV/('comet_d3_link_'+str(i)+'.vot'));url=str(lt[lt['semantics']=='#this'][0]['access_url'])
 with fits.open(url,use_fsspec=True,fsspec_kwargs={'block_size':65536,'cache_type':'bytes'}) as h:
  hdr=h['IMAGE'].header;ra,dec=float(row['comet_ra']),float(row['comet_dec']); x,y=WCS(hdr).world_to_pixel(SkyCoord(ra,dec,unit='deg'));sp=WCS(hdr,fobj=h,key='W');sp.sip=None;wave,bw=sp.pixel_to_world(x,y)
  d={'obs_id':str(row['obs_id']),'url':url,'ra_deg':ra,'dec_deg':dec,'mjd_start':float(row['t_min']),'mjd_end':float(row['t_max']),'xy_zero':[float(x),float(y)],'wave_um':float(wave.to_value(u if False else __import__('astropy.units',fromlist=['um']).um)),'bandwidth_um':float(bw.to_value(__import__('astropy.units',fromlist=['um']).um)),'image_header':dict(hdr)}
  out.append(d);print('comet_header',{k:v for k,v in d.items() if k!='image_header'},flush=True)
 (EV/'comet_d3_header_scan.json').write_text(json.dumps(out,indent=2,default=str))
# Recommended precision calibration and ePSF, real DataLink references.
lt=read_table(EV/'comet_datalink.vot')
for r in lt:
 if r['semantics']=='#calibration' and 'spectral_wcs' in str(r['access_url']):
  p=download('spectral_wcs_d3',str(r['access_url']))
  with fits.open(p) as h:(EV/'spectral_wcs_d3_hdus.json').write_text(json.dumps([{'name':x.name,'shape':getattr(x,'shape',None),'unit':x.header.get('BUNIT'),'dtype':str(x.data.dtype) if x.data is not None else None} for x in h],indent=2))
