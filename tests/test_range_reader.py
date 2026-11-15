import unittest
import numpy as np
from io import BytesIO
from astropy.io import fits


class Response:
    def __init__(self,data,start,end,total,etag='"fixed-object"',status=206):
        self.status_code=status
        self.headers={'Content-Range':f'bytes {start}-{end}/{total}','Content-Length':str(len(data)),'ETag':etag,'Last-Modified':'Sun, 25 Oct 2026 05:14:07 GMT'}
        self.data=data
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def raise_for_status(self):
        if self.status_code>=400:raise ValueError('HTTP failure')
    def iter_content(self,size):yield self.data


class Transport:
    def __init__(self,data,change_version=False,ignore_range=False):self.data=data;self.calls=[];self.change=change_version;self.ignore=ignore_range
    def get(self,url,headers,**kwargs):
        start,end=map(int,headers['Range'].removeprefix('bytes=').split('-'));end=min(end,len(self.data)-1);self.calls.append((start,end))
        return Response(self.data[start:end+1],start,end,len(self.data),etag='"changed"' if self.change and len(self.calls)>1 else '"fixed-object"',status=200 if self.ignore else 206)
    def close(self):pass


class BoundedRangeTests(unittest.TestCase):
    def test_actual_astropy_sections_and_versioned_bounded_ranges(self):
        from backend.range_reader import VersionedCubeFile
        cube=np.arange(102*9*11,dtype=np.float32).reshape(102,9,11)
        hdus=fits.HDUList([fits.PrimaryHDU(),fits.ImageHDU(cube,name='IMAGE'),fits.ImageHDU(np.full(cube.shape,1<<31,dtype=np.uint32),name='FLAGS')])
        buffer=BytesIO();hdus.writeto(buffer);transport=Transport(buffer.getvalue())
        with VersionedCubeFile(445,transport=transport,block_size=4096,max_bytes=100_000) as file:
            with fits.open(file,memmap=False) as image:
                np.testing.assert_array_equal(image['IMAGE'].section[:,3,5],cube[:,3,5])
                np.testing.assert_array_equal(image['FLAGS'].section[:,3,5],np.full(102,1<<31))
            self.assertLessEqual(file.transferred_bytes,100_000)
            self.assertTrue(file.ranges)
            self.assertEqual(file.source_info['etag'],'"fixed-object"')
        self.assertTrue(all(end-start<4096 for start,end in transport.calls))

    def test_ignored_range_changed_etag_budget_and_cancel_fail_closed(self):
        from backend.range_reader import VersionedCubeFile
        data=bytes(range(256))*100
        with self.assertRaisesRegex(ValueError,'206'):VersionedCubeFile(445,transport=Transport(data,ignore_range=True))
        with VersionedCubeFile(445,transport=Transport(data,change_version=True),block_size=4096) as file:
            file.seek(5000)
            with self.assertRaisesRegex(ValueError,'version'):file.read(10)
        with VersionedCubeFile(445,transport=Transport(data),block_size=4096,max_bytes=5000) as file:
            file.seek(5000)
            with self.assertRaisesRegex(ValueError,'budget'):file.read(10)
            with self.assertRaisesRegex(ValueError,'Unbounded'):file.read()
        def cancelled():raise ValueError('cancelled')
        with self.assertRaisesRegex(ValueError,'cancelled'):VersionedCubeFile(445,transport=Transport(data),check_cancel=cancelled)
        for index in [-1,12288,2.5]:
            with self.assertRaises(ValueError):VersionedCubeFile(index,transport=Transport(data))

    def test_malformed_or_weak_etags_are_not_strong_versions(self):
        from backend.range_reader import VersionedCubeFile
        class TagTransport(Transport):
            def get(self,*args,**kwargs):
                response=super().get(*args,**kwargs);response.headers['ETag']=tag;return response
        for tag in ['unquoted','W/"weak"','"unterminated','"bad space"']:
            with self.subTest(tag=tag),self.assertRaisesRegex(ValueError,'strong object version'):
                VersionedCubeFile(445,transport=TagTransport(bytes(20000)))


if __name__=='__main__':unittest.main()
