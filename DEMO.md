# Vantage demo — production

Open **[vantage-spherex.vercel.app](https://vantage-spherex.vercel.app)**. The circular logo and descriptive tab title are retained.

## Prepare these tabs

- [Time viewer and all featured examples](https://vantage-spherex.vercel.app)
- [102-channel wavelengths](https://vantage-spherex.vercel.app/?view=wavelengths)
- [Actual P330E native measurements](https://vantage-spherex.vercel.app/?view=measure&samples=e52f4762907e229bf9ce2c3e1247d8f4b38456ec395010f2b7e7e02eeec2e915)
- [Backend health](https://vantage-spherex.vercel.app/v1/health) should show `status: ok`.

Saved products are authentic previously processed observations. Describe them as saved results. A new brightness trace took about 35–40 seconds in the measured examples; native extraction is asynchronous. Cached retrieval is not a new instantaneous reduction.

## Current demonstration, about three to four minutes

1. **Time:** start on WISE 0855. Enter RA `08h55m10.831s` and Dec `-7d14m42.53s`, choose **Search archive**, then open a returned sequence. Use **Examples** to show NASA's five named targets: Barnard's Star, Epsilon Indi B, WISE 0855, RW Aurigae and R Draconis. Play, pause, step and scrub. Actual gaps remain separate from playback speed.
2. **Intervals:** open Ceres and **Playback interval and groups**. Its UTC-day group retains two individual exposures across nearly five hours. Wavelengths differ, so demonstrate positional context rather than calibrated brightness variation.
3. **Compare/combine:** choose M101, then **A/B compare → Comparison display → Swipe**. Inspect both halves and change the divider/stretches. Share restores the pair; PNG export contains both inputs. Then use **Stack observations → Build weighted coadd** and show its science FITS/provenance. Swipe is not numerical subtraction; the actual coadd has visible response/PSF limits.
4. **Wavelengths:** use the wavelength tab. Select detector groups, show the two blank layers and build false color. Select a pixel, then **Trace pixel across wavelengths**. This is survey-combined visual brightness in MJy/sr without invented errors.
5. **Other surveys:** expand **Other telescopes · Gaia / WISE** in the time viewer. Toggle markers, opacity and selection. Epochs and candidate associations are labeled.
6. **Measured light:** use the P330E tab. Inspect native data, source/background/residual, statistical uncertainty and dates. Show all 102 coverage rows and CSV/ECSV export. This small reference measures six channels, not a complete instantaneous spectrum. Supported observations can be re-extracted if time permits.

For a shorter demo, prioritize steps 1–3 and the share/provenance export. A predicted locator is not a measured detection.

## Keep it running

Prepared images are served directly by Vercel. Live search, wavelength retrieval, catalogs and scientific jobs still depend on the Python service on this computer and its temporary tunnel. **Keep this computer awake and leave the backend/tunnel processes running.** This is not durable scientific hosting.

The configured backend is port 8000 through `cardiovascular-encoding-duo-prefix.trycloudflare.com`. A changed tunnel address requires updating the deployment rewrite. If an archive fails, retain its recovery message and use prepared examples or saved authentic measurements.

Do not claim a new discovery, validated temporal variability, a complete instantaneous spectrum or precision subtraction. PSF-matched subtraction, full detector-band broadband calibration, compact cross-site embedding, automated release promotion and durable hosting remain unfinished. See [NASA_DEMO_CHECKLIST.md](NASA_DEMO_CHECKLIST.md) and IMPLEMENTATION_STATUS.md for scope and release evidence.

## Historical temporal-only walkthrough

The sections below describe the earlier release; use the current walkthrough above for this demo.

## 60 seconds

1. Open the prepared WISE 0855 field and show its exact UTC acquisition date.
2. Enter RA `08h55m10.831s` and Dec `-7d14m42.53s`, then search the archive. Coverage comes from DR1/QR3 metadata.
3. Choose WISE 0855 and play its three prepared frames. Its predicted displacement is subpixel across this short interval.
4. Open Ceres and step A/B. The source shifts position. Different wavelengths prevent a brightness-change interpretation.
5. Open M101 and toggle Joint support. Cyan shows where wavelength, quality and coverage agree across frames.
6. Share the view and export provenance with source and calibration hashes.

## Three minutes

- First 45 seconds. Enter WISE coordinates, search coverage and show date, detector and wavelength controls. Open a prepared or cached live sequence.
- Next 35 seconds. Visit the five official targets. Explain flagged cores in Barnard's Star, RW Aurigae and R Draconis, and the unresolved Epsilon Indi Ba/Bb system.
- Next 30 seconds. Play, pause, step and scrub. Pan, zoom and change speed while acquisition gaps remain separately labeled.
- Next 25 seconds. Compare Ceres on the same sky grid. Show positional motion and the limited numerical-brightness scope.
- Next 20 seconds. Show M101's support overlay, inspect a pixel and compare frames with a synchronized camera.
- Next 15 seconds. Open 3I/ATLAS. These thumbnails follow the source and have different sky centers.
- Final 10 seconds. Share the view, export image/JSON and open Data & Methods.

## Rehearsal

Keep Python and the temporary tunnel running for live searches. Check `/v1/health`. Prepared examples were browser-tested through Vercel while the backend was stopped. If an unrelated query fails, retain its failure state and select an authentic prepared target. No new planet, orbit, validated infrared light curve or detection significance is claimed.
