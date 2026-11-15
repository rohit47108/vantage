import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from astropy.table import Table
from backend.science import ROOT
from backend.spectra import build_spectrum, SpectrumRequest,target_description


class SpectrumTests(unittest.TestCase):
    def test_actual_measurements_rejections_units_and_export_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            result=build_spectrum(SpectrumRequest(),Path(directory))
            self.assertEqual(result['type'],'source_samples')
            self.assertEqual(len(result['samples']),4)
            by_id={s['obs_id']:s for s in result['samples']}
            good=by_id['2025W30_1B_0059_3']
            self.assertEqual(good['status'],'accepted')
            self.assertAlmostEqual(good['flux_ujy'],28983.6846778,places=3)
            self.assertAlmostEqual(good['statistical_sigma_ujy'],175.6402061,places=3)
            self.assertEqual(by_id['2026W08_1A_0601_1']['status'],'rejected')
            self.assertIsNone(by_id['2026W08_1A_0601_1']['flux_ujy'])
            self.assertIn('cover',by_id['2026W08_1A_0601_1']['reason'])
            self.assertEqual(by_id['2026W07_2A_0338_3']['status'],'diagnostic_only')
            self.assertFalse(result['complete_102_channel_spectrum'])
            self.assertIn('calibration',result['uncertainty_method'])
            folder=Path(directory)/result['id']
            table=Table.read(folder/'samples.ecsv',format='ascii.ecsv')
            self.assertEqual(str(table['flux_ujy'].unit),'uJy')
            self.assertEqual(str(table['mjd_mid'].unit),'d')
            self.assertEqual(len(table),4)
            self.assertEqual(int(table['flux_ujy'].mask.sum()),1)
            self.assertTrue((folder/'samples.csv').is_file())
            self.assertTrue((folder/'plot.svg').is_file())
            self.assertEqual(json.loads((folder/'manifest.json').read_text())['id'],result['id'])
            self.assertEqual(build_spectrum(SpectrumRequest(observation_indices=[3,2,1,0]),Path(directory))['id'],result['id'])

    def test_aperture_time_subset_identity_and_no_silent_fill(self):
        with tempfile.TemporaryDirectory() as directory:
            result=build_spectrum(SpectrumRequest(method='aperture',observation_indices=[1,3]),Path(directory))
            self.assertEqual(len(result['samples']),2)
            self.assertAlmostEqual(result['samples'][0]['flux_ujy'],28937.0976969,places=3)
            self.assertEqual(result['sampling']['selected_observation_indices'],[1,3])
            self.assertEqual(result['sampling']['available_observations'],4)
            self.assertEqual(result['sampling']['unselected_observations'],2)
            self.assertEqual(result['sampling']['accepted_samples'],1)
            self.assertEqual(result['sampling']['rejected_samples'],1)
            self.assertEqual(result['samples'][1]['status'],'rejected')

    def test_checksum_failure_and_cancellation_prevent_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('backend.spectra.digest',return_value='incorrect'):
                with self.assertRaisesRegex(ValueError,'checksum'):
                    build_spectrum(SpectrumRequest(),Path(directory))
            def cancel():raise ValueError('Job cancelled')
            with self.assertRaisesRegex(ValueError,'cancelled'):
                build_spectrum(SpectrumRequest(),Path(directory),check_cancel=cancel)
            self.assertEqual(list(Path(directory).glob('*/manifest.json')),[])

    def test_request_bounds_and_background_geometry(self):
        for values in [{'target_key':'../file'},{'observation_indices':[4]},{'observation_indices':[0,0]},
                       {'aperture_radius':5},{'background_inner':8,'background_outer':7},
                       {'arbitrary_url':'https://example.com'},{'method':'median'}]:
            with self.assertRaises(ValueError):SpectrumRequest(**values)
        target=target_description()
        self.assertEqual(len(target['observations']),4)
        self.assertEqual(len(target['revision']),64)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'metadata changed'):
                build_spectrum(SpectrumRequest(target_revision='0'*64),Path(directory))


if __name__=='__main__':unittest.main()
