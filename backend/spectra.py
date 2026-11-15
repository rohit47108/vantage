"""Bounded native extraction products with explicit incomplete sampling.

The first enabled target is the independently inspected retained P330E field.
This does not imply that a full six-detector/102-channel workflow is enabled.
ECSV units/masks: https://docs.astropy.org/en/stable/io/ascii/ecsv.html
"""
import hashlib
import io
import json
import os
import tempfile
from pathlib import Path
from typing import Literal
from xml.sax.saxutils import escape
from urllib.parse import urlencode
import numpy as np
import astropy
import photutils
import scipy
import astropy.units as u
from astropy.io import fits
from astropy.table import Table,MaskedColumn
from astropy.time import Time
from astropy.wcs import WCS
from scipy.ndimage import map_coordinates
from pydantic import BaseModel,ConfigDict,Field,model_validator
from backend.science import ROOT,digest,write_json,finite_list
from backend.photometry import measure_fits,POLICY as PHOTOMETRY_POLICY

POLICY='retained-native-source-samples-2'
BENCHMARK=ROOT/'research/updates/2026-11-15/photometry'


class SpectrumRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    target_key:Literal['p330e']='p330e'
    target_revision:str|None=Field(default=None,pattern=r'^[a-f0-9]{64}$')
    observation_indices:list[int]=Field(default_factory=lambda:[0,1,2,3],min_length=1,max_length=4)
    method:Literal['psf','aperture']='psf'
    refine_centroid:bool=True
    aperture_radius:float=Field(default=2.5,ge=1.5,le=3.5)
    background_inner:float=Field(default=5,ge=4.5,le=6)
    background_outer:float=Field(default=8,ge=7,le=10)

    @model_validator(mode='after')
    def geometry(self):
        if len(set(self.observation_indices))!=len(self.observation_indices) or any(i<0 or i>3 for i in self.observation_indices):
            raise ValueError('Choose distinct retained observation indices between 0 and 3')
        if self.aperture_radius>=self.background_inner or self.background_inner>=self.background_outer:
            raise ValueError('The background annulus must surround the source aperture')
        return self


def target_description():
    benchmark=json.loads((BENCHMARK/'benchmark.json').read_text(encoding='utf-8'))
    revision=hashlib.sha256(((BENCHMARK/'benchmark.json').read_text(encoding='utf-8')+(BENCHMARK/'fixture-manifest.json').read_text(encoding='utf-8')).encode()).hexdigest()
    return {'key':'p330e','name':'P330E','revision':revision,'source':benchmark['source'],
        'position_model':benchmark['source_position_model'],
        'sampling_description':'Four retained DR1 observations from detector D2. Partial wavelength coverage across separate acquisition dates.',
        'observations':[{k:r[k] for k in ['obs_id','detector','release','mjd_mid']}|{'index':i,'utc_mid':Time(r['mjd_mid'],format='mjd',scale='utc').isot+'Z'} for i,r in enumerate(benchmark['observations'])]}


def atomic_text(path,content):
    with tempfile.NamedTemporaryFile(dir=path.parent,mode='w',encoding='utf-8',newline='',delete=False) as handle:
        handle.write(content);temporary=handle.name
    os.replace(temporary,path)


def cutout_request(row):
    if row['retrieval_mode']!='native_ibe_cutout':
        raise ValueError('This retained workflow requires an explicitly recorded native IBE cutout derivation')
    parameters={'center':f"{row['position_deg'][0]},{row['position_deg'][1]}deg",
        'size':f"{row['cutout_fov_arcmin']/60*1.5}deg"}
    return {'parent_url':row['ibe'],'parameters':parameters,'url':row['ibe']+'?'+urlencode(parameters),
        'retrieval_mode':row['retrieval_mode'],'sha256':row['sha256'],
        'checksum_semantics':'Checksum identifies the retained native IBE cutout response, not the full parent exposure. Parameters record its native cutout geometry. Compare any refreshed response bytes with this retained checksum; upstream service availability is separate.'}


