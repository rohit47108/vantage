import {useEffect,useState} from 'react';
import {json} from './api';
import type {Sequence} from './types';

export type SurveyName='gaia'|'wise';
export interface CatalogSource {
  id:string;survey:SurveyName;ra:number;dec:number;ref_epoch?:number|null;
  pmra?:number|null;pmdec?:number|null;parallax?:number|null;
  phot_g_mean_mag?:number|null;w1mpro?:number|null;w2mpro?:number|null;
  w1mjdmean?:number|null;w2mjdmean?:number|null;ext_flg?:number|null;cc_flags?:string;ph_qual?:string;
  motion_model:string;observer_parallax_applied:boolean;pixels_by_frame:(number[]|null)[];coordinates_by_frame:number[][];
}
export interface SurveyLayer {sequence_id:string;survey:SurveyName;sources:CatalogSource[];queried_rows:number;search_completeness:string;queried_radius_deg:number;query_radius_deg:number;query_url:string;query_urls:string[];data_status:string;retrieved_utc:string;credits:string;acknowledgment_url:string;documentation:string;position_semantics:string;limitations:string[]}
export interface CatalogMarker {key:string;survey:SurveyName;pixel:number[];selected:boolean;opacity:number}
export interface SurveyLoad {layer:SurveyLayer|null;loading:boolean;error:string}

function useSurveyLayer(name:SurveyName,sequence:Sequence|null,wanted:boolean,retry:number){
  const [state,set]=useState<SurveyLoad>({layer:null,loading:false,error:''});
  useEffect(()=>{
    const abort=new AbortController();
    set({layer:null,loading:wanted&&!!sequence,error:''});
    if(wanted&&sequence){
      json<SurveyLayer>(`/v1/surveys/${name}?sequence_id=${sequence.id}`,{signal:abort.signal}).then(layer=>{
        if(!abort.signal.aborted&&layer.sequence_id===sequence.id)set({layer,loading:false,error:''});
      }).catch(error=>{if(!abort.signal.aborted)set({layer:null,loading:false,error:String(error)});});
    }
    return()=>abort.abort();
  },[sequence?.id,name,wanted,retry]);
  if(!wanted)return {layer:null,loading:false,error:''};
  if(state.layer&&state.layer.sequence_id!==sequence?.id)return {layer:null,loading:!!sequence,error:''};
  return state;
}

export function useSurveyLayers(sequence:Sequence|null,overlays:string[]){
  const [retry,setRetry]=useState(0);
  const gaia=useSurveyLayer('gaia',sequence,overlays.includes('gaia'),retry);
  const wise=useSurveyLayer('wise',sequence,overlays.includes('wise'),retry);
  return {gaia,wise,retry:()=>setRetry(x=>x+1)};
}
