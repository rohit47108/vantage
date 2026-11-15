import React, { useState, useEffect, useRef,useMemo } from "react";
import { createRoot } from "react-dom/client";
import { SkyCanvas } from "./SkyCanvas";
import { Methods } from "./Methods";
import { PixelInspector } from "./PixelInspector";
import { readView, viewQuery } from "./viewState";
import type {ComparisonState} from './viewState';
import {ComparisonSurface} from './ComparisonSurface';
import {comparisonImage} from './comparisonExport';
import {TimeSelectionControls} from './TimeSelectionControls';
import {ALL_TIMES,selectTemporalFrames} from './timeSelection';
import type {TimeSelection} from './timeSelection';
import type { Sequence, Plane, Coverage } from "./types";
import { json, readResponse } from "./api";
import "./style.css";
import { SpectralExplorer } from "./SpectralExplorer";
import { CoaddAnalysis } from "./CoaddAnalysis";
import {SourceSamples} from './SourceSamples';
import {LiveSourceExplorer} from './LiveSourceExplorer';
import type {SourceSeed} from './LiveSourceExplorer';
import { Brand } from "./Brand";
import {NameLookup} from './NameLookup';
import {SurveyContext} from './SurveyContext';
import type {Associations} from './SurveyContext';
import {useSurveyLayers} from './surveys';
import type {CatalogMarker} from './surveys';

