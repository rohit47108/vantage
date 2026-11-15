import type { Frame, Plane } from "./types";

export function PixelInspector({
  plane,
  frame,
  pixel,
}: {
  plane: Plane;
  frame: Frame;
  pixel: number[];
}) {
  const [x, y] = pixel;
  return (
    <dl aria-label="Inspected pixel measurements">
      <dt>Inspected acquisition</dt>
      <dd>{frame.utc_mid}</dd>
      <dt>ICRS · degrees</dt>
      <dd>
        {plane.ra[y][x].toFixed(6)}, {plane.dec[y][x].toFixed(6)}
      </dd>
      <dt>Surface brightness · MJy/sr</dt>
      <dd>{plane.brightness[y][x]?.toPrecision(6) ?? "No data"}</dd>
      <dt>Pixel wavelength · µm</dt>
      <dd>{plane.wavelength[y][x]?.toFixed(6) ?? "No data"}</dd>
      <dt>Flags · nearest pixel</dt>
      <dd>{plane.coverage[y][x] ? plane.flags[y][x] : "No data"}</dd>
      <dt>Interpolated support</dt>
      <dd>
        {plane.quality[y][x]
          ? "Usable visual support"
          : "Defect or missing contributor"}
      </dd>
    </dl>
  );
}
