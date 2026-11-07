"""Core mathematical, physical, and protocol modules."""

from .geo import (
    parse_dms_coord,
    great_circle_distance_bearing,
    destination_point,
    interpolate_great_circle,
    cross_track_distance,
    get_regional_magnetic_variation,
    EARTH_RADIUS_NM,
    FEET_PER_NM,
)
from .physics import (
    radio_line_of_sight_nm,
    free_space_path_loss_db,
    calculate_slant_range_nm,
    is_in_vor_cone_of_confusion,
    calculate_vor_deviation,
    calculate_ils_localizer_deviation,
    calculate_ils_glideslope_deviation,
    calculate_ndb_relative_bearing,
    compute_gnss_dop_metrics,
)
from .protocol import (
    encode_arinc429_vor_bearing,
    encode_arinc429_dme_distance,
    encode_arinc429_loc_deviation,
    encode_arinc429_gs_deviation,
    encode_arinc429_adf_bearing,
    encode_arinc429_nav_frequency,
    generate_nmea_sentences,
    to_morse_code,
)

__all__ = [
    "parse_dms_coord",
    "great_circle_distance_bearing",
    "destination_point",
    "interpolate_great_circle",
    "cross_track_distance",
    "get_regional_magnetic_variation",
    "EARTH_RADIUS_NM",
    "FEET_PER_NM",
    "radio_line_of_sight_nm",
    "free_space_path_loss_db",
    "calculate_slant_range_nm",
    "is_in_vor_cone_of_confusion",
    "calculate_vor_deviation",
    "calculate_ils_localizer_deviation",
    "calculate_ils_glideslope_deviation",
    "calculate_ndb_relative_bearing",
    "compute_gnss_dop_metrics",
    "encode_arinc429_vor_bearing",
    "encode_arinc429_dme_distance",
    "encode_arinc429_loc_deviation",
    "encode_arinc429_gs_deviation",
    "encode_arinc429_adf_bearing",
    "encode_arinc429_nav_frequency",
    "generate_nmea_sentences",
    "to_morse_code",
]