def native_sample(row,request,area_path):
    sample={k:row[k] for k in ['obs_id','detector','release','mjd_mid']}
    sample.update({'utc_mid':Time(row['mjd_mid'],format='mjd',scale='utc').isot+'Z',
        'source_url':row['ibe'],'source_sha256':row['sha256'],
        'native_cutout_request':cutout_request(row),
        'calibration_url':row['calibration_url'],'calibration_sha256':row['calibration_sha256'],
        'input_position_deg':row['position_deg'],'flux_ujy':None,'statistical_sigma_ujy':None,
        'wavelength_um':None,'bandwidth_um':None,'status':'rejected','reason':None})
    try:
        with fits.open(ROOT/row['path'],memmap=False) as image,fits.open(area_path,memmap=False) as area:
            header=image['IMAGE'].header
            if str(header['OBSID'])!=row['obs_id'] or int(header['DETECTOR'])!=row['detector']:
                raise ValueError('Native observation identity differs from its retained association')
            if abs(float(header['MJD-AVG'])-row['mjd_mid'])>1e-6:
                raise ValueError('Native acquisition time differs from its retained association')
            x,y=map(float,WCS(header).world_to_pixel_values(*row['position_deg']))
            measurement=measure_fits(image,area,x,y,method=request.method,refine_centroid=request.refine_centroid,
                aperture_radius=request.aperture_radius,background_inner=request.background_inner,background_outer=request.background_outer)
            px,py=measurement['position_pixel_xy'];parent_x,parent_y=px+1-header['CRPIX1A'],py+1-header['CRPIX2A']
            with fits.open(ROOT/row['calibration_path'],memmap=False) as calibration:
                wave=calibration['CWAVE'];width=calibration['CBAND']
                if int(wave.header['DETECTOR'])!=row['detector'] or int(width.header['DETECTOR'])!=row['detector']:
                    raise ValueError('Spectral calibration detector association differs')
                if u.Unit(wave.header['BUNIT'])!=u.um or u.Unit(width.header['BUNIT'])!=u.um:
                    raise ValueError('Spectral calibration units differ')
                sample['wavelength_um']=float(map_coordinates(wave.data,[[parent_y],[parent_x]],order=1,cval=np.nan)[0])
                sample['bandwidth_um']=float(map_coordinates(width.data,[[parent_y],[parent_x]],order=1,cval=np.nan)[0])
                if not np.isfinite([sample['wavelength_um'],sample['bandwidth_um']]).all() or sample['bandwidth_um']<=0:
                    raise ValueError('No finite calibrated wavelength at the measured source position')
            for key in ['flux_ujy','statistical_sigma_ujy','background_coefficients_mjysr','background_pixels',
                        'core_support_fraction','aperture_throughput','pixel_flags_union','epsf','position_pixel_xy',
                        'parameter_order','parameter_covariance','reduced_chi2','residual_expected_noise_dof']:
                value=measurement[key]
                sample[key]=value.tolist() if isinstance(value,np.ndarray) else value
            if 'centroid_fit' in measurement:
                sample['centroid_fit']={k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in measurement['centroid_fit'].items()}
            sample['status']='accepted' if measurement['reduced_chi2']<3 else 'diagnostic_only'
            sample['reason']=None if sample['status']=='accepted' else 'Source/background residual score exceeds the declared maximum of 3. Inspect the fit; excluded from the accepted-sample plot.'
            sample['image_context']={'shape':list(image['IMAGE'].data.shape),
                'brightness_mjysr':finite_list(np.asarray(image['IMAGE'].data,dtype=float)),
                'residual_ujy':finite_list(measurement['residual_ujy']),
                'used':measurement['used'].astype(int).tolist()}
    except (ValueError,IndexError,KeyError) as exc:
        sample.update({'status':'rejected','reason':str(exc),'flux_ujy':None,'statistical_sigma_ujy':None})
    return sample


def table_for_product(product):
    table=Table()
    samples=product['samples']
    for name,unit in [('mjd_mid',u.d),('wavelength_um',u.um),('bandwidth_um',u.um),('flux_ujy',u.uJy),
                      ('statistical_sigma_ujy',u.uJy),('reduced_chi2',None)]:
        values=[s.get(name) for s in samples]
        table[name]=MaskedColumn([float(v) if v is not None else 0. for v in values],mask=[v is None for v in values],unit=unit)
    for name in ['obs_id','utc_mid','detector','release','status','reason']:
        table[name]=[s.get(name) or '' for s in samples]
    table.meta={k:product[k] for k in ['id','policy','source','request','sampling','uncertainty_method','limitations','credits']}
    table.meta['time_scale']='UTC'
    table.meta['covariance_resource']='manifest.json: each sample contains its source/background parameter covariance and, when fitted, full centroid covariance with explicit parameter order.'
    table['reduced_chi2'].description='Residual sum normalized by its expected noise value from R C R^T; not a discovery p-value.'
    return table


