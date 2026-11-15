from probe_metadata import probe
from fetch_sources import fetch
from concurrent.futures import ThreadPoolExecutor
tasks=[]
for name in ('plane','observation','artifact','obscore','provenance_input'):
 tasks.append((f'tap_{name}_schema','https://irsa.ipac.caltech.edu/TAP/sync',{'QUERY':f"SELECT column_name,datatype,unit,description FROM TAP_SCHEMA.columns WHERE table_name='spherex.{name}'",'FORMAT':'CSV'}))
with ThreadPoolExecutor(max_workers=2) as pool: list(pool.map(lambda t:probe(*t),tasks))
fetch(('spectral_calibration_document','https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHERExSpectralFiles_202607.pdf'))
