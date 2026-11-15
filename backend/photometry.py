"""Native-pixel isolated-source measurements with explicit linear estimators.

No resampling, guessed pixel area, optical-PSF substitution, clipping, or ZODI
subtraction. Statistical errors condition on the supplied position/ePSF and
independent native pixels; calibration/model/position errors are separate.

https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/
https://docs.astropy.org/projects/photutils/en/stable/api/photutils.psf.ImagePSF.html
https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/#additional-product-solid-angle-pixel-map
"""
import math
import numpy as np
import astropy.units as u
from photutils.psf import ImagePSF
from photutils.aperture import CircularAperture
from scipy.optimize import least_squares
from backend.science import BAD_MASK,KNOWN_MASK

POLICY='native-isolated-photometry-1'


def _origin(header):
    origin=np.array([1-float(header['CRPIX1A']),1-float(header['CRPIX2A'])])
    if not np.isfinite(origin).all():raise ValueError('Invalid parent detector origin')
    return origin


def solid_angle_for_image(calibration,image_header,shape):
    """Read the release's actual SAPM, retaining its native detector origin.

    Map values are square arcseconds; output is steradians. A cutout's alternate
    CRPIX offsets map zero-based native pixels to the uncut calibration map.
    """
    hdu=calibration['IMAGE']
    if int(hdu.header['DETECTOR'])!=int(image_header['DETECTOR']):
        raise ValueError('Solid-angle calibration detector mismatch')
    unit=u.Unit(hdu.header.get('BUNIT',''))
    if not unit.is_equivalent(u.sr):raise ValueError('Solid-angle calibration units are not an angular area')
    origin=_origin(image_header)
    if not np.allclose(origin,np.round(origin),atol=1e-9,rtol=0):
        raise ValueError('Solid-angle lookup requires integer parent cutout offsets')
    x,y=map(int,np.round(origin));height,width=map(int,shape)
    if x<0 or y<0 or x+width>hdu.data.shape[1] or y+height>hdu.data.shape[0]:
        raise ValueError('Native cutout extends outside its solid-angle calibration')
    area=np.array(hdu.data[y:y+height,x:x+width],dtype=float,copy=True)*unit.to(u.sr)
    if not np.isfinite(area).all() or np.any(area<=0):raise ValueError('Invalid calibrated solid angles')
    return area


def to_pixel_flux(brightness_mjysr,variance_mjysr2,solid_angle_sr):
    brightness=np.asarray(brightness_mjysr,dtype=float)
    variance=np.asarray(variance_mjysr2,dtype=float)
    area=np.asarray(solid_angle_sr,dtype=float)
    if brightness.shape!=variance.shape or brightness.shape!=area.shape:
        raise ValueError('Brightness, variance and solid-angle shapes differ')
    if not np.isfinite(area).all() or np.any(area<=0):raise ValueError('Invalid solid angles')
    # 1 MJy/sr * sr = 1e12 microJy; variance uses the SQUARE of this factor.
    factor=area*1e12
    return brightness*factor,variance*factor**2


