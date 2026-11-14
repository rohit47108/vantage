"""Fixed-grid visual processing. Numerical photometry is deliberately gated.

WCS API: https://docs.astropy.org/en/stable/wcs/wcsapi.html
Calibration semantics: https://irsa.ipac.caltech.edu/data/SPHEREx/docs/spherex_spectral_calibrations.html
"""
from pathlib import Path
import hashlib
import json
import os
import tempfile

import numpy as np
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS
from scipy.ndimage import map_coordinates

ROOT = Path(__file__).resolve().parents[1]
BAD_BITS = [0, 1, 2, 4, 5, 6, 7, 9, 10, 11, 12, 14, 15, 17, 19, 20, 22, 23, 24, 25, 26, 27, 28, 29]
BAD_MASK = sum(1 << bit for bit in BAD_BITS)
POLICY = 'vantage-visual-1'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    """Atomic publication, including Windows readers."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, mode='w', encoding='utf-8', delete=False) as handle:
        json.dump(value, handle, allow_nan=False, separators=(',', ':'))
        temp = handle.name
    os.replace(temp, path)


def sample(array, x, y, fill=np.nan, order=1):
    return map_coordinates(array, [y, x], order=order, mode='constant', cval=fill)


def grid(center, fov, size=None):
    size = size or min(512, max(16, int(np.ceil(fov * 60 / 6.15))))
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ['RA---TAN', 'DEC--TAN']
    wcs.wcs.crval = center
    wcs.wcs.crpix = [(size + 1) / 2] * 2
    wcs.wcs.cdelt = [-fov / (60 * size), fov / (60 * size)]
    wcs.wcs.radesys = 'ICRS'
    return wcs, size


def plane(record, output, size):
    yy, xx = np.indices((size, size), dtype=float)
    ra, dec = output.pixel_to_world_values(xx, yy)
    with fits.open(record['fixture'], memmap=False) as hdus:
        image = hdus['IMAGE']
        header = image.header
        spatial = WCS(header)
        x, y = spatial.world_to_pixel_values(ra, dec)
        raw = np.array(image.data, dtype=float)
        variance = np.array(hdus['VARIANCE'].data, dtype=float)
        flags = np.array(hdus['FLAGS'].data, dtype=np.uint32)
        if not all(hdus[name].data.shape == raw.shape for name in ('FLAGS', 'VARIANCE', 'ZODI')):
            raise ValueError('Ancillary layer shape mismatch')
        if record.get('obs_id') and header['OBSID'] != record['obs_id']:
            raise ValueError('Observation identity mismatch')
        brightness = sample(raw, x, y)
        good = np.isfinite(raw) & np.isfinite(variance) & (variance > 0) & ((flags & BAD_MASK) == 0)
        support = sample(good.astype(float), x, y, 0) >= 1 - 1e-8
        nearest_flags = sample(flags.astype(float), x, y, 0, order=0).astype(np.uint32)
        px = x + 1 - header['CRPIX1A']
        py = y + 1 - header['CRPIX2A']
        # Independent handles and eager copies avoid lazy FITS shared-handle races.
        with fits.open(record['source_calibration'], memmap=False) as calibration:
            wave_map = np.array(calibration['CWAVE'].data, dtype=float)
            width_map = np.array(calibration['CBAND'].data, dtype=float)
            if calibration['CWAVE'].header['DETECTOR'] != header['DETECTOR']:
                raise ValueError('Calibration detector mismatch')
        wave = sample(wave_map, px, py)
        width = sample(width_map, px, py)
        predicted = record.get('predicted_target_deg')
        target = predicted or list(output.wcs.crval)
        tx, ty = spatial.world_to_pixel_values(*target)
        dx, dy = tx + 1 - header['CRPIX1A'], ty + 1 - header['CRPIX2A']
        local_wave = float(sample(wave_map, np.array([dx]), np.array([dy]))[0])
        local_width = float(sample(width_map, np.array([dx]), np.array([dy]))[0])
        prediction_pixel = list(map(float, output.world_to_pixel_values(*predicted))) if predicted else None
        meta = {
            'obs_id': header['OBSID'], 'detector': header['DETECTOR'],
            'mjd_mid': header['MJD-AVG'], 'utc_mid': Time(header['MJD-AVG'], format='mjd', scale='utc').isot + 'Z',
            'release': record.get('release', 'qr2'), 'unit': header.get('BUNIT', 'MJy/sr'),
            'wavelength_um': local_wave if np.isfinite(local_wave) else None,
            'bandwidth_um': local_width if np.isfinite(local_width) else None,
            'wavelength_reference_deg': target, 'prediction_pixel': prediction_pixel,
            'source_url': record.get('ibe', record.get('url')),
            'source_sha256': digest(record['fixture']),
            'calibration_url': record.get('source_calibration_url'),
            'calibration_sha256': digest(record['source_calibration']),
            'processing_version': header.get('PIPE_VER', header.get('VERSION', 'See source FITS')),
            'finite_fraction': float(np.isfinite(brightness).mean()),
            'good_fraction': float(support.mean()), 'core_flag_bits': record.get('core_flag_bits', []),
            'ancillary_hdus': [h.name for h in hdus],
        }
    return brightness, support, wave, width, nearest_flags, ra, dec, meta


def finite_list(array):
    return np.where(np.isfinite(array), array, None).tolist()


def build_sequence(key, name, center, fov, records, destination, note='', data_status='prepared', tracked=False):
    output, size = grid(center, fov)
    records = sorted(records, key=lambda record: fits.getheader(record['fixture'], 'IMAGE')['MJD-AVG'])
    planes = []
    frame_grids = []
    for record in records:
        frame_grid = grid(record['predicted_target_deg'], fov, size)[0] if tracked else output
        planes.append(plane(record, frame_grid, size))
        frame_grids.append(dict(frame_grid.to_header()))
    waves = np.array([p[2] for p in planes])
    widths = np.array([p[3] for p in planes])
    finite = np.logical_and.reduce([np.isfinite(p[0]) for p in planes])
    spectral = np.isfinite(waves).all(axis=0) & np.isfinite(widths).all(axis=0)
    spectral &= np.min(widths, axis=0) > 0
    spectral &= np.ptp(waves, axis=0) <= .1 * np.min(widths, axis=0)
    spectral &= np.max(widths, axis=0) <= 1.1 * np.min(widths, axis=0)
    joint = spectral & finite & np.logical_and.reduce([p[1] for p in planes])
    if tracked:
        joint[:] = False
    values = np.concatenate([p[0][p[1] & np.isfinite(p[0])] for p in planes])
    if not len(values):
        values = np.concatenate([p[0][np.isfinite(p[0])] for p in planes])
    if not len(values):
        raise ValueError('Selected frames do not cover the requested field')
    low, high = np.percentile(values, [2, 99.5])
    span = max(float(high - low), 1e-10)
    sources = [p[-1] for p in planes]
    identity = {'policy': POLICY, 'grid': dict(output.to_header()), 'sources': sources, 'tracked': tracked}
    sequence_id = hashlib.sha256(json.dumps(identity, sort_keys=True, allow_nan=False).encode()).hexdigest()
    folder = Path(destination) / sequence_id
    folder.mkdir(parents=True, exist_ok=True)
    frames = []
    for index, p in enumerate(planes):
        brightness, good, wave, width, flags, ra, dec, meta = p
        pixels = np.clip(np.arcsinh((brightness - low) / (span / 8)) / np.arcsinh(8), 0, 1)
        asset = {
            'shape': [size, size], 'pixels': finite_list(pixels), 'brightness': finite_list(brightness),
            'coverage': np.isfinite(brightness).astype(int).tolist(), 'quality': good.astype(int).tolist(),
            'spectral': (spectral & finite).astype(int).tolist(), 'joint': joint.astype(int).tolist(),
            'wavelength': finite_list(wave), 'bandwidth': finite_list(width),
            'flags': flags.astype('uint64').tolist(), 'ra': finite_list(ra), 'dec': finite_list(dec),
        }
        path = folder / f'frame-{index}.json'
        write_json(path, asset)
        frames.append(meta | {'asset': f'/prepared/{sequence_id}/{path.name}', 'asset_sha256': digest(path),
                              'grid': frame_grids[index]})
    count = len(frames)
    fraction = float(joint.mean())
    manifest = {
        'schema_version': '1.0.0', 'id': sequence_id, 'key': key, 'name': name,
        'center_deg': center, 'fov_arcmin': fov, 'grid': dict(output.to_header()), 'shape': [size, size],
        'frames': frames, 'data_status': data_status, 'policy': POLICY,
        'mode': 'source_tracked' if tracked else 'fixed_sky',
        'coverage_state': 'single' if count == 1 else 'pair' if count == 2 else 'sequence',
        'search_completeness': 'limited',
        'science_status': 'restricted_visual' if fraction > 0 else 'context_only',
        'joint_support_fraction': fraction, 'numerical_products_authorized': False,
        'stretch': {'low': float(low), 'high': float(high), 'transfer': 'shared_asinh'},
        'limitations': [note, 'Visual WCS alignment. Precision registration, PSF matching and uncertainty validation are pending.',
                        'Brightness differences and detection significance are unavailable for this sequence.'],
        'credits': (ROOT / 'required_acknowledgments.txt').read_text(),
        'software': {'astropy': __import__('astropy').__version__, 'numpy': np.__version__},
    }
    write_json(folder / 'manifest.json', manifest)
    return manifest
