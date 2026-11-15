"""Stage the built static site with a backend proxy for the public demonstration."""
import argparse
import json
import shutil
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]


def stage(backend_url):
    parsed=urlparse(backend_url)
    if parsed.scheme!='https' or not parsed.netloc or parsed.path not in ('','/'):
        raise ValueError('Backend must be an HTTPS origin')
    destination=ROOT/'.runtime/deploy'
    shutil.copytree(ROOT/'dist',destination,dirs_exist_ok=True)
    backend_url=backend_url.rstrip('/')
    config={
        'version':2,
        'routes':[
            {'src':'/(.*)','headers':{'X-Content-Type-Options':'nosniff','Referrer-Policy':'strict-origin-when-cross-origin'},'continue':True},
            {'src':'/v1/(.*)','dest':backend_url+'/v1/$1'},
            {'handle':'filesystem'},
            {'src':'/prepared/(.*)','dest':backend_url+'/prepared/$1'},
            {'src':'/(.*)','dest':'/index.html'},
        ],
    }
    (destination/'vercel.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    print(destination)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--backend-url',required=True)
    stage(parser.parse_args().backend_url)
