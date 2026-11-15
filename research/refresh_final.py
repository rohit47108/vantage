from fetch_sources import fetch
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
src={'mission_final':'https://irsa.ipac.caltech.edu/Missions/spherex.html','overview_final':'https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_qr.html','schedule_final':'https://spherex.caltech.edu/page/data-products','spaceapps_faq_final':'https://www.spaceappschallenge.org/resources/participant-faqs/','spaceapps_final':'https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/','fornax_final':'https://docs.fornax.sciencecloud.nasa.gov/','simbad_coordinates':'https://simbad.cds.unistra.fr/Pages/guide/ch15.htx'}
with ThreadPoolExecutor(max_workers=4) as p:out=list(p.map(fetch,src.items()))
Path('research/evidence/final_refresh.json').write_text(json.dumps(out,indent=2))
