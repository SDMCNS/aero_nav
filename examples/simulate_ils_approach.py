"""
Example: Simulating an ILS Precision Approach into Shannon Runway 24 using navaid_sim.
"""

import math
from navaid_sim import AirspaceDatabase, AircraftState, AvionicsSuite
from navaid_sim.core.geo import destination_point, get_regional_magnetic_variation

db = AirspaceDatabase()
avionics = AvionicsSuite(db)

# Tune Shannon ILS Runway 24 (ISW 110.95 MHz)
avionics.tune_nav1("ISW")
isw = db.navaids["EINN_ISW_24"]

print("=== SHANNON AIRPORT (EINN) ILS RWY 24 PRECISION APPROACH DESCENT ===")
print(f"{'DIST (NM)':<10} {'ALT (FT)':<10} {'LOC DEV':<12} {'GP DEV':<12} {'LOC DDM':<12} {'AUTOLAND'}")

thr_lat, thr_lon = isw.runway_thr_lat, isw.runway_thr_lon
mag_var = isw.declination
# Runway 24 magnetic heading: 236°M -> True heading: 236° + mag_var (e.g. 236 - 3.2 = 232.8°T)
# Outbound reciprocal from threshold: 232.8° - 180° = 52.8°T
true_inbound = (isw.runway_bearing_mag + mag_var + 360.0) % 360.0
true_outbound = (true_inbound + 180.0) % 360.0

# Simulate approach steps from 10 NM down to touchdown
distances = [10.0, 7.5, 5.0, 3.0, 1.0, 0.3]
for dist in distances:
    # 3.0° glide path nominal altitude: d * 6076.115 * tan(3°) + 46 ft
    nominal_alt = dist * 6076.115 * math.tan(math.radians(3.0)) + 46.0

    # Put aircraft on centerline with exact glideslope tracking
    ac_lat, ac_lon = destination_point(thr_lat, thr_lon, true_outbound, dist)

    aircraft = AircraftState(
        callsign="EIN381",
        aircraft_type="A320",
        lat=ac_lat,
        lon=ac_lon,
        altitude_ft=nominal_alt,
        groundspeed_kts=140.0,
        true_heading_deg=true_inbound,
    )

    t = avionics.evaluate_all(aircraft)
    nav1 = t["nav1"]["evaluation"]
    print(f"{dist:<10.1f} {nominal_alt:<10.0f} {nav1['loc_deflection_dots']:>+5.2f} dots {nav1['gp_deflection_dots']:>+5.2f} dots {nav1['loc_ddm']:>+7.4f} DDM   {'ARMED' if nav1['autoland_guidance_valid'] else 'WAITING'}")
