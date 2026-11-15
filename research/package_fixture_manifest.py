from inspect_fits import *
from reproject import reproject_interp
from astropy.coordinates import SkyCoord
from astropy.time import Time
from astropy.stats import sigma_clipped_stats
import matplotlib.pyplot as plt
__import__('astropy.logger').log.setLevel('ERROR')
r=json.loads((EV/'motion_fixture_screening.json').read_text());c=[x for x in r if x['fixture'].startswith('ceres')];center=SkyCoord([x['ra_deg'] for x in c],[x['dec_deg'] for x in c],unit='deg').cartesian.mean();center=SkyCoord(center,representation_type='cartesian').icrs;center.representation_type='spherical';w=WCS(naxis=2);w.wcs.crpix=[30,30];w.wcs.crval=[center.ra.deg,center.dec.deg];w.wcs.cdelt=[-6.15/3600,6.15/3600];w.wcs.ctype=['RA---TAN','DEC--TAN'];arrays=[];footprints=[]
for x in c:
 with fits.open(FIX/x['fixture']) as h:a,f=reproject_interp((h['IMAGE'].data,WCS(h['IMAGE'].header)),w,shape_out=(59,59));arrays.append(a);footprints.append(f)
fig,axs=plt.subplots(1,2,figsize=(10,5));lo,hi=np.nanpercentile(np.concatenate(arrays),[10,99.5])
for ax,a,x in zip(axs,arrays,c):
 ax.imshow(np.arcsinh(np.clip((a-lo)/(hi-lo),0,None)/.05),origin='lower',cmap='gray',vmin=0,vmax=np.arcsinh(20));sky=SkyCoord(x['ra_deg'],x['dec_deg'],unit='deg');px,py=w.world_to_pixel(sky);ax.plot(px,py,'ro',fillstyle='none');ax.set_title(Time(x['mjd'],format='mjd').isot+' UTC\n'+str(round(x['wave_um'],4))+' um');ax.set_xlabel('Common sky grid, x pixels')
measured=SkyCoord(c[0]['centroid_ra_deg'],c[0]['centroid_dec_deg'],unit='deg').separation(SkyCoord(c[1]['centroid_ra_deg'],c[1]['centroid_dec_deg'],unit='deg')).arcsec
fig.suptitle('Ceres: same celestial grid, positional motion only\nDifferent wavelength samples: brightness-change calculation prohibited');fig.tight_layout();fig.savefig(EV/'ceres_motion_research.png',dpi=160);plt.close(fig)
(EV/'ceres_motion_measured.json').write_text(json.dumps({'predicted_displacement_arcsec':142.95778591164955,'screening_centroid_displacement_arcsec':float(measured),'duration_hours':abs(c[1]['mjd']-c[0]['mjd'])*24,'caveat':'Screening centroids, not PSF-fit astrometry; differing passbands and flags disallow a photometric-change claim.'},indent=2))
# Portable dataset manifest: raw sources + derivatives are identified separately.
inv=json.loads((EV/'target_inventory.json').read_text());coords=json.loads((EV/'target_coordinates.json').read_text());targets=[]
for x in inv:
 key=x['name'].replace('sia_','').replace('_qr2','');targets.append(x|{'coordinate_deg':coords.get(key,[210.80227,54.34895] if key=='m101' else None),'verification':'metadata_coverage_only; no asserted source detection'})
files=[]
for p in FIX.glob('*.fits'):
 meta=EV/(p.stem+'_download.json');d=json.loads(meta.read_text()) if meta.exists() else {};files.append({'path':'research/fixtures/'+p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'retrieval':d,'verified_structure':str((EV/(p.stem+'_fits.json')).relative_to(ROOT.parent)) if (EV/(p.stem+'_fits.json')).exists() else None})
manifest={'schema_version':'1.0.0','project':'Vantage','research_only':True,'initial_tests_utc':'2026-10-04','refreshed_utc':'2026-10-19','collections':['spherex_qr2','spherex_qr3'],'release_doi':{'spherex_qr2':'10.26131/IRSA652','spherex_qr3':'10.26131/IRSA662'},'targets':targets,'files':files,'m101_pair':json.loads((EV/'m101_precision_pairs.json').read_text())[0],'m101_field_audit':json.loads((EV/'m101_pair_coverage_audit.json').read_text()),'motion_fixtures':r,'ceres_motion':json.loads((EV/'ceres_motion_measured.json').read_text()),'scientific_status':'No validated PSF-matched difference significance or automated discovery claim is included. Metadata matches and screening detections retain their explicit evidence level.'}
manifest['spacecraft_ephemerides']=json.loads((EV/'spacecraft_ephemeris_summary.json').read_text())
(ROOT.parent/'demo_dataset_manifest.json').write_text(json.dumps(manifest,indent=2,default=str),encoding='utf-8');print('manifest files',len(files),'targets',len(targets),'Ceres motion',measured,flush=True)
