"""Research evidence capture only; this is not application code."""
from pathlib import Path
import sys, json, time, hashlib, concurrent.futures
import requests
from html.parser import HTMLParser
class TextParser(HTMLParser):
 def __init__(self): super().__init__(); self.parts=[]; self.links=[]; self.skip=0
 def handle_starttag(self,tag,attrs):
  if tag in ('script','style'): self.skip+=1
  if tag=='a':
   href=dict(attrs).get('href')
   if href: self.links.append(href)
 def handle_endtag(self,tag):
  if tag in ('script','style'): self.skip=max(0,self.skip-1)
 def handle_data(self,data):
  if not self.skip and data.strip(): self.parts.append(data.strip())
sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).parent / 'evidence'
SOURCES = {
 'access': 'https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/',
 'products': 'https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/',
 'calibrations': 'https://irsa.ipac.caltech.edu/data/SPHEREx/docs/spherex_spectral_calibrations.html',
 'cutout_api': 'https://irsa.ipac.caltech.edu/ibe/cutouts.html',
 'sia_api': 'https://irsa.ipac.caltech.edu/ibe/sia.html',
 'vo_api': 'https://irsa.ipac.caltech.edu/voapi.html',
 'cloud': 'https://irsa.ipac.caltech.edu/cloud_access/',
 'mosaic_tutorial': 'https://caltech-ipac.github.io/irsa-tutorials/spherex-mosaic/',
 'cutout_tutorial': 'https://caltech-ipac.github.io/irsa-tutorials/spherex-cutouts/',
 'psf_tutorial': 'https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/',
 'mosaic_help': 'https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/mosaic.html',
 'explorer_api': 'https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/api.html',
 'spaceapps': 'https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/',
 'intro_tutorial':'https://caltech-ipac.github.io/irsa-tutorials/spherex-intro/',
 'most_api':'https://irsa.ipac.caltech.edu/applications/MOST/MOSTProgramInterface.html',
 'sdt_tutorial':'https://caltech-ipac.github.io/irsa-tutorials/spherex-source-discovery-tool-demo/',
}
def fetch(item):
 name,url=item; t=time.perf_counter()
 try:
  r=requests.get(url,timeout=90); ext='.pdf' if 'pdf' in r.headers.get('Content-Type','') else '.html'
  (ROOT/(name+ext)).write_bytes(r.content)
  if ext=='.pdf' and r.ok:
   import fitz
   doc=fitz.open(stream=r.content,filetype='pdf')
   (ROOT/(name+'.txt')).write_text('\n'.join(f'\n--- PDF PAGE {i+1} ---\n'+p.get_text() for i,p in enumerate(doc)),encoding='utf-8')
  elif r.ok:
   parser=TextParser(); parser.feed(r.text)
   (ROOT/(name+'.txt')).write_text('\n'.join(parser.parts),encoding='utf-8')
   (ROOT/(name+'_links.json')).write_text(json.dumps([requests.compat.urljoin(r.url,a) for a in parser.links],indent=2),encoding='utf-8')
  out={'name':name,'url':url,'final_url':r.url,'status':r.status_code,'bytes':len(r.content),'seconds':round(time.perf_counter()-t,3),'sha256':hashlib.sha256(r.content).hexdigest(),'headers':dict(r.headers),'access_date':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).date().isoformat()}
 except Exception as e: out={'name':name,'url':url,'error':str(e),'access_date':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).date().isoformat()}
 print(json.dumps({k:v for k,v in out.items() if k!='headers'}),flush=True)
 return out
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(fetch,SOURCES.items()))
 (ROOT/'source_fetch_log.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
