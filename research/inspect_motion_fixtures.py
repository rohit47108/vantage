from inspect_fits import *
from native_crop_research import remote_native_crop
from scipy.ndimage import map_coordinates
from astropy.time import Time
from astropy.stats import sigma_clipped_stats
from astropy.wcs.utils import fit_wcs_from_points
__import__('astropy.logger').log.setLevel('ERROR')
records=[]
for obj,keys in [('comet',['2025W32_1A_0662_3','2025W32_2D_0017_4']),('ceres',['2025W27_1A_0591_4','2025W27_1A_0632_1'])]:
 scan=json.loads((EV/(obj+'_d'+('3' if obj=='comet' else '2')+'_precision_scan.json')).read_text())
 for i,key in enumerate(keys):
  row=next(x for x in scan if x['obs_id']==key);name=obj+'_epoch_'+('a' if i==0 else 'b');p=remote_native_crop(name,row,row['ra_deg'],row['dec_deg']);r=inspect(name,p,(row['ra_deg'],row['dec_deg']))
  with fits.open(p) as h:
   img=h['IMAGE'].data;flags=h['FLAGS'].data.astype(np.uint32);variance=h['VARIANCE'].data;w=WCS(h['IMAGE'].header);x,y=w.world_to_pixel(SkyCoord(row['ra_deg'],row['dec_deg'],unit='deg'));yy,xx=np.indices(img.shape);rr=np.hypot(xx-x,yy-y);good=(flags&sum(1<<b for b in [0,1,2,6,7,9,10,11,12,14,15,17,19,20,22,24,25,26,27,28,29]))==0;ann=(rr>8)&(rr<20)&good;_,bg,sd=sigma_clipped_stats(img[ann]);core=(rr<4)&good
   peak=np.unravel_index(np.nanargmax(np.where(core,img-bg,np.nan)),img.shape);weights=np.where(core,np.maximum(img-bg-2*sd,0),0);cx=float((weights*xx).sum()/weights.sum());cy=float((weights*yy).sum()/weights.sum());sky=w.pixel_to_world(cx,cy);offset=float(sky.separation(SkyCoord(row['ra_deg'],row['dec_deg'],unit='deg')).arcsec)
   d={k:v for k,v in row.items() if k!='header'}|{'fixture':name+'.fits','background_MJy_sr':float(bg),'annulus_scatter_MJy_sr':float(sd),'peak_pixel_yx':[int(v) for v in peak],'positive_weight_centroid_xy':[cx,cy],'centroid_ra_deg':float(sky.ra.deg),'centroid_dec_deg':float(sky.dec.deg),'centroid_prediction_offset_arcsec':offset,'peak_empirical_snr':float((img[peak]-bg)/sd),'method':'research screening only; positive-weight centroid, no PSF fit or crowding correction'};records.append(d);print(obj,d,flush=True)
  import matplotlib.pyplot as plt
  fig,ax=plt.subplots(figsize=(5,5));v=np.nanpercentile(img,[5,99.5]);ax.imshow(img,origin='lower',cmap='gray',vmin=v[0],vmax=v[1]);ax.plot(x,y,'rx',label='Predicted position');ax.plot(cx,cy,'co',fillstyle='none',label='Screening centroid');ax.set_title(name+' '+Time(row['mjd'],format='mjd').isot);ax.legend();fig.tight_layout();fig.savefig(EV/(name+'_screening.png'),dpi=130);plt.close(fig)
(EV/'motion_fixture_screening.json').write_text(json.dumps(records,indent=2,default=str))
