/**
 * TypeScript definitions matching backend avionics and scenario models.
 */

export interface AircraftTelemetry {
  callsign: string;
  type: string;
  lat: number;
  lon: number;
  altitude_ft: number;
  groundspeed_kts: number;
  true_airspeed_kts: number;
  true_heading_deg: number;
  magnetic_heading_deg: number;
  pitch_deg: number;
  roll_deg: number;
  vertical_speed_fpm: number;
  flight_phase: string;
  transponder_code: string;
}

export interface VOREvaluation {
  is_received: boolean;
  is_in_los: boolean;
  is_in_doc: boolean;
  is_in_cone_of_confusion: boolean;
  is_terrain_restricted: boolean;
  radial_deg: number;
  true_bearing_to_station: number;
  magnetic_bearing_to_station: number;
  cdi_deflection_dots: number;
  to_from_flag: 'TO' | 'FROM' | 'OFF';
  signal_strength_dbm: number;
  snr_db: number;
  morse_code: string;
  failure_flag: boolean;
}

export interface ILSEvaluation {
  is_received: boolean;
  loc_received: boolean;
  gp_received: boolean;
  loc_deflection_dots: number;
  gp_deflection_dots: number;
  loc_ddm: number;
  gp_ddm: number;
  runway_id: string;
  runway_bearing_mag: number;
  dist_to_touchdown_nm: number;
  height_above_threshold_ft: number;
  back_course: boolean;
  morse_code: string;
  autoland_guidance_valid: boolean;
}

export interface DMEEvaluation {
  is_received: boolean;
  is_in_los: boolean;
  is_in_doc: boolean;
  ground_dist_nm: number;
  slant_range_nm: number;
  altitude_diff_ft: number;
  channel: string;
  pulse_spacing_us: number;
  reply_freq_mhz: number;
  transponder_delay_us: number;
  groundspeed_readout_kts: number;
  time_to_station_min: number;
  lock_status: 'LOCKED' | 'SEARCHING' | 'UNAVAILABLE';
  signal_strength_dbm: number;
  morse_code: string;
}

export interface NDBEvaluation {
  is_received: boolean;
  relative_bearing_deg: number;
  qdm_magnetic_bearing: number;
  qdr_magnetic_bearing: number;
  true_bearing: number;
  dist_nm: number;
  field_strength_uv_m: number;
  audio_tone_hz: number;
  morse_code: string;
  advisory_night_effect: boolean;
}

export interface GNSSEvaluation {
  mode: string;
  satellites_tracked: number;
  satellites_total: number;
  hdop: number;
  vdop: number;
  pdop: number;
  hpl_meters: number;
  vpl_meters: number;
  raim_status: string;
  satellites: Array<{
    prn: string;
    constellation: string;
    azimuth: number;
    elevation: number;
    snr_db: number;
    tracked: boolean;
  }>;
  geodetic_lat: number;
  geodetic_lon: number;
  altitude_msl_ft: number;
  altitude_msl_m: number;
}

export interface ARINC429Word {
  raw_hex: string;
  raw_bin: string;
  label_octal: string;
  label_bits: string;
  sdi: number;
  sdi_bits: string;
  data_bits: string;
  ssm: number;
  ssm_name: string;
  parity: number;
  parameter?: string;
  decoded_value?: number;
  units?: string;
}

export interface ReceptionMatrixItem {
  id: string;
  name: string;
  type: string;
  freq: string;
  received: boolean;
  signal_dbm?: number;
  bearing_mag?: number;
  distance_nm?: number;
  dist_nm?: number;
  field_strength_uv?: number;
  rel_bearing?: number;
  in_cone?: boolean;
  restricted?: boolean;
  lock_status?: string;
}

export interface FullTelemetry {
  timestamp: string;
  aircraft: AircraftTelemetry;
  nav1: {
    mode: 'VOR' | 'ILS' | 'NONE';
    station: any;
    obs_deg: number;
    evaluation: VOREvaluation | ILSEvaluation | null;
  };
  nav2: {
    station: any;
    obs_deg: number;
    evaluation: VOREvaluation | null;
  };
  dme1: {
    station: any;
    evaluation: DMEEvaluation | null;
  };
  adf1: {
    station: any;
    evaluation: NDBEvaluation | null;
  };
  gnss: GNSSEvaluation;
  arinc429_bus: ARINC429Word[];
  nmea_0183: {
    GGA: string;
    RMC: string;
    GSA: string;
  };
  reception_matrix: ReceptionMatrixItem[];
}

export interface ScenarioWaypoint {
  name: string;
  lat: number;
  lon: number;
  target_alt_ft: number;
  target_speed_kts: number;
  phase: string;
  nav1_tune?: string;
  nav1_obs?: number;
  briefing_note: string;
  is_current: boolean;
  is_passed: boolean;
}

export interface ScenarioState {
  id: string;
  title: string;
  summary: string;
  flight_level: string;
  departure: string;
  destination: string;
  airspace_context: string;
  avionics_focus: string;
  current_waypoint_index: number;
  total_waypoints: number;
  target_waypoint_name: string;
  target_waypoint_note: string;
  is_running: boolean;
  speed_multiplier: number;
  manual_tune_overridden?: boolean;
  elapsed_time_sec: number;
  waypoints: ScenarioWaypoint[];
}

export interface SimSnapshot {
  scenario: ScenarioState;
  telemetry: FullTelemetry;
}

