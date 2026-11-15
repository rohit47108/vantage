# CODEX HANDOFF PACKET

### Product Definition

Build **Vantage**, a public SPHEREx temporal explorer. A visitor enters RA and Dec and plays a dated sequence of real exposures of one fixed sky patch. Show wavelength and quality limits, and offer pair inspection and exact sharing. Use J1 to test all five targets in the published 2026 objective. [Official challenge][s13].

### Core User Journey

Enter RA/Dec or choose a named fixture → preview fixed center/FOV and coverage → open a recommended common-grid sequence → play, pause, step and scrub through actual acquisition dates → inspect quality, wavelength and source predictions → optionally choose A/B → share immutable sequence and provenance.

### Final Feature Set

**Core:** typed decimal and sexagesimal coordinates; bounded field size; live and prepared fixed-sky sequences for the five named targets; actual exposure dates and snapped spectral options; common grid, shared stretch, play/pause/step/scrub and A/B inspection; coverage, quality and wavelength overlays; known-object prediction labels; typed failures; coordinate search and immutable share URLs; accessible controls and prepared fallback. Use Ceres and M101 as separate scientific controls.

**Optional:** matched coadds and differences, Gaia/WISE context through an independently credited overlay, official spectrophotometry link-out and later validated extraction, measured motions, validated significance and reviewed tracklets. Use V for dependency and scope decisions.

### Chosen Stack

React 19.3.x + TypeScript + Vite 8.3.x; Canvas 2D + semantic HTML/SVG controls; Python 3.13 + FastAPI/Pydantic, NumPy/SciPy, Astropy 8.0.1, PyVO 1.9.1, Reproject 0.21.0, Photutils (3.0.0 research-tested; 3.1.1 current release at final refresh), `fsspec`/`aiohttp`; SQLite single-instance job/cache metadata; bounded worker processes; static/CDN assets and object/disk scientific cache. Lock/test exact dependencies and runtime engines. React 19.3.1 and FastAPI 0.146.0 were current at final refresh; they were repository-verified, not application-tested here.

### System Architecture

Browser handles view state and rendering. API validates typed requests, resolves/cache-searches metadata and submits jobs. Workers retrieve native MEFs/calibrations, apply science gates and transforms, and publish immutable arrays/images/masks/manifests. Prepared examples use the same manifest contract. No raw-FITS reduction or giant catalog scan in a visitor's browser.

### External Services

`https://irsa.ipac.caltech.edu/SIA` for discovery; `https://irsa.ipac.caltech.edu/TAP/{sync,async}` for ADQL; `https://irsa.ipac.caltech.edu/datalink/links/spherex?ID=...` for exact files/calibrations; returned `https://irsa.ipac.caltech.edu/ibe/data/spherex/...fits?center=...&size=...` for native cutouts; bucket `nasa-irsa-spherex`, `us-east-1` for anonymous range fallback. MOST `https://irsa.ipac.caltech.edu/cgi-bin/MOST/nph-most` for known-object footprints. Optional CDS Sesame/SIMBAD and serialized backend Horizons requests; spacecraft observer `CENTER='500@-163182'` is live-verified for selected Ceres and 3I exposure times. Mosaic/photometry are supported interactive link-outs unless a documented API becomes available.

### Dataset Strategy

Use verified QR2/QR3 L2 exposures. Preserve per-artifact release and calibration identities. DR1 DOI/help records exist but no working DR1 image or cube data access was established on 7 November. Follow C’s capability gate and deduplicate replacement exposures on migration. The 28-file `demo_dataset_manifest.json` and `research/fixtures/` supply the data. Keep metadata coverage, predicted position and measured detection distinct. [Archive access guide][s72], [DR1 images DOI][s76], [DR1 cube DOI][s77].

### Data Pipeline

Typed center/FOV/time/λ → circumscribed SIA/TAP footprint query → VO status/completeness → exact artifact and calibration resolution → group actual visits and shortlist candidates → padded cutouts or S3 sections → named-HDU checks → common TAN grid with per-frame coverage, quality and wavelength → joint support → display assets and immutable manifest. Numerical pair products additionally require background, PSF, registration and uncertainty gates.

### Algorithms

