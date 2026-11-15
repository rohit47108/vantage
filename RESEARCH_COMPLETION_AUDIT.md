# Vantage research completion audit

Audit scope covers the research and technical architecture, all 65 numbered requirements in the attachment, and the complete 2026 challenge objectives. The original baseline was checked on 18 October 2026 ET / 19 October UTC. The full challenge, five target fields and selected archive facts were refreshed on 7 November. Future implementation tests are marked separately from live archive and file checks.

The authoritative deliverables are the full A–Z dossier, its separately usable Codex handoff, the checksummed dataset manifest, complete required acknowledgment text, and the evidence package. The scientific/architectural uncertainties that affect construction are resolved into an explicit choice, a tested fact, a declared engineering policy, or a bounded limitation with a safe implementation path. No application was built.

## Requirement-by-requirement coverage

| # | Requested topic | Dossier coverage and evidence inspected | Research audit result |
|---:|---|---|---|
| 1 | Precise challenge interpretation | B; phrase analysis and change-type distinctions; official challenge/FAQ refresh | Covered |
| 2 | Competition strategy | W; current schedule versus prior-year rubric/awards; concrete decisions | Covered; final guide not yet published |
| 3 | Developer science primer | D/G; actual L2 HDUs, LVF and 102-channel distinction, units/times | Covered |
| 4 | Complete public product audit | C/E/G; QR2/QR3/current/future/calibration/tool matrix; sample mosaic and MEFs | Covered |
| 5 | Exact programmatic access | F; successful SIA/TAP/DataLink/IBE/S3/MOST/Horizons/resolver requests and schemas | Covered; undocumented APIs not invented |
| 6 | Cutout pipeline | F4/F5/G/H; native IBE and S3 equality test, WCS and PSF preservation | Covered and tested for named case |
| 7 | Cloud data | F5/E/M; bucket/region/keys/range/CORS/bytes; current AWS registry | Covered and tested |
| 8 | FITS handling/libraries | G/L/M; actual QR2/QR3 formats; maintained-library/license audit | Covered |
| 9 | Alignment/reprojection | H/I/T; SIP/TAB separation, operator/support/coverage method and acceptance | Covered; production precision tests specified |
| 10 | Same-wavelength matching | H; actual precision maps, M101 field audit, moving versus fixed-sky gates | Covered with evidence and explicit tolerances |
| 11 | Normalization | I3/I4; calibrated units, ZODI/background, release/gain/PSF and display distinction | Covered |
| 12 | Quality flags | I2/G5; named bit table, SOURCE preserved, unknown/wide flags | Covered; source tables and actual headers checked |
| 13 | Uncertainty | I5; squared weights, covariance, fitted-parameter terms, significance restrictions | Covered; no unsupported probability claim |
| 14 | Temporal metadata | D/G4/H1/N; acquisition versus processing dates, exact example | Covered and tested |
| 15 | Comparison methods | I6/L; blink/swipe/ratio/difference/trails/source methods and tradeoffs | Covered |
| 16 | Automatic motion detection | I6/V; astrometry, matching, recurrence, tracks/parallax, safe candidate language | Covered with bounded feasibility |
| 17 | MOST | F6/J; ambiguity and two-table responses, 287 actual broad-search matches | Covered and tested |
| 18 | Discovery/photometry tools | E/F7/I; official package/source and photometry schema; API boundary | Covered; advanced/link-out path chosen |
| 19 | At least eight real targets/best three | J; nine retained fixed-position searches plus Ceres/comet/QR3 fixture | Covered with exact IDs/coordinates/times/evidence levels |
| 20 | Existing-tool differentiation | L5; Data Explorer/Aladin/ESASky/WWT/Zooniverse; failed WiseView check disclosed | Covered without unverified novelty claims |
| 21 | Five scored concepts/selection | K; five distinct concepts and eight-dimension scores | Covered; one selected direction |
| 22 | Full public user experience | L1/L2/N; progressive disclosure from search through share | Covered |
| 23 | Visualization research | L3/L4; FITS/WCS/HiPS/overlays/mobile/a11y/license/maintenance, explicit choice | Covered |
| 24 | Stretches/false color | I8/L; shared calibrated mapping, signed differences, labeled RGB | Covered |
| 25 | Core interactions | L2/Z; data and component requirements per interaction | Covered |
| 26 | Citizen science | K/N/V; exact classification metadata, controls/consensus/expert boundary | Covered as advanced, no accounts in core |
| 27 | Enrichment services | F8/S; exact tested CDS/JPL, optional Gaia/NED/IRSA holdings, credits/limits | Covered; inaccessible Gaia credit child page disclosed, not a core dependency |
| 28 | Frontend architecture | L/M; React/TS/Vite/Canvas/state/optional charts, reasons | Covered; no product code written |
| 29 | Backend alternatives | M1/M2; browser/proxy/precompute/scientific service/hybrid decision | Covered; one chosen architecture |
| 30 | Precompute/live split | M4/O/X; identical provenance contract, outage-ready real data | Covered |
| 31 | Caching | O2; exact identity/calibration/parameter policy and invalidation | Covered |
| 32 | Data model | N1; all requested entities plus calibration/grid/classification | Covered |
| 33 | Internal APIs | N2; methods, inputs, outputs, errors/cache/provenance and examples | Covered as proposed contracts |
| 34 | Full pipeline pseudocode | H5/I7; discovery through calibration/masks/registration/residuals/assets/provenance | Covered |
| 35 | Performance | O; measured bytes/network/local scope plus memory math/budgets | Covered; deployment measurements explicitly future |
| 36 | Failures | Q; typed system/public/recovery behavior, no fabricated fill | Covered |
| 37 | Accessibility | P/L; WCAG, keyboard/motion/flash/nonvisual/table/contrast checks | Covered as implementation requirements |
| 38 | Transparency | L/N/Q; persistent basic metadata and detailed source/processing records | Covered |
| 39 | Security/privacy | R; typed inputs/SSRF/redirects/files/work limits/caching/secrets | Covered proportionately |
| 40 | License/attribution | S, required_acknowledgments.txt; release DOI and canonical papers, OSS license files | Covered; exact mandatory texts supplied |
| 41 | Small validation dataset | J, demo_dataset_manifest.json; exact URLs/hashes, native/derived distinction | Covered; local FITS inspected |
| 42 | Tests | T; archive/FITS/WCS/spectral/flags/motion/uncertainty/UI/failure/a11y/performance | Covered; actual research checks distinguished from planned app tests |
| 43 | Scientific acceptance | H/I/Q/T/Z; concrete invariant/gate/measurement rules | Covered |
| 44 | Product acceptance | L/T/Z; complete user loop and error/share/offline behavior | Covered |
| 45 | Core/advanced/exceptional | V; each advanced/exceptional feature scored on five requested dimensions | Covered |
| 46 | Risk-first build order | V3/Z; stage objective/dependency/output/verification/fallback | Covered |
| 47 | Risk register | U; likelihood/severity/test/mitigation/fallback | Covered |
| 48 | Decision matrix | M1; explicit choices for source/access/FITS/rendering/compute/data/detection | Covered |
| 49 | AI/ML | M5/V; deterministic baseline, data/evaluation gate for later ML | Covered |
| 50 | Demo storytelling | X/J; 60-second/3-minute/5-minute paths from authentic fixtures | Covered; no fictional discovery |
| 51 | Design direction | L; data-first layout, typography direction, loading/empty/quality states | Covered |
| 52 | Public explanations | L5; concise contextual vocabulary, no textbook UI | Covered |
| 53 | Search/discovery | F8/L/N; named/fixed/moving/coordinate/curated flows and ambiguity | Covered |
| 54 | Reproducible sharing | N3/O; immutable science manifest versus validated display URL state | Covered |
| 55 | Exports | N3/S; PNG/JSON/CSV/FITS and optional clearly labeled animation | Covered |
| 56 | Official SPHEREx examples | F/J/Z; intro/cutouts/ePSF/mosaic/SDT/comet/photometry references | Covered and underlying resources inspected |
| 57 | Code/notebooks | E/F/L/Z; actual official repository source retained, license and pitfalls | Covered; no blind code reuse recommendation |
| 58 | Performance-safe fallback | M4/O/X; real prepared comparison manifests and outage rehearsal | Covered |
| 59 | Thirty direct answers | Y; numbered answer table 1–30 | Covered |
| 60 | Required A–Z order | Full dossier section headers A through Z | Covered; mechanically checked |
| 61 | Final Codex handoff fields | Z and CODEX_HANDOFF_PACKET.md | Covered; all requested subsections present |
| 62 | Implementation-grade specificity | F/G/H/I/N/O/T; exact queries, fields, methods, formulas and acceptance | Covered; recommendations labeled |
| 63 | Recursive research | Underlying PDFs, schema, official source, real FITS, API responses/range tests | Covered; evidence inventory supplied |
| 64 | Prohibited shortcuts | B/C/H/I/Q/Z; no app, future data, fake λ/change/probability/discovery/API | Covered |
| 65 | Final self-review | This audit, source-link/fixture/format/provenance checks, retained scientific limitations | Covered in research scope |

