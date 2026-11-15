import unittest
import numpy as np
from backend.hips import metadata, tile_index, render_plane


class SpectralContextTests(unittest.TestCase):
    def test_actual_channel_table_and_blank_layers(self):
        m=metadata()
        self.assertEqual(len(m['channels']),102)
        self.assertEqual([c['index'] for c in m['channels'] if c['blank']],[50,51])
        self.assertEqual(m['channels'][62]['detector'],4)
        self.assertAlmostEqual(m['channels'][62]['wavelength_um'],3.293,places=5)
        self.assertGreater(m['channels'][62]['bandwidth_um'],0)
        self.assertFalse(m['numerical_products_authorized'])

    def test_official_nested_healpix_reference(self):
        self.assertEqual(int(tile_index(60.8109955,51.3404038)),445)
        self.assertEqual(int(tile_index(0,0)),int(tile_index(360,0)))

    def test_invalid_and_blank_requests_do_not_retrieve_data(self):
        def reject(*args):raise AssertionError('No retrieval allowed')
        for center,fov,layer in [([0,91],6,0),([float('nan'),0],6,0),([0,0],0,0),([0,0],121,0),([0,0],6,102)]:
            with self.assertRaises(ValueError):render_plane(center,fov,layer,tile_reader=reject)
        p=render_plane([60.81,51.34],6,50,size=16,tile_reader=reject)
        self.assertEqual(p['coverage_fraction'],0)
        self.assertTrue(p['channel']['blank'])
        self.assertTrue(all(v is None for row in p['brightness'] for v in row))

    def test_nearest_sampling_preserves_flags_and_missing_support(self):
        def reader(ipix,layer,ra,dec):
            v=np.ones(ra.shape)*12
            hits=np.ones(ra.shape,dtype=int)*2
            flags=np.ones(ra.shape,dtype=np.uint32)*(1<<21)
            hits[0]=0
            return v,hits,flags,{'url':'https://irsa.ipac.caltech.edu/test','tile':int(ipix),'mjd_start':60000,'mjd_end':60100}
        p=render_plane([60.81,51.34],6,62,size=16,tile_reader=reader)
        self.assertEqual(p['flags'][1][1],1<<21)
        self.assertEqual(p['brightness'][1][1],12)
        self.assertIsNone(p['brightness'][0][0])
        self.assertFalse(p['numerical_products_authorized'])
        self.assertEqual(p['grid']['CTYPE1'],'RA---TAN')
        self.assertLess(p['grid']['CDELT1'],0)
        self.assertGreater(p['grid']['CDELT2'],0)

    def test_real_reference_matches_independent_range_read(self):
        import json
        from backend.science import ROOT
        evidence=json.loads((ROOT/'research/updates/2026-11-14/hips-live-probe.json').read_text())
        p=json.loads((ROOT/'artifacts/hips-real-plane.json').read_text())
        self.assertEqual(p['brightness'][80][80],evidence['IMAGE_reference'][62])
        self.assertEqual(p['hits'][80][80],evidence['NHITS_reference'][62])
        self.assertEqual(p['flags'][80][80],evidence['FLAGS_reference'][62])

    def test_api_bounds_and_restart_readable_products(self):
        import tempfile,os
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from backend.app import app
        from backend.science import write_json
        from backend.spectral_routes import storage
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'VANTAGE_RUNTIME':tmp}):
            c=TestClient(app)
            self.assertEqual(len(c.get('/v1/spectral/metadata').json()['channels']),102)
            self.assertEqual(c.get('/v1/spectral/plane?ra=0&dec=91').status_code,422)
            self.assertEqual(c.get('/v1/spectral/plane?ra=0&dec=0&layer=102').status_code,422)
            p=c.get('/v1/spectral/plane?ra=0&dec=0&layer=50').json()
            self.assertTrue(p['channel']['blank'])
            result=TestClient(app).get('/v1/spectral/products/'+p['id'])
            self.assertEqual(result.json()['id'],p['id'])
            self.assertEqual(c.get('/v1/spectral/products/../../secret').status_code,404)

if __name__=='__main__':unittest.main()