Use primary TAN-SIP for sky geometry. For approximate alternate spectral WCS, set its SIP to None. For precision use native parent-pixel CWAVE/CBAND. Load calibration planes independently or fully materialize them before sharing across worker threads. For every accepted grid pixel require sequence max−min wavelength ≤0.10 × minimum width and max/min width ≤1.10, with stricter response gates where needed. Pick 3–8 actual visits when available. If fewer pass, expose pair/single/empty or context states under H6. Keep the sky grid fixed even for moving targets. Reproject brightness with declared weights and variance with squared weights plus covariance. Use B−αA−β only after the numerical pair gates. Validate ePSF, registration and uncertainty against controls before measuring sources or reporting significance.

### Data Structures

Implement section N entities, including `Sequence` with a fixed grid and ordered immutable frame records. Preserve per-frame artifact/calibration IDs, UTC and MJD, wavelength reference coordinate/width/range, display/mask hashes and coverage. Keep search completeness, coverage state and scientific status separate. Use explicit units and decimal strings for wide flags. Pair comparisons distinguish fixed-sky temporal, moving-source astrometry and spectral context.

### Internal API Contracts

Implement N2: resolve target, search exposures, `POST /v1/sequences`, `GET /v1/sequences/{hash}`, job status/cancel, optional pair submission, manifest/inspect/provenance. Return `202` with job URL or a cached immutable result. Define recoverable coverage states for 0/1/2/3+ frames and typed upstream/scientific failures. Enforce fixed work limits and allowlisted archive destinations. Implement `/sky?ra=...&dec=...&fov_arcmin=...` for fresh searches and `/sequence/{hash}` for exact replay.

### UI Screens

Coordinate form and five named quick starts, coverage selector, primary fixed-sky player, A/B inspection, source and quality drawer, Data & Methods and sharing. Persist fixed center, field size, current acquisition date, sampled wavelength, science status and credits. Show full source and calibration information in details.

### Interaction Requirements

Start paused. Provide keyboard-operable previous/next, scrub and frame-list selection, play/pause and an optional loop. Show actual UTC gaps separately from playback speed. Preserve camera and stretch on frame changes, swap imagery and metadata atomically and expose no-data coverage. Provide A/B swipe and static alternatives, text legends, and exact restore. Failed assets keep their identity and date.

### Demo Dataset Manifest

**Required five targets:** `full_challenge_benchmarks` gives three ordered QR2 files per target, exact fixed centers, checksums, actual UTC/MJD, calibration links and support metrics. Start with the challenge’s WISE 0855 input (`08h55m10.831s, −7d14m42.53s`), D6 around 4.816 µm, then test Barnard’s Star, Epsilon Indi B, RW Aurigae and R Draconis. Three fields have defective source cores. The brown-dwarf fields have scalar source agreement but limited full-field support. WISE’s 0.295″ prediction across these frames is subpixel. All five sequences are for real playback and interpretation tests. No numerical brightness-change or measured-motion claim was established for them. See J1 and `research/evidence/full_challenge_sequences_research.png`.

**Ceres:** `2025W27_1A_0591_4/D2` and `2025W27_1A_0632_1/D2`, 3 July 2025, ~4.79653 h apart; predicted 142.96″ and provisional centroid 139.05″ displacement; λ≈1.41348/1.44823 µm, so positional-only and no brightness difference. **M101:** `2025W22_1B_0584_1/D2` and `2025W49_2A_0650_4/D2`, 29 May/7 December 2025; matching center but only ~19.94% of tested 6′ field passes provisional scalar gate. **3I/ATLAS:** `2025W32_1A_0662_3/D3` and `2025W32_2D_0017_4/D3`, 7 August 2025; λ≈2.19044/2.19229 µm, ~812.48″ predicted movement; existing small cutouts are separately tracked, not overlapping fixed-sky views. All exact URLs, times, bytes and SHA-256 values are in the supplied JSON manifest.

### Edge Cases

Handle RA wrap/poles, high proper motion/catalog epoch, moving-target observer geometry, clipped/rotated boxes, different actual dimensions, gaps/NaNs, unknown flags, saturated/extended/crowded sources, structured foreground, unsupported wavelength/epoch, reprocessed artifacts, QR2/QR3 formats, multiple VOTable tables, VO overflow, CORS and upstream 503/timeouts. Prepared data remain labeled and traceable.

