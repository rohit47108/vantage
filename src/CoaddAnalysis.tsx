import { useEffect, useRef, useState } from "react";
import { json, readResponse } from "./api";
import type { Sequence } from "./types";
import "./analysis.css";

interface Coadd {
  id: string;
  name: string;
  shape: number[];
  brightness: (number | null)[][];
  variance: (number | null)[][];
  mask: number[][];
  contributions: number[][];
  joint_support_fraction: number;
  mjd_interval: number[];
  limitations: string[];
  response_description: string;
  uncertainty_method: string;
  sequence_id: string;
}
interface Job {
  job_id: string;
  state: string;
  result_id: string | null;
  error: string | null;
}

function ProductImage({ product }: { product: Coadd }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const c = ref.current!;
    const size = product.shape[0];
    c.width = size;
    c.height = size;
    const ctx = c.getContext("2d")!;
    const values = product.brightness
      .flat()
      .filter((v): v is number => v !== null)
      .sort((a, b) => a - b);
    const lo = values[Math.floor(values.length * 0.02)] || 0;
    const hi = values[Math.floor(values.length * 0.99)] || 1;
    const pixels = ctx.createImageData(size, size);
    for (let y = 0; y < size; y++)
      for (let x = 0; x < size; x++) {
        const i = 4 * ((size - y - 1) * size + x);
        const value = product.brightness[y][x];
        const g =
          value === null
            ? 12
            : Math.round(
                (255 *
                  Math.asinh(
                    8 * Math.max(0, Math.min(1, (value - lo) / (hi - lo || 1))),
                  )) /
                  Math.asinh(8),
              );
        pixels.data.set([g, g, g, 255], i);
      }
    ctx.putImageData(pixels, 0, 0);
  }, [product]);
  return (
    <canvas
      ref={ref}
      className="product-image"
      role="img"
      aria-label="Narrowband coadd. Black regions are excluded by spectral, coverage or quality checks."
    />
  );
}