def render_epsf(data,oversampling_yx,x0,y0,shape):
    """Sample an already pixel-convolved ePSF at native pixel centers.

    IRSA stores arrays with sum 1, not Photutils' oversampled sum convention.
    Normalize the complete phase-rendered stamp BEFORE cropping it to the image.
    Never integrate the already pixel-convolved ePSF over the pixel a second time.
    The unit-flux convention refers to the finite supplied ePSF footprint;
    unknown wings outside that calibration are not invented.
    """
    data=np.asarray(data,dtype=float)
    oversampling=np.asarray(oversampling_yx,dtype=float)
    if data.ndim!=2 or min(data.shape)<4 or not np.isfinite(data).all() or data.sum()<=0:
        raise ValueError('Invalid effective PSF samples')
    if oversampling.shape!=(2,) or not np.equal(oversampling,np.round(oversampling)).all() or np.any(oversampling<1) or np.any(oversampling>10):
        raise ValueError('Unsupported effective PSF oversampling')
    if not np.isfinite([x0,y0]).all():raise ValueError('Source position must be finite')
    if len(shape)!=2 or min(shape)<1 or max(shape)>4096:raise ValueError('Unsupported native image shape')
    # Pad past the full calibration support at any source phase.
    half=int(math.ceil(max((np.array(data.shape)-1)/(2*oversampling))))+1
    xll,yll=int(math.floor(x0-half)),int(math.floor(y0-half))
    yy,xx=np.indices((2*half+1,2*half+1));xx+=xll;yy+=yll
    model=ImagePSF(data,oversampling=oversampling.astype(int),fill_value=0.)
    stamp=np.asarray(model.evaluate(xx,yy,flux=1.,x_0=x0,y_0=y0),dtype=float)
    normalization=float(stamp.sum())
    if not math.isfinite(normalization) or normalization<=0:raise ValueError('Invalid phase-dependent ePSF normalization')
    stamp/=normalization
    output=np.zeros(shape,dtype=float)
    inside=(xx>=0)&(yy>=0)&(xx<shape[1])&(yy<shape[0])
    output[yy[inside],xx[inside]]=stamp[inside]
    return output,{'oversampling_yx':oversampling.astype(int).tolist(),
        'stored_sample_sum':float(data.sum()),'native_sum_before_normalization':normalization,
        'cutout_psf_fraction':float(output.sum()),
        'cutout_absolute_psf_fraction':float(abs(stamp[inside]).sum()/abs(stamp).sum()),
        'negative_l1_fraction':float(abs(stamp[stamp<0]).sum()/abs(stamp).sum()),
        'normalization':'Unit sum over the complete phase-rendered finite ePSF footprint before image clipping; no extra pixel integration.'}


def epsf_for_image(image,x0,y0,external_epsf=None):
    header=image['IMAGE'].header
    parent=_origin(header)+[x0,y0]
    if np.any(parent<0) or np.any(parent>=2040):raise ValueError('Source position outside active parent detector')
    if 'EPSF' in image:
        epsf=image['EPSF'];basis='native EPSF extension'
    elif external_epsf is not None and 'EPSF' in external_epsf:
        epsf=external_epsf['EPSF'];basis='Explicit newer ePSF calibration; official tutorial permits replacing the QR2 optical model'
    else:
        raise ValueError('The older optical PSF cannot authorize photometry; a verified effective-PSF calibration is required')
    detector=int(header['DETECTOR'])
    if int(epsf.header['DETECTOR'])!=detector:raise ValueError('Effective PSF detector mismatch')
    if str(epsf.header.get('DETCOORD','')).strip()!='sky':raise ValueError('Unverified effective PSF detector coordinate convention')
    required=['XCENTER','YCENTER','EPSF','XWIDTH','YWIDTH','BINX','BINY']
    if any(c not in epsf.columns.names for c in required):raise ValueError('Effective PSF schema changed')
    table=epsf.data
    centers=np.column_stack([table['XCENTER'],table['YCENTER']])
    if not np.isfinite(centers).all():raise ValueError('Invalid effective PSF zone centers')
    index=int(np.argmin(np.sum((centers-parent)**2,axis=1)));row=table[index]
    ovs=(int(epsf.header['OVSMPY']),int(epsf.header['OVSMPX']))
    output,metadata=render_epsf(np.array(row['EPSF'],copy=True),ovs,float(x0),float(y0),image['IMAGE'].data.shape)
    metadata.update({'detector':detector,'zone_row':index,'zone_bin_xy':[int(row['BINX']),int(row['BINY'])],
        'zone_center_xy':centers[index].tolist(),'zone_width_xy':[float(row['XWIDTH']),float(row['YWIDTH'])],
        'parent_pixel_xy':parent.tolist(),'detector_coordinate_convention':'sky','basis':basis,
        'zone_wavelength_um':float(row['CWAVE']) if 'CWAVE' in epsf.columns.names else None})
    return output,metadata


