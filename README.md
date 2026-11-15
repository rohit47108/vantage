# Vantage

Explore the changing infrared sky with authentic NASA SPHEREx data. Vantage combines fixed-field time playback with a new 102-channel wavelength workspace. Numerical analysis features are under development; this repository does not yet satisfy the complete-product specification.

## Current capabilities

- Eight real-data examples, including all five challenge targets, Ceres, M101 and explicitly tracked 3I/ATLAS.
- Coordinate coverage search, fixed-grid temporal playback, pixel inspection, synchronized comparison, scientific support overlays, immutable sequence links and image/provenance exports.
- Object-name lookup through CDS Sesame/SIMBAD; independently loaded Gaia DR3 and AllWISE catalog overlays with frame-specific angular proper motion, source inspection, opacity, bounded candidate associations, credits and exported query/source provenance.
- Metadata-driven wavelength navigation across the DR1 all-sky visualization cube, six detector groups, blank-channel handling, wavelength playback, user-selected false color and view/image exports. Native files are range-read by the backend; the browser never downloads a full cube.
- Asynchronous inverse-variance coadds from selected native exposures, with conservative wavelength/quality support, FITS science and full sparse statistical-covariance exports, provenance and saved-result links. M101 supplies a successful real-data example; incompatible Ceres wavelengths are rejected. These are conditional response-mixed coadds, not PSF-homogenized photometry.

The wavelength cube combines many observation times. Its brightness values and hit/flag maps are visual context, not validated source photometry or a temporal sequence. Robust and motion-compensated coaddition, PSF-matched subtraction, source extraction, Gaia/WISE integration, durable hosting and other complete-product requirements remain in progress. Track actual evidence in [the requirement matrix](tasks/product-evidence.md) and [implementation plan](tasks/product-plan.md).

The original research is retained separately from current findings under research/updates/2026-11-14. Current service URLs and hosting limits are in IMPLEMENTATION_STATUS.md.

## Local launch

Use Node 24 and Python 3.13. From the workspace root, run `npm ci`, create `.venv` with Python 3.13, and install `requirements.lock.txt`. The application now has a clean environment separate from the research environment.

```powershell
npm ci
& C:\Python313\python.exe -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
& .\scripts\launch.ps1
```

The Python path above is the verified interpreter on this Windows machine. Use the equivalent Python 3.13 executable on another machine. For preprocessing or tests, call `.\.venv\Scripts\python.exe` explicitly or activate that environment first.

Generate prepared artifacts with `python -m scripts.prepare`. This verifies the supplied FITS checksums and produces static manifests and bounded pixel/inspection maps in public/prepared.

Run `& .\scripts\launch.ps1` to build and launch the full application at http://127.0.0.1:8000/. This procedure was tested on port 8002 as well. Use one Uvicorn process with the application's two bounded worker threads and persistent `.runtime` directory. For frontend development, run `npm run dev` separately and use http://127.0.0.1:5173/.

Install `requirements-dev.txt`, then run `npm run build`, `python -m unittest discover -s tests -v`, and `npx playwright test`. Browser tests use installed Chrome and a running application. Set `VANTAGE_BASE_URL` to test a public deployment. See ACCEPTANCE.md for actual results, DEMO.md for the walkthrough, and IMPLEMENTATION_STATUS.md for the current public URL and process details.

The development lock includes Reproject as an independent spherical-reprojection reference. Run `python -m scripts.validate_coadd` to reproduce the actual M101 geometry and 2,000-realization statistical-noise validation. Method and limitations are in research/updates/2026-11-14/NUMERICAL_METHODS.md. Pending numerical jobs resume on startup of the explicitly single-instance service. `scripts/check_product_recovery.py` documents the controlled pending-request restart test; its `--seed` step is for a stopped local test service only.

With the local API running, `python -m scripts.validate_surveys` checks real M101 and Barnard Gaia/AllWISE responses against independent analytic TAN projection and Astropy angular transport. It makes live requests. The model and omitted astrometric terms, API/query limits, service failures and primary documentation are recorded in research/updates/2026-11-15/SOURCES.md. Catalog markers and proximity candidates do not validate absolute astrometry or source identity.

