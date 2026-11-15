import {useEffect,useRef,useState} from 'react';
import {json} from './api';
import {useChartWidth} from './useChartWidth';

interface Sample {
  index:number;detector:number;channel:number;wavelength_um:number;bandwidth_um:number;
  brightness_mjysr:number|null;hits:number|null;flags:number|null;
  status:'available'|'blank'|'missing';flag_review:boolean;reason:string|null;
}
interface Trace {
  id:string;type:string;available_channels:number;interpretation:string;limitations:string[];
  request:{pixel_xy:number[];position_deg:number[]};
  display_grid:{center_deg:number[];fov_arcmin:number;shape:number[]};
  source:{url:string;date_start:string;date_end:string;etag:string};
  samples:Sample[];exports:Record<string,{url:string}>;
}
interface Props {
  plane:{id:string;shape:number[]}|null;pixel:number[]|null;center:number[];fov:number;
  active:number[];choose:(index:number)=>void;restorePixel:(pixel:number[])=>void;
  onMeasure:(position:number[])=>void;
}
const format=(value:number|null)=>value===null?'No data':value.toLocaleString('en-US',{maximumSignificantDigits:7});
const samePoint=(a:number[],b:number[])=>a.length===b.length&&a.every((v,i)=>Math.abs(v-b[i])<1e-8);

function TraceChart({samples,active,choose}:{samples:Sample[];active:number[];choose:(index:number)=>void}){
  const layout=useChartWidth(),left=73,right=layout.width-20;
  const values=samples.flatMap(s=>s.brightness_mjysr===null?[]:[s.brightness_mjysr]);
  const lo=Math.min(0,...values),hi=Math.max(1,...values),span=hi-lo;
  const low=lo-.08*span,high=hi+.12*span;
  const x=(value:number)=>left+(value-.7)/4.4*(right-left),y=(value:number)=>260-(value-low)/(high-low)*205;
  return <svg ref={layout.ref} className="trace-chart" viewBox={`0 0 ${layout.width} 330`} role="group" aria-labelledby="trace-chart-title trace-chart-description">
    <title id="trace-chart-title">Mosaic pixel brightness by wavelength</title>
    <desc id="trace-chart-description">Points are native mosaic samples, without error bars. Squares at the bottom mark missing or blank channels, not zero brightness. Choose a point to show its wavelength image, or use the channel table.</desc>
    <path d={`M${left} 45 V260 H${right}`} stroke="#9eb3c2" fill="none"/>
    {[1,2,3,4,5].map(v=><text key={v} x={x(v)} y={301} textAnchor="middle">{v}</text>)}
    {[0,.25,.5,.75,1].map(r=>{const v=low+r*(high-low);return <text key={r} x={left-9} y={y(v)+4} textAnchor="end">{v.toLocaleString('en-US',{maximumSignificantDigits:3})}</text>;})}
    {samples.map((s,i)=>{
      const cy=s.brightness_mjysr===null?278:y(s.brightness_mjysr),selected=active.includes(s.index);
      const start=i?(x(samples[i-1].wavelength_um)+x(s.wavelength_um))/2:x(s.wavelength_um)-4;
      const end=i+1<samples.length?(x(samples[i+1].wavelength_um)+x(s.wavelength_um))/2:x(s.wavelength_um)+4;
      return <g key={s.index}>
        <rect x={start} y={35} width={end-start} height={252} fill="transparent" role="button" tabIndex={0}
          aria-label={`Choose trace D${s.detector} channel ${s.channel}`} aria-pressed={selected}
          onClick={()=>choose(s.index)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose(s.index);}}}/>
        {s.brightness_mjysr===null?<rect x={x(s.wavelength_um)-3} y={cy-3} width={6} height={6} fill="none" stroke="#c6d3df" pointerEvents="none"/>:
          <circle cx={x(s.wavelength_um)} cy={cy} r={3.5} fill={s.flag_review?'#ffc186':'#9ddfd2'} pointerEvents="none"/>}
        {selected&&<circle cx={x(s.wavelength_um)} cy={cy} r={8} fill="none" stroke="#f3e0ab" strokeWidth={2} pointerEvents="none"/>}
      </g>;
    })}
    <text x={(left+right)/2} y={327} textAnchor="middle">Mosaic wavelength (µm)</text>
    <text transform="translate(18 155) rotate(-90)" textAnchor="middle">Brightness (MJy/sr)</text>
  </svg>;
}

