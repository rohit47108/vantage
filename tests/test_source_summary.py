import json
import unittest
import numpy as np
from scipy.integrate import quad
from scipy.stats import norm
from backend.science import ROOT


class SourceSummaryTests(unittest.TestCase):
    def test_actual_geometric_map_all_detectors_and_unassigned_failures(self):
        from backend.source_summary import channel_for_sample,channel_metadata
        product=json.loads((ROOT/'artifacts/native-workflow-public-product.json').read_text())
        expected={1:9,2:11,3:10,4:8,5:17,6:11}
        for sample in product['samples']:
            assignment=channel_for_sample(sample)
            if sample['status']=='accepted':self.assertEqual(assignment['channel'],expected[sample['detector']])
            self.assertEqual(assignment['coordinate_convention'],'sky; no additional MWIR flip')
        self.assertEqual(len(channel_metadata()['channels']),102)
        self.assertEqual(channel_metadata()['channels'][50]['visualization_blank'],True)
        self.assertEqual(channel_metadata()['channels'][51]['visualization_blank'],True)
        self.assertIsNone(channel_for_sample({'status':'rejected','detector':2}))

    def test_fixed_gaussian_bound_agrees_with_independent_posterior_integral(self):
        from backend.source_summary import gaussian_upper_bound
        for flux in [-40.,-4.,0.,1.,2.9,10.]:
            bound=gaussian_upper_bound(flux,1,.95)
            self.assertGreater(bound,0)
            # Factor out the maximum log likelihood on physical flux >= 0,
            # so independent quadrature also works in the far negative tail.
            peak=max(0,flux)
            def relative(value):return np.exp(-.5*((value-flux)**2-(peak-flux)**2))
            mass=quad(relative,0,bound,epsabs=1e-12)[0]/quad(relative,0,np.inf,epsabs=1e-12)[0]
            self.assertAlmostEqual(mass,.95,places=9)
        self.assertAlmostEqual(gaussian_upper_bound(0,1,.95),norm.ppf(.975),places=12)
        for flux,sigma,probability in [(0,0,.95),(np.nan,1,.95),(1,1,1)]:
            with self.assertRaises(ValueError):gaussian_upper_bound(flux,sigma,probability)

    def test_weighted_statistics_keep_negative_flux_and_conditional_covariance(self):
        from backend.source_summary import weighted_statistics
        result=weighted_statistics([-2,4],[1,2])
        self.assertAlmostEqual(result['flux_ujy'],-.8)
        self.assertAlmostEqual(result['statistical_sigma_ujy'],np.sqrt(.8))
        np.testing.assert_allclose(result['weights'],[.8,.2])
        random=np.random.default_rng(45346)
        draws=random.normal([-2,4],[1,2],(12000,2))@np.array(result['weights'])
        self.assertLess(abs(draws.var()/result['statistical_sigma_ujy']**2-1),.04)
        self.assertLess(result['equal_mean_p_value'],.01)
        self.assertIsNone(weighted_statistics([1],[2])['equal_mean_p_value'])

    def test_actual_summary_keeps_all_102_channels_dates_and_quality_counts(self):
        from backend.source_summary import summarize_samples,SummaryOptions
        product=json.loads((ROOT/'artifacts/native-workflow-public-product.json').read_text())
        result=summarize_samples(product,SummaryOptions(time_bin_days=1))
        self.assertEqual(len(result['coverage']),102)
        self.assertEqual(sum(row['accepted'] for row in result['coverage']),6)
        self.assertEqual(sum(row['diagnostic_only'] for row in result['coverage']),1)
        self.assertEqual(result['coverage'][33]['status'],'no_passing_measurement')
        self.assertEqual(len(result['bins']),6)
        self.assertTrue(all(row['count']==1 for row in result['bins']))
        self.assertTrue(all(row['bound'] is None for row in result['sample_statistics']))
        subset=summarize_samples(product,SummaryOptions(start_utc='2025-07-16',end_utc='2025-07-16'))
        self.assertEqual(subset['selected_sample_count'],2)
        self.assertEqual(len(subset['bins']),1)
        self.assertEqual(subset['bins'][0]['detector'],5)
        self.assertEqual(subset['bins'][0]['input_sample_ids'],['2025W29_1A_0544_1/D5'])
        product['samples'].append(product['samples'][0].copy())
        with self.assertRaisesRegex(ValueError,'physical'):summarize_samples(product,SummaryOptions())

    def test_limits_are_conditional_and_do_not_replace_missing_or_poor_fits(self):
        from backend.source_summary import sample_statistics
        sample={'sample_id':'example/D1','status':'accepted','flux_ujy':-1.,'statistical_sigma_ujy':2.}
        result=sample_statistics(sample)
        self.assertGreater(result['bound']['upper_ujy'],0)
        self.assertAlmostEqual(result['sensitivity']['flux_ujy']/2,5+norm.ppf(.95))
        for patch in [{'status':'rejected'},{'status':'diagnostic_only'},
                      {'centroid_fit':{'shift_pixel_xy':[0,0]}},{'flux_ujy':10.}]:
            result=sample_statistics(sample|patch)
            self.assertIsNone(result['bound'])

    def test_gaussian_scatter_and_detection_power_have_declared_null_behavior(self):
        from backend.source_summary import weighted_statistics,sample_statistics
        random=np.random.default_rng(165379)
        scores=[weighted_statistics(row,[1,2,3]) for row in random.normal(20,[1,2,3],(2500,3))]
        self.assertLess(abs(np.mean([r['equal_mean_chi2'] for r in scores])-2),.12)
        self.assertLess(abs(np.mean([r['equal_mean_p_value']<.01 for r in scores])-.01),.008)
        sensitivity=sample_statistics({'sample_id':'fixed','status':'accepted','flux_ujy':0.,'statistical_sigma_ujy':2.})['sensitivity']
        detected=random.normal(sensitivity['flux_ujy'],2,30000)>=10
        self.assertLess(abs(detected.mean()-.95),.004)


if __name__=='__main__':unittest.main()