def _least_squares(design,values,variance,selected):
    """Fixed-mask WLS; return coefficients, conditional covariance and beta=L y."""
    indices=np.flatnonzero(selected)
    x=design[indices];sigma=np.sqrt(variance[indices])
    white=x/sigma[:,None];scale=np.linalg.norm(white,axis=0)
    if len(indices)<=design.shape[1] or np.any(scale<=0):raise ValueError('Insufficient independent fit samples')
    scaled=white/scale
    if np.linalg.cond(scaled)>1e8:raise ValueError('Source/background model is not identifiable')
    covariance=np.linalg.inv(scaled.T@scaled)/scale[:,None]/scale[None,:]
    operator=np.zeros((design.shape[1],len(values)))
    operator[:,indices]=covariance@(x.T/variance[indices])
    coefficients=operator@np.nan_to_num(values,nan=0.,posinf=0.,neginf=0.)
    return coefficients,covariance,operator


def _residual_diagnostic(values,variance,model,design,parameter_operator,selected):
    """R C R^T diagonal and expected normalized residual sum.

    Aperture estimation is an oblique, not an orthogonal least-squares
    projection. Its residual statistic therefore cannot simply divide by N-k.
    This is a conditional model diagnostic, not a source-detection p-value.
    """
    indices=np.flatnonzero(selected)
    native_variance=np.where(np.isfinite(variance.ravel())&(variance.ravel()>0),variance.ravel(),0.)
    hat=design[indices]@parameter_operator
    v=native_variance[indices]
    diagonal=v-2*hat[np.arange(len(indices)),indices]*v+(hat**2)@native_variance
    if np.any(diagonal < -1e-8*v):raise ValueError('Invalid fitted residual covariance')
    diagonal=np.maximum(diagonal,0.)
    expected=float(np.sum(diagonal/v))
    if expected<=0:raise ValueError('No residual degrees of freedom')
    score=float(np.sum((values.ravel()[indices]-model.ravel()[indices])**2/v)/expected)
    output=np.full(values.shape,np.nan);output.ravel()[indices]=diagonal
    return score,expected,output


