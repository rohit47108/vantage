# Vantage implementation plan

Existing specification is CODEX_HANDOFF_PACKET.md and the attached master prompt. Started November 14 at 18:22 EST. Deadline 23:59 EST.

## Architecture

React/TypeScript/Vite and Canvas consume immutable JSON manifests and display maps. FastAPI performs bounded archive discovery and scientific processing. Prepared manifests/assets are static and survive backend outages. SQLite indexes live requests and jobs. Source FITS stay backend-only. Numerical brightness products remain disabled until every scientific gate is validated.

DR1 is now officially released. The November 12 access guide says to search DR1 and QR3. QR2 remains direct-download only through February 2027. Prepared QR2 examples retain exact provenance. Sources https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/ and https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_qr.html.

## Ordered slices

1. Prepared exploration. Verify all source hashes, reproject the five named sequences plus Ceres/M101 to fixed TAN grids, generate common stretch and support/inspection assets, render a paused player. Check independent calibration values and common-grid identities. Files backend/science.py, scripts/prepare.py, public/prepared, src.
2. Live coordinate workflow. Typed parsing, circumscribed discovery against DR1/QR3, actual visit/wavelength selection, bounded persistent jobs and source/calibration retrieval. Verify actual arbitrary search and generated sequence, errors and cancellation. Dependencies slice 1. Files backend/archive.py, backend/app.py, tests.
3. Inspection/comparison/share. Implement overlays, pan/zoom, A/B, coordinate readouts, provenance and image export, immutable restore and matching prepared fallback. Verify browser workflows and restart. Dependencies slices 1/2. Files src components and API.
4. Accessibility/visual review. Use actual desktop/mobile screenshots. Verify keyboard, reduced motion, loading and failed assets, stale selection and scientific controls. Record actual acceptance and measured timings. Dependencies slice 3.
5. Launch. Read shipping and deployment skills. Verify infrastructure, deploy authorized free configuration where possible, browser-test public URL. Record exact blockers and complete local launch/docs/demo materials regardless. Dependencies slice 4.

Checkpoints after every slice require its focused tests and a clean build. The user authorized autonomous execution of this specification, including routine decisions and deployment where available.
