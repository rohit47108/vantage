import unittest
import numpy as np
from scipy.special import erf
from astropy.io import fits
from astropy import units as u
from backend.science import ROOT
from backend.photometry import render_epsf,epsf_for_image,solid_angle_for_image,to_pixel_flux,measure_source,measure_with_centroid,measure_fits


def gaussian_epsf(sigma=1.,oversampling=5):
    axis=np.arange(-40,41)/oversampling
    pixel=(erf((axis+.5)/(sigma*np.sqrt(2)))-erf((axis-.5)/(sigma*np.sqrt(2))))/2
    data=np.outer(pixel,pixel)
    return data/data.sum()


def synthetic():
    y,x=np.indices((41,41));position=(20.23,20.68)
    p,_=render_epsf(gaussian_epsf(),(5,5),*position,(41,41))
    omega=(37.7+.002*x+.003*y)*(u.arcsec**2).to(u.sr)
    factor=omega*1e12
    background=1.3+.001*(x-position[0])-.002*(y-position[1])
    brightness=17250*p/factor+background
    variance=np.ones(x.shape)*.0001
    return brightness,variance,np.zeros(x.shape,dtype=np.uint32),omega,p,position


class PhotometryTests(unittest.TestCase):
    def test_retained_photometry_inputs_match_their_source_checksums(self):
        import json
        from backend.science import digest
        folder=ROOT/'research/updates/2026-11-15/photometry'
        manifest=json.loads((folder/'fixture-manifest.json').read_text())
        for record in manifest['files']:
            self.assertEqual(digest(ROOT/record['path']),record['sha256'],record['path'])

    def test_solid_angle_units_origin_and_surface_brightness_conversion(self):
        path=ROOT/'research/updates/2026-11-15/photometry/sapm_d2.fits'
        with fits.open(path,memmap=False) as h:
            header={'DETECTOR':2,'CRPIX1A':-100.,'CRPIX2A':-200.}
            area=solid_angle_for_image(h,header,(3,4))
            expected=np.array(h['IMAGE'].data[201:204,101:105],dtype=float)*(u.arcsec**2).to(u.sr)
            np.testing.assert_allclose(area,expected,rtol=1e-12)
            with self.assertRaisesRegex(ValueError,'detector'):solid_angle_for_image(h,header|{'DETECTOR':1},(3,4))
            with self.assertRaisesRegex(ValueError,'integer'):solid_angle_for_image(h,header|{'CRPIX1A':-.5},(3,4))
        flux,var=to_pixel_flux(np.ones((3,4)),np.full((3,4),2.),area)
        np.testing.assert_allclose(flux,area*1e12)
        np.testing.assert_allclose(var,2*(area*1e12)**2)

    def test_phase_render_matches_an_independent_pixel_integrated_gaussian(self):
        y,x=np.indices((41,41));x0,y0=20.23,20.68
        p,meta=render_epsf(gaussian_epsf(),(5,5),x0,y0,(41,41))
        gx=(erf((x-x0+.5)/np.sqrt(2))-erf((x-x0-.5)/np.sqrt(2)))/2
        gy=(erf((y-y0+.5)/np.sqrt(2))-erf((y-y0-.5)/np.sqrt(2)))/2
        reference=gx*gy;reference/=reference.sum()
        np.testing.assert_allclose(p,reference,atol=2e-5,rtol=0)
        self.assertAlmostEqual(p.sum(),1.,places=12)
        self.assertAlmostEqual(meta['stored_sample_sum'],1.,places=12)
        self.assertLess(meta['native_sum_before_normalization'],.05)
        shifted,_=render_epsf(gaussian_epsf(),(5,5),20.,20.,(41,41))
        self.assertGreater(np.max(abs(shifted-p)),.01)

    def test_cutout_edge_does_not_renormalize_missing_source_flux(self):
        p,meta=render_epsf(gaussian_epsf(),(5,5),.1,.1,(41,41))
        self.assertLess(p.sum(),.7)
        self.assertLess(meta['cutout_psf_fraction'],.7)

    def test_actual_epsf_zones_detector_metadata_and_legacy_guard(self):
        with fits.open(ROOT/'research/fixtures/m101_epoch_a.fits') as image:
            with self.assertRaisesRegex(ValueError,'optical PSF'):epsf_for_image(image,25.2,26.3)
            with fits.open(ROOT/'research/fixtures/epsf_d2.fits') as calibration:
                p,m=epsf_for_image(image,25.2,26.3,external_epsf=calibration)
                self.assertEqual(m['oversampling_yx'],[5,5])
                parent=[25.2+1-image['IMAGE'].header['CRPIX1A'],26.3+1-image['IMAGE'].header['CRPIX2A']]
                table=calibration['EPSF'].data
                row=np.argmin((table['XCENTER']-parent[0])**2+(table['YCENTER']-parent[1])**2)
                self.assertEqual(m['zone_row'],row)
                np.testing.assert_allclose(m['parent_pixel_xy'],parent)
                self.assertAlmostEqual(p.sum(),1.)
        with fits.open(ROOT/'research/fixtures/dr1_d6_cutout.fits') as image:
            p,m=epsf_for_image(image,40.2,41.3)
            self.assertEqual(m['detector'],6)
            self.assertEqual(m['detector_coordinate_convention'],'sky')
            self.assertAlmostEqual(p.sum(),1.)

    def test_psf_and_aperture_recover_flux_with_a_fitted_surface_brightness_gradient(self):
        image,var,flags,area,p,position=synthetic()
        for method in ['psf','aperture']:
            result=measure_source(image,var,flags,area,p,*position,method=method)
            self.assertAlmostEqual(result['flux_ujy'],17250,places=6)
            self.assertGreater(result['statistical_sigma_ujy'],0)
            np.testing.assert_allclose(result['background_coefficients_mjysr'],[1.3,.001,-.002],atol=1e-10)
            self.assertLess(result['reduced_chi2'],1e-15)
            self.assertTrue(result['statistical_only'])

    def test_background_and_aperture_error_propagation_matches_noise_realizations(self):
        image,var,flags,area,p,position=synthetic()
        rng=np.random.default_rng(8715)
        noise=rng.normal(size=(2000,image.size))*np.sqrt(var).ravel()*area.ravel()*1e12
        for method in ['psf','aperture']:
            result=measure_source(image,var,flags,area,p,*position,method=method)
            measured=np.var(noise@result['linear_estimator'].ravel(),ddof=1)
            self.assertLess(abs(measured/result['statistical_sigma_ujy']**2-1),.10)
            self.assertGreater(np.max(abs(result['linear_estimator'][15:18,15:18])),0)

    def test_source_information_is_allowed_but_defective_and_unknown_core_pixels_block(self):
        image,var,flags,area,p,position=synthetic()
        flags[20,20]=1<<21
        self.assertTrue(np.isfinite(measure_source(image,var,flags,area,p,*position)['flux_ujy']))
        for bit in [0,1,3]:
            flags[20,20]=1<<bit
            for method in ['psf','aperture']:
                with self.assertRaises(ValueError):measure_source(image,var,flags,area,p,*position,method=method)
        oversized=flags.astype(np.uint64);oversized[20,20]=1<<40
        with self.assertRaisesRegex(ValueError,'32-bit'):measure_source(image,var,oversized,area,p,*position)

    def test_insufficient_background_support_and_invalid_units_are_not_valid_measurements(self):
        image,var,flags,area,p,position=synthetic()
        y,x=np.indices(image.shape);distance=np.hypot(x-position[0],y-position[1])
        flags[distance>=5]=1<<21
        with self.assertRaisesRegex(ValueError,'background'):measure_source(image,var,flags,area,p,*position)
        with self.assertRaises(ValueError):to_pixel_flux(image,var,area*0)
        with self.assertRaises(ValueError):measure_source(image,var,flags,area,p,*position,method='sum')
        large=np.ones((97,97))
        with self.assertRaisesRegex(ValueError,'96 pixels'):measure_source(large,large,large.astype(np.uint32),large*1e-9,large/large.size,48.,48.)

    def test_authentic_calspec_flux_and_real_bad_aperture_and_missing_coverage(self):
        import json
        folder=ROOT/'research/updates/2026-11-15/photometry'
        benchmark=json.loads((folder/'benchmark.json').read_text())
        with fits.open(folder/'sapm_d2.fits',memmap=False) as area:
            row=benchmark['observations'][1]
            with fits.open(ROOT/row['path'],memmap=False) as image:
                for method in ['psf','aperture']:
                    result=measure_fits(image,area,*row['position_pixel'],method=method,refine_centroid=True)
                    # Independent CALSPEC top-hat approximation at the actual CWAVE/CBAND.
                    self.assertLess(abs(result['flux_ujy']/28822.785546862528-1),.10)
                    self.assertLess(result['reduced_chi2'],3.)
                    self.assertGreater(result['statistical_sigma_ujy'],100.)
            row=benchmark['observations'][0]
            with fits.open(ROOT/row['path'],memmap=False) as image:
                with self.assertRaisesRegex(ValueError,'defective pixel'):measure_fits(image,area,*row['position_pixel'],method='aperture',refine_centroid=True)
            row=benchmark['observations'][3]
            with fits.open(ROOT/row['path'],memmap=False) as image:
                with self.assertRaisesRegex(ValueError,'does not cover'):measure_fits(image,area,*row['position_pixel'])

    def test_centroid_refinement_recovers_offset_and_propagates_joint_errors(self):
        image,var,flags,area,p,position=synthetic()
        data=gaussian_epsf()
        renderer=lambda x,y:render_epsf(data,(5,5),x,y,image.shape)[0]
        for method in ['psf','aperture']:
            result=measure_with_centroid(image,var,flags,area,renderer,20.,20.,method=method)
            np.testing.assert_allclose(result['position_pixel_xy'],position,atol=1e-5)
            self.assertAlmostEqual(result['flux_ujy'],17250,places=4)
            covariance=result['centroid_fit']['covariance']
            self.assertEqual(covariance.shape,(6,6))
            np.testing.assert_allclose(covariance,covariance.T,atol=1e-10)
            self.assertGreater(np.linalg.eigvalsh(covariance).min(),0)
            self.assertAlmostEqual(result['statistical_sigma_ujy']**2,covariance[0,0])

    def test_centroid_and_flux_covariance_match_repeated_noisy_fits(self):
        image,var,flags,area,p,position=synthetic()
        data=gaussian_epsf();renderer=lambda x,y:render_epsf(data,(5,5),x,y,image.shape)[0]
        rng=np.random.default_rng(17503)
        for method in ['psf','aperture']:
            draws=[];predictions=[];scores=[]
            for _ in range(200):
                result=measure_with_centroid(image+rng.normal(size=image.shape)*np.sqrt(var),var,flags,area,renderer,20.05,20.5,method=method)
                draws.append([result['flux_ujy'],*result['position_pixel_xy']])
                predictions.append(np.diag(result['centroid_fit']['covariance'])[[0,4,5]])
                scores.append(result['reduced_chi2'])
            expected=np.mean(predictions,axis=0);actual=np.var(draws,axis=0,ddof=1)
            self.assertTrue(np.all(abs(actual/expected-1)<.25),(method,actual/expected))
            self.assertTrue(np.all(abs(np.mean(draws,axis=0)-[17250,*position])/np.sqrt(expected)<.3))
            self.assertLess(abs(np.mean(scores)-1),.05)

    def test_centroid_fit_blocks_faint_sources_and_boundary_solutions(self):
        image,var,flags,area,p,position=synthetic()
        data=gaussian_epsf();renderer=lambda x,y:render_epsf(data,(5,5),x,y,image.shape)[0]
        with self.assertRaisesRegex(ValueError,'signal-to-noise'):
            measure_with_centroid(image-17150*p/(area*1e12),var,flags,area,renderer,*position)
        with self.assertRaisesRegex(ValueError,'bounds'):
            measure_with_centroid(image,var,flags,area,renderer,position[0]-1.,position[1])


if __name__=='__main__':unittest.main()
