"""Research-only common-grid diagnostics; no application or residual detector."""
from pathlib import Path
import json, math, warnings
from astropy import log
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import map_coordinates

warnings.filterwarnings('ignore')
log.setLevel('ERROR')
p=Path('research/evidence')
data=json.loads((p/'full_challenge_sequence_screening.json').read_text())
bad_bits=[0,1,2,4,5,6,7,9,10,11,12,14,15,17,19,20,22,23,24,25,26,27,28,29]
bad_mask=np.uint32(sum(1<<b for b in bad_bits))
def sample(a,x,y,cval=np.nan):
    return map_coordinates(a,[y,x],order=1,mode='constant',cval=cval)

fig,ax=plt.subplots(5,4,figsize=(11,14),constrained_layout=True)
result={}
for n,(k,q) in enumerate(data.items()):
    npx=59
    w=WCS(naxis=2)
    w.wcs.ctype=['RA---TAN','DEC--TAN'];w.wcs.crval=q['center_deg'];w.wcs.crpix=[30,30]
    w.wcs.cdelt=[-6.15/3600,6.15/3600];w.wcs.radesys='ICRS'
    yy,xx=np.indices((npx,npx),dtype=float);ra,dec=w.pixel_to_world_values(xx,yy)
    fields=[]; waves=[]; widths=[]; footprints=[];goods=[]; centers=[]; checks=[]
    for f in q['sequence']:
        with fits.open(f['fixture']) as h, fits.open(f['source_calibration']) as c:
            image=h['IMAGE']; cw=WCS(image.header)
            x,y=cw.world_to_pixel_values(ra,dec)
            rx,ry=cw.pixel_to_world_values(x,y);tx,ty=w.world_to_pixel_values(rx,ry)
            err=float(np.nanmax(np.hypot(tx-xx,ty-yy)))
            pcx,pcy=cw.world_to_pixel_values(*q['center_deg'])
            dx,dy=np.array(f['center_xy'])-np.array([pcx,pcy])
            # The IBE cutout preserves detector orientation. Match parent offsets to independent alternate-A WCS convention.
            alt=(1-image.header['CRPIX1A'],1-image.header['CRPIX2A'])
            assert np.allclose([dx,dy],alt,atol=1e-4)
            a=image.data.astype('float64');flags=h['FLAGS'].data.astype(np.uint32);v=h['VARIANCE'].data
            b=sample(a,x,y); fields.append(b); footprints.append(np.isfinite(b))
            good=np.isfinite(a)&np.isfinite(v)&(v>0)&((flags&bad_mask)==0)
            goods.append((sample(good.astype(float),x,y,cval=0)>1-1e-8)&np.isfinite(b))
            waves.append(sample(c['CWAVE'].data,x+dx,y+dy))
            widths.append(sample(c['CBAND'].data,x+dx,y+dy))
            centers.append(w.world_to_pixel_values(*f['predicted_target_deg']))
            checks.append({'grid_wcs_roundtrip_max_px':err,'cutout_parent_offset_xy':list(alt),
                           'field_finite_fraction':float(np.isfinite(b).mean())})
    waves=np.asarray(waves); widths=np.asarray(widths)
    footprint=np.logical_and.reduce(footprints);good=np.logical_and.reduce(goods)
    spectral=np.isfinite(waves).all(axis=0)&np.isfinite(widths).all(axis=0)&(np.min(widths,axis=0)>0)
    spectral &= np.ptp(waves,axis=0)<=.1*np.min(widths,axis=0)
    spectral &= np.max(widths,axis=0)<=1.10*np.min(widths,axis=0)
    for i,f in enumerate(q['sequence']):
        checks[i]['obs_id']=f['obs_id']
        checks[i]['positive_peak_screening']=bool((f['peak_minus_annulus_median_mjy_sr'] or 0)>0)
        checks[i]['defect_bits_in_source_core']=sorted(set(f['core_flag_bits'])&set(bad_bits))
    a,b=map(lambda f:SkyCoord(*f['predicted_target_deg'],unit='deg'),(q['sequence'][0],q['sequence'][-1]))
    result[k]={'grid_shape_yx':[npx,npx],'grid_center_deg':q['center_deg'],
       'pixel_scale_arcsec':6.15,'frames':checks,'joint_finite_fraction':float(footprint.mean()),
       'spectral_on_joint_finite_fraction_of_grid':float(np.mean(spectral&footprint)),
       'joint_strict_flag_and_spectral_fraction_of_grid_before_psf_margin':float(np.mean(spectral&good)),
       'first_last_prediction_displacement_arcsec':a.separation(b).arcsec,
       'scope':'Sampled WCS/spectral/quality geometry and visual assets; not a PSF-registered detection, photometric result, or measured centroid.'}
    pixels=np.concatenate([b[np.isfinite(b)&footprint] for b in fields])
    low,high=np.percentile(pixels,[2,99.5]);scale=max((high-low)/8,1e-10)
    for i,(b,c) in enumerate(zip(fields,centers)):
        panel=ax[n,i]; im=np.arcsinh((b-low)/scale)
        panel.imshow(im,cmap='gray',vmin=0,vmax=np.arcsinh(8),origin='lower')
        panel.scatter(*c,facecolors='none',edgecolors='orange',s=68,lw=.8)
        panel.set_title(q['sequence'][i]['utc_mid'][:10]+' UTC',fontsize=9);panel.set_xticks([]);panel.set_yticks([])
    ax[n,0].set_ylabel(k.replace('_',' '),fontsize=11)
    panel=ax[n,3];panel.imshow((spectral&good).astype(float),vmin=0,vmax=1,cmap='viridis',origin='lower')
    panel.set_title(f"Joint support {result[k]['joint_strict_flag_and_spectral_fraction_of_grid_before_psf_margin']:.1%}",fontsize=9)
    panel.set_xticks([]);panel.set_yticks([])
fig.suptitle('SPHEREx fixed-field research checks • real QR2 exposures\nOrange = predicted location, not detection; right = joint spectral + flag support before PSF margin',fontsize=12)
fig.savefig(p/'full_challenge_sequences_research.png',dpi=155,bbox_inches='tight')
(p/'full_challenge_common_grid_audit.json').write_text(json.dumps(result,indent=2,allow_nan=False))
for k,q in result.items():
    print(k,round(q['joint_finite_fraction'],4),round(q['spectral_on_joint_finite_fraction_of_grid'],4),
          round(q['joint_strict_flag_and_spectral_fraction_of_grid_before_psf_margin'],4),
          round(q['first_last_prediction_displacement_arcsec'],3),
          [f['defect_bits_in_source_core'] for f in q['frames']],flush=True)
