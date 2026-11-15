import {useRef,useState,useEffect} from 'react';
import {json} from './api';

export interface NamedPosition {center_deg:number[];name:string;provider:string;warning:string;query_url:string}
export function NameLookup({onResolve}:{onResolve:(result:NamedPosition)=>void}){
  const [name,setName]=useState(''),[busy,setBusy]=useState(false),[message,setMessage]=useState('');
  const request=useRef<AbortController|null>(null);
  useEffect(()=>()=>request.current?.abort(),[]);
  return <form className="name-lookup" onSubmit={async e=>{
    e.preventDefault();request.current?.abort();const abort=new AbortController();request.current=abort;setBusy(true);setMessage('Looking up the catalog name…');
    try{const result=await json<NamedPosition>(`/v1/targets/resolve?name=${encodeURIComponent(name)}`,{signal:abort.signal});if(!abort.signal.aborted){setMessage(`Found ${result.name}. Catalog position; motion is not applied by name lookup.`);onResolve(result);}}
    catch(error){if(!abort.signal.aborted)setMessage(`${String(error)} You can also choose a featured field.`);}
    finally{if(!abort.signal.aborted)setBusy(false);}
  }}>
    <label>Find an object<input aria-label="Object name" placeholder="M101, Vega, Barnard's Star" maxLength={128} value={name} onChange={e=>setName(e.target.value)} required/></label>
    <button type="submit" disabled={busy}>{busy?'Looking up…':'Find object'}</button>
    {message&&<p role="status" aria-label="Object lookup status">{message}</p>}
  </form>;
}
