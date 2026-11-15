import {useCallback,useEffect,useRef,useState} from 'react';
import {Brand} from './Brand';
import {NameLookup} from './NameLookup';
import {json,readResponse} from './api';
import {NativeStamp,SampleChart} from './SourceSamples';
import {SourceSummaryPanel} from './SourceSummaryPanel';
import type {Sample} from './SourceSamples';
import './sources.css';

export interface SourceSeed {name?:string;ra:number;dec:number;pmra?:number|null;pmdec?:number|null;ref_epoch?:number}
interface Observation {index:number;obs_id:string;detector:number;release:string;utc_mid:string;measurement_capability:string}
interface SourceField {id:string;type:string;source:SourceSeed;request:{source:SourceSeed;start_utc:string;end_utc:string;include_deep:boolean};observations:Observation[];candidate_observations:number;unsupported_release_observations:number;search_completeness:string;discovery:{data_status:string;retrieved_utc?:string;snapshot_note?:string}}
interface Options {method:string;centroid_mode:string;aperture_radius:number;background_inner:number;background_outer:number}
interface NativeProduct {id:string;type:string;data_status:string;name:string;source:SourceSeed;request:Options&{field_id?:string;observation_indices?:number[]};samples:Sample[];sampling:{accepted_samples:number;diagnostic_only_samples:number;rejected_samples:number;interpretation:string};uncertainty_method:string;limitations:string[];credits:string;exports:Record<string,{url:string}>}
interface Job {job_id:string;state:string;result_id:string|null;error:string|null}
const defaults:Options={method:'psf',centroid_mode:'auto',aperture_radius:2.5,background_inner:5,background_outer:8};
const terminal=(job:Job|null)=>!job||['complete','failed','cancelled'].includes(job.state);
const key=(s:{obs_id:string;detector:number;sample_id?:string})=>s.sample_id??`${s.obs_id}/D${s.detector}`;
const n=(v:number|null|undefined,digits=2)=>v==null?'—':v.toLocaleString('en-US',{minimumFractionDigits:digits,maximumFractionDigits:digits});

function sourceFromLink(params:URLSearchParams):{seed:SourceSeed|null;error:string}{
  if(!params.has('source_ra')&&!params.has('source_dec'))return {seed:null,error:''};
  const ra=Number(params.get('source_ra')),dec=Number(params.get('source_dec'));
  if(!params.has('source_ra')||!params.has('source_dec')||!Number.isFinite(ra)||!Number.isFinite(dec)||ra<0||ra>=360||Math.abs(dec)>90)return {seed:null,error:'The source link contains invalid coordinates. Enter a source position.'};
  const result:SourceSeed={ra,dec,name:params.get('source_name')??'Selected sky position'};
  if(params.has('pmra')||params.has('pmdec')){
    const pmra=Number(params.get('pmra')),pmdec=Number(params.get('pmdec')),epoch=Number(params.get('ref_epoch')??2016);
    if(!params.has('pmra')||!params.has('pmdec')||!Number.isFinite(pmra)||!Number.isFinite(pmdec)||Math.abs(pmra)>12000||Math.abs(pmdec)>12000||!Number.isFinite(epoch)||epoch<1900||epoch>2100)return {seed:null,error:'The source link needs both valid motion components and their reference epoch.'};
    Object.assign(result,{pmra,pmdec,ref_epoch:epoch});
  }
  return {seed:result,error:''};
}