// The parent keys this panel by field and selected pixel. A selection change
// aborts local polling/restoration before a response can update the new view.
export function SpectralTracePanel({plane,pixel,center,fov,active,choose,restorePixel,onMeasure}:Props){
  const [result,setResult]=useState<Trace|null>(null),[job,setJob]=useState<string|null>(null);
  const [submitting,setSubmitting]=useState(false),[restoring,setRestoring]=useState(false);
  const [stage,setStage]=useState(''),[error,setError]=useState(''),[share,setShare]=useState('');
  const alive=useRef(true),pending=useRef<AbortController|null>(null);
  const initial=useRef(new URLSearchParams(location.search));
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;pending.current?.abort();};},[]);
  function show(value:Trace){
    if(value.type!=='visual_spectral_trace'||value.samples.length!==102||
      !samePoint(value.display_grid.center_deg,center)||Math.abs(value.display_grid.fov_arcmin-fov)>1e-8||
      !samePoint(value.display_grid.shape,plane?.shape??[160,160])||
      (pixel&&!samePoint(value.request.pixel_xy,pixel)))throw new Error('This trace belongs to another sky field or pixel. Select a pixel and request a new trace.');
    setResult(value);setError('');setJob(null);
    const p=new URLSearchParams(location.search);p.set('trace',value.id);p.delete('trace_job');
    p.set('wave_x',String(value.request.pixel_xy[0]));p.set('wave_y',String(value.request.pixel_xy[1]));history.replaceState(null,'','/?'+p);
    if(!pixel)restorePixel(value.request.pixel_xy);
  }
  useEffect(()=>{
    const abort=new AbortController(),saved=initial.current.get('trace'),id=initial.current.get('trace_job');
    if(id){if(/^[a-f0-9]{32}$/.test(id))setJob(id);else setError('The saved trace job identifier is invalid.');}
    else if(saved){
      if(!/^[a-f0-9]{64}$/.test(saved)){setError('The saved trace identifier is invalid.');return;}
      setRestoring(true);json<Trace>('/v1/products/'+saved,{signal:abort.signal})
        .then(value=>{if(!abort.signal.aborted)show(value);})
        .catch(e=>{if(!abort.signal.aborted)setError(e.message);})
        .finally(()=>{if(!abort.signal.aborted)setRestoring(false);});
    }
    return()=>abort.abort();
  },[]);
  useEffect(()=>{
    if(!job)return;const abort=new AbortController();let timer:ReturnType<typeof setTimeout>;
    async function poll(){
      try{
        const state=await json<{state:string;result_id:string|null;error:string|null}>('/v1/analysis/jobs/'+job,{signal:abort.signal});
        if(abort.signal.aborted)return;
        if(state.state==='complete'&&state.result_id){
          const value=await json<Trace>('/v1/products/'+state.result_id,{signal:abort.signal});
          if(!abort.signal.aborted){
            try{show(value);}catch(e){setJob(null);setError((e as Error).message);const p=new URLSearchParams(location.search);p.delete('trace_job');history.replaceState(null,'','/?'+p);}
          }
          return;
        }
        if(['failed','cancelled'].includes(state.state)){
          setJob(null);setError(state.error??'Trace cancelled. Select the pixel again or retry.');
          const p=new URLSearchParams(location.search);p.delete('trace_job');history.replaceState(null,'','/?'+p);return;
        }
        setError('');const count=/^sampling_channels_(\d+)_of_102$/.exec(state.state);
        setStage(count?`Read ${count[1]} of 102 channels…`:state.state==='queued'?'Waiting for an archive worker…':'Reading bounded native cube samples…');
      }catch(e){if(!abort.signal.aborted)setError((e as Error).message+' Reconnecting to the saved trace job…');}
      if(!abort.signal.aborted)timer=setTimeout(()=>void poll(),1500);
    }
    void poll();return()=>{abort.abort();clearTimeout(timer);};
  },[job]);
  async function submit(){
    if(!plane||!pixel)return;const abort=new AbortController();pending.current=abort;setSubmitting(true);setError('');setShare('');
    try{
      const value=await json<{job_id:string}>('/v1/spectral-traces',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({plane_id:plane.id,x:pixel[0],y:pixel[1]}),signal:abort.signal});
      if(alive.current){setJob(value.job_id);const p=new URLSearchParams(location.search);p.delete('trace');p.set('trace_job',value.job_id);history.replaceState(null,'','/?'+p);}
    }catch(e){if(alive.current&&!abort.signal.aborted)setError((e as Error).message);}finally{if(alive.current)setSubmitting(false);}
  }
  const busy=submitting||restoring||!!job;
  const selected=result?.samples.filter(s=>active.includes(s.index))??[];
  return <section className="spectral-trace" aria-label="Mosaic pixel brightness trace" aria-busy={busy}>
    <h2>One pixel, across infrared light</h2>
    <p>Select a point in the image, then read its native mosaic brightness across all 102 channels. This combines survey dates; it does not measure a source spectrum.</p>
    {!pixel&&<p>Click the sky, or focus the image and press Enter. Arrow keys move the selected pixel.</p>}
    <div className="trace-actions">
      <button disabled={!plane||!pixel||busy} onClick={()=>void submit()}>{error?'Retry brightness trace':'Trace pixel across wavelengths'}</button>
      {job&&<button onClick={()=>{void json('/v1/analysis/jobs/'+job,{method:'DELETE'}).catch(e=>setError(e.message));}}>Cancel brightness trace</button>}
    </div>
    {busy&&<p role="status">{restoring?'Restoring the saved brightness trace…':stage||'Submitting brightness trace…'}</p>}
    {error&&<p role="alert">{error}</p>}
    {result&&<>
      <p data-testid="trace-coverage"><strong>{result.available_channels} of 102</strong> channels have brightness samples at this native mosaic pixel.</p>
      <TraceChart samples={result.samples} active={active} choose={choose}/>
      <p className="trace-legend">Squares below the axis mark blank or missing samples. Amber points have flags to review. Rings show the displayed image channels.</p>
      <div data-testid="trace-selected-channel" aria-live="polite">
        {selected.map(s=><p key={s.index}><strong>D{s.detector} · channel {s.channel}</strong> · {s.wavelength_um.toFixed(4)} µm · width {s.bandwidth_um.toFixed(4)} µm<br/>
          {format(s.brightness_mjysr)}{s.brightness_mjysr!==null?' MJy/sr':''} · hits {s.hits??'unknown'} · flags {s.flags??'unknown'}{s.flag_review?' · review flags':''}{s.status!=='available'?` · ${s.status}`:''}</p>)}
      </div>
      <p data-testid="trace-interpretation">{result.interpretation}</p>
      <p>Contributing mosaic interval: {result.source.date_start.replace('T',' ')} to {result.source.date_end.replace('T',' ')} UTC. This is not a separate date for each point.</p>
      <details><summary>All 102 brightness samples</summary><div className="trace-table" tabIndex={0} role="region" aria-label="Scrollable brightness samples">
        <table><caption>Native mosaic brightness · missing values are not zeros</caption>
          <thead><tr><th scope="col">Image channel</th><th scope="col">µm</th><th scope="col">Width µm</th><th scope="col">MJy/sr</th><th scope="col">Hits</th><th scope="col">Flags</th><th scope="col">Status</th></tr></thead>
          <tbody>{result.samples.map(s=><tr key={s.index}><th scope="row"><button aria-label={`Show table D${s.detector} channel ${s.channel}`} onClick={()=>choose(s.index)}>D{s.detector} · {s.channel}</button></th>
            <td>{s.wavelength_um.toFixed(4)}</td><td>{s.bandwidth_um.toFixed(4)}</td><td>{format(s.brightness_mjysr)}</td><td>{s.hits??'unknown'}</td><td>{s.flags??'unknown'}</td><td>{s.status}{s.flag_review?' · review flags':''}</td></tr>)}</tbody>
        </table></div></details>
      <details><summary>Trace data and interpretation</summary><ul>{result.limitations.map((v,i)=><li key={i}>{v}</li>)}</ul>
        <p><a href={result.source.url}>Original native FITS cube</a> · object version {result.source.etag}</p></details>
      <div className="trace-actions">
        {(['trace.ecsv','trace.csv','trace.svg'] as const).map(name=><a key={name} href={result.exports[name].url} download>Trace {name.split('.')[1].toUpperCase()}</a>)}
        <button onClick={()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='vantage-brightness-trace.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}}>Trace provenance JSON</button>
        <button onClick={()=>{setShare(location.href);void navigator.clipboard?.writeText(location.href).catch(()=>{});}}>Share brightness trace</button>
        <button onClick={()=>onMeasure(result.request.position_deg)}>Measure this trace position</button>
      </div>
      {share&&<label>Brightness trace link<input aria-label="Brightness trace link" value={share} readOnly onFocus={e=>e.currentTarget.select()}/></label>}
      <p>For source flux and uncertainty, choose an isolated source and inspect its actual dated exposures in Measure.</p>
    </>}
  </section>;
}
