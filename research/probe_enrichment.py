from probe_metadata import probe
from pathlib import Path
import requests,json,concurrent.futures
EV=Path(__file__).parent/'evidence'
probe('simbad_barnard','https://simbad.cds.unistra.fr/simbad/sim-tap/sync',{'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','QUERY':"SELECT b.main_id,b.ra,b.dec,b.pmra,b.pmdec,b.plx_value,b.rvz_radvel FROM basic b JOIN ident i ON b.oid=i.oidref WHERE i.id='Barnard''s star'"})
probe('sesame_barnard','https://cds.unistra.fr/cgi-bin/nph-sesame/-oxp/SNV?Barnard%27s%20star',None)
probe('horizons_ceres','https://ssd.jpl.nasa.gov/api/horizons.api',{'format':'json','COMMAND':"'1;'",'EPHEM_TYPE':"'OBSERVER'",'CENTER':"'500@399'",'TLIST':"'60888.334105877'",'TLIST_TYPE':"'MJD'",'QUANTITIES':"'1,3,20'",'ANG_FORMAT':"'DEG'",'CSV_FORMAT':"'YES'",'TIME_DIGITS':"'FRACSEC'",'REF_SYSTEM':"'ICRF'"})
# Read the actual official notebook source and maintenance metadata.
u='https://api.github.com/repos/Caltech-IPAC/irsa-tutorials/git/trees/main?recursive=1';r=requests.get(u,timeout=30);d=r.json();(EV/'tutorial_tree.json').write_text(json.dumps(d,indent=2));files=[x['path'] for x in d.get('tree',[]) if 'spherex' in x['path'].lower() and x['type']=='blob'];print(files)
for p in files:
 if p.endswith(('.md','.ipynb','.py')):
  r=requests.get('https://raw.githubusercontent.com/Caltech-IPAC/irsa-tutorials/main/'+p,timeout=30)
  (EV/('repo_'+p.replace('/','_'))).write_bytes(r.content)
  print(p,r.status_code,len(r.content),flush=True)
