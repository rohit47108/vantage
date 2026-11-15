import {useEffect,useRef,useState} from 'react';
import {json} from './api';
import {useChartWidth} from './useChartWidth';

interface Bin {
  bin_id:string;index:number;detector:number;channel:number;count:number;
  flux_ujy:number;statistical_sigma_ujy:number;weighted_wavelength_um:number;
  wavelength_range_um:number[];mjd_range:number[];input_sample_ids:string[];
  input_utc_mids:string[];input_wavelengths_um:number[];weights:number[];
  equal_mean_p_value:number|null;scatter_warning:boolean;
}
interface Coverage {index:number;detector:number;channel:number;accepted:number;diagnostic_only:number;rejected:number;visualization_blank:boolean;status:string}
interface Statistic {sample_id:string;snr:number|null;reason:string|null;bound:{upper_ujy:number}|null;sensitivity:{flux_ujy:number}|null}
interface Summary {
  id:string;type:string;parent_product_id:string;measured_nominal_channels:number;selected_sample_count:number;parent_sample_count:number;
  options:{start_utc:string|null;end_utc:string|null;time_bin_days:number|null};
  coverage:Coverage[];bins:Bin[];assignments:Record<string,unknown>;unassigned_sample_ids:string[];edge_sample_ids:string[];
  sample_statistics:Statistic[];interpretation:string;scatter_interpretation:string;uncertainty_method:string;
  exports:Record<string,{url:string}>;
}
const number=(v:number,digits=2)=>v.toLocaleString('en-US',{maximumFractionDigits:digits});

function SummaryChart({bins,select}:{bins:Bin[];select:(id:string)=>void}){
  const layout=useChartWidth(),left=80,right=layout.width-25;
  const low=Math.min(0,...bins.map(b=>b.flux_ujy-3*b.statistical_sigma_ujy));
  const high=Math.max(1,...bins.map(b=>b.flux_ujy+3*b.statistical_sigma_ujy))*1.1;
  const x=(v:number)=>left+(v-.7)/4.4*(right-left),y=(v:number)=>280-(v-low)/(high-low)*215;
  return <svg ref={layout.ref} className="sample-chart responsive-chart" viewBox={`0 0 ${layout.width} 340`} role="group" aria-labelledby="summary-chart-title summary-chart-description">
    <title id="summary-chart-title">Time and channel summary means</title>
    <desc id="summary-chart-description">Statistical means of selected native measurements. Vertical bars show one statistical error. Horizontal bars span input wavelength centers, not a bandpass. Use the summary table to inspect dates and contributors.</desc>
    <path d={`M${left} 65 V280 H${right}`} stroke="#9eb3c2" fill="none"/>
    {[1,2,3,4,5].map(value=><text key={value} x={x(value)} y={303} textAnchor="middle">{value}</text>)}
    {[0,.25,.5,.75,1].map(ratio=>{const value=low+ratio*(high-low);return <text key={ratio} x={left-10} y={y(value)+5} textAnchor="end">{number(value,0)}</text>;})}
    {bins.map(b=><g key={b.bin_id} stroke={b.scatter_warning?'#ffc186':'#9ddfd2'} fill={b.scatter_warning?'#ffc186':'#9ddfd2'}>
      <path d={`M${x(b.weighted_wavelength_um)} ${y(b.flux_ujy-b.statistical_sigma_ujy)} V${y(b.flux_ujy+b.statistical_sigma_ujy)} M${x(b.wavelength_range_um[0])} ${y(b.flux_ujy)} H${x(b.wavelength_range_um[1])}`}/>
      <circle cx={x(b.weighted_wavelength_um)} cy={y(b.flux_ujy)} r={6} role="button" tabIndex={0}
        aria-label={`Select summary D${b.detector} channel ${b.channel}, ${b.count} inputs, ${b.input_utc_mids[0]}`}
        onClick={()=>select(b.bin_id)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select(b.bin_id);}}}/>
    </g>)}
    {!bins.length&&<text x={layout.width/2} y={170} textAnchor="middle">No passing summaries</text>}
    <text x={(left+right)/2} y={333} textAnchor="middle">Mean wavelength (µm)</text>
    <text transform="translate(22 175) rotate(-90)" textAnchor="middle">Mean flux density (µJy)</text>
  </svg>;
}

