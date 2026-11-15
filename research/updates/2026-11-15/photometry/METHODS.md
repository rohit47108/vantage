# Native photometry core — November 15, 2026

This is a tested numerical dependency for source spectra and PSF-aware analysis. It is **not yet an in-app spectrum workflow**, a complete spectrum, a validated difference pipeline, or authorization for every source/detector. The public viewer has no new spectrum button from this slice. The complete product goal remains active.

## Sources and observed conventions

| Primary resource | Verified fact / observed behavior | Consequence |
|---|---|---|
| [Current IRSA ePSF tutorial](https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/) and [official notebook source](https://github.com/Caltech-IPAC/irsa-tutorials/blob/main/tutorials/spherex/spherex_psf.md) | Versions ≥7 use `EPSF` binary tables; older `PSF` optical arrays are not the recommended scientific model. Tutorial explicitly permits newer ePSF calibration for retained QR2 imagery. | Prefer embedded DR1/QR3 ePSFs. QR2 requires an explicit newer calibration; an optical array alone is rejected. |
| Same tutorial; actual retained D2/D6 tables | Zone centers are in parent-detector coordinates. D2 has 441 rows, 33×33 arrays, 5× sampling and `DETCOORD=sky`. Parent position is `(x+1-CRPIX1A, y+1-CRPIX2A)`. | Select the nearest actual zone center, without assuming equal x/y zone counts. D3's documented 11×41 grid remains supported by the selection method. No additional MWIR flip is applied to a `sky` ePSF. |
| [Photutils 3.1.1 ImagePSF](https://docs.astropy.org/projects/photutils/en/stable/api/photutils.psf.ImagePSF.html) | An ePSF already incorporates pixel convolution; `ImagePSF` interpolates whole-pixel responses and does not integrate them again. The model's usual oversampled normalization differs from the retained SPHEREx arrays. | Actual SPHEREx arrays sum to 1; their native sampled sum is approximately 0.04 at 5× sampling. Normalize the complete phase-rendered native stamp as in IRSA's example. Avoid an approximately 25-fold flux error. Preserve negative empirical wings; do not silently clip the calibration. |
| [Archive product descriptions](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/#additional-product-solid-angle-pixel-map) | Solid-angle maps have 2040×2040 samples in square arcseconds. `IMAGE` is MJy/sr; `VARIANCE` is its square. | Use the actual calibrated map, integer parent cutout offsets and angular units. Convert to steradians, then multiply brightness by `Omega_sr * 1e12` for microJy per pixel. Square that factor for variance. |
| [Live DR1 S3 listing](https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/?list-type=2&prefix=dr1%2Fsolid_angle_pixel_map%2F) | All six current map keys were enumerated. The D2 v3-2026-191 map returned 16,652,160 bytes with `BUNIT=arcsec2`. DataLink's actual D2 association list did not include SAPM. | The benchmark pins the enumerated DR1 map separately. Do not assume the existing spectral-calibration adapter also returns solid angle. Production result generation still needs an explicit release/calibration registry binding. |
| [Official spectrophotometry tool](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html) | Uses native variance, local background, position-dependent source models and calibrated solid angle; ZODI is not separately used. Its `fit_ql` is a mean absolute normalized residual. | The new core fits local background without separately subtracting ZODI. Its residual score is explicitly its own statistic, **not** IRSA's `fit_ql` or a discovery p-value. |
| [SciPy 1.15.2 least_squares](https://docs.scipy.org/doc/scipy-1.15.2/reference/generated/scipy.optimize.least_squares.html) | Supports bounded trust-region fitting and three-point numerical derivatives. | Profile linear flux/background over a bounded centroid search; calculate the full joint Jacobian covariance afterward. |
| [STScI CALSPEC](https://www.stsci.edu/hst/instrumentation/reference-data-for-calibration-and-tools/astronomical-catalogs/calspec.html) and [current FITS directory](https://ssb.stsci.edu/cdbs/current_calspec/) | P330E is a G-type flux standard. `p330e_mod_009.fits` is a March 2026 model with vacuum wavelengths in Angstroms and flux in FLAM, extending to 32 microns. | Pin the actual FITS file and use Astropy spectral-density units to convert the reference to microJy. It is a model/reference, not a SPHEREx measurement. |

These sources were checked live; the historical dossier was not modified. The kernel also checks actual HDU names, detector identity, sampling, coordinate conventions, array shapes, integer calibration origins and units. Callers provide open FITS handles; the future public job layer must bind them to trusted release records and checksums before invoking the kernel.

## Estimators and statistical covariance

No science image is resampled. Native brightness `I_i` is converted to pixel flux `y_i = 10^12 Omega_i I_i`. Native covariance is approximated by the diagonal of the correspondingly converted `VARIANCE`; unprovided correlations and calibration uncertainties are not invented.

For a fixed source position, the model is

```
y_i = F P_i + 10^12 Omega_i [b0 + bx (x_i-x0) + by (y_i-y0)].
```

`P` is the complete phase-rendered finite ePSF normalized before clipping it to the cutout. F therefore refers to that calibrated footprint. Unknown flux outside the supplied ePSF is not added. A clipped PSF cannot be renormalized to conceal missing source coverage.

The PSF estimator solves scaled weighted least squares for F and the three surface-brightness background coefficients. Its complete linear operator L is retained, giving `Cov(beta) = L C L^T`. Background is a surface-brightness plane multiplied by the local pixel solid angles; a constant microJy-per-pixel background would be incorrect when Omega varies.

The aperture estimator uses exact circular pixel-overlap weights. If B maps native flux to the annulus background fit and v integrates that background through the aperture, then the uncorrected estimator is `a - v B`. Its response to the source is `(a - v B) P`; divide by that response for the aperture correction. Also remove the modeled source-wing contribution from the **reported** annulus background. Retain the corrected source/background cross covariance. Simply adding aperture variances or dividing by encircled energy while ignoring the background estimator would omit terms.

An aperture intersecting a defective pixel is rejected. The PSF fit may omit small wing defects only while retaining ≥98% absolute ePSF core support. Unknown flags remain conservative defects; known-source bit 21 is allowed for the target but excluded in the background annulus. At least 20 usable non-source background pixels are required. Source/background masks remain anchored to the independent input position during centroid refinement.

Optional centroid refinement is limited to ±0.75 native pixel per axis, requires initial conditional source S/N ≥20, must converge away from its bounds, and requires local position errors ≤0.2 pixel. Crossing an ePSF zone boundary is rejected with rerun guidance. These are declared engineering validity bounds, not NASA guarantees. The full six-parameter model Jacobian includes flux, background and two centroids. The aperture's derivative through its fitted position is included using the delta method, preserving the covariance with the same native data. This is a local high-S/N approximation.

For residuals, use `R = I - J L` and `C_residual = R C R^T`. Aperture estimation is an oblique projection, so dividing its normalized residual sum blindly by `N-k` is not correct. The diagnostic instead divides by the expected sum obtained from the propagated residual diagonal. It is not a significance calculation. Native windows are capped at 96×96 pixels to bound the matrix operations.

No clipping, robust-estimator uncertainty, deblending, galaxy morphology fit, unknown-wing correction, absolute astrometric registration or PSF homogenization is claimed. Errors are statistical and conditional on the supplied ePSF, masks and model. Position refinement does not convert pixel centroids into precision astrometry.

## Authentic benchmark and validity range

`benchmark.json` retains four actual DR1 D2 cutouts, observation times, source/calibration URLs, checksums and parent-grid positions. `fixture-manifest.json` pins native data, the DR1 spectral/solid-angle calibrations, the CALSPEC model and real Gaia/AllWISE responses. These are factual scientific files with their own credits, not MIT-licensed project code. Validate offline with:

```
python -m unittest discover -s tests -v
python -m scripts.validate_photometry
```

The candidate source is Gaia DR3 `1312054926303736704`, associated with the primary CALSPEC P330E coordinates. Actual Gaia proper motions are -8.882/-38.705 mas/year; catalog parallax is 2.2149 mas. The acquisition coordinates use the stated angular-motion model, omitting observer parallax and perspective acceleration, followed by a fitted local pixel correction. `isolation.json` retains the one-arcminute catalog searches: other Gaia entries within 20 arcsec are much fainter, while the nearest distinct WISE entry is about 27 arcsec away. A brighter object around 46 arcsec lies in the background region and is excluded by source flags. This supports the tested isolated-source use case without proving absence of unresolved companions.

Predeclared checks: 10% agreement with the CALSPEC reference approximation, 5% agreement between aperture and PSF fluxes, 0.1% map-versus-spherical-WCS area agreement, and residual diagnostic <3 for at least one actual sample. The reference approximates the response by a uniform wavelength top hat defined from CWAVE/CBAND; it is **not** exact passband synthesis. P330E is also used in SPHEREx calibration, so agreement tests reduction consistency, not independent correctness of the mission's absolute gain.

For `2025W30_1B_0059_3`, near 1.419737 microns:

| Quantity | Observed result |
|---|---|
| Reference approximation | 28,822.786 microJy |
| PSF flux / conditional statistical error | 28,983.685 / 175.640 microJy |
| Aperture flux / conditional statistical error | 28,937.098 / 186.825 microJy |
| Reference difference | +0.558% PSF; +0.397% aperture |
| Method difference | 0.161% |
| Fitted pixel shift | -0.00085, +0.03103 |
| Residual score | about 1.55–1.6; inspect the current JSON for the exact propagated diagnostic |

Other observations are retained as failures/diagnostics: one aperture intersects a bad pixel, another exposure still has residual score around 4 after centering, and one footprint-search result does not cover the requested point in its actual native cutout. They must not be quietly promoted to valid spectral points. The initial fixed-position result also failed the declared residual criterion and is retained separately. No gate was relaxed to obtain the successful sample.

Synthetic validation uses an independently pixel-integrated analytic Gaussian to test phase rendering, noiseless flux/background recovery, 2,000 native-noise realizations for fixed estimators, and 200 repeated nonlinear noisy fits **per method** for centroid/flux covariance and normalized residual expectations. It also tests detector/legacy-model rejection, unknown/defective flags, insufficient background, missing coverage, invalid units, resource bounds and exact source checksums. Validity outside the tested isolated, high-S/N point-source conditions remains unproven.

## Next integration work — required, incomplete

1. Bind release-matched SAPM/ePSF/spectral calibrations for all supported detectors, with additional real benchmarks and isolation/centering diagnostics.
2. Add persistent asynchronous spectral jobs, bounded live observation selection, cancellation/recovery, per-sample rejection records and truthful time mixing.
3. Add sky source/aperture/background selection, linked scientific chart and native inspection, table/FITS/plot/provenance exports and accessible mobile workflows.
4. Validate missing samples, nondetections, binning and upper-limit policies. Formal errors are not total calibration/model errors.
5. Complete spatially transformed PSF operators, registration and the separate real subtraction workflow. This point-source kernel alone does not satisfy subtraction.