## Full challenge verification, 7 November 2026

| Requirement | Research evidence | Implementation acceptance |
|---|---|---|
| Enter RA/Dec for one sky patch | Exact fixed centers and WISE 0855 sexagesimal-to-decimal conversion in J1 and the manifest | Equivalent inputs produce the same ICRS center. Keep it fixed across playback, URL restore and FOV changes. |
| Display a series like a video | Three independently dated, verified QR2 FITS cutouts per target, common-grid diagnostic and sequence contracts H6/N | Start paused. Play, step or scrub with consistent pixels, dates, wavelengths and masks. Show actual visit gaps. |
| Test all five named fields | Ten live QR2/QR3 SIA discovery responses, 15 successful native IBE cutouts, 15 DataLink calibration associations and five common-grid audits | Exercise all five in the built app, including WISE at the challenge coordinate and flagged bright-source cases. |
| Make motion interpretable | Predicted locators and support checks for the five target fields. Separate Ceres control has visible displacement on the same sky grid. | Keep predictions, observed displacements and brightness changes separate. Retain restricted/context statuses. |
| Optional archive and science features | C, H/I, N and V cover release migration, FOV, coordinate URLs, flags, coadd/difference gates, external overlays and spectra | Keep unsupported quantitative controls gated. Core stays functional during archive failure. |

