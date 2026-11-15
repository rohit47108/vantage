"""General native DR1 point-source measurements, with explicit validity gates.

Caller-owned discovery and observation selection are separate from extraction.
No measurement is derived from the visualization cube or resampled sky planes.
"""
import hashlib
import io
import json
from contextlib import ExitStack
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode
import requests
import numpy as np
import astropy
import scipy
import photutils
import astropy.units as u
from astropy.io import fits
from astropy.wcs import WCS
from astropy.time import Time
from pydantic import BaseModel,ConfigDict,Field,model_validator
from scipy.ndimage import map_coordinates
from backend.science import digest,finite_list,write_json
from backend.archive import native_cutout
from backend.surveys import propagate_gaia
from backend.photometry import measure_fits,solid_angle_for_image,POLICY as PHOTOMETRY_POLICY
from backend.calibration_registry import approved_binding,registry,verified_path
from backend.spectra import table_for_product,atomic_text,spectrum_svg

POLICY='native-observation-extraction-1'


class SourcePosition(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    name:str=Field(default='Selected sky position',min_length=1,max_length=100)
    ra:float=Field(ge=0,lt=360)
    dec:float=Field(ge=-90,le=90)
    ref_epoch:float=Field(default=2016,ge=1900,le=2100)
    pmra:float|None=Field(default=None,ge=-12000,le=12000)
    pmdec:float|None=Field(default=None,ge=-12000,le=12000)

    @model_validator(mode='after')
    def motion(self):
        if (self.pmra is None)!=(self.pmdec is None):raise ValueError('Supply both angular-motion components, or use a fixed ICRS coordinate')
        if any(ord(c)<32 for c in self.name):raise ValueError('Source names must not contain control characters')
        return self

    def position(self,mjd):
        if self.pmra is None:return [self.ra,self.dec]
        return list(map(float,propagate_gaia(self.model_dump(),mjd)[:2]))


class ExtractionOptions(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    method:Literal['psf','aperture']='psf'
    centroid_mode:Literal['fixed','auto']='auto'
    aperture_radius:float=Field(default=2.5,ge=1.5,le=3.5)
    background_inner:float=Field(default=5,ge=4.5,le=6)
    background_outer:float=Field(default=8,ge=7,le=10)

    @model_validator(mode='after')
    def geometry(self):
        if self.aperture_radius>=self.background_inner or self.background_inner>=self.background_outer:
            raise ValueError('The background annulus must surround the source aperture')
        return self


def pixel_area(wcs,x,y):
    """Spherical area of the four native WCS pixel corners; diagnostic only."""
    ra,dec=np.deg2rad(wcs.pixel_to_world_values(np.array([x-.5,x+.5,x+.5,x-.5]),np.array([y-.5,y-.5,y+.5,y+.5])))
    v=np.column_stack([np.cos(dec)*np.cos(ra),np.cos(dec)*np.sin(ra),np.sin(dec)])
    def triangle(a,b,c):return 2*np.arctan2(abs(np.dot(a,np.cross(b,c))),1+np.dot(a,b)+np.dot(b,c)+np.dot(c,a))
    return triangle(v[0],v[1],v[2])+triangle(v[0],v[2],v[3])


def measure_native(image,calibration,area,position,options):
    header=image['IMAGE'].header;wcs=WCS(header)
    x,y=map(float,wcs.world_to_pixel_values(*position));height,width=image['IMAGE'].data.shape
    if not np.isfinite([x,y]).all() or not (0<=x<width and 0<=y<height):raise ValueError('Native cutout does not cover the requested source position')
    omega=solid_angle_for_image(area,header,(height,width))
    ix,iy=int(round(x)),int(round(y))
    if not (0<=ix<width and 0<=iy<height):raise ValueError('Source falls outside a complete native center pixel')
    ratio=float(omega[iy,ix]/pixel_area(wcs,ix,iy))
    if not np.isfinite(ratio) or abs(ratio-1)>.001:raise ValueError('Calibrated pixel area and native WCS disagree by more than 0.1 percent')
    if str(area['IMAGE'].header.get('DETCOORD',''))!='sky' or str(calibration['CWAVE'].header.get('DETCOORD',''))!='sky':
        raise ValueError('Native calibration orientation is not approved')
    geometry={k:getattr(options,k) for k in ['aperture_radius','background_inner','background_outer']}
    refine=False
    if options.centroid_mode=='auto':
        initial=measure_fits(image,area,x,y,method='psf',refine_centroid=False,**geometry)
        refine=initial['flux_ujy']/initial['statistical_sigma_ujy']>=20
    result=measure_fits(image,area,x,y,method=options.method,refine_centroid=refine,**geometry)
    px,py=result['position_pixel_xy'];parent_x,parent_y=px+1-header['CRPIX1A'],py+1-header['CRPIX2A']
    for name in ['CWAVE','CBAND']:
        if int(calibration[name].header['DETECTOR'])!=int(header['DETECTOR']) or u.Unit(calibration[name].header['BUNIT'])!=u.um:
            raise ValueError('Native wavelength calibration detector or units differ')
    wave,width=[float(map_coordinates(calibration[name].data,[[parent_y],[parent_x]],order=1,cval=np.nan)[0]) for name in ['CWAVE','CBAND']]
    if not np.isfinite([wave,width]).all() or width<=0:raise ValueError('No finite calibrated wavelength at the source position')
    packet={k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in result.items() if k in [
        'flux_ujy','statistical_sigma_ujy','background_coefficients_mjysr','background_pixels','core_support_fraction',
        'aperture_throughput','pixel_flags_union','epsf','position_pixel_xy','parameter_order','parameter_covariance',
        'reduced_chi2','residual_expected_noise_dof']}
    if 'centroid_fit' in result:packet['centroid_fit']={k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in result['centroid_fit'].items()}
    packet.update({'wavelength_um':wave,'bandwidth_um':width,'solid_angle_wcs_ratio':ratio,
        'centroid_refinement':'performed' if refine else 'fixed_requested' if options.centroid_mode=='fixed' else 'not_attempted_below_snr20',
        'status':'accepted' if result['reduced_chi2']<3 else 'diagnostic_only',
        'reason':None if result['reduced_chi2']<3 else 'Source/background residual score exceeds the declared maximum of 3.'})
    context={'shape':[height,image['IMAGE'].data.shape[1]],'brightness_mjysr':finite_list(np.asarray(image['IMAGE'].data,dtype=float)),
        'residual_ujy':finite_list(result['residual_ujy']),'used':result['used'].astype(int).tolist()}
    return packet,context


def extract_observations(rows,source,options,destination,native_loader=None,check_cancel=lambda:None,progress=lambda stage:None):
    if not 1<=len(rows)<=512:raise ValueError('Choose one to 512 native observations')
    if len({(r['obs_id'],r['detector']) for r in rows})!=len(rows):raise ValueError('Duplicate physical observations cannot enter one source product')
    rows=sorted(rows,key=lambda r:(r['mjd_mid'],r['detector'],r['obs_id']))
    samples=[];contexts={};handles={};verified=set();bindings={}
    approved=registry()
    loader=native_loader or (lambda row,position:native_cutout(row,position,2.5))
    with ExitStack() as stack:
        for index,row in enumerate(rows):
            check_cancel();progress(f'measuring_{index+1}_of_{len(rows)}')
            position=source.position(row['mjd_mid'])
            sample={k:row[k] for k in ['obs_id','detector','release','mjd_mid']}
            sample['sample_id']=f"{row['obs_id']}/D{row['detector']}"
            sample.update({'utc_mid':Time(row['mjd_mid'],format='mjd',scale='utc').isot+'Z','source_url':row['ibe'],
                'input_position_deg':position,'status':'rejected','reason':None,'flux_ujy':None,'statistical_sigma_ujy':None,
                'wavelength_um':None,'bandwidth_um':None,'source_sha256':None})
            try:
                path,mode=loader(row,position);check_cancel()
                if mode not in ['native_ibe_cutout','native_s3_section']:raise ValueError('Only verified native IBE cutouts or native S3 sections may be measured')
                sample['source_sha256']=digest(path)
                with fits.open(path,memmap=False) as image:
                    header=image['IMAGE'].header
                    if str(header['OBSID'])!=row['obs_id'] or int(header['DETECTOR'])!=row['detector'] or abs(float(header['MJD-AVG'])-row['mjd_mid'])>1e-6:
                        raise ValueError('Native observation, detector or acquisition time differs from its discovery association')
                    binding=approved_binding(image,row['release'],approved);key=(row['release'],row['detector'])
                    bindings['/'.join(map(str,key))]=binding
                    if key not in handles:
                        handles[key]=[stack.enter_context(fits.open(verified_path(binding[k],verified),memmap=False)) for k in ['spectral_wcs','solid_angle']]
                    parameters={'center':f'{position[0]},{position[1]}deg','size':'0.0625deg'}
                    origin=[int(round(1-header['CRPIX1A'])),int(round(1-header['CRPIX2A']))]
                    sample['native_input']={'retrieval_mode':mode,'requested_center_deg':position,'cutout_parameters':parameters,
                        'parent_detector_bbox_xywh':origin+[image['IMAGE'].data.shape[1],image['IMAGE'].data.shape[0]],
                        'cloud_access':row.get('cloud_access'),
                        'checksum_semantics':'SHA-256 identifies the retained native measurement input. An S3 section is a derived FITS with native pixel values and adjusted cutout origins; its bytes are not the full parent exposure.'}
                    if mode=='native_ibe_cutout':sample['native_cutout_request']={'url':row['ibe']+'?'+urlencode(parameters),'sha256':sample['source_sha256'],'parent_url':row['ibe']}
                    measured,context=measure_native(image,*handles[key],position,options)
                    sample.update(measured)
                    encoded=json.dumps(context,sort_keys=True,allow_nan=False,separators=(',',':'))
                    sample['image_context_file']=f'sample-{index}.json';sample['image_context_sha256']=hashlib.sha256(encoded.encode()).hexdigest()
                    contexts[sample['image_context_file']]=encoded
            except (ValueError,IndexError,KeyError) as exc:sample.update({'status':'rejected','reason':str(exc),'flux_ujy':None,'statistical_sigma_ujy':None})
            except requests.RequestException:sample['reason']='Native archive input is temporarily unavailable after bounded retries. Retry this observation.'
            samples.append(sample)
    check_cancel()
    canonical={'policy':POLICY,'photometry_policy':PHOTOMETRY_POLICY,'calibration_registry_policy':approved['policy'],
        'source':source.model_dump(),'request':options.model_dump(),
        'calibrations':bindings,'samples':samples,
        'software':{'numpy':np.__version__,'scipy':scipy.__version__,'astropy':astropy.__version__,'photutils':photutils.__version__}}
    identity=hashlib.sha256(json.dumps(canonical,sort_keys=True,allow_nan=False).encode()).hexdigest()
    counts={state:sum(s['status']==state for s in samples) for state in ['accepted','diagnostic_only','rejected']}
    product={'schema_version':'1.0.0','id':identity,'type':'source_samples','name':source.name+' · native source samples',**canonical,
        'data_status':'native_exposure_measurements','science_status':'conditional_point_source_samples',
        'complete_102_channel_spectrum':False,'units':'uJy',
        'sampling':{'available_observations':len(rows),'accepted_samples':counts['accepted'],'diagnostic_only_samples':counts['diagnostic_only'],
            'rejected_samples':counts['rejected'],'detectors':sorted({r['detector'] for r in rows}),
            'mjd_range':[min(r['mjd_mid'] for r in rows),max(r['mjd_mid'] for r in rows)],
            'interpretation':'Individual native measurements at their own acquisition times and central CWAVE/CBAND. No inferred or zero-filled missing channels; this is not an instantaneous spectrum.'},
        'uncertainty_method':'Native independent-pixel statistical covariance, including fitted local background and optional centroid/source cross covariance. Common calibration, native correlations and PSF/model errors are not supplied and are excluded.',
        'limitations':['Point-source measurements require inspection of isolation and fit residuals; no deblending, extended-source or identity validation is performed.',
            'Only exact approved native release/processing/calibration associations are enabled. Unsupported files remain rejected.',
            'Samples at different acquisition dates must not be interpreted as a simultaneous spectrum. No binning or upper-limit inference is performed here.',
            'Central CWAVE/CBAND do not describe the full wavelength-response variation over the native estimator.',
            'Angular motion uses supplied reference-epoch components (pmra includes cos declination), with no observer parallax or perspective acceleration. Fixed ICRS inputs request one sky coordinate at all times.',
            'Automatic centroid refinement is attempted only at initial PSF signal-to-noise >=20; fainter samples retain the supplied position and conditional statistical errors.',
            'Accepted means the declared mask/coverage/geometry/fit checks pass; it is not a detection probability, source classification or claim of discovery.',
            'Finite calibrated ePSF convention; no unknown outer wings, separate ZODI subtraction, clipping or total calibration-error estimate.'],
        'credits':'SPHEREx: NASA/JPL-Caltech/Caltech-IPAC, IRSA. Supplied source-position metadata and its interpretation remain separate from measured native fluxes.'}
    folder=Path(destination)/identity;folder.mkdir(parents=True,exist_ok=True)
    for name,encoded in contexts.items():atomic_text(folder/name,encoded)
    table=table_for_product(product)
    for format,name in [('ascii.ecsv','samples.ecsv'),('ascii.csv','samples.csv')]:
        buffer=io.StringIO();table.write(buffer,format=format);atomic_text(folder/name,buffer.getvalue())
    atomic_text(folder/'plot.svg',spectrum_svg(product,x_bounds=(.7,5.1),title=source.name))
    product['exports']={name:{'url':f'/v1/products/{identity}/{name}','sha256':digest(folder/name)} for name in ['samples.ecsv','samples.csv','plot.svg']}
    for sample in product['samples']:
        if 'image_context_file' in sample:sample['image_context_url']=f'/v1/products/{identity}/'+sample['image_context_file']
    check_cancel();write_json(folder/'manifest.json',product)
    return product
