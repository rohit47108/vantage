from inspect_fits import *
from native_crop_research import remote_native_crop
__import__('astropy.logger').log.setLevel('ERROR')
d=json.loads((EV/'m101_qr2_cutout_download.json').read_text());url=d['url'].split('?')[0];p=remote_native_crop('native_crop_equivalence_check',{'url':url},210.80227,54.34895)
with fits.open(p) as a,fits.open(FIX/'m101_qr2_cutout.fits') as b:
 out={'purpose':'Compare S3 native-section research fallback against authentic IBE native cutout of same parent/bounds','arrays_equal':{},'hdu_names_equal':[x.name for x in a]==[x.name for x in b]}
 for name in ['IMAGE','FLAGS','VARIANCE','ZODI','PSF']:out['arrays_equal'][name]=bool(np.array_equal(a[name].data,b[name].data,equal_nan=True))
 out['wcs_wave_values_equal']=bool(np.array_equal(a['WCS-WAVE'].data['VALUES'],b['WCS-WAVE'].data['VALUES'],equal_nan=True))
 xy=[]
 for h in [a,b]:
  w=WCS(h['IMAGE'].header);x,y=w.world_to_pixel(SkyCoord(210.80227,54.34895,unit='deg'));sw=WCS(h['IMAGE'].header,fobj=h,key='W');sw.sip=None;la,bw=sw.pixel_to_world(x,y);xy.append([float(x),float(y),float(la.value),float(bw.value)])
 out['wcs_coordinate_values']=xy;out['max_wcs_difference']=float(np.max(np.abs(np.array(xy[0])-np.array(xy[1]))));out['passed']=all(out['arrays_equal'].values()) and out['hdu_names_equal'] and out['wcs_wave_values_equal'] and out['max_wcs_difference']<1e-8
(EV/'native_crop_equivalence.json').write_text(json.dumps(out,indent=2));print(json.dumps(out));assert out['passed']
