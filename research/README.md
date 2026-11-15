# Vantage research evidence

Historical research package. The application was built later; the statements below describe the research-only stage. Current live refreshes are under updates/2026-11-14 and current product progress is in ../tasks/product-evidence.md. Public repository copies retain native benchmark inputs, analysis scripts and small factual responses; downloaded upstream PDFs/HTML remain local references rather than being republished under the project MIT license.

Start with `../VANTAGE_RESEARCH_DOSSIER.md`. The shorter `../CODEX_HANDOFF_PACKET.md` is a separate copy of its final implementation specification. `../demo_dataset_manifest.json` lists exact source/derived files, byte sizes, hashes, observation identities and limitations. `../required_acknowledgments.txt` contains the complete official attribution text.

This directory contains **research probes and analysis, not an application**. No frontend, backend server, deployment, user account, or production scientific detector was built. The scripts establish archive/file behavior and produce research fixtures/plots; they are not a production pipeline or an instruction to execute downloaded notebook code.

## Dates and evidence levels

- Initial SIA/cutout/schema/browser checks: 4 October 2026 UTC.
- Additional precision-map, target, library and file checks: 12 October UTC.
- Final release/competition/library checks, motion fixtures, spacecraft ephemerides and source audit: 18 October evening America/New_York / 19 October UTC.
- Full challenge browser check, QR2/QR3 and DR1 checkpoint, five named target sequences and source refresh: 7 November UTC.
- Snapshot row counts are not permanent archive expectations. A metadata match is not a source detection. Screening centroids are not precision PSF-fit astrometry. No scientifically validated general difference-significance/candidate detector is supplied.
- Earlier unsuccessful probes remain evidence of failures. Prefer the latest named successful response when applying a contract; do not mistake a retained error VOTable for a current catalog.

## Files worth reading first

| Evidence | Purpose |
|---|---|
| `evidence/source_fetch_log.json`, `source_refresh_20261012.json`, `final_refresh.json` | Source URLs, dates, HTTP status, hashes and retained documentation |
| `evidence/dossier_source_link_audit.json` | Verification of the dossier's source pointers; notes an inaccessible linked Gaia credit document separately |
| `evidence/full_challenge_source_audit.json`, `full_current_challenge_visible.txt`, `full_current_faq_visible.txt` | November source access outcomes and exact official challenge/FAQ evidence |
| `evidence/full_sia_*_probe.json`, `full_sia_*.vot` | Two live collections across all five named fields, plus a DR1 test cone |
| `evidence/full_challenge_sequence_screening.json`, `full_challenge_calibration_associations.json` | Exact selected observations, native source-core checks and DataLink-to-map associations |
| `evidence/full_challenge_common_grid_audit.json`, `full_challenge_sequences_research.png` | Fixed-sky WCS and full-grid spectral/quality support diagnostics for the five target sequences |
| `evidence/full_dr1_landing.txt`, `full_dr1_s3.txt`, `full_dr1_doc.pdf`, `full_dr1_help_extract.txt` | Conflicting DR1 documentation and data-access observations |
| `evidence/sia_*_probe.json` and raw `.vot` | Query fields, units, status, timings and snapshot rows |
| `evidence/tap_*_schema.txt`, `tap_m101_join.txt` | Actual TAP schema and successful release-scoped ADQL join |
| `evidence/comet_datalink.vot` | Science image versus cutout descriptor and calibration associations |
| `evidence/most_ceres_id.vot`, `most_ceres_wide.vot` | Two-table MOST responses; final image matches versus ephemeris samples |
| `evidence/*_fits.json`, `m101_mosaic_hdus.json`, `epsf_d2_hdus.json` | Actual HDU layouts and headers |
| `evidence/m101_d2_precision_scan.json`, `m101_precision_pairs.json`, `m101_pair_coverage_audit.json` | Real temporal-pair selection and restricted wavelength-compatible footprint |
| `evidence/comet_d3_precision_scan.json`, `ceres_d2_precision_scan.json`, `*_precision_pairs.json` | Target-position wavelength checks; nearest-pixel versus bilinear methods are identified by the probes |
| `evidence/motion_fixture_screening.json`, `ceres_motion_measured.json` | Provisional native source checks and observed positional-motion screening |
| `evidence/horizons_spherex_lookup.json`, `horizons_*_spherex.json`, `spacecraft_ephemeris_summary.json` | Actual spacecraft identity/coverage and successful observer ephemerides |
| `evidence/native_crop_equivalence.json` | Native S3-section fallback equals IBE science/PSF/table data and WCS in the tested case |
| `evidence/library_repository_audit.json`, `library_final_refresh.json` | Maintenance/licenses and final selected-version refresh |
| `evidence/performance_microbenchmark.json` | Narrow local timing scope; not a deployment SLA |
| `evidence/repo_tutorials_spherex_*` | Actual official notebook/package source inspected; retain its BSD license attribution before reuse |
| `evidence/supplement.pdf`, `spectral_calibration_document.pdf` | Downloaded primary technical PDFs; text extracts and selected table renderings are alongside them |
| `evidence_inventory.csv` | Relative file paths, byte sizes and SHA-256 inventory |

