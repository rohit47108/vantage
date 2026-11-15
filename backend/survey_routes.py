"""Bounded, fixed-catalog context routes; no general-purpose query proxy."""
from fastapi import APIRouter,HTTPException,Query
from backend.surveys import sequence_manifest,layer,candidate_associations

router=APIRouter(tags=['Survey context'])

@router.get('/v1/surveys/{survey}')
def survey_layer(survey:str,sequence_id:str=Query(pattern=r'^[a-f0-9]{64}$')):
    if survey not in ['gaia','wise']:raise HTTPException(404,'This survey is not supported')
    try:return layer(survey,sequence_manifest(sequence_id))
    except FileNotFoundError as exc:raise HTTPException(404,'Sequence unavailable') from exc
    except RuntimeError as exc:raise HTTPException(429,'Catalog service busy. Retry shortly.') from exc
    except Exception as exc:raise HTTPException(502,f'{survey.title()} catalog unavailable or its schema changed. Retry; SPHEREx images remain available.') from exc

@router.get('/v1/associations')
def associations(sequence_id:str=Query(pattern=r'^[a-f0-9]{64}$')):
    try:
        sequence=sequence_manifest(sequence_id)
        gaia=layer('gaia',sequence);wise=layer('wise',sequence)
        pairs=candidate_associations(gaia['sources'],wise['sources'],limit=501)
        limited=len(pairs)>500 or any(s['search_completeness']=='limited' for s in [gaia,wise])
        return {'sequence_id':sequence_id,'pairs':pairs[:500],
                'radius_arcsec':2,'status':'candidate_associations_only',
                'search_completeness':'limited' if limited else 'complete_within_loaded_sources',
                'pair_limit_reached':len(pairs)>500,'pair_limit':500,
                'method':'Angular proximity after propagating Gaia to the WISE W1 mean MJD. That MJD approximates the positional epoch; observer parallax is not included.',
                'limitations':['Many-to-many candidates are retained. Proximity is not proof of identity.',
                               'Extended, blended, artifact-flagged sources and missing motions require review.',
                               'Only retained sources visible in a SPHEREx frame are compared; this is not a complete catalog cross-match.'],
                'source_queries':list(dict.fromkeys(gaia['query_urls']+wise['query_urls']))}
    except FileNotFoundError as exc:raise HTTPException(404,'Sequence unavailable') from exc
    except RuntimeError as exc:raise HTTPException(429,'Catalog service busy. Retry shortly.') from exc
    except Exception as exc:raise HTTPException(502,'Catalog associations are unavailable. Retry; no identities were assumed.') from exc
