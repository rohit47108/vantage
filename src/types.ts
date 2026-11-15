export interface Frame {
  obs_id: string;
  detector: number;
  utc_mid: string;
  mjd_mid: number;
  release: string;
  wavelength_um: number | null;
  bandwidth_um: number | null;
  prediction_pixel: number[] | null;
  asset: string;
  source_url: string;
  source_sha256: string;
  core_flag_bits: number[];
  finite_fraction: number;
}
export interface Sequence {
  id: string;
  key: string;
  name: string;
  center_deg: number[];
  fov_arcmin: number;
  frames: Frame[];
  data_status: string;
  science_status: string;
  mode: string;
  shape: number[];
  joint_support_fraction: number;
  limitations: string[];
  credits: string;
  numerical_products_authorized: boolean;
}
export interface Plane {
  shape: number[];
  pixels: (number | null)[][];
  brightness: (number | null)[][];
  coverage: number[][];
  quality: number[][];
  spectral: number[][];
  joint: number[][];
  wavelength: (number | null)[][];
  bandwidth: (number | null)[][];
  flags: number[][];
  ra: number[][];
  dec: number[][];
}

export interface Coverage {
  center_deg: number[];
  fov_arcmin: number;
  search_completeness: "complete" | "limited";
  data_status: "live" | "cached";
  observations: {
    obs_id: string;
    detector: number;
    release: string;
    mjd_mid: number;
    em_min_um: number;
    em_max_um: number;
  }[];
}
