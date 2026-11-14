# Vantage

SPHEREx sky exploration built from authentic calibrated detector exposures. The original research package remains in the workspace. Current build status and open acceptance work are in IMPLEMENTATION_STATUS.md.

## Local launch

Use Node 24 and Python 3.13. From the workspace root, install `npm ci`, then create a Python virtual environment and run `python -m pip install -r requirements.txt`. The supplied research virtual environment is usable in this workspace.

Generate prepared artifacts with `python -m scripts.prepare`. This verifies the supplied FITS checksums and produces static manifests and bounded pixel/inspection maps in public/prepared.

Start the API with `python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000` and the frontend with `npm run dev`. Open http://127.0.0.1:5173/. Vite proxies /v1 requests to the API. Prepared examples load from static delivery independently of the API.

Run `npm run build` and `python -m unittest discover -s tests -v` for the current build and offline scientific regression checks. Browser and public deployment acceptance remain tracked separately.

## Data and scientific scope

Prepared QR2 examples preserve their original dates, files and checksums. Current live discovery uses DR1 and QR3 following IRSA's November 12 access documentation. Direct IBE cutouts have bounded retries. Verified cloud metadata permits an S3 native-section fallback. Production-grade astrometry, photometry and significance are gated pending registration, PSF and uncertainty validation. 3I/ATLAS is explicitly source tracked.

Full NASA/IRSA acknowledgments and release DOIs appear in the application methods panel and exported manifests. Source files and dependency documentation are identified in the research dossier and source comments.

## Official implementation sources

- https://react.dev/reference/react/useEffect#fetching-data-with-effects
- https://vite.dev/guide/
- https://fastapi.tiangolo.com/tutorial/static-files/
- https://docs.astropy.org/en/stable/wcs/wcsapi.html
- https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/
- https://irsa.ipac.caltech.edu/data/SPHEREx/docs/spherex_spectral_calibrations.html
