import json
import tempfile
import unittest
from pathlib import Path
from backend.science import ROOT
from backend.native_extraction import SourcePosition,ExtractionOptions,extract_observations


class NativeExtractionTests(unittest.TestCase):
    def fixtures(self):
        acquisition=json.loads((ROOT/'research/updates/2026-11-15/native-extraction/acquisition.json').read_text())
        old=json.loads((ROOT/'research/updates/2026-11-15/photometry/benchmark.json').read_text())
        rows=acquisition['observations']+[old['observations'][1]]
        source=SourcePosition(name='P330E',**{k:old['source'][k] for k in ['ra','dec','pmra','pmdec','ref_epoch']})
        paths={(r['obs_id'],r['detector']):(ROOT/r['path'],r['retrieval_mode']) for r in rows}
        return rows,source,lambda row,position:paths[(row['obs_id'],row['detector'])]

    def test_real_general_extraction_covers_all_six_detectors_with_failed_coverage(self):
        rows,source,loader=self.fixtures()
        with tempfile.TemporaryDirectory() as directory:
            result=extract_observations(rows,source,ExtractionOptions(),Path(directory),native_loader=loader)
            passing=[s for s in result['samples'] if s['status']=='accepted']
            self.assertEqual({s['detector'] for s in passing},set(range(1,7)))
            self.assertEqual(len(result['samples']),7)
            failed=next(s for s in result['samples'] if s['obs_id']=='2025W29_1A_0544_2')
            self.assertEqual(failed['status'],'rejected');self.assertIsNone(failed['flux_ujy'])
            self.assertIn('cover',failed['reason'])
            self.assertFalse(result['complete_102_channel_spectrum'])
            self.assertEqual(result['source']['name'],'P330E')
            for sample in passing:
                self.assertLess(abs(sample['solid_angle_wcs_ratio']-1),.001)
                self.assertNotIn('image_context',sample)
                self.assertTrue((Path(directory)/result['id']/sample['image_context_file']).is_file())
                self.assertEqual(len(sample['source_sha256']),64)
            self.assertLess(min(s['wavelength_um'] for s in passing),1.)
            self.assertGreater(max(s['wavelength_um'] for s in passing),4.7)
            self.assertTrue((Path(directory)/result['id']/'samples.ecsv').is_file())

    def test_source_request_bounds_and_motion_model(self):
        for change in [{'ra':float('nan'),'dec':0},{'ra':0,'dec':91},{'ra':0,'dec':0,'pmra':1},
                       {'ra':0,'dec':0,'arbitrary_url':'https://example.com'}]:
            with self.assertRaises(ValueError):SourcePosition(**change)
        fixed=SourcePosition(ra=10,dec=20)
        self.assertEqual(fixed.position(60000),[10.,20.])
        moving=SourcePosition(ra=10,dec=20,pmra=100,pmdec=-50,ref_epoch=2016)
        self.assertNotEqual(moving.position(60000),fixed.position(60000))
        with self.assertRaises(ValueError):ExtractionOptions(background_inner=9,background_outer=7)

    def test_cancelled_generic_extraction_does_not_publish(self):
        rows,source,loader=self.fixtures()
        def cancelled():raise ValueError('Job cancelled')
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'cancelled'):
                extract_observations(rows,source,ExtractionOptions(),Path(directory),native_loader=loader,check_cancel=cancelled)
            self.assertEqual(list(Path(directory).glob('*/manifest.json')),[])


if __name__=='__main__':unittest.main()
