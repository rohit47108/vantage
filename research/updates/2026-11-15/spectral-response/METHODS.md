# Native channel coverage, time summaries and conditional bounds

November 15, 2026. This extends the [native extraction workflow](../native-extraction/LIVE_SOURCE_WORKFLOW.md). It derives an immutable view from actual native measurements; it does not replace the parent product, invent missing fluxes, standardize different passbands, or turn separate dates into a simultaneous spectrum.

## Official spectral inputs and the resolved orientation issue

The current [IRSA spectral-calibration page](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/spherex_spectral_calibrations.html) links the July 2026 delivery and its [detailed five-page description](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHERExSpectralFiles_202607.pdf). Nominal channel assignment is geometric, rather than a nearest-wavelength lookup. The delivery also includes representative middle-pixel and all-pixel responses. Those laboratory products have a different role from the pipeline's per-pixel CWAVE/CBAND maps.

The actual `CHANNEL_MAP_17` HDU was inspected: 2040 by 2040 unsigned-byte values 0–18, `DETECTOR=ALL`, `DETCOORD=sky`, instrument version 2.2, date July 25. Its explicit header is more specific than the overview page's generic detector-coordinate/flip warning. Vantage applies no extra MWIR flip to this map. The array is not exactly symmetric: 2,416 pixels differ after an x flip, so the convention matters. Header/schema/checksum checks fail closed if the approved input changes. Native calibration images retain their own separately approved orientation checks.

The original tar object is 436,705,280 bytes. Acquisition used a verified HTTP 206 range of its first 40,000,000 bytes with `If-Match` and the recorded ETag. Only one channel map, six nominal summary CSVs and 204 representative response CSVs were retained, totaling 1,894,325 stored bytes. Tar member paths were never extracted to the filesystem. `acquisition.json` records exact member byte offsets, original/stored SHA-256, original object metadata and the prefix fingerprint. Gzip preserves the original FITS byte stream losslessly. CSV and acquisition-record bytes are protected from checkout newline conversion.

Run `python -m scripts.acquire_spectral_fiducials` for offline verification of all 211 retained members. `--download` reproduces the pinned bounded acquisition; a changed object/prefix is rejected for review. The representative curves are retained for subsequent response work. They are not silently substituted for exact per-pixel responses or used as positive probability densities: some published samples contain negative laboratory baseline values. Current numerical means use the listed native measurements and their errors, without a new synthetic-photometry calibration.

## Exact meaning of channel coverage

For a measured sample, the recorded parent-detector cutout origin plus its final native source position selects the nearest central native pixel using `floor(coordinate + 0.5)`. The official map supplies its local channel. Channels 1–17 yield indices `17*(detector-1)+(channel-1)`. Map values 0 and 18 remain extra edge-region samples; they are not forced into a nominal bin. A conservative 11-pixel central window additionally records whether neighboring channel labels differ. This is a boundary caution, not a proof of an exact point-source passband.

All 102 nominal rows remain in every coverage export, including channels with no passing measurement. Counts distinguish accepted, diagnostic-only and rejected samples when channel assignment is available. A failed input without measured native coordinates remains explicitly unassigned. Therefore a zero passing count means **no passing measurement in this selected product/time window**, not necessarily no exposure or no astrophysical flux.

