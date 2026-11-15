"""Native sample coverage and conditional statistical summaries.

Nominal channels use the delivered geometric map, never nearest wavelength.
The map's actual DETCOORD=sky overrides the overview's generic flip warning.
https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHERExSpectralFiles_202607.pdf
https://pdg.lbl.gov/2025/reviews/rpp2025-rev-statistics.pdf
"""
import csv
import gzip
import hashlib
import io
import json
from functools import lru_cache
from pathlib import Path
from datetime import date
from collections import defaultdict
import numpy as np
from astropy.io import fits
from astropy.time import Time
from pydantic import BaseModel,ConfigDict,Field,model_validator
from scipy.special import log_ndtr,ndtri_exp
from scipy.stats import chi2,norm
from backend.science import ROOT

POLICY='native-source-summary-1'
FOLDER=ROOT/'research/updates/2026-11-15/spectral-response'


class SummaryOptions(BaseModel):
    model_config=ConfigDict(extra='forbid')
    start_utc:date|None=None
    end_utc:date|None=None
    time_bin_days:int|None=Field(default=1,ge=1,le=366)

    @model_validator(mode='after')
    def dates(self):
        if self.start_utc and self.end_utc and self.start_utc>self.end_utc:raise ValueError('Choose increasing UTC summary dates')
        return self


class SourceSummaryRequest(SummaryOptions):
    product_id:str=Field(pattern=r'^[a-f0-9]{64}$')


@lru_cache(maxsize=1)
def spectral_model():
    manifest=(FOLDER/'acquisition.json').read_bytes()
    acquisition=json.loads(manifest)
    def read(member):
        entry=next(row for row in acquisition['files'] if row['member']==member)
        path=(ROOT/entry['path']).resolve()
        if not path.is_relative_to(FOLDER.resolve()) or path.stat().st_size>10_000_000:
            raise ValueError('Unsupported retained spectral artifact')
        encoded=path.read_bytes()
        if hashlib.sha256(encoded).hexdigest()!=entry['stored_sha256']:raise ValueError('Spectral artifact checksum differs')
        if path.suffix=='.gz':
            with gzip.GzipFile(fileobj=io.BytesIO(encoded)) as stream:decoded=stream.read(10_000_001)
        else:decoded=encoded
        if len(decoded)!=entry['bytes'] or hashlib.sha256(decoded).hexdigest()!=entry['sha256']:
            raise ValueError('Decoded spectral artifact checksum differs')
        return decoded
    data=read('ChannelMaps/spectral_channels_17ch_2040.fits')
    with fits.open(io.BytesIO(data),memmap=False) as hdus:
        hdu=hdus['CHANNEL_MAP_17']
        if hdu.header.get('DETCOORD')!='sky' or hdu.header.get('DETECTOR')!='ALL' or hdu.data.shape!=(2040,2040):
            raise ValueError('Unapproved geometric channel-map convention')
        channel_map=np.array(hdu.data,copy=True)
        if not np.isin(channel_map,np.arange(19)).all():raise ValueError('Unexpected geometric channel index')
        channel_map.setflags(write=False)
    channels=[]
    for detector in range(1,7):
        member=f'FidSpecSummary/SubChannel17/Band{detector}/FidSpecSummary_Band{detector}_SpecCh17.csv'
        rows={int(row['SpecCh']):row for row in csv.DictReader(io.StringIO(read(member).decode()))}
        for channel in range(1,18):
            row=rows[channel];index=(detector-1)*17+channel-1
            channels.append({'index':index,'detector':detector,'channel':channel,
                'fiducial_wavelength_um':float(row['BandCenter_um']),'fiducial_bandwidth_um':float(row['BandWidth_um']),
                'visualization_blank':index in [50,51]})
    metadata={'id':hashlib.sha256(manifest).hexdigest(),'policy':POLICY,'channels':channels,
        'channel_map_sha256':hashlib.sha256(data).hexdigest(),'coordinate_convention':'sky; no additional MWIR flip',
        'definition':'Central native pixel in the official geometric 17-channel map; source PSF support may span a channel boundary.',
        'fiducial_semantics':'Laboratory representative channel centers/widths for labeling, not replacements for per-sample pipeline CWAVE/CBAND.',
        'visualization_blank_semantics':'Blank HiPS layers 50/51 do not prove the absence or validity of native measurements in those nominal channels.',
        'source_url':acquisition['url'],'source_etag':acquisition['etag'],
        'documentation':'https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHERExSpectralFiles_202607.pdf'}
    return channel_map,metadata


def channel_metadata():return spectral_model()[1]


