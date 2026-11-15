import { useEffect, useRef } from "react";

export function Methods({
  credits,
  close,
}: {
  credits: string;
  close: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    dialog.current?.showModal();
    return () => previous?.focus();
  }, []);
  return (
    <dialog
      ref={dialog}
      className="modal"
      aria-labelledby="methods-title"
      onCancel={close}
    >
      <button onClick={close} autoFocus>
        Close
      </button>
      <h2 id="methods-title">Real observations. Visible limits.</h2>
      <p>
        Each frame is an authentic SPHEREx detector exposure aligned with
        celestial WCS. The shared asinh stretch preserves display continuity.
        Cyan marks joint wavelength, coverage and quality support. Amber marks
        defective support or a predicted locator.
      </p>
      <p>
        The scalar wavelength gate is 0.10 of the narrower bandwidth, with width
        ratio at most 1.10. Precision registration, PSF matching and uncertainty
        validation are required before numerical brightness comparisons.
        Calibrated pixel brightness includes modeled zodiacal foreground.
      </p>
      <p>
        Ceres shows positional motion at differing wavelengths. M101 shows a
        restricted spectral footprint. 3I/ATLAS thumbnails follow the source and
        have distinct celestial grids.
      </p>
      <p>
        Prepared examples use QR2. Current archive searches use DR1 and QR3.
        Playback delay represents observations per second, while date labels
        show actual irregular acquisition gaps.
      </p>
      <p>
        Source bit 21 is information about a known source. Other defects
        propagate through interpolation. A prediction marker indicates a catalog
        or ephemeris position, with no detection implied.
      </p>
      <pre>{credits}</pre>
      <a
        href="https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_qr.html"
        target="_blank"
        rel="noreferrer"
      >
        IRSA release documentation ↗
      </a>
    </dialog>
  );
}
