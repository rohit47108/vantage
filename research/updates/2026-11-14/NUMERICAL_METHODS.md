# Numerical processing slice

Current implementation is a conditional narrowband linear coadd. This is partial progress on the full analysis specification, not authorization for precision source photometry, source significance or PSF-matched differences.

## Primary sources inspected

- https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/ — newer EPSF table, parent coordinates, zone selection and phase-dependent rendering; official guidance permits newer ePSF calibration for retained QR2 images. Actual retained D2 EPSF table has 441 zones and 33² samples at 5× oversampling. Older optical PSF arrays are not used to claim scientific matching.
- https://irsa.ipac.caltech.edu/data/SPHEREx/docs/spherex_spectral_calibrations.html — CWAVE/CBAND are not full response functions; channel-averaged transmission products have distinct interpretations. A central-wavelength screen does not establish full spectral equivalence.
- https://docs.astropy.org/projects/reproject/en/stable/celestial.html and /api/reproject.reproject_exact.html — area/spherical-polygon reprojection provides an independent geometry reference. Installed validation version: 0.21.0.
- https://docs.scipy.org/doc/scipy/reference/sparse.html — installed SciPy 1.15.2 sparse arrays represent the actual overlap and covariance operators.
- https://docs.astropy.org/projects/photutils/en/stable/api/photutils.psf.ImagePSF.html — installed 3.1.1 for phase-aware PSF work. PSF homogenization remains pending; merely installing this package does not complete that requirement.

## Defined product

Each native pixel is mapped as a quadrilateral into a bounded local TAN region. Polygon overlap areas define a sparse surface-brightness operator A. The small-field planar corner approximation is independently tested against spherical reproject_exact at a predeclared normalized maximum error of 0.001. It is not offered for arbitrary wide-field numerical work.

No weights are renormalized around bad pixels. Any invalid native contributor invalidates the affected output sample. Unknown flags are conservative defects; SOURCE bit 21 remains source information. Native parent offsets and exact versioned CWAVE/CBAND maps are used.

Output covariance is A diag(native VARIANCE) Aᵀ, retaining resampling-induced correlations. Coadds use fixed inverse-diagonal-variance weights and sum Wᵢ Cᵢ Wᵢᵀ. Shared physical exposures are rejected. Native-pixel independence and independent exposures are explicit approximations. Common calibration systematics and unprovided native covariance are excluded; statistical errors are not total scientific errors.

Only joint pixels passing every selected input's coverage, flags and the stricter 0.025-minimum-bandwidth central-wavelength screen (width ratio ≤1.05) are retained. This screen is an engineering selection for a defined mixture, not a claim that full response functions are identical. Individual input wavelengths, widths and weights remain in the FITS export. The weighted CWAVE map is a mean calibration parameter, not an inferred exact effective bandpass.

No background subtraction, ZODI removal, rescaling, clipping, registration fitting or PSF homogenization is done in this product. Times remain an interval and individual dated inputs. A robust estimator, motion compensation and a scientifically eligible subtraction path remain required by the full goal.

## Verification

Run `python -m scripts.validate_coadd` in the locked development environment. It uses real M101 QR2 inputs, a predeclared 0.001 geometry tolerance, and 2,000 independent-native-noise realizations with a predeclared 10% statistical-variance tolerance. It writes artifacts/coadd-scientific-validation.json, including failures.

The first current result retains 105 of 1,024 pixels. Planar versus spherical normalized maximum error is 7.18e-9. Integrated-region covariance predicts variance 0.15185; simulated variance is 0.14843. A diagonal-only calculation gives 0.07331 and substantially underestimates the integrated noise. This simulation validates conditional propagation mathematics, not the unknown native correlations or absolute calibration.

FITS export includes IMAGE, VARIANCE, MASK, NCONTRIB, FLAGS, CWAVE, WEIGHTS, INPUT_CWAVE, INPUT_CBAND and sparse COVARIANCE (ROW,COL,COVARIANCE). Row/column indices use flattened row-major image pixels. Read FITS numeric columns into native-endian NumPy arrays before constructing SciPy sparse arrays; FITS itself uses standard big-endian storage. Masked IMAGE/VARIANCE values are NaN. Covariance entries for excluded samples must not be interpreted without MASK.