def channel_for_sample(sample):
    position=sample.get('position_pixel_xy');native=sample.get('native_input')
    if position is None or native is None:return None
    bbox=native['parent_detector_bbox_xywh'];detector=sample['detector']
    if detector not in range(1,7) or len(position)!=2 or len(bbox)!=4 or not np.isfinite(position+bbox).all():
        raise ValueError('Invalid native source geometry for channel assignment')
    x,y=np.floor(np.asarray(position)+np.asarray(bbox[:2])+.5).astype(int)
    if not 0<=x<2040 or not 0<=y<2040:raise ValueError('Source center is outside the geometric channel map')
    channel_map,metadata=spectral_model();channel=int(channel_map[y,x])
    support=channel_map[max(0,y-5):min(2040,y+6),max(0,x-5):min(2040,x+6)]
    nominal=1<=channel<=17
    return {'detector':detector,'channel':channel,'index':(detector-1)*17+channel-1 if nominal else None,
        'nominal':nominal,'parent_pixel_xy':[int(x),int(y)],'support_crosses_channel_boundary':bool(np.any(support!=channel)),
        'coordinate_convention':metadata['coordinate_convention']}


def gaussian_upper_bound(flux,sigma,probability=.95):
    """One-sided credible bound: Gaussian likelihood, flat prior on flux >= 0.

    This is an observed-data inference bound, not detection completeness.
    log_ndtr/ndtri_exp avoid CDF cancellation in negative-flux tails.
    """
    if not np.isfinite([flux,sigma,probability]).all() or sigma<=0 or not 0<probability<1:
        raise ValueError('Upper bounds require finite flux, positive sigma and probability in (0,1)')
    result=float(flux-sigma*ndtri_exp(np.log1p(-probability)+log_ndtr(flux/sigma)))
    if not np.isfinite(result) or result<=0:raise ValueError('Upper-bound inputs exceed stable numerical precision')
    return result


def weighted_statistics(flux,sigma):
    flux,sigma=np.asarray(flux,dtype=float),np.asarray(sigma,dtype=float)
    if flux.ndim!=1 or sigma.shape!=flux.shape or not 1<=len(flux)<=512 or not np.isfinite([flux,sigma]).all() or np.any(sigma<=0):
        raise ValueError('Summary inputs require one to 512 finite measurements with positive statistical errors')
    relative=(sigma.min()/sigma)**2;weights=relative/relative.sum()
    mean=float(weights@flux);error=float(np.linalg.norm(weights*sigma))
    score=float(np.sum(((flux-mean)/sigma)**2))
    if not np.isfinite([mean,error,score]).all() or error<=0:raise ValueError('Summary inputs exceed stable numerical precision')
    return {'flux_ujy':mean,'statistical_sigma_ujy':error,'weights':weights.tolist(),
        'equal_mean_chi2':score if len(flux)>1 else None,'equal_mean_dof':len(flux)-1,
        'equal_mean_p_value':float(chi2.sf(score,len(flux)-1)) if len(flux)>1 else None}


def sample_statistics(sample):
    result={'sample_id':sample['sample_id'],'bound':None,'sensitivity':None,'snr':None,'reason':None}
    if sample['status']!='accepted':result['reason']='Coverage, pixel or fit checks do not support a statistical bound';return result
    flux,sigma=sample['flux_ujy'],sample['statistical_sigma_ujy']
    if flux is None or sigma is None or not np.isfinite([flux,sigma]).all() or sigma<=0:
        result['reason']='A finite native measurement and positive statistical error are required';return result
    result['snr']=float(flux/sigma)
    if sample.get('centroid_fit'):
        result['reason']='Position was fitted; fixed-position low-signal bounds are not applied';return result
    result['sensitivity']={'flux_ujy':float((5+norm.ppf(.95))*sigma),'threshold_sigma':5,
        'false_positive_probability_one_position':float(norm.sf(5)),'target_detection_probability':.95,
        'interpretation':'Conditional Gaussian fixed-position sensitivity. Quality-gate acceptance, source searching, varying variance and real-sky completeness are not included.'}
    if result['snr']>=3:result['reason']='Signal-to-statistical-error is at least 3; keep the measured flux and error';return result
    result['bound']={'upper_ujy':gaussian_upper_bound(flux,sigma),'credibility':.95,
        'prior':'Uniform in nonnegative true flux; zero for negative true flux',
        'likelihood':'Gaussian fixed-position measurement with the reported conditional statistical error',
        'interpretation':'Observed-data upper credible bound, not a detection-completeness limit or total-error bound.'}
    return result


