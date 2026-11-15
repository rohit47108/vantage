from pathlib import Path
import re,json,hashlib,csv
import numpy as np
from astropy.io import fits
from astropy.time import Time
from astropy.coordinates import SkyCoord
from scipy.ndimage import map_coordinates
root=Path('.');doc=(root/'VANTAGE_RESEARCH_DOSSIER.md').read_text(encoding='utf-8');hand=(root/'CODEX_HANDOFF_PACKET.md').read_text(encoding='utf-8');audit=(root/'RESEARCH_COMPLETION_AUDIT.md').read_text(encoding='utf-8');manifest=json.loads((root/'demo_dataset_manifest.json').read_text());checks=[]
def check(name,value,detail=''):
 checks.append({'check':name,'passed':bool(value),'detail':detail})
check('A-Z ordered',re.findall(r'^## ([A-Z])\. ',doc,re.M)==list('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
refs=dict(re.findall(r'^\[(s\d+)\]: (\S+)$',doc,re.M));used=set(re.findall(r'\]\[(s\d+)\]',doc));check('all reference definitions resolve',not used-set(refs),str(sorted(used-set(refs))))
linkaudit=json.loads((root/'research/evidence/dossier_source_link_audit.json').read_text());check('75 unique checked source pointers',len({x['id'] for x in linkaudit})==75);check('source pointers HTTP200',all(x.get('status')==200 for x in linkaudit),'Underlying optional Gaia credit child returned 451 and is disclosed.')
november=json.loads((root/'research/evidence/full_challenge_source_audit.json').read_text())
check('November source audit covers all added references',set(refs)-{x['id'] for x in linkaudit}<={x['id'] for x in november})
check('November source audit URLs match final index',all(refs[x['id']]==x['url'] for x in november))
check('November source access results disclosed',all(x.get('status')==200 or x.get('separate_inspection') for x in november))
check('separate handoff matches final Z',hand==doc.split('## Z. CODEX HANDOFF PACKET\n\n',1)[1])
required=['Product Definition','Core User Journey','Final Feature Set','Chosen Stack','System Architecture','External Services','Dataset Strategy','Data Pipeline','Algorithms','Data Structures','Internal API Contracts','UI Screens','Interaction Requirements','Demo Dataset Manifest','Edge Cases','Scientific Guardrails','Performance Targets','Accessibility Requirements','Testing Requirements','Build Sequence','Acceptance Criteria','Source Index'];check('22 requested handoff subsections',all('### '+x in hand for x in required))
nums=[int(x) for x in re.findall(r'^\| (\d+) \|',audit,re.M)];check('65 requirement audit rows',nums==list(range(1,66)))
y=doc.split('### Direct answers to the 30 requested questions',1)[1].split('## Z.',1)[0];check('30 direct answers',len(re.findall(r'^\| \d+ \|',y,re.M))==30)
jsonblocks=re.findall(r'```json\n(.*?)\n```',doc,re.S)
for i,b in enumerate(jsonblocks):
 try:json.loads(b);ok=True
 except Exception as e:ok=False
 check('proposed JSON example '+str(i+1)+' valid',ok)
check('at least eight metadata target fixtures',len(manifest['targets'])>=8)
files={f['path']:f for f in manifest['files']}
check('28 unique listed FITS files',len(files)==len(manifest['files'])==28)
for f in manifest['files']:
 p=root/f['path'];check('file hash '+p.name,p.exists() and p.stat().st_size==f['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==f['sha256'])
 with fits.open(p) as h:
  if 'IMAGE' in h:
   shape=h['IMAGE'].data.shape;check('science shape consistency '+p.name,all(h[n].data.shape==shape for n in ['FLAGS','VARIANCE','ZODI']))
  else:check('calibration HDUs '+p.name,'CWAVE' in h or 'EPSF' in h)
benchmarks=manifest['full_challenge_benchmarks']
check('five named challenge benchmarks',set(benchmarks)=={'barnard','eps_indi_b','wise0855','rw_aur','r_dra'})
check('15 challenge frames and one new calibration',sum(f['role']=='full_challenge_frame' for f in files.values())==15 and
      sum(f['role']=='full_challenge_calibration' for f in files.values())==1)
associations=json.loads((root/'research/evidence/full_challenge_calibration_associations.json').read_text())
associations={(x['obs_id'],x['detector']):x for x in associations}
check('15 successful live calibration associations',len(associations)==15 and all(x['matches'] and x['status']==200 for x in associations.values()))
wise=benchmarks['wise0855']
coord=SkyCoord(wise['challenge_input']['ra'],wise['challenge_input']['dec'])
check('WISE challenge coordinates resolve to fixed manifest center',np.allclose([coord.ra.deg,coord.dec.deg],wise['center_deg'],atol=1e-8,rtol=0))
for target, benchmark in benchmarks.items():
 sequence=benchmark['sequence'];grid=benchmark['common_grid_audit']
 ids=[x['obs_id'] for x in sequence]
 check('three distinct chronological visits '+target,len(set(ids))==len(ids)==3 and np.all(np.diff([x['mjd_avg_fits_utc'] for x in sequence])>=1))
 check('common fixed WCS grid '+target,grid['grid_center_deg']==benchmark['center_deg'] and grid['grid_shape_yx']==[59,59] and
       grid['pixel_scale_arcsec']==6.15 and all(x['grid_wcs_roundtrip_max_px']<1e-4 for x in grid['frames']))
 check('common-grid support ordering '+target,0<=grid['joint_strict_flag_and_spectral_fraction_of_grid_before_psf_margin']<=
       grid['spectral_on_joint_finite_fraction_of_grid']<=grid['joint_finite_fraction']<=1)
 check('no full-field numerical authorization '+target,not benchmark['numerical_full_field_authorized'] and
       grid['joint_strict_flag_and_spectral_fraction_of_grid_before_psf_margin']<0.8)
 for release,q in benchmark['discovery'].items():
  check('archive snapshot '+target+' '+release,q['http_status']==200 and q['query_status']=='OK' and (root/q['votable']).is_file())
 for frame in sequence:
  info=files[frame['fixture']];h=fits.getheader(root/frame['fixture'],'IMAGE')
  check('frame FITS, manifest and visit identity '+frame['obs_id'],h['OBSID']==frame['obs_id']==info['obs_id'] and
        h['DETECTOR']==frame['detector']==info['detector'] and
        h['MJD-AVG']==frame['mjd_avg_fits_utc'] and abs((h['MJD-AVG']-frame['mjd_mid'])*86400)<0.1 and
        Time(h['MJD-AVG'],format='mjd',scale='utc').isot==frame['utc_avg_fits'])
  cal=frame['source_calibration'];link=associations[(frame['obs_id'],frame['detector'])];x,y=frame['target_xy']
  with fits.open(root/cal) as c:
   vals=[float(map_coordinates(c[n].data,[[y],[x]],order=1)[0]) for n in ['CWAVE','CBAND']]
   check('independent scalar calibration sample '+frame['obs_id'],c['CWAVE'].header['DETECTOR']==frame['detector'] and
         1<vals[0]<5.1 and 0<vals[1]<0.1 and np.allclose(vals,frame['target_lambda_width_um'],atol=4e-7,rtol=0) and
         link['expected_calibration_url']==files[cal]['retrieval']['url']==frame['source_calibration_url'] and (root/frame['data_link_evidence']).is_file())
check('DR1 kept outside verified collections',set(manifest['collections'])=={'spherex_qr2','spherex_qr3'} and
      manifest['dr1_access_checkpoint']['status']=='documentation_verified_data_access_unresolved')
check('native crop equivalence proof',json.loads((root/'research/evidence/native_crop_equivalence.json').read_text())['passed'])
check('M101 restricted field evidence',abs(manifest['m101_field_audit']['spectral_eligible_fraction']-694/3481)<1e-12)
check('spacecraft observer verified',all(x['observer']=='500@-163182' for x in manifest['spacecraft_ephemerides'].values()))
check('required acknowledgment text present',all(x in (root/'required_acknowledgments.txt').read_text() for x in ['This publication makes use of data products','This research has made use of the NASA/IPAC Infrared Science Archive','IRSA652','IRSA662']))
check('no application scaffold',(not (root/'package.json').exists()) and (not (root/'src').exists()) and (not (root/'app').exists()))
check('no unfinished prose markers',not re.search(r'\b(TODO|TBD|PLACEHOLDER)\b',doc))
result={'scope':'Research deliverable and artifact audit; not application validation','checked_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'word_count':len(doc.split()),'source_references':len(refs),'fixture_count':len(manifest['files']),'fixture_bytes':sum(f['bytes'] for f in manifest['files']),'checks':checks,'passed':all(x['passed'] for x in checks)}
(root/'research/evidence/final_deliverable_validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
# Rebuild evidence inventory after the final verification file.
rows=[]
for p in sorted((root/'research/evidence').iterdir()):
 if p.is_file():rows.append({'path':str(p).replace('\\','/'),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
with (root/'research/evidence_inventory.csv').open('w',encoding='utf-8',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);w.writeheader();w.writerows(rows)
print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2));print('checks',len(checks),'evidence_files',len(rows),'failures',[x for x in checks if not x['passed']]);assert result['passed']
