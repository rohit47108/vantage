import { useEffect, useRef, useState } from "react";
import { json } from "./api";
import "./spectral.css";
import { Brand } from "./Brand";
import {NameLookup} from './NameLookup';

interface Channel {
  index: number;
  detector: number;
  channel: number;
  wavelength_um: number;
  bandwidth_um: number;
  blank: boolean;
}
interface Metadata {
  channels: Channel[];
  credits: string;
  checked_utc: string;
  properties_url: string;
  limitations: string[];
}
interface SpectralPlane {
  id: string;
  brightness: (number | null)[][];
  hits: number[][];
  flags: number[][];
  shape: number[];
  channel: Channel;
  center_deg: number[];
  fov_arcmin: number;
  coverage_fraction: number;
  sources: { url: string; mjd_start: number; mjd_end: number }[];
  units: string;
}

function save(name: string, data: unknown) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function SpectralExplorer({ onTime }: { onTime: () => void }) {
  const initial = new URLSearchParams(location.search);
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [center, setCenter] = useState([
    Number(initial.get("wave_ra") || 60.8109955),
    Number(initial.get("wave_dec") || 51.3404038),
  ]);
  const [fov, setFov] = useState(Number(initial.get("wave_fov") || 30));
  const [layer, setLayer] = useState(
    Math.min(101, Math.max(0, Number(initial.get("layer") || 62))),
  );
  const [plane, setPlane] = useState<SpectralPlane | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [selected, setSelected] = useState<number[] | null>(null);
  const colorParam = initial.get("rgb")?.split(",").map(Number);
  const validColors =
    colorParam?.length === 3 &&
    colorParam.every(
      (x) => Number.isInteger(x) && x >= 0 && x < 102 && x !== 50 && x !== 51,
    );
  const [colors, setColors] = useState(
    validColors ? colorParam! : [84, 62, 24],
  );
  const [rgb, setRgb] = useState(!!validColors);
  const [rgbPlanes, setRgbPlanes] = useState<SpectralPlane[]>([]);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [status, setStatus] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const abort = new AbortController();
    json<Metadata>("/v1/spectral/metadata", { signal: abort.signal })
      .then(setMetadata)
      .catch((e) => {
        if (!abort.signal.aborted) setError(String(e));
      });
    return () => abort.abort();
  }, []);
  useEffect(() => {
    const abort = new AbortController();
    setLoading(true);
    setError("");
    setPlane(null);
    setRgbPlanes([]);
    const query = (l: number) =>
      `/v1/spectral/plane?ra=${center[0]}&dec=${center[1]}&fov_arcmin=${fov}&layer=${l}`;
    // One request at a time also respects the bounded public context workers.
    const load = async () => {
      try {
        if (rgb) {
          const p: SpectralPlane[] = [];
          for (const l of colors)
            p.push(
              await json<SpectralPlane>(query(l), { signal: abort.signal }),
            );
          if (!abort.signal.aborted) {
            setRgbPlanes(p);
            setPlane(p[0]);
          }
        } else {
          const p = await json<SpectralPlane>(query(layer), {
            signal: abort.signal,
          });
          if (!abort.signal.aborted) setPlane(p);
        }
      } catch (e) {
        if (!abort.signal.aborted) {
          setError(String(e));
          setPlaying(false);
        }
      } finally {
        if (!abort.signal.aborted) setLoading(false);
      }
    };
    void load();
    const params = new URLSearchParams({
      view: "wavelengths",
      wave_ra: String(center[0]),
      wave_dec: String(center[1]),
      wave_fov: String(fov),
      layer: String(layer),
    });
    if (rgb) params.set("rgb", colors.join(","));
    history.replaceState(null, "", `/?${params}`);
    return () => abort.abort();
  }, [center, fov, layer, rgb, colors, retry]);
  useEffect(() => {
    if (!playing || loading || !plane || rgb) return;
    const timer = setTimeout(
      () =>
        setLayer((l) => {
          let next = (l + 1) % 102;
          while (metadata?.channels[next].blank) next = (next + 1) % 102;
          return next;
        }),
      1000,
    );
    return () => clearTimeout(timer);
  }, [playing, loading, plane, rgb, metadata]);
  useEffect(() => {
    if (!plane || !canvas.current) return;
    const ctx = canvas.current.getContext("2d")!;
    const size = plane.shape[0];
    canvas.current.width = size;
    canvas.current.height = size;
    const image = ctx.createImageData(size, size);
    const scales = (rgb ? rgbPlanes : [plane]).map((p) => {
      const valid = p.brightness
        .flat()
        .filter((v): v is number => v !== null)
        .sort((a, b) => a - b);
      return [
        valid[Math.floor(valid.length * 0.01)] || 0,
        valid[Math.floor(valid.length * 0.995)] || 1,
      ];
    });
    for (let y = 0; y < size; y++)
      for (let x = 0; x < size; x++) {
        const offset = 4 * ((size - 1 - y) * size + x);
        for (let c = 0; c < 3; c++) {
          const p = rgb ? rgbPlanes[c] : plane;
          const v = p?.brightness[y][x];
          const [lo, hi] = scales[rgb ? c : 0] || [0, 1];
          image.data[offset + c] =
            v === null || v === undefined
              ? 10
              : Math.round(
                  (255 *
                    Math.asinh(
                      10 * Math.max(0, Math.min(1, (v - lo) / (hi - lo || 1))),
                    )) /
                    Math.asinh(10),
                );
        }
        image.data[offset + 3] = 255;
      }
    ctx.putImageData(image, 0, 0);
  }, [plane, rgb, rgbPlanes]);
  const channel = metadata?.channels[layer];
  const choose = (l: number) => {
    setPlaying(false);
    setRgb(false);
    setLayer(l);
    setSelected(null);
  };
  const inspector =
    selected && plane
      ? {
          x: selected[0],
          y: selected[1],
          value: plane.brightness[selected[1]][selected[0]],
          hits: plane.hits[selected[1]][selected[0]],
          flags: plane.flags[selected[1]][selected[0]],
        }
      : null;
  return (
    <div className="spectral-workspace">
      <header>
        <Brand />
        <div className="mode-switch">
          <button aria-current="page">Explore wavelengths</button>
          <button onClick={onTime}>Compare time</button>
        </div>
        <span className="badge">DR1 · survey combined</span>
      </header>
      <div className="spectral-layout">
        <aside className="spectral-controls">
          <p className="eyebrow">What does infrared light reveal?</p>
          <h1>See the sky in a different light.</h1>
          <p>
            Move through real SPHEREx wavelengths. These mosaics combine
            observations across time.
          </p>
          <NameLookup onResolve={result=>{setCenter(result.center_deg);setPlaying(false);setSelected(null);}}/>
          <label>
            Start with a field
            <select
              aria-label="Spectral example"
              onChange={(e) => {
                const c = JSON.parse(e.target.value);
                setCenter(c);
                setPlaying(false);
                setSelected(null);
              }}
              defaultValue="[60.8109955,51.3404038]"
            >
              <option value="[60.8109955,51.3404038]">
                Infrared nebula · official tutorial
              </option>
              <option value="[210.80227,54.34895]">M101 · spiral galaxy</option>
              <option value="[83.82208,-5.39111]">Orion nebula</option>
            </select>
          </label>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const data = new FormData(e.currentTarget);
              setCenter([Number(data.get("ra")), Number(data.get("dec"))]);
              setFov(Number(data.get("fov")));
              setPlaying(false);
            }}
            key={center.join(",")}
          >
            <label>
              Right ascension · degrees
              <input
                name="ra"
                type="number"
                step="any"
                min="0"
                max="360"
                defaultValue={center[0]}
                required
              />
            </label>
            <label>
              Declination · degrees
              <input
                name="dec"
                type="number"
                step="any"
                min="-90"
                max="90"
                defaultValue={center[1]}
                required
              />
            </label>
            <label>
              Field size · arcminutes
              <input
                name="fov"
                type="number"
                min="1"
                max="120"
                defaultValue={fov}
                required
              />
            </label>
            <button type="submit">Explore field</button>
          </form>
          <label>
            Detector group
            <select
              aria-label="Detector group"
              value={channel?.detector || 1}
              onChange={(e) => choose((Number(e.target.value) - 1) * 17)}
            >
              {[1, 2, 3, 4, 5, 6].map((d) => (
                <option key={d} value={d}>
                  Detector {d}
                </option>
              ))}
            </select>
          </label>
          <details>
            <summary>Build a false-color image</summary>
            <p>
              Assign a wavelength to each display color. Colors are
              independently stretched; this is a visualization, not calibrated
              broadband photometry.
            </p>
            {["Red", "Green", "Blue"].map((name, c) => (
              <label key={name}>
                {name}
                <select
                  aria-label={`${name} channel`}
                  value={colors[c]}
                  onChange={(e) => {
                    setColors((old) =>
                      old.map((v, i) => (i === c ? Number(e.target.value) : v)),
                    );
                    setPlaying(false);
                  }}
                >
                  {metadata?.channels
                    .filter((s) => !s.blank)
                    .map((s) => (
                      <option key={s.index} value={s.index}>
                        {s.wavelength_um.toFixed(3)} µm · D{s.detector}
                      </option>
                    ))}
                </select>
              </label>
            ))}
            <label>
              <input
                type="checkbox"
                checked={rgb}
                onChange={(e) => {
                  setRgb(e.target.checked);
                  setPlaying(false);
                }}
              />{" "}
              Show false color
            </label>
          </details>
        </aside>
        <main className="spectral-main">
          <div className="spectral-heading">
            <div>
              <p className="eyebrow">
                {rgb
                  ? "False-color composite"
                  : "Wavelength exploration · not time playback"}
              </p>
              <h2>
                {rgb
                  ? "Three wavelengths, one field"
                  : channel
                    ? `${channel.wavelength_um.toFixed(3)} µm`
                    : "Loading channels…"}
              </h2>
              <p>
                {channel && !rgb
                  ? `Detector ${channel.detector} · channel ${channel.channel} · width ${channel.bandwidth_um.toFixed(3)} µm`
                  : "Red, green and blue are user-selected spectral samples."}
              </p>
            </div>
            <span className="badge">Visualization only</span>
          </div>
          <div className="spectral-image" aria-busy={loading}>
            {plane ? (
              <canvas
                ref={canvas}
                aria-label="SPHEREx spectral sky image; press Enter to inspect center"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter") setSelected([80, 80]);
                }}
                onClick={(e) => {
                  const r = e.currentTarget.getBoundingClientRect();
                  const n = plane.shape[0];
                  setSelected([
                    Math.min(
                      n - 1,
                      Math.max(
                        0,
                        Math.floor(((e.clientX - r.left) / r.width) * n),
                      ),
                    ),
                    Math.min(
                      n - 1,
                      Math.max(
                        0,
                        n -
                          1 -
                          Math.floor(((e.clientY - r.top) / r.height) * n),
                      ),
                    ),
                  ]);
                }}
              />
            ) : (
              <div role="status">
                {loading
                  ? "Reading a bounded region of the infrared sky…"
                  : error
                    ? "Image unavailable"
                    : "Choose a wavelength"}
              </div>
            )}
          </div>
          {error && (
            <p role="alert">
              {error}{" "}
              <button onClick={() => setRetry((x) => x + 1)}>Retry</button>
            </p>
          )}
          {channel?.blank && !rgb && (
            <p className="warning">
              This dichroic channel is blank in the official product. Choose a
              neighboring channel.
            </p>
          )}
          <div className="wavelength-dock">
            <label>
              Wavelength channel · {layer + 1} of 102
              <input
                aria-label="Wavelength channel"
                type="range"
                min="0"
                max="101"
                value={layer}
                onChange={(e) => choose(Number(e.target.value))}
                disabled={rgb}
              />
            </label>
            <div className="wave-actions">
              <button
                onClick={() => choose(Math.max(0, layer - 1))}
                disabled={rgb || layer === 0}
              >
                Previous wavelength
              </button>
              <button
                onClick={() => setPlaying((p) => !p)}
                disabled={rgb || !!error}
              >
                {playing ? "Pause wavelengths" : "Play wavelengths"}
              </button>
              <button
                onClick={() => choose(Math.min(101, layer + 1))}
                disabled={rgb || layer === 101}
              >
                Next wavelength
              </button>
            </div>
            <p>
              Appearance can change with wavelength. This does not show change
              over time. Playback skips the two blank channels.
            </p>
          </div>
        </main>
        <aside className="spectral-inspector">
          <h2>What am I seeing?</h2>
          <p>
            {plane
              ? `${(100 * plane.coverage_fraction).toFixed(1)}% of this field has data in the selected channel.`
              : "The image will appear when retrieval finishes."}
          </p>
          <p>
            The image is north-up, east-left. Click a pixel or focus the image
            and press Enter.
          </p>
          {inspector && (
            <dl>
              <dt>Surface brightness</dt>
              <dd>
                {inspector.value === null
                  ? "No data"
                  : `${inspector.value.toFixed(5)} MJy/sr`}
              </dd>
              <dt>Contributing input pixels</dt>
              <dd>{inspector.hits}</dd>
              <dt>Propagated flags</dt>
              <dd>{inspector.flags} (bitwise OR)</dd>
            </dl>
          )}
          <details>
            <summary>Dates, data and limitations</summary>
            <p>
              This is a survey-combined visualization. A brightness trace here
              is not a validated source spectrum. No per-channel error estimates
              are supplied.
            </p>
            {plane?.sources.map((s) => (
              <p key={s.url}>
                <a href={s.url}>Native FITS cube</a>
                <br />
                Contributing interval: MJD {s.mjd_start.toFixed(3)}–
                {s.mjd_end.toFixed(3)}
              </p>
            ))}
            <a href={metadata?.properties_url}>Official metadata</a>
            <p>{metadata?.credits}</p>
          </details>
          <button
            disabled={!plane}
            onClick={() =>
              save("vantage-spectral-provenance.json", {
                plane,
                rgb,
                color_channels: rgb ? colors : null,
                display:
                  "Independent percentile/asinh stretch; visualization only",
                metadata,
              })
            }
          >
            Export view & provenance
          </button>
          <button
            disabled={!plane}
            onClick={() => {
              const out = document.createElement("canvas");
              out.width = 720;
              out.height = 840;
              const ctx = out.getContext("2d")!;
              ctx.fillStyle = "#090d12";
              ctx.fillRect(0, 0, 720, 840);
              ctx.imageSmoothingEnabled = false;
              ctx.drawImage(canvas.current!, 0, 0, 720, 720);
              ctx.fillStyle = "white";
              ctx.font = "16px sans-serif";
              ctx.fillText(
                `Vantage · SPHEREx DR1 · ${rgb ? "false color" : `${plane!.channel.wavelength_um.toFixed(3)} µm`}`,
                20,
                748,
              );
              ctx.font = "12px monospace";
              ctx.fillText(
                `ICRS ${center.join(", ")} · ${fov} arcmin · survey combined`,
                20,
                772,
              );
              ctx.fillText(
                rgb
                  ? `R/G/B layers: ${colors.join("/")} · independent display stretches`
                  : "Visualization only · not a time sequence or source spectrum",
                20,
                793,
              );
              ctx.fillText(
                "NASA/SPHEREx · Caltech/IPAC/IRSA · export JSON for full provenance",
                20,
                817,
              );
              const a = document.createElement("a");
              a.href = out.toDataURL();
              a.download = "vantage-wavelength.png";
              a.click();
            }}
          >
            Export image
          </button>
          <button
            onClick={() =>
              navigator.clipboard
                .writeText(location.href)
                .then(() => setStatus("View link copied."))
                .catch(() =>
                  setStatus("Copy this page URL from your address bar."),
                )
            }
          >
            Copy wavelength link
          </button>
          <p role="status">{status}</p>
        </aside>
      </div>
    </div>
  );
}
