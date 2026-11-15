export interface ViewState {
  frame: number;
  zoom: number;
  pan: number[];
  stretch: number;
  overlays: string[];
  survey_opacity?:number[];
}

export function readView(search: string, frames: number): ViewState {
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
  };
}

export function viewQuery(view: ViewState) {
  return new URLSearchParams({
    frame: String(view.frame),
    zoom: String(view.zoom),
    x: String(view.pan[0]),
    y: String(view.pan[1]),
    stretch: String(view.stretch),
    layers: view.overlays.join(","),
    gaia_opacity:String(view.survey_opacity?.[0]??.8),
    wise_opacity:String(view.survey_opacity?.[1]??.8),
    v: "1",
  }).toString();
}
