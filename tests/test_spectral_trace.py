import json
import tempfile
import unittest
import numpy as np
from pathlib import Path
from backend.science import ROOT
from backend.range_reader import VersionedCubeFile
from range_fixture import CubeFixtureTransport


class SpectralTraceTests(unittest.TestCase):
    def reader(self,index,**kwargs):return VersionedCubeFile(index,transport=CubeFixtureTransport(),**kwargs)

    def test_actual_all_channel_values_flags_blanks_and_bounded_native_io(self):
        from backend.spectral_trace import sample_visual_point
        result=sample_visual_point(60.8109955,51.3404038,file_factory=self.reader)
        fixture=json.loads((ROOT/'research/updates/2026-11-15/spectral-trace/fixture.json').read_text())
        self.assertEqual(result['native_pixel_xy'],fixture['native_pixel_xy'])
        self.assertEqual(result['brightness'],fixture['reference']['IMAGE'])
        self.assertEqual(result['hits'],fixture['reference']['NHITS'])
        self.assertEqual(result['flags'],fixture['reference']['FLAGS'])
        self.assertLess(result['transfer']['bytes'],8_000_000)
        self.assertEqual(result['source']['etag'],fixture['source']['etag'])

    def test_real_trace_product_keeps_102_rows_without_invented_errors(self):
        from backend.spectral_trace import build_visual_trace
        plane=json.loads((ROOT/'artifacts/hips-real-plane.json').read_text())
        def sampler(ra,dec,**kwargs):
            from backend.spectral_trace import sample_visual_point
            return sample_visual_point(ra,dec,file_factory=self.reader,**kwargs)
        with tempfile.TemporaryDirectory() as directory:
            product=build_visual_trace(plane,[80,80],directory,sampler=sampler)
            self.assertEqual(product['type'],'visual_spectral_trace')
            self.assertEqual(len(product['samples']),102)
            self.assertEqual([s['index'] for s in product['samples'] if s['status']=='blank'],[50,51])
            self.assertEqual(product['samples'][62]['brightness_mjysr'],plane['brightness'][80][80])
            self.assertFalse(product['numerical_products_authorized'])
            self.assertFalse(product['uncertainties_available'])
            self.assertNotIn('flux_ujy',product['samples'][62])
            self.assertTrue((Path(directory)/product['id']/'trace.ecsv').is_file())
            self.assertTrue((Path(directory)/product['id']/'trace.svg').is_file())
            saved=(Path(directory)/product['id']/'manifest.json').read_bytes()
            again=build_visual_trace(plane,[80,80],directory,sampler=sampler)
            self.assertEqual(again,product)
            self.assertEqual((Path(directory)/product['id']/'manifest.json').read_bytes(),saved)
            other=build_visual_trace(plane|{'id':'f'*64},[80,80],directory,sampler=sampler)
            self.assertEqual(other['trace_data_id'],product['trace_data_id'])
            self.assertNotEqual(other['id'],product['id'])
            for point in [[-1,0],[plane['shape'][1],0],[0,plane['shape'][0]],[1.5,1]]:
                with self.assertRaises(ValueError):build_visual_trace(plane,point,directory,sampler=lambda *args,**kwargs:self.fail('Invalid geometry must not read the archive'))

    def test_cancel_and_nonfinite_coordinates_stop_before_archive_sampling(self):
        from backend.spectral_trace import sample_visual_point
        for position in [(np.nan,0),(0,np.inf),(0,91)]:
            with self.assertRaises(ValueError):sample_visual_point(*position,file_factory=lambda *args,**kwargs:self.fail('Invalid coordinates cannot read data'))
        def cancelled():raise ValueError('cancelled')
        with self.assertRaisesRegex(ValueError,'cancelled'):sample_visual_point(60.8109955,51.3404038,file_factory=self.reader,check_cancel=cancelled)


if __name__=='__main__':unittest.main()
