"""Read-only public archive verification; retain raw evidence."""
from pathlib import Path
import sys,json,time,hashlib,concurrent.futures,xml.etree.ElementTree as ET
import requests
sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).parent/'evidence'
def probe(name,url,params=None,headers=None):
 t=time.perf_counter()
 try:
  r=requests.get(url,params=params,headers=headers or {'Origin':'https://vantage.example'},timeout=(15,120))
  ct=r.headers.get('Content-Type',''); ext='.json' if 'json' in ct else '.vot' if 'xml' in ct or r.content.lstrip().startswith(b'<?xml') else '.txt'
  (ROOT/(name+ext)).write_bytes(r.content)
  meta={'name':name,'url':r.url,'status':r.status_code,'bytes':len(r.content),'seconds':round(time.perf_counter()-t,3),'headers':dict(r.headers),'sha256':hashlib.sha256(r.content).hexdigest(),'access_date':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).date().isoformat()}
  try:
   root=ET.fromstring(r.content)
   meta['fields']=[x.attrib for x in root.iter() if x.tag.split('}')[-1]=='FIELD']
   rows=[[v.text for v in x] for x in root.iter() if x.tag.split('}')[-1]=='TR']
   meta['rows']=len(rows); meta['sample_rows']=rows[:2]
   meta['query_status']=[x.attrib|{'text':x.text} for x in root.iter() if x.tag.split('}')[-1]=='INFO']
  except ET.ParseError: pass
  (ROOT/(name+'_probe.json')).write_text(json.dumps(meta,indent=2),encoding='utf-8')
  print(json.dumps({k:v for k,v in meta.items() if k not in ['headers','fields','sample_rows']}),flush=True)
  return meta
 except Exception as e:
  out={'name':name,'url':url,'params':params,'error':str(e),'seconds':time.perf_counter()-t}; (ROOT/(name+'_probe.json')).write_text(json.dumps(out,indent=2)); print(json.dumps(out),flush=True); return out
if __name__=='__main__':
 tasks=[
  ('sia_m101_qr2','https://irsa.ipac.caltech.edu/SIA',{'COLLECTION':'spherex_qr2','POS':'CIRCLE 210.80227 54.34895 0.001','MAXREC':'2000'}),
  ('sia_m101_qr3','https://irsa.ipac.caltech.edu/SIA',{'COLLECTION':'spherex_qr3','POS':'CIRCLE 210.80227 54.34895 0.001','MAXREC':'2000'}),
  ('tap_spherex_tables','https://irsa.ipac.caltech.edu/TAP/sync',{'QUERY':"SELECT table_name, description FROM TAP_SCHEMA.tables WHERE table_name LIKE 'spherex%'",'FORMAT':'CSV'}),
  ('comet_3i_manifest','https://irsa.ipac.caltech.edu/data/SPHEREx/docs/comet3iatlas/obscore_3I_Atlas.vot',None),
  ('s3_root','https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/',{'list-type':'2','delimiter':'/','max-keys':'50'}),
 ]
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool: list(pool.map(lambda t:probe(*t),tasks))
