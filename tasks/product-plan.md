# Complete Vantage product — November 14, 2026

Authority: the user's new goal-objective.md and pasted-text-1.txt in attachment 09d78874-514b-479c-9b47-69a53104e855. No inherited deadline. Earlier demo acceptance does not establish completion of this product.

## Ordered vertical slices

1. Preserve branding; integrate existing GitHub main and MIT license. Publish accurate README and source without environments/secrets. Verify Git remote tree and build.
2. Spectral context: live properties and FITS schema, bounded range reads, metadata-driven channels, actual wavelength images, missing channels, false color and exports. Keep visualization trace distinct from source extraction. Verify real cube pixels against independent direct reads, blank channels, HPX orientation and browser controls. Dependencies: none. Modules backend/hips.py, src/SpectralExplorer.tsx, tests/test_hips.py.
3. Search and survey context: name resolution, direct field manipulation, Gaia epochs/proper motion and WISE imagery/catalog with failure handling. Verify real alignment and independent coordinate transforms. Depends on shared sky coordinates.
4. Numerical operators: explicit sparse resampling, variance/covariance, conservative masks, calibrated solid angle and position-dependent PSFs. Synthetic flux/noise/registration tests plus real cutouts. Keep public products locked until validated. Modules backend/operators.py and scientific regression tests.
5. Coadds: typed asynchronous product requests, weighted and validated robust methods, counts, membership, time windows, native exports; fixed and motion-compensated authentic benchmarks. Depends on 4.
6. Difference: PSF match, registration, background/calibration fits, fitted uncertainty and shared-input rejection. Demonstrate actual eligible real pair with injections and residual checks. Depends on 4/5.
7. Source spectra: isolated-source aperture and supported PSF fitting, solid-angle/aperture corrections, time/quality selection, missing samples and source/plot/table exports. Validate authentic isolated-source benchmark independently. Depends on 4.
8. Cohesive Explore / Compare time / Measure light workflow; swipe/independent stretch, epoch groups, accessible charts and progressive disclosure. Refactor current large component as these slices integrate; preserve existing regression tests.
9. Persistent investigations, scientific identities, FITS exports, embed mode/iframe tests and reproducibility. Depends on product contracts.
10. Release registry: canary promotion, schema checks, retirement, cache invalidation and rollback. Retain immutable older results. No unknown-release auto-promotion.
11. Durable deployment, persistent store, restart/backup/restore and operational diagnostics. Investigate existing authorized hosting early; no paid purchases. Prepare deployable single-instance service independently if infrastructure needs credentials.
12. Complete performance, security, WCAG/mobile/public acceptance, authentic six-part demo and plain-language team guide. Audit every requirement below against current evidence.

Every slice: focused regression → build → real-data operation → relevant browser evidence → update matrix → coherent commit. No analysis feature is complete without a successful authentic-data path, a negative gate test and a justified independent check. Recoverable failures are fixed before proceeding.

## Scientific boundaries

HiPS cube is survey-combined visualization context, not a temporal sequence or variance-bearing source spectrum. Native exposures and release-matched calibration govern numerical analysis. Existing five target fixtures remain interpretation examples and cannot be used to bypass numerical gates.

## API contracts for first slice

- GET /v1/spectral/metadata: properties, version identity, 102 channel records with detector/channel/index/wavelength/width/blank status and documented provenance.
- GET /v1/spectral/plane?ra=&dec=&fov_arcmin=&layer=: one bounded north-up TAN image, sample coordinates, brightness/hits/flags, actual spectral metadata and per-tile sources. Backend only reads bounded native sections through HTTP ranges.
- Later scientific product POST routes return durable Job; completed immutable products have distinct typed manifests. View stretch/color choices do not change scientific source identity.

Retain existing snake_case conventions and additive routes. Reject invalid/nonfinite coordinates, layers and oversized regions. No arbitrary remote URL input.
