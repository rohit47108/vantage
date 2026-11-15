from probe_metadata import probe
from fetch_sources import fetch
from inspect_fits import read_table,EV
from concurrent.futures import ThreadPoolExecutor
from astropy.time import Time
import json,requests
sources={
'spectrophotometry_help':'https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html',
'judging_2025':'https://spaceapps-v2-staging.s3.amazonaws.com/media/documents/Final_Space_Apps_2025_Judging_Guidelines_for_web.pdf',
'astropy_remote':'https://docs.astropy.org/en/stable/io/fits/usage/cloud.html',
'reproject_algorithms':'https://reproject.readthedocs.io/en/stable/celestial.html',
'photutils_matching':'https://photutils.readthedocs.io/en/stable/user_guide/psf_matching.html',
'horizons_api':'https://ssd-api.jpl.nasa.gov/doc/horizons.html',
'jpl_policies':'https://ssd-api.jpl.nasa.gov/doc/index.php',
'wcag':'https://www.w3.org/TR/WCAG22/',
}
with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(fetch,sources.items()))
t=read_table(EV/'comet_3i_manifest.vot'); out=[]
for detector in sorted(set(t['spherex_detector'])):
 r=t[t['spherex_detector']==detector];print('Comet',detector,len(r),[(str(x['obs_id']),float(x['t_min']),float(x['comet_ra']),float(x['comet_dec'])) for x in r[:10]],flush=True)
probe('comet_datalink',str(t[0]['access_url']))
probe('most_ceres_id','https://irsa.ipac.caltech.edu/cgi-bin/MOST/nph-most',{'catalog':'spherex','input_type':'naifid_input','obj_naifid':'20000001','obs_begin':'2025 08 01','obs_end':'2025 08 10','output_mode':'VOTable'})
for path in EV.glob('sia_*_qr2.vot'):
 t=read_table(path);row=t[0];out.append({'name':path.stem,'rows':len(t),'mjd_min':float(min(t['t_min'])),'mjd_max':float(max(t['t_max'])),'date_min':Time(min(t['t_min']),format='mjd').isot,'date_max':Time(max(t['t_max']),format='mjd').isot,'first':{k:str(row[k]) for k in ['obs_id','access_url','energy_bandpassname','t_min','t_max','obs_collection']}})
(EV/'target_inventory.json').write_text(json.dumps(out,indent=2));print(json.dumps(out),flush=True)
u='https://irsa.ipac.caltech.edu/data/demos/notebooks/spherex/M101_irsa.fits';r=requests.head(u,timeout=30);print('MosaicHEAD',r.status_code,dict(r.headers),flush=True)
