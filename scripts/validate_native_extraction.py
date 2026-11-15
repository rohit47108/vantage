"""All-six-detector native reduction consistency, with declared tolerances.

P330E is also used by the mission calibration. This is not an independent
absolute-gain validation. CALSPEC synthesis uses a central CWAVE/CBAND top-hat.
"""
import json
from datetime import datetime,timezone
from backend.science import ROOT
from backend.native_extraction import SourcePosition,ExtractionOptions,extract_observations
from scripts.validate_photometry import reference_flux

FLUX_TOLERANCE=.10
METHOD_TOLERANCE=.05
AREA_TOLERANCE=.001
MAXIMUM_RESIDUAL_SCORE=3.


def validate():
    folder=ROOT/'research/updates/2026-11-15/native-extraction'
    acquisition=json.loads((folder/'acquisition.json').read_text(encoding='utf-8'))
    old=json.loads((ROOT/'research/updates/2026-11-15/photometry/benchmark.json').read_text(encoding='utf-8'))
    rows=acquisition['observations']+[old['observations'][1]]
    source=SourcePosition(name='P330E',**{k:old['source'][k] for k in ['ra','dec','pmra','pmdec','ref_epoch']})
    paths={(r['obs_id'],r['detector']):(ROOT/r['path'],r['retrieval_mode']) for r in rows}
    products={method:extract_observations(rows,source,ExtractionOptions(method=method),ROOT/'.runtime/native-validation',
        native_loader=lambda row,position:paths[(row['obs_id'],row['detector'])]) for method in ['psf','aperture']}
    reference=ROOT/'research/updates/2026-11-15/photometry/p330e_mod_009.fits'
    records=[]
    for method,product in products.items():
        for sample in product['samples']:
            record={k:sample.get(k) for k in ['obs_id','detector','mjd_mid','status','reason','wavelength_um','bandwidth_um','flux_ujy','statistical_sigma_ujy','reduced_chi2','solid_angle_wcs_ratio']}
            record['method']=method
            if sample['flux_ujy'] is not None:
                ref=reference_flux(reference,sample['wavelength_um'],sample['bandwidth_um'])
                record.update({'reference_top_hat_flux_ujy':ref,'relative_reference_error':sample['flux_ujy']/ref-1})
            records.append(record)
    accepted=[r for r in records if r['status']=='accepted']
    assert {r['detector'] for r in accepted if r['method']=='psf'}==set(range(1,7)),'Need successful actual PSF measurements on all six detectors'
    assert {r['detector'] for r in accepted if r['method']=='aperture'}==set(range(1,6)),'Aperture benchmark changed; inspect retained failures and fluxes'
    assert all(abs(r['relative_reference_error'])<FLUX_TOLERANCE for r in accepted),'CALSPEC reduction consistency failed'
    assert all(abs(r['solid_angle_wcs_ratio']-1)<AREA_TOLERANCE for r in accepted),'Native WCS/SAPM area consistency failed'
    assert all(r['reduced_chi2']<MAXIMUM_RESIDUAL_SCORE for r in accepted),'Declared residual gate failed'
    pairs=[]
    for psf in [r for r in accepted if r['method']=='psf']:
        aperture=next((r for r in accepted if r['method']=='aperture' and r['obs_id']==psf['obs_id'] and r['detector']==psf['detector']),None)
        if aperture:
            difference=abs(aperture['flux_ujy']/psf['flux_ujy']-1)
            assert difference<METHOD_TOLERANCE,'Aperture/PSF method consistency failed'
            pairs.append({'obs_id':psf['obs_id'],'detector':psf['detector'],'relative_difference':difference})
    result={'checked_utc':datetime.now(timezone.utc).isoformat(),'tolerances':{'reference_relative':FLUX_TOLERANCE,'method_relative':METHOD_TOLERANCE,'area_relative':AREA_TOLERANCE,'maximum_residual_score':MAXIMUM_RESIDUAL_SCORE},
        'records':records,'method_comparisons':pairs,'product_ids':{k:v['id'] for k,v in products.items()},
        'all_six_detector_psf_measurements_pass':True,'complete_102_channel_spectrum':False,
        'interpretation':'Native reduction consistency on the supplied isolated calibration-star cases. CALSPEC is not an independent mission gain reference. Uniform-wavelength top-hat synthesis is not exact response integration. Statistical errors omit unprovided calibration, PSF and native-correlation terms.'}
    (ROOT/'artifacts/native-extraction-scientific-validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'all_six_detector_psf_measurements_pass':True,'accepted_measurements':len(accepted),'method_pairs':len(pairs),'product_ids':result['product_ids']}))
    return result


if __name__=='__main__':validate()