def spectrum_svg(product,x_bounds=None,title=None):
    accepted=[s for s in product['samples'] if s['status']=='accepted']
    width,height=780,390
    left,right,top,bottom=115,745,75,280
    low_x,high_x=x_bounds or (1.05,1.7)
    display_title=escape(title or 'P330E')
    sampling_label='Partial native sampling' if x_bounds else 'Partial D2 sampling'
    coverage_label='Individual native exposures' if x_bounds else 'Partial D2 coverage'
    high_y=max([s['flux_ujy']+s['statistical_sigma_ujy']*3 for s in accepted]+[1.])*1.15
    low_y=min([s['flux_ujy']-s['statistical_sigma_ujy']*3 for s in accepted]+[0.])
    def x(v):return left+(v-low_x)/(high_x-low_x)*(right-left)
    def y(v):return bottom-(v-low_y)/(high_y-low_y)*(bottom-top)
    elements=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">Vantage — {display_title} native source samples</title>',
        f'<desc id="desc">{sampling_label} at separate acquisition times. Only samples passing residual checks are plotted. Error bars are one statistical standard deviation. Horizontal bars are calibrated CBAND, not an exact response curve.</desc>',
        '<rect width="100%" height="100%" fill="#09151a"/>','<g fill="#e3efeb" font-family="sans-serif" font-size="14">',
        f'<text x="35" y="30" font-size="20">Vantage · {display_title} source samples</text>',
        f'<text x="35" y="53">{coverage_label} · separate acquisition times · statistical errors only</text>',
        f'<path d="M {left} {top} V {bottom} H {right}" fill="none" stroke="#b7cbc4"/>']
    for tick in ([1,2,3,4,5] if x_bounds else [1.1,1.3,1.5,1.65]):
        elements.append(f'<text x="{x(tick):.2f}" y="302" text-anchor="middle">{tick}</text>')
    for value in np.linspace(low_y,high_y,5):
        elements.append(f'<text x="105" y="{y(value)+5:.2f}" text-anchor="end">{value:.0f}</text>')
    for sample in accepted:
        px,py=x(sample['wavelength_um']),y(sample['flux_ujy']);sigma=sample['statistical_sigma_ujy']
        a,b=y(sample['flux_ujy']-sigma),y(sample['flux_ujy']+sigma)
        lo,hi=x(sample['wavelength_um']-sample['bandwidth_um']/2),x(sample['wavelength_um']+sample['bandwidth_um']/2)
        elements.append(f'<g stroke="#7ee4c2" fill="#7ee4c2"><path d="M {px:.2f} {a:.2f} V {b:.2f} M {lo:.2f} {py:.2f} H {hi:.2f}"/><circle cx="{px:.2f}" cy="{py:.2f}" r="5"><title>{escape(sample["obs_id"])} · {sample["utc_mid"]} · {sample["flux_ujy"]:.2f} ± {sigma:.2f} microJy</title></circle></g>')
    if not accepted:elements.append('<text x="150" y="170">No sample passes the fit checks in this selection.</text>')
    elements.extend(['<text x="390" y="329" text-anchor="middle">Wavelength (µm) · horizontal bars: CBAND</text>',
        '<text transform="translate(23 195) rotate(-90)" text-anchor="middle">Flux density (µJy)</text>',
        f'<text x="35" y="356">{len(accepted)} passing / {len(product["samples"])} requested · {escape(product["request"]["method"])} · no connecting lines</text>',
        '<text x="35" y="379" font-size="11">NASA / JPL-Caltech / Caltech-IPAC · Gaia / ESA · see provenance JSON for input hashes and limitations</text></g></svg>'])
    return ''.join(elements)


