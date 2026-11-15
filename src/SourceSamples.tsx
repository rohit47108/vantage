import {useEffect,useRef,useState} from 'react';
import {Brand} from './Brand';
import {json} from './api';
import './sources.css';

interface Observation {index:number;obs_id:string;utc_mid:string;detector:number;mjd_mid:number}
interface Target {key:string;name:string;revision:string;sampling_description:string;position_model:string;observations:Observation[]}
interface Sample {obs_id:string;utc_mid:string;detector:number;status:'accepted'|'diagnostic_only'|'rejected';reason:string|null;
  flux_ujy:number|null;statistical_sigma_ujy:number|null;wavelength_um:number|null;bandwidth_um:number|null;
  reduced_chi2?:number;position_pixel_xy?:number[];pixel_flags_union?:number;source_url:string;source_sha256:string;
  native_cutout_request?:{url:string;checksum_semantics:string};
  image_context?:{shape:number[];brightness_mjysr:(number|null)[][];residual_ujy:(number|null)[][];used:number[][]};
  centroid_fit?:{shift_pixel_xy:number[];sigma_pixel_xy:number[]}}
interface Product {id:string;name:string;type:string;samples:Sample[];limitations:string[];uncertainty_method:string;credits:string;
  request:{method:string;observation_indices:number[];refine_centroid:boolean;aperture_radius:number;background_inner:number;background_outer:number};sampling:{accepted_samples:number;rejected_samples:number;diagnostic_only_samples:number;interpretation:string};
  exports:Record<string,{url:string}>}
interface Job {job_id:string;state:string;result_id:string|null;error:string|null}
const finished=(job:Job|null)=>!job||['complete','failed','cancelled'].includes(job.state);
const number=(value:number|null|undefined,digits=2)=>value==null?'—':value.toLocaleString('en-US',{minimumFractionDigits:digits,maximumFractionDigits:digits});
const status=(sample:Sample)=>sample.status==='accepted'?'Passes fit checks':sample.status==='diagnostic_only'?'Inspect fit':'No measurement';

function NativeStamp({sample,residual=false}:{sample:Sample;residual?:boolean}){
  const ref=useRef<HTMLCanvasElement>(null);
  useEffect(()=>{
    if(!sample.image_context||!ref.current)return;
    const context=sample.image_context,values=residual?context.residual_ujy:context.brightness_mjysr;
    const [height,width]=context.shape,canvas=ref.current;canvas.width=width*8;canvas.height=height*8;
    const ctx=canvas.getContext('2d')!;
    const finite=values.flatMap((row,y)=>row.filter((v,x):v is number=>v!==null&&(!residual||context.used[y][x]===1))).sort((a,b)=>a-b);
    const low=finite[Math.floor(finite.length*.02)]??0,high=finite[Math.floor(finite.length*.99)]??1;
    const limit=Math.max(Math.abs(low),Math.abs(high),1e-12);
    for(let y=0;y<height;y++)for(let x=0;x<width;x++){
      const v=residual&&!context.used[y][x]?null:values[y][x];let color='#080d11';
      if(v!==null){
        if(residual){const strength=Math.min(1,Math.abs(v)/limit);color=v>0?`rgb(${Math.round(30+210*strength)},${Math.round(40+90*strength)},65)`:`rgb(40,${Math.round(50+100*strength)},${Math.round(60+180*strength)})`;}
        else{const g=Math.round(255*Math.asinh(8*Math.max(0,Math.min(1,(v-low)/(high-low||1))))/Math.asinh(8));color=`rgb(${g},${g},${g})`;}
      }
      ctx.fillStyle=color;ctx.fillRect(x*8,(height-y-1)*8,8,8);
    }
    if(sample.position_pixel_xy){const [x,y]=sample.position_pixel_xy;ctx.strokeStyle='#c4ffda';ctx.lineWidth=1.5;
      const px=(x+.5)*8,py=(height-y-.5)*8;ctx.beginPath();ctx.moveTo(px-9,py);ctx.lineTo(px+9,py);ctx.moveTo(px,py-9);ctx.lineTo(px,py+9);ctx.stroke();}
  },[sample,residual]);
  return <figure><canvas ref={ref} role="img" aria-label={residual?'Fitted source and local background residual in microJy per native pixel; only fit pixels shown. Array rows increase upward.':'Native brightness cutout; source cross marks the measured position. Array rows increase upward.'}/>
    <figcaption>{residual?'Fit residual · µJy / native pixel · used pixels only':'Native brightness · MJy/sr'}<br/>Native columns → · rows ↑</figcaption></figure>;
}

