from pathlib import Path
import requests,json
from fetch_sources import fetch
from concurrent.futures import ThreadPoolExecutor
sources={'aladin_api':'https://cds-astro.github.io/aladin-lite/','aladin_docs':'https://aladin.cds.unistra.fr/AladinLite/doc/','wwt_docs':'https://docs.worldwidetelescope.org/webgl-reference/latest/','hips_standard':'https://www.ivoa.net/documents/HiPS/','esasky':'https://sky.esa.int/esasky/','zooniverse':'https://www.zooniverse.org/about','wiseview':'https://byw.tools/wiseview','react_docs':'https://react.dev/learn/build-a-react-app-from-scratch','vite_docs':'https://vite.dev/guide/','fastapi_tasks':'https://fastapi.tiangolo.com/tutorial/background-tasks/','d3_scale':'https://d3js.org/d3-scale','plotly_js':'https://plotly.com/javascript/','mdn_canvas':'https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API','mdn_cors':'https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS','gaia_api':'https://www.cosmos.esa.int/web/gaia-users/archive/programmatic-access','simbad_docs':'https://astroquery.readthedocs.io/en/latest/simbad/simbad.html','ned_api':'https://ned.ipac.caltech.edu/Documents/Guides/Interface/URLs','fornax':'https://fornax-docs.readthedocs.io/en/latest/'}
with ThreadPoolExecutor(max_workers=4) as pool:out=list(pool.map(fetch,sources.items()))
Path('research/evidence/software_source_log.json').write_text(json.dumps(out,indent=2))
