"""
Example script demonstrating headless programmatic execution of all 3 Irish FIR scenarios
using the reusable navaid_sim library.
"""

from navaid_sim.database.loader import AirspaceDatabase
from navaid_sim.scenarios.runner import ScenarioRunner
from navaid_sim.scenarios.definitions import ALL_SCENARIOS


def run_scenario_demo(scenario_id: str, db: AirspaceDatabase, max_steps: int = 50):
    runner = ScenarioRunner(db)
    runner.load_scenario(scenario_id)
    sc = runner.active_scenario
    assert sc is not None

    print("\n" + "=" * 80)
    print(f"SCENARIO: {sc.title} ({sc.callsign} - {sc.aircraft_type})")
    print(f"ROUTE   : {sc.departure} -> {sc.destination} [{sc.flight_level}]")
    print(f"FOCUS   : {sc.avionics_focus}")
    print("=" * 80)

    runner.set_speed_multiplier(10.0)
    runner.play()

    print(f"{'STEP':4s} | {'WAYPOINT':12s} | {'PHASE':18s} | {'ALT (FT)':8s} | {'MAG HDG':7s} | {'GS (KT)':7s} | {'NAV1 TUNED':10s}")
    print("-" * 80)

    for step_num in range(max_steps):
        if not runner.is_running:
            break
        snapshot = runner.step(dt_real_sec=0.5)
        ac = snapshot["telemetry"]["aircraft"]
        nav1 = snapshot["telemetry"]["nav1"]
        sc_info = snapshot["scenario"]

        wp_name = sc_info["target_waypoint_name"]
        nav1_st = nav1["station"]["id"] if nav1["station"] else "NONE"

        if step_num % 5 == 0 or not runner.is_running:
            print(
                f"{step_num:4d} | {wp_name:12s} | {ac['flight_phase']:18s} | "
                f"{ac['altitude_ft']:8.1f} | {ac['magnetic_heading_deg']:6.1f}° | "
                f"{ac['groundspeed_kts']:6.1f} | {nav1_st:10s}"
            )

    print(f"Demo complete for {scenario_id}. Current status: {runner.aircraft.flight_phase}")


def main():
    db = AirspaceDatabase()
    print("Loaded Irish Airspace Database:")
    print(f"- {len(db.fir_boundaries)} FIR Boundaries (EISNFIR, EISNUIR)")
    print(f"- {len(db.navaids)} Radio Navigation Aids")
    print(f"- {len(db.waypoints)} Waypoints (IE_Waypoints.txt)")
    print(f"- {len(db.airports)} Certified Aerodromes (EINN, EIDW, EICK)")

    for sc_id in ALL_SCENARIOS.keys():
        run_scenario_demo(sc_id, db, max_steps=25)


if __name__ == "__main__":
    main()