function SampleChart({product,select,selected}:{product:Product;select:(id:string)=>void;selected:string}){
  const samples=product.samples.filter(s=>s.status==='accepted');
  const max=Math.max(1,...samples.map(s=>s.flux_ujy!+3*s.statistical_sigma_ujy!))*1.15;
  const min=Math.min(0,...samples.map(s=>s.flux_ujy!-3*s.statistical_sigma_ujy!));
  const x=(v:number)=>110+(v-1.05)/.65*600,y=(v:number)=>265-(v-min)/(max-min)*210;
  return <svg className="sample-chart" viewBox="0 0 760 340" role="group" aria-labelledby="sample-chart-title sample-chart-description">
    <title id="sample-chart-title">P330E measured flux density versus wavelength</title>
    <desc id="sample-chart-description">Partial D2 sampling at separate dates. Only samples passing fit checks are plotted. Vertical bars: one statistical standard deviation. Horizontal bars: central calibrated CBAND, not a full response curve. Use the observation table for rejected samples.</desc>
    <path d="M110 50 V265 H710" fill="none" stroke="#8fa5b7"/>
    {[1.1,1.3,1.5,1.65].map(tick=><text key={tick} x={x(tick)} y={288} textAnchor="middle">{tick}</text>)}
    {[0,.25,.5,.75,1].map(fraction=>{const value=min+(max-min)*fraction;return <text key={fraction} x="100" y={y(value)+5} textAnchor="end">{number(value,0)}</text>;})}
    <text x="390" y="322" textAnchor="middle">Wavelength (µm) · horizontal bars: CBAND</text>
    <text transform="translate(20 160) rotate(-90)" textAnchor="middle">Flux density (µJy)</text>
    {samples.map(s=><g key={s.obs_id}>
      <path d={`M${x(s.wavelength_um!)} ${y(s.flux_ujy!-s.statistical_sigma_ujy!)} V${y(s.flux_ujy!+s.statistical_sigma_ujy!)} M${x(s.wavelength_um!-s.bandwidth_um!/2)} ${y(s.flux_ujy!)} H${x(s.wavelength_um!+s.bandwidth_um!/2)}`} stroke="#9ddfd2" strokeWidth="2"/>
      <circle cx={x(s.wavelength_um!)} cy={y(s.flux_ujy!)} r={selected===s.obs_id?9:7} fill="#9ddfd2" stroke={selected===s.obs_id?'white':'#061316'} strokeWidth="2"
        tabIndex={0} role="button" aria-label={`Select sample ${s.obs_id}, ${number(s.flux_ujy)} microJy, ${s.utc_mid}`} aria-pressed={selected===s.obs_id}
        onClick={()=>select(s.obs_id)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select(s.obs_id);}}}/>
    </g>)}
    {!samples.length&&<text x="380" y="160" textAnchor="middle">No selected sample passes fit checks.</text>}
  </svg>;
}

