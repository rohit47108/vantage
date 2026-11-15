import requests,json,concurrent.futures
from pathlib import Path
R=Path('research/evidence');repos=['astropy/astropy','astropy/pyvo','astropy/astroquery','astropy/reproject','astropy/photutils','cds-astro/aladin-lite','WorldWideTelescope/wwt-webgl-engine','ericmandel/js9','astrojs/fitsjs','plotly/plotly.js','d3/d3','caltech-ipac/irsa-tutorials','caltech-ipac/spherex-archive-documentation','tiangolo/fastapi','vitejs/vite','facebook/react']
def one(repo):
 out={'repo':repo,'access_date':'2026-10-12'}
 for suffix in ['', '/releases/latest','/license']:
  r=requests.get('https://api.github.com/repos/'+repo+suffix,timeout=30);d=r.json();out[suffix or 'repository']={k:d.get(k) for k in (['html_url','archived','pushed_at','default_branch','license'] if not suffix else ['tag_name','published_at','html_url'] if 'releases' in suffix else ['html_url','download_url','license'])};out[suffix or 'repository']['status']=r.status_code
 return out
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as p:out=list(p.map(one,repos))
(R/'library_repository_audit.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