The five target sequences support playback testing. Three have defective source cores, WISE 0855 moves only 0.295″ in the retained prediction, and none qualifies for a full-field quantitative comparison. The nine-point prefilter was rerun after a shared lazy FITS read returned the wrong D2 map plane. The final offline audit independently resamples both calibration planes and checks file identity, exact data-link association and epoch alignment. Catalog source-fetch results, including direct timeouts and web-index inspection, are in `research/evidence/full_challenge_source_audit.json`.

## Completion evidence and material limits

- The full dossier has all 26 ordered sections, a condensed final handoff, a source index and resolved reference links. Links were checked; the corrected uncertainty reference is recorded. A linked optional Gaia credit document returned HTTP 451 and is explicitly not represented as inspected.
- Every supplied dataset-manifest file is checked against its byte count and SHA-256. All primary science files have matching IMAGE/FLAGS/VARIANCE/ZODI shapes, appropriate ancillary structure and named provenance. A duplicate crop is explicitly a validation artifact.
- The S3 native-section crop equals the authentic IBE cutout in every tested science/PSF/table array and at the tested WCS/λ coordinate. This supports the proposed fallback without claiming universal crop validation.
- The M101 audit proves that a center match can fail full-field eligibility; the report preserves that limitation. Ceres is a visible positional example with different passbands; no brightness-change claim is made. Comet thumbnails are source-centered, not described as an overlapping fixed-sky blink.
- Horizons spacecraft observer `-163182` and actual ephemeris tables for both selected objects were verified. Formal TLE observer uncertainty and final Vantage centroid uncertainty remain scientific validation gates.
- The research deliverable intentionally includes no built app, production deployment, blind source catalog, proven global detector completeness, trained model, or finished UI/accessibility/performance test results. Those are specified for the separate implementation run, not silently claimed as research accomplishments.
- The final challenge objectives are live. The 2026 judging and submission guides were still unverified at the November refresh. See W for the FAQ’s pre-event-work boundary.
- DR1 documentation is published. The linked landing, bucket listing and SIA cone/collection-only checks did not establish DR1 data access. The handoff uses verified QR2/QR3 paths and describes the migration gate.
