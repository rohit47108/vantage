# Project copy

## Description

Vantage makes NASA's SPHEREx infrared observations accessible through a web explorer. Visitors enter sky coordinates, retrieve real coverage and play dated images of the same fixed patch. They can inspect calibrated pixel values, compare frames, see quality and wavelength support, and share or export the exact view with its provenance.

Prepared examples cover Barnard's Star, Epsilon Indi B, WISE 0855, RW Aurigae and R Draconis. Ceres demonstrates positional motion, M101 demonstrates wavelength limits across a field, and separately tracked 3I/ATLAS thumbnails show a comet example. Scientific limits remain visible, including flagged cores, missing coverage, mismatched wavelengths and predicted positions.

## Data use

Prepared assets derive from checksummed QR2 detector exposures and spectral calibrations. Live discovery and processing use IRSA DR1 and QR3. The backend uses IMAGE, FLAGS and VARIANCE layers, primary celestial WCS and precision CWAVE/CBAND maps. It publishes aligned visual assets with source IDs, actual UTC/MJD dates, calibration hashes, masks and processing versions.

Relevant release DOIs are 10.26131/IRSA652, 10.26131/IRSA662 and 10.26131/IRSA678. Full acknowledgments appear in the application and exported manifests.

## AI and contribution disclosure

OpenAI Codex assisted with architecture, code generation, scientific preprocessing, testing, troubleshooting, deployment and documentation. NASA/IRSA provided observations, calibrations and archive documentation. Imagery derives from authentic observations. Add team members' actual individual contributions before submitting.

## Submission checks

Use the preview in IMPLEMENTATION_STATUS.md and DEMO.md for the walkthrough. Live processing currently depends on this computer and a temporary tunnel. Static prepared examples survive backend failure.

The official challenge objectives and optional considerations were reverified in Chrome on November 15, 2026 after other fetch methods failed. See NASA_DEMO_CHECKLIST.md for capabilities and remaining optional work. Submission-format limits and local judging guidance were not reverified during this demo deadline. Confirm those before submitting. No competition submission was made by this run.