The new native photometry core is validated offline with `python -m scripts.validate_photometry`. It performs calibrated-solid-angle aperture and effective-PSF measurements, including background and optional fitted-centroid statistical covariance, on retained real P330E observations. See research/updates/2026-11-15/photometry/METHODS.md for the exact model, reference approximation, successful sample, rejected observations and limits. This is a numerical dependency: asynchronous in-app spectrum generation and scientific spectrum exports remain unfinished.

GitHub Actions runs the production build, retained-fixture/API tests, independent numerical benchmark and browser-runtime dependency audit on pushes to main and pull requests. Real-browser public acceptance is recorded separately; passing this CI workflow alone does not establish public application correctness or complete-product acceptance.

Prepared display assets are included in the repository. Regeneration and offline scientific tests require the supplied FITS research package. Live search caches metadata for 24 hours and empty results for 15 minutes. Wavelength goals check up to 20 parent headers and precision maps at the requested field center.

## Public deployment

The verified public preview is recorded in IMPLEMENTATION_STATUS.md. Static assets are hosted on Vercel. Live Python processing currently runs on this computer through a temporary Cloudflare tunnel. The live route stops when the computer or tunnel process stops. Static prepared examples remain available during backend failure. A persistent cloud Python service has not been provisioned.

After `npm run build`, use `python -m scripts.stage_deploy --backend-url https://YOUR-BACKEND-ORIGIN`, then deploy `.runtime/deploy` through Vercel. Staging contains built public files and an API/new-manifest proxy. Source FITS, credentials, caches and research environment files are excluded. Preserve `.runtime` and generated manifests for exact live-result links. A changed backend origin requires restaging. Prior previews provide rollback.

`python -m scripts.verify_fallback` forces an IBE failure and compares actual S3 native pixels with an authentic IBE cutout. It makes public network requests. Bundled React licenses are in `public/licenses`.

The active product goal still requires persistent cloud Python hosting, saved investigations, the remaining coadd methods, validated differences and source spectra. Catalog context is implemented; it does not establish SPHEREx detections or confirmed cross-identifications.

## License and attribution

Project code is MIT licensed; the existing [LICENSE](LICENSE) is retained. NASA/SPHEREx observations and third-party software retain their own attribution and license requirements. The project MIT license does not relicense upstream data or software. Full NASA/IRSA acknowledgment text is in required_acknowledgments.txt and the application. Historical QR2 native benchmark inputs are preserved under research/fixtures because upstream direct downloads have a retirement date; their exact URLs and SHA-256 hashes are recorded in demo_dataset_manifest.json. Downloaded upstream documentation is not republished as project code.

## Data and scientific scope

Prepared QR2 examples preserve their original dates, files and checksums. Current live discovery uses DR1 and QR3 following IRSA's November 12 access documentation. Direct IBE cutouts have bounded retries. Verified cloud metadata permits an S3 native-section fallback. Production-grade astrometry, photometry and significance are gated pending registration, PSF and uncertainty validation. 3I/ATLAS is explicitly source tracked.

Full NASA/IRSA acknowledgments and release DOIs appear in the application methods panel and exported manifests. Source files and dependency documentation are identified in the research dossier and source comments.

## Official implementation sources

The visual processing path uses Requests plus Astropy's VOTable reader rather than PyVO, and explicit Astropy WCS transformations plus a SciPy bilinear sampler rather than Reproject or Photutils. This keeps interpolation support and defect propagation explicit. These choices implement visual alignment only; they do not establish photometric flux conservation or correct resampled variance. Numerical products remain gated.

SQLite persists the single-instance job index, while hashed disk files cache metadata and scientific products. Two bounded threads perform independent FITS reads with eagerly materialized calibration maps. Multi-instance execution requires a shared queue/storage design before scaling.

- https://react.dev/reference/react/useEffect#fetching-data-with-effects
- https://vite.dev/guide/
- https://fastapi.tiangolo.com/tutorial/static-files/
- https://docs.astropy.org/en/stable/wcs/wcsapi.html
- https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/
- https://irsa.ipac.caltech.edu/data/SPHEREx/docs/spherex_spectral_calibrations.html
