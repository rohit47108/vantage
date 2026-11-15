"""Frozen source-discovery fields and validated general extraction requests."""
import hashlib
import json
import math
import requests
from urllib.parse import urlparse,parse_qs
from datetime import date,datetime,timezone
from pathlib import Path
from typing import Annotated
from astropy.time import Time
from pydantic import BaseModel,ConfigDict,Field,model_validator
from backend.archive import discover
from backend.native_extraction import SourcePosition,ExtractionOptions
from backend.calibration_registry import registry
from backend.science import write_json
from backend import archive

POLICY='native-source-discovery-1'


class SourceFieldRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    source:SourcePosition
    start_utc:date=Field(default_factory=lambda:date(2025,1,1))
    end_utc:date=Field(default_factory=lambda:datetime.now(timezone.utc).date())
    include_deep:bool=True
    refresh:bool=False

    @model_validator(mode='after')
    def dates(self):
        if self.end_utc<self.start_utc or (self.end_utc-self.start_utc).days>5*366:
            raise ValueError('Choose an increasing UTC date interval of at most five years')
        return self


class NativeExtractionRequest(ExtractionOptions):
    field_id:str=Field(pattern=r'^[a-f0-9]{64}$')
    observation_indices:list[Annotated[int,Field(ge=0,le=1999)]]=Field(min_length=1,max_length=512)
    refresh:bool=False

    @model_validator(mode='after')
    def unique_observations(self):
        if len(set(self.observation_indices))!=len(self.observation_indices):raise ValueError('Choose distinct native observation indices')
        return self


def retained_snapshot(center,fov,time_bounds):
    """Outage-only candidates from an enclosing, explicitly dated real query.

    This is never a fresh/inventory-complete query. A snapshot of another sky
    region or a narrower time window cannot stand in for the requested field.
    """
    requested_radius=fov/60/math.sqrt(2)+15/3600
    choices=[]
    for path in archive.CACHE.glob('*.json'):
        try:
            if path.stat().st_size>8_000_000:continue
            saved=json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(saved.get('observations'),list) or not saved.get('retrieved_utc'):continue
            if saved.get('search_completeness') not in ('complete','limited'):continue
            longitude,latitude=saved['center_deg'];radius=float(saved['fov_arcmin'])/60/math.sqrt(2)+15/3600
            if not all(math.isfinite(v) for v in [longitude,latitude,radius]) or abs(latitude)>90 or radius<=0:continue
            ra1,dec1,ra2,dec2=map(math.radians,[center[0],center[1],longitude,latitude])
            hav=math.sin((dec2-dec1)/2)**2+math.cos(dec1)*math.cos(dec2)*math.sin((ra2-ra1)/2)**2
            separation=math.degrees(2*math.asin(math.sqrt(max(0,min(1,hav)))))
            if radius<requested_radius+separation+1e-6:continue
            bounds=saved.get('time_bounds_mjd_utc')
            if bounds and not (bounds[0]<=time_bounds[0] and bounds[1]>=time_bounds[1]):continue
            if not saved.get('queries') or any(urlparse(url).scheme!='https' or urlparse(url).hostname!='irsa.ipac.caltech.edu' for url in saved['queries']):continue
            timestamp=datetime.fromisoformat(saved['retrieved_utc'].replace('Z','+00:00'))
            if timestamp.tzinfo is None:continue
            choices.append((saved.get('search_completeness')=='complete',timestamp.timestamp(),saved))
        except (ValueError,KeyError,TypeError,IndexError,OSError):continue
    if not choices:return None
    saved=max(choices,key=lambda row:row[:2])[2]
    collections=saved.get('collections') or list(dict.fromkeys(c for url in saved['queries'] for c in parse_qs(urlparse(url).query).get('COLLECTION',[])))
    return {**saved,'collections':collections,'data_status':'retained_metadata_snapshot',
        'snapshot_original_completeness':saved['search_completeness'],'search_completeness':'limited',
        'snapshot_note':'The live archive query failed. Candidates come from the dated enclosing query shown in provenance. New ingestion, unqueried collections and the current inventory are not established by this snapshot.'}


def build_source_field(request,destination,check_cancel=lambda:None):
    # Dates are resolved in the request before it is stored in the job queue;
    # recovery tomorrow must not silently change the end of today's search.
    start=float(Time(request.start_utc.isoformat(),scale='utc').mjd)
    end=float(Time(request.end_utc.isoformat(),scale='utc').mjd)+1
    midpoint=request.source.position((start+end)/2)
    angular=math.hypot(request.source.pmra or 0,request.source.pmdec or 0)*(end-start)/365.25/2000
    fov=max(.5,(angular+60-15)/60*math.sqrt(2))
    check_cancel()
    try:found=discover(midpoint,fov,refresh=request.refresh,include_deep=request.include_deep,time_bounds=[start,end])
    except requests.RequestException as exc:
        found=retained_snapshot(midpoint,fov,[start,end])
        if found is None:raise
        found['failed_query']={'url':getattr(exc.request,'url',None),'status':getattr(exc.response,'status_code',None),'error':type(exc).__name__}
    check_cancel()
    approved=registry();releases=sorted({r['release'] for r in approved['bindings']})
    observations=[]
    for row in found['observations']:
        if start<=row['mjd_mid']<end:
            observations.append({**row,'index':len(observations),
                'utc_mid':Time(row['mjd_mid'],format='mjd',scale='utc').isot+'Z',
                'measurement_capability':'requires_native_checks' if row['release'] in releases else 'release_not_approved'})
    canonical={'policy':POLICY,'request':request.model_dump(mode='json'),
        'source':request.source.model_dump(),'time_bounds_mjd_utc':[start,end],
        'discovery':found,'observations':observations,'calibration_registry_policy':approved['policy'],'approved_calibrations':approved}
    identity=hashlib.sha256(json.dumps(canonical,sort_keys=True,allow_nan=False).encode()).hexdigest()
    result={'schema_version':'1.0.0','id':identity,'type':'source_field','name':request.source.name+' · observation field',**canonical,
        'approved_releases':releases,'candidate_observations':sum(r['measurement_capability']=='requires_native_checks' for r in observations),
        'unsupported_release_observations':sum(r['measurement_capability']=='release_not_approved' for r in observations),
        'search_completeness':found['search_completeness'],
        'selection_semantics':'UTC acquisition midpoint in the inclusive start/end calendar-date interval. Discovery uses a circumscribed source/motion search; native coverage, flags, exact calibration and residuals are checked during extraction.',
        'limitations':['A footprint-query match is not proof that the native source/background region is covered or usable.',
            'Overflow or capped metadata searches remain incomplete. Refine the dates when coverage is limited.',
            'New files can appear in SIA about a day after archive ingestion. This search is not an instantaneous inventory of all ingested data.',
            'Only exact approved release/processing/calibration inputs can be measured. Other release records remain visible but are not selected for extraction.',
            'Angular motion omits observer parallax and perspective acceleration. A fixed ICRS request does not infer source motion.']}
    folder=Path(destination)/identity;folder.mkdir(parents=True,exist_ok=True)
    check_cancel();write_json(folder/'manifest.json',result)
    return result