export function CoaddAnalysis({
  sequence,
  initialProduct,
  onClose,
  standalone = false,
}: {
  sequence?: Sequence;
  initialProduct?: string;
  onClose: () => void;
  standalone?: boolean;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [selected, setSelected] = useState<number[]>(
    sequence ? sequence.frames.map((_, i) => i) : [],
  );
  const [fov, setFov] = useState(3);
  const [job, setJob] = useState<Job | null>(() => {
    try {
      const previous = JSON.parse(
        localStorage.getItem("vantage-active-coadd") || "null",
      );
      if (
        previous?.sequence_id === sequence?.id &&
        /^[a-f0-9]{32}$/.test(previous?.job_id)
      )
        return {
          job_id: previous.job_id,
          state: "queued",
          result_id: null,
          error: null,
        };
    } catch {
      /* A malformed local bookmark does not prevent a new analysis. */
    }
    return null;
  });
  const [product, setProduct] = useState<Coadd | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [submitting, setSubmitting] = useState(false);
  useEffect(() => {
    if (standalone) return;
    const previous = document.activeElement as HTMLElement;
    dialog.current?.showModal();
    return () => previous?.focus();
  }, []);
  useEffect(() => {
    if (!initialProduct) return;
    const abort = new AbortController();
    json<Coadd>("/v1/products/" + initialProduct, { signal: abort.signal })
      .then(setProduct)
      .catch((e) => {
        if (!abort.signal.aborted) setError(String(e));
      });
    return () => abort.abort();
  }, [initialProduct]);
  useEffect(() => {
    if (!job || ["complete", "failed", "cancelled"].includes(job.state)) return;
    const abort = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const current = await json<Job>("/v1/analysis/jobs/" + job.job_id, {
          signal: abort.signal,
        });
        if (abort.signal.aborted) return;
        setError("");
        if (current.state === "complete" && current.result_id) {
          const result = await json<Coadd>(
            "/v1/products/" + current.result_id,
            { signal: abort.signal },
          );
          if (!abort.signal.aborted) {
            setProduct(result);
            setJob(current);
          }
          return;
        }
        if (current.state === "failed" || current.state === "cancelled") {
          setJob(current);
          setError(current.error || "Analysis cancelled.");
          return;
        }
        if (current.state !== job.state) setJob(current);
        timer = setTimeout(poll, 800);
      } catch (e) {
        if (!abort.signal.aborted) {
          setError("Status temporarily unavailable. Retrying the same job.");
          timer = setTimeout(poll, 2500);
        }
      }
    };
    void poll();
    return () => {
      abort.abort();
      clearTimeout(timer);
    };
  }, [job?.job_id, job?.state]);
  async function submit() {
    if (!sequence) return;
    setSubmitting(true);
    setError("");
    setProduct(null);
    try {
      const response = await readResponse(
        await fetch("/v1/coadds", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            sequence_id: sequence.id,
            frame_indices: selected,
            fov_arcmin: fov,
          }),
        }),
      );
      setJob({
        job_id: response.job_id,
        state: "queued",
        result_id: null,
        error: null,
      });
      try {
        localStorage.setItem(
          "vantage-active-coadd",
          JSON.stringify({ job_id: response.job_id, sequence_id: sequence.id }),
        );
      } catch {
        /* Storage can be unavailable in private/embedded browsing. */
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setSubmitting(false);
    }
  }
  async function cancel() {
    if (!job) return;
    try {
      const response = await json<{ state: string }>(
        "/v1/analysis/jobs/" + job.job_id,
        { method: "DELETE" },
      );
      setJob({ ...job, state: response.state });
    } catch (e) {
      setError(String(e));
    }
  }
  const busy =
    submitting ||
    !!(job && !["complete", "failed", "cancelled"].includes(job.state));
  const contents = (
    <div className="analysis-body">
      <div className="analysis-title">
        <div>
          <p className="eyebrow">Combine independent observations</p>
          <h1>{product ? product.name : "Stack observations"}</h1>
        </div>
        <button onClick={onClose} aria-label="Close analysis">
          Close
        </button>
      </div>
      <p>
        Average nearby spectral samples to inspect a quieter view. Each pixel
        must pass coverage, quality and wavelength checks in every selected
        observation.
      </p>
      {sequence && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void submit();
          }}
        >
          <fieldset disabled={busy}>
            <legend>Contributing observations · {sequence.name}</legend>
            {sequence.frames.map((f, i) => (
              <label
                key={`${f.obs_id}/${f.detector}`}
                className="analysis-frame"
              >
                <input
                  type="checkbox"
                  checked={selected.includes(i)}
                  onChange={(e) =>
                    setSelected((old) =>
                      e.target.checked
                        ? [...old, i]
                        : old.filter((v) => v !== i),
                    )
                  }
                />
                <span>
                  {f.utc_mid}
                  <small>
                    {f.wavelength_um?.toFixed(5)} µm · detector {f.detector} ·{" "}
                    {f.obs_id}
                  </small>
                </span>
              </label>
            ))}
            <label>
              Region size · arcminutes
              <input
                type="number"
                min="0.5"
                max="3.3"
                step="0.1"
                value={fov}
                onChange={(e) => setFov(Number(e.target.value))}
              />
            </label>
            <button
              className="primary"
              type="submit"
              disabled={selected.length < 2}
            >
              Build weighted coadd
            </button>
          </fieldset>
        </form>
      )}
      {busy && (
        <p role="status">
          {job?.state === "queued"
            ? "Queued for processing…"
            : "Reading native measurements and aligning their pixel footprints…"}{" "}
          <button onClick={() => void cancel()} disabled={!job}>
            Cancel job
          </button>
        </p>
      )}
      {error && (
        <p role="alert" className="warning">
          {error}
        </p>
      )}
      {product && (
        <section aria-label="Coadd result">
          <div className="coadd-result">
            <ProductImage product={product} />
            <div>
              <h2>Only the supported region is shown</h2>
              <p>
                <strong>
                  {(100 * product.joint_support_fraction).toFixed(1)}%
                </strong>{" "}
                of the requested field passes every check. Dark regions are
                excluded, not zero brightness.
              </p>
              <p>
                This averages light measured on different dates. Brightness is
                shown in MJy/sr, a measure of light per area of sky.
              </p>
              <p>
                Contributing interval: MJD {product.mjd_interval[0].toFixed(3)}–
                {product.mjd_interval[1].toFixed(3)}.
              </p>
              <p>
                The result does not by itself prove a change. Moving sources can
                blur when observations are stacked on a fixed sky grid.
              </p>
            </div>
          </div>
          <div className="analysis-actions">
            <a
              className="action-link"
              href={`/v1/products/${product.id}/science.fits`}
            >
              Download science FITS
            </a>
            <button
              onClick={() => {
                const u = URL.createObjectURL(
                  new Blob([JSON.stringify(product, null, 2)], {
                    type: "application/json",
                  }),
                );
                const a = document.createElement("a");
                a.href = u;
                a.download = "vantage-coadd-provenance.json";
                a.click();
                setTimeout(() => URL.revokeObjectURL(u), 1000);
              }}
            >
              Export coadd provenance
            </button>
            <button
              onClick={() =>
                navigator.clipboard
                  .writeText(
                    `${location.origin}/?view=coadd&product=${product.id}`,
                  )
                  .then(() => setNotice("Analysis link copied."))
                  .catch(() =>
                    setNotice(
                      `Share ${location.origin}/?view=coadd&product=${product.id}`,
                    ),
                  )
              }
            >
              Copy analysis link
            </button>
            <a
              className="action-link"
              href={`/?view=coadd&product=${product.id}`}
            >
              Open saved result
            </a>
          </div>
          <p role="status">{notice}</p>
          <details>
            <summary>Method, uncertainty and limits</summary>
            <p>{product.response_description}</p>
            <p>{product.uncertainty_method}</p>
            <ul>
              {product.limitations.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
            <p>
              The science FITS includes IMAGE, VARIANCE, MASK, NCONTRIB, FLAGS,
              CWAVE, input wavelength/widths, weights and sparse covariance.
              Masked variances are missing, not zero uncertainty.
            </p>
          </details>
        </section>
      )}
      {!product && !busy && !sequence && !error && (
        <p role="status">Loading saved analysis…</p>
      )}
    </div>
  );
  return standalone ? (
    <main className="standalone-analysis">{contents}</main>
  ) : (
    <dialog
      className="analysis-dialog"
      ref={dialog}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
    >
      {contents}
    </dialog>
  );
}
