"""Real P330E flux/geometry consistency check and retained diagnostics.

Tolerances are declared before evaluation. CALSPEC comparison uses a top-hat
approximation from CWAVE/CBAND, not an unavailable exact per-pixel response.
P330E itself is an SPHEREx calibrator: this checks the reduction, not the
independence or absolute correctness of the mission's gain scale.
"""
import json
from datetime import datetime,timezone
import numpy as np
import astropy.units as u
from astropy.io import fits
from astropy.wcs import WCS
from scipy.ndimage import map_coordinates
from backend.science import ROOT
from backend.photometry import measure_fits,solid_angle_for_image

FLUX_TOLERANCE=.10
METHOD_TOLERANCE=.05
AREA_TOLERANCE=.001
MAX_REDUCED_CHI2=3.


def reference_flux(path,wavelength,bandwidth):
    with fits.open(path,memmap=False) as hdus:
        if str(hdus[1].columns['WAVELENGTH'].unit).upper()!='ANGSTROMS' or str(hdus[1].columns['FLUX'].unit).upper()!='FLAM':
            raise ValueError('CALSPEC reference units/schema changed')
        wave=np.asarray(hdus[1].data['WAVELENGTH'],dtype=float)/10000
        selected=(wave>wavelength-bandwidth)&(wave<wavelength+bandwidth)
        flux=np.asarray(hdus[1].data['FLUX'][selected],dtype=float)*u.erg/u.s/u.cm**2/u.AA
        wave=wave[selected]
        fnu=flux.to_value(u.uJy,equivalencies=u.spectral_density(wave*u.um))
    low,high=wavelength-bandwidth/2,wavelength+bandwidth/2
    axis=np.r_[low,wave[(wave>low)&(wave<high)],high]
    return float(np.trapezoid(np.interp(axis,wave,fnu),axis)/bandwidth)


def spherical_pixel_area(wcs,x,y):
    ra,dec=np.deg2rad(wcs.pixel_to_world_values(np.array([x-.5,x+.5,x+.5,x-.5]),np.array([y-.5,y-.5,y+.5,y+.5])))
    v=np.column_stack([np.cos(dec)*np.cos(ra),np.cos(dec)*np.sin(ra),np.sin(dec)])
    def triangle(a,b,c):return 2*np.arctan2(abs(np.dot(a,np.cross(b,c))),1+np.dot(a,b)+np.dot(b,c)+np.dot(c,a))
    return triangle(v[0],v[1],v[2])+triangle(v[0],v[2],v[3])


def validate():
    folder=ROOT/'research/updates/2026-11-15/photometry'
    benchmark=json.loads((folder/'benchmark.json').read_text(encoding='utf-8'))
    records=[]
    for row in benchmark['observations']:
        x,y=row['position_pixel'];record={'obs_id':row['obs_id'],'mjd_mid':row['mjd_mid'],'position_pixel':[x,y]}
        try:
            with fits.open(ROOT/row['path'],memmap=False) as hdus,fits.open(folder/'sapm_d2.fits',memmap=False) as area:
                header=hdus['IMAGE'].header
                if not 0<=x<hdus['IMAGE'].data.shape[1] or not 0<=y<hdus['IMAGE'].data.shape[0]:
                    raise ValueError('Native cutout does not cover the source position')
                with fits.open(ROOT/row['calibration_path'],memmap=False) as calibration:
                    parent_x,parent_y=x+1-header['CRPIX1A'],y+1-header['CRPIX2A']
                    wave=float(map_coordinates(calibration['CWAVE'].data,[[parent_y],[parent_x]],order=1)[0])
                    width=float(map_coordinates(calibration['CBAND'].data,[[parent_y],[parent_x]],order=1)[0])
                record.update({'wavelength_um':wave,'bandwidth_um':width,'reference_top_hat_flux_ujy':reference_flux(folder/'p330e_mod_009.fits',wave,width)})
                omega=solid_angle_for_image(area,header,hdus['IMAGE'].data.shape)
                ix,iy=int(round(x)),int(round(y))
                geometric=spherical_pixel_area(WCS(header),ix,iy)
                record['solid_angle_relative_error']=float(abs(omega[iy,ix]/geometric-1))
                results={method:measure_fits(hdus,area,x,y,method=method,refine_centroid=True) for method in ['psf','aperture']}
                for method,result in results.items():
                    record[method]={k:result[k] for k in ['flux_ujy','statistical_sigma_ujy','reduced_chi2','background_pixels','core_support_fraction','aperture_throughput','pixel_flags_union','epsf']}
                    record[method]['relative_reference_error']=result['flux_ujy']/record['reference_top_hat_flux_ujy']-1
                    record[method]['centroid_fit']={k:v for k,v in result['centroid_fit'].items() if k!='covariance'}
                record['method_relative_difference']=abs(results['psf']['flux_ujy']/results['aperture']['flux_ujy']-1)
                record['flux_consistency_pass']=all(abs(record[m]['relative_reference_error'])<FLUX_TOLERANCE for m in results)
                record['method_consistency_pass']=record['method_relative_difference']<METHOD_TOLERANCE
                record['geometry_pass']=record['solid_angle_relative_error']<AREA_TOLERANCE
                record['fit_quality_pass']=all(r['reduced_chi2']<MAX_REDUCED_CHI2 for r in results.values())
        except (ValueError,IndexError) as exc:record['rejected_reason']=str(exc)
        records.append(record);print(json.dumps(record),flush=True)
    result={'checked_utc':datetime.now(timezone.utc).isoformat(),'tolerances':{'reference_relative':FLUX_TOLERANCE,'method_relative':METHOD_TOLERANCE,'solid_angle_relative':AREA_TOLERANCE,'maximum_reduced_chi2':MAX_REDUCED_CHI2},
            'records':records,'reference_interpretation':'CALSPEC model, uniform wavelength top-hat approximation. This tests reduction consistency; it is not exact bandpass synthesis or an independent absolute-gain validation.',
            'passes_current_benchmark_checks':[r['obs_id'] for r in records if r.get('fit_quality_pass') and r.get('geometry_pass') and r.get('flux_consistency_pass') and r.get('method_consistency_pass')],
            'all_methods_complete':False,'public_spectrum_workflow_complete':False}
    (ROOT/'artifacts/photometry-scientific-validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    eligible=[r for r in records if 'rejected_reason' not in r]
    assert len(eligible)>=2,'Need at least two actual usable measurements'
    assert all(r['flux_consistency_pass'] and r['method_consistency_pass'] and r['geometry_pass'] for r in eligible),'Real-data reduction checks failed; inspect retained evidence'
    assert any(r['fit_quality_pass'] for r in eligible),'No real sample meets the predeclared residual quality criterion'
    return result

if __name__=='__main__':validate()