### Scientific Guardrails

One L2 file is one spatially varying-wavelength detector exposure. SIA BAND/channel/detector equality is not source/field passband equivalence. SOURCE bit 21 is not a defect. DATE is not DATE-OBS. Do not double-divide exposure or double-subtract ZODI. No variance-as-brightness reprojection, omitted convolution covariance, unvalidated sigma, fake probabilities, invented identity, or Planet-X discovery claim. Source-centered tracking and fixed-sky motion are different views. Preserve masks/coverage/calibration/provenance through export.

### Performance Targets

Prepared first frame ≤1.5 s warm/≤3 s typical cold target, decoded swaps ≤50 ms, cached inspect ≤1 s, and interactive pan/zoom usable at 30 Hz. Acknowledge uncached jobs asynchronously and start with the O budgets. Default 6′, bounded ≤30′/≤512² science grid, 3–8 visits when available, next-frame predecode and two bounded workers. Measure full workflow performance on deployment.

### Accessibility Requirements

WCAG 2.2 AA target; full keyboard workflow, focus restoration, labeled discrete units/timeline, pause/static/reduced-motion alternatives, flash-safety review, sufficient contrast/touch targets, non-color masks/markers, accessible measurement tables and comparison summaries, no announcement per blink frame.

### Testing Requirements

Pass section T: all five sequence fixtures, WISE sexagesimal parsing, actual chronological identity, one fixed grid per sequence, spectral and quality intersections, QR2/QR3 parser and calibration tests, Ceres positional control and M101 footprint rejection. Also test stale jobs/failed frames, search URL versus immutable replay, prepared fallback, keyboard/reduced motion and deployment performance. Apply PSF, registration and variance tests before enabling numerical claims.

### Build Sequence

1. Lock exact fixtures, schemas, units, WCS and flags.
2. Prove multi-frame spectral-time selection and per-frame quality states on real inputs.
3. Prepare the five common-grid sequences and the Ceres/M101 controls with reviewed overlays.
4. Implement immutable manifest/cache and bounded persistent jobs.
5. Build accessible public comparison/inspection/share flow.
6. Add live search/retrieval with IBE/S3 failure handling.
7. Validate numerical residual/significance only where scientifically supported.
8. Finish credits, mobile/a11y/performance, outage rehearsal and demo.
9. Add one advanced feature only after core acceptance.

### Acceptance Criteria

A new visitor enters decimal or sexagesimal RA/Dec and plays actual observations of one fixed field. All five named fixtures open and pass the frame-identity, timeline, coverage and quality tests. Ceres shows positional motion separately. The player handles sparse coverage, disabled science modes and failed assets with explicit states. An immutable link restores the exact sequence, and prepared mode works with the archive disconnected. Refresh 2026 submission and licensing requirements before any competition use. These are acceptance criteria for the future implementation.

### Source Index

Read the full challenge and J1 first, then IRSA’s release overview, product/access guide, explanatory supplement, SIA/TAP/IBE contracts, official notebooks, spectral calibration documentation and actual saved responses/files. The software and baseline archive checks are dated in the dossier. The challenge objectives and targeted archive evidence were refreshed on 7 November. Recheck changing sources at build and submission time.

