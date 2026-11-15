import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from backend.science import ROOT
from backend.native_extraction import SourcePosition
from backend.source_fields import SourceFieldRequest,NativeExtractionRequest,build_source_field


class SourceFieldTests(unittest.TestCase):
    def test_real_metadata_subset_keeps_completeness_dates_and_capabilities(self):
        acquisition=json.loads((ROOT/'research/updates/2026-11-15/native-extraction/acquisition.json').read_text())
        source=SourcePosition(ra=acquisition['source']['ra'],dec=acquisition['source']['dec'])
        request=SourceFieldRequest(source=source,start_utc=date(2025,7,1),end_utc=date(2025,7,31))
        found={'observations':acquisition['observations'],'search_completeness':'limited','collections':['spherex_dr1'],
            'queries':[r['ibe'] for r in acquisition['observations']],'data_status':'retained_metadata_subset'}
        with tempfile.TemporaryDirectory() as directory,patch('backend.source_fields.discover',return_value=found) as discover:
            result=build_source_field(request,Path(directory))
            self.assertEqual(result['type'],'source_field')
            self.assertEqual(result['search_completeness'],'limited')
            self.assertEqual(result['candidate_observations'],6)
            self.assertEqual(result['approved_releases'],['dr1'])
            self.assertTrue(discover.call_args.kwargs['include_deep'])
            self.assertEqual(result['request']['end_utc'],'2025-07-31')
            self.assertTrue((Path(directory)/result['id']/'manifest.json').is_file())

    def test_date_selection_and_extraction_bounds(self):
        with self.assertRaises(ValueError):SourceFieldRequest(source=SourcePosition(ra=0,dec=0),start_utc='2026-10-01',end_utc='2025-01-01')
        for change in [{'field_id':'../bad','observation_indices':[0]},
                       {'field_id':'a'*64,'observation_indices':[0,0]},
                       {'field_id':'a'*64,'observation_indices':[2000]},
                       {'field_id':'a'*64,'observation_indices':list(range(513))}]:
            with self.assertRaises(ValueError):NativeExtractionRequest(**change)
        request=SourceFieldRequest(source=SourcePosition(ra=0,dec=0))
        self.assertRegex(request.model_dump(mode='json')['end_utc'],r'^\d{4}-\d{2}-\d{2}$')

    def test_outage_fallback_requires_a_genuine_enclosing_snapshot(self):
        import requests
        from backend.source_fields import retained_snapshot
        acquisition=json.loads((ROOT/'research/updates/2026-11-15/native-extraction/acquisition.json').read_text())
        snapshot={'center_deg':[247.8908392831,30.14604947207],'fov_arcmin':2.5,
            'observations':acquisition['observations'],'search_completeness':'complete','queries':['https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1'],
            'retrieved_utc':'2026-11-15T08:23:00+00:00','data_status':'live'}
        with tempfile.TemporaryDirectory() as directory,patch('backend.archive.CACHE',Path(directory)):
            (Path(directory)/'actual-snapshot.json').write_text(json.dumps(snapshot))
            result=retained_snapshot([247.8908392831,30.14604947207],1.1,[60857,60888])
            self.assertEqual(result['search_completeness'],'limited')
            self.assertEqual(result['data_status'],'retained_metadata_snapshot')
            self.assertEqual(result['snapshot_original_completeness'],'complete')
            self.assertIsNone(retained_snapshot([239.8,47.6],1.1,[60857,60888]))
            source=SourcePosition(ra=snapshot['center_deg'][0],dec=snapshot['center_deg'][1])
            with patch('backend.source_fields.discover',side_effect=requests.HTTPError('upstream 502')):
                field=build_source_field(SourceFieldRequest(source=source,start_utc='2025-07-01',end_utc='2025-07-31'),Path(directory)/'products')
            self.assertEqual(field['discovery']['data_status'],'retained_metadata_snapshot')


if __name__=='__main__':unittest.main()
