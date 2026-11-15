import type {ComparisonState} from './viewState';
import type {Sequence} from './types';

export function comparisonImage(a:HTMLCanvasElement,b:HTMLCanvasElement,sequence:Sequence,comparison:ComparisonState,
  view:{zoom:number;pan:number[];stretch:number;overlays:string[]}){
  const out=document.createElement('canvas');out.width=comparison.mode==='swipe'?800:1600;out.height=1040;
  const ctx=out.getContext('2d')!;ctx.fillStyle='#090d12';ctx.fillRect(0,0,out.width,out.height);ctx.drawImage(a,0,0,800,800);
  if(comparison.mode==='swipe'){
    const cut=comparison.divider/100*800;ctx.save();ctx.beginPath();ctx.rect(cut,0,800-cut,800);ctx.clip();ctx.drawImage(b,0,0,800,800);ctx.restore();
    ctx.strokeStyle='#ecf3f7';ctx.beginPath();ctx.moveTo(cut,0);ctx.lineTo(cut,800);ctx.stroke();
  }else ctx.drawImage(b,800,0,800,800);
  ctx.fillStyle='#ecf3f7';ctx.font='16px monospace';ctx.fillText(`Vantage · ${sequence.name} · ${comparison.mode} · visual comparison`,24,830);
  ctx.font='11px monospace';
  for(const [offset,index] of [comparison.frame_a,comparison.frame_b].entries()){
    const f=sequence.frames[index];ctx.fillText(`${offset?'B':'A'} · ${f.utc_mid} · ${f.obs_id} · ${f.wavelength_um?.toFixed(4)} µm · ${f.release}`,24,858+offset*26);
  }
  const stretch=comparison.independent?`independent A=${comparison.stretch_a}, B=${comparison.stretch_b}`:`shared ${view.stretch}`;
  ctx.fillText(`Display stretch: ${stretch} · visual contrast only`,24,910);
  ctx.fillText(`Zoom ${view.zoom}; pan ${view.pan.join(', ')}; divider ${comparison.divider}%; layers ${view.overlays.join(', ')||'none'}`,24,936);
  ctx.fillText('Visual context · no numerical subtraction or brightness-change measurement.',24,962);
  ctx.fillText('NASA/SPHEREx · JPL/Caltech/IPAC · catalog attribution and processing in provenance JSON.',24,988);
  ctx.fillText(`Sequence ${sequence.id} · export JSON for both input identities and view settings.`,24,1014);
  return out;
}
