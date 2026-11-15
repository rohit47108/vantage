# General native source workflow

November 15, 2026. This documents the implemented general source-selection, discovery, queued extraction and inspection slice. It extends the [six-detector numerical methods](METHODS.md) and preserves the earlier [retained D2 workflow](../photometry/SOURCE_WORKFLOW.md). It does not establish complete channel coverage, a simultaneous spectrum, independently validated absolute calibration, or completion of specification F.

## Browser path

Open `/?view=measure` through **Sources**, **Measure this sky position**, or **Measure selected Gaia source** in the sky workspace. A pixel selection supplies the inspected plane's actual ICRS coordinate. A Gaia selection supplies its original catalog coordinate, both angular-motion components and reference epoch; a propagated display marker is not reused as a catalog-epoch coordinate. The user can instead enter coordinates or resolve an object name. Name resolution alone does not infer motion.

Choose inclusive UTC start/end dates, optionally include deep-survey metadata, and find source observations. The frozen observation field lists individual detector exposures, release capability, original metadata query dates and completeness. Select at most 512 observations, choose effective-PSF or corrected-aperture extraction and run it. Coverage, exact approved calibration, pixel quality, background and fit gates are applied to each native input. Metadata selection does not guarantee a measurement.

The result links each table row to its native brightness and used-pixel residual stamp, with source/core/aperture and background-annulus geometry. The chart plots passing measurements at their own central CWAVE/CBAND and acquisition dates. Failed and diagnostic-only inputs remain in the table and downloads. An unmeasured input is not a zero or an upper limit. Quality filtering affects the table; the chart always plots passing samples only. All-row CSV/ECSV, SVG and provenance JSON exports remain available.

Native stamp JSON is loaded only when inspected, checked against the product's SHA-256, bounded to 1 MB and cached for at most six contexts in the browser. The result manifest contains references rather than every stamp array. The observation selector pages 25 candidates at a time. The displayed input-size estimate is approximate, before cache reuse; it is not a network-transfer guarantee.

## API contracts

`POST /v1/source-fields` accepts this JSON and returns HTTP 202 with `job_id` and `status_url`:

```json
{
  "source": {
    "name": "P330E",
    "ra": 247.8908392831,
    "dec": 30.14604947207,
    "pmra": -8.882,
    "pmdec": -38.705,
    "ref_epoch": 2016
  },
  "start_utc": "2025-07-01",
  "end_utc": "2025-07-31",
  "include_deep": true,
  "refresh": false
}
```

Coordinates are ICRS degrees, RA in [0,360), declination in [-90,90]. `pmra` includes cos(dec); both components must be present together, in mas/year, with absolute values at most 12,000. The reference epoch is a TCB Julian year in [1900,2100]. A request without motion measures the same ICRS position at every acquisition. Observer parallax and perspective acceleration remain omitted. Source labels are bounded to 100 characters and exclude control characters. Dates are increasing, span at most five years, and are resolved to concrete values before queue persistence.

The discovery cone encloses the supplied angular trajectory with a 60-arcsecond margin. SIA TIME filtering is followed by an explicit acquisition-midpoint filter: start-date midnight inclusive through midnight after the end date exclusive. The four queried collections, when requested, are `spherex_dr1`, `spherex_qr3`, `spherex_dr1_deep` and `spherex_qr3_deep`. Collection availability does not mean native extraction is approved for that release. Only exact approved DR1 processing/calibration inputs currently pass that gate. SIA overflow remains visible.

`GET /v1/analysis/jobs/{job_id}` returns persisted state, error and eventual `result_id`. `DELETE` requests cancellation. `GET /v1/products/{result_id}` returns a frozen `type: source_field` manifest containing source, resolved request, time bounds, original discovery metadata, indexed observation records and the complete approved calibration-registry snapshot. Its identity includes these scientific inputs, not just a display label or job ID.

`POST /v1/native-source-samples` accepts:

```json
{
  "field_id": "<64 lowercase hex characters from source_field.id>",
  "observation_indices": [4, 7, 61, 62, 95, 110, 111],
  "method": "psf",
  "centroid_mode": "auto",
  "aperture_radius": 2.5,
  "background_inner": 5,
  "background_outer": 8,
  "refresh": false
}
```

Those example indices belong to the live-query field recorded in `artifacts/native-workflow-public-field.json`; indices are not stable across a new discovery. Choose records from the returned manifest. The API rejects absent/wrong-type fields, unknown or duplicate indices, selections beyond 512 and releases without approved native calibration. Selection order is canonicalized for deduplication. Refresh creates a new server-controlled attempt; it does not change a saved field's observations or calibration snapshot. `centroid_mode: auto` refines only when the initial fixed fit has S/N at least 20 and the bounded fit meets the kernel's positional-error gate; other samples retain the supplied conditional position. `fixed` never requests refinement. The same bounds and ordering constraints on aperture/background geometry apply as in the native kernel.

