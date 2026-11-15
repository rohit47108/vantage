import copy
import json
import unittest
from astropy.io import fits
from backend.science import ROOT,digest
from backend.calibration_registry import approved_binding,registry,verified_path


class CalibrationRegistryTests(unittest.TestCase):
    def test_actual_six_detector_headers_and_datalink_associations(self):
        acquisition=json.loads((ROOT/'research/updates/2026-11-15/native-extraction/acquisition.json').read_text())
        for row in acquisition['observations']:
            self.assertEqual(digest(ROOT/row['path']),row['sha256'])
            self.assertEqual(digest(ROOT/row['datalink_path']),row['datalink_sha256'])
            with fits.open(ROOT/row['path'],memmap=False) as image:
                result=approved_binding(image,'dr1')
                self.assertEqual(result['detector'],row['detector'])
                self.assertEqual(result['spectral_wcs']['original_fits_sha256'],row['calibration_sha256'])
                self.assertEqual(result['solid_angle']['original_fits_sha256'],row['solid_angle_sha256'])
                self.assertEqual(verified_path(result['spectral_wcs']),ROOT/row['calibration_path'])
                self.assertEqual(verified_path(result['solid_angle']),ROOT/row['solid_angle_path'])
        self.assertEqual(len(registry()['bindings']),6)

    def test_unknown_release_processing_uuid_and_orientation_do_not_promote(self):
        path=ROOT/'research/updates/2026-11-15/native-extraction/reference_d1.fits'
        with fits.open(path,memmap=False) as image:
            for release in ['qr2','future','dr9']:
                with self.assertRaisesRegex(ValueError,'approved'):approved_binding(image,release)
            image[0].header['VERSION']='99.0'
            with self.assertRaisesRegex(ValueError,'processing'):approved_binding(image,'dr1')
            image[0].header['VERSION']='7.0.5'
            image['EPSF'].header['DETCOORD']='detector'
            with self.assertRaisesRegex(ValueError,'orientation'):approved_binding(image,'dr1')
            image['EPSF'].header['DETCOORD']='sky'
            image['IMAGE'].header['HISTORY']='[CALIB] spectral_wcs 11111111-1111-1111-1111-111111111111'
            with self.assertRaisesRegex(ValueError,'association'):approved_binding(image,'dr1')

    def test_changed_calibration_bytes_are_rejected(self):
        binding=copy.deepcopy(registry()['bindings'][0]['spectral_wcs'])
        binding['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'checksum'):verified_path(binding)


if __name__=='__main__':unittest.main()
