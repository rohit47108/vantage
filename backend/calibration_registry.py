"""Explicitly approved native calibration associations, never newest-file lookup.

Reference exposure HISTORY UUIDs are paired with actual DataLink responses.
SAPM selection follows the current official IRSA source-discovery notebook.
https://caltech-ipac.github.io/irsa-tutorials/spherex-source-discovery-tool-demo/
"""
import gzip
import hashlib
import json
import re
from pathlib import Path
from backend.science import ROOT,digest

REGISTRY=ROOT/'config/scientific_calibrations.json'


def registry():
    result=json.loads(REGISTRY.read_text(encoding='utf-8'))
    if result['schema_version']!='1.0.0':raise ValueError('Unsupported approved calibration registry schema')
    return result


def approved_binding(image,release,approved=None):
    detector=int(image['IMAGE'].header['DETECTOR'])
    matches=[r for r in (approved or registry())['bindings'] if r['release']==release and r['detector']==detector]
    if len(matches)!=1:raise ValueError('No approved native calibration binding for this release/detector')
    entry=matches[0]
    if str(image[0].header.get('VERSION','')) not in entry['processing_versions']:
        raise ValueError('Native processing version has not passed the approved calibration checks')
    if 'EPSF' not in image or str(image['EPSF'].header.get('DETCOORD','')).strip()!='sky':
        raise ValueError('Native effective-PSF orientation has not been approved')
    if str(image['IMAGE'].header.get('DETCOORD','')).strip()!='sky':
        raise ValueError('Native image orientation has not been approved')
    if int(image['EPSF'].header['DETECTOR'])!=detector:raise ValueError('Native effective-PSF detector association differs')
    history='\n'.join(image['IMAGE'].header.get('HISTORY',[]))
    for kind in ['spectral_wcs','sip','epsf']:
        identities=set(re.findall(r'\[CALIB\] '+kind+r' ([a-f0-9-]{36})',history))
        if identities!={entry['calibration_ids'][kind]}:
            raise ValueError(f'Native {kind} calibration association has not been approved')
    return entry


def verified_path(artifact,verified=None):
    path=(ROOT/artifact['path']).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        raise ValueError('Approved calibration is unavailable in the scientific package')
    key=(str(path),artifact['sha256'],artifact['original_fits_sha256'])
    if verified is not None and key in verified:return path
    if digest(path)!=artifact['sha256']:raise ValueError('Approved calibration checksum differs')
    # Gzip retains the original FITS bytes exactly; no pixel quantization or
    # precision loss. Bound decoded bytes before verifying the original hash.
    stream=gzip.open(path,'rb') if path.suffix=='.gz' else path.open('rb')
    checksum=hashlib.sha256();size=0
    with stream:
        while chunk:=stream.read(1_048_576):
            size+=len(chunk)
            if size>40_000_000:raise ValueError('Approved calibration exceeds the decoded work limit')
            checksum.update(chunk)
    if checksum.hexdigest()!=artifact['original_fits_sha256']:
        raise ValueError('Original FITS calibration checksum differs after decompression')
    if verified is not None:verified.add(key)
    return path
