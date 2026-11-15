export interface ViewState {
  frame: number;
  zoom: number;
  pan: number[];
  stretch: number;
  overlays: string[];
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
            ["prediction", "coverage", "quality", "spectral"].includes(x),
          )
      : ["prediction"],
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
    v: "1",
  }).toString();
}
