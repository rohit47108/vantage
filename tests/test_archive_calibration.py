import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import requests
from backend.archive import allowed,calibration


class CalibrationAccessTests(unittest.TestCase):
    def test_additive_discovery_schema_preserves_fresh_legacy_cache(self):
        import hashlib,json
        from backend.archive import discover
        center=[11.,22.];fov=3
        key=hashlib.sha256(json.dumps([center,fov,'dr1-qr3-20261114']).encode()).hexdigest()
        saved={'center_deg':center,'fov_arcmin':fov,'observations':[],'search_completeness':'complete','queries':[],
            'coverage_state':'empty','visit_count':0,'retrieved_utc':'2026-11-15T08:00:00+00:00','data_status':'live'}
        with tempfile.TemporaryDirectory() as directory,patch('backend.archive.CACHE',Path(directory)),patch('backend.archive.requests.get',side_effect=AssertionError('Fresh existing metadata must not require a forced cold query')):
            (Path(directory)/(key+'.json')).write_text(json.dumps(saved))
            result=discover(center,fov)
        self.assertEqual(result['data_status'],'cached')
        self.assertEqual(result['collections'],['spherex_dr1','spherex_qr3'])

    def test_only_official_calibration_mirror_paths_are_allowed(self):
        good='https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/dr1/spectral_wcs/cal-swcs-v5-2026-191/2/spectral_wcs_D2_spx_cal-swcs-v5-2026-191.fits'
        self.assertEqual(allowed(good),good)
        for url in [good.replace('nasa-irsa-spherex','another-bucket'),good.replace('/dr1/','/private/'),
                    good.replace('/spectral_wcs/','/level2/'),good.replace('https://','http://'),
                    good.replace('/dr1/','/dr1/../'),good.replace('https://','https://user@')]:
            with self.assertRaises(ValueError):allowed(url)

    def test_datalink_association_survives_on_prem_calibration_failure(self):
        xml=b'''<VOTABLE version="1.3" xmlns="http://www.ivoa.net/xml/VOTable/v1.3"><RESOURCE type="results"><TABLE><FIELD name="access_url" datatype="char" arraysize="*"/><DATA><TABLEDATA><TR><TD>https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/spectral_wcs/cal-swcs-v5-2026-191/1/spectral_wcs_D1_spx_cal-swcs-v5-2026-191.fits</TD></TR></TABLEDATA></DATA></TABLE></RESOURCE></VOTABLE>'''
        with tempfile.TemporaryDirectory() as directory:
            table=Path(directory)/'links.xml';table.write_bytes(xml)
            fits=Path(directory)/'map.fits';fits.write_bytes(b'retained-test-placeholder')
            with patch('backend.archive.retrieve',side_effect=[table,requests.HTTPError('upstream 502'),fits]) as retrieve:
                url,path=calibration({'publisher_id':'ivo://irsa.ipac/spherex_dr1?test/D1'})
            self.assertEqual(path,fits)
            self.assertTrue(url.startswith('https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/spectral_wcs/'))
            self.assertEqual(retrieve.call_args_list[-1].args[0],url.replace('https://irsa.ipac.caltech.edu/ibe/data/spherex/','https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/'))

    def test_source_discovery_queries_deep_collections_and_time_with_retries(self):
        import os
        from astropy.table import Table
        from backend.archive import discover
        from unittest.mock import MagicMock
        response=MagicMock();response.__enter__.return_value=response
        response.iter_content.return_value=[b'retained-protocol-fixture'];response.url='https://irsa.ipac.caltech.edu/SIA'
        table=Table({'access_url':['https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/example.fits'],
            'obs_id':['physical-exposure'],'obs_publisher_did':['ivo://example/physical-exposure'],
            'energy_bandpassname':['SPHEREx-D1'],'t_min':[60000.],'t_max':[60000.001],'em_min':[.8e-6],'em_max':[1.1e-6]})
        response.status_code=200
        with tempfile.TemporaryDirectory() as directory,patch('backend.archive.CACHE',Path(directory)),patch('backend.archive.requests.get',side_effect=[requests.ConnectionError('temporary'),response,response,response,response]) as get,patch('backend.archive.votable',return_value=(table,False)),patch('backend.archive.time.sleep'):
            result=discover([10.,20.],2,refresh=True,include_deep=True,time_bounds=[59999,60001])
        collections=[call.kwargs['params']['COLLECTION'] for call in get.call_args_list]
        self.assertEqual(set(collections),{'spherex_dr1','spherex_qr3','spherex_dr1_deep','spherex_qr3_deep'})
        self.assertEqual(get.call_args_list[-1].kwargs['params']['TIME'],'59999 60001')
        self.assertEqual(len(result['observations']),1)
        self.assertEqual(result['observations'][0]['release'],'dr1')
        self.assertEqual(result['collections'],['spherex_dr1','spherex_qr3','spherex_dr1_deep','spherex_qr3_deep'])


if __name__=='__main__':unittest.main()