| Resource | Implementation purpose |
|---|---|
| [IRSA mission][s01], [release overview][s02], [delivery schedule][s03] | Current versus planned products, DOIs and release transitions |
| [Archive product guide][s04], [access guide][s72], [supplement PDF][s19] | HDU/header/calibration semantics; deeper pipeline and quality definitions |
| [SIA][s05], [TAP][s07], [IBE cutouts][s06], [DataLink standard][s32] | Exact discovery/query/cutout and association contracts |
| [Intro][s09], [cutouts][s33], [PSFs][s10], [mosaics][s23], [SDT][s18] | Official worked examples; audit the documented source conflicts |
| [Official repository][s73] | BSD-licensed tutorial source; exact files under `tutorials/spherex/`, including `spherex_intro.md`, `spherex_cutouts.md`, `spherex_psf.md`, `spherex_mosaic.md`, and `spherex_source_discovery/` |
| [Spectral package][s11], [fiducial PDF][s21] | Per-pixel/nominal-channel/response distinctions, file organization/orientation/numbering |
| [Photometry help][s24], [mosaic help][s25], [MOST API][s36] | Tool inputs, output flags, limits and API boundary |
| [Dedicated 3I/ATLAS][s17], [comet science][s50] | Actual moving-object data manifest and published context |
| [Mission paper][s20], [pipeline paper][s22], [mapmaking paper][s26] | Scientific derivations, instrument/processing/mapmaking limitations |
| [Cloud][s08], [AWS registry][s34], [Astropy remote sections][s35], [Fornax][s40] | Public hosting, range access and optional cloud analysis |
| [Current challenge][s13], [FAQ][s14], [2025 guide][s70], [prior awards][s71] | Current schedule and explicitly prior-year judging reference |
| [DR1 image DOI][s76], [DR1 cube DOI][s77], [updated Explorer help][s78] | Published DR1 documentation with separate unresolved access checks in C |
| [Epsilon Indi B][s79], [binary measurement][s80], [WISE 0855][s81], [discovery paper][s82], [adopted WISE astrometry][s86], [RW Aur][s83], [R Dra][s84], [optical bulletin][s85] | Identities, astrometry and variable-star context for the exact fixtures |
| [Reproject][s12], [Photutils PSF matching][s46], [detection][s48], [normalization][s49], [uncertainty][s47] | Scientific implementation primitives; validate chosen operators |
| [WCAG][s67], [NASA media][s69], [IRSA acknowledgment][s68], library/license audit | Accessibility and attribution obligations |

