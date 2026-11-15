import {useEffect,useRef,useState} from 'react';
import type {ReactNode} from 'react';

export function ComparisonSurface({enabled,swipe,divider,children}:{enabled:boolean;swipe:boolean;divider:number;children:ReactNode}){
  const ref=useRef<HTMLDivElement>(null),[size,setSize]=useState(300);
  useEffect(()=>{
    if(!swipe||!enabled||!ref.current)return;
    const observer=new ResizeObserver(entries=>{
      const {width,height}=entries[0].contentRect;setSize(Math.max(1,Math.floor(Math.min(width,height))));
    });
    observer.observe(ref.current);return()=>observer.disconnect();
  },[swipe,enabled]);
  return <div ref={ref} className={enabled?`sky comparison${swipe?' comparison-swipe':''}`:'sky'}>
    {enabled&&swipe?<div className="swipe-content" data-testid="comparison-image" style={{width:size,height:size}}>
      {children}<div className="swipe-line" style={{left:divider+'%'}} aria-hidden="true"/>
      <span className="swipe-label swipe-label-a" aria-hidden="true">A</span><span className="swipe-label swipe-label-b" aria-hidden="true">B</span>
    </div>:children}
  </div>;
}
