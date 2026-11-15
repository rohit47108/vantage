import json
import unittest
from pathlib import Path
import numpy as np
import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time
from backend.science import ROOT
from backend.surveys import parse_catalog,propagate_gaia,project_layer,candidate_associations,resolve_xml


class SurveyTests(unittest.TestCase):
    def test_actual_catalogs_preserve_ids_dates_and_missing_values(self):
        folder=ROOT/'research/updates/2026-11-15'
        gaia=parse_catalog((folder/'gaia_gator.xml').read_bytes(),'gaia')
        wise=parse_catalog((folder/'wise_gator.xml').read_bytes(),'wise')
        self.assertEqual(len(gaia),283)
        self.assertEqual(gaia[0]['id'],'1609275081322912256')
        self.assertEqual(gaia[1]['id'],'1609275081322912000')
        self.assertEqual(wise[0]['id'],'J140312.52+542055.6')
        self.assertIsInstance(wise[0]['w1mjdmean'],float)
        self.assertEqual(wise[0]['ext_flg'],5)
        self.assertTrue(all(isinstance(s['id'],str) for s in gaia))
        fast=parse_catalog((folder/'barnard-fast-motion.xml').read_bytes(),'gaia')
        import hashlib
        probe=json.loads((folder/'fast-motion-probe.json').read_text())
        self.assertEqual(hashlib.sha256((folder/'barnard-fast-motion.xml').read_bytes()).hexdigest(),probe['sha256'])
        self.assertEqual([s['id'] for s in fast],['4472832130942575872'])
        self.assertGreater(np.hypot(fast[0]['pmra'],fast[0]['pmdec']),10000)

    def test_angular_motion_matches_independent_astropy_model_at_wrap_and_pole(self):
        import warnings
        row={'ra':359.999,'dec':89.9,'pmra':500.,'pmdec':-250.,'ref_epoch':2016.}
        target=Time(2025.,format='jyear',scale='tcb')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            ref=SkyCoord(ra=row['ra']*u.deg,dec=row['dec']*u.deg,pm_ra_cosdec=row['pmra']*u.mas/u.yr,pm_dec=row['pmdec']*u.mas/u.yr,obstime=Time(2016.,format='jyear',scale='tcb')).apply_space_motion(new_obstime=target)
        actual=propagate_gaia(row,target.utc.mjd)
        self.assertLess(SkyCoord(actual[0]*u.deg,actual[1]*u.deg).separation(ref).mas,.01)
        row['pmra']=None
        self.assertEqual(propagate_gaia(row,target.utc.mjd)[:2],(row['ra'],row['dec']))

    def test_real_projection_matches_primary_grid_and_changes_with_frame_epoch(self):
        from astropy.wcs import WCS
        folder=ROOT/'research/updates/2026-11-15'
        rows=parse_catalog((folder/'gaia_gator.xml').read_bytes(),'gaia')
        sequence=next(s for s in json.loads((ROOT/'public/prepared/catalog.json').read_text()) if s['key']=='m101')
        p=project_layer('gaia',rows,sequence)
        self.assertGreater(len(p),0)
        source=p[0];w=WCS(sequence['grid'])
        for i,frame in enumerate(sequence['frames']):
            coord=source['coordinates_by_frame'][i]
            expected=w.world_to_pixel_values(*coord)
            np.testing.assert_allclose(source['pixels_by_frame'][i],expected,atol=1e-7)
        self.assertFalse(source['observer_parallax_applied'])

    def test_association_compares_at_wise_epoch_and_remains_candidate(self):
        g={'id':'123','ra':20.,'dec':30.,'pmra':1000.,'pmdec':-500.,'ref_epoch':2016.}
        epoch=Time(2010.,format='jyear').mjd
        ra,dec,_=propagate_gaia(g,epoch)
        w={'id':'Jtest','ra':ra,'dec':dec,'w1mjdmean':epoch}
        pairs=candidate_associations([g],[w])
        self.assertEqual(len(pairs),1)
        self.assertEqual(pairs[0]['status'],'candidate_association')
        self.assertLess(pairs[0]['separation_arcsec'],.001)
        self.assertEqual(candidate_associations([g],[w|{'dec':31.}]),[])

    def test_tracked_projection_serializes_unprojectable_frame_as_missing(self):
        from backend.science import grid
        a,_=grid([20.,30.],6,32)
        b,_=grid([200.,-30.],6,32)
        sequence={'shape':[32,32],'grid':dict(a.to_header()),'frames':[
            {'mjd_mid':61000.,'grid':dict(a.to_header())},
            {'mjd_mid':61001.,'grid':dict(b.to_header())}]}
        rows=[{'id':'Jtest','ra':20.,'dec':30.}]
        result=project_layer('wise',rows,sequence)
        self.assertEqual(len(result),1)
        self.assertIsNone(result[0]['pixels_by_frame'][1])
        json.dumps(result,allow_nan=False)

    def test_association_cap_and_catalog_limits_are_explicit(self):
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from backend.app import app
        sequence=next(s for s in json.loads((ROOT/'public/prepared/catalog.json').read_text()) if s['key']=='m101')
        layer={'sources':[],'search_completeness':'limited','query_urls':['https://irsa.ipac.caltech.edu/first','https://irsa.ipac.caltech.edu/second']}
        with patch('backend.survey_routes.layer',return_value=layer),patch('backend.survey_routes.candidate_associations',return_value=[{'status':'candidate_association'}]*501):
            result=TestClient(app).get('/v1/associations',params={'sequence_id':sequence['id']}).json()
        self.assertEqual(len(result['pairs']),500)
        self.assertEqual(result['search_completeness'],'limited')
        self.assertTrue(result['pair_limit_reached'])
        self.assertEqual(len(result['source_queries']),2)

    def test_resolver_requires_finite_positions_and_retains_provider(self):
        p=resolve_xml((ROOT/'research/updates/2026-11-15/name.xml').read_bytes())
        self.assertAlmostEqual(p['center_deg'][0],210.8024292)
        self.assertIn('Simbad',p['provider'])
        with self.assertRaises(ValueError):resolve_xml(b'<Sesame/>')
        with self.assertRaises(ValueError):resolve_xml(b'<Sesame><Resolver><jradeg>NaN</jradeg><jdedeg>0</jdedeg></Resolver></Sesame>')

    def test_dense_gator_limit_is_not_an_empty_or_complete_result(self):
        import tempfile,os
        from unittest.mock import patch
        from backend.surveys import fetch_catalog
        error=b'<VOTABLE><RESOURCE><INFO name="QUERY_STATUS" value="ERROR">Exceeding output table size limit</INFO></RESOURCE></VOTABLE>'
        real=(ROOT/'research/updates/2026-11-15/gaia_gator.xml').read_bytes()
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'VANTAGE_RUNTIME':tmp}),patch('backend.surveys._bytes',side_effect=[(error,'https://irsa.ipac.caltech.edu/error'),(real,'https://irsa.ipac.caltech.edu/reduced'),(real,'https://irsa.ipac.caltech.edu/fast')]) as fetch:
            p=fetch_catalog('gaia',[210.,54.],.1)
            self.assertTrue(p['limited'])
            self.assertEqual(len(p['rows']),283)
            self.assertEqual(p['queried_radius_deg'],.05)
            self.assertEqual(len(p['query_urls']),2)
            self.assertEqual(fetch.call_count,3)

    def test_name_redirect_cannot_leave_the_official_host_allowlist(self):
        import tempfile,os
        from unittest.mock import patch,MagicMock
        from backend.surveys import resolve_name
        response=MagicMock()
        response.__enter__.return_value=response
        response.is_redirect=True
        response.headers={'Location':'https://unapproved.example/private'}
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'VANTAGE_RUNTIME':tmp}),patch('backend.surveys.requests.get',return_value=response) as get:
            with self.assertRaisesRegex(ValueError,'approved CDS mirror'):resolve_name('M101')
            self.assertEqual(get.call_count,1)

    def test_typed_routes_preserve_failure_and_old_coordinate_contract(self):
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from backend.app import app
        c=TestClient(app)
        self.assertEqual(c.get('/v1/targets/resolve?ra=360&dec=0').json()['center_deg'],[0.,0.])
        self.assertEqual(c.get('/v1/targets/resolve?name=M101&ra=0&dec=0').status_code,422)
        self.assertEqual(c.get('/v1/targets/resolve',params={'name':'a'*129}).status_code,422)
        with patch('backend.app.resolve_name',return_value={'center_deg':[210.8024292,54.34875],'frame':'ICRS'}):
            self.assertEqual(c.get('/v1/targets/resolve?name=M101').status_code,200)
        sequence=next(s for s in json.loads((ROOT/'public/prepared/catalog.json').read_text()) if s['key']=='m101')
        with patch('backend.survey_routes.layer',side_effect=ConnectionError('upstream failure')):
            self.assertEqual(c.get('/v1/surveys/wise',params={'sequence_id':sequence['id']}).status_code,502)
        self.assertEqual(c.get('/prepared/catalog.json').status_code,200)

if __name__=='__main__':unittest.main()
