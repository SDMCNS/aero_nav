"""
Geodesy and coordinate mathematics for the Irish Flight Information Region (FIR).
Handles Great Circle navigation, Rhumb lines, DMS coordinate parsing,
and magnetic variation calculations.
"""

import math
import re
from typing import Tuple, Optional


# Earth radius in nautical miles (WGS-84 mean radius)
EARTH_RADIUS_NM = 3440.065
EARTH_RADIUS_KM = 6371.0088
FEET_PER_NM = 6076.11548


def parse_dms_coord(coord_input: any) -> Optional[Tuple[float, float]]:
    """
    Parses various DMS coordinate string formats used in aviation datasets:
    - 531759.6N 0062652.0W (DDMMSS.S[N/S] DDDMMSS.S[E/W])
    - 524207N 0085529W (DDMMSS[N/S] DDDMMSS[E/W])
    - 515026.19N 0082939.37W
    - Float tuple / list (lat, lon)
    """
    if coord_input is None:
        return None

    if isinstance(coord_input, (tuple, list)) and len(coord_input) == 2:
        return float(coord_input[0]), float(coord_input[1])

    coord_str = str(coord_input).strip().upper()
    if not coord_str:
        return None

    # Try matching standard aviation DMS format
    match = re.match(r"([0-9.]+)([NS])\s+([0-9.]+)([EW])", coord_str)
    if match:
        lat_part, lat_hemi, lon_part, lon_hemi = match.groups()

        lat_deg = float(lat_part[:2])
        lat_min = float(lat_part[2:4])
        lat_sec = float(lat_part[4:]) if len(lat_part) > 4 else 0.0
        lat = lat_deg + (lat_min / 60.0) + (lat_sec / 3600.0)
        if lat_hemi == "S":
            lat = -lat

        lon_deg = float(lon_part[:3])
        lon_min = float(lon_part[3:5])
        lon_sec = float(lon_part[5:]) if len(lon_part) > 5 else 0.0
        lon = lon_deg + (lon_min / 60.0) + (lon_sec / 3600.0)
        if lon_hemi == "W":
            lon = -lon

        return lat, lon

    # Decimal coordinates fallback e.g. "53.299, -6.447"
    try:
        parts = coord_str.replace(",", " ").split()
        if len(parts) == 2:
            return float(parts[0]), float(parts[1])
    except ValueError:
        pass

    return None


def great_circle_distance_bearing(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> Tuple[float, float]:
    """
    Computes Great Circle distance in Nautical Miles and initial true bearing in degrees [0, 360).
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    # Haversine formula
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    a = max(0.0, min(1.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    dist_nm = EARTH_RADIUS_NM * c

    # Initial bearing
    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - (
        math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    )
    bearing_deg = (math.degrees(math.atan2(y, x)) + 360.0) % 360.0

    return dist_nm, bearing_deg


def destination_point(
    lat: float, lon: float, bearing_deg: float, distance_nm: float
) -> Tuple[float, float]:
    """
    Calculates destination coordinates given start point, initial bearing (deg), and distance (NM).
    """
    angular_dist = distance_nm / EARTH_RADIUS_NM
    phi1 = math.radians(lat)
    lambda1 = math.radians(lon)
    theta = math.radians(bearing_deg)

    phi2 = math.asin(
        math.sin(phi1) * math.cos(angular_dist)
        + math.cos(phi1) * math.sin(angular_dist) * math.cos(theta)
    )
    lambda2 = lambda1 + math.atan2(
        math.sin(theta) * math.sin(angular_dist) * math.cos(phi1),
        math.cos(angular_dist) - math.sin(phi1) * math.sin(phi2),
    )

    dest_lat = math.degrees(phi2)
    dest_lon = (math.degrees(lambda2) + 540.0) % 360.0 - 180.0
    return dest_lat, dest_lon


def interpolate_great_circle(
    lat1: float, lon1: float, lat2: float, lon2: float, fraction: float
) -> Tuple[float, float]:
    """
    Interpolates a point along the great circle arc between two points at parameter fraction [0.0, 1.0].
    """
    if fraction <= 0.0:
        return lat1, lon1
    if fraction >= 1.0:
        return lat2, lon2

    phi1 = math.radians(lat1)
    lambda1 = math.radians(lon1)
    phi2 = math.radians(lat2)
    lambda2 = math.radians(lon2)

    delta_phi = phi2 - phi1
    delta_lambda = lambda2 - lambda1
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    a = max(0.0, min(1.0, a))
    d = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    if d < 1e-10:
        return lat1, lon1

    A = math.sin((1.0 - fraction) * d) / math.sin(d)
    B = math.sin(fraction * d) / math.sin(d)

    x = A * math.cos(phi1) * math.cos(lambda1) + B * math.cos(phi2) * math.cos(lambda2)
    y = A * math.cos(phi1) * math.sin(lambda1) + B * math.cos(phi2) * math.sin(lambda2)
    z = A * math.sin(phi1) + B * math.sin(phi2)

    new_phi = math.atan2(z, math.sqrt(x * x + y * y))
    new_lambda = math.atan2(y, x)

    return math.degrees(new_phi), (math.degrees(new_lambda) + 540.0) % 360.0 - 180.0


def cross_track_distance(
    lat_p: float, lon_p: float, lat_a: float, lon_a: float, lat_b: float, lon_b: float
) -> float:
    """
    Computes cross-track distance in NM from point P to the great circle path between A and B.
    Positive value indicates P is to the right of the course line, negative to the left.
    """
    dist_ap, brg_ap = great_circle_distance_bearing(lat_a, lon_a, lat_p, lon_p)
    _, brg_ab = great_circle_distance_bearing(lat_a, lon_a, lat_b, lon_b)

    delta_ang = math.radians(brg_ap - brg_ab)
    dist_ang = dist_ap / EARTH_RADIUS_NM

    xt_ang = math.asin(math.sin(dist_ang) * math.sin(delta_ang))
    return xt_ang * EARTH_RADIUS_NM


def get_regional_magnetic_variation(lat: float, lon: float) -> float:
    """
    Returns estimated magnetic variation (declination) in degrees for Ireland and adjacent airspace.
    Negative value = West variation (e.g. -3.0 means 3°W).
    Variation in Ireland generally ranges from ~2°W in the east to ~4°W in the far west.
    """
    # Linear approximation tailored for Irish FIR (lat 51 to 56, lon -12 to -5)
    # At lon -6 (Dublin): ~ -2.2°W
    # At lon -9 (Shannon): ~ -3.2°W
    # At lon -11 (Oceanic boundary): ~ -4.0°W
    base_var = -2.2 + (lon - (-6.0)) * 0.35 + (lat - 53.0) * 0.05
    return round(base_var, 2)

