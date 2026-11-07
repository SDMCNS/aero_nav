"""
Command-line interface for the Aviation Navaid Simulation Library.
Allows launching the FastAPI server, running headless simulation,
or inspecting database facilities and scenarios.
"""

import argparse
import sys
import time

from navaid_sim.database.loader import AirspaceDatabase
from navaid_sim.scenarios.runner import ScenarioRunner
from navaid_sim.scenarios.definitions import ALL_SCENARIOS


def main():
    parser = argparse.ArgumentParser(
        description="✈️ Aviation Navaid & Cockpit Avionics Simulator CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Launch FastAPI REST & WebSocket server")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    serve_parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    # List scenarios
    subparsers.add_parser("scenarios", help="List available flight scenarios")

    # Headless simulation
    run_parser = subparsers.add_parser("run", help="Run scenario headlessly in console")
    run_parser.add_argument(
        "--scenario",
        default="a320_shannon_arrival",
        choices=list(ALL_SCENARIOS.keys()),
        help="Scenario ID to run",
    )
    run_parser.add_argument("--speed", type=float, default=5.0, help="Simulation speed multiplier")
    run_parser.add_argument("--steps", type=int, default=30, help="Number of telemetry cycles to output")

    # Inspect facilities
    subparsers.add_parser("facilities", help="List all parsed navaids and airports in Irish airspace")

    args = parser.parse_args()

    if args.command == "serve":
        import uvicorn
        print(f"🚀 Starting Navaid Simulation Server at http://{args.host}:{args.port}")
        uvicorn.run("navaid_sim.server:app", host=args.host, port=args.port, reload=args.reload)

    elif args.command == "scenarios":
        print("\n=== AVAILABLE FLIGHT SCENARIOS ===")
        for sc_id, sc in ALL_SCENARIOS.items():
            print(f"\n[{sc_id}] - {sc.title}")
            print(f"  Aircraft: {sc.aircraft_type} ({sc.callsign}) | Level: {sc.flight_level}")
            print(f"  Route: {sc.departure} -> {sc.destination}")
            print(f"  Summary: {sc.summary}")
            print(f"  Avionics Focus: {sc.avionics_focus}")
            print(f"  Waypoints ({len(sc.waypoints)}): " + " -> ".join(w.name for w in sc.waypoints))

    elif args.command == "facilities":
        db = AirspaceDatabase(".")
        print(f"\n=== IRISH AIRSPACE BOUNDARIES ({len(db.fir_boundaries)}) ===")
        for b_id, b in db.fir_boundaries.items():
            print(f"  {b_id}: FL{b.min_fl} to FL{b.max_fl} ({len(b.coordinates)} vertices)")

        print(f"\n=== AIRPORTS ({len(db.airports)}) ===")
        for ap_id, ap in db.airports.items():
            rwys = ", ".join(f"RWY {r.designation} ({r.magnetic_bearing_deg:.0f}°M)" for r in ap.runways)
            print(f"  {ap_id} - {ap.name} (Elev: {ap.elevation_ft:.0f}ft, Var: {ap.magnetic_variation})")
            print(f"    Runways: {rwys}")

        print(f"\n=== RADIO NAVIGATION AIDS ({len(db.navaids)}) ===")
        for k, n in sorted(db.navaids.items()):
            rwy_info = f" [RWY {n.runway_id}]" if n.runway_id else ""
            print(f"  {n.id:<5} {n.type:<10} {n.freq_mhz or 0:>7.2f} MHz | {n.name:<30}{rwy_info} (DOC: {n.doc_range_nm:.0f}NM)")

    elif args.command == "run":
        db = AirspaceDatabase(".")
        runner = ScenarioRunner(db)
        runner.load_scenario(args.scenario)
        runner.play()
        runner.set_speed_multiplier(args.speed)

        print(f"\n▶ Executing {args.scenario} at {args.speed}x speed...")
        print(f"Departure: {runner.active_scenario.departure} | Destination: {runner.active_scenario.destination}\n")

        for step in range(args.steps):
            snap = runner.step(dt_real_sec=0.5)
            ac = snap["telemetry"]["aircraft"]
            nav1 = snap["telemetry"]["nav1"]
            dme1 = snap["telemetry"]["dme1"]
            target_wp = snap["scenario"]["target_waypoint_name"]

            nav1_str = "N/A"
            if nav1["mode"] == "VOR" and nav1["evaluation"]:
                nav1_str = f"VOR {nav1['station']['id']} R-{nav1['evaluation']['radial_deg']:.0f}° CDI:{nav1['evaluation']['cdi_deflection_dots']:+.1f} {nav1['evaluation']['to_from_flag']}"
            elif nav1["mode"] == "ILS" and nav1["evaluation"]:
                nav1_str = f"ILS {nav1['station']['id']} LOC:{nav1['evaluation']['loc_deflection_dots']:+.1f} GS:{nav1['evaluation']['gp_deflection_dots']:+.1f}"

            dme_str = f"DME: {dme1['evaluation']['slant_range_nm']:.1f}NM" if dme1.get("evaluation") else "DME: ---"

            print(f"[{ac['flight_phase']:<16}] Pos: {ac['lat']:.4f}°N {ac['lon']:.4f}°W | Alt: {ac['altitude_ft']:>5.0f}ft | HDG: {ac['magnetic_heading_deg']:>3.0f}° | GS: {ac['groundspeed_kts']:>3.0f}kt | Next: {target_wp:<10} | {nav1_str} | {dme_str}")
            time.sleep(0.1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

