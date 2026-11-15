# Vantage implementation status

## New complete-product goal — active

The later complete-product specification supersedes the demo scope described below. The application is PARTIALLY COMPLETE for that goal. See tasks/product-evidence.md; coadds, subtraction, source extraction, Gaia/WISE, embeds/investigations, release promotion and durable hosting still require implementation/validation.

The new spectral workspace runs at /?view=wavelengths. Verified locally and publicly: 102-channel metadata, six detector groups, two blank layers, actual range-read native brightness/hits/flags, false color, pixel inspection, view restore, provenance and image export. Fourteen scientific/API tests pass, including six new spectral tests. All thirteen browser tests pass locally and on the public preview, including two new real-data spectral tests and automated WCAG A/AA checks in the tested desktop state. Reports: artifacts/product-local-browser.json and artifacts/product-public-browser.json.

Current verified preview: https://vantage-spherex-7pcgn4j98-rohit-singhs-projects-48f82479.vercel.app . Local complete service: http://127.0.0.1:8000/ . API exec session 62536 replaced the earlier API session. Temporary tunnel session 31231 remains in use. This is not durable cloud backend hosting.

Independent native range sampling and the north-up visual sampler agree exactly at the official tutorial coordinate for channel 62: 12.00507926940918 MJy/sr. This validates that context sample, not source photometry. Research/updates/2026-11-14 retains current cube properties and native schema evidence.

GitHub origin is https://github.com/rohit47108/vantage.git. Its original MIT license and history were merged. Source and authentic benchmark fixtures are published to main; downloaded upstream PDFs/HTML/text documentation remain local references. Current scoped Vercel CLI inspection returned no installed integration configurations; durable database/storage and Python hosting remain to be resolved.

## Earlier temporal demonstration

Updated November 14, 2026. Required demonstration workflows are complete at the documented scientific scope. Public acceptance passed all eleven browser tests, including real date and precision-wavelength selection.

## Public demo

Verified public preview: https://vantage-spherex-grpoty722-rohit-singhs-projects-48f82479.vercel.app . The older production alias is not the final tested release; use this preview.

The full local application is http://127.0.0.1:8000/. Vite development mode is http://127.0.0.1:5173/.

## Running processes

- Python API and complete local application use exec session 56256 on port 8000.
- Cloudflare tunnel uses exec session 31231 and origin https://dependent-singing-burning-int.trycloudflare.com.
- Vite development server uses exec session 39702.
- The browser CLI session is vantage.

The public static frontend is on Vercel. Live processing currently depends on this computer and the temporary tunnel. A persistent public Python host has not been provisioned. Prepared targets remain available if the backend stops. The first Vercel deployment was automatically assigned to production by the CLI. Subsequent releases are public preview deployments. Access settings were changed only for the new Vantage project to permit public viewing.

## Completed behavior and evidence

- Eight authentic prepared examples, including the five required three-frame targets and Ceres/M101 controls.
- Fixed TAN-grid processing, exact source/calibration hashes, eager precision maps, unknown/defective-flag support, source bit preservation and gated numerical products.
- DR1/QR3 coordinate search, persistent jobs, typed inputs, canonical deduplication, safe retry/cancellation, cached metadata and native IBE/S3 retrieval.
- Exact date and precision-wavelength filtering was verified against a real single-observation result in artifacts/precision-goal-job.json.
- Inspection, A/B comparison, overlays, camera/stretch, immutable URLs, exports and failed/slow-request handling.
- Eight scientific/API tests pass in the clean environment. Source/hash/grid checks, actual QR2/QR3 flag representations and real DR1 text-detector behavior are covered.
- Public browser reports, screenshots and measured timings are under artifacts. All eleven public browser tests pass with no skipped or flaky tests. The final run measured a prepared first frame of 592 ms and decoded swaps of 1.7–4.1 ms in fresh-context headless Chrome on Windows without mobile throttling. These are observed timings, not service guarantees.
- A physical backend shutdown produced public health HTTP 502 and static catalog HTTP 200. All eight prepared examples still opened and played.
- Actual S3 fallback data matched IBE over 3,473 common pixels, with equal flags/wavelengths and brightness differences below 1e-6 MJy/sr.
- Runtime requirement audit reports no known vulnerabilities. npm audit reports zero vulnerabilities. pip check reports no broken requirements.
- scripts/launch.ps1 built and served the full app on port 8002. The same service now runs on 8000 and was opened in Chrome for prepared playback.

## Delivered documentation

README.md contains setup, preprocessing, tests and deployment staging. DEMO.md has 60-second and three-minute walkthroughs. SUBMISSION_DRAFT.md contains project/data/AI text and current competition-source limits. REVIEW.md records fixes and scope. ACCEPTANCE.md maps requirements to evidence.

## Remaining scope

Quantitative photometry, precision astrometry, validated differences/significance, survey overlays and live spectra remain optional and gated. The final competition-guide refresh failed certificate validation or web retrieval. Submission-format limits and judging guidance remain unverified. Final competition submission belongs to the user.
