from probe_metadata import probe,ROOT
from fetch_sources import fetch
from concurrent.futures import ThreadPoolExecutor
import requests,xml.etree.ElementTree as ET,json
sources={
 'spectrophotometry_help':'https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/spectrophotometry.html',
 'spaceapps_resources':'https://www.spaceappschallenge.org/resources/',
 'spaceapps_faq':'https://www.spaceappschallenge.org/resources/participant-faqs/',
 'mapmaking_paper':'https://arxiv.org/html/2603.25790v1',
 'mission_paper':'https://arxiv.org/html/2511.02985v1',
 'pipeline_paper':'https://arxiv.org/html/2511.15823v1',
 'anomalies':'https://spherex.caltech.edu/page/anomalyimages',
}
with ThreadPoolExecutor(max_workers=3) as pool: list(pool.map(fetch,sources.items()))
probe('most_ceres','https://irsa.ipac.caltech.edu/cgi-bin/MOST/nph-most',{'catalog':'spherex','input_type':'name_input','obj_name':'Ceres','obs_begin':'2025 08 01','obs_end':'2025 08 10','output_mode':'VOTable'})
# Discover one current QR3 product via public ListObjectsV2, never guessed keys.
prefix='qr3/level2/'
for depth in range(3):
 m=probe('s3_qr3_depth'+str(depth),'https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/',{'list-type':'2','delimiter':'/','prefix':prefix,'max-keys':'3'})
 root=ET.parse(ROOT/('s3_qr3_depth'+str(depth)+'.vot')); ns={'s':'http://s3.amazonaws.com/doc/2006-03-01/'}
 prefixes=root.findall('.//s:CommonPrefixes/s:Prefix',ns)
 if prefixes:prefix=prefixes[0].text
 else:break
probe('s3_qr3_object','https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/',{'list-type':'2','prefix':prefix,'max-keys':'1'})
