"""
Aircraft state and 6-DOF kinematics representation.
Tracks geodetic position, flight dynamics, autopilot guidance vectors, and flight phases.
"""

import math
from dataclasses import dataclass, field
from typing import Optional

from navaid_sim.core.geo import destination_point, get_regional_magnetic_variation


@dataclass
class AircraftState:
    callsign: str = "EI-NAV"
    aircraft_type: str = "A320"
    lat: float = 52.7019
    lon: float = -8.9247
    altitude_ft: float = 3000.0
    groundspeed_kts: float = 220.0
    true_airspeed_kts: float = 220.0
    vertical_speed_fpm: float = 0.0
    true_heading_deg: float = 236.0
    magnetic_heading_deg: float = 240.0
    pitch_deg: float = 1.5
    roll_deg: float = 0.0
    wind_speed_kts: float = 15.0
    wind_dir_deg: float = 260.0
    transponder_code: str = "7000"
    flight_phase: str = "CRUISE"  # CLIMB, CRUISE, DESCENT, APPROACH, FINAL, TOUCHDOWN

    def update_magnetic_heading(self):
        mag_var = get_regional_magnetic_variation(self.lat, self.lon)
        self.magnetic_heading_deg = (self.true_heading_deg - mag_var + 360.0) % 360.0

    def step_kinematics(
        self,
        dt_sec: float,
        target_hdg_deg: Optional[float] = None,
        target_alt_ft: Optional[float] = None,
        target_speed_kts: Optional[float] = None,
    ):
        """
        Advances aircraft position and dynamics over time step dt_sec (seconds).
        Applies standard rate turns (~3 deg/sec max), vertical climbs/descents, and speed changes.
        """
        # Heading rate limit (Standard rate turn = 3 deg/sec)
        if target_hdg_deg is not None:
            hdg_diff = (target_hdg_deg - self.true_heading_deg + 540.0) % 360.0 - 180.0
            turn_rate_max = 3.0 * dt_sec
            if abs(hdg_diff) <= turn_rate_max:
                self.true_heading_deg = target_hdg_deg
                self.roll_deg = 0.0
            else:
                turn_dir = 1.0 if hdg_diff > 0 else -1.0
                self.true_heading_deg = (self.true_heading_deg + turn_dir * turn_rate_max + 360.0) % 360.0
                # Bank angle proportional to turn
                self.roll_deg = round(turn_dir * min(25.0, abs(hdg_diff) * 1.5), 1)
        else:
            self.roll_deg = 0.0

        self.update_magnetic_heading()

        # Altitude rate
        if target_alt_ft is not None:
            prev_alt = self.altitude_ft
            alt_diff = target_alt_ft - self.altitude_ft

            max_climb = 2500.0
            max_desc = -2000.0
            desired_vs = alt_diff * 4.0
            target_vs = max(max_desc, min(max_climb, desired_vs))
            vs_step = target_vs * (dt_sec / 60.0)

            if abs(vs_step) >= abs(alt_diff):
                self.altitude_ft = target_alt_ft
            else:
                self.altitude_ft += vs_step

            if dt_sec > 0:
                actual_vs = ((self.altitude_ft - prev_alt) / dt_sec) * 60.0
                self.vertical_speed_fpm = round(actual_vs, 1)
            self.pitch_deg = round(2.5 if self.vertical_speed_fpm > 100 else (-2.0 if self.vertical_speed_fpm < -100 else 1.0), 1)

        # Speed adjustment
        if target_speed_kts is not None:
            speed_diff = target_speed_kts - self.groundspeed_kts
            accel_rate = 2.0 * dt_sec  # 2 kts/sec
            if abs(speed_diff) <= accel_rate:
                self.groundspeed_kts = target_speed_kts
            else:
                self.groundspeed_kts += math.copysign(accel_rate, speed_diff)
            self.true_airspeed_kts = self.groundspeed_kts

        # Distance traveled in nautical miles
        dist_nm = (self.groundspeed_kts / 3600.0) * dt_sec

        # Advance position along Great Circle
        new_lat, new_lon = destination_point(self.lat, self.lon, self.true_heading_deg, dist_nm)
        self.lat = new_lat
        self.lon = new_lon

