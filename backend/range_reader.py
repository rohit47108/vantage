"""Bounded, version-checked byte ranges for official SPHEREx HiPS cubes.

IBE currently omits ETag on HEAD and ignores If-Match, so every GET response
must supply the same strong ETag. Never treat a requested condition as proof
that the service enforced it. Astropy consumes this seekable file with section.
"""
import io
import re
import time
import hashlib
from collections import OrderedDict
import requests
from backend.hips import BASE


class VersionedCubeFile(io.RawIOBase):
    def __init__(self,index,transport=None,block_size=16384,max_bytes=8_000_000,check_cancel=lambda:None):
        super().__init__()
        if not isinstance(index,int) or isinstance(index,bool) or not 0<=index<12288:raise ValueError('Unsupported native HiPS tile index')
        if not 512<=block_size<=65536 or max_bytes<block_size:raise ValueError('Unsupported sparse range budget')
        self.name=f'{BASE}/Norder5/Dir{index//10000*10000}/Npix{index}_cube.fits'
        self.mode='rb';self._transport=transport or requests.Session();self._block_size=block_size;self._budget=max_bytes
        self._cache=OrderedDict();self._position=0;self._size=None;self._etag=None;self._cancel=check_cancel
        self._started=time.monotonic();self.transferred_bytes=0;self.ranges=[];self.source_info={}
        try:self._block(0)
        except Exception:self.close();raise

    def readable(self):return True
    def seekable(self):return True
    def tell(self):return self._position
    def seek(self,offset,whence=0):
        self._checkClosed()
        if whence not in [0,1,2]:raise ValueError('Unsupported seek origin')
        position=offset if whence==0 else self._position+offset if whence==1 else self._size+offset
        if not isinstance(position,int) or position<0:raise ValueError('Invalid native range position')
        self._position=position;return position

    def _block(self,start):
        self._cancel()
        if time.monotonic()-self._started>180:raise ValueError('Native trace exceeded its sampling time budget')
        if start in self._cache:
            self._cache.move_to_end(start);return self._cache[start]
        expected_end=start+self._block_size-1
        if self._size is not None:expected_end=min(expected_end,self._size-1)
        if len(self.ranges)>=400 or self.transferred_bytes+expected_end-start+1>self._budget:
            raise ValueError('Native trace exceeded its sparse range budget')
        headers={'Range':f'bytes={start}-{expected_end}','Accept-Encoding':'identity'}
        with self._transport.get(self.name,headers=headers,timeout=(8,20),stream=True,allow_redirects=False) as response:
            response.raise_for_status()
            if response.status_code!=206:raise ValueError('Native cube must honor HTTP 206 byte ranges')
            match=re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)',response.headers.get('Content-Range',''))
            if not match:raise ValueError('Native cube omitted an exact byte-range description')
            actual_start,actual_end,total=map(int,match.groups())
            if not 0<total<=400_000_000 or actual_start!=start or actual_end!=min(expected_end,total-1):
                raise ValueError('Native cube returned an unexpected byte range or object size')
            etag=response.headers.get('ETag')
            # RFC 9110 section 8.8.3: an unquoted/weak value cannot identify
            # the exact representation used by all byte ranges in this trace.
            if not etag or len(etag)>200 or not re.fullmatch(r'"[\x21\x23-\x7e\x80-\xff]*"',etag):
                raise ValueError('Native cube omitted a strong object version')
            if self._etag is not None and (etag!=self._etag or total!=self._size):raise ValueError('Native cube version changed during sparse sampling')
            if response.headers.get('Content-Encoding') not in [None,'identity']:raise ValueError('Compressed HTTP byte ranges are not supported')
            expected_size=actual_end-start+1
            if response.headers.get('Content-Length') and int(response.headers['Content-Length'])!=expected_size:
                raise ValueError('Native byte-range length differs from its description')
            chunks=[];size=0
            for chunk in response.iter_content(16384):
                self._cancel();size+=len(chunk)
                if size>expected_size:raise ValueError('Native byte-range response exceeded its bound')
                chunks.append(chunk)
            if size!=expected_size:raise ValueError('Native byte-range response ended early')
            data=b''.join(chunks);self._etag=etag;self._size=total
            self.source_info={'url':self.name,'etag':etag,'object_bytes':total,'last_modified':response.headers.get('Last-Modified')}
        self.transferred_bytes+=len(data);self.ranges.append({'start':start,'end_inclusive':actual_end,'sha256':hashlib.sha256(data).hexdigest()})
        if len(self._cache)>=64:self._cache.popitem(last=False)
        self._cache[start]=data;return data

    def read(self,size=-1):
        self._checkClosed()
        if size is None or size<0:raise ValueError('Unbounded native cube reads are not permitted')
        if size>2_000_000:raise ValueError('Native read exceeds the sparse sampling budget')
        size=min(size,max(0,self._size-self._position));chunks=[]
        while size:
            start=self._position//self._block_size*self._block_size;data=self._block(start);offset=self._position-start
            count=min(size,len(data)-offset);chunks.append(data[offset:offset+count]);self._position+=count;size-=count
        return b''.join(chunks)

    def readinto(self,buffer):
        data=self.read(len(buffer));buffer[:len(data)]=data;return len(data)

    def close(self):
        if hasattr(self,'_transport'):self._transport.close()
        if hasattr(self,'_cache'):self._cache.clear()
        super().close()
