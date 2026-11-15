# Implementation review

November 15, latest general-source slice: reviewed source-discovery/native-job boundaries, immutable calibration snapshots, physical observation/detector identities, result/sample links, error/cancellation and resubmission behavior, native stamp checksums, archive allowlists, input bounds and single-instance cache publication. Fixed saved-product options carrying stale observation indices, motion values dropped from links, reference loading that could overwrite edits, missing cancellation announcement, stale result URLs and invalid fallback-cache records. All 69 scientific/API tests, final 27 local browser cases, type/build checks and runtime npm audit pass. The initial 25/26 browser run and isolated wavelength rerun remain separately recorded. No implementation fix is claimed for that transient loading failure. Controlled native queue recovery after a real test-service restart reproduces the exact immutable six-detector result. Public acceptance follows separately.

The declared limits remain material: conditional statistical errors; no source deblending, complete channel spectrum, validated binning/limits or simultaneous SED; query-specific live archive failures; source-cache quota covers binary publication in one process only; result-store budgets, admission/rate limiting and durable hosting remain unfinished. This slice improves the complete-product goal without marking it complete. See native-extraction/LIVE_SOURCE_WORKFLOW.md under research/updates/2026-11-15.

Public follow-up: the P330E date-bounded query recovered and returned 147 candidates without overflow across the four requested collections. Its narrower cone correctly excludes the uncovered native reference used in the earlier 150-candidate broad-snapshot test. The first public run passed 26/27 and exposed this test-data assumption. The browser selection now uses the six covered passing exposures plus the authentic covered D2 poor-fit input; it requires the unchanged residual-score rejection and does not expand the search or weaken a numerical gate. All four updated source cases pass locally. Direct public extraction and all ten export/stamp checksums pass. Final public acceptance passes 27/27 without retries/skips/flaky cases in artifacts/native-workflow-browser-public-final.json. The actual public native/residual screenshots were visually inspected; branding and fit guidance remain legible. Functional application source remains 7b9fe84, with successful Ubuntu CI 43720565136. Only test selections/evidence/docs changed after that deployment; no app-code redeployment is required for those records.

Review covers correctness, readability, architecture, security and performance under the supplied specification.

## Corrected findings

- Normalize DR1 calibration detector strings before comparing with exposure headers. A regression exercises real DR1 files.
- Preserve frame, camera, stretch and layers on immutable loads. Fresh-browser restoration passes.
- Inspect the correct frame for either comparison canvas and label exported images accordingly.
- Give retries new job IDs while equivalent active requests deduplicate transactionally. Cancelled workers cannot update a replacement row.
- Invalidate support for unknown flags and retain their metadata. Preserve source bit 21.
- QR2/QR3 flag storage can be unsigned or signed integer data. Normalize to uint32 while preserving all 32 bits. Actual fixtures exercise both representations and spatial WCS roundtrips.
- Check wavelength goals against precision maps at the requested coordinate with a 20-header cap.
- Reserve space for the playback dock and keep mobile controls collapsible.
- Use a clean runtime and dependency lock after updating packages with advisories. The resolved runtime audit reports no known vulnerabilities.
- Continue observing the same active job while it runs. Failed assets preserve their requested identity and offer retry.

## Boundaries

The app supplies visual WCS alignment and support diagnostics. Quantitative differences, calibrated significance and precision astrometry remain gated. Comet thumbnails use distinct tracked grids. The public demo uses one Python instance, two bounded workers, SQLite and persistent disk through a temporary tunnel. A persistent hosted Python service remains an infrastructure task.

See ACCEPTANCE.md and artifacts for results. Automated accessibility checks complement keyboard and mobile tests and do not establish universal screen-reader conformance.
