import {useState,useEffect,useRef} from 'react';
import type {Sequence} from './types';
import type {SurveyLoad} from './surveys';
import {json} from './api';
import './surveys.css';

export interface Associations {
  sequence_id:string;
  pairs:{gaia_id:string;wise_id:string;status:string;separation_arcsec:number;comparison_epoch_mjd:number}[];
  method:string;limitations:string[];search_completeness:string;
  pair_limit_reached:boolean;source_queries:string[];
}
interface Props {
  sequence:Sequence|null;frame:number;gaia:SurveyLoad;wise:SurveyLoad;
  overlays:string[];toggle:(name:string)=>void;opacity:number[];
  setOpacity:(values:number[])=>void;selected:string|null;
  onSelect:(key:string)=>void;retry:()=>void;
  onAssociations:(result:Associations|null)=>void;
}

export function SurveyContext({sequence,frame,gaia,wise,overlays,toggle,opacity,setOpacity,selected,onSelect,retry,onAssociations}:Props){
  const [associations,setAssociations]=useState<Associations|null>(null);
  const [error,setError]=useState(''),[loading,setLoading]=useState(false);
  const [check,setCheck]=useState(false),[attempt,setAttempt]=useState(0);
  const inspector=useRef<HTMLElement>(null);
  useEffect(()=>{setCheck(false);setAssociations(null);setError('');onAssociations(null);},[sequence?.id,onAssociations]);
  // Abort and stale-result guard: https://react.dev/reference/react/useEffect#fetching-data-with-effects
  useEffect(()=>{
    if(!check||!sequence)return;
    const abort=new AbortController();setLoading(true);setError('');
    json<Associations>(`/v1/associations?sequence_id=${sequence.id}`,{signal:abort.signal})
      .then(r=>{if(!abort.signal.aborted&&r.sequence_id===sequence.id){setAssociations(r);onAssociations(r);}})
      .catch(e=>{if(!abort.signal.aborted)setError(String(e));})
      .finally(()=>{if(!abort.signal.aborted)setLoading(false);});
    return()=>abort.abort();
  },[check,sequence?.id,attempt,onAssociations]);
  useEffect(()=>{if(selected)inspector.current?.scrollIntoView({block:'nearest'});},[selected]);
  const all=[...(gaia.layer?.sources||[]),...(wise.layer?.sources||[])];
  const source=all.find(s=>`${s.survey}:${s.id}`===selected);
  const nearby=associations?.pairs.filter(p=>source?.survey==='gaia'?p.gaia_id===source.id:p.wise_id===source?.id)||[];
  const shown=source?nearby:associations?.pairs.slice(0,30)||[];
  return <section className="survey-context" aria-label="Other telescopes">
    <h2>Other telescopes</h2>
    <p>Catalog markers add optical and infrared context. They are separate from the SPHEREx measurements.</p>
    {([['gaia','Gaia DR3 · optical circles',gaia],['wise','AllWISE · infrared diamonds',wise]] as const).map(([key,label,state],i)=><div key={key} className="survey-layer">
      <label><input type="checkbox" checked={overlays.includes(key)} onChange={()=>toggle(key)}/>{label}</label>
      {overlays.includes(key)&&<>
        <label>Marker opacity<input type="range" aria-label={`${key==='gaia'?'Gaia':'WISE'} marker opacity`} min="0" max="1" step="0.05" value={opacity[i]} onChange={e=>setOpacity(opacity.map((v,j)=>i===j?Number(e.target.value):v))}/></label>
        {state.loading&&<p role="status">Loading {key==='gaia'?'Gaia':'AllWISE'} catalog…</p>}
        {state.error&&<p role="alert">{state.error} <button onClick={retry}>Retry catalogs</button></p>}
        {state.layer&&<>
          <p>{state.layer.sources.length} catalog entries fall in these frames. {state.layer.search_completeness==='limited'?'Limited search; some sources may be omitted.':'Complete within the queried cone.'}</p>
          <label>Select a {key==='gaia'?'Gaia':'WISE'} source
            <select aria-label={`Select ${key==='gaia'?'Gaia':'WISE'} source`} value={source?.survey===key?source.id:''} onChange={e=>onSelect(`${key}:${e.target.value}`)}>
              <option value="">Choose a source or click its marker</option>
              {state.layer.sources.map(s=><option value={s.id} key={s.id}>{s.id}</option>)}
            </select>
          </label>
          <details><summary>Catalog dates, credits & limits</summary>
            <p>{state.layer.position_semantics}</p>
            <p>Retrieved {state.layer.retrieved_utc}. Data: {state.layer.data_status}. Query radius: {(60*state.layer.queried_radius_deg).toFixed(2)} arcminutes.</p>
            <p>{state.layer.credits}</p>
            <a href={state.layer.documentation}>Column definitions & units</a><br/>
            <a href={state.layer.acknowledgment_url}>Full survey credit instructions</a><br/>
            {state.layer.query_urls.map((url,j)=><p key={url}><a href={url}>Original catalog query {j+1}</a></p>)}
            <ul>{state.layer.limitations.map(l=><li key={l}>{l}</li>)}</ul>
          </details>
        </>}
      </>}
    </div>)}
    {source&&<section ref={inspector} className="catalog-inspector" aria-label="Selected catalog source">
      <h3>{source.survey==='gaia'?'Gaia DR3':'AllWISE'} source</h3>
      <p className="catalog-id">{source.id}</p>
      <dl>
        <dt>Catalog ICRS position · degrees</dt><dd>{source.ra.toFixed(7)}, {source.dec.toFixed(7)}</dd>
        {source.survey==='gaia'?<>
          <dt>Catalog reference epoch</dt><dd>J{source.ref_epoch?.toFixed(1)} TCB</dd>
          <dt>Proper motion · mas/year</dt><dd>RA* {source.pmra??'missing'}; Dec {source.pmdec??'missing'}</dd>
          <dt>Optical G magnitude</dt><dd>{source.phot_g_mean_mag??'missing'}</dd>
          <dt>Locator at SPHEREx acquisition</dt><dd>{sequence?.frames[frame]?.utc_mid}</dd>
          <dt>Modeled ICRS position · degrees</dt><dd>{source.coordinates_by_frame[frame]?.map(v=>v.toFixed(7)).join(', ')}</dd>
          <dt>Position model</dt><dd>{source.motion_model==='catalog_position_missing_motion'?'Catalog position retained: motion unavailable.':'Angular proper-motion prediction; observer parallax and perspective acceleration omitted.'}</dd>
        </>:<>
          <dt>W1 / W2 magnitudes · Vega</dt><dd>{source.w1mpro??'missing'} / {source.w2mpro??'missing'}</dd>
          <dt>W1 mean MJD / W2 mean MJD</dt><dd>{source.w1mjdmean?.toFixed(3)??'missing'} / {source.w2mjdmean?.toFixed(3)??'missing'}</dd>
          <dt>Artifact / photometry flags</dt><dd>{source.cc_flags} / {source.ph_qual}</dd>
          <dt>Extended-source flag</dt><dd>{source.ext_flg??'missing'}</dd>
        </>}
      </dl>
      <p>{source.survey==='wise'?'Historical infrared catalog position; not propagated to the SPHEREx date.':'This locator is an imported catalog model, not a measured SPHEREx centroid.'}</p>
    </section>}
    {gaia.layer&&wise.layer&&<button onClick={()=>{setCheck(true);setAttempt(x=>x+1);}} disabled={loading}>{loading?'Checking candidate associations…':'Check Gaia / WISE associations'}</button>}
    {error&&<p role="alert">{error}</p>}
    {associations&&<div>
      <p>{associations.pairs.length} nearby catalog pairs. <strong>Candidate associations only.</strong> Multiple matches can describe a blend.</p>
      {associations.search_completeness==='limited'&&<p>Limited catalog search; additional pairs may be missing.</p>}
      {associations.pair_limit_reached&&<p>The 500-pair limit was reached.</p>}
      {source&&<p>{nearby.length} retained candidates for the selected entry.</p>}
      <details><summary>Association method and candidates</summary>
        <p>{associations.method}</p><ul>{associations.limitations.map(l=><li key={l}>{l}</li>)}</ul>
        <p>Showing {shown.length} {source?'candidates for this source':'of the retained pairs'}. Export provenance to keep all returned pairs and queries.</p>
        <div className="catalog-table" tabIndex={0} role="region" aria-label="Candidate associations table"><table>
          <caption>Angular proximity candidates · not confirmed identities</caption>
          <thead><tr><th>Gaia ID</th><th>WISE ID</th><th>Separation · arcsec</th></tr></thead>
          <tbody>{shown.map(p=><tr key={p.gaia_id+p.wise_id}><td>{p.gaia_id}</td><td>{p.wise_id}</td><td>{p.separation_arcsec.toFixed(3)}</td></tr>)}</tbody>
        </table></div>
      </details>
    </div>}
  </section>;
}
