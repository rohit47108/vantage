# NASA challenge coverage for the demo

The [official challenge](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/) was read in Chrome on November 15, 2026 with HTTP 200 and normal TLS validation. Browser rendering succeeded after other fetch methods failed. NASA explicitly distinguishes required objectives from optional considerations.

| Required objective | Demo evidence |
|---|---|
| Public coordinate-based time viewer | Decimal/sexagesimal coordinates, real coverage, dated fixed-field images, playback, inspection and sharing work. |
| Five named target tests | Barnard's Star, Epsilon Indi B, WISE 0855, RW Aurigae and R Draconis each have three authentic prepared exposures. All five are browser-tested and included in production preflight. |

## Every optional consideration

| Topic | Capability and boundary |
|---|---|
| Updating data | Approved DR1/QR3 discovery and versioned calibrations work. Automated new-release approval/rollback remains pending. |
| Infrared bands/spectra | All 102 mosaic channels, detector grouping, false color, visual traces and actual asynchronous native-source extraction work. Source coverage is incomplete; full-detector calibrated broadband sums are not claimed. |
| Combining/differencing | Actual weighted combination works on M101. Validated numerical subtraction remains pending; swipe is visual comparison. |
| Field size | User-chosen bounded fields work. Arbitrarily wide-sky processing is unfinished. |
| Other surveys | Gaia DR3 and AllWISE catalogs, epochs, opacity, selection, credits and candidate associations work. |
| URL integration | Coordinate/view URLs work. A dedicated compact cross-site iframe mode remains unfinished. |
| Metadata/contamination | Timestamps, wavelengths, support/quality masks, flags, missing pixels and provenance are exposed. |
| Astronomy software | Astropy WCS/FITS/tables and scientific operators are used, with independent numerical references. |

These rows cover the whole list without claiming unfinished features. The optional list is distinct from the core requirement. This is not NASA certification. The broader custom product specification still has open requirements in tasks/product-evidence.md.

See DEMO.md for presenting steps and the local-backend dependency. Test and release records are in IMPLEMENTATION_STATUS.md.