def measure_source(brightness_mjysr,variance_mjysr2,flags,solid_angle_sr,psf,x0,y0,
                   method='psf',aperture_radius=2.5,background_inner=5.,background_outer=8.,_selection_center=None):
    """Isolated-source aperture or forced-ePSF fit with a planar sky background.

    The source position and ePSF are held fixed. Aperture correction includes
    the background estimator's response to the finite ePSF. This function does
    not infer a detection, a source identity, a full spectrum or total errors.
    """
    if method not in ['psf','aperture']:raise ValueError('Choose psf or aperture photometry')
    values,variance=to_pixel_flux(brightness_mjysr,variance_mjysr2,solid_angle_sr)
    psf=np.asarray(psf,dtype=float);raw_flags=np.asarray(flags)
    if values.ndim!=2 or max(values.shape)>96:raise ValueError('Extract a native cutout of at most 96 pixels per axis before photometry')
    if values.ndim!=2 or psf.shape!=values.shape or raw_flags.shape!=values.shape or not np.issubdtype(raw_flags.dtype,np.integer):
        raise ValueError('Native PSF or flag shape/type mismatch')
    if int(raw_flags.min())<-(1<<31) or int(raw_flags.max())>(1<<32)-1:
        raise ValueError('Flags exceed the supported native 32-bit image schema')
    if not np.isfinite(psf).all() or psf.sum()<.98 or psf.sum()>1.02:raise ValueError('The full effective PSF is not covered by this cutout')
    if not np.isfinite([x0,y0,aperture_radius,background_inner,background_outer]).all():raise ValueError('Photometry geometry must be finite')
    if not 1<=aperture_radius<=4 or not 4.5<background_inner<background_outer<=12 or background_inner<=aperture_radius+.5:
        raise ValueError('Invalid aperture/background radii in native pixels')
    height,width=values.shape
    if min(x0,y0)<background_outer+.5 or x0+background_outer+.5>width-1 or y0+background_outer+.5>height-1:
        raise ValueError('The cutout does not contain the complete background annulus')
    flags=raw_flags.astype(np.uint32)
    unknown=flags&np.uint32(~KNOWN_MASK&0xffffffff)
    good=np.isfinite(values)&np.isfinite(variance)&(variance>0)&((flags&BAD_MASK)==0)&(unknown==0)
    yy,xx=np.indices(values.shape);dx,dy=xx-x0,yy-y0
    selection_center=_selection_center or (x0,y0)
    radius=np.hypot(xx-selection_center[0],yy-selection_center[1]);core=radius<=4.5
    fraction=float(abs(psf[core&good]).sum()/abs(psf).sum())
    if fraction<.98:raise ValueError('Defects or missing pixels remove significant source-core support')
    annulus=(radius>=background_inner)&(radius<=background_outer)
    background=annulus&good&((flags&(1<<21))==0)
    if background.sum()<20:raise ValueError('Too few unflagged, non-source background pixels')
    factor=np.asarray(solid_angle_sr)*1e12
    sky=np.stack([factor,factor*dx,factor*dy],axis=-1).reshape(-1,3)
    flat_values=values.ravel();flat_variance=variance.ravel();p=psf.ravel()
    if method=='psf':
        selected=(core&good)|background
        design=np.column_stack([p,sky])
        coefficients,covariance,operator=_least_squares(design,flat_values,flat_variance,selected.ravel())
        flux=float(coefficients[0]);estimator=operator[0];background_coefficients=coefficients[1:]
        parameter_operator=operator
        fit_model=(design@coefficients).reshape(values.shape)
        throughput=1.;dof=int(selected.sum()-4)
    else:
        aperture=CircularAperture((x0,y0),r=aperture_radius).to_mask(method='exact').to_image(values.shape)
        if aperture is None or np.any((aperture>1e-6)&~good):raise ValueError('A defective pixel intersects the source aperture')
        background_coefficients,_,bg_operator=_least_squares(sky,flat_values,flat_variance,background.ravel())
        a=aperture.ravel();background_integral=a@sky
        estimator=a-background_integral@bg_operator
        throughput=float(estimator@p)
        if not .5<throughput<=1.02:raise ValueError('Aperture has inadequate calibrated PSF throughput')
        estimator/=throughput
        flux=float(estimator@np.nan_to_num(flat_values,nan=0.,posinf=0.,neginf=0.))
        # The target's modeled wings can extend into the annulus. Undo that
        # component in the REPORTED background and retain its covariance with F.
        wing_background=bg_operator@p
        background_coefficients-=flux*wing_background
        parameter_operator=np.vstack([estimator,bg_operator-wing_background[:,None]*estimator])
        covariance=(parameter_operator*np.where(good.ravel(),flat_variance,0.))@parameter_operator.T
        selected=(core&good)|background
        fit_model=(flux*p+sky@background_coefficients).reshape(values.shape)
        dof=int(selected.sum()-4)
    # Include the fitted background through the full linear estimator, not just
    # sqrt(sum(aperture VARIANCE)). Native-pixel independence is explicit.
    flux_variance=float(np.sum(estimator**2*np.where(good.ravel(),flat_variance,0.)))
    residual=values-fit_model
    design=np.column_stack([p,sky])
    chi2,effective_dof,residual_variance=_residual_diagnostic(values,variance,fit_model,design,parameter_operator,selected)
    involved=selected|(abs(psf)>1e-8)
    flag_union=int(np.bitwise_or.reduce(flags[involved],initial=np.uint32(0)))
    return {'method':method,'policy':POLICY,'flux_ujy':flux,'statistical_sigma_ujy':math.sqrt(flux_variance),
        'background_coefficients_mjysr':background_coefficients,'parameter_covariance':covariance,
        'parameter_operator':parameter_operator,
        'parameter_order':['flux_ujy','background_mjysr','gradient_x_mjysr_per_pixel','gradient_y_mjysr_per_pixel'],
        'linear_estimator':estimator.reshape(values.shape),'model_ujy':fit_model,'residual_ujy':residual,
        'used':selected,'reduced_chi2':chi2,'dof':dof,'aperture_throughput':throughput,
        'residual_expected_noise_dof':effective_dof,'residual_variance_ujy2':residual_variance,
        'residual_statistic_interpretation':'Normalized residual sum divided by its expected noise value from R C R^T; not a discovery p-value.',
        'core_support_fraction':fraction,'background_pixels':int(background.sum()),'pixel_flags_union':flag_union,
        'contains_rejected_pixels':bool(np.any(involved&~good)),'statistical_only':True,
        'units':'uJy','position_pixel_xy':[float(x0),float(y0)],
        'geometry_pixels':{'aperture_radius':aperture_radius,'background_inner':background_inner,'background_outer':background_outer},
        'selection_center_pixel_xy':list(selection_center),
        'limitations':['Flux convention normalizes the supplied finite ePSF; unknown wings are not added.',
                       'Statistical covariance conditions on the fixed position, PSF and masks. Native covariance, calibration, PSF and position errors are not supplied.',
                       'A planar local surface-brightness background is fitted. ZODI is not separately subtracted.',
                       'Residual diagnostics and a separate isolation/centering assessment are required before publishing a science sample.']}


