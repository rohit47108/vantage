from inspect_fits import *
from scipy.ndimage import map_coordinates
from reproject import reproject_interp
from astropy.time import Time
import warnings
__import__('astropy.logger').log.setLevel('ERROR')
hs=[fits.open(FIX/(n+'.fits')) for n in ['m101_epoch_a','m101_epoch_b']];hdr=hs[0]['IMAGE'].header.copy();wout=WCS(hdr);shape=hs[0]['IMAGE'].data.shape
with fits.open(FIX/'spectral_wcs_d2.fits') as cal:
 wave,bw=cal['CWAVE'].data,cal['CBAND'].data
 yy,xx=np.indices(shape);world=wout.pixel_to_world(xx,yy);maps=[];im=[];mask=[];vari=[];probes=[]
 for h in hs:
  w=WCS(h['IMAGE'].header);x,y=w.world_to_pixel(world);px=1+x-h['IMAGE'].header['CRPIX1A'];py=1+y-h['IMAGE'].header['CRPIX2A'];lam=map_coordinates(wave,[py,px],order=1,mode='constant',cval=np.nan);width=map_coordinates(bw,[py,px],order=1,mode='constant',cval=np.nan);maps.append((lam,width));a,f=reproject_interp((h['IMAGE'].data,w),wout,shape_out=shape);im.append(a)
  flags=h['FLAGS'].data.astype(np.uint32);badbits=sum(1<<b for b in [0,1,2,4,5,6,7,9,10,11,12,14,15,17,19,20,22,23,24,25,26,27,28,29]);good=((flags&badbits)==0)&np.isfinite(h['IMAGE'].data)&np.isfinite(h['VARIANCE'].data)&(h['VARIANCE'].data>0);g,_=reproject_interp((good.astype(float),w),wout,shape_out=shape);mask.append((g>.999)&(f>.999))
 m=np.abs(maps[0][0]-maps[1][0])/np.minimum(maps[0][1],maps[1][1]);valid=mask[0]&mask[1]&np.isfinite(m)&(m<=.1);d=im[1]-im[0];res={'purpose':'research spectral coverage audit; not validated PSF-matched difference','shape_yx':shape,'central_bilinear_wave_um':[float(z[0][29,29]) for z in maps],'spectral_eligible_pixels':int(np.count_nonzero(m<=.1)),'spectral_eligible_fraction':float(np.mean(m<=.1)),'strict_quality_and_spectral_pixels':int(valid.sum()),'central_mismatch_bandwidths':float(m[29,29]),'median_difference_MJy_sr_unmatched_psf':float(np.nanmedian(d[valid])),'mjd_mid':[h['IMAGE'].header.get('MJD-AVG') for h in hs]}
 (EV/'m101_pair_coverage_audit.json').write_text(json.dumps(res,indent=2));print(json.dumps(res),flush=True)
 import matplotlib.pyplot as plt
 fig,axs=plt.subplots(1,3,figsize=(12,4));lo,hi=np.nanpercentile(np.concatenate(im),[5,99]);
 for ax,a,title in zip(axs,im+ [m],['M101: May 29 2025','M101: December 7 2025','Spectral mismatch / narrower bandwidth']):
  ax.imshow(a,origin='lower',cmap='gray' if a is not m else 'viridis',vmin=lo if a is not m else 0,vmax=hi if a is not m else .5);ax.set_title(title);ax.set_xlabel('Native A-grid x pixel')
 axs[2].contour(m,levels=[.1],colors=['red']);fig.suptitle('Research check: real native cutouts; wavelength compatibility varies across the field');fig.tight_layout();fig.savefig(EV/'m101_coverage_research.png',dpi=160);plt.close(fig)
for h in hs:h.close()
