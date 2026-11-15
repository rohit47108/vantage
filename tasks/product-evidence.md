# Requirement-to-evidence matrix

Updated November 14, 2026. Status is for the NEW complete-product goal. Historical test reports prove only their tested demo release. F=functionality, S=scientific validation, P=public deployment. Pending is incomplete, including earlier claims not yet reverified. The complete attached specification remains authoritative, including every subitem.

| ID / specification scope | Required proof | F | S | P |
|---|---|---|---|---|
| Baseline / §3 | Preserve five targets, Ceres, M101, tracked comet, coordinate and player tests; original research; branding | historical baseline | historical baseline | historical preview |
| GitHub request | Existing repo updated, accurate README, existing MIT license retained | license merged; push pending | n/a | pending |
| A / find field | Name/coordinate resolution, search/context manipulation, URL config, empty/failure recovery | pending | pending | pending |
| B / time | Epoch exposures/groups/windows; playback gaps; side-by-side/swipe; both inspectors; shared/independent stretch; masks; predictions; exact share/export | partial baseline | partial baseline | pending |
| C / wavelength | All 102 metadata-driven samples, six detectors, blank channels, linked chart/image, wavelength playback, false color, exports | in progress | live properties tested | pending |
| D / stacks | Real eligible weighted/robust coadd, broad visualization, counts, response/time/units/rejections/uncertainty; motion-compensated comparison | pending | pending | pending |
| E / difference | Authentic eligible pair, PSF/registration/background/scaling, covariance and fitted errors, signed image, FITS/mask/uncertainty export; invalid pair guidance | pending | pending | pending |
| F / source spectra | Asynchronous actual extraction; aperture/background/PSF; units/errors/flags/time, missing/bins/limits; chart linkage; CSV/ECSV/plot | pending | pending | pending |
| G / Gaia + WISE | Real aligned optical/IR context, proper motions and reference epochs, candidate matches, opacity/select controls, attribution, failure | pending | pending | pending |
| §7 geometry/wavelength | Primary TAN-SIP, cutout origins, eager versioned CWAVE/CBAND; response-level gates | baseline visual only | numerical pending | pending |
| §7 operators | A C Aᵀ, masks through interpolation/convolution, independent weighted variance; shared covariance | pending | pending | pending |
| §7 PSF/registration | Release PSF conventions/normalization/orientation, reference residuals, crowding/background/ZODI, solid angle | pending | pending | pending |
| §8 benchmarks | Successful authentic coadd/difference/spectrum and survey alignment; references + predeclared tolerances; injection and negative tests | pending | pending | pending |
| §9 UX | Cohesive three modes, first-visit example/search, reversible analysis, stale guards, clear results and next actions; mobile/tablet | pending | n/a | pending |
| §10 architecture | Clear modules, typed result/job contracts, canonical scientific identities, calibrated provenance, durable bounded queue/storage | partial baseline | pending | pending |
| §11 releases | Registry capabilities, canary processing, retirement/dedup, safe promotion, affected-cache invalidation, rollback, refresh failures | pending | pending | pending |
| §11 broad sky | Multi-resolution context, real region selection, work/transfer estimates, progressive bounded tiles, cancellation, wide motion benchmark | pending | pending | pending |
| §12 share/embed | Coordinates + immutable products + validated views, real compact iframe, safe messaging if offered, accessible labels | partial baseline | pending | pending |
| §12 export/save | PNG, FITS with WCS/extensions, CSV/ECSV/plots, JSON and analysis summary, local investigations/notes/import/export, restart persistence | partial baseline | pending | pending |
| §13 assistance | Valid combination suggestions; specific block reasons/alternative example; smear/artifact/coverage/channel guidance | pending | pending | pending |
| §13 candidate review | Conditional on validated residual pipeline; justify before enabling, no discovery/confidence claims | not enabled | pending decision after E | n/a |
| §14 infrastructure | Durable Python + store, queue recovery, health/readiness, logs/resource bounds/rate limits/circuit breaker, locks, backup/restore/rollback | pending | pending | laptop tunnel insufficient |
| §14 security | Allowlist/redirect/path/size/decompression/import guards; secrets exclusion; independent prepared delivery | partial baseline | n/a | pending |
| §15 accessibility | WCAG 2.2 AA meaningful workflows, keyboard field/chart selection, focus, tables/text/noncolor cues, touch/reduced-motion/paused/flash-safe/live updates | partial baseline | n/a | pending |
| §15 performance | First prepared frame <3s/swaps <50ms; spectral/context transfer/memory/cancellation/cache measured cold/warm | historical demo only | correctness preserved | pending |
| §16 tests 1–6 | Existing targets; QR2/3/DR1; HiPS indexing/blanks; orientation/catalog; spectral compatibility; masks/unknowns | partial baseline | pending new run | pending |
| §16 tests 7–14 | Coadd variance/motion, PSF, registration/background, difference recovery/distribution, shared covariance, spectra/solid-angle/corrections/missing/time | pending | pending | pending |
| §16 tests 15–22 | Surveys; release rollback; identity/persistence; stale/cancel/restart; URL/embed; responsive/a11y; outage; public storage path | partial baseline | pending | pending |
| §17 communication | Current challenge/judging verification, IRSA workflow comparison; actual six-part demo, storyboard/submission materials; team/AI/limitations/architecture | pending | pending | pending |
| §17 team guide | Understand your project: data flow, valid claims, pitfalls and each advanced measurement in plain language | pending | pending | pending |
| §19 final audit | Source/locks, commands, authentic provenance, URLs/screenshots, per-requirement actual acceptance/science/performance/reliability/docs/demo | pending | pending | pending |

No row with pending evidence may be reported complete. Current goal remains active across slices. A hosting dependency cannot justify stopping independent science, UX, tests or documentation work.
