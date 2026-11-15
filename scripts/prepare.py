"""Run from workspace root: python -m scripts.prepare."""
import json
from pathlib import Path
from backend.science import ROOT, build_sequence, digest, write_json


def prepare():
    data = json.loads((ROOT / 'demo_dataset_manifest.json').read_text(encoding='utf-8'))
    for record in data['files']:
        path = ROOT / record['path']
        if digest(path) != record['sha256']:
            raise ValueError(f'Fixture checksum failed: {path.name}')
    destination = ROOT / 'public/prepared'
    catalog = []
    for key, benchmark in data['full_challenge_benchmarks'].items():
        manifest = build_sequence(key, benchmark['name'], benchmark['center_deg'], 6,
                                  benchmark['sequence'], destination, benchmark['notes'])
        catalog.append(manifest)
        print(key, manifest['id'][:12], manifest['joint_support_fraction'], flush=True)
    extra = {
        'm101': ('M101', [210.80227, 54.34895], 'Matching at the center leaves a restricted wavelength-compatible footprint.'),
        'ceres': ('Ceres', [15.636366, -5.468931], 'Positional motion control. Different passbands disable brightness comparison.'),
        'comet': ('3I/ATLAS', [248.599626795, -17.027980660], 'Source-tracked thumbnails. Each frame has a different sky center.'),
    }
    files = {Path(f['path']).name: f for f in data['files']}
    for key, (name, center, note) in extra.items():
        records = []
        for suffix in ('a', 'b'):
            filename = f'{key}_epoch_{suffix}.fits'
            file = files[filename]
            motion = next((r for r in data['motion_fixtures'] if r['fixture'] == filename), {})
            detector = 3 if key == 'comet' else 2
            records.append({'fixture': str(ROOT / file['path']), 'source_calibration': str(ROOT / f'research/fixtures/spectral_wcs_d{detector}.fits'),
                            'url': file['retrieval']['url'], 'predicted_target_deg': [motion['ra_deg'], motion['dec_deg']] if motion else None,
                            'retrieval_mode': file['retrieval'].get('mode', 'direct_ibe_native_cutout'),
                            'source_calibration_url': files[f'spectral_wcs_d{detector}.fits']['retrieval']['url']})
        manifest = build_sequence(key, name, center, 6, records, destination, note, tracked=key == 'comet')
        catalog.append(manifest)
        print(key, manifest['id'][:12], manifest['joint_support_fraction'], flush=True)
    write_json(destination / 'catalog.json', catalog)


if __name__ == '__main__':
    prepare()
