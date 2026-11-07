"""
Electromagnetic wave propagation and avionics sensor physics.
Simulates radio line-of-sight, free-space path loss, DME slant-range geometry,
VOR cone of confusion, ILS Localizer/Glide Path lobe dynamics, and GNSS satellite DOP.
"""

import math
from typing import Tuple, Dict, Any, List


# Standard constants
C_MPS = 299792458.0  # Speed of light (m/s)
FEET_TO_METERS = 0.3048
METERS_TO_FEET = 3.28084
NM_TO_METERS = 1852.0
METERS_TO_NM = 1.0 / 1852.0


def radio_line_of_sight_nm(h_ac_ft: float, h_station_ft: float) -> float:
    """
    Computes effective radio horizon distance in NM accounting for standard
    atmospheric refraction (4/3 equivalent Earth radius model):
        D_LOS = 1.23 * (sqrt(h_aircraft) + sqrt(h_station))
    """
    h_ac = max(0.0, h_ac_ft)
    h_st = max(0.0, h_station_ft)
    return 1.23 * (math.sqrt(h_ac) + math.sqrt(h_st))


def free_space_path_loss_db(dist_nm: float, freq_mhz: float) -> float:
    """
    Calculates Free-Space Path Loss (FSPL) in decibels:
        FSPL = 20*log10(d_km) + 20*log10(f_MHz) + 32.44
    """
    if dist_nm <= 0.01:
        dist_nm = 0.01
    dist_km = dist_nm * 1.852
    return 20.0 * math.log10(dist_km) + 20.0 * math.log10(freq_mhz) + 32.44


def calculate_slant_range_nm(ground_dist_nm: float, alt_diff_ft: float) -> float:
    """
    Computes direct 3D line-of-sight slant range:
        R_slant = sqrt(D_ground^2 + (alt_diff_ft / 6076.115)^2)
    """
    alt_nm = abs(alt_diff_ft) / 6076.11548
    return math.sqrt(ground_dist_nm**2 + alt_nm**2)


def is_in_vor_cone_of_confusion(
    ground_dist_nm: float, alt_diff_ft: float, cone_half_angle_deg: float = 40.0
) -> bool:
    """
    Determines whether an aircraft is within the VOR/DVOR cone of confusion (overhead null zone).
    Above the ground station antenna, the vertical radiation pattern drops off drastically.
    An inverted cone of half-angle ~40° from vertical means:
        d_ground <= alt_nm * tan(half_angle)
    """
    if alt_diff_ft <= 100.0:
        return False
    alt_nm = alt_diff_ft / 6076.11548
    cone_radius_nm = alt_nm * math.tan(math.radians(cone_half_angle_deg))
    return ground_dist_nm < cone_radius_nm


def calculate_vor_deviation(
    radial_deg: float, obs_deg: float
) -> Tuple[float, str, bool]:
    """
    Calculates Course Deviation Indicator (CDI) deflection and TO/FROM flag:
    - Standard CDI full-scale deflection (5 dots) is +/- 10 degrees (2.0 deg/dot).
    - Returns:
        deflection_dots: float in range [-5.0, 5.0]
        to_from_flag: "TO", "FROM", or "OFF"
        in_ambiguity_zone: boolean (transiting 90 deg off-course)
    """
    # Angular difference between aircraft radial and selected OBS course
    # Normalized to [-180, 180]
    angle_diff = (radial_deg - obs_deg + 540.0) % 360.0 - 180.0

    # TO / FROM resolution
    # If the aircraft is on the FROM side (|diff| < 90), flying radial away
    # If |diff| > 90, flying TO the station
    abs_diff = abs(angle_diff)

    # Within +/- 1.5 degrees of 90 or 270 degrees is the ambiguity/warning zone
    if 88.5 <= abs_diff <= 91.5:
        to_from_flag = "OFF"
        in_ambiguity = True
    elif abs_diff < 90.0:
        to_from_flag = "FROM"
        in_ambiguity = False
    else:
        to_from_flag = "TO"
        in_ambiguity = False

    # CDI needle points toward the dialed course
    # For TO: error = (radial - (obs + 180))
    # Standard formula: deflection is proportional to track error
    if to_from_flag == "FROM":
        track_error = -angle_diff
    else:
        # TO flag: needle senses course toward station
        # heading toward station with OBS course dialed
        rev_radial = (radial_deg + 180.0) % 360.0
        track_error = -((rev_radial - obs_deg + 540.0) % 360.0 - 180.0)

    # 10 degrees is 5 dots (2 deg/dot)
    deflection_dots = max(-5.0, min(5.0, track_error / 2.0))

    return deflection_dots, to_from_flag, in_ambiguity


