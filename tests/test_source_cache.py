import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from backend.archive import publish_cached_file


class SourceCacheTests(unittest.TestCase):
    def test_full_cache_rejects_new_bytes_without_deleting_retained_inputs(self):
        with tempfile.TemporaryDirectory() as directory,patch('backend.archive.CACHE',Path(directory)),patch.dict(os.environ,{'VANTAGE_SOURCE_CACHE_BYTES':'5'}):
            root=Path(directory);retained=root/'retained.fits';retained.write_bytes(b'1234')
            temporary=root/'new.partial';temporary.write_bytes(b'567')
            with self.assertRaisesRegex(ValueError,'cache is full'):publish_cached_file(temporary,root/'new.fits')
            self.assertEqual(retained.read_bytes(),b'1234')
            self.assertFalse(temporary.exists());self.assertFalse((root/'new.fits').exists())

    def test_concurrent_publication_stays_within_quota_and_retains_cache_identity(self):
        with tempfile.TemporaryDirectory() as directory,patch('backend.archive.CACHE',Path(directory)),patch.dict(os.environ,{'VANTAGE_SOURCE_CACHE_BYTES':'5'}):
            root=Path(directory)
            def write(i):
                temporary=root/f'{i}.partial';temporary.write_bytes(b'abc')
                try:publish_cached_file(temporary,root/f'{i}.fits');return True
                except ValueError:return False
            with ThreadPoolExecutor(max_workers=2) as pool:states=list(pool.map(write,range(2)))
            self.assertEqual(sum(states),1)
            self.assertLessEqual(sum(p.stat().st_size for p in root.iterdir()),5)
            existing=next(root.glob('*.fits'));temporary=root/'duplicate.partial';temporary.write_bytes(b'changed')
            publish_cached_file(temporary,existing)
            self.assertEqual(existing.read_bytes(),b'abc');self.assertFalse(temporary.exists())


if __name__=='__main__':unittest.main()