## Research images

`ceres_motion_research.png` places two real cutouts on the same sky grid and explicitly prohibits a brightness-change interpretation because their wavelengths differ. `m101_coverage_research.png` illustrates field-dependent spectral compatibility. `*_epoch_*_screening.png` shows predictions and simple screening centroids in source-centered native cutouts. These are supporting scientific figures, not application mockups or simulated NASA observations.

`full_challenge_sequences_research.png` shows three exposures per target on a fixed TAN grid with one shared stretch per row. White outside the footprints is missing coverage. Orange markers locate predictions. The final panel in each row shows joint spectral and flag support before PSF support erosion.

## Reproducing a particular check

The research used Python 3.13.2 on Windows. `.venv/` was created for this research and inherited some system packages. `research_environment_snapshot.txt` records what was present; **it is not a clean production requirements lock**. The scientific packages actually exercised are identified in dossier M/Z. A fresh research environment needs requests, NumPy/SciPy, Astropy, PyVO, Astroquery, Reproject, Photutils, Matplotlib, fsspec and aiohttp. Use compatible pinned versions and verify imports; the handoff distinguishes tested versions from newer repository releases.

Run only the specific probe needed after reading it. Many scripts perform public network requests and can download calibrations or replace their own research evidence. Do not execute every script indiscriminately. Most helper paths resolve relative to the script, but early inline-research scripts may assume the workspace root as the current directory. Use the exact data in the manifest for deterministic offline tests.

Useful narrow checks from the workspace root:

```powershell
& .\research\.venv\Scripts\python.exe research\verify_native_crop.py
& .\research\.venv\Scripts\python.exe research\audit_m101_pair.py
& .\research\.venv\Scripts\python.exe research\audit_full_challenge_sequences.py
& .\research\.venv\Scripts\python.exe research\verify_deliverable_structure.py
```

The first makes public S3 range requests to reproduce the native-crop equality check. The second uses saved files for the field-compatibility audit. Other network scripts save actual errors as well as successes. Do not promote fixed retry thresholds, approximate centroids, raw TSV/VOTable parsing shortcuts, inherited environment dependencies, or research-only plot processing directly into production without the tests in dossier T.

The last two commands work offline with the saved fixtures. The structure verifier also updates the evidence inventory. `probe_full_challenge_targets.py` refreshes public discovery. `inspect_full_challenge_fields.py` performs the bounded network shortlist and retrieves new native fixtures if necessary. Run these only for an intentional new snapshot, since exposure selection can change with upstream metadata. Raw DataLink responses for the saved selections are under `evidence/full_datalink_*`.

## Reuse and packaging

The report is the architectural source of truth; actual source metadata and versioned scientific files govern measurements. Preserve upstream URLs, timestamps, checksums, release/calibration identity, units, native bounds, processing parameters and limitations when moving the research package to another implementation workspace. Large FITS/PDF fixtures should be distributed through a checksum-based artifact store or suitable large-file mechanism, not casually committed as ordinary source code. The local research environment is disposable and excluded by this directory's `.gitignore`.

No external message, competition submission, deployment or application publication was made. Current 2026 competition rules do not establish that this dossier is exempt from the pre-event-work restriction; the report records that policy boundary.