def measure_with_centroid(brightness,variance,flags,area,psf_renderer,x0,y0,method='psf',max_shift=.75,**geometry):
    """High-S/N bounded centroid fit with local Jacobian covariance propagation.

    Masks remain anchored to the input catalog position. Fit flux/background
    linearly at each centroid trial; then form the FULL six-parameter Jacobian,
    not just the profiled two-coordinate optimizer covariance. Aperture errors
    also include its dependence on the fitted centroid via the delta method.
    https://docs.scipy.org/doc/scipy-1.15.2/reference/generated/scipy.optimize.least_squares.html
    """
    if not 0<max_shift<=.75:raise ValueError('Centroid refinement is limited to 0.75 native pixel per axis')
    values,flux_variance=to_pixel_flux(brightness,variance,area)
    initial=np.array([x0,y0],dtype=float)
    frozen={'_selection_center':(x0,y0),**geometry}
    first=measure_source(brightness,variance,flags,area,psf_renderer(x0,y0),x0,y0,method='psf',**frozen)
    if first['flux_ujy']/first['statistical_sigma_ujy']<20:raise ValueError('Centroid refinement requires source signal-to-noise of at least 20; use a fixed catalog position')
    selected=first['used'];sigma=np.sqrt(flux_variance[selected])
    def residual(position):
        result=measure_source(brightness,variance,flags,area,psf_renderer(*position),*position,method='psf',**frozen)
        return (values[selected]-result['model_ujy'][selected])/sigma
    fit=least_squares(residual,initial,bounds=(initial-max_shift,initial+max_shift),jac='3-point',
        max_nfev=80,ftol=1e-10,xtol=1e-10,gtol=1e-8)
    if not fit.success or np.any(abs(fit.x-initial)>max_shift-.01):raise ValueError('Centroid refinement did not converge inside its bounds')
    px,py=map(float,fit.x);psf=psf_renderer(px,py)
    forced=measure_source(brightness,variance,flags,area,psf,px,py,method='psf',**frozen)
    yy,xx=np.indices(values.shape);factor=np.asarray(area)*1e12
    sky=np.stack([factor,factor*(xx-px),factor*(yy-py)],axis=-1).reshape(-1,3)
    step=.001
    dpdx=(psf_renderer(px+step,py)-psf_renderer(px-step,py))/(2*step)
    dpdy=(psf_renderer(px,py+step)-psf_renderer(px,py-step))/(2*step)
    b=forced['background_coefficients_mjysr'];flux=forced['flux_ujy']
    jacobian=np.column_stack([psf.ravel(),sky,(flux*dpdx-b[1]*factor).ravel(),(flux*dpdy-b[2]*factor).ravel()])
    _,joint_covariance,joint_operator=_least_squares(jacobian,np.zeros(values.size),flux_variance.ravel(),selected.ravel())
    if np.any(np.sqrt(np.diag(joint_covariance)[4:])>.2):raise ValueError('Fitted centroid is too uncertain for local covariance propagation')
    if method=='psf':
        result=forced;parameter_operator=joint_operator[:4]
    elif method=='aperture':
        result=measure_source(brightness,variance,flags,area,psf,px,py,method=method,**frozen)
        def parameters(x,y):
            r=measure_source(brightness,variance,flags,area,psf_renderer(x,y),x,y,method='aperture',**frozen)
            return np.r_[r['flux_ujy'],r['background_coefficients_mjysr']]
        gradient=np.column_stack([(parameters(px+step,py)-parameters(px-step,py))/(2*step),
                                  (parameters(px,py+step)-parameters(px,py-step))/(2*step)])
        parameter_operator=result['parameter_operator']+gradient@joint_operator[4:]
    else:raise ValueError('Choose psf or aperture photometry')
    # Derivatives of ALL retained parameters with respect to the same native
    # noise preserve source/background/centroid cross covariance.
    full_operator=np.vstack([parameter_operator,joint_operator[4:]])
    valid_variance=np.where(np.isfinite(flux_variance)&(flux_variance>0),flux_variance,0).ravel()
    full_covariance=(full_operator*valid_variance)@full_operator.T
    result['parameter_covariance']=full_covariance[:4,:4]
    result['parameter_operator']=parameter_operator
    result['linear_estimator']=parameter_operator[0].reshape(values.shape)
    result['statistical_sigma_ujy']=float(np.sqrt(full_covariance[0,0]))
    result['dof']=int(selected.sum()-6)
    score,effective_dof,residual_variance=_residual_diagnostic(values,flux_variance,result['model_ujy'],jacobian,full_operator,selected)
    result['reduced_chi2']=score
    result['residual_expected_noise_dof']=effective_dof
    result['residual_variance_ujy2']=residual_variance
    result['centroid_fit']={'initial_pixel_xy':initial.tolist(),'fitted_pixel_xy':[px,py],
        'shift_pixel_xy':(fit.x-initial).tolist(),'sigma_pixel_xy':np.sqrt(np.diag(full_covariance)[4:]).tolist(),
        'maximum_shift_per_axis':max_shift,'covariance':full_covariance,
        'parameter_order':result['parameter_order']+['centroid_x_pixel','centroid_y_pixel'],
        'uncertainty_method':'Local full-Jacobian covariance; aperture uses delta-method position derivatives. Masks anchored to the independent input position. High-S/N bounded fit only.'}
    return result