def build_spectrum(request,destination,check_cancel=lambda:None):
    if request.target_revision and request.target_revision!=target_description()['revision']:
        raise ValueError('The retained target metadata changed. Reload the target before extracting.')
    benchmark=json.loads((BENCHMARK/'benchmark.json').read_text(encoding='utf-8'))
    registry=json.loads((BENCHMARK/'fixture-manifest.json').read_text(encoding='utf-8'))['files']
    rows=[benchmark['observations'][i] for i in sorted(request.observation_indices)]
    requested_paths={r[k] for r in rows for k in ['path','calibration_path']}
    requested_paths.add(str((BENCHMARK/'sapm_d2.fits').relative_to(ROOT)).replace('\\','/'))
    inputs=[]
    for path in sorted(requested_paths):
        check_cancel()
        match=next((r for r in registry if r['path']==path),None)
        if not match or digest(ROOT/path)!=match['sha256']:raise ValueError('Retained native/calibration checksum does not match the approved fixture registry')
        inputs.append(match)
    for row in rows:
        if next(r for r in inputs if r['path']==row['path'])['sha256']!=row['sha256'] or next(r for r in inputs if r['path']==row['calibration_path'])['sha256']!=row['calibration_sha256']:
            raise ValueError('Retained observation/calibration checksum associations differ')
    canonical={'policy':POLICY,'photometry_policy':PHOTOMETRY_POLICY,
        'request':request.model_dump()|{'observation_indices':sorted(request.observation_indices)},
        'source':benchmark['source'],'position_model':benchmark['source_position_model'],
        'observations':[{k:r[k] for k in ['obs_id','detector','release','mjd_mid','position_deg','sha256','calibration_sha256','cutout_fov_arcmin','retrieval_mode']}|{'native_cutout_request':cutout_request(r)} for r in rows],
        'inputs':inputs,'residual_score_maximum':3.,
        'software':{'numpy':np.__version__,'scipy':scipy.__version__,'astropy':astropy.__version__,'photutils':photutils.__version__}}
    identity=hashlib.sha256(json.dumps(canonical,sort_keys=True,allow_nan=False).encode()).hexdigest()
    samples=[]
    for row in rows:
        check_cancel();samples.append(native_sample(row,request,BENCHMARK/'sapm_d2.fits'))
    check_cancel()
    counts={state:sum(s['status']==state for s in samples) for state in ['accepted','diagnostic_only','rejected']}
    product={'schema_version':'1.0.0','id':identity,'type':'source_samples','name':'P330E · native source samples',**canonical,
        'data_status':'retained_authentic_benchmark','science_status':'conditional_isolated_point_source_samples',
        'complete_102_channel_spectrum':False,'samples':samples,
        'sampling':{'available_observations':len(benchmark['observations']),'selected_observation_indices':sorted(request.observation_indices),
            'unselected_observations':len(benchmark['observations'])-len(rows),'accepted_samples':counts['accepted'],
            'diagnostic_only_samples':counts['diagnostic_only'],'rejected_samples':counts['rejected'],
            'detectors':[2],'mjd_range':[min(r['mjd_mid'] for r in rows),max(r['mjd_mid'] for r in rows)],
            'interpretation':'Partial retained D2 sampling. Each point has its own observation time and central CWAVE/CBAND. Unobserved channels are not inferred or zero-filled.'},
        'units':'uJy','uncertainty_method':'Native independent-pixel statistical covariance, including fitted local background and optional centroid/source cross covariance. Common calibration, native correlations and PSF/model errors are not supplied and are excluded.',
        'limitations':['This first workflow enables the retained P330E D2 test field only; arbitrary fields and six-detector/102-channel extraction remain pending.',
            'Samples at different acquisition times are not an instantaneous spectrum. No wavelength binning or time averaging is performed.',
            'Accepted means the stated mask/coverage/fit checks pass. It is not a probability of detection, identity, isolation or a claim of discovery.',
            'Point-source flux uses the finite calibrated ePSF convention; unknown outer wings are not invented. No deblending or extended-source measurements.',
            'Wavelength bars use central CWAVE/CBAND at the fitted source position; they do not encode the full response variation over the native estimator.',
            'Gaia angular motion omits observer parallax and perspective acceleration. The small parallax for this benchmark is documented in the source record.',
            'No clipping, separate ZODI subtraction or common calibration-error estimate. Signed fluxes and statistical errors are retained, with no automatic upper-limit claims.'],
        'credits':'SPHEREx: NASA/JPL-Caltech/Caltech-IPAC, IRSA; Gaia DR3: ESA/Gaia/DPAC, mirrored at IRSA. P330E isolation and CALSPEC consistency evidence: research/updates/2026-11-15/photometry/METHODS.md.'}
    folder=Path(destination)/identity;folder.mkdir(parents=True,exist_ok=True)
    table=table_for_product(product)
    for format,name in [('ascii.ecsv','samples.ecsv'),('ascii.csv','samples.csv')]:
        buffer=io.StringIO();table.write(buffer,format=format);atomic_text(folder/name,buffer.getvalue())
    atomic_text(folder/'plot.svg',spectrum_svg(product))
    product['exports']={name:{'url':f'/v1/products/{identity}/{name}','sha256':digest(folder/name)} for name in ['samples.ecsv','samples.csv','plot.svg']}
    check_cancel();write_json(folder/'manifest.json',product)
    return product
