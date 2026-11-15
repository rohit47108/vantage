"""Calibrated, explicitly response-mixed narrowband linear coadds.

This operator does not authorize precision photometry or difference detections.
It retains the individual responses and full resampling covariance instead of
pretending that a weighted mean defines one exact bandpass or one timestamp.
"""
import json
import hashlib
from pathlib import Path
import numpy as np
import astropy.units as u
from astropy.io import fits
from astropy.wcs import WCS
from scipy import sparse
from backend.science import ROOT, BAD_MASK, KNOWN_MASK, digest, grid, write_json, finite_list
from backend.operators import overlap_operator, linear_transform, weighted_mean

POLICY='narrowband-linear-coadd-3'

def source_file(sha):
    registry=json.loads((ROOT/'demo_dataset_manifest.json').read_text(encoding='utf-8'))
    dr1=json.loads((ROOT/'research/updates/2026-11-14/dr1-fixtures.json').read_text(encoding='utf-8'))
    for row in registry['files']+dr1['files']:
        if row['sha256']==sha and (ROOT/row['path']).is_file():
            path=ROOT/row['path']
            if digest(path)!=sha:raise ValueError('Retained source checksum does not match')
            return path
    for path in (ROOT/'.runtime/sources').glob('*.fits'):
        if digest(path)==sha:return path
    raise ValueError('Native inputs are not retained for this sequence. Generate a fresh live sequence first.')

def native_plane(frame,output,shape):
    source=source_file(frame['source_sha256'])
    calibration=source_file(frame['calibration_sha256'])
    with fits.open(source,memmap=False) as hdus:
        h=hdus['IMAGE'].header.copy();raw=np.asarray(hdus['IMAGE'].data,dtype=float)
        variance=np.asarray(hdus['VARIANCE'].data,dtype=float)
        if u.Unit(h.get('BUNIT',''))!=u.MJy/u.sr or u.Unit(hdus['VARIANCE'].header.get('BUNIT',''))!=(u.MJy/u.sr)**2:
            raise ValueError('Native brightness or variance units do not match the supported calibrated units')
        flags=np.asarray(hdus['FLAGS'].data,dtype=np.uint32)
        if raw.shape!=variance.shape or raw.shape!=flags.shape:raise ValueError('Native layers have inconsistent shapes')
        unknown=flags & np.uint32(~KNOWN_MASK & 0xffffffff)
        good=np.isfinite(raw)&np.isfinite(variance)&(variance>0)&((flags&BAD_MASK)==0)&(unknown==0)
        a=overlap_operator(WCS(h),raw.shape,output,shape)
        geometric=np.asarray(a.sum(axis=1)).ravel()
        valid=(geometric>.99999)&(np.asarray(a@good.ravel().astype(float))>.99999)
        # An invalid native sample receives zero internally, but every output
        # touched by it remains invalid. These zeros are never published as data.
        values,cov=linear_transform(a,np.nan_to_num(raw).ravel(),np.where(good,variance,0).ravel())
        values[~valid]=np.nan
        yy,xx=np.indices(raw.shape)
        with fits.open(calibration,memmap=False) as ch:
            if int(ch['CWAVE'].header['DETECTOR'])!=int(h['DETECTOR']):raise ValueError('Spectral calibration detector mismatch')
            dx,dy=1-h['CRPIX1A'],1-h['CRPIX2A']
            if abs(dx-round(dx))>1e-8 or abs(dy-round(dy))>1e-8:
                raise ValueError('Non-integer parent cutout offsets require a calibrated interpolation method')
            x=xx+int(round(dx));y=yy+int(round(dy))
            wave_map=np.array(ch['CWAVE'].data,dtype=float)
            width_map=np.array(ch['CBAND'].data,dtype=float)
            inside=(x>=0)&(x<wave_map.shape[1])&(y>=0)&(y<wave_map.shape[0])
            waves=np.full(raw.shape,np.nan);widths=np.full(raw.shape,np.nan)
            waves[inside]=wave_map[y[inside],x[inside]]
            widths[inside]=width_map[y[inside],x[inside]]
        wave=np.asarray(a@waves.ravel())/np.maximum(geometric,1e-20)
        width=np.asarray(a@widths.ravel())/np.maximum(geometric,1e-20)
        result_flags=np.zeros(a.shape[0],dtype=np.uint32)
        for row in range(a.shape[0]):
            result_flags[row]=np.bitwise_or.reduce(flags.ravel()[a.indices[a.indptr[row]:a.indptr[row+1]]],initial=np.uint32(0))
    return {'values':values,'covariance':cov,'valid':valid,'source_ids':[f"{frame['obs_id']}/D{frame['detector']}"],
            'wavelength':wave,'bandwidth':width,'flags':result_flags,'operator':a,
            'mjd_start':float(h['MJD-BEG']),'mjd_end':float(h['MJD-END']),
            'native_file':str(source),'native_good':good,'native_variance':variance,'native_values':raw,'native_wcs':WCS(h)}

