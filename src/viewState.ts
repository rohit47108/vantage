export interface ComparisonState {
  enabled:boolean;mode:'side-by-side'|'swipe';frame_a:number;frame_b:number;
  independent:boolean;stretch_a:number;stretch_b:number;divider:number;
}
export interface ViewState {
  frame: number;
  zoom: number;
  pan: number[];
  stretch: number;
  overlays: string[];
  survey_opacity?:number[];
  comparison?:ComparisonState;
}

export function readView(search: string, frames: number): ViewState&{comparison:ComparisonState} {
  const query = new URLSearchParams(search);
  function bounded(key: string, fallback: number, min: number, max: number) {
    const text = query.get(key);
    const value = text === null ? fallback : Number(text);
    return Number.isFinite(value)
      ? Math.max(min, Math.min(max, value))
      : fallback;
  }
  return {
    frame: Math.floor(bounded("frame", 0, 0, frames - 1)),
    zoom: bounded("zoom", 1, 0.5, 6),
    pan: [bounded("x", 0, -4000, 4000), bounded("y", 0, -4000, 4000)],
    stretch: bounded("stretch", 1, 0.3, 3),
    overlays: query.has("layers")
      ? (query.get("layers") || "")
          .split(",")
          .filter((x) =>
            ["prediction", "coverage", "quality", "spectral", "gaia", "wise"].includes(x),
          )
      : ["prediction"],
    survey_opacity:[bounded('gaia_opacity',.8,0,1),bounded('wise_opacity',.8,0,1)],
    comparison:{enabled:frames>1&&['side-by-side','swipe'].includes(query.get('compare')??''),
      mode:query.get('compare')==='swipe'?'swipe':'side-by-side',
      frame_a:Math.floor(bounded('frame_a',0,0,frames-1)),frame_b:Math.floor(bounded('frame_b',1,0,frames-1)),
      independent:query.get('independent')==='1',stretch_a:bounded('stretch_a',1,.3,3),stretch_b:bounded('stretch_b',1,.3,3),divider:bounded('divider',50,0,100)},
  };
}

export function viewQuery(view: ViewState) {
  const query=new URLSearchParams({
    frame: String(view.frame),
    zoom: String(view.zoom),
    x: String(view.pan[0]),
    y: String(view.pan[1]),
    stretch: String(view.stretch),
    layers: view.overlays.join(","),
    gaia_opacity:String(view.survey_opacity?.[0]??.8),
    wise_opacity:String(view.survey_opacity?.[1]??.8),
    v: "1",
  });
  const c=view.comparison;
  if(c?.enabled){
    query.set('compare',c.mode);query.set('frame_a',String(c.frame_a));query.set('frame_b',String(c.frame_b));
    query.set('independent',c.independent?'1':'0');query.set('stretch_a',String(c.stretch_a));query.set('stretch_b',String(c.stretch_b));query.set('divider',String(c.divider));
  }
  return query.toString();
}
