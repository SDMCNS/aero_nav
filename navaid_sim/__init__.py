"""
Aviation Navaid & Cockpit Avionics Simulation Library.
Irish Flight Information Region (EISNFIR / EISNUIR) high-fidelity navigation physics,
avionics receiver suite, and scenarios.
"""

from .core.geo import (
    parse_dms_coord,
    great_circle_distance_bearing,
    destination_point,
    interpolate_great_circle,
    cross_track_distance,
    get_regional_magnetic_variation,
)
from .core.physics import (
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
from .core.protocol import (
    encode_arinc429_vor_bearing,
    encode_arinc429_dme_distance,
    encode_arinc429_loc_deviation,
    encode_arinc429_gs_deviation,
    encode_arinc429_adf_bearing,
    encode_arinc429_nav_frequency,
    generate_nmea_sentences,
    to_morse_code,
)
from .database.loader import (
    AirspaceDatabase,
    NavaidRecord,
    RunwayRecord,
    AirportRecord,
    AirspaceBoundary,
    WaypointRecord,
)
from .models.aircraft import AircraftState
from .models.navaid import (
    VORStation,
    DMEStation,
    NDBStation,
    ILSStation,
    GNSSSystem,
    VOREvaluation,
    DMEEvaluation,
    NDBEvaluation,
    ILSEvaluation,
)
from .models.avionics import AvionicsSuite
from .scenarios.definitions import (
    ALL_SCENARIOS,
    SCENARIO_1_TRANSATLANTIC,
    SCENARIO_2_A320_ARRIVAL,
    SCENARIO_3_CITY_HOPPER,
    ScenarioDefinition,
    ScenarioWaypoint,
)
from .scenarios.runner import ScenarioRunner

__version__ = "3.0.0"

__all__ = [
    "AirspaceDatabase",
    "AircraftState",
    "AvionicsSuite",
    "ScenarioRunner",
    "VORStation",
    "DMEStation",
    "NDBStation",
    "ILSStation",
    "GNSSSystem",
    "ALL_SCENARIOS",
    "SCENARIO_1_TRANSATLANTIC",
    "SCENARIO_2_A320_ARRIVAL",
    "SCENARIO_3_CITY_HOPPER",
    "parse_dms_coord",
    "great_circle_distance_bearing",
    "destination_point",
    "radio_line_of_sight_nm",
    "calculate_slant_range_nm",
    "is_in_vor_cone_of_confusion",
    "calculate_vor_deviation",
    "calculate_ils_localizer_deviation",
    "calculate_ils_glideslope_deviation",
    "calculate_ndb_relative_bearing",
    "encode_arinc429_vor_bearing",
    "encode_arinc429_dme_distance",
    "encode_arinc429_loc_deviation",
    "encode_arinc429_gs_deviation",
    "encode_arinc429_adf_bearing",
    "generate_nmea_sentences",
    "to_morse_code",
]

