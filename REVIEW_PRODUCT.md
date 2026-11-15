# Complete-product review log

## Name and survey context — November 15, 2026

The adapter uses actual Gator VOTables for both Gaia DR3 and AllWISE after spatial TAP probes failed. It preserves integer source IDs as strings, catalog flags/epochs, raw-query hashes and all query URLs. Bounded response, concurrency, rows, radius and redirect policies keep the routes from becoming arbitrary fetch proxies. A negative test proves name redirects cannot leave the approved CDS mirror hosts.

Gaia angular proper motion is evaluated separately for every acquisition and projected onto that frame's own grid. Historical AllWISE catalog positions are retained, with per-band mean-MJD and Vega-magnitude labels. Observer parallax, perspective acceleration and exact WISE positional epochs are not claimed. The candidate threshold is a review aid with explicit many-to-many, cap and incomplete-query status. Independent analytic projection plus Astropy transport passes on real M101 and Barnard source records to the declared tolerance; this is not measured centroid accuracy.

Review fixes: preserve missing tracked-frame projections as null instead of invalid JSON NaN; expose candidate limits and supplemental source queries; load catalogs independently; abort stale UI requests; include catalog data/credits/selection/opacity in exports; retain frame-specific inspection after marker selection; make the scrolling candidate table keyboard focusable and enlarge disclosure targets. Mobile controls no longer sit underneath the floating timeline. Empty lookup status regions are removed.

Performance diagnosis retained the original/profile failures: drawing finished about 1.4 ms after the click in the apparent 69.5-ms swap, while the RAF observer woke late. Reports now distinguish draw completion, scheduling and observer latency; the <50-ms decoded-update requirement is unchanged. Physical presentation timing remains unmeasured. All 34 scientific/API tests and all 20 local browser tests pass at this source state. Public verification is recorded separately.

Branding follows the user's later explicit choice to retain the restored circular logo and longer title. The complete-product requirements for subtraction, spectra, remaining coadd methods, broad context, releases, investigations/embed and durable hosting remain active.

## First spectral context slice — November 14, 2026

Correctness: confirmed 102 native SPECTRAL_CHANNELS records, two explicitly blank dichroic layers and NESTED HEALPix reference tile 445. Actual IMAGE/NHITS/FLAGS samples at the official tutorial coordinate agree exactly between independent native range sampling and TAN visualization. This does not validate source extraction, photometric resampling or uncertainty propagation.

Contracts: metadata and context results are separate from temporal sequences. Context products carry arrays checksum, source tile URLs, contributing time intervals, units, version, geometry and a numerical-use prohibition. The opaque saved-product route rejects malformed identities.

Security: all cube URLs are constructed from a fixed official base and validated tile indices. Public fields are limited to 1–120 arcminutes and 160² output samples, at most nine tiles, two concurrent context requests and explicit network timeouts. No URL/ADQL proxy is exposed. Further global request rate limits, disk quotas, circuit breakers and durable hosting remain required before declaring the full product operationally complete.

Maintainability: spectral retrieval, API routing and frontend workspace are separate modules. The existing temporal component is preserved and still requires later decomposition as new modes integrate. Upstream visualization arrays are never used to enable numerical analysis.

| Before | After | Why |
|---|---|---|
| New wavelength action crowded the phone header | Action lives in the navigation rail; mobile wordmark is narrower | Removes measured horizontal overflow while preserving the supplied identity |
| Image-only test selector matched both logo and sky | Test targets the sky's accessible name | Tests the intended interaction without removing logo accessibility |
| Cube availability was unresolved in older research | Retained live properties/schema and range-read reference values | Current documented product now powers real wavelength navigation |
| Unlabeled image download | PNG carries channel/color interpretation, field coordinates and NASA/IRSA credit | Export remains interpretable outside the application |

Verification records: artifacts/product-local-browser.json, artifacts/product-public-browser.json, tests/test_hips.py and research/updates/2026-11-14. Public report is written only after its run completes. Earlier demonstration and the new complete-product goal have separate acceptance records.

Remaining scope is explicitly tracked in tasks/product-evidence.md; this review does not approve the full product as complete.

## Conditional coadd slice

Implemented a distinct native-exposure linear coadd with a per-pixel spectral/quality gate, full sparse covariance and calibrated FITS exports. Its narrower 0.025-bandwidth engineering screen does not establish complete response equality. Results retain that limitation and are not eligible for scientific subtraction.

Reviewed fixes: use actual exposure start/end for interval bounds rather than mislabeling midpoints; reject incompatible IMAGE/VARIANCE units; avoid native calibration-map out-of-range indexing; give cancelled retries distinct job IDs; resume persisted pending analysis on process startup; keep initial async loading from closing an already opened mobile control panel. The control-panel regression was observed failing with the old behavior and passing with the fix.

Independent check: planar overlap versus spherical Reproject has normalized maximum discrepancy 7.18e-9 on the real M101 field. Monte Carlo integrated-region variance is 0.14843 versus full-covariance prediction 0.15185; a diagonal-only calculation produces 0.07331. These validate conditional statistical propagation, not native-pixel independence or absolute calibration.

Public endpoint review: numerical inputs are bounded, source files are selected by retained checksums, scientific identities are validated, queue admission is transactional and bounded, and numerical jobs share the two existing workers. UI export paths expose scientific products, not local file paths. Global rate limits, storage quotas, multi-instance queue architecture and durable hosting remain incomplete product requirements.
