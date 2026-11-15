# Vantage acceptance record

This section records the earlier temporal demonstration. It does not establish completion of the new analysis-product goal. Current full-scope acceptance is tracked separately in tasks/product-evidence.md.

Tested on Windows with Node 24.17, Python 3.13 and headless Chrome. The public deployment uses Vercel static delivery and a temporary tunnel to the local Python service. All eleven tests pass in the public report, `artifacts/browser-results.json`, with no skipped or flaky tests.

| Requirement | Evidence and result |
|---|---|
| Decimal/sexagesimal coordinates, RA wrap and invalid inputs | Scientific unit tests and real browser search pass, including the exact WISE 0855 input. |
| All five official sequences | Each opens three authentic, chronological frames. Browser tests exercise every named field and acquisition identity. |
| Fixed-grid processing | Scientific regression checks compare every frame grid, shape, hash and wavelength sample against supplied research evidence. |
| Ceres, M101 and comet controls | Ceres is a fixed-sky positional example with brightness analysis gated. M101 displays restricted support. Comet thumbnails explicitly use tracked grids. All open and step in browser tests. |
| Playback, stepping, scrubbing, speed and looping controls | Player starts paused. Browser tests exercise play/pause, previous/next, scrub and speed. Acquisition gaps remain distinct from display speed. Loop is an explicit user control. |
| Pan, zoom, shared stretch and reset | Shared camera state applies to both comparison canvases. URL restore verifies camera and selected overlays. |
| Pixel/source inspection | Pointer and keyboard inspection expose ICRS coordinates, calibrated brightness, local wavelength, flags and support. Comparison inspection uses the clicked frame. |
| Date and wavelength selection | Live endpoint evidence in `artifacts/precision-goal-job.json` verifies an exact UTC date, observation identity, precision wavelength tolerance and single-frame context status. A browser test exercises the same controls. |
| Arbitrary coverage and field of view | Real backend search and coordinate URL restore pass for RA 12.345, Dec -32.1, FOV 7 arcminutes. |
| Immutable sharing and provenance | A fresh browser opens the same sequence with camera/layers restored. JSON export retains sequence ID and scientific restrictions. Image export downloads a labeled PNG. |
| Restart persistence | Generated manifests survive API restarts and reopen through static URLs and the manifest endpoint. SQLite retains terminal jobs. Interrupted work gets an explicit retry state. |
| Stale and failed requests | Throttled frame requests cannot replace a newer selection. Failed assets identify the intended observation and date, pause playback and recover through retry. |
| Archive/backend failure | With Python physically stopped, the public health route returned 502 while catalog delivery returned 200. A separate browser run opened and played all eight static examples. See `artifacts/backend-outage.json` and `backend-outage-browser-results.json`. |
| S3 fallback | An injected IBE 503 triggers actual anonymous S3 reads. Comparison over 3,473 common pixels has maximum brightness difference below 1e-6 MJy/sr, equal flags and equal sampled wavelengths. See `artifacts/s3-fallback-verification.json`. |
| Accessibility | Keyboard inspection, native dialog focus/escape restoration, mobile layout and reduced-motion starting state pass. Automated WCAG A/AA checks found no violations in the tested desktop state. |
| Performance | Public fresh-context and decoded-swap measurements are in `artifacts/performance.json`. The tested environment has no mobile network throttling. |
| Dependencies | Build passes. Eight scientific/API tests pass in the clean environment. Runtime requirement audit reports no known vulnerabilities, and npm audit reports zero vulnerabilities. |
| Credits and licensing | NASA/IRSA acknowledgment text, applicable release DOIs, source/calibration hashes and limitations appear in manifests and Data & Methods. React license files are included under `public/licenses`. |
| Public and local launch | Public browser acceptance is recorded in the report. `scripts/launch.ps1 -Port 8002` built and served HTML, assets, share routes and API locally. The complete service normally runs on port 8000. |
| Documentation and project materials | README, DEMO, SUBMISSION_DRAFT, REVIEW and IMPLEMENTATION_STATUS describe tested behavior, launch, sources and limitations. |

## Material limits

The final public run measured a prepared first frame of 592 ms, with decoded frame swaps of 1.7–4.1 ms. The measurements used a fresh headless Chrome context on Windows, actual network access and no mobile throttling. CDN caches may have been warm. They do not establish a universal latency guarantee.

The public live backend depends on this computer and the temporary tunnel. A persistent hosted Python service has not been provisioned. Static examples remain available on Vercel.

Quantitative photometry, precision astrometry, PSF-matched differences, calibrated significance, external-survey overlays and spectral extraction remain outside the enabled scientific scope. Their required validation gates remain in place.

The official competition guide refresh failed through certificate validation or web fetch errors. Final 2026 submission format and judging rules remain unverified. The user retains final competition submission.
