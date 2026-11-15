import {useEffect,useState} from 'react';
import type {Frame} from './types';
import {ALL_TIMES,selectTemporalFrames,temporalDayGroups} from './timeSelection';
import type {TimeSelection} from './timeSelection';

export function TimeSelectionControls({frames,selection,onApply}:{frames:Frame[];selection:TimeSelection;onApply:(value:TimeSelection)=>void}){
  const [start,setStart]=useState(selection.start_date),[end,setEnd]=useState(selection.end_date);
  useEffect(()=>{setStart(selection.start_date);setEnd(selection.end_date);},[frames,selection.start_date,selection.end_date]);
  const groups=temporalDayGroups(frames,selection),group=groups.find(g=>g.day===selection.group_date);
  const count=selectTemporalFrames(frames,selection).length;
  return <details className="time-selection">
    <summary>Playback interval and groups</summary>
    <p data-testid="playback-selection-count">{count} of {frames.length} exposures selected for playback.</p>
    <form onSubmit={e=>{e.preventDefault();onApply({start_date:start,end_date:end,group_date:''});}}>
      <label>Playback start date · UTC<input type="date" value={start} onChange={e=>setStart(e.target.value)}/></label>
      <label>Playback end date · UTC<input type="date" min={start||undefined} value={end} onChange={e=>setEnd(e.target.value)}/></label>
      <button type="submit">Apply playback interval</button>
    </form>
    <label>UTC day group<select value={selection.group_date} onChange={e=>onApply({...selection,group_date:e.target.value})}>
      <option value="">All days in the interval</option>
      {selection.group_date&&!group&&<option value={selection.group_date}>{selection.group_date} · no exposures in this interval</option>}
      {groups.map(g=><option key={g.day} value={g.day}>{g.day} · {g.indices.length} exposure{g.indices.length===1?'':'s'}</option>)}
    </select></label>
    {group&&<p data-testid="playback-group-interval">{group.indices.length} individual exposures · midpoint range {group.first_midpoint.replace('T',' ')} to {group.last_midpoint.replace('T',' ')} UTC.</p>}
    <p>Groups use the UTC day of each acquisition midpoint. Playback keeps each exposure separate with its actual time and wavelength. Grouping does not average images.</p>
    <button onClick={()=>{setStart('');setEnd('');onApply({...ALL_TIMES});}}>Clear playback filters</button>
  </details>;
}
