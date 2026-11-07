"""
Example: Simulating VOR/DME navigation and ARINC 429 bus streaming using navaid_sim.
"""

from navaid_sim import AirspaceDatabase, AircraftState, AvionicsSuite

# 1. Initialize central database (bundled Irish FIR facilities)
db = AirspaceDatabase()
print(f"Airspace loaded: {len(db.fir_boundaries)} FIRs, {len(db.navaids)} Navaids, {len(db.waypoints)} Fixes")

# 2. Set up aircraft state (Cruising over the Midlands toward Shannon)
aircraft = AircraftState(
    callsign="EI-SIM",
    aircraft_type="A320",
    lat=53.00,
    lon=-7.50,
    altitude_ft=12000.0,
    groundspeed_kts=250.0,
    true_heading_deg=255.0,
)

# 3. Initialize Avionics Suite and tune stations
avionics = AvionicsSuite(db)
avionics.tune_nav1("SHA", obs_deg=255.0)  # Tune Shannon DVOR/DME
avionics.tune_adf1("CML")                 # Tune Clonmel NDB

# 4. Evaluate radio reception & telemetry
telemetry = avionics.evaluate_all(aircraft)

print("\n--- NAV1 VOR/DME TELEMETRY ---")
nav1 = telemetry["nav1"]
ev = nav1["evaluation"]
print(f"Station: {nav1['station']['name']} ({nav1['station']['frequency']})")
print(f"Computed Radial: {ev['radial_deg']:.1f}° Magnetic (OBS: {nav1['obs_deg']:.0f}°)")
print(f"CDI Deflection: {ev['cdi_deflection_dots']:+.2f} dots | Flag: {ev['to_from_flag']}")
print(f"Signal Strength: {ev['signal_strength_dbm']:.1f} dBm | SNR: {ev['snr_db']:.1f} dB")

print("\n--- DME SLANT RANGE ---")
dme = telemetry["dme1"]["evaluation"]
print(f"Ground Distance: {dme['ground_dist_nm']:.2f} NM")
print(f"Slant Range: {dme['slant_range_nm']:.2f} NM (Altitude diff: {dme['altitude_diff_ft']:.0f} ft)")
print(f"Groundspeed: {dme['groundspeed_readout_kts']:.0f} KTS | Time to Station: {dme['time_to_station_min']:.1f} MIN")

print("\n--- ARINC 429 DIGITAL BUS WORDS ---")
for word in telemetry["arinc429_bus"]:
    print(f"  LBL {word['label_octal']:<3} | Hex: {word['raw_hex']} | {word['parameter']:<20}: {word['decoded_value']} {word.get('units', '')}")

print("\n--- NMEA 0183 SENTENCE ---")
print("  " + telemetry["nmea_0183"]["GGA"])