The [official HiPS tutorial](https://caltech-ipac.github.io/irsa-tutorials/spherex-hipscube/) identifies visualization layers 50/51 as blank. The coverage metadata marks that distinction but does not remove native measurements from those nominal channels merely because a visualization layer is blank.

## Time windows and descriptive means

UTC date endpoints are inclusive calendar dates. Internally the start is midnight inclusive and the end is midnight after the end date exclusive; acquisition midpoints determine membership. Empty date fields use the frozen parent product's extent, not the current date. Default groups span one UTC day; arbitrary integer groups 1–366 days and the entire selected interval are supported by the API. Group boundaries are anchored at the selected start midnight. UI presets are 1, 7, 30 days and all dates; saved custom group lengths restore explicitly.

Only samples passing native fit checks enter means. All signed fluxes, including negative values, are retained; there is no S/N clipping or replacement with zero. Each group contains one detector/nominal channel and one chosen time bucket. Repeated physical observation/detector identities or identical native input checksums are rejected. Different detectors from one simultaneous acquisition are separate physical inputs.

For independent reported statistical errors, `w_i = sigma_i^-2 / sum(sigma_j^-2)`, mean `sum(w_i f_i)`, and variance `sum(w_i^2 sigma_i^2)`. Weights are calculated with a scaled equivalent to avoid overflow. Each bin retains exact input IDs, times, central wavelengths, bandwidths and weights. The plotted mean wavelength is a weighted label; horizontal bars span contributing centers, not CBAND or a new effective bandwidth. The result is a **response-mixed descriptive mean**, not a measurement standardized to a newly calibrated common passband. Original native samples remain authoritative.

A conditional equal-mean chi-square with `n-1` degrees of freedom supplies a scatter diagnostic using the [SciPy 1.15.2 distribution implementation](https://docs.scipy.org/doc/scipy-1.15.2/reference/generated/scipy.stats.chi2.html). The warning threshold is 0.01 divided by the number of tested bins in that view. Wavelength-response differences, variability and systematics can all cause excess scatter. The diagnostic is not a variability detection; repeated interactive choices are not a controlled survey search. Unknown native correlations, shared calibration and model/position systematics remain excluded from the statistical error rather than invented.

## Upper credible bounds versus detection sensitivity

These are distinct outputs. The [PDG statistical review, section 40.4.1](https://pdg.lbl.gov/2025/reviews/rpp2025-rev-statistics.pdf) describes posterior credible intervals and the need to specify a prior. [Kashyap et al. 2010](https://arxiv.org/abs/1006.4334) distinguish observed-data inference bounds from detection-procedure sensitivity. Vantage keeps that distinction explicit.

For an accepted, fixed-position sample with finite positive statistical error and signed S/N below 3, the optional 95% upper credible bound assumes a Gaussian measurement likelihood and a uniform prior on nonnegative true flux. The original signed measurement is still shown/exported. A fitted centroid, missing coverage, bad fit or missing variance produces no such bound. Higher-S/N samples retain the usual flux/error presentation. This reporting threshold does not claim source detection or nondetection.

Writing `f` for measured flux, `s` for its error and `q=.95`, the posterior CDF is

`[Phi((U-f)/s) - Phi(-f/s)] / Phi(f/s)`.

The bound satisfies that expression equal to `q`. The stable implementation is

`U = f - s * ndtri_exp(log(1-q) + log_ndtr(f/s))`.

The [version-matched SciPy inverse-log-CDF API](https://docs.scipy.org/doc/scipy-1.15.2/reference/generated/scipy.special.ndtri_exp.html) avoids cancellation/underflow for negative measurements. At measured zero it gives `1.9599639845*s`, rather than an unjustified generic `f+1.645*s` rule. Independent posterior quadrature checks positive, zero and negative measurements down to -40 statistical errors.

Separately, the conditional fixed-position Gaussian sensitivity asks what true flux gives 95% probability of exceeding a one-position `measured_flux/s >= 5` threshold. With fixed known noise it is `(5 + Phi^-1(.95))*s = 6.644853627*s`; the single-position false-positive probability is about 2.8665e-7. Noise changing with source flux, acceptance by additional quality gates, searching over positions, non-Gaussian backgrounds and real-sky completeness are outside that calculation. It is not a total-error limit. Bounds/sensitivity are not assigned to missing channels, failed fits or descriptive response-mixed means.

## Actual-data evidence and limits

The full frozen live P330E July query contains 147 supported observations. Actual extraction yielded 123 passing samples, nine diagnostic-only samples and fifteen rejected inputs. Passing samples cover 88 nominal channels; three measured inputs lie in extra edge regions and fifteen failures have no channel assignment. With one-day grouping, 118 descriptive bins remain. This is measured coverage of the selected dates, not a claim of complete 102-channel coverage.

An additional, unchanged 10% CALSPEC top-hat approximation check covers all 123 passing samples: 122 meet it; `2025W29_1A_0056_2/D6` differs by approximately +10.9%. That discrepancy is retained in `artifacts/source-full-p330e-calspec-screen.json`, not hidden or passed by relaxing the bound. The original six-detector benchmark remains separately governed by its predeclared checks. This broader query is therefore not claimed to validate precision absolute photometry across every sample. CALSPEC itself also participates in mission calibration, and the top-hat approximation is not exact response synthesis.

A predefined adjacent fixed sky position, without a source identification, was measured from the known actual D4 exposure through the normal native IBE/S3 loader. It gives -18.7904 ± 14.1511 microJy, residual score about 1.039, an 18.0606-microJy conditional upper credible bound and 94.0322-microJy conditional sensitivity. The input is actual archive pixels, with native input checksum/request and a retained measurement product. A fresh SIA query for that adjacent field failed with an upstream request error; its specific HTTP status was not retained. This benchmark does not claim successful discovery there. Its read-only result clearly states that it has no saved discovery parent. All four initial diagonal-position attempts and their failures were retained separately.

Evidence: `artifacts/source-full-p330e-*`, `source-blank-*`, `source-summary-kernel-tests.log`, `source-summary-scientific-tests.log` and browser reports. Tests include independent posterior integration, 12,000 weighted-noise realizations, 2,500 null-scatter realizations, 30,000 sensitivity-power realizations, real unit/mask export round trips, physical-input duplication rejection, date filtering, visible missing channels, native contributor inspection and immutable sharing. Real astrophysical completeness, full-response standardization, broader isolated-source accuracy and unprovided systematic errors remain unresolved.

## Implemented interface

`POST /v1/source-summaries` accepts `product_id`, optional `start_utc`/`end_utc`, and `time_bin_days` (1–366 or null for the entire selected interval). It returns an asynchronous job in the existing bounded persistent queue. Its immutable `source_summary` product records the parent, geometric model identity, complete request, coverage, descriptive means, exact contributors and statistical-bound models. Each CSV/ECSV and SVG export is checksummed. Only fixed summary export filenames are served.

The source workspace automatically prepares the default view, offers explicit date/group selection, filters the individual native chart/table by that time view, and links summary contributors back to native/residual inspection. The current URL and Share measured light retain the summary identity; pending summary jobs can resume by URL. Editing controls clears stale derived output until the next application. Original native exports always retain the full parent. The browser labels dates, mixed responses, statistical errors and the distinction between missing values and bounds.