function download(name: string, value: string, type = "application/json") {
  const url = URL.createObjectURL(new Blob([value], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function TemporalExplorer({onSpectral,onSources}:{onSpectral:()=>void;onSources:(seed?:SourceSeed)=>void}) {
  const [analysis,setAnalysis]=useState(false);
  const [targetLoading,setTargetLoading]=useState(false);
  const [catalog, setCatalog] = useState<Sequence[]>([]),
    [sequence, setSequence] = useState<Sequence | null>(null),
    [planes, setPlanes] = useState<Plane[]>([]);
  const [index, setIndex] = useState(0),
    [playing, setPlaying] = useState(false),
    [speed, setSpeed] = useState(1),
    [loop, setLoop] = useState(false);
  const [zoom, setZoom] = useState(1),
    [pan, setPan] = useState([0, 0]),
    [stretch, setStretch] = useState(1),
    [overlays, setOverlays] = useState(["prediction"]);
  const [message, setMessage] = useState("Loading prepared observations…"),
    [panel, setPanel] = useState(() => window.innerWidth > 760),
    [methods, setMethods] = useState(false);
  const [ra, setRa] = useState("08h55m10.831s"),
    [dec, setDec] = useState("-7d14m42.53s"),
    [fov, setFov] = useState(6);
  const [inspect, setInspect] = useState<number[] | null>(null),
    [compare, setCompare] = useState(false),
    [a, setA] = useState(0),
    [b, setB] = useState(1);
  const [comparisonMode,setComparisonMode]=useState<'side-by-side'|'swipe'>('side-by-side');
  const [independent,setIndependent]=useState(false),[stretchA,setStretchA]=useState(1),[stretchB,setStretchB]=useState(1),[divider,setDivider]=useState(50);
  const comparison:ComparisonState={enabled:compare,mode:comparisonMode,frame_a:a,frame_b:b,independent,stretch_a:stretchA,stretch_b:stretchB,divider};
  const [timeSelection,setTimeSelection]=useState<TimeSelection>({...ALL_TIMES});
  const visibleIndices=useMemo(()=>selectTemporalFrames(sequence?.frames??[],timeSelection),[sequence,timeSelection]);
  const playbackPosition=visibleIndices.indexOf(index);
  useEffect(()=>{
    if(!visibleIndices.length){setPlaying(false);setCompare(false);return;}
    if(!visibleIndices.includes(index))setIndex(visibleIndices[0]);
    if(!visibleIndices.includes(a)||!visibleIndices.includes(b)){setA(visibleIndices[0]);setB(visibleIndices[Math.min(1,visibleIndices.length-1)]);}
    if(visibleIndices.length<2)setCompare(false);
  },[visibleIndices,index,a,b]);
  function applyTimeSelection(value:TimeSelection){setPlaying(false);setInspect(null);setInspectFrame(null);setTimeSelection(value);}
  const [coverage, setCoverage] = useState<Coverage | null>(null),
    [detector, setDetector] = useState(6),
    [jobId, setJobId] = useState<string | null>(null);
  const [startDate, setStartDate] = useState("");
  const [inspectFrame, setInspectFrame] = useState<number | null>(null);
  const [endDate, setEndDate] = useState("");
  const [wavelength, setWavelength] = useState("");
  const [failedSelection, setFailedSelection] = useState<Sequence | null>(null);
  const [surveyOpacity,setSurveyOpacity]=useState([.8,.8]);
  const [selectedCatalog,setSelectedCatalog]=useState<string|null>(null);
  const [surveyFrame,setSurveyFrame]=useState<number|null>(null);
  const [surveyOpen,setSurveyOpen]=useState(false);
  const [associations,setAssociations]=useState<Associations|null>(null);
  const surveys=useSurveyLayers(sequence,overlays);
  useEffect(()=>{setSelectedCatalog(null);setSurveyFrame(null);setAssociations(null);},[sequence?.id]);
  useEffect(()=>setSurveyFrame(null),[index,compare,a,b]);
  function catalogMarkers(frameIndex:number):CatalogMarker[]{
    return [surveys.gaia.layer,surveys.wise.layer].flatMap((layer,i)=>{
      if(!layer||layer.sequence_id!==sequence?.id||!overlays.includes(layer.survey)||surveyOpacity[i]===0)return [];
      return layer.sources.flatMap(source=>{
        const pixel=source.pixels_by_frame[frameIndex];
        return pixel?[{key:`${source.survey}:${source.id}`,survey:source.survey,pixel,selected:selectedCatalog===`${source.survey}:${source.id}`,opacity:surveyOpacity[i]}]:[];
      });
    });
  }
  function selectCatalog(key:string,frameIndex:number){
    setSelectedCatalog(key);setSurveyFrame(frameIndex);setPanel(true);setSurveyOpen(true);
  }
  const request = useRef(0),
    canvas = useRef<HTMLCanvasElement>(null);
  const canvasB=useRef<HTMLCanvasElement>(null);
  async function open(s: Sequence, replace = true, collapseControls = true) {
    const generation = ++request.current;
    setTargetLoading(true);
    setPlaying(false);
    setMessage("Preparing aligned frames…");
    try {
      const data = await Promise.all(
        s.frames.map(async (f) => {
          try {
            return await json(f.asset);
          } catch (error) {
            throw new Error(
              `${s.name}: ${f.obs_id} at ${f.utc_mid}. ${String(error)}`,
            );
          }
        }),
      );
      if (generation !== request.current) return;
      setSequence(s);
      setPlanes(data);
      setIndex(0);
      setA(0);
      setB(Math.min(1, s.frames.length - 1));
      setPan([0, 0]);
      setZoom(1);
      setInspect(null);
      setInspectFrame(null);
      setCompare(false);
      setRa(String(s.center_deg[0]));
      setDec(String(s.center_deg[1]));
      setFov(s.fov_arcmin);
      setMessage("");
      setCoverage(null);
      if (replace) history.pushState(null, "", `/sequence/${s.id}`);
      const view = readView(replace ? "" : location.search, s.frames.length);
      setIndex(view.frame);
      setZoom(view.zoom);
      setPan(view.pan);
      setStretch(view.stretch);
      setTimeSelection(view.time_selection);
      setCompare(view.comparison.enabled);setComparisonMode(view.comparison.mode);
      setA(view.comparison.frame_a);setB(view.comparison.frame_b);
      setIndependent(view.comparison.independent);setStretchA(view.comparison.stretch_a);setStretchB(view.comparison.stretch_b);setDivider(view.comparison.divider);
      setOverlays(view.overlays);
      setSurveyOpacity(view.survey_opacity||[.8,.8]);
      setJobId(null);
      setFailedSelection(null);
      if (window.innerWidth <= 760 && collapseControls) setPanel(false);
    } catch (e) {
      if (generation === request.current) {
        setFailedSelection(s);
        setMessage(`Frames unavailable. Playback paused. ${String(e)}`);
      }
    } finally {
      if (generation === request.current) setTargetLoading(false);
    }
  }
  // Cleanup and generation guards follow https://react.dev/reference/react/useEffect#fetching-data-with-effects
  useEffect(() => {
    let active = true;
    json("/prepared/catalog.json")
      .then(async (items: Sequence[]) => {
        if (!active) return;
        setCatalog(items);
        const id = location.pathname.split("/sequence/")[1];
        const selected = items.find((s) => s.id === id);
        if (id && !selected) {
          try {
            await open(await json(`/prepared/${id}/manifest.json`), false);
          } catch {
            setMessage(
              "This sequence is unavailable on this server. Choose a prepared field.",
            );
          }
          return;
        }
        await open(
          selected || items.find((s) => s.key === "wise0855")!,
          !id && !location.pathname.startsWith("/sky"),
          false,
        );
        if (location.pathname.startsWith("/sky")) {
          const q = new URLSearchParams(location.search);
          setRa(q.get("ra") || "");
          setDec(q.get("dec") || "");
          setFov(Number(q.get("fov_arcmin")) || 6);
          await searchCoordinates(
            q.get("ra") || "",
            q.get("dec") || "",
            Number(q.get("fov_arcmin")) || 6,
          );
        }
      })
      .catch((e) => setMessage(String(e)));
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    async function restore() {
      const id = location.pathname.split("/sequence/")[1];
      if (id) {
        try {
          await open(await json(`/prepared/${id}/manifest.json`), false);
        } catch {
          setMessage(
            "Shared sequence is unavailable. Choose a prepared field.",
          );
        }
      } else if (location.pathname === "/sky") {
        const q = new URLSearchParams(location.search);
        const nextRa = q.get("ra") || "",
          nextDec = q.get("dec") || "",
          nextFov = Number(q.get("fov_arcmin")) || 6;
        setRa(nextRa);
        setDec(nextDec);
        setFov(nextFov);
        await searchCoordinates(nextRa, nextDec, nextFov);
      }
    }
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, []);
  useEffect(() => {
    if (!playing || !sequence) return;
    const timer = setInterval(
      () =>
        setIndex((i) => {
          const position=visibleIndices.indexOf(i);
          if (position+1<visibleIndices.length) return visibleIndices[position+1];
          if (loop) return visibleIndices[0];
          setPlaying(false);
          return i;
        }),
      1000 / speed,
    );
    return () => clearInterval(timer);
  }, [playing, speed, loop, sequence,visibleIndices]);
  useEffect(() => setInspectFrame(null), [index, compare, a, b]);
  async function search(e: React.FormEvent) {
    e.preventDefault();
    history.pushState(
      null,
      "",
      `/sky?ra=${encodeURIComponent(ra)}&dec=${encodeURIComponent(dec)}&fov_arcmin=${fov}`,
    );
    await searchCoordinates(ra, dec, fov);
  }
  async function searchCoordinates(ra: string, dec: string, fov: number) {
    setPlaying(false);
    setCoverage(null);
    setMessage("Searching current SPHEREx coverage…");
    const generation = ++request.current;
    try {
      const response = await fetch("/v1/observations/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ra, dec, fov_arcmin: fov }),
      });
      const result = await readResponse(response);
      if (generation !== request.current) return;
      setCoverage(result);
      setStartDate("");
      setEndDate("");
      setWavelength("");
      setMessage(
        `${result.observations.length} exposure products · ${result.search_completeness} search. Choose a detector and open a sequence.`,
      );
    } catch (error) {
      if (generation === request.current)
        setMessage(`${String(error)}. Prepared examples remain available.`);
    }
  }
  async function generate() {
    const generation = ++request.current;
    setMessage("Submitting sequence…");
    try {
      const response = await fetch("/v1/sequences", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ra,
          dec,
          fov_arcmin: fov,
          detector,
          max_frames: 3,
          start_utc: startDate || null,
          end_utc: endDate || null,
          wavelength_goal_um: wavelength ? Number(wavelength) : null,
        }),
      });
      const job = await readResponse(response);
      setJobId(job.job_id);
      for (let attempt = 0; generation === request.current; attempt++) {
        await new Promise((resolve) =>
          setTimeout(resolve, Math.min(5000, 1000 + attempt * 500)),
        );
        if (generation !== request.current) return;
        const status = await json(job.status_url);
        setMessage(`Archive job · ${status.state}`);
        if (status.state === "complete") {
          setJobId(null);
          await open(await json(`/v1/sequences/${status.result_id}`));
          return;
        }
        if (["failed", "cancelled", "interrupted"].includes(status.state))
          throw new Error(status.error || status.state);
      }
    } catch (e) {
      if (generation === request.current) {
        setJobId(null);
        setMessage(String(e));
      }
    }
  }
  function sequencePath(){return `/sequence/${sequence!.id}?${viewQuery({frame:index,zoom,pan,stretch,overlays,survey_opacity:surveyOpacity,comparison,time_selection:timeSelection})}`;}
  function openSourceSelection(seed?:SourceSeed){
    if(sequence)history.replaceState(null,'',sequencePath());onSources(seed);
  }
  function share(search = false) {
    const path = search
      ? `/sky?ra=${encodeURIComponent(ra)}&dec=${encodeURIComponent(dec)}&fov_arcmin=${fov}`
      : sequencePath();
    navigator.clipboard
      .writeText(location.origin + path)
      .then(() => setMessage("Link copied."))
      .catch(() => setMessage(location.origin + path));
  }
  function exportImage() {
    if (!sequence || !canvas.current) return;
    if(compare&&canvasB.current){
      const out=comparisonImage(canvas.current,canvasB.current,sequence,comparison,{zoom,pan,stretch,overlays});
      const link=document.createElement('a');link.download=`vantage-${sequence.key}-comparison.png`;link.href=out.toDataURL();link.click();return;
    }
    const out = document.createElement("canvas");
    const catalogLayers=[surveys.gaia.layer,surveys.wise.layer].filter(layer=>layer&&overlays.includes(layer.survey));
    out.width = 800;
    out.height = catalogLayers.length?1020:960;
    const exportedFrame = sequence.frames[compare ? a : index];
    const ctx = out.getContext("2d")!;
    ctx.fillStyle = "#090d12";
    ctx.fillRect(0, 0, 800, out.height);
    ctx.drawImage(canvas.current, 0, 0);
    ctx.fillStyle = "#ecf3f7";
    ctx.font = "16px monospace";
    ctx.fillText(
      `Vantage · ${sequence.name} · SPHEREx ${exportedFrame.release}`,
      24,
      830,
    );
    ctx.fillText(
      `${exportedFrame.utc_mid} · ${exportedFrame.wavelength_um?.toFixed(4)} µm`,
      24,
      857,
    );
    ctx.font = "12px monospace";
    ctx.fillText(
      "Visual context · quality and wavelength limits apply · NASA/JPL/Caltech/IPAC",
      24,
      884,
    );
    ctx.fillText(
      `${exportedFrame.obs_id} · sequence ${sequence.id.slice(0, 16)}`,
      24,
      912,
    );
    if(catalogLayers.length){
      ctx.fillText(`Catalog context: ${catalogLayers.map(l=>l!.survey==='gaia'?'Gaia DR3 optical circles':'AllWISE historical IR diamonds').join('; ')}`,24,944);
      ctx.fillText('ESA/Gaia/DPAC · WISE UCLA/JPL/Caltech/NASA · full credits in provenance',24,970);
      ctx.fillText('Imported positions; not SPHEREx detections or confirmed identities.',24,996);
    }
    const link = document.createElement("a");
    link.download = `vantage-${sequence.key}-${compare ? a : index}.png`;
    link.href = out.toDataURL();
    link.click();
  }
  const current = sequence?.frames[index],
    plane = planes[index];
  return (
    <>
      <header>
        <Brand context="Explore" />
        <span className="tag">SPHEREx · infrared sky</span>
        <button onClick={() => share()} disabled={!sequence}>
          Share view ↗
        </button>
        <span className="badge">● {sequence?.data_status || "prepared"}</span>
      </header>
      <nav aria-label="Main navigation">
        <button title="Measure a source" onClick={()=>openSourceSelection()}>∿<small>Sources</small></button>
        <button title="Explore wavelengths" onClick={onSpectral}>λ<small>Wavelengths</small></button>
        <button
          title="Explore"
          onClick={() => {
            setMethods(false);
            setPanel(!panel);
          }}
        >
          ◎<small>Explore</small>
        </button>
        <button
          title="Examples"
          onClick={() => {
            setMethods(false);
            setPanel(true);
          }}
        >
          ✧<small>Examples</small>
        </button>
        <button title="Data and methods" onClick={() => setMethods(true)}>
          ≋<small>Methods</small>
        </button>
      </nav>
      {panel && (
        <aside className="controls">
          <div className="panelTitle">
            <h1>Explore the infrared sky</h1>
            <button aria-label="Hide controls" onClick={() => setPanel(false)}>
              ‹
            </button>
          </div>
          <p className="muted">{sequence?.mode==='source_tracked'?'Follow the predicted object position between observations.':'One patch of sky. Different moments in time.'}</p>
          <NameLookup onResolve={result=>{setRa(String(result.center_deg[0]));setDec(String(result.center_deg[1]));history.pushState(null,'',`/sky?ra=${result.center_deg[0]}&dec=${result.center_deg[1]}&fov_arcmin=${fov}`);void searchCoordinates(String(result.center_deg[0]),String(result.center_deg[1]),fov);}}/>
          <form onSubmit={search}>
            <label>
              Right ascension
              <input
                value={ra}
                onChange={(e) => setRa(e.target.value)}
                required
                placeholder="Degrees or 08h55m10.831s"
              />
            </label>
            <label>
              Declination
              <input
                value={dec}
                onChange={(e) => setDec(e.target.value)}
                required
                placeholder="Degrees or -7d14m42.53s"
              />
            </label>
            <label>
              Field of view · arcminutes
              <input
                type="number"
                min={1}
                max={30}
                step={1}
                value={fov}
                onChange={(e) => setFov(Number(e.target.value))}
              />
            </label>
            <button className="primary" type="submit">
              Search archive ↗
            </button>
            <button type="button" onClick={() => share(true)}>
              Copy coordinate link
            </button>
          </form>
          {coverage && (
            <section>
              <h2>Current coverage</h2>
              <p>
                {coverage.observations.length} products · {coverage.data_status}{" "}
                · {coverage.search_completeness}
              </p>
              <label>
                Detector
                <select
                  value={detector}
                  onChange={(e) => setDetector(Number(e.target.value))}
                >
                  {[1, 2, 3, 4, 5, 6].map((n) => (
                    <option key={n} value={n}>
                      D{n} ·{" "}
                      {
                        coverage.observations.filter((r) => r.detector === n)
                          .length
                      }{" "}
                      products
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Start UTC date
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </label>
              <label>
                End UTC date
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                />
              </label>
              <label>
                Wavelength goal · µm
                <input
                  type="number"
                  min="0.7"
                  max="5.1"
                  step="0.001"
                  placeholder="Any returned detector sample"
                  value={wavelength}
                  onChange={(e) => setWavelength(e.target.value)}
                />
              </label>
              <p className="muted">
                Up to 20 exposure headers are checked against precision
                wavelength maps at your field center. The final support map
                tests agreement across the field.
              </p>
              <button className="primary" onClick={generate}>
                Open live sequence
              </button>
              <details>
                <summary>Exposure metadata</summary>
                {coverage.observations
                  .filter((r) => r.detector === detector)
                  .slice(0, 40)
                  .map((r) => (
                    <p key={r.obs_id}>
                      {r.obs_id}
                      <small>
                        MJD {r.mjd_mid.toFixed(5)} · {r.em_min_um.toFixed(2)}–
                        {r.em_max_um.toFixed(2)} µm · {r.release}
                      </small>
                    </p>
                  ))}
              </details>
            </section>
          )}
          {jobId && (
            <button
              onClick={async () => {
                try {
                  const result = await readResponse(
                    await fetch(`/v1/jobs/${jobId}`, { method: "DELETE" }),
                  );
                  request.current++;
                  setJobId(null);
                  setMessage(
                    result.state === "complete"
                      ? "This job has already completed. Open the same request to retrieve it."
                      : "Cancellation confirmed.",
                  );
                } catch (error) {
                  setMessage(
                    `Cancellation could not be confirmed. ${String(error)}`,
                  );
                }
              }}
            >
              Cancel job
            </button>
          )}
          <h2>Featured fields</h2>
          <div className="targets">
            {catalog.map((s) => (
              <button
                key={s.id}
                aria-pressed={sequence?.id === s.id}
                onClick={() => open(s)}
              >
                {s.name}
                <small>
                  {s.frames.length} frames ·{" "}
                  {s.mode === "source_tracked" ? "tracked" : "fixed sky"}
                </small>
              </button>
            ))}
          </div>
          <details className="survey-disclosure" open={surveyOpen} onToggle={e=>setSurveyOpen(e.currentTarget.open)}><summary>Other telescopes · Gaia / WISE</summary>
            <SurveyContext key={sequence?.id} sequence={sequence} frame={surveyFrame??(compare?a:index)} gaia={surveys.gaia} wise={surveys.wise} overlays={overlays} toggle={name=>setOverlays(old=>old.includes(name)?old.filter(x=>x!==name):[...old,name])} opacity={surveyOpacity} setOpacity={setSurveyOpacity} selected={selectedCatalog} onSelect={key=>selectCatalog(key,compare?a:index)} retry={surveys.retry} onAssociations={setAssociations}/>
          </details>
          <h2>Layers</h2>
          {["prediction", "coverage", "quality", "spectral"].map((name) => (
            <label className="check" key={name}>
              <input
                type="checkbox"
                checked={overlays.includes(name)}
                disabled={
                  name === "prediction" &&
                  !sequence?.frames.some(
                    (frame) => frame.prediction_pixel !== null,
                  )
                }
                onChange={() =>
                  setOverlays((o) =>
                    o.includes(name)
                      ? o.filter((x) => x !== name)
                      : [...o, name],
                  )
                }
              />
              {name === "prediction"
                ? "Predicted position (amber ring)"
                : name === "spectral"
                  ? "Joint support (cyan)"
                  : name === "quality"
                    ? "Defective support (amber)"
                    : "Missing coverage (hatching)"}
              {name === "prediction" &&
                !sequence?.frames.some(
                  (frame) => frame.prediction_pixel !== null,
                ) && <small>No locator for this field</small>}
            </label>
          ))}
          {sequence&&<TimeSelectionControls frames={sequence.frames} selection={timeSelection} onApply={applyTimeSelection}/>}
          <label>
            Shared display stretch
            <input
              type="range"
              min={0.3}
              max={3}
              step={0.1}
              value={stretch}
              onChange={(e) => setStretch(Number(e.target.value))}
              disabled={compare&&independent}
            />
          </label>
        </aside>
      )}
      <main className={panel ? "withPanel" : ""}>
        {failedSelection && (
          <button className="retry" onClick={() => open(failedSelection)}>
            Retry requested frames
          </button>
        )}
        <div className="fieldHeading">
          <div className="eyebrow">
            NASA SPHEREx /{" "}
            {sequence?.mode === "source_tracked"
              ? "SOURCE-TRACKED THUMBNAILS"
              : "FIXED SKY FIELD"}
          </div>
          <h2>{sequence?.name || "Loading sky"}</h2>
          <p className="mono">
            {sequence?.center_deg.map((n) => n.toFixed(6)).join("°, ")}° ·{" "}
            {sequence?.fov_arcmin}′ field · north ↑ east ←
          </p>
          {(timeSelection.start_date||timeSelection.end_date||timeSelection.group_date)&&<p data-testid="playback-active-selection">
            Showing {visibleIndices.length} of {sequence?.frames.length} exposures · UTC midpoint dates {timeSelection.start_date||'earliest'} to {timeSelection.end_date||'latest'}{timeSelection.group_date?` · day group ${timeSelection.group_date}`:''}.
          </p>}
        </div>
        {message && (
          <div className="notice" role="status">
            {message}
            <button onClick={() => setMessage("")} aria-label="Dismiss status">
              ×
            </button>
          </div>
        )}
        {sequence&&!visibleIndices.length&&<div className="sky empty-time-selection"><div>
          <p>No exposures in this playback selection.</p><p>Choose a different interval or day group. The retained sequence contains {sequence.frames.length} individual exposures.</p>
          <button onClick={()=>applyTimeSelection({...ALL_TIMES})}>Show all sequence exposures</button>
        </div></div>}
        {plane && current && playbackPosition>=0 && (
          <ComparisonSurface enabled={compare} swipe={comparisonMode==='swipe'} divider={divider}>
            <SkyCanvas
              plane={compare ? planes[a] : plane}
              frame={compare ? sequence!.frames[a] : current}
              zoom={zoom}
              pan={pan}
              stretch={compare&&independent?stretchA:stretch}
              label={compare?`Frame A, ${sequence!.frames[a].utc_mid}`:undefined}
              overlays={overlays}
              onPan={setPan}
              onInspect={(x, y) => {
                setInspect([x, y]);
                setInspectFrame(compare ? a : index);
              }}
              canvasRef={canvas}
              catalogMarkers={catalogMarkers(compare?a:index)}
              onCatalogSelect={key=>selectCatalog(key,compare?a:index)}
            />
            {compare && (
              <SkyCanvas
                plane={planes[b]}
                frame={sequence!.frames[b]}
                zoom={zoom}
                pan={pan}
                stretch={independent?stretchB:stretch}
                label={`Frame B, ${sequence!.frames[b].utc_mid}`}
                clipLeft={comparisonMode==='swipe'?divider:undefined}
                canvasRef={canvasB}
                overlays={overlays}
                catalogMarkers={catalogMarkers(b)}
                onCatalogSelect={key=>selectCatalog(key,b)}
                onPan={setPan}
                onInspect={(x, y) => {
                  setInspect([x, y]);
                  setInspectFrame(b);
                }}
              />
            )}
          </ComparisonSurface>
        )}
        <div className="viewTools">
          <button
            onClick={() => setZoom((z) => Math.min(6, z * 1.25))}
            aria-label="Zoom in"
          >
            +
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(0.5, z / 1.25))}
            aria-label="Zoom out"
          >
            −
          </button>
          <button
            onClick={() => {
              setZoom(1);
              setPan([0, 0]);
              setStretch(1);
              setStretchA(1);setStretchB(1);setDivider(50);
            }}
          >
            Reset view
          </button>
          <button
            aria-pressed={compare}
            disabled={!sequence || visibleIndices.length < 2}
            title={
              sequence && visibleIndices.length < 2
                ? "Comparison needs two observations"
                : "Compare two frames"
            }
            onClick={() => {
              setCompare(!compare);
              setPlaying(false);
            }}
          >
            A/B compare
          </button>
        </div>
        {sequence && playbackPosition>=0 && (
          <section className="dock" aria-label="Playback controls">
            <div className="frameInfo">
              <strong>
                {current?.utc_mid.replace("T", " ").replace("Z", " UTC")}
              </strong>
              <span>
                {current?.wavelength_um?.toFixed(4)} µm · D{current?.detector} ·{" "}
                {current?.release.toUpperCase()}
              </span>
            </div>
            <div className="playControls">
              <button
                aria-label="Previous frame"
                disabled={playbackPosition<=0}
                onClick={() => {
                  setPlaying(false);
                  setIndex(visibleIndices[Math.max(0,playbackPosition-1)]);
                }}
              >
                ←
              </button>
              <button
                className="primary"
                disabled={visibleIndices.length < 2}
                title={
                  visibleIndices.length < 2
                    ? "One observation is available. Choose a wider date range for playback."
                    : "Play or pause actual observations"
                }
                onClick={() => {
                  setCompare(false);
                  setPlaying(!playing);
                }}
              >
                {playing ? "Pause" : "Play"}
              </button>
              <button
                aria-label="Next frame"
                disabled={playbackPosition===visibleIndices.length-1}
                onClick={() => {
                  setPlaying(false);
                  setIndex(visibleIndices[Math.min(visibleIndices.length-1,playbackPosition+1)]);
                }}
              >
                →
              </button>
              <label>
                Speed
                <select
                  value={speed}
                  onChange={(e) => setSpeed(Number(e.target.value))}
                >
                  <option value={0.5}>0.5 fps</option>
                  <option value={1}>1 fps</option>
                  <option value={2}>2 fps</option>
                </select>
              </label>
              <label className="check">
                <input
                  type="checkbox"
                  checked={loop}
                  onChange={(e) => setLoop(e.target.checked)}
                />
                Loop
              </label>
            </div>
            <label className="scrub">
              Frame {playbackPosition + 1} of {visibleIndices.length}
              <input
                aria-label="Selected frame"
                type="range"
                min={0}
                max={visibleIndices.length - 1}
                value={playbackPosition}
                onChange={(e) => {
                  setPlaying(false);
                  setIndex(visibleIndices[Number(e.target.value)]);
                }}
              />
            </label>
            <div className="dates">
              {visibleIndices.map((i,position) => {const f=sequence.frames[i];return (
                <button
                  key={f.obs_id}
                  aria-pressed={index === i}
                  onClick={() => {
                    setPlaying(false);
                    setIndex(i);
                  }}
                >
                  {f.utc_mid.slice(0, 10)}
                  {position > 0 && (
                    <small>
                      +{(f.mjd_mid - sequence.frames[visibleIndices[position-1]].mjd_mid).toFixed(2)}{" "}
                      days
                    </small>
                  )}
                </button>
              );})}
            </div>
          </section>
        )}
      </main>
      {sequence && current && playbackPosition>=0 && (
        <aside className="inspector">
          <div className="eyebrow">OBSERVATION DETAILS</div>
          <h2>
            {sequence.science_status === "context_only"
              ? "Context sequence"
              : sequence.science_status === "matched_visual"
                ? "Matched visual sequence"
                : "Restricted support"}
          </h2>
          <p className="warning">{sequence.limitations[0]}</p>
          <dl>
            <dt>Joint usable field</dt>
            <dd>{(sequence.joint_support_fraction * 100).toFixed(1)}%</dd>
            {!compare&&<>
              <dt>Acquisition UTC</dt><dd>{current.utc_mid}</dd>
              <dt>Observation</dt><dd>{current.obs_id}</dd>
              <dt>Source-core bits</dt><dd>{current.core_flag_bits.join(', ')||'Not screened'}</dd>
            </>}
          </dl>
          <p className="muted">
            Bit 21 marks source information. Brightness-change measurements are
            unavailable.
          </p>
          {!compare&&<a href={current.source_url} target="_blank" rel="noreferrer">
            Original FITS ↗
          </a>}
          {compare && (
            <div>
              <section aria-label="Comparison acquisitions">
                {[a,b].map((frameIndex,side)=>{const frame=sequence.frames[frameIndex];return <p key={side}>
                  <strong>{side?'B':'A'} · {frame.utc_mid}</strong><br/>
                  {frame.wavelength_um?.toFixed(4)} µm · D{frame.detector} · {frame.release.toUpperCase()}<br/>
                  <span className="mono">{frame.obs_id}</span><br/>Source-core bits: {frame.core_flag_bits.join(', ')||'Not screened'}<br/>
                  <a href={frame.source_url} target="_blank" rel="noreferrer">Original {side?'B':'A'} FITS ↗</a>
                </p>;})}
              </section>
              <label>Comparison display<select value={comparisonMode} onChange={e=>setComparisonMode(e.target.value as 'side-by-side'|'swipe')}>
                <option value="side-by-side">Side by side</option><option value="swipe">{sequence.mode==='source_tracked'?'Swipe aligned tracked thumbnails':'Swipe over the same sky'}</option>
              </select></label>
              {sequence.mode==='source_tracked'&&<p className="warning">These thumbnails follow the predicted object position. The two halves use different sky centers. Inspect each exposure's coordinates.</p>}
              {comparisonMode==='swipe'&&<label>Swipe divider<input type="range" min={0} max={100} value={divider} onChange={e=>setDivider(Number(e.target.value))}/></label>}
              <label className="check"><input type="checkbox" checked={independent} onChange={e=>{
                setIndependent(e.target.checked);if(e.target.checked){setStretchA(stretch);setStretchB(stretch);}
              }}/>Independent display stretches</label>
              {independent&&<>
                <label>Frame A display stretch<input type="range" min={.3} max={3} step={.1} value={stretchA} onChange={e=>setStretchA(Number(e.target.value))}/></label>
                <label>Frame B display stretch<input type="range" min={.3} max={3} step={.1} value={stretchB} onChange={e=>setStretchB(Number(e.target.value))}/></label>
                <p className="muted">Independent stretches change visual contrast. Recorded pixel brightness is unchanged. This comparison does not subtract the exposures or measure a brightness change.</p>
              </>}
              <label>
                Frame A
                <select
                  value={a}
                  onChange={(e) => setA(Number(e.target.value))}
                >
                  {visibleIndices.map(i=>{const f=sequence.frames[i];return (
                    <option value={i} key={f.obs_id}>
                      {f.utc_mid.replace('T',' ')} · {f.obs_id}
                    </option>
                  );})}
                </select>
              </label>
              <label>
                Frame B
                <select
                  value={b}
                  onChange={(e) => setB(Number(e.target.value))}
                >
                  {visibleIndices.map(i=>{const f=sequence.frames[i];return (
                    <option value={i} key={f.obs_id}>
                      {f.utc_mid.replace('T',' ')} · {f.obs_id}
                    </option>
                  );})}
                </select>
              </label>
            </div>
          )}
          <h2>Inspect the field</h2>
          <p className="muted">
            Click a pixel, or focus the sky and press Enter.
          </p>
          {inspect && sequence && (
            <><PixelInspector
              plane={planes[inspectFrame ?? index]}
              frame={sequence.frames[inspectFrame ?? index]}
              pixel={inspect}
            /><button onClick={()=>{
              const plane=planes[inspectFrame??index],x=inspect[0],y=inspect[1];
              openSourceSelection({name:'Selected sky position',ra:plane.ra[y][x],dec:plane.dec[y][x]});
            }}>Measure this sky position</button></>
          )}
          <div className="exports">
            <button onClick={exportImage}>Export labeled image ↓</button>
            <button
              onClick={() =>
                download(
                  `vantage-${sequence.id}.json`,
                  JSON.stringify(
                    {
                      ...sequence,
                      view: { frame: index, zoom, pan, stretch, overlays, comparison, time_selection:timeSelection,selected_frame_indices:visibleIndices, survey_opacity:surveyOpacity, selected_catalog:selectedCatalog, catalog_frame:surveyFrame },
                      catalog_context:{gaia:surveys.gaia.layer,wise:surveys.wise.layer,associations,
                        failures:{gaia:surveys.gaia.error||null,wise:surveys.wise.error||null},
                        interpretation:'Imported catalog locators and proximity candidates; not measured SPHEREx positions or confirmed identities.'},
                    },
                    null,
                    2,
                  ),
                )
              }
            >
              Export provenance ↓
            </button>
            <button onClick={() => setAnalysis(true)} disabled={!sequence||visibleIndices.length<2||targetLoading||!!failedSelection}>Stack observations</button>
            {selectedCatalog?.startsWith('gaia:')&&<button onClick={()=>{
              const source=surveys.gaia.layer?.sources.find(s=>'gaia:'+s.id===selectedCatalog);
              if(source)openSourceSelection({name:'Gaia DR3 '+source.id,ra:source.ra,dec:source.dec,pmra:source.pmra,pmdec:source.pmdec,ref_epoch:source.ref_epoch??2016});
            }}>Measure selected Gaia source</button>}
            <button onClick={() => setMethods(true)}>Data & methods</button>
          </div>
        </aside>
      )}
      {analysis&&sequence&&<CoaddAnalysis key={sequence.id} sequence={sequence} onClose={()=>setAnalysis(false)}/>}
      {methods && (
        <Methods
          credits={[sequence?.credits,surveys.gaia.layer?.credits,surveys.wise.layer?.credits].filter(Boolean).join('\n\n')}
          close={() => setMethods(false)}
        />
      )}
    </>
  );
}
function App(){
  const [mode,setMode]=useState(new URLSearchParams(location.search).get('view')||'time');
  const [product,setProduct]=useState(new URLSearchParams(location.search).get('product'));
  const [sourceSeed,setSourceSeed]=useState<SourceSeed|null>(null);
  const returnTo=useRef('/');
  function openSource(seed?:SourceSeed){
    returnTo.current=location.pathname+location.search;setSourceSeed(seed??null);
    const params=new URLSearchParams({view:'measure'});
    if(seed){params.set('source_ra',String(seed.ra));params.set('source_dec',String(seed.dec));if(seed.name)params.set('source_name',seed.name);
      if(seed.pmra!=null&&seed.pmdec!=null){params.set('pmra',String(seed.pmra));params.set('pmdec',String(seed.pmdec));params.set('ref_epoch',String(seed.ref_epoch??2016));}}
    history.pushState(null,'','/?'+params);setMode('measure');
  }
  if(product)return <CoaddAnalysis initialProduct={product} standalone onClose={()=>{history.replaceState(null,'','/');setProduct(null);}}/>;
  if(mode==='sources')return <SourceSamples initialProduct={new URLSearchParams(location.search).get('samples')} onTime={()=>{history.pushState(null,'','/');setMode('time');}}/>;
  if(mode==='measure')return <LiveSourceExplorer seed={sourceSeed} onTime={()=>{history.pushState(null,'',returnTo.current);setMode(new URLSearchParams(location.search).get('view')||'time');}}/>;
  return mode==='wavelengths'?<SpectralExplorer onMeasure={position=>openSource({name:'Selected mosaic position',ra:position[0],dec:position[1]})} onTime={()=>{history.pushState(null,'','/');setMode('time');}}/>:<TemporalExplorer onSources={openSource} onSpectral={()=>{history.pushState(null,'','/?view=wavelengths');setMode('wavelengths');}}/>;
}
createRoot(document.getElementById("root")!).render(<App />);
