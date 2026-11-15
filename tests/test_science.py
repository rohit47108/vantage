"""Offline regression checks against independently supplied fixture metadata."""
import json
import unittest
import os
import tempfile
from unittest.mock import patch
import numpy as np
from pathlib import Path
from fastapi.testclient import TestClient
TEST_RUNTIME = tempfile.TemporaryDirectory()
os.environ['VANTAGE_RUNTIME'] = TEST_RUNTIME.name
from backend.app import app
from backend.archive import coordinates, allowed
from backend.science import ROOT, digest, BAD_MASK, plane, grid


class ScientificContract(unittest.TestCase):
    def test_actual_qr2_qr3_named_layers_and_spatial_wcs(self):
        from astropy.io import fits
        from astropy.wcs import WCS
        from astropy.time import Time
        for name,psf_extension in [('m101_qr2_cutout.fits','PSF'),('qr3_cutout.fits','EPSF')]:
            with fits.open(ROOT/'research/fixtures'/name) as hdus:
                shape=hdus['IMAGE'].data.shape
                self.assertTrue(all(hdus[layer].data.shape==shape for layer in ('FLAGS','VARIANCE','ZODI')))
                raw=hdus['FLAGS'].data
                self.assertIn(raw.dtype.kind,('i','u'))
                normalized=np.array(raw,dtype=np.uint32)
                np.testing.assert_array_equal(normalized.astype(np.uint64),raw.astype(np.int64)&0xffffffff)
                self.assertIn(psf_extension,hdus)
                wcs=WCS(hdus['IMAGE'].header)
                ra,dec=wcs.pixel_to_world_values(20.,20.)
                x,y=wcs.world_to_pixel_values(ra,dec)
                np.testing.assert_allclose([x,y],[20,20],atol=1e-5)
                self.assertTrue(np.isfinite(hdus['IMAGE'].header['MJD-AVG']))

    def test_archive_failure_remains_explicit(self):
        import requests
        client=TestClient(app)
        with patch('backend.app.discover',side_effect=requests.ConnectTimeout('test archive outage')):
            response=client.post('/v1/observations/search',json={'ra':23,'dec':-32,'fov_arcmin':7})
        self.assertEqual(response.status_code,502)
        self.assertIn('prepared',response.json()['detail'])
    def test_canonical_jobs_and_retry_identity(self):
        from backend.app import connect
        client = TestClient(app)
        with patch('backend.app.pool.submit'):
            request = {'ra':0,'dec':0,'fov_arcmin':6}
            first = client.post('/v1/sequences',json=request).json()
            duplicate = client.post('/v1/sequences',json=request | {'ra':360}).json()
            self.assertEqual(first['job_id'],duplicate['job_id'])
            self.assertEqual(client.delete('/v1/jobs/'+first['job_id']).status_code,200)
            retry = client.post('/v1/sequences',json=request).json()
            self.assertNotEqual(first['job_id'],retry['job_id'])
            self.assertEqual(client.get(first['status_url']).json()['state'],'cancelled')
        self.assertEqual(client.post('/v1/sequences',json=request|{'start_utc':'2026-12-01','end_utc':'2026-01-01'}).status_code,422)
        self.assertEqual(client.post('/v1/sequences',json=request|{'observations':[{}]}).status_code,422)

    def test_actual_dr1_text_detector_schema(self):
        from astropy.io import fits
        from backend.science import write_json
        calibration = ROOT/'research/fixtures/dr1_spectral_wcs_d6.fits'
        exposure = ROOT/'research/fixtures/dr1_d6_cutout.fits'
        retained=json.loads((ROOT/'research/updates/2026-11-14/dr1-fixtures.json').read_text())
        for row in retained['files']:
            self.assertEqual(digest(ROOT/row['path']),row['sha256'])
        self.assertEqual(str(fits.getheader(calibration,'CWAVE')['DETECTOR']),'6')
        wcs,size=grid([133.79512916666664,-7.245147222222222],6)
        result=plane({'fixture':str(exposure),'source_calibration':str(calibration),'release':'dr1'},wcs,size)
        self.assertEqual(result[-1]['detector'],6)
        self.assertIn('EPSF',result[-1]['ancillary_hdus'])
        self.assertTrue(4.3<result[-1]['wavelength_um']<5.1)

    def test_coordinate_conventions(self):
        np.testing.assert_allclose(coordinates('08h55m10.831s', '−7d14m42.53s'),
                                   [133.79512916666664, -7.245147222222222], atol=1e-10)
        self.assertEqual(coordinates(-1, 90), [359, 90])
        for ra, dec in [('NaN', '0'), ('4', '91'), ('08:55:10', '0'), ('0', 'inf')]:
            with self.assertRaises(ValueError):
                coordinates(ra, dec)

    def test_scientific_assets(self):
        catalog = json.loads((ROOT/'public/prepared/catalog.json').read_text())
        self.assertEqual(len(catalog), 8)
        for sequence in catalog:
            self.assertFalse(sequence['numerical_products_authorized'])
            self.assertEqual([f['mjd_mid'] for f in sequence['frames']], sorted(f['mjd_mid'] for f in sequence['frames']))
            for frame in sequence['frames']:
                path = ROOT/'public'/frame['asset'].lstrip('/')
                self.assertEqual(digest(path), frame['asset_sha256'])
                data = json.loads(path.read_text())
                self.assertEqual(list(np.shape(data['pixels'])), sequence['shape'])
                if sequence['mode'] == 'fixed_sky':
                    self.assertEqual(frame['grid'], sequence['grid'])
                valid = np.array(data['joint'], dtype=bool)
                self.assertTrue(np.all(np.array(data['quality'])[valid]))
                self.assertTrue(np.all(np.array(data['coverage'])[valid]))

    def test_wavelength_matches_independent_research(self):
        benchmarks = json.loads((ROOT/'demo_dataset_manifest.json').read_text(encoding='utf-8'))['full_challenge_benchmarks']
        for benchmark in benchmarks.values():
            wcs, size = grid(benchmark['center_deg'], 6)
            for frame in benchmark['sequence']:
                result = plane(frame, wcs, size)
                np.testing.assert_allclose([result[-1]['wavelength_um'], result[-1]['bandwidth_um']], frame['target_lambda_width_um'], atol=5e-7)
        self.assertEqual(BAD_MASK & (1 << 21), 0)

    def test_api_bounds_and_persistence(self):
        client = TestClient(app)
        self.assertEqual(client.post('/v1/observations/search', json={'ra':0,'dec':0,'fov_arcmin':31}).status_code, 422)
        self.assertEqual(client.get('/v1/sequences/../../etc').status_code, 404)
        for sequence in json.loads((ROOT/'public/prepared/catalog.json').read_text()):
            self.assertEqual(client.get('/v1/sequences/'+sequence['id']).json()['id'], sequence['id'])
        for url in ['http://irsa.ipac.caltech.edu/ibe/data/spherex/a','https://evil.test/ibe/data/spherex/a','https://irsa.ipac.caltech.edu:80/ibe/data/spherex/a']:
            with self.assertRaises(ValueError):
                allowed(url)


if __name__ == '__main__':
    unittest.main()