def measure_fits(image,solid_angle,x0,y0,method='psf',external_epsf=None,refine_centroid=False,**geometry):
    if u.Unit(image['IMAGE'].header.get('BUNIT',''))!=u.MJy/u.sr or u.Unit(image['VARIANCE'].header.get('BUNIT',''))!=(u.MJy/u.sr)**2:
        raise ValueError('Unsupported calibrated IMAGE/VARIANCE units')
    height,width=image['IMAGE'].data.shape
    if max(height,width)>96:raise ValueError('Extract a native cutout of at most 96 pixels per axis before photometry')
    if not np.isfinite([x0,y0]).all() or not (0<=x0<width and 0<=y0<height):
        raise ValueError('Native cutout does not cover the source position')
    area=solid_angle_for_image(solid_angle,image['IMAGE'].header,image['IMAGE'].data.shape)
    psf,metadata=epsf_for_image(image,x0,y0,external_epsf)
    args=[np.array(image['IMAGE'].data,dtype=float),np.array(image['VARIANCE'].data,dtype=float),np.array(image['FLAGS'].data),area]
    if refine_centroid:
        def renderer(x,y):
            p,m=epsf_for_image(image,x,y,external_epsf)
            if m['zone_row']!=metadata['zone_row']:raise ValueError('Centroid refinement crosses an effective PSF zone boundary; rerun at the refined position')
            return p
        result=measure_with_centroid(*args,renderer,x0,y0,method=method,**geometry)
        _,metadata=epsf_for_image(image,*result['position_pixel_xy'],external_epsf)
    else:
        result=measure_source(*args,psf,x0,y0,method=method,**geometry)
    result['epsf']=metadata
    return result
