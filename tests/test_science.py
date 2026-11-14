"""Offline regression checks against independently supplied fixture metadata."""
import json
import unittest
import numpy as np
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app import app
from backend.archive import coordinates, allowed
from backend.science import ROOT, digest, BAD_MASK, plane, grid


class ScientificContract(unittest.TestCase):
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
