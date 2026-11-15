# Implementation review

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