def summarize_samples(product,options):
    if product.get('type')!='source_samples' or not product.get('samples'):raise ValueError('Choose a nonempty native source-measurement product')
    samples=product['samples'];identities=[(row['obs_id'],row['detector']) for row in samples]
    if len(identities)!=len(set(identities)):raise ValueError('Repeated physical observations cannot enter a source summary')
    hashes=[row['source_sha256'] for row in samples if row.get('source_sha256')]
    if len(hashes)!=len(set(hashes)):raise ValueError('Shared physical native inputs cannot enter a source summary')
    if any(row['flux_ujy'] is not None and not row.get('native_input') for row in samples):
        raise ValueError('This summary requires general native products with recorded parent-detector geometry')
    minimum=min(s['mjd_mid'] for s in samples);maximum=max(s['mjd_mid'] for s in samples)
    start=float(Time(options.start_utc.isoformat(),scale='utc').mjd) if options.start_utc else float(np.floor(minimum))
    end=float(Time(options.end_utc.isoformat(),scale='utc').mjd)+1 if options.end_utc else float(np.floor(maximum)+1)
    if start>=end:raise ValueError('The selected summary time interval is empty or reversed')
    selected=[s for s in samples if start<=s['mjd_mid']<end]
    coverage=[{**row,'accepted':0,'diagnostic_only':0,'rejected':0,'sample_ids':[]} for row in channel_metadata()['channels']]
    assignments={};groups=defaultdict(list);unassigned=[];edges=[]
    for sample in selected:
        sample_id=sample['sample_id'];assignment=channel_for_sample(sample);assignments[sample_id]=assignment
        if assignment is None:unassigned.append(sample_id);continue
        if not assignment['nominal']:edges.append(sample_id);continue
        row=coverage[assignment['index']];row[sample['status']]+=1;row['sample_ids'].append(sample_id)
        if sample['status']=='accepted':
            bucket=int(np.floor((sample['mjd_mid']-start)/options.time_bin_days)) if options.time_bin_days else 0
            groups[(assignment['index'],bucket)].append(sample)
    for row in coverage:row['status']='measured' if row['accepted'] else 'no_passing_measurement'
    bins=[]
    for (index,bucket),members in sorted(groups.items()):
        statistics=weighted_statistics([s['flux_ujy'] for s in members],[s['statistical_sigma_ujy'] for s in members])
        weights=np.asarray(statistics['weights']);waves=[s['wavelength_um'] for s in members]
        bins.append({'bin_id':f'{index}:{bucket}','index':index,'detector':index//17+1,'channel':index%17+1,'time_bucket':bucket,
            **statistics,'count':len(members),'input_sample_ids':[s['sample_id'] for s in members],
            'input_wavelengths_um':waves,'input_bandwidths_um':[s['bandwidth_um'] for s in members],
            'input_utc_mids':[s['utc_mid'] for s in members],
            'weighted_wavelength_um':float(weights@np.asarray(waves)),
            'mjd_range':[min(s['mjd_mid'] for s in members),max(s['mjd_mid'] for s in members)],
            'wavelength_range_um':[min(waves),max(waves)],
            'response_description':'Inverse-variance mean of the listed native measurements at their actual CWAVE/CBAND; response mixed, not a newly calibrated common bandpass.',
            'scatter_warning':False})
    comparisons=sum(row['equal_mean_p_value'] is not None for row in bins)
    for row in bins:
        row['scatter_warning']=bool(row['equal_mean_p_value'] is not None and row['equal_mean_p_value']<.01/max(1,comparisons))
    return {'policy':POLICY,'parent_product_id':product['id'],'options':options.model_dump(mode='json'),
        'time_bounds_mjd_utc':[start,end],'selected_sample_count':len(selected),'parent_sample_count':len(samples),
        'coverage':coverage,'bins':bins,'assignments':assignments,'unassigned_sample_ids':unassigned,'edge_sample_ids':edges,
        'sample_statistics':[sample_statistics(s) for s in selected],
        'spectral_model':channel_metadata(),'measured_nominal_channels':sum(row['accepted']>0 for row in coverage),
        'interpretation':'Time-combined descriptive summaries. Missing or unassigned measurements are not zeros or upper bounds. Original individual measurements remain authoritative.',
        'scatter_interpretation':'Equal-mean Gaussian chi-square is conditional on independent reported errors and a constant expectation. Differing spectral responses, variability or systematics can cause scatter. Warning uses family threshold 0.01 divided by tested bins; it is not a variability detection.',
        'uncertainty_method':'Independent native statistical variances propagated through fixed inverse-variance weights. Native correlations, common calibration, spectral-model and source-position systematics are not supplied.'}