export function SourceSamples({onTime,initialProduct}:{onTime:()=>void;initialProduct?:string|null}){
  const [target,setTarget]=useState<Target|null>(null),[loading,setLoading]=useState(true),[error,setError]=useState('');
  const [targetError,setTargetError]=useState(''),[loadingSaved,setLoadingSaved]=useState(!!initialProduct);
  const [selected,setSelected]=useState([0,1,2,3]),[method,setMethod]=useState('psf'),[refine,setRefine]=useState(true);
  const [aperture,setAperture]=useState(2.5),[inner,setInner]=useState(5),[outer,setOuter]=useState(8);
  const [job,setJob]=useState<Job|null>(null),[submitting,setSubmitting]=useState(false),[product,setProduct]=useState<Product|null>(null);
  const [sampleId,setSampleId]=useState(''),[link,setLink]=useState(''),[retry,setRetry]=useState(0);
  const mounted=useRef(true),resultHeading=useRef<HTMLHeadingElement>(null);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
  useEffect(()=>{
    const abort=new AbortController();setLoading(true);
    json<Target>('/v1/source-targets/p330e',{signal:abort.signal}).then(value=>{if(!abort.signal.aborted){setTarget(value);setLoading(false);setTargetError('');}})
      .catch(e=>{if(!abort.signal.aborted){setTargetError(e.message);setLoading(false);}});
    return()=>abort.abort();
  },[retry]);
  function show(value:Product){
    if(value.type!=='source_samples')throw new Error('This product is not a source-sample measurement.');
    setProduct(value);setLink('');
    const desired=new URLSearchParams(location.search).get('sample');
    setSampleId(value.samples.find(s=>s.obs_id===desired)?.obs_id??value.samples.find(s=>s.status==='accepted')?.obs_id??value.samples[0]?.obs_id??'');
    setSelected(value.request.observation_indices);setMethod(value.request.method);setRefine(value.request.refine_centroid);
    setAperture(value.request.aperture_radius);setInner(value.request.background_inner);setOuter(value.request.background_outer);
  }
  useEffect(()=>{
    if(!initialProduct)return;
    const abort=new AbortController();setLoadingSaved(true);
    json<Product>('/v1/products/'+encodeURIComponent(initialProduct),{signal:abort.signal}).then(value=>{if(!abort.signal.aborted){show(value);setError('');}})
      .catch(e=>{if(!abort.signal.aborted)setError(e.message);}).finally(()=>{if(!abort.signal.aborted)setLoadingSaved(false);});
    return()=>abort.abort();
  },[initialProduct,retry]);
  useEffect(()=>{
    if(!job||finished(job))return;
    const abort=new AbortController();let timer:ReturnType<typeof setTimeout>;
    const poll=async()=>{
      try{
        const current=await json<Job>('/v1/analysis/jobs/'+job.job_id,{signal:abort.signal});
        if(abort.signal.aborted)return;
        if(current.state==='complete'&&current.result_id){
          const value=await json<Product>('/v1/products/'+current.result_id,{signal:abort.signal});
          if(!abort.signal.aborted){show(value);setJob(current);setError('');setTimeout(()=>resultHeading.current?.focus(),0);}return;
        }
        if(current.state==='failed'||current.state==='cancelled'){setJob(current);setError(current.error||'Extraction cancelled. Change the selection or start again.');return;}
        if(current.state!==job.state)setJob(current);setError('');
      }catch(e){if(!abort.signal.aborted)setError((e as Error).message+' Reconnecting to the stored job…');}
      if(!abort.signal.aborted)timer=setTimeout(poll,1000);
    };
    void poll();return()=>{abort.abort();clearTimeout(timer);};
  },[job?.job_id,job?.state]);
  const busy=submitting||loadingSaved||!finished(job);
  function changed(){setProduct(null);setJob(null);setError('');setLink('');}
  async function extract(){
    if(!target)return;changed();setSubmitting(true);
    try{
      const response=await json<{job_id:string}>('/v1/source-samples',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({target_key:target.key,target_revision:target.revision,observation_indices:selected,method,refine_centroid:refine,
          aperture_radius:aperture,background_inner:inner,background_outer:outer})});
      if(mounted.current)setJob({job_id:response.job_id,state:'queued',result_id:null,error:null});
    }catch(e){if(mounted.current)setError((e as Error).message);}
    finally{if(mounted.current)setSubmitting(false);}
  }
  async function cancel(){if(!job)return;try{
    const value=await json<{state:string}>('/v1/analysis/jobs/'+job.job_id,{method:'DELETE'});
    if(!mounted.current)return;
    if(value.state==='complete'){
      const current=await json<Job>('/v1/analysis/jobs/'+job.job_id);
      const result=await json<Product>('/v1/products/'+current.result_id);
      if(mounted.current){show(result);setJob(current);}
    }else setJob({...job,state:value.state});
  }catch(e){if(mounted.current)setError((e as Error).message);}}
  const sample=product?.samples.find(s=>s.obs_id===sampleId);
  return <div className="source-workspace">
    <header className="source-header"><Brand/><button onClick={onTime}>← Back to sky</button></header>
    <main id="source-main">
      <div className="source-intro"><p className="eyebrow">Source measurements</p><h1>Measure a source</h1>
        <p>Measure an isolated star in the native SPHEREx pixels, then inspect the flux, uncertainty and fit for each observation.</p>
        <p className="source-notice"><strong>Partial D2 sampling</strong><br/>This first extraction field is P330E, with four retained DR1 observations. The points have different acquisition dates. Other fields and full 102-channel extraction are still in development.</p></div>
      <section aria-labelledby="source-controls-title" className="source-card">
        <h2 id="source-controls-title">1. Choose the observations</h2>
        {loading&&<p role="status">Loading the retained source field…</p>}
        {target&&<><p>{target.sampling_description}</p><fieldset disabled={busy}><legend>P330E · available observations</legend>
          <div className="source-observations">{target.observations.map(obs=><label key={obs.obs_id}>
            <input type="checkbox" aria-label={'Include '+obs.obs_id} checked={selected.includes(obs.index)} onChange={e=>{changed();setSelected(e.target.checked?[...selected,obs.index]:selected.filter(i=>i!==obs.index));}}/>
            <span><strong>{obs.utc_mid.slice(0,10)}</strong><small>{obs.obs_id} · D{obs.detector}</small></span></label>)}</div>
          <div className="source-options"><label>Extraction method<select value={method} onChange={e=>{changed();setMethod(e.target.value);}}><option value="psf">Effective PSF fit</option><option value="aperture">Aperture with PSF correction</option></select></label>
            <label className="check-label"><input type="checkbox" checked={refine} onChange={e=>{changed();setRefine(e.target.checked);}}/>Refine the source position</label></div>
          <p className="muted">Both methods fit a local planar background. Position refinement is bounded to 0.75 native pixel per axis and requires a source signal-to-noise ratio of at least 20.</p>
          <details><summary>Measurement geometry</summary><div className="source-options">
            <label>Aperture radius · native pixels<input type="number" min="1.5" max="3.5" step="0.5" value={aperture} onChange={e=>{changed();setAperture(Number(e.target.value));}}/></label>
            <label>Background inner radius · pixels<input type="number" min="4.5" max="6" step="0.5" value={inner} onChange={e=>{changed();setInner(Number(e.target.value));}}/></label>
            <label>Background outer radius · pixels<input type="number" min="7" max="10" step="0.5" value={outer} onChange={e=>{changed();setOuter(Number(e.target.value));}}/></label></div>
            <p className="muted">The aperture radius affects aperture extraction. PSF fits use the calibrated shape with a 4.5-pixel core and the selected background annulus.</p></details>
        </fieldset><div className="source-actions"><button className="primary" disabled={busy||!selected.length} onClick={()=>void extract()}>Extract selected observations</button>
          {busy&&job&&<button onClick={()=>void cancel()}>Cancel extraction</button>}</div></>}
        <p role="status" aria-live="polite">{submitting?'Submitting extraction…':job&&!finished(job)?job.state==='queued'?'Extraction queued…':'Measuring native pixels…':job?.state==='cancelled'?'Extraction cancelled.':''}</p>
        {loadingSaved&&<p role="status">Loading saved measurements…</p>}
        {targetError&&<div role="alert"><p>{targetError}</p><button onClick={()=>setRetry(n=>n+1)}>Retry source field</button></div>}
        {error&&<div role="alert"><p>{error}</p>{initialProduct&&!product&&<button onClick={()=>setRetry(n=>n+1)}>Retry saved measurements</button>}</div>}
      </section>
      {product&&<section className="source-card" aria-labelledby="source-result-title">
        <h2 id="source-result-title" tabIndex={-1} ref={resultHeading}>P330E · source samples</h2>
        <div className="source-counts"><span>{product.sampling.accepted_samples} passes fit checks</span><span>{product.sampling.diagnostic_only_samples} needs fit review</span><span>{product.sampling.rejected_samples} has no measurement</span></div>
        <p>{product.sampling.interpretation}</p><div className="source-chart-scroll" role="region" aria-label="Source-sample chart; scroll horizontally on small screens" tabIndex={0}><SampleChart product={product} select={setSampleId} selected={sampleId}/></div>
        <p className="muted">Only samples passing fit checks are plotted. Vertical bars show one statistical standard deviation; horizontal bars show central CBAND. No connecting lines or inferred missing channels.</p>
        <div className="source-table-scroll" role="region" aria-label="Source-sample observation table" tabIndex={0}><table>
          <caption>Individual observations · {product.request.method} extraction · signed fluxes and statistical errors</caption>
          <thead><tr><th scope="col">Observation · UTC</th><th scope="col">Wavelength · µm</th><th scope="col">Flux ± σ · µJy</th><th scope="col">Fit check</th><th scope="col">Inspect</th></tr></thead>
          <tbody>{product.samples.map(s=><tr key={s.obs_id} aria-selected={s.obs_id===sampleId}><th scope="row">{s.utc_mid.slice(0,10)}<small>{s.obs_id}</small></th>
            <td>{number(s.wavelength_um,5)}</td><td>{s.flux_ujy===null?'—':`${number(s.flux_ujy)} ± ${number(s.statistical_sigma_ujy)}`}</td><td>{status(s)}</td>
            <td><button aria-label={'Inspect '+s.obs_id} aria-pressed={s.obs_id===sampleId} onClick={()=>setSampleId(s.obs_id)}>Inspect</button></td></tr>)}</tbody></table></div>
        {sample&&<section aria-label="Selected source sample" data-testid="selected-sample" className="source-sample-detail">
          <h3>{sample.obs_id}</h3><p>{sample.utc_mid} · D{sample.detector} · {status(sample)}</p>
          {sample.reason&&<p className="source-notice">{sample.reason}</p>}
          {sample.flux_ujy!==null&&<><p className="measurement-flux" data-testid="measurement-flux">{number(sample.flux_ujy)} ± {number(sample.statistical_sigma_ujy)} µJy <small>statistical error only</small></p>
            <p>Residual score: {number(sample.reduced_chi2,3)} · maximum 3. This is a fit diagnostic, not a probability of discovery.</p>
            {sample.centroid_fit&&<p>Position shift: {sample.centroid_fit.shift_pixel_xy.map(v=>number(v,4)).join(', ')} native pixels.</p>}
            <div className="source-stamps"><NativeStamp sample={sample}/><NativeStamp sample={sample} residual/></div></>}
          <p>{sample.native_cutout_request&&<><a href={sample.native_cutout_request.url} target="_blank" rel="noreferrer">Official native cutout request ↗</a><br/></>}
            <a href={sample.source_url} target="_blank" rel="noreferrer">Official parent exposure ↗</a></p>
          <details><summary>Input identity</summary><p className="source-hash">Retained cutout SHA-256: {sample.source_sha256}</p><p>The parent exposure is a separate file. The checksum identifies the retained cutout used for this measurement.</p></details>
        </section>}
        <div className="source-actions">{Object.entries(product.exports).map(([name,resource])=><a className="source-download" key={name} href={resource.url} download>{name==='samples.ecsv'?'ECSV with units':name==='samples.csv'?'CSV table':'SVG plot'}</a>)}
          <a className="source-download" href={'/v1/products/'+product.id} download={'vantage-'+product.id.slice(0,12)+'.json'}>Provenance JSON</a>
          <button onClick={()=>setLink(location.origin+'/?view=sources&samples='+product.id+'&sample='+encodeURIComponent(sampleId))}>Share these measurements</button></div>
        {link&&<label className="source-share">Measurement link<input readOnly value={link} onFocus={e=>e.target.select()}/></label>}
        <details><summary>Methods, uncertainties and limits</summary><p>{product.uncertainty_method}</p><ul>{product.limitations.map(item=><li key={item}>{item}</li>)}</ul><p>{product.credits}</p>
          <a href="https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/" target="_blank" rel="noreferrer">Official IRSA effective-PSF tutorial ↗</a></details>
      </section>}
    </main>
  </div>;
}
