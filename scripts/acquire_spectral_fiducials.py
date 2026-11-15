"""Verify retained fiducials, or reproduce their bounded official acquisition.

Default is offline verification. --download requires the pinned official object
and prefix fingerprint; changed upstream data needs review before promotion.
"""
import argparse
import gzip
import hashlib
import io
import json
import re
import tarfile
from pathlib import Path
from datetime import datetime,timezone
import requests
from backend.science import ROOT

FOLDER=ROOT/'research/updates/2026-11-15/spectral-response'
URL='https://irsa.ipac.caltech.edu/data/SPHEREx/docs/spectral_files_20260812/SPHERExSpectralFiles_202607.tar'
ETAG='"1a079800-659fa773f9c47"'
PREFIX_BYTES=40_000_000
PREFIX_SHA256='2af25dcf8fef3461207336f4d7b3affbba00e9b00157664cf00b4437527c7a54'


def selected(name):
    if name=='ChannelMaps/spectral_channels_17ch_2040.fits':return True
    if re.fullmatch(r'FidSpecSummary/SubChannel17/Band([1-6])/FidSpecSummary_Band\1_SpecCh17\.csv',name):return True
    match=re.fullmatch(r'(MiddlePixel|MeanAllPixel)/SubChannel17/Band([1-6])/FiducialSpec_Band\2_SubCh(0[1-9]|1[0-7])_17_(Cent|Allpix)\.csv',name)
    return bool(match and (match[1]=='MiddlePixel')==(match[4]=='Cent'))


def verify():
    record=json.loads((FOLDER/'acquisition.json').read_text(encoding='utf-8'))
    if len(record['files'])!=211:raise ValueError('Need the geometric map, six summaries and 204 representative curves')
    for entry in record['files']:
        if not selected(entry['member']):raise ValueError('Unapproved spectral member')
        path=(ROOT/entry['path']).resolve()
        if not path.is_relative_to(FOLDER.resolve()) or path.stat().st_size>10_000_000:raise ValueError('Unexpected retained spectral path/size')
        encoded=path.read_bytes()
        if hashlib.sha256(encoded).hexdigest()!=entry['stored_sha256']:raise ValueError('Stored spectral checksum differs')
        if path.suffix=='.gz':
            with gzip.GzipFile(fileobj=io.BytesIO(encoded)) as stream:decoded=stream.read(10_000_001)
        else:decoded=encoded
        if len(decoded)!=entry['bytes'] or hashlib.sha256(decoded).hexdigest()!=entry['sha256']:raise ValueError('Original spectral checksum differs')
    return len(record['files'])


def acquire():
    head=requests.head(URL,timeout=(8,25),allow_redirects=False);head.raise_for_status()
    if head.headers.get('ETag')!=ETAG:raise ValueError('Official spectral object changed; inspect before promoting new data')
    response=requests.get(URL,headers={'Range':f'bytes=0-{PREFIX_BYTES-1}','If-Match':ETAG},timeout=(8,60),stream=True,allow_redirects=False)
    with response:
        response.raise_for_status()
        if response.status_code!=206 or response.headers.get('ETag')!=ETAG or not response.headers.get('Content-Range','').startswith(f'bytes 0-{PREFIX_BYTES-1}/'):
            raise ValueError('The archive did not honor the pinned bounded range')
        chunks=[];total=0
        for chunk in response.iter_content(65536):
            total+=len(chunk)
            if total>PREFIX_BYTES:raise ValueError('Spectral response exceeds the work bound')
            chunks.append(chunk)
    content=b''.join(chunks)
    if hashlib.sha256(content).hexdigest()!=PREFIX_SHA256:raise ValueError('Spectral prefix fingerprint changed')
    files=[];entries=[];FOLDER.mkdir(parents=True,exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(content),mode='r:') as tar:
        for member in tar:
            if len(entries)>=5000:raise ValueError('Too many spectral archive entries')
            entries.append({'name':member.name,'size':member.size,'offset_data':member.offset_data})
            if member.name.startswith('ParameterFiles/') and member.isfile():break
            if not member.isfile() or not selected(member.name):continue
            if member.offset_data+member.size>len(content) or member.size>10_000_000:raise ValueError('Selected spectral member exceeds the retained prefix')
            data=tar.extractfile(member).read();isfits=member.name.endswith('.fits')
            stored=gzip.compress(data,mtime=0) if isfits else data
            path=FOLDER/(member.name.replace('/','__')+('.gz' if isfits else ''));path.write_bytes(stored)
            files.append({'member':member.name,'offset_data':member.offset_data,'bytes':member.size,'sha256':hashlib.sha256(data).hexdigest(),
                'path':path.relative_to(ROOT).as_posix(),'stored_bytes':len(stored),'stored_sha256':hashlib.sha256(stored).hexdigest()})
    record={'retrieved_utc':datetime.now(timezone.utc).isoformat(),'url':URL,'etag':ETAG,'last_modified':head.headers.get('Last-Modified'),
        'full_object_bytes':int(head.headers['Content-Length']),'downloaded_range':[0,len(content)-1],'downloaded_bytes':len(content),
        'range_sha256':PREFIX_SHA256,'files':files,'inspected_entries':entries,
        'scope':'Exact members from a pinned HTTP 206 range, not the whole archive. No tar paths were extracted to the filesystem.'}
    (FOLDER/'acquisition.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    return verify()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--download',action='store_true');args=parser.parse_args()
    print(json.dumps({'verified_members':acquire() if args.download else verify()}))
