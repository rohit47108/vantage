from pathlib import Path
import re,json,requests,concurrent.futures,datetime
R=Path('.');p=R/'VANTAGE_RESEARCH_DOSSIER.md';s=p.read_text(encoding='utf-8');s=s.replace('**Research cutoff: 12 October 2026.** Initial archive tests were performed on 4 October; releases, schedules, repositories, and selected services were refreshed on 12 October.','**Research cutoff: 18 October 2026 America/New_York (19 October UTC).** Initial archive tests were performed on 4 October; additional file/API and software tests on 12 October; releases, schedules, selected repositories and motion fixtures were refreshed on 18 October evening / 19 October UTC.');p.write_text(s,encoding='utf-8')
# Required data acknowledgments, exact functional attribution text extracted from authoritative pages.
a=(R/'research/evidence/overview_final.txt').read_text(encoding='utf-8');ack=re.search(r'"(This publication makes use of data products.*?Administration\.)"',a,re.S).group(1)
b=(R/'research/evidence/irsa_ack.txt').read_text(encoding='utf-8');irsa=re.search(r'"(This research has made use of the.*?Technology\.)"',b,re.S).group(1);irsa=' '.join(irsa.split())
(R/'required_acknowledgments.txt').write_text('SPHEREx required acknowledgment\nSource: https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_qr.html\n\n'+ack+'\n\nIRSA acknowledgment\nSource: https://irsa.ipac.caltech.edu/ack.html\n\n'+irsa+'\n\nRelease DOIs:\nQR2: https://doi.org/10.26131/IRSA652\nQR3: https://doi.org/10.26131/IRSA662\n\nUse the acknowledgments and DOI(s) appropriate to the data actually used. Preserve source credits on any third-party/NASA publicity image.\n',encoding='utf-8')
# Structural and link audit; payload retained for review.
refs=dict(re.findall(r'^\[(s\d+)\]: (\S+)$',s,re.M));used=set(re.findall(r'\]\[(s\d+)\]',s));heads=re.findall(r'^## ([A-Z])\. ',s,re.M);assert heads==list('ABCDEFGHIJKLMNOPQRSTUVWXYZ'),heads;assert not used-set(refs),used-set(refs)
def check(x):
 k,u=x;t=__import__('time').perf_counter()
 try:
  r=requests.get(u,timeout=(6,20),stream=True,headers={'User-Agent':'Vantage research source verification'});out={'id':k,'url':u,'status':r.status_code,'final_url':r.url,'content_type':r.headers.get('Content-Type'),'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'seconds':round(__import__('time').perf_counter()-t,3)};r.close();return out
 except Exception as e:return {'id':k,'url':u,'error':str(e),'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:out=list(ex.map(check,refs.items()))
(R/'research/evidence/dossier_source_link_audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('word count',len(s.split()),'refs',len(refs),'A-Z',len(heads));print(json.dumps([x for x in out if x.get('status')!=200],indent=2))
