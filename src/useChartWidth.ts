import {useEffect,useRef,useState} from 'react';

// Observe the rendered SVG width; data coordinates change without resizing its
// CSS box, avoiding a ResizeObserver layout cycle. Font sizes stay legible.
// https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserver
export function useChartWidth(enabled=true,initial=760){
  const ref=useRef<SVGSVGElement>(null),[width,setWidth]=useState(initial);
  useEffect(()=>{
    if(!enabled||!ref.current)return;
    const observer=new ResizeObserver(entries=>setWidth(Math.max(240,Math.floor(entries[0].contentRect.width))));
    observer.observe(ref.current);return()=>observer.disconnect();
  },[enabled]);
  return {ref,width:enabled?width:initial};
}
