"""
Scenario specifications and trajectory definitions using official Irish waypoints from IE_Waypoints.txt.
Contains 3 scenarios:
1. Long-Haul Transatlantic Oceanic Overflight (B77W, FL370)
2. Airbus A320 UK Arrival into Shannon via ILS RWY 24 (A320, FL240 to Touchdown)
3. Domestic City Hopper from Dublin to Shannon (AT76, FL160)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ScenarioWaypoint:
    name: str
    lat: float
    lon: float
    target_alt_ft: float
    target_speed_kts: float
    phase: str
    nav1_tune: Optional[str] = None
    nav1_obs: Optional[float] = None
    dme1_tune: Optional[str] = None
    adf1_tune: Optional[str] = None
    briefing_note: str = ""


@dataclass
class ScenarioDefinition:
    id: str
    title: str
    aircraft_type: str
    callsign: str
    summary: str
    flight_level: str
    departure: str
    destination: str
    airspace_context: str
    avionics_focus: str
    initial_alt_ft: float
    initial_speed_kts: float
    waypoints: List[ScenarioWaypoint] = field(default_factory=list)


# 1. Transatlantic Long-Haul Overflight (BAW178)
# Uses official IE_Waypoints: GISTI (Oceanic Landfall), AGINI, SHA, TORLU, PELIG, DUB, LIPGO
SCENARIO_1_TRANSATLANTIC = ScenarioDefinition(
    id="long_haul_overflight",
    title="Transatlantic Oceanic Overflight (BAW178)",
    aircraft_type="B77W",
    callsign="BAW178",
    summary="Heavy commercial airliner crossing the Atlantic from Boston to London Heathrow, transiting through Shannon Upper Information Region (EISNUIR) at FL370.",
    flight_level="FL370 (37,000 ft AMSL)",
    departure="Oceanic Landfall (GISTI / IE_Waypoints)",
    destination="London FIR Boundary (LIPGO / IE_Waypoints)",
    airspace_context="Shannon UIR (FL245 - FL660) high-altitude oceanic transition into continental upper airspace.",
    avionics_focus="Long-range VOR/DME line-of-sight geometry (>150 NM at FL370), high-altitude DME slant-range altitude error (minimum 6.09 NM overhead SHA), multi-VOR cross-fixing, and GNSS RAIM integrity.",
    initial_alt_ft=37000.0,
    initial_speed_kts=480.0,
    waypoints=[
        ScenarioWaypoint(
            name="GISTI",
            lat=53.0000,
            lon=-14.0000,
            target_alt_ft=37000.0,
            target_speed_kts=480.0,
            phase="OCEANIC_ENTRY",
            nav1_tune="SHA",
            nav1_obs=84.0,
            dme1_tune="SHA",
            adf1_tune="CML",
            briefing_note="Oceanic Landfall Point (GISTI). Intercepting Shannon SHA DVOR (113.3 MHz) Radial 264° inbound (OBS 084°). Distance ~180 NM.",
        ),
        ScenarioWaypoint(
            name="AGINI",
            lat=53.1556,
            lon=-8.5794,
            target_alt_ft=37000.0,
            target_speed_kts=480.0,
            phase="ENROUTE_CRUISE",
            nav1_tune="SHA",
            nav1_obs=84.0,
            dme1_tune="SHA",
            adf1_tune="CML",
            briefing_note="Passing waypoint AGINI (IE_Waypoints). Tuning Wolftrap DME (WTP 116.3 MHz) and Dublin DUB DVOR (114.9 MHz).",
        ),
        ScenarioWaypoint(
            name="TORLU",
            lat=52.9878,
            lon=-7.5831,
            target_alt_ft=37000.0,
            target_speed_kts=480.0,
            phase="ENROUTE_CRUISE",
            nav1_tune="DUB",
            nav1_obs=68.0,
            dme1_tune="WTP",
            adf1_tune="CML",
            briefing_note="Cruising over TORLU at FL370. Observe Wolftrap DME slant-range altitude error and cross-bearing with Clonmel CML NDB.",
        ),
        ScenarioWaypoint(
            name="PELIG",
            lat=53.1997,
            lon=-7.3333,
            target_alt_ft=37000.0,
            target_speed_kts=480.0,
            phase="ENROUTE_CRUISE",
            nav1_tune="DUB",
            nav1_obs=68.0,
            dme1_tune="DUB",
            adf1_tune="GMN",
            briefing_note="Overhead PELIG (Dublin FRA Fix). Intercepting Dublin DVOR 248° radial inbound to station.",
        ),
        ScenarioWaypoint(
            name="LIPGO",
            lat=53.0639,
            lon=-5.5000,
            target_alt_ft=37000.0,
            target_speed_kts=480.0,
            phase="FIR_EXIT",
            nav1_tune="DUB",
            nav1_obs=115.0,
            dme1_tune="DUB",
            adf1_tune="GMN",
            briefing_note="Exiting Shannon FIR/UIR at LIPGO (IE_Waypoints UK Boundary). Handoff to London Control.",
        ),
    ],
)


# 2. Airbus A320 Arrival to Shannon (EIN381)
# Uses official IE_Waypoints: SLANY (Irish Sea Entry), ABAGU, TIPUR, radar base-leg vector VECT24,
# followed by precision alignment onto Runway 24 extended centerline at 15 NM (CF24), 10 NM (IF24), 5 NM (FAF24),
# runway threshold, and touchdown zone on asphalt.
SCENARIO_2_A320_ARRIVAL = ScenarioDefinition(
    id="a320_shannon_arrival",
    title="Airbus A320 UK Arrival to Shannon (EIN381)",
    aircraft_type="A320",
    callsign="EIN381",
    summary="Scheduled Airbus A320 flight from London Heathrow arriving into Shannon Airport (EINN), tracking en-route VOR/NDB before executing radar base-leg vectoring onto the Runway 24 extended centerline for a stabilized CAT II precision ILS approach.",
    flight_level="FL240 descending to 15 ft (Shannon RWY 24)",
    departure="SLANY (IE_Waypoints / Irish Sea Entry)",
    destination="Shannon Airport (EINN / RWY 24)",
    airspace_context="Shannon FIR (EISNFIR) lower airspace descent and Shannon Terminal Control Area (TMA).",
    avionics_focus="Transition from en-route VOR/NDB navigation to terminal ILS Localizer/Glide Slope capture, RMI relative bearing tracking of Clonmel NDB, ARINC 429 Labels 173 and 174 deviation words, and DME to touchdown.",
    initial_alt_ft=24000.0,
    initial_speed_kts=290.0,
    waypoints=[
        ScenarioWaypoint(
            name="SLANY",
            lat=52.1586,
            lon=-5.8422,
            target_alt_ft=24000.0,
            target_speed_kts=290.0,
            phase="DESCENT_INITIATION",
            nav1_tune="SHA",
            nav1_obs=285.0,
            dme1_tune="SHA",
            adf1_tune="CML",
            briefing_note="Entering Shannon FIR at SLANY (IE_Waypoints). Cleared direct ABAGU, descending to FL120.",
        ),
        ScenarioWaypoint(
            name="ABAGU",
            lat=52.5033,
            lon=-7.6467,
            target_alt_ft=12000.0,
            target_speed_kts=250.0,
            phase="ENROUTE_DESCENT",
            nav1_tune="SHA",
            nav1_obs=270.0,
            dme1_tune="SHA",
            adf1_tune="CML",
            briefing_note="Passing waypoint ABAGU (IE_Waypoints) at 12,000 ft. Tracking Clonmel CML NDB (387 kHz) on RMI needle.",
        ),
        ScenarioWaypoint(
            name="TIPUR",
            lat=52.5892,
            lon=-8.1253,
            target_alt_ft=6000.0,
            target_speed_kts=210.0,
            phase="INITIAL_APPROACH",
            nav1_tune="SHA",
            nav1_obs=255.0,
            dme1_tune="SHA",
            adf1_tune="CML",
            briefing_note="Passing TIPUR (IE_Waypoints) descending to 6,000 ft. Shannon Radar vectoring south of Lough Derg toward terminal area.",
        ),
        ScenarioWaypoint(
            name="VECT24",
            lat=52.7200,
            lon=-8.3500,
            target_alt_ft=4000.0,
            target_speed_kts=185.0,
            phase="TERMINAL_RADAR_VECTOR",
            nav1_tune="ISW",
            nav1_obs=236.0,
            dme1_tune="SHA",
            adf1_tune="CML",
            briefing_note="Shannon Radar base leg vector heading 315° south of Lough Derg. Switching NAV1 to Shannon ILS RWY 24 (ISW 110.95 MHz). Cleared to descend to 3,000 ft to intercept localizer at 15 NM.",
        ),
        ScenarioWaypoint(
            name="CF24",
            lat=52.863337,
            lon=-8.581909,
            target_alt_ft=3000.0,
            target_speed_kts=170.0,
            phase="LOCALIZER_INTERCEPT",
            nav1_tune="ISW",
            nav1_obs=236.0,
            dme1_tune="SHA",
            adf1_tune="CML",
            briefing_note="Intercepting Runway 24 extended centerline at 15.0 NM on a 35° intercept angle. Localizer alive. Arming LOC capture mode.",
        ),
        ScenarioWaypoint(
            name="IF24",
            lat=52.812227,
            lon=-8.690520,
            target_alt_ft=3000.0,
            target_speed_kts=160.0,
            phase="LOCALIZER_CAPTURE",
            nav1_tune="ISW",
            nav1_obs=236.0,
            dme1_tune="SHA",
            adf1_tune="CML",
            briefing_note="10.0 NM Intermediate Fix. Established on Localizer centerline inbound heading 236°M (232° true). Level at 3,000 ft platform altitude to capture 3.0° Glide Path from below.",
        ),
        ScenarioWaypoint(
            name="FAF24",
            lat=52.761118,
            lon=-8.799131,
            target_alt_ft=1657.0,
            target_speed_kts=142.0,
            phase="FINAL_APPROACH",
            nav1_tune="ISW",
            nav1_obs=236.0,
            dme1_tune="SHA",
            adf1_tune="CML",
            briefing_note="Final Approach Fix (FAF 5.0 NM). Locked on 3.0° glide path at 1,657 ft AMSL (nominal sink rate -740 fpm). PAPI 2 White / 2 Red. Gear down, flaps full.",
        ),
        ScenarioWaypoint(
            name="RWY24_THR",
            lat=52.710008,
            lon=-8.907742,
            target_alt_ft=65.0,
            target_speed_kts=135.0,
            phase="THRESHOLD",
            nav1_tune="ISW",
            nav1_obs=236.0,
            dme1_tune="SHA",
            adf1_tune="CML",
            briefing_note="Runway 24 Threshold crossing at 50 ft TCH (65 ft AMSL). Initiating aerodynamic flare along runway centerline.",
        ),
        ScenarioWaypoint(
            name="EINN_RWY24",
            lat=52.708077,
            lon=-8.911847,
            target_alt_ft=15.0,
            target_speed_kts=120.0,
            phase="TOUCHDOWN",
            nav1_tune="ISW",
            nav1_obs=236.0,
            dme1_tune="SHA",
            adf1_tune="CML",
            briefing_note="Touchdown on Shannon Runway 24 centerline asphalt (15 ft AMSL, 1,200 ft down runway). Reverse thrust and rollout.",
        ),
    ],
)


# 3. City Hopper Dublin to Shannon (STK3211)
# Uses official IE_Waypoints & Shannon Terminal Procedures: EIDW, PELIG, TORLU, RIKUL, DW06, BASE06, CF06, IF06, FAF06, EINN
SCENARIO_3_CITY_HOPPER = ScenarioDefinition(
    id="city_hopper_dub_snn",
    title="Domestic Midlands City Hopper (STK3211)",
    aircraft_type="AT76",
    callsign="STK3211",
    summary="Regional turboprop flight departing Dublin Airport (EIDW), cruising across the Irish Midlands over Wolftrap DME, flying radar downwind vectors over Shannon Estuary, and executing a stabilized CAT I ILS precision approach to Runway 06.",
    flight_level="FL160 (Dublin to Shannon)",
    departure="Dublin Airport (EIDW / RWY 28L)",
    destination="Shannon Airport (EINN / RWY 06)",
    airspace_context="Dublin CTA departure, Shannon FIR Midlands airway, and Shannon TMA terminal radar maneuvering.",
    avionics_focus="Regional airway navigation, dual-VOR cross-bearings, Wolftrap standalone DME interrogation, ADF station tracking, terminal downwind vectoring, and CAT I ILS approach to EINN RWY 06 (ISE 109.5 MHz).",
    initial_alt_ft=242.0,
    initial_speed_kts=140.0,
    waypoints=[
        ScenarioWaypoint(
            name="EIDW_28L",
            lat=53.4215,
            lon=-6.2700,
            target_alt_ft=1500.0,
            target_speed_kts=150.0,
            phase="DEPARTURE_CLIMB",
            nav1_tune="DAP",
            nav1_obs=275.0,
            dme1_tune="DAP",
            adf1_tune="KLY",
            briefing_note="Airborne off Dublin Runway 28L. Climbing to 3,000 ft tracking Collinstown DAP DVOR/DME (111.2 MHz).",
        ),
        ScenarioWaypoint(
            name="PELIG",
            lat=53.1997,
            lon=-7.3333,
            target_alt_ft=10000.0,
            target_speed_kts=200.0,
            phase="ENROUTE_CLIMB",
            nav1_tune="BAL",
            nav1_obs=255.0,
            dme1_tune="BAL",
            adf1_tune="KLY",
            briefing_note="Passing waypoint PELIG (IE_Waypoints). Climbing through 10,000 ft to cruising level FL160.",
        ),
        ScenarioWaypoint(
            name="TORLU",
            lat=52.9878,
            lon=-7.5831,
            target_alt_ft=16000.0,
            target_speed_kts=230.0,
            phase="ENROUTE_CRUISE",
            nav1_tune="SHA",
            nav1_obs=240.0,
            dme1_tune="WTP",
            adf1_tune="CML",
            briefing_note="Cruising at FL160 over TORLU / Wolftrap DME (WTP 116.3 MHz). Observe DME slant-range altitude difference.",
        ),
        ScenarioWaypoint(
            name="RIKUL",
            lat=53.0578,
            lon=-8.3458,
            target_alt_ft=9000.0,
            target_speed_kts=210.0,
            phase="TERMINAL_DESCENT",
            nav1_tune="SHA",
            nav1_obs=240.0,
            dme1_tune="SHA",
            adf1_tune="CML",
            briefing_note="Waypoint RIKUL (IE_Waypoints 29 NM NE of Shannon). Shannon Radar descent clearance into TMA to 9,000 ft.",
        ),
        ScenarioWaypoint(
            name="DW06",
            lat=52.7800,
            lon=-8.9500,
            target_alt_ft=4000.0,
            target_speed_kts=180.0,
            phase="DOWNWIND_VECTOR",
            nav1_tune="ISE",
            nav1_obs=56.0,
            dme1_tune="SHA",
            adf1_tune="CML",
            briefing_note="Shannon Radar vectoring downwind north of Runway 06/24 on heading 233°. Descending to 4,000 ft. Switching NAV1 to Shannon ILS RWY 06 (ISE 109.5 MHz).",
        ),
        ScenarioWaypoint(
            name="BASE06",
            lat=52.4800,
            lon=-9.4500,
            target_alt_ft=3000.0,
            target_speed_kts=160.0,
            phase="BASE_LEG_TURN",
            nav1_tune="ISE",
            nav1_obs=56.0,
            dme1_tune="SHA",
            adf1_tune="CML",
            briefing_note="Turning base leg over Shannon Estuary. Turning left heading 060° to intercept Runway 06 extended centerline at 15.0 NM. Level at 3,000 ft platform altitude.",
        ),
        ScenarioWaypoint(
            name="CF06",
            lat=52.539883,
            lon=-9.269277,
            target_alt_ft=3000.0,
            target_speed_kts=150.0,
            phase="LOCALIZER_INTERCEPT",
            nav1_tune="ISE",
            nav1_obs=56.0,
            dme1_tune="SHA",
            adf1_tune="CML",
            briefing_note="Intercepting Runway 06 extended centerline at 15.0 NM (35° intercept angle). Localizer needle alive. Arming LOC capture mode.",
        ),
        ScenarioWaypoint(
            name="IF06",
            lat=52.590979,
            lon=-9.160691,
            target_alt_ft=3000.0,
            target_speed_kts=140.0,
            phase="LOCALIZER_CAPTURE",
            nav1_tune="ISE",
            nav1_obs=56.0,
            dme1_tune="SHA",
            adf1_tune="CML",
            briefing_note="10.0 NM Intermediate Fix Runway 06. Established on localizer centerline heading 056°M (052° true). Level at 3,000 ft to intercept 3.0° Glide Path from below.",
        ),
        ScenarioWaypoint(
            name="FAF06",
            lat=52.642076,
            lon=-9.052105,
            target_alt_ft=1688.0,
            target_speed_kts=130.0,
            phase="FINAL_APPROACH",
            nav1_tune="ISE",
            nav1_obs=56.0,
            dme1_tune="SHA",
            adf1_tune="CML",
            briefing_note="Final Approach Fix Runway 06 (FAF 5.0 NM). Locked on 3.0° glide path at 1,688 ft AMSL (nominal sink rate -690 fpm). PAPI 2 White / 2 Red. Gear down, flaps full.",
        ),
        ScenarioWaypoint(
            name="RWY06_THR",
            lat=52.693172,
            lon=-8.943519,
            target_alt_ft=96.0,
            target_speed_kts=120.0,
            phase="THRESHOLD",
            nav1_tune="ISE",
            nav1_obs=56.0,
            dme1_tune="SHA",
            adf1_tune="CML",
            briefing_note="Runway 06 Threshold crossing at 50 ft TCH (96 ft AMSL). Initiating aerodynamic flare along runway centerline.",
        ),
        ScenarioWaypoint(
            name="EINN_RWY06",
            lat=52.695104,
            lon=-8.939415,
            target_alt_ft=46.0,
            target_speed_kts=110.0,
            phase="TOUCHDOWN",
            nav1_tune="ISE",
            nav1_obs=56.0,
            dme1_tune="SHA",
            adf1_tune="CML",
            briefing_note="Touchdown on Shannon Runway 06 centerline asphalt (46 ft AMSL, 1,200 ft down runway). Reverse thrust and rollout.",
        ),
    ],
)

ALL_SCENARIOS: Dict[str, ScenarioDefinition] = {
    SCENARIO_1_TRANSATLANTIC.id: SCENARIO_1_TRANSATLANTIC,
    SCENARIO_2_A320_ARRIVAL.id: SCENARIO_2_A320_ARRIVAL,
    SCENARIO_3_CITY_HOPPER.id: SCENARIO_3_CITY_HOPPER,
}
