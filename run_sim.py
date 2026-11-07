"""
✈️ Irish FIR Navaid & Cockpit Avionics Simulator Launcher
Starts the Python FastAPI backend with real-time WebSocket telemetry
and serves the TypeScript avionics UI.
"""

import sys
import webbrowser
import uvicorn


def main():
    port = 8000
    host = "127.0.0.1"

    print("================================================================================")
    print("   ✈️  IRISH FIR NAVAID & COCKPIT AVIONICS SIMULATION SYSTEM")
    print(f"   Server listening at: http://{host}:{port}")
    print("   - ICAO Airspace: Shannon FIR (EISNFIR) & Shannon UIR (EISNUIR)")
    print("   - Airports: Shannon (EINN), Dublin (EIDW), Cork (EICK)")
    print("   - Scenarios: Long-Haul Overflight, A320 Shannon Arrival, City Hopper")
    print("   - Protocols: ARINC 429 (32-bit BNR/BCD) & NMEA 0183 ($GPGGA, $GPRMC)")
    print("================================================================================")

    # Launch browser after slight delay unless --no-browser passed
    if "--no-browser" not in sys.argv:
        try:
            import threading
            import time
            def open_browser():
                time.sleep(1.2)
                webbrowser.open(f"http://{host}:{port}")
            threading.Thread(target=open_browser, daemon=True).start()
        except Exception:
            pass

    uvicorn.run("navaid_sim.server:app", host=host, port=port, log_level="info", reload=True)


if __name__ == "__main__":
    main()

