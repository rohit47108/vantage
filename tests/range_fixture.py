"""HTTP adapter over exact retained native cube byte ranges; never fills gaps."""
import json
import hashlib
import numpy as np
from backend.science import ROOT
from test_range_reader import Response


class CubeFixtureTransport:
    def __init__(self):
        folder=ROOT/'research/updates/2026-11-15/spectral-trace'
        self.record=json.loads((folder/'fixture.json').read_text(encoding='utf-8'))
        path=ROOT/self.record['path']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=self.record['sha256']:raise ValueError('Retained native ranges changed')
        with np.load(path,allow_pickle=False) as archive:self.blocks={int(key[2:]):archive[key].tobytes() for key in archive.files}
        for entry in self.record['ranges']:
            assert hashlib.sha256(self.blocks[entry['start']]).hexdigest()==entry['sha256']
        self.calls=[]
    def get(self,url,headers,**kwargs):
        assert url==self.record['source']['url']
        start,end=map(int,headers['Range'].removeprefix('bytes=').split('-'));data=self.blocks[start]
        assert len(data)==min(end+1,self.record['source']['object_bytes'])-start
        self.calls.append((start,end))
        return Response(data,start,start+len(data)-1,self.record['source']['object_bytes'],etag=self.record['source']['etag'])
    def close(self):pass
