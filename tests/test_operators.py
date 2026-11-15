"""Numerical operators: independent analytic and Monte Carlo checks."""
import unittest
import numpy as np
from scipy import sparse
from backend.operators import linear_transform, weighted_mean, difference, overlap_operator
from backend.science import grid


class LinearOperatorTests(unittest.TestCase):
    def test_covariance_uses_squared_weights_and_keeps_offdiagonal(self):
        a=sparse.csr_matrix([[.5,.5,0],[0,.5,.5]])
        y,c=linear_transform(a,np.array([2.,4.,8.]),np.array([1.,4.,9.]))
        np.testing.assert_allclose(y,[3,6])
        np.testing.assert_allclose(c.toarray(),[[1.25,1],[1,3.25]])
        rng=np.random.default_rng(174)
        simulations=rng.normal(size=(100000,3))*np.sqrt([1.,4.,9.])
        empirical=np.cov((a@simulations.T))
        np.testing.assert_allclose(empirical,c.toarray(),rtol=.025)

    def test_independent_weighted_mean_and_shared_input_rejection(self):
        planes=[{'values':np.array([2.,4.]),'covariance':sparse.diags([1.,4.]),'valid':np.ones(2,dtype=bool),'source_ids':['a']},
                {'values':np.array([4.,8.]),'covariance':sparse.diags([3.,4.]),'valid':np.ones(2,dtype=bool),'source_ids':['b']}]
        p=weighted_mean(planes)
        np.testing.assert_allclose(p['values'],[2.5,6])
        np.testing.assert_allclose(p['covariance'].diagonal(),[.75,2])
        np.testing.assert_array_equal(p['contributions'],[2,2])
        planes[1]['source_ids']=['a']
        with self.assertRaisesRegex(ValueError,'shared'):weighted_mean(planes)

    def test_difference_background_fit_propagates_parameter_covariance(self):
        n=8
        a={'values':np.arange(n,dtype=float),'covariance':sparse.eye(n),'valid':np.ones(n,dtype=bool),'source_ids':['a']}
        b={'values':np.arange(n,dtype=float)+3,'covariance':sparse.eye(n),'valid':np.ones(n,dtype=bool),'source_ids':['b']}
        p=difference(a,b,background_mask=np.ones(n,dtype=bool))
        np.testing.assert_allclose(p['values'],0,atol=1e-12)
        np.testing.assert_allclose(p['covariance'].toarray(),2*(np.eye(n)-np.ones((n,n))/n),atol=1e-12)
        self.assertAlmostEqual(p['background'],3)
        b['source_ids']=['a']
        with self.assertRaisesRegex(ValueError,'shared'):difference(a,b,np.ones(n,dtype=bool))

    def test_pixel_overlap_preserves_uniform_surface_brightness_and_flux(self):
        source,_=grid([210.,54.],1,size=8)
        out,_=grid([210.,54.],1,size=16)
        a=overlap_operator(source,(8,8),out,(16,16))
        image=(a@np.ones(64)).reshape(16,16)
        np.testing.assert_allclose(image,1,atol=1e-6)
        point=np.zeros((8,8));point[4,4]=10
        self.assertAlmostEqual((a@point.ravel()).sum()/4,point.sum(),places=5)

    def test_actual_distorted_geometry_against_independent_spherical_overlap(self):
        from astropy.io import fits
        from astropy.wcs import WCS
        from reproject import reproject_exact
        from backend.science import ROOT
        source=WCS(fits.getheader(ROOT/'research/fixtures/m101_epoch_a.fits','IMAGE'))
        out,_=grid([210.80227,54.34895],3,size=32)
        raw=fits.getdata(ROOT/'research/fixtures/m101_epoch_a.fits','IMAGE').astype(float)
        a=overlap_operator(source,raw.shape,out,(32,32))
        actual=(a@raw.ravel()).reshape(32,32)
        reference,footprint=reproject_exact((raw,source),out,shape_out=(32,32))
        good=(footprint>.999)&np.isfinite(reference)
        scale=np.percentile(raw,99)-np.percentile(raw,1)
        self.assertLess(np.max(np.abs(actual[good]-reference[good]))/scale,.001)

    def test_real_narrowband_coadd_export_and_correlated_aperture_noise(self):
        import json,tempfile
        from astropy.io import fits
        from backend.science import ROOT
        from backend.coadds import build_coadd
        catalog=json.loads((ROOT/'public/prepared/catalog.json').read_text())
        s=next(s for s in catalog if s['key']=='m101')
        with tempfile.TemporaryDirectory() as folder:
            p=build_coadd(s,[0,1],folder)
            self.assertGreater(p['joint_support_fraction'],.05)
            self.assertLess(p['mjd_interval'][0],min(f['mjd_mid'] for f in s['frames']))
            self.assertGreater(p['mjd_interval'][1],max(f['mjd_mid'] for f in s['frames']))
            with fits.open(f'{folder}/{p["id"]}/science.fits',checksum=True,memmap=False) as hdus:
                self.assertEqual(hdus['VARIANCE'].header['BUNIT'],'(MJy/sr)^2')
                self.assertTrue(np.all(hdus['NCONTRIB'].data[hdus['MASK'].data==0]==2))
                rows=hdus['COVARIANCE'].data
                c=sparse.csr_array((np.array(rows['COVARIANCE'],dtype=float),(np.array(rows['ROW'],dtype=int),np.array(rows['COL'],dtype=int))),shape=(1024,1024))
                valid=(hdus['MASK'].data==0).ravel()
                # Integrated-region variance must include off-diagonal noise.
                full=float(valid.astype(float)@c@valid.astype(float))
                diagonal=float(c.diagonal()[valid].sum())
                self.assertGreater(full,diagonal)
            with self.assertRaisesRegex(ValueError,'distinct'):build_coadd(s,[0,0],folder)

    def test_native_unit_mismatch_is_rejected(self):
        import json,tempfile
        from pathlib import Path
        from unittest.mock import patch
        from astropy.io import fits
        from backend.science import ROOT
        from backend.coadds import native_plane
        s=next(s for s in json.loads((ROOT/'public/prepared/catalog.json').read_text()) if s['key']=='m101')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'invalid-units.fits'
            with fits.open(ROOT/'research/fixtures/m101_epoch_a.fits',memmap=False) as hdus:
                hdus['VARIANCE'].header['BUNIT']='Jy'
                hdus.writeto(path)
            with patch('backend.coadds.source_file',return_value=path):
                with self.assertRaisesRegex(ValueError,'units'):
                    native_plane(s['frames'][0],grid(s['center_deg'],3,32)[0],(32,32))

if __name__=='__main__':unittest.main()
