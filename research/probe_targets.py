from probe_metadata import probe,ROOT
from fetch_sources import fetch
from concurrent.futures import ThreadPoolExecutor
import requests,json,xml.etree.ElementTree as ET
targets={'barnard':'Barnard star','luhman16':'WISE J104915.57-531906.1','mira':'Mira','ngc1333':'NGC 1333','ngc6543':'NGC 6543'}
coords={}
for key,name in targets.items():
 m=probe('sesame_'+key,'https://cds.unistra.fr/cgi-bin/nph-sesame/-oxp/SNV?'+requests.utils.quote(name,safe=''))
 try:
  p=ROOT/('sesame_'+key+'.vot'); root=ET.parse(p)
  coords[key]=[float(root.find('.//jradeg').text),float(root.find('.//jdedeg').text)]
 except Exception as e: print('resolve',key,str(e))
coords.update({'cygnus':[304.693508808,42.4436872991],'cosmos_sdt':[150.7817877,3.3502204],'ngc3256':[156.96263,-43.90506]})
(ROOT/'target_coordinates.json').write_text(json.dumps(coords,indent=2))
def run(item):
 name,c=item
 return probe('sia_'+name+'_qr2','https://irsa.ipac.caltech.edu/SIA',{'COLLECTION':'spherex_qr2','POS':f'CIRCLE {c[0]} {c[1]} 0.01','MAXREC':'3000'})
with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(run,coords.items()))
