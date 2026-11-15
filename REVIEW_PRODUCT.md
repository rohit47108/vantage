# Complete-product review log

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
