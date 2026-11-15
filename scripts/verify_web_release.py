"""Compare a public preview with the exact local build, retaining evidence."""
import argparse
import hashlib
import json
import re
from datetime import datetime,timezone
from pathlib import Path
import requests


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview',required=True)
    parser.add_argument('--deployment-id',required=True)
    parser.add_argument('--source-commit',required=True)
    parser.add_argument('--backend-origin',required=True)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if not re.fullmatch(r'dpl_[A-Za-z0-9]+',args.deployment_id):raise ValueError('Invalid deployment identifier')
    if not re.fullmatch(r'[a-f0-9]{40}',args.source_commit):raise ValueError('Use the full source commit')
    base=args.preview.rstrip('/');session=requests.Session()
    local=Path('dist/index.html').read_bytes();response=session.get(base+'/',timeout=30);response.raise_for_status()
    tag=f'<script async data-explicit-opt-in="true" data-deployment-id="{args.deployment_id}" src="https://vercel.live/_next-live/feedback/feedback.js"></script>'.encode()
    remote=response.content
    if remote.count(tag)>1:raise ValueError('Unexpected duplicate preview-feedback script')
    removed=tag.decode() if tag in remote else None
    cleaned=remote.replace(tag,b'')
    newline=cleaned!=local and cleaned.endswith(b'\n') and cleaned[:-1]==local
    if newline:cleaned=cleaned[:-1]
    if cleaned!=local:raise ValueError('Public HTML differs beyond the exact inspected preview-feedback tag/newline')
    assets=[]
    for asset in sorted(set(re.findall(rb'(?:src|href)="(/(?:assets/[^"]+|favicon\.svg))"',local))):
        path=asset.decode();expected=(Path('dist')/path.lstrip('/')).read_bytes()
        result=session.get(base+path,timeout=30);result.raise_for_status()
        if result.content!=expected:raise ValueError('Public build asset differs: '+path)
        assets.append({'path':path,'bytes':len(expected),'sha256':hashlib.sha256(expected).hexdigest(),'verified_exact':True})
    if not any(x['path'].endswith('.js') for x in assets):raise ValueError('No JavaScript build asset was verified')
    health=session.get(base+'/v1/health',timeout=30);health.raise_for_status()
    output={'checked_utc':datetime.now(timezone.utc).isoformat(),'preview':base,'deployment_id':args.deployment_id,
        'source_commit':args.source_commit,'backend_origin':args.backend_origin,
        'hosting':'Temporary local backend and tunnel; not durable hosting.','assets':assets,
        'html':{'local_sha256':hashlib.sha256(local).hexdigest(),'public_sha256':hashlib.sha256(remote).hexdigest(),
            'removed_exact_tag':removed,'one_appended_newline_removed':newline,'exact_otherwise':True},'public_health':health.json()}
    args.output.write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'assets':len(assets),'exact_html':True,'public_health':health.status_code,'output':str(args.output)}))


if __name__=='__main__':main()
