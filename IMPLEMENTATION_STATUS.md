# Vantage implementation status

Updated November 14, 2026, 18:35 EST. Goal remains active. Deadline 23:59 EST.

## Verified progress

- React 19.3.1, Vite 8.3.8, TypeScript build passes. npm audit after updates reports zero vulnerabilities.
- Prepared preprocessing checks every supplied source checksum. Eight static manifests include the five required three-frame sequences, Ceres/M101 two-frame controls and separately tracked comet thumbnails.
- Shared TAN reprojection, eager calibration arrays, parent detector origins, named QR2/QR3 HDUs, finite/defect support propagation, joint spectral gate, shared asinh stretch and inspection maps are implemented in backend/science.py.
- Four offline regression tests pass, covering input conventions and invalid inputs, source bit preservation, prepared identities/assets/fixed grids, API bounds, and independently supplied per-target wavelength values.
- Actual Playwright browser smoke actions opened all eight targets, stepped a frame, inspected via keyboard Enter and opened a two-canvas A/B comparison. Screenshots artifacts/prepared-desktop.png, prepared-comparison.png and prepared-mobile.png are current partial-state evidence.
- Actual DR1 SIA cone returned five rows. Raw response artifacts/dr1-live-probe.vot. Current IRSA guide says DR1/QR3 replace QR2 search and QR2 direct files remain through February 2027.
- Backend offers coordinate parsing, discovery, persistent SQLite jobs, bounded workers, cancellation, immutable manifest lookup and static assets.

## Active process handles and next actions

Vite exec session 39702 serves http://127.0.0.1:5173/. Current API exec session 50451 serves http://127.0.0.1:8000/. Old API sessions 33601, 46781 and 12295 were stopped. CLI browser session is `vantage`, currently mobile viewport 390x844. Use `npx @playwright/cli -s=vantage snapshot` before interactions.

Job f93a3a042f5f1277304f75767cc58c4d594e44de18ef6a925753e0d3477fe506 was retried after the initial IBE HTTP503. It reached retrieval and then failed with a missing Path import in the new fallback/cache code. The import is fixed, the API was restarted with it and the terminal job was resubmitted successfully (HTTP 202). Poll GET /v1/jobs/{id} and inspect result/error. S3 fallback and bounded retry still require live verification.

## Outstanding required acceptance

- Complete live retrieval/generation and browser opening. Diagnose real upstream errors. Verify actual DR1/QR3 calibration/HDU differences and S3 fallback against the resulting file.
- Finish date and wavelength selection from live coverage. Current UI lets users choose detector and lists exposure dates/bounds; it does not yet let users filter dates or explicit wavelength selection.
- Fix coordinate URL boot workflow so it automatically searches/restores, and preserve exact frame/camera/display state in immutable sharing. Frame query restore is present; pan/zoom/stretch are not yet encoded.
- Complete job generation identity, retry/cancellation race review, caching/negative cache, safe failure detail and anonymous ownership. Current request hashes preserve field order rather than a fully canonical normalized request. Complete manifests are atomically published, but multi-process dedup is not established.
- Review absolute WCS/pixel conventions, unsigned flag schema, unknown bits, ZODI policy, source calibration fields for supporting controls, missing calibration/state edge cases and provenance. Current numerical products remain disabled.
- Inspect mobile screenshot. Left panel is in normal flow on narrow screens and needs sheet-style usability refinement. Desktop dock currently overlaps part of the image and view tools. Improve layout before final screenshots.
- Native or fully focus-managed methods dialog, focus restoration, reduced-motion player behavior, text measurement tables, image flash safety and keyboard full-flow tests remain incomplete.
- Measure cold load/swap performance. Test image/provenance downloads, sharing in fresh session, browser back/popstate, API restart, archive-offline fallback, failed/slow frames and stale results. Do not infer these from smoke checks.
- Read review and launch skills in their phases. Inspect authorized hosting tools and credentials. No public deployment attempted or verified yet. No infrastructure blocker established yet.
- Produce full acceptance checklist, tested production launch/configuration, final screenshots, 60-second/3-minute walkthrough, project copy/data/AI disclosure and precise optional-work list.

Historical research audit is unchanged and does not certify application acceptance. No competition submission was made.