def build_coadd(sequence,indices,destination,fov_arcmin=3.0,size=32,mismatch_bandwidths=.025):
    if sequence.get('mode')!='fixed_sky':raise ValueError('Tracked thumbnails cannot be used as fixed-sky coadd inputs')
    if not 2<=len(indices)<=8 or len(set(indices))!=len(indices):raise ValueError('Choose two to eight distinct input frames')
    if any(i<0 or i>=len(sequence['frames']) for i in indices):raise ValueError('Unknown frame index')
    if not .5<=fov_arcmin<=3.3 or not 16<=size<=48:raise ValueError('Numerical coadd regions must be 0.5–3.3 arcminutes and 16–48 pixels')
    output,_=grid(sequence['center_deg'],fov_arcmin,size)
    frames=[sequence['frames'][i] for i in indices]
    planes=[native_plane(frame,output,(size,size)) for frame in frames]
    waves=np.asarray([p['wavelength'] for p in planes]);widths=np.asarray([p['bandwidth'] for p in planes])
    spectral=np.isfinite(waves).all(axis=0)&np.isfinite(widths).all(axis=0)&(widths.min(axis=0)>0)
    spectral&=np.ptp(waves,axis=0)<=mismatch_bandwidths*widths.min(axis=0)
    spectral&=widths.max(axis=0)<=1.05*widths.min(axis=0)
    # Numerical combination is only shown where ALL selected inputs have valid
    # geometry/quality and the narrow spectral screen. Missing inputs are not
    # silently turned into a single-frame coadd.
    quality=np.logical_and.reduce([p['valid'] for p in planes])
    joint=spectral&quality
    if joint.sum()<4:
        reason='The selected wavelengths or bandwidths do not match in this region.' if spectral.sum()<4 else 'Coverage and flagged pixels leave too little common usable sky.'
        raise ValueError(reason+' Try a smaller region or the M101 narrowband example. No coadd was published.')
    for p in planes:p['valid']&=joint
    coadd=weighted_mean(planes)
    w=coadd['weights'];values=coadd['values'].reshape(size,size)
    variance=coadd['covariance'].diagonal().reshape(size,size)
    variance[~joint.reshape(size,size)]=np.nan
    times=[f['mjd_mid'] for f in frames]
    interval=[min(p['mjd_start'] for p in planes),max(p['mjd_end'] for p in planes)]
    canonical={'policy':POLICY,'sequence_id':sequence['id'],'frames':frames,'grid':dict(output.to_header()),
               'fov_arcmin':fov_arcmin,'size':size,'mismatch_bandwidths':mismatch_bandwidths,
               'native_intervals':[[p['mjd_start'],p['mjd_end']] for p in planes],
               'software':{'numpy':np.__version__,'scipy':__import__('scipy').__version__,'astropy':__import__('astropy').__version__}}
    identity=hashlib.sha256(json.dumps(canonical,sort_keys=True,allow_nan=False).encode()).hexdigest()
    folder=Path(destination)/identity;folder.mkdir(parents=True,exist_ok=True)
    header=output.to_header();header['BUNIT']='MJy/sr';header['BTYPE']='Inverse-variance weighted mean'
    primary=fits.PrimaryHDU();primary.header['METHOD']=POLICY;primary.header['MJD-BEG']=interval[0];primary.header['MJD-END']=interval[1];primary.header['TIMESYS']='UTC'
    primary.header['NSOURCE']=len(frames);primary.header['CALWARN']='Statistical covariance only; common calibration systematics excluded'
    coo=coadd['covariance'].tocoo()
    columns=[fits.Column(name='ROW',format='J',array=coo.row),fits.Column(name='COL',format='J',array=coo.col),
             fits.Column(name='COVARIANCE',format='D',unit='(MJy/sr)^2',array=coo.data)]
    flags=np.bitwise_or.reduce([p['flags'] for p in planes]).reshape(size,size)
    wave=np.sum(w*waves,axis=0).reshape(size,size);wave[~joint.reshape(size,size)]=np.nan
    hdus=[primary,fits.ImageHDU(values,header,name='IMAGE'),fits.ImageHDU(variance,header,name='VARIANCE'),
          fits.ImageHDU((~joint).reshape(size,size).astype(np.uint8),header,name='MASK'),
          fits.ImageHDU(coadd['contributions'].reshape(size,size).astype(np.int16),header,name='NCONTRIB'),
          fits.ImageHDU(flags,header,name='FLAGS'),fits.ImageHDU(wave,header,name='CWAVE'),
          fits.ImageHDU(w.reshape(len(frames),size,size),name='WEIGHTS'),
          fits.ImageHDU(waves.reshape(len(frames),size,size),name='INPUT_CWAVE'),
          fits.ImageHDU(widths.reshape(len(frames),size,size),name='INPUT_CBAND'),
          fits.BinTableHDU.from_columns(columns,name='COVARIANCE')]
    # Per-extension units must not inherit surface-brightness units blindly.
    hdus[2].header['BUNIT']='(MJy/sr)^2'
    for index in [3,4,5,7]:hdus[index].header['BUNIT']='1'
    for index in [6,8,9]:hdus[index].header['BUNIT']='um'
    fits_path=folder/'science.fits'
    fits.HDUList(hdus).writeto(folder/'science.partial',overwrite=True,checksum=True)
    (folder/'science.partial').replace(fits_path)
    manifest={'schema_version':'1.0.0','id':identity,'type':'coadd','name':sequence['name']+' · narrowband coadd',
              **canonical,'shape':[size,size],'units':'MJy/sr','science_status':'conditional_narrowband_coadd',
              'brightness':finite_list(values),'variance':finite_list(variance),'mask':(~joint).reshape(size,size).astype(int).tolist(),
              'contributions':coadd['contributions'].reshape(size,size).tolist(),'wavelength':finite_list(wave),
              'joint_support_fraction':float(joint.mean()),'mjd_interval':interval,'mjd_midpoint_range':[min(times),max(times)],
              'exclusion_counts':{'requested_pixels':size*size,'spectral_rejections':int((~spectral).sum()),
                                  'geometry_or_quality_rejections':int((~quality).sum()),
                                  'retained_pixels':int(joint.sum())},
              'fits_sha256':digest(fits_path),'source_ids':coadd['source_ids'],
              'response_description':'At each pixel, an inverse-statistical-variance weighted mixture of the retained input CWAVE/CBAND samples. CWAVE output is the weighted mean calibration CWAVE, not a full effective response curve.',
              'uncertainty_method':'A diag(native VARIANCE) A^T, then sum of W_i C_i W_i^T. Native-pixel and independent-exposure assumptions. Full sparse output covariance exported in FITS.',
              'limitations':['Spectral screening does not establish identical response curves or authorize precision photometry.',
                             'Native-pixel covariance and common calibration errors are not supplied and are not included in statistical errors.',
                             'WCS-only registration; input PSFs are mixed, not homogenized. This coadd is not eligible for subtraction.',
                             'Fixed-sky stacking can smear moving sources. Contributing epochs remain separate in provenance.',
                             'No ZODI subtraction, background fit, outlier clipping or photometric rescaling was performed.'],
              'credits':sequence['credits']}
    write_json(folder/'manifest.json',manifest)
    return manifest