export function SourceSummaryPanel({productId,onFilter,onInspect}:{productId:string;onFilter:(ids:string[]|null)=>void;onInspect:(id:string)=>void}){
  const [form,setForm]=useState({start_utc:'',end_utc:'',time_bin_days:'1'});
  const [result,setResult]=useState<Summary|null>(null),[jobId,setJobId]=useState<string|null>(null);
  const [submitting,setSubmitting]=useState(false),[restoring,setRestoring]=useState(false),[error,setError]=useState('');
  const [selected,setSelected]=useState(''),[page,setPage]=useState(0),[channel,setChannel]=useState<number|null>(null);
  const callbacks=useRef({onFilter,onInspect});callbacks.current={onFilter,onInspect};
  const alive=useRef(true),detail=useRef<HTMLHeadingElement>(null);
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);
  const busy=submitting||restoring||!!jobId;
  function show(value:Summary){
    if(value.type!=='source_summary'||value.parent_product_id!==productId)throw new Error('This summary belongs to different native measurements.');
    setResult(value);setForm({start_utc:value.options.start_utc??'',end_utc:value.options.end_utc??'',time_bin_days:value.options.time_bin_days==null?'all':String(value.options.time_bin_days)});
    setPage(0);setChannel(null);setSelected(value.bins[0]?.bin_id??'');
    const params=new URLSearchParams(location.search);params.set('summary',value.id);params.delete('summary_job');history.replaceState(null,'','/?'+params);
  }
  useEffect(()=>{callbacks.current.onFilter(result?Object.keys(result.assignments):null);},[result]);
  function clear(){setResult(null);setSelected('');setChannel(null);setError('');const p=new URLSearchParams(location.search);p.delete('summary');p.delete('summary_job');history.replaceState(null,'','/?'+p);}
  async function submit(body:typeof form){
    setSubmitting(true);clear();
    try{
      const response=await json<{job_id:string}>('/v1/source-summaries',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({product_id:productId,start_utc:body.start_utc||null,end_utc:body.end_utc||null,time_bin_days:body.time_bin_days==='all'?null:Number(body.time_bin_days)})});
      if(alive.current){setJobId(response.job_id);const p=new URLSearchParams(location.search);p.set('summary_job',response.job_id);history.replaceState(null,'','/?'+p);}
    }catch(e){if(alive.current)setError((e as Error).message);}finally{if(alive.current)setSubmitting(false);}
  }
  useEffect(()=>{
    const abort=new AbortController(),p=new URLSearchParams(location.search),saved=p.get('summary'),pending=p.get('summary_job');
    if(pending&&/^[a-f0-9]{32}$/.test(pending)){setJobId(pending);return()=>abort.abort();}
    if(saved){
      setRestoring(true);json<Summary>('/v1/products/'+encodeURIComponent(saved),{signal:abort.signal}).then(value=>{if(!abort.signal.aborted)show(value);})
        .catch(e=>{if(!abort.signal.aborted)setError(e.message);}).finally(()=>{if(!abort.signal.aborted)setRestoring(false);});
    }else void submit(form);
    return()=>abort.abort();
  },[productId]);
  useEffect(()=>{
    if(!jobId)return;const abort=new AbortController();let timer:ReturnType<typeof setTimeout>;
    const poll=async()=>{
      try{
        const state=await json<{state:string;result_id:string|null;error:string|null}>('/v1/analysis/jobs/'+jobId,{signal:abort.signal});
        if(abort.signal.aborted)return;
        if(state.state==='complete'&&state.result_id){const value=await json<Summary>('/v1/products/'+state.result_id,{signal:abort.signal});if(!abort.signal.aborted){show(value);setJobId(null);setError('');}return;}
        if(['failed','cancelled'].includes(state.state)){setJobId(null);setError(state.error??'Summary cancelled.');return;}
      }catch(e){if(!abort.signal.aborted)setError((e as Error).message+' Reconnecting to the saved summary job…');}
      if(!abort.signal.aborted)timer=setTimeout(poll,750);
    };void poll();return()=>{abort.abort();clearTimeout(timer);};
  },[jobId]);
  function choose(id:string){setSelected(id);setTimeout(()=>detail.current?.focus(),0);}
  async function cancel(){
    if(!jobId)return;
    try{const state=await json<{state:string}>('/v1/analysis/jobs/'+jobId,{method:'DELETE'});
      if(state.state!=='complete'){setJobId(null);setError('Summary cancelled. Individual measurements remain available.');const p=new URLSearchParams(location.search);p.delete('summary_job');history.replaceState(null,'','/?'+p);}
    }catch(e){setError((e as Error).message);}
  }
  const bins=result?.bins.filter(row=>channel==null||row.index===channel)??[];
  const bin=result?.bins.find(row=>row.bin_id===selected);
  const bounds=result?.sample_statistics.filter(row=>row.bound)??[];
  return <section className="source-summary" aria-labelledby="source-summary-title"><h3 id="source-summary-title">Time and channel summaries</h3>
    <p>Keep individual observations, or compare descriptive means within a channel and time interval. Means can mix slightly different wavelength responses; they do not form an instantaneous spectrum.</p>
    <form onSubmit={e=>{e.preventDefault();void submit(form);}}><fieldset disabled={busy}><legend>Filter measurements and define summaries</legend><div className="source-options">
      <label>Summary start date · UTC<input type="date" value={form.start_utc} onChange={e=>{clear();setForm({...form,start_utc:e.target.value});}}/></label>
      <label>Summary end date · UTC<input type="date" value={form.end_utc} onChange={e=>{clear();setForm({...form,end_utc:e.target.value});}}/></label>
      <label>Time grouping<select value={form.time_bin_days} onChange={e=>{clear();setForm({...form,time_bin_days:e.target.value});}}><option value="1">One UTC day</option><option value="7">Seven days from start</option><option value="30">Thirty days from start</option><option value="all">Entire selected interval</option>{!['1','7','30','all'].includes(form.time_bin_days)&&<option value={form.time_bin_days}>{form.time_bin_days} days from start</option>}</select></label>
    </div><button type="submit">Apply time and channel summary</button></fieldset></form>
    {busy&&<p role="status">Building time and channel summaries… Individual measurements remain available.</p>}
    {jobId&&<button onClick={()=>void cancel()}>Cancel summary</button>}
    {error&&<p role="alert">{error}</p>}
    {!result&&!busy&&<p>Run the summary to apply these dates. Individual measurements currently show every date.</p>}
    {result&&<><p data-testid="summary-coverage-count"><strong>{result.measured_nominal_channels} of 102 nominal channels have passing measurements</strong> · {result.selected_sample_count} of {result.parent_sample_count} native inputs in this time view.</p>
      <p className="muted">Individual chart and table below follow this time view. Channels without passing measurements stay empty. {result.unassigned_sample_ids.length} failed inputs have no channel assignment; {result.edge_sample_ids.length} inputs fall in extra edge regions.</p>
      <details><summary>Inspect all 102 nominal channels</summary><p>Each cell is a detector’s nominal channel, defined by the official geometric map. A blank visualization layer does not mean that native measurements are absent or valid.</p>
        <div className="source-table-scroll" role="region" aria-label="Nominal channel coverage" tabIndex={0}><div className="summary-channel-grid">{result.coverage.map(row=><button key={row.index} className={row.accepted?'has-measurements':''} aria-pressed={channel===row.index}
          aria-label={`D${row.detector} channel ${row.channel}: ${row.accepted} passing, ${row.diagnostic_only} need fit review${row.visualization_blank?', blank in visualization cube':''}`}
          onClick={()=>{setChannel(row.index);setPage(0);const first=result.bins.find(b=>b.index===row.index);setSelected(first?.bin_id??'');}}>{row.detector}:{row.channel}<small>{row.accepted?row.accepted+' pass':'—'}</small></button>)}</div></div>
        {channel!=null&&<p>D{Math.floor(channel/17)+1} channel {channel%17+1} · {result.coverage[channel].accepted?'passing inputs listed below':'No passing measurement in this time view.'} <button onClick={()=>{setChannel(null);setPage(0);}}>Show all summary channels</button></p>}
      </details>
      <div className="source-chart-scroll" role="region" aria-label="Time-combined summary chart" tabIndex={0}><SummaryChart bins={bins} select={choose}/></div>
      <p className="muted">Vertical bars: one statistical error. Horizontal span: contributing wavelength centers, not a bandpass. Orange markers have excess scatter under the stated constant-mean model.</p>
      <div className="source-table-scroll" role="region" aria-label="Binned native source summaries" tabIndex={0}><table><caption>Time and response mixed descriptive means · individual measurements remain available</caption><thead><tr><th scope="col">Channel</th><th scope="col">Dates · UTC</th><th scope="col">Inputs</th><th scope="col">Mean ± σ · µJy</th><th scope="col">Scatter</th><th scope="col">Inspect</th></tr></thead><tbody>{bins.slice(page*25,page*25+25).map(row=><tr key={row.bin_id}>
        <th scope="row">D{row.detector}:{row.channel}</th><td>{row.input_utc_mids[0].slice(0,10)} – {row.input_utc_mids.at(-1)!.slice(0,10)}</td><td>{row.count}</td><td>{number(row.flux_ujy)} ± {number(row.statistical_sigma_ujy)}</td><td>{row.scatter_warning?'Inspect excess scatter':row.count===1?'One input':'No flagged excess'}</td><td><button aria-label={`Inspect summary D${row.detector} channel ${row.channel}${bins.filter(b=>b.index===row.index).length>1?' · '+row.input_utc_mids[0]:''}`} onClick={()=>choose(row.bin_id)}>Inspect</button></td>
      </tr>)}</tbody></table></div>
      {bins.length>25&&<div className="source-actions"><button disabled={!page} onClick={()=>setPage(p=>p-1)}>Previous summary page</button><span>Page {page+1} of {Math.ceil(bins.length/25)}</span><button disabled={(page+1)*25>=bins.length} onClick={()=>setPage(p=>p+1)}>Next summary page</button></div>}
      {bin&&<section data-testid="summary-contributors"><h4 ref={detail} tabIndex={-1}>D{bin.detector} channel {bin.channel} · contributors</h4><p>{bin.count} native inputs. Each retains its date, wavelength and statistical weight.</p><ul>{bin.input_sample_ids.map((id,i)=><li key={id}><button onClick={()=>callbacks.current.onInspect(id)} aria-label={'Inspect native '+id}>{id}</button> · {bin.input_utc_mids[i]} · {number(bin.input_wavelengths_um[i],5)} µm · weight {number(bin.weights[i],4)}</li>)}</ul>{bin.scatter_warning&&<p className="source-notice">Scatter exceeds the conditional constant-mean screen. Different wavelength responses, variability or systematic errors may explain it; this is not a variability detection.</p>}</section>}
      <details><summary>Statistical upper bounds and sensitivity</summary><p>A low-signal, fixed-position measurement can support a conditional 95% upper credible bound with a uniform prior on nonnegative true flux. This differs from the nominal Gaussian detection sensitivity shown alongside it. Neither includes total calibration/model errors or sky-search completeness. Failed coverage and poor fits receive no bound.</p>
        {bounds.length?<ul>{bounds.map(row=><li key={row.sample_id}><button onClick={()=>callbacks.current.onInspect(row.sample_id)}>{row.sample_id}</button>: 95% upper credible bound {number(row.bound!.upper_ujy)} µJy; conditional 95% detection sensitivity {number(row.sensitivity!.flux_ujy)} µJy at a one-position 5σ threshold.</li>)}</ul>:<p>No low-signal fixed-position sample supports an upper bound in this selection.</p>}
      </details>
      <div className="source-actions">{Object.entries(result.exports).map(([name,resource])=><a className="source-download" key={name} href={resource.url} download>{name==='bins.ecsv'?'Binned ECSV':name==='coverage.ecsv'?'Coverage ECSV':name==='limits.ecsv'?'Bounds ECSV':name==='summary.svg'?'Summary SVG':name}</a>)}<a className="source-download" href={'/v1/products/'+result.id} download>Summary provenance</a></div>
      <p className="muted">The current URL saves this immutable summary and its native parent.</p><details><summary>Summary methods and interpretation</summary><p>{result.interpretation}</p><p>{result.uncertainty_method}</p><p>{result.scatter_interpretation}</p></details>
    </>}
  </section>;
}
