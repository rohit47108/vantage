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
      <p>
        Gaia circles are imported optical catalog positions, moved to each
        SPHEREx acquisition using angular proper motion where available.
        Observer parallax and perspective acceleration are omitted. AllWISE
        diamonds keep their historical infrared catalog positions; W1/W2 mean
        MJDs describe the observation sampling, not an exact positional epoch.
        Nearby Gaia / WISE pairs are candidates, including possible blends.
        These catalog values cannot be subtracted from SPHEREx brightness.
      </p>
      <p><a href="https://gea.esac.esa.int/archive/documentation/GDR3/Miscellaneous/sec_credit_and_citation_instructions/">Gaia credit and citation instructions</a> · <a href="https://irsa.ipac.caltech.edu/docs/knowledgebase/general.html">WISE / IRSA acknowledgments</a></p>
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