[s01]: https://irsa.ipac.caltech.edu/Missions/spherex.html
[s02]: https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_qr.html
[s03]: https://spherex.caltech.edu/page/data-products
[s04]: https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/
[s05]: https://irsa.ipac.caltech.edu/ibe/sia.html
[s06]: https://irsa.ipac.caltech.edu/ibe/cutouts.html
[s07]: https://irsa.ipac.caltech.edu/docs/program_interface/TAP.html
[s08]: https://irsa.ipac.caltech.edu/cloud_access/
[s09]: https://caltech-ipac.github.io/irsa-tutorials/spherex-intro/
[s10]: https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/
[s11]: https://irsa.ipac.caltech.edu/data/SPHEREx/docs/spherex_spectral_calibrations.html
[s12]: https://reproject.readthedocs.io/en/stable/celestial.html
[s13]: https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/
[s14]: https://www.spaceappschallenge.org/resources/participant-faqs/
[s15]: https://science.nasa.gov/mission/spherex/
[s16]: https://arxiv.org/abs/2108.09868
[s17]: https://irsa.ipac.caltech.edu/data/SPHEREx/docs/comet3iatlas/index.html
[s18]: https://caltech-ipac.github.io/irsa-tutorials/spherex-source-discovery-tool-demo/
[s19]: https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp_QR.pdf
[s20]: https://doi.org/10.3847/1538-4357/ae2be2
[s21]: https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHERExSpectralFiles_202607.pdf
[s22]: https://doi.org/10.3847/1538-4365/ae8843
[s23]: https://caltech-ipac.github.io/irsa-tutorials/spherex-mosaic/
[s24]: https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html
[s25]: https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/mosaic.html
[s26]: https://arxiv.org/abs/2603.25790
[s27]: https://ivoa.net/documents/SIA/
[s28]: https://ivoa.net/documents/ObsCore/
[s29]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS
[s30]: https://ivoa.net/documents/TAP/
[s31]: https://pyvo.readthedocs.io/en/latest/dal/index.html
[s32]: https://ivoa.net/documents/DataLink/
[s33]: https://caltech-ipac.github.io/irsa-tutorials/spherex-cutouts/
[s34]: https://registry.opendata.aws/spherex-qr/
[s35]: https://docs.astropy.org/en/stable/io/fits/usage/cloud.html
[s36]: https://irsa.ipac.caltech.edu/applications/MOST/MOSTProgramInterface.html
[s37]: https://pyvo.readthedocs.io/en/latest/api/pyvo.dal.SIA2Service.html
[s38]: https://astroquery.readthedocs.io/en/latest/ipac/irsa/irsa.html
[s39]: https://ned.ipac.caltech.edu/Documents/Guides/Interface/URLs
[s40]: https://docs.fornax.sciencecloud.nasa.gov/
[s41]: https://astroquery.readthedocs.io/en/latest/simbad/simbad.html
[s42]: https://docs.astropy.org/en/stable/coordinates/apply_space_motion.html
[s43]: https://ssd-api.jpl.nasa.gov/doc/horizons.html
[s44]: https://ssd-api.jpl.nasa.gov/doc/index.php
[s45]: https://fits.gsfc.nasa.gov/fits_standard.html
[s46]: https://photutils.readthedocs.io/en/stable/user_guide/psf_matching.html
[s47]: https://docs.astropy.org/en/stable/api/astropy.nddata.VarianceUncertainty.html
[s48]: https://photutils.readthedocs.io/en/stable/user_guide/detection.html
[s49]: https://docs.astropy.org/en/stable/visualization/normalization.html
[s50]: https://spherex.caltech.edu/news/nasa-s-spherex-mission-tracks-brightening-of-interstellar-comet
[s51]: https://simbad.cds.unistra.fr/Pages/guide/ch15.htx
[s52]: https://aladin.cds.unistra.fr/AladinLite/doc/
[s53]: https://github.com/cds-astro/aladin-lite/blob/master/LICENSE
[s54]: https://docs.worldwidetelescope.org/webgl-reference/latest/
[s55]: https://github.com/ericmandel/js9
[s56]: https://github.com/astrojs/fitsjs
[s57]: https://plotly.com/javascript/
[s58]: https://d3js.org/d3-scale
[s59]: https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API
[s60]: https://www.ivoa.net/documents/HiPS/
[s61]: https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/api.html
[s62]: https://sky.esa.int/esasky/
[s63]: https://www.zooniverse.org/about
[s64]: https://react.dev/learn/build-a-react-app-from-scratch
[s65]: https://vite.dev/guide/
[s66]: https://fastapi.tiangolo.com/tutorial/background-tasks/
[s67]: https://www.w3.org/TR/WCAG22/
[s68]: https://irsa.ipac.caltech.edu/ack.html
[s69]: https://www.nasa.gov/nasa-brand-center/images-and-media/
[s70]: https://spaceapps-v2-staging.s3.amazonaws.com/media/documents/Final_Space_Apps_2025_Judging_Guidelines_for_web.pdf
[s71]: https://www.spaceappschallenge.org/2025/awards/
[s72]: https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/
[s73]: https://github.com/Caltech-IPAC/irsa-tutorials/tree/main/tutorials/spherex

[s74]: https://ssd.jpl.nasa.gov/api/horizons.api?format=json&COMMAND=%27SPHEREx%27&MAKE_EPHEM=%27NO%27&OBJ_DATA=%27YES%27
[s75]: https://www.cosmos.esa.int/web/gaia-users/archive/programmatic-access
[s76]: https://www.ipac.caltech.edu/doi/10.26131/IRSA678
[s77]: https://www.ipac.caltech.edu/doi/10.26131/IRSA679
[s78]: https://irsa.ipac.caltech.edu/onlinehelp/spherex/help.pdf?id=607b86d
[s79]: https://simbad.u-strasbg.fr/simbad/sim-id?Ident=Epsilon+Indi+B
[s80]: https://www.aanda.org/articles/aa/pdf/2004/03/aa0292.pdf
[s81]: https://simbad.cds.unistra.fr/simbad/sim-id?Ident=WISEA+J085510.74-071442.5
[s82]: https://doi.org/10.1088/2041-8205/786/2/L18
[s83]: https://vsx.aavso.org/index.php?revid=418953&view=detail.top
[s84]: https://simbad.cds.unistra.fr/simbad/sim-id?Ident=%40376084&Name=V%2A+R+Dra&submit=submit
[s85]: https://www.aavso.org/sites/default/files/bulletin/Bulletin2014.pdf
[s86]: https://vizier.cfa.harvard.edu/viz-bin/asu-tsv?-source=J%2FApJS%2F253%2F7%2Ftablea1&-c=133.81890825+-7.247048&-c.rs=300&-out.max=20&-out.all=1