def calculate_ils_localizer_deviation(
    aircraft_bearing_from_threshold: float,
    runway_magnetic_heading: float,
    ground_dist_nm: float,
) -> Tuple[float, bool]:
    """
    Calculates ILS Localizer angular deviation and reception:
    - Standard LOC coverage: +/- 35° within 10 NM; +/- 10° up to 18-25 NM.
    - Full-scale deflection (5 dots) is +/- 2.5 degrees (0.5 deg/dot).
    - Returns (deflection_dots, is_valid_signal).
    """
    # Angular error between inbound runway centerline and aircraft bearing from threshold
    # Note: localizer antenna is situated at the departure end of runway, looking down centerline.
    # Angle of aircraft relative to inbound course:
    inbound_course = runway_magnetic_heading
    # Bearing from threshold to aircraft:
    delta_angle = (aircraft_bearing_from_threshold - ((inbound_course + 180.0) % 360.0) + 540.0) % 360.0 - 180.0

    # Coverage check
    abs_delta = abs(delta_angle)
    is_valid = False
    if ground_dist_nm <= 10.0 and abs_delta <= 35.0:
        is_valid = True
    elif ground_dist_nm <= 25.0 and abs_delta <= 10.0:
        is_valid = True

    # Needle deflects toward runway centerline
    # Full scale deflection = 2.5 degrees = 5 dots (0.5 deg/dot)
    track_error = -delta_angle
    deflection_dots = max(-5.0, min(5.0, track_error / 0.5))

    return deflection_dots, is_valid


def calculate_ils_glideslope_deviation(
    aircraft_alt_ft: float,
    threshold_alt_ft: float,
    ground_dist_to_touchdown_nm: float,
    nominal_gp_angle_deg: float = 3.0,
) -> Tuple[float, bool]:
    """
    Calculates ILS Glide Path angular deviation and reception:
    - Standard GP nominal angle: 3.0 degrees.
    - Full-scale deflection (5 dots) is +/- 0.7 degrees (0.14 deg/dot).
    - Coverage: 0.45 * theta (1.35°) to 1.75 * theta (5.25°) within 10 NM.
    - Returns (deflection_dots, is_valid_signal).
    """
    if ground_dist_to_touchdown_nm <= 0.05:
        return 0.0, False

    alt_diff_ft = aircraft_alt_ft - threshold_alt_ft
    if alt_diff_ft < 0:
        alt_diff_ft = 0.0

    dist_ft = ground_dist_to_touchdown_nm * 6076.11548
    current_angle_deg = math.degrees(math.atan2(alt_diff_ft, dist_ft))

    # Coverage check: within 10 NM and between 1.35° and 5.25°
    is_valid = (
        ground_dist_to_touchdown_nm <= 12.0
        and 1.35 <= current_angle_deg <= 6.0
    )

    # Angular deviation from nominal 3.0° glide path
    # Above glide path -> needle deflects DOWN (-); Below -> needle deflects UP (+)
    angle_error = nominal_gp_angle_deg - current_angle_deg
    # Full scale deflection = 0.7 degrees = 5 dots (0.14 deg/dot)
    deflection_dots = max(-5.0, min(5.0, angle_error / 0.14))

    return deflection_dots, is_valid


def calculate_ndb_relative_bearing(
    aircraft_hdg_deg: float, station_true_brg_deg: float
) -> float:
    """
    Computes relative bearing (RB) to NDB station:
        RB = (True Bearing - Aircraft Heading + 360) % 360
    """
    return (station_true_brg_deg - aircraft_hdg_deg + 360.0) % 360.0


def compute_gnss_dop_metrics(
    satellites: List[Dict[str, Any]]
) -> Dict[str, float]:
    """
    Computes realistic Dilution of Precision (DOP) metrics (HDOP, VDOP, PDOP)
    from a list of active satellites with elevation and azimuth angles.
    """
    active_sats = [s for s in satellites if s.get("elevation", 0) > 5.0 and s.get("tracked", True)]
    n = len(active_sats)
    if n < 4:
        return {"hdop": 99.9, "vdop": 99.9, "pdop": 99.9, "num_sats": n}

    # Construct geometry matrix G (Nx4)
    # Row i: [-cos(el)*sin(az), -cos(el)*cos(az), -sin(el), 1]
    g_matrix = []
    for s in active_sats:
        el_rad = math.radians(s["elevation"])
        az_rad = math.radians(s["azimuth"])
        g_matrix.append([
            -math.cos(el_rad) * math.sin(az_rad),
            -math.cos(el_rad) * math.cos(az_rad),
            -math.sin(el_rad),
            1.0,
        ])

    # G^T * G (4x4)
    gtg = [[0.0] * 4 for _ in range(4)]
    for i in range(4):
        for j in range(4):
            for row in g_matrix:
                gtg[i][j] += row[i] * row[j]

    # Invert 4x4 matrix using standard Gauss-Jordan
    try:
        inv = [[float(i == j) for j in range(4)] for i in range(4)]
        matrix = [row[:] for row in gtg]

        for col in range(4):
            pivot = matrix[col][col]
            if abs(pivot) < 1e-12:
                return {"hdop": 1.2, "vdop": 1.6, "pdop": 2.0, "num_sats": n}
            for j in range(4):
                matrix[col][j] /= pivot
                inv[col][j] /= pivot
            for r in range(4):
                if r != col:
                    factor = matrix[r][col]
                    for j in range(4):
                        matrix[r][j] -= factor * matrix[col][j]
                        inv[r][j] -= factor * inv[col][j]

        q11 = max(0.0, inv[0][0])
        q22 = max(0.0, inv[1][1])
        q33 = max(0.0, inv[2][2])

        hdop = round(math.sqrt(q11 + q22), 2)
        vdop = round(math.sqrt(q33), 2)
        pdop = round(math.sqrt(q11 + q22 + q33), 2)
        return {"hdop": hdop, "vdop": vdop, "pdop": pdop, "num_sats": n}

    except Exception:
        return {"hdop": 0.8, "vdop": 1.2, "pdop": 1.4, "num_sats": n}

