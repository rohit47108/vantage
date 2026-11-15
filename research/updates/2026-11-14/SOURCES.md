# Current product source ledger

Accessed November 14, 2026 (America/New_York). Historical dossier retained unchanged.

| Source | Evidence category | Finding / implementation consequence |
|---|---|---|
| https://irsa.ipac.caltech.edu/data/hips/SPHEREx/spherex_allsky_cube/properties | Live-tested | HTTP 200, CORS *, 102 layers, six groups of 17, layers 50/51 blank; release date 2026-11-01. Metadata and headers retained alongside this file. This supersedes the historical unavailability of cubes. |
| https://caltech-ipac.github.io/irsa-tutorials/spherex-hipscube/ | Documented | NESTED HEALPix order 5, documented native cube URL construction; IMAGE/NHITS/FLAGS/SPECTRAL_CHANNELS/WCS-WAVE. Visualization only; no fabricated photometric errors. |
| https://docs.astropy.org/en/stable/io/fits/usage/cloud.html | Documented API | use_fsspec=True and HDU.section allow partial range reads. Avoid HDU.data on the three 102×512×512 cubes. |
| https://docs.astropy.org/projects/astropy-healpix/en/latest/api/astropy_healpix.HEALPix.html | Documented API | lonlat_to_healpix with nested order maps field samples to documented native cube tiles. Installed version 2.0.1. |
| https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html | Documented | Official source extraction fits a PSF-aware model and background, with solid-angle calibration and minutes-to-hours jobs. Cube trace does not satisfy validated extraction requirement. |
| https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_qr.html | Documented | DR1 and QR3 are current discovery releases; preserve historical QR2 fixtures and test migration separately. |
| https://github.com/rohit47108/vantage | Live-tested | Existing public repository main contained MIT license, copyright Rohit Singh 2026. Merged its history without overwriting it. MIT covers project code; upstream data/software retain their own credits/licenses. |

Engineering choice: first deliver bounded north-up TAN views sampled from native HPX cube sections. This is explicitly visual nearest-neighbor sampling, preserving no-data and flags; it authorizes neither flux-conserving reprojection nor source photometry. A separate validated native-exposure pipeline will govern numerical products.
