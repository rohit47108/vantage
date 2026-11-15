# Vantage implementation status

## New complete-product goal — active

The later complete-product specification supersedes the demo scope described below. The application is PARTIALLY COMPLETE for that goal. See tasks/product-evidence.md; remaining coadd methods, subtraction, source extraction, embeds/investigations, release promotion and durable hosting still require implementation/validation.

### Catalog context and name lookup — November 15

Gaia DR3 and AllWISE context are implemented through bounded IRSA Gator queries. Each catalog loads independently of the images and the other catalog. Source IDs remain strings, Gaia angular proper motion follows each frame's epoch/grid, and AllWISE positions retain their historical meaning. Visibility, opacity, marker/keyboard selection, exact layer/opacity links, candidate associations, image labels, full catalog/query/credit JSON exports and failure/retry states are functional. CDS Sesame follows the verified official IDIA mirror and supplies name-based coordinates in both workspaces. The user explicitly chose the restored circular logo and longer title on November 15; this supersedes the earlier branding request.

Thirty-four scientific/API tests pass, including ten survey tests. All twenty browser tests pass locally and publicly, including four new real-data survey/name tests. An independent analytic TAN projection plus Astropy angular transport agrees with the displayed M101/Barnard catalog pixels to at most 2.691e-7 pixels, against a predeclared 1e-4-pixel tolerance. This validates the stated coordinate model, not absolute centroid astrometry. Observer parallax/perspective acceleration remain omitted; WISE mean MJDs are approximate positional epochs. Gaia queries are visibly limited. See research/updates/2026-11-15/SOURCES.md and artifacts/survey-scientific-validation.json.

Current verified public preview: https://vantage-spherex-h5rr0ebgl-rohit-singhs-projects-48f82479.vercel.app . Source commit 0d95a51 is published to GitHub. Fresh Ubuntu CI run 43686276672 passed dependency installation, build, scientific/API tests, independent numerical validation and npm audit. Reports: artifacts/survey-local-browser.json, survey-public-browser.json, survey-github-ci.json and survey-public-release.json. Public JS/CSS/favicon bytes match the local build exactly; HTML comparison accounts explicitly for Vercel's appended preview-feedback script and trailing newline.

Local API and built application: http://127.0.0.1:8000/ (exec session 9168). The previous 8000/8003 instances were positively identified and replaced by one updated service. Cloudflare had invalidated the earlier quick tunnel: direct DNS failed, Vercel returned DNS_HOSTNAME_NOT_FOUND, and the live connector repeatedly reported Unauthorized: Tunnel not found. That specific remote rejection justified replacement. New tunnel session 69266 uses https://journal-increases-recent-hope.trycloudflare.com and forwards port 8000. Both direct and public health returned HTTP 200 after replacement, and all twenty public tests passed. This remains temporary/laptop dependent; it does not satisfy durable hosting. Earlier process IDs and preview reports below are historical checkpoints.

The refreshed public run measured a first prepared frame of 406.3 ms and completed decoded canvas updates of 1.1–2.4 ms in headless Chrome on Windows without mobile throttling. RAF observation latency is separately recorded; physical display timing and service-level guarantees are not claimed.

### Conditional coadd workflow

Current verified preview: https://vantage-spherex-l7w07dm2n-rohit-singhs-projects-48f82479.vercel.app . All sixteen public browser tests pass (no skipped/flaky tests), including actual M101 coadd submission, scientific FITS/provenance exports, saved-result restore, mobile invalid Ceres rejection and rapid target-change guards. Twenty-four scientific/API tests pass without skips. Artifacts/coadd-public-browser.json and coadd-unit-tests.txt retain results.

The service now exposes POST /v1/coadds, persistent analysis-job status/cancellation and immutable /v1/products/{id} manifests/FITS. Numerical jobs share the two bounded worker threads. Pending work resumed and produced an authentic result after an actual process restart; artifacts/product-restart-recovery.json records the controlled fault-injection test. Current API exec session is 43043 on port 8000; the existing temporary tunnel remains session 31231.

The new coadd is an explicitly response-mixed statistical weighted mean on a restricted region, not a completed precision-photometry or subtraction pipeline. M101 retains 105/1,024 pixels with the stronger central-wavelength/quality screen. Sparse covariance is exported, but unknown native covariance and common calibration systematics remain excluded. Robust estimators, motion compensation, full-response validation, PSF matching and absolute registration remain required. See research/updates/2026-11-14/NUMERICAL_METHODS.md.

Authentic DR1 D6 cutout and calibration fixtures are now retained with hashes in research/updates/2026-11-14/dr1-fixtures.json, removing the local-cache dependency from the DR1 regression. Original historical research manifests are unchanged. Runtime dependency audit found no known vulnerabilities, and npm audit reported zero. GitHub CI run 43666276712 succeeded on Ubuntu with Python 3.13 and Node 24, including fresh dependency installation, build, scientific/API tests, independent numerical validation and npm audit. This verifies a fresh Linux checkout in addition to local Windows results.

The new spectral workspace runs at /?view=wavelengths. Verified locally and publicly: 102-channel metadata, six detector groups, two blank layers, actual range-read native brightness/hits/flags, false color, pixel inspection, view restore, provenance and image export. Fourteen scientific/API tests pass, including six new spectral tests. All thirteen browser tests pass locally and on the public preview, including two new real-data spectral tests and automated WCAG A/AA checks in the tested desktop state. Reports: artifacts/product-local-browser.json and artifacts/product-public-browser.json.

Earlier spectral-only preview: https://vantage-spherex-7pcgn4j98-rohit-singhs-projects-48f82479.vercel.app . Local complete service: http://127.0.0.1:8000/ . This remains a laptop-backed temporary tunnel, not durable cloud backend hosting.

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