export function LiveSourceExplorer({onTime,seed}:{onTime:()=>void;seed?:SourceSeed|null}){
  const initial=new URLSearchParams(location.search);
  const linked=sourceFromLink(initial),inputSeed=seed??linked.seed;
  const [form,setForm]=useState(()=>({name:inputSeed?.name??'Selected sky position',ra:inputSeed?String(inputSeed.ra):'',dec:inputSeed?String(inputSeed.dec):'',
    motion:inputSeed?.pmra!=null&&inputSeed?.pmdec!=null,pmra:inputSeed?.pmra==null?'':String(inputSeed.pmra),pmdec:inputSeed?.pmdec==null?'':String(inputSeed.pmdec),ref_epoch:String(inputSeed?.ref_epoch??2016),
    start_utc:'2025-01-01',end_utc:new Date().toISOString().slice(0,10),include_deep:true}));
  const [field,setField]=useState<SourceField|null>(null),[product,setProduct]=useState<NativeProduct|null>(null);
  const [selected,setSelected]=useState<number[]>([]),[options,setOptions]=useState(defaults);
  const [job,setJob]=useState<Job|null>(null),[submitting,setSubmitting]=useState(false),[exampleLoading,setExampleLoading]=useState(false),[restoring,setRestoring]=useState(!!(initial.get('samples')||initial.get('field')));
  const [error,setError]=useState(linked.error),[fieldWarning,setFieldWarning]=useState(''),[filter,setFilter]=useState(''),[page,setPage]=useState(0);
  const [sampleId,setSampleId]=useState(''),[link,setLink]=useState(''),[quality,setQuality]=useState(initial.get('quality')==='passing'?'passing':'all');
  const [context,setContext]=useState<NonNullable<Sample['image_context']>|null>(null),[contextError,setContextError]=useState(''),[contextRetry,setContextRetry]=useState(0);
  const [timeSelection,setTimeSelection]=useState<Set<string>|null>(null);
  const sampleHeading=useRef<HTMLHeadingElement>(null);
  const applyTimeSelection=useCallback((ids:string[]|null)=>{
    setTimeSelection(ids?new Set(ids):null);
    if(ids)setSampleId(current=>{
      const visible=product?.samples.filter(s=>ids.includes(key(s))&&(quality==='all'||s.status==='accepted'))??[];
      if(visible.some(s=>key(s)===current))return current;
      const first=visible.find(s=>s.status==='accepted')??visible[0];return first?key(first):'';
    });
  },[product,quality]);
  const mounted=useRef(true),heading=useRef<HTMLHeadingElement>(null),fieldHeading=useRef<HTMLHeadingElement>(null),cache=useRef(new Map<string,NonNullable<Sample['image_context']>>());
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
  const busy=submitting||exampleLoading||restoring||!terminal(job);
  function restoreSource(source:SourceSeed,dates?:{start_utc:string;end_utc:string;include_deep:boolean}){
    setForm(f=>({...f,name:source.name??'Selected sky position',ra:String(source.ra),dec:String(source.dec),motion:source.pmra!=null&&source.pmdec!=null,
      pmra:source.pmra==null?'':String(source.pmra),pmdec:source.pmdec==null?'':String(source.pmdec),ref_epoch:String(source.ref_epoch??2016),...(dates?{start_utc:dates.start_utc,end_utc:dates.end_utc,include_deep:dates.include_deep}:{})}));
  }
  function showField(value:SourceField,selection?:number[]){
    if(value.type!=='source_field')throw new Error('This resource is not a source-discovery field.');
    setField(value);restoreSource(value.source,value.request);
    const candidates=value.observations.filter(r=>r.measurement_capability==='requires_native_checks').map(r=>r.index);
    setSelected(selection??(candidates.length<=512?candidates:[]));setFilter('');setPage(0);
  }
  async function showProduct(value:NativeProduct,signal?:AbortSignal){
    if(value.type!=='source_samples'||value.data_status!=='native_exposure_measurements')throw new Error('Open a general native source-measurement product.');
    setProduct(value);setOptions({method:value.request.method,centroid_mode:value.request.centroid_mode,
      aperture_radius:value.request.aperture_radius,background_inner:value.request.background_inner,background_outer:value.request.background_outer});restoreSource(value.source);setLink('');
    const desired=new URLSearchParams(location.search).get('sample');
    const desiredSample=value.samples.find(s=>key(s)===desired&&(quality!=='passing'||s.status==='accepted'));
    setSampleId(desiredSample?key(desiredSample):key(value.samples.find(s=>s.status==='accepted')??value.samples[0]));
    if(!value.request.field_id){setField(null);setSelected([]);setFieldWarning('This native result was measured from explicitly selected exposures without a saved discovery field. Its measurements and provenance remain available; find source observations to make a new selection.');}
    else try{
      const parent=await json<SourceField>('/v1/products/'+value.request.field_id,{signal});
      if(!signal?.aborted&&mounted.current){showField(parent,value.request.observation_indices);setFieldWarning('');}
    }catch(e){if(!signal?.aborted&&mounted.current)setFieldWarning('Discovery metadata could not be restored. The saved measurements and their provenance remain readable.');}
    if(!signal?.aborted&&mounted.current)setTimeout(()=>heading.current?.focus(),0);
  }
  useEffect(()=>{
    const abort=new AbortController();
    const params=new URLSearchParams(location.search),saved=params.get('samples')||params.get('field'),pending=params.get('job');
    if(pending&&/^[a-f0-9]{32}$/.test(pending)){setJob({job_id:pending,state:'queued',result_id:null,error:null});setRestoring(false);return()=>abort.abort();}
    if(!saved){setRestoring(false);return()=>abort.abort();}
    json<SourceField|NativeProduct>('/v1/products/'+encodeURIComponent(saved),{signal:abort.signal}).then(async value=>{
      if(abort.signal.aborted)return;
      if(value.type==='source_field')showField(value as SourceField);else await showProduct(value as NativeProduct,abort.signal);
    }).catch(e=>{if(!abort.signal.aborted)setError(e.message);}).finally(()=>{if(!abort.signal.aborted)setRestoring(false);});
    return()=>abort.abort();
  },[]);
  useEffect(()=>{
    if(!job||terminal(job))return;
    const abort=new AbortController();let timer:ReturnType<typeof setTimeout>;
    const poll=async()=>{
      try{
        const current=await json<Job>('/v1/analysis/jobs/'+job.job_id,{signal:abort.signal});
        if(abort.signal.aborted)return;
        if(current.state==='complete'&&current.result_id){
          const value=await json<SourceField|NativeProduct>('/v1/products/'+current.result_id,{signal:abort.signal});
          if(abort.signal.aborted)return;
          if(value.type==='source_field'){showField(value as SourceField);history.replaceState(null,'','/?view=measure&field='+value.id);setTimeout(()=>fieldHeading.current?.focus(),0);}
          else{history.replaceState(null,'','/?view=measure&samples='+value.id);await showProduct(value as NativeProduct,abort.signal);}
          if(!abort.signal.aborted){setJob(current);setError('');}return;
        }
        if(current.state==='failed'||current.state==='cancelled'){setJob(current);setError(current.error||'Cancelled. Update the selection and run again.');return;}
        if(current.state!==job.state)setJob(current);setError('');
      }catch(e){if(!abort.signal.aborted)setError((e as Error).message+' Reconnecting to the stored job…');}
      if(!abort.signal.aborted)timer=setTimeout(poll,1000);
    };void poll();return()=>{abort.abort();clearTimeout(timer);};
  },[job?.job_id,job?.state]);
  const sample=product?.samples.find(s=>key(s)===sampleId);
  useEffect(()=>{
    setContext(null);setContextError('');if(!sample)return;
    if(sample.image_context){setContext(sample.image_context);return;}
    const resource=(sample as Sample&{image_context_url?:string;image_context_sha256?:string});
    if(!resource.image_context_url)return;
    const saved=cache.current.get(resource.image_context_url);if(saved){setContext(saved);return;}
    const abort=new AbortController();
    const load=async()=>{
      const response=await fetch(resource.image_context_url!,{signal:abort.signal});if(!response.ok){await readResponse(response);return;}
      const bytes=await response.arrayBuffer();if(bytes.byteLength>1_000_000)throw new Error('Native inspection exceeds the supported display size.');
      const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(v=>v.toString(16).padStart(2,'0')).join('');
      if(hash!==resource.image_context_sha256)throw new Error('Native inspection checksum differs from the saved product.');
      const value=JSON.parse(new TextDecoder().decode(bytes));
      if(abort.signal.aborted)return;
      if(cache.current.size>=6)cache.current.delete(cache.current.keys().next().value!);
      cache.current.set(resource.image_context_url!,value);setContext(value);
    };void load().catch(e=>{if(!abort.signal.aborted)setContextError(e.message);});return()=>abort.abort();
  },[product?.id,sampleId,contextRetry]);
  function clearResult(){setProduct(null);setLink('');setContext(null);setTimeSelection(null);setError('');setFieldWarning('');history.replaceState(null,'',field?'/?view=measure&field='+field.id:'/?view=measure');}
  function edit(patch:Partial<typeof form>){setForm(f=>({...f,...patch}));setField(null);setSelected([]);clearResult();history.replaceState(null,'','/?view=measure');}
  async function submit(path:string,body:unknown){
    setSubmitting(true);setError('');clearResult();
    try{const response=await json<{job_id:string}>(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      if(mounted.current){setJob({job_id:response.job_id,state:'queued',result_id:null,error:null});history.replaceState(null,'','/?view=measure&job='+response.job_id);}
    }catch(e){if(mounted.current)setError((e as Error).message);}finally{if(mounted.current)setSubmitting(false);}
  }
  async function find(refresh=false){
    if(form.motion&&(!form.pmra.trim()||!form.pmdec.trim()||!form.ref_epoch.trim())){setError('Enter both catalog-motion components and their reference epoch. Open the catalog-motion controls to complete them.');return;}
    setField(null);setSelected([]);
    await submit('/v1/source-fields',{source:{name:form.name,ra:Number(form.ra),dec:Number(form.dec),...(form.motion?{pmra:Number(form.pmra),pmdec:Number(form.pmdec),ref_epoch:Number(form.ref_epoch)}:{})},
      start_utc:form.start_utc,end_utc:form.end_utc,include_deep:form.include_deep,refresh});
  }
  async function example(){
    setError('');setExampleLoading(true);try{const value=await json<{source:SourceSeed}>('/v1/source-targets/p330e');if(mounted.current){edit({});restoreSource({...value.source,name:'P330E'},{start_utc:'2025-07-01',end_utc:'2025-07-31',include_deep:true});}}
    catch(e){if(mounted.current)setError((e as Error).message);}finally{if(mounted.current)setExampleLoading(false);}
  }
  async function cancel(){if(!job)return;try{const state=await json<{state:string}>('/v1/analysis/jobs/'+job.job_id,{method:'DELETE'});if(mounted.current)setJob({...job,state:state.state==='complete'?'queued':state.state});}catch(e){if(mounted.current)setError((e as Error).message);}}
  const filtered=field?.observations.filter(r=>!filter||r.obs_id.includes(filter))??[];
  const visible=filtered.slice(page*25,page*25+25);
  const timeSamples=product?.samples.filter(s=>timeSelection==null||timeSelection.has(key(s)))??[];
  const displayed=timeSamples.filter(s=>quality==='all'||s.status==='accepted');
  const progress=job?.state.match(/^measuring_(\d+)_of_(\d+)$/);
  return <div className="source-workspace"><header className="source-header"><Brand/><button onClick={onTime}>← Back to sky</button></header><main>
    <div className="source-intro"><p className="eyebrow">Measure light</p><h1>Measure a source</h1><p>Choose a point of light, find its observations, and inspect its brightness across SPHEREx wavelengths.</p>
      <p className="source-notice">Point-source measurements need a clear, isolated source. Measurements at different dates stay separate; this is not an instantaneous spectrum.</p></div>
    <section className="source-card" aria-labelledby="native-find-title"><h2 id="native-find-title">Find source observations</h2>
      <fieldset disabled={busy}><legend>Source position and dates</legend><button onClick={()=>void example()}>Use P330E calibration example</button>
        <NameLookup onResolve={value=>edit({ra:String(value.center_deg[0]),dec:String(value.center_deg[1]),name:'Resolved sky position',motion:false})}/>
        <form onSubmit={e=>{e.preventDefault();void find();}}>
          <div className="source-options"><label>Source label<input required maxLength={100} value={form.name} onChange={e=>edit({name:e.target.value})}/></label>
            <label>Right ascension · degrees<input required type="number" step="any" min="0" max="359.999999999999" value={form.ra} onChange={e=>edit({ra:e.target.value})}/></label>
            <label>Declination · degrees<input required type="number" step="any" min="-90" max="90" value={form.dec} onChange={e=>edit({dec:e.target.value})}/></label></div>
          <div className="source-options"><label>Start date · UTC<input required type="date" value={form.start_utc} onChange={e=>edit({start_utc:e.target.value})}/></label><label>End date · UTC<input required type="date" value={form.end_utc} onChange={e=>edit({end_utc:e.target.value})}/></label></div>
          <details><summary>Catalog motion and survey coverage</summary><p>Name lookup supplies a position only. For moving stars, use catalog motion or select a Gaia source in the sky workspace.</p>
            <label className="check-label"><input type="checkbox" checked={form.motion} onChange={e=>edit({motion:e.target.checked})}/>Apply supplied angular motion</label>
            {form.motion&&<div className="source-options"><label>RA motion · mas/year · includes cos(dec)<input type="number" step="any" min="-12000" max="12000" value={form.pmra} onChange={e=>edit({pmra:e.target.value})}/></label>
              <label>Declination motion · mas/year<input type="number" step="any" min="-12000" max="12000" value={form.pmdec} onChange={e=>edit({pmdec:e.target.value})}/></label>
              <label>Reference epoch · Julian year<input type="number" step="any" min="1900" max="2100" value={form.ref_epoch} onChange={e=>edit({ref_epoch:e.target.value})}/></label></div>}
            <label className="check-label"><input type="checkbox" checked={form.include_deep} onChange={e=>edit({include_deep:e.target.checked})}/>Include deep-survey metadata</label></details>
          <div className="source-actions"><button className="primary" type="submit">Find source observations</button><button type="button" onClick={e=>{if(e.currentTarget.form?.reportValidity())void find(true);}}>Refresh archive search</button></div>
        </form></fieldset>
      {busy&&<p role="status" aria-live="polite">{restoring?'Restoring saved measurements…':exampleLoading?'Loading source reference…':submitting?'Submitting request…':progress?`Measuring observation ${progress[1]} of ${progress[2]}…`:job?.state==='discovering_source_observations'?'Searching archive metadata…':'Waiting for the stored analysis job…'}</p>}
      {!terminal(job)&&<button onClick={()=>void cancel()}>Cancel source analysis</button>}
      {job?.state==='cancelled'&&<p role="status">Source analysis cancelled.</p>}
      {error&&<p role="alert">{error}</p>}{fieldWarning&&<p className="source-notice">{fieldWarning}</p>}
    </section>
    {field&&<section className="source-card" aria-labelledby="native-select-title"><h2 id="native-select-title" tabIndex={-1} ref={fieldHeading}>Choose observations</h2>
      {field.discovery.data_status==='retained_metadata_snapshot'&&<p className="source-notice"><strong>Retained metadata snapshot</strong><br/>{field.discovery.snapshot_note}<br/>Retrieved: {field.discovery.retrieved_utc}</p>}
      <p>{field.candidate_observations} DR1 candidates · {field.unsupported_release_observations} observations from releases awaiting native calibration approval. {field.search_completeness==='limited'?'The inventory is limited; refine dates or refresh the archive search.':'Metadata query completed for the listed collections.'}</p>
      {field.discovery.retrieved_utc&&<p className="muted">Metadata retrieved {field.discovery.retrieved_utc} · {field.discovery.data_status==='cached'?'cached archive query':field.discovery.data_status==='retained_metadata_snapshot'?'retained query snapshot':'archive query'}.</p>}
      <p>Each native image still needs coverage, pixel-quality, exact calibration and fit checks.</p>
      <fieldset disabled={busy}><legend>Observation selection</legend><div className="source-actions"><button disabled={field.candidate_observations>512} onClick={()=>{clearResult();setSelected(field.observations.filter(r=>r.measurement_capability==='requires_native_checks').map(r=>r.index));}}>Select supported observations</button>
        <button onClick={()=>{clearResult();setSelected([]);}}>Clear observation selection</button></div>
        <p data-testid="native-selection-count">{selected.length} observations selected · up to 512 per extraction. Native input size is roughly {n(selected.length*4.2,0)} MB before cache reuse.</p>
        <label>Filter observation IDs<input value={filter} onChange={e=>{setFilter(e.target.value);setPage(0);}}/></label>
        <div className="source-table-scroll" role="region" aria-label="Native observation selection" tabIndex={0}><table><caption>Individual candidate observations · UTC dates · selection does not guarantee a usable measurement</caption><thead><tr><th scope="col">Include</th><th scope="col">Observation</th><th scope="col">UTC date</th><th scope="col">Detector</th><th scope="col">Release</th></tr></thead><tbody>
          {visible.map(row=><tr key={row.index}><td><input className="native-row-check" type="checkbox" aria-label={'Include '+key(row)} checked={selected.includes(row.index)} disabled={row.measurement_capability!=='requires_native_checks'} onChange={e=>{clearResult();setSelected(e.target.checked?[...selected,row.index]:selected.filter(i=>i!==row.index));}}/></td><th scope="row">{row.obs_id}</th><td>{row.utc_mid.slice(0,10)}</td><td>D{row.detector}</td><td>{row.release.toUpperCase()}{row.measurement_capability!=='requires_native_checks'&&' · not enabled'}</td></tr>)}</tbody></table></div>
        <div className="source-actions"><button disabled={page===0} onClick={()=>setPage(p=>p-1)}>Previous observation page</button><span>Page {page+1} of {Math.max(1,Math.ceil(filtered.length/25))}</span><button disabled={(page+1)*25>=filtered.length} onClick={()=>setPage(p=>p+1)}>Next observation page</button></div>
        <div className="source-options"><label>Native extraction method<select value={options.method} onChange={e=>{clearResult();setOptions({...options,method:e.target.value});}}><option value="psf">Effective PSF fit</option><option value="aperture">Aperture with PSF correction</option></select></label>
          <label>Source position during fitting<select value={options.centroid_mode} onChange={e=>{clearResult();setOptions({...options,centroid_mode:e.target.value});}}><option value="auto">Refine when bright enough</option><option value="fixed">Keep supplied position</option></select></label></div>
        <details><summary>Aperture and background geometry</summary><div className="source-options">{(['aperture_radius','background_inner','background_outer'] as const).map((property,i)=><label key={property}>{['Aperture radius · native pixels','Background inner radius · native pixels','Background outer radius · native pixels'][i]}<input type="number" min={[1.5,4.5,7][i]} max={[3.5,6,10][i]} step="0.5" value={options[property]} onChange={e=>{clearResult();setOptions({...options,[property]:Number(e.target.value)});}}/></label>)}</div></details>
        <button className="primary" disabled={!selected.length||selected.length>512} onClick={()=>void submit('/v1/native-source-samples',{field_id:field.id,observation_indices:selected,...options})}>Measure selected observations</button></fieldset>
    </section>}
    {product&&<section className="source-card" aria-labelledby="native-result-title"><h2 id="native-result-title" tabIndex={-1} ref={heading}>{product.source.name??'Selected source'} · measured light</h2>
      <div className="source-counts"><span>{product.sampling.accepted_samples} pass fit checks</span><span>{product.sampling.diagnostic_only_samples} need fit review</span><span>{product.sampling.rejected_samples} have no measurement</span></div><p>{product.sampling.interpretation}</p>
      <SourceSummaryPanel key={product.id} productId={product.id} onFilter={applyTimeSelection} onInspect={id=>{setSampleId(id);setTimeout(()=>sampleHeading.current?.focus(),0);}}/>
      <div className="source-chart-scroll" role="region" aria-label="Native source chart" tabIndex={0}><SampleChart product={{samples:timeSamples}} select={setSampleId} selected={sampleId} wide responsive sourceLabel={product.source.name}/></div>
      <p className="muted">Vertical bars: one statistical error. Horizontal bars: central calibrated bandwidth. No inferred missing channels or lines joining different dates.</p><p className="source-scroll-help">Scroll the detailed tables sideways on narrow screens. Charts fit the available width.</p>
      <label>Result quality view<select value={quality} onChange={e=>{setQuality(e.target.value);if(e.target.value==='passing'&&sample?.status!=='accepted'){const first=timeSamples.find(s=>s.status==='accepted');setSampleId(first?key(first):'');}}}><option value="all">All requested observations</option><option value="passing">Passing fit checks</option></select></label>
      <div className="source-table-scroll" role="region" aria-label="Native source measurements" tabIndex={0}><table><caption>Individual native measurements · errors are statistical only</caption><thead><tr><th scope="col">Observation · detector</th><th scope="col">UTC date</th><th scope="col">Wavelength · µm</th><th scope="col">Flux ± σ · µJy</th><th scope="col">Fit check</th><th scope="col">Inspect</th></tr></thead><tbody>
        {displayed.map(s=><tr key={key(s)}><th scope="row">{key(s)}</th><td>{s.utc_mid.slice(0,10)}</td><td>{n(s.wavelength_um,5)}</td><td>{s.flux_ujy==null?'—':`${n(s.flux_ujy)} ± ${n(s.statistical_sigma_ujy)}`}</td><td>{s.status==='accepted'?'Passes':s.status==='diagnostic_only'?'Inspect fit':'No measurement'}</td><td><button aria-label={'Inspect '+key(s)} aria-pressed={sampleId===key(s)} onClick={()=>setSampleId(key(s))}>Inspect</button></td></tr>)}</tbody></table></div>
      {sample&&<section className="source-sample-detail" data-testid="native-selected-sample"><h3 ref={sampleHeading} tabIndex={-1}>{key(sample)}</h3><p>{sample.utc_mid} · D{sample.detector}</p>{sample.reason&&<p className="source-notice">{sample.reason}</p>}
        {sample.flux_ujy!=null&&<><p className="measurement-flux" data-testid="native-measured-flux">{n(sample.flux_ujy)} ± {n(sample.statistical_sigma_ujy)} µJy<small>Statistical error only</small></p><p>Wavelength {n(sample.wavelength_um,5)} µm · central bandwidth {n(sample.bandwidth_um,5)} µm · residual score {n(sample.reduced_chi2,3)} (maximum 3).</p></>}
        {context&&<div className="source-stamps"><NativeStamp sample={{...sample,image_context:context}} geometry={product.request}/><NativeStamp sample={{...sample,image_context:context}} residual geometry={product.request}/></div>}
        {sample.flux_ujy!=null&&!context&&!contextError&&<p role="status">Loading this observation’s native cutout…</p>}
        {contextError&&<div role="alert"><p>{contextError}</p><button onClick={()=>setContextRetry(v=>v+1)}>Retry native inspection</button></div>}
        <p>{sample.native_cutout_request&&<><a href={sample.native_cutout_request.url} target="_blank" rel="noreferrer">Official native cutout request ↗</a><br/></>}<a href={sample.source_url} target="_blank" rel="noreferrer">Official parent exposure ↗</a></p>
        <details><summary>Input identity and flags</summary><p className="source-hash">Retained input SHA-256: {sample.source_sha256}</p><p>Flags union: {sample.pixel_flags_union==null?'unavailable':'0x'+sample.pixel_flags_union.toString(16)}. The source flag is expected; a union can include rejected pixels outside the fitted support.</p></details>
      </section>}
      <div className="source-actions">{Object.entries(product.exports).map(([name,resource])=><a key={name} className="source-download" href={resource.url} download>{name==='samples.ecsv'?'ECSV with units':name==='samples.csv'?'CSV · all observations':'SVG plot'}</a>)}<a className="source-download" href={'/v1/products/'+product.id} download={'vantage-'+product.id.slice(0,12)+'.json'}>Provenance JSON</a><button onClick={()=>{const summary=new URLSearchParams(location.search).get('summary');setLink(location.origin+'/?view=measure&samples='+product.id+'&sample='+encodeURIComponent(sampleId)+'&quality='+quality+(summary?'&summary='+encodeURIComponent(summary):''));}}>Share measured light</button></div>
      <p className="muted">Table downloads include every requested observation and its status.</p>
      {link&&<label className="source-share">Measured-light link<input readOnly value={link} onFocus={e=>e.target.select()}/></label>}
      <details><summary>Methods, uncertainties and limits</summary><p>{product.uncertainty_method}</p><ul>{product.limitations.map(item=><li key={item}>{item}</li>)}</ul><p>{product.credits}</p></details>
    </section>}
  </main></div>;
}
