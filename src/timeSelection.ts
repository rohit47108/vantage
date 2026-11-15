export interface TimeSelection {start_date:string;end_date:string;group_date:string}
interface Acquisition {utc_mid:string}
export const ALL_TIMES:TimeSelection={start_date:'',end_date:'',group_date:''};

function calendarDate(value:string|null){
  if(!value||!/^\d{4}-\d{2}-\d{2}$/.test(value))return '';
  const stamp=Date.parse(value+'T00:00:00Z');
  return Number.isFinite(stamp)&&new Date(stamp).toISOString().slice(0,10)===value?value:'';
}
export function parseTimeSelection(query:URLSearchParams):TimeSelection{
  return {start_date:calendarDate(query.get('time_start')),end_date:calendarDate(query.get('time_end')),group_date:calendarDate(query.get('time_day'))};
}
function utcDay(frame:Acquisition){
  const stamp=Date.parse(frame.utc_mid);
  if(!Number.isFinite(stamp))throw new Error('An exposure has no valid acquisition midpoint.');
  return new Date(stamp).toISOString().slice(0,10);
}
export function selectTemporalFrames(frames:Acquisition[],selection:TimeSelection):number[]{
  return frames.flatMap((frame,index)=>{
    const day=utcDay(frame);
    return (!selection.start_date||day>=selection.start_date)&&(!selection.end_date||day<=selection.end_date)&&
      (!selection.group_date||day===selection.group_date)?[index]:[];
  });
}
export function temporalDayGroups(frames:Acquisition[],selection:TimeSelection){
  const groups=new Map<string,{day:string;indices:number[];first_midpoint:string;last_midpoint:string}>();
  for(const index of selectTemporalFrames(frames,{...selection,group_date:''})){
    const frame=frames[index],day=utcDay(frame),group=groups.get(day);
    if(group){
      group.indices.push(index);
      if(Date.parse(frame.utc_mid)<Date.parse(group.first_midpoint))group.first_midpoint=frame.utc_mid;
      if(Date.parse(frame.utc_mid)>Date.parse(group.last_midpoint))group.last_midpoint=frame.utc_mid;
    }else groups.set(day,{day,indices:[index],first_midpoint:frame.utc_mid,last_midpoint:frame.utc_mid});
  }
  return [...groups.values()].sort((a,b)=>a.day.localeCompare(b.day));
}