Jobs share the existing two-worker pool and persistent SQLite queue. At most ten logical nonterminal analysis requests are admitted. Recovery replays the persisted payload; it does not replace today's saved date defaults with tomorrow's date. Cancellation is checked between native inputs and processing stages. An in-progress external HTTP call is not immediately interrupted. Immutable scientific identities include source, options, selected field/observation context, native/calibration checksums, software policies, results and stamp checksums. Existing results remain readable after an upstream failure.

The final `type: source_samples` manifest identifies samples as `obs_id/Dn`, allowing simultaneous observations on different detectors without conflating them. Sampling metadata reports accepted, diagnostic, rejected, available and unselected observations and the discovery completeness. Native inspection files use `/v1/products/{id}/sample-{index}.json`, with indices 0–511. Table/plot routes are `/samples.csv`, `/samples.ecsv` and `/plot.svg`. Check the manifest's URLs and hashes; filenames do not establish scientific identity.

Browser URLs support `field=`, `job=` or immutable `samples=` plus selected `sample=` and quality view. Source-entry links support `source_ra`, `source_dec`, `source_name`, and paired `pmra`, `pmdec`, `ref_epoch`. Motion fields survive reload. Unknown/invalid links produce recoverable errors. A saved product can remain readable when its discovery parent is unavailable; resubmission then requires rediscovery.

## Verified availability and fallback boundary

Actual November 15 requests are recorded in `artifacts/native-query-availability.json`. The official SIA example and several P177D queries returned HTTP 502; both inspected SPHEREx TAP metadata/point-query responses also contained HTTP 502 HTML. The retained P330E broad SIA URI returned HTTP 200 with a VOTable. These observations demonstrate query-specific failures, not a universal archive outage or a validated P177D workflow. No successful measurements for P177D are claimed.

When live discovery raises an HTTP/transport exception, a retained snapshot may supply candidates only if its recorded cone encloses the entire new cone, its original time bounds contain the requested interval, it has dated official IRSA query provenance, and its data structure is valid. A query for another sky region cannot supply fallback candidates. The fallback always reports `retained_metadata_snapshot`, `limited`, its original query date/completeness and the failed query. It does not establish new ingestion, unqueried deep collections or a current complete inventory. A fresh search button can retry the provider. Failed VO queries or invalid query responses are not silently converted to success.

The earlier local HTTP workflow found 150 July DR1 candidates using the explicit retained P330E snapshot. Selecting seven authentic exposures produced six passing PSF measurements, one on each detector, and one authentic missing-coverage rejection. Later, at 13:42 UTC, the actual date-bounded P330E query recovered: all four requested collection queries completed without overflow and returned 147 DR1 candidates. The smaller query correctly excludes the uncovered reference exposure from the broader snapshot. Public acceptance therefore selects the six passing exposures plus a covered D2 input whose residual score exceeds the unchanged maximum of 3. Its measurement remains diagnostic-only and stays out of the accepted plot. The native missing-coverage regression is retained separately. `artifacts/native-workflow-public-field.json`, public-product.json and public-api.json retain this actual query, seven-input reduction and exact scientific-download checksums.

The six-detector CALSPEC consistency benchmark retains its unchanged numerical bounds. This is end-to-end evidence for P330E, not a survey-wide validation of arbitrary crowded/extended/variable sources or fresh discovery in every sky region. The earlier P177D query failures remain evidence of those attempts; P330E recovery does not establish P177D availability.

## Resource and operational limits

Archive binary publication is atomic and uses a single-instance lock with a default 5-GiB source-cache quota (`VANTAGE_SOURCE_CACHE_BYTES`). Existing science inputs are retained; a full cache rejects new binary publication instead of evicting inputs underneath a result. In-flight temporary bytes are counted. This is not a global/multiprocess storage quota; metadata, result products, logs, retention/cleanup, rate limits and a complete disk/memory budget remain operational work. No durable cloud backend has been provisioned by this slice. A laptop-backed tunnel is a temporary preview.

Remaining scientific/product requirements include channel/epoch-aware coverage, validated binning and upper limits, additional isolated calibration fields, release promotion/rollback, broader response validation, and crowded/extended-source policies. No native correlated-noise, common calibration, ePSF-model or position-prior uncertainty has been invented. The errors remain conditional statistical estimates described in the numerical methods.

Primary implementation references: [IRSA SIA parameters and TIME](https://irsa.ipac.caltech.edu/ibe/sia.html), [SPHEREx access and collections](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/), [native data/calibration products](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/), [official source-discovery notebook](https://caltech-ipac.github.io/irsa-tutorials/spherex-source-discovery-tool-demo/), [STScI CALSPEC](https://www.stsci.edu/hst/instrumentation/reference-data-for-calibration-and-tools/astronomical-catalogs/calspec.html). Current code contracts are in `backend/source_fields.py`, `backend/native_extraction.py`, `backend/product_jobs.py` and `/openapi.json` on the running backend.
