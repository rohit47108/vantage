"""Explicit linear science operators with correlated output noise.

Sparse-array API: https://docs.scipy.org/doc/scipy/reference/sparse.html
Pixel-overlap interpretation: https://docs.astropy.org/projects/reproject/en/stable/celestial.html
The local planar overlap is bounded to small fields and independently checked
against spherical reproject_exact. Native-input diagonal covariance is an
explicit approximation, never inferred from a resampled variance image.
"""
import numpy as np
from scipy import sparse


def linear_transform(operator, values, covariance):
    a=sparse.csr_array(operator,dtype=float)
    values=np.asarray(values,dtype=float).ravel()
    if np.any(~np.isfinite(values)):
        raise ValueError('Mask invalid native inputs before applying a linear transform')
    c=np.asarray(covariance) if not sparse.issparse(covariance) else covariance
    c=sparse.diags_array(c) if getattr(c,'ndim',2)==1 else sparse.csr_array(c)
    if c.shape!=(len(values),len(values)) or a.shape[1]!=len(values):
        raise ValueError('Operator and covariance dimensions do not agree')
    if np.any(~np.isfinite(c.data)) or np.any(c.diagonal()<0):
        raise ValueError('Covariance must be finite with nonnegative diagonal')
    return np.asarray(a@values),sparse.csr_array(a@c@a.T)


def independent_sources(planes):
    seen=set()
    for p in planes:
        identifiers=set(p['source_ids'])
        if not identifiers or identifiers&seen:
            raise ValueError('Independent-input method rejects empty or shared physical exposures')
        seen.update(identifiers)
    return sorted(seen)


def weighted_mean(planes):
    identifiers=independent_sources(planes)
    if len(planes)<2:raise ValueError('A coadd requires at least two independent exposures')
    weights=[]
    for p in planes:
        variance=p['covariance'].diagonal()
        valid=p['valid']&np.isfinite(p['values'])&np.isfinite(variance)&(variance>0)
        weights.append(np.divide(1.,variance,out=np.zeros_like(variance),where=valid))
    weights=np.asarray(weights)
    total=weights.sum(axis=0)
    normalized=np.divide(weights,total,out=np.zeros_like(weights),where=total>0)
    values=np.zeros(len(total));cov=sparse.csr_array((len(total),len(total)))
    for p,w in zip(planes,normalized):
        values+=w*np.nan_to_num(p['values'])
        diag=sparse.diags_array(w)
        cov+=diag@p['covariance']@diag
    values[total==0]=np.nan
    return {'values':values,'covariance':cov,'valid':total>0,
            'contributions':(weights>0).sum(axis=0),'weights':normalized,'source_ids':identifiers}


def difference(reference,comparison,background_mask,alpha=1.,alpha_variance=0.):
    identifiers=independent_sources([reference,comparison])
    if not np.isfinite(alpha) or alpha<=0 or not np.isfinite(alpha_variance) or alpha_variance<0:
        raise ValueError('Scale and its external variance must be finite and physical')
    valid=reference['valid']&comparison['valid']
    a=np.nan_to_num(reference['values']);b=np.nan_to_num(comparison['values'])
    raw=b-alpha*a
    covariance=sparse.csr_array(comparison['covariance']+alpha**2*reference['covariance'])
    if alpha_variance:
        # External scale estimate must be independent of these pixels.
        covariance+=sparse.csr_array(alpha_variance*np.outer(a,a))
    selection=np.asarray(background_mask,dtype=bool)&valid
    indices=np.flatnonzero(selection)
    if len(indices)<3:raise ValueError('At least three valid background pixels are required')
    c=covariance[indices,:][:,indices].toarray()
    precision=np.linalg.pinv(c,rcond=1e-10,hermitian=True)
    w=precision@np.ones(len(indices))
    if w.sum()<=0:raise ValueError('Background covariance is singular or unsupported')
    w/=w.sum()
    full=np.zeros(len(raw));full[indices]=w
    background=float(full@raw)
    # Apply fitted-background projection to BOTH values and covariance,
    # including correlations between fitted parameters and the science pixels.
    projection=sparse.eye_array(len(raw),format='csr')-sparse.csr_array(np.outer(np.ones(len(raw)),full))
    values=raw-background
    covariance=sparse.csr_array(projection@covariance@projection.T)
    values[~valid]=np.nan
    return {'values':values,'covariance':covariance,'valid':valid,'background':background,
            'alpha':alpha,'alpha_variance':alpha_variance,'source_ids':identifiers}


def _clip(poly,axis,bound,greater):
    out=[]
    if not len(poly):return out
    previous=poly[-1]
    for current in poly:
        previous_inside=(previous[axis]>=bound) if greater else (previous[axis]<=bound)
        current_inside=(current[axis]>=bound) if greater else (current[axis]<=bound)
        if current_inside!=previous_inside:
            fraction=(bound-previous[axis])/(current[axis]-previous[axis])
            out.append(previous+fraction*(current-previous))
        if current_inside:out.append(current)
        previous=current
    return out


def _area(poly):
    p=np.asarray(poly)
    if len(p)<3:return 0.
    return float(abs(np.dot(p[:,0],np.roll(p[:,1],1))-np.dot(p[:,1],np.roll(p[:,0],1)))/2)


def overlap_operator(source_wcs,source_shape,output_wcs,output_shape):
    """Area weights from native quadrilaterals onto a small TAN grid.

    Surface brightness is area averaged. No renormalization across clipped or
    invalid support is done. Callers must mask rows without complete support.
    Curved pixel edges are approximated by their corners, with tested limits.
    """
    if np.prod(output_shape)>4096 or np.prod(source_shape)>512**2:
        raise ValueError('Numerical region exceeds the bounded operator size')
    ny,nx=source_shape;oy,ox=output_shape
    yy,xx=np.indices((ny+1,nx+1),dtype=float)
    ra,dec=source_wcs.pixel_to_world_values(xx-.5,yy-.5)
    px,py=output_wcs.world_to_pixel_values(ra,dec)
    rows=[];cols=[];weights=[]
    for y in range(ny):
        for x in range(nx):
            polygon=np.array([[px[y,x],py[y,x]],[px[y,x+1],py[y,x+1]],
                              [px[y+1,x+1],py[y+1,x+1]],[px[y+1,x],py[y+1,x]]])
            if not np.isfinite(polygon).all():continue
            lo=np.floor(polygon.min(axis=0)+.5).astype(int)
            hi=np.floor(polygon.max(axis=0)+.5).astype(int)
            for j in range(max(0,lo[1]),min(oy-1,hi[1])+1):
                for i in range(max(0,lo[0]),min(ox-1,hi[0])+1):
                    clipped=polygon
                    for axis,bound,greater in [(0,i-.5,True),(0,i+.5,False),(1,j-.5,True),(1,j+.5,False)]:
                        clipped=_clip(clipped,axis,bound,greater)
                    area=_area(clipped)
                    if area>1e-12:
                        rows.append(j*ox+i);cols.append(y*nx+x);weights.append(area)
    return sparse.csr_array((weights,(rows,cols)),shape=(oy*ox,ny*nx))
