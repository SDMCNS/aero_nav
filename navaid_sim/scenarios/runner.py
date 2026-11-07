"""
Scenario execution engine and trajectory simulator.
Advances aircraft kinematics along scenario flight plans, simulates autopilot guidance,
and coordinates radio tuning and digital avionics bus output.
"""

import math
from typing import Dict, Any, Optional, List

from navaid_sim.core.geo import (
    great_circle_distance_bearing,
    interpolate_great_circle,
    destination_point,
    cross_track_distance,
    get_regional_magnetic_variation,
)
from navaid_sim.database.loader import AirspaceDatabase
from navaid_sim.models.aircraft import AircraftState
from navaid_sim.models.avionics import AvionicsSuite
from navaid_sim.scenarios.definitions import (
    ALL_SCENARIOS,
    ScenarioDefinition,
    ScenarioWaypoint,
)


class ScenarioRunner:
    """Manages the real-time simulation of an active flight scenario."""

    def __init__(self, db: AirspaceDatabase):
        self.db = db
        self.avionics = AvionicsSuite(db)
        self.active_scenario: Optional[ScenarioDefinition] = None
        self.aircraft: AircraftState = AircraftState()

        self.current_wp_idx: int = 0
        self.last_auto_tuned_wp_idx: int = -1
        self.manual_tune_overridden: bool = False
        self.is_running: bool = False
        self.speed_multiplier: float = 1.0
        self.elapsed_time_sec: float = 0.0

        # Load default scenario
        self.load_scenario("a320_shannon_arrival")

    def load_scenario(self, scenario_id: str):
        aliases = {
            "1": "long_haul_overflight",
            "scenario-1": "long_haul_overflight",
            "scenario_1": "long_haul_overflight",
            "overflight": "long_haul_overflight",
            "2": "a320_shannon_arrival",
            "scenario-2": "a320_shannon_arrival",
            "scenario_2": "a320_shannon_arrival",
            "a320": "a320_shannon_arrival",
            "3": "city_hopper_dub_snn",
            "scenario-3": "city_hopper_dub_snn",
            "scenario_3": "city_hopper_dub_snn",
            "city_hopper": "city_hopper_dub_snn",
        }
        scenario_id = aliases.get(scenario_id, scenario_id)
        if scenario_id not in ALL_SCENARIOS:
            scenario_id = "a320_shannon_arrival"

        defn = ALL_SCENARIOS[scenario_id]
        self.active_scenario = defn
        self.current_wp_idx = 1 if len(defn.waypoints) > 1 else 0
        self.last_auto_tuned_wp_idx = 0
        self.manual_tune_overridden = False
        self.elapsed_time_sec = 0.0
        self.is_running = False

        first_wp = defn.waypoints[0]
        second_wp = defn.waypoints[1] if len(defn.waypoints) > 1 else first_wp

        _, initial_hdg = great_circle_distance_bearing(
            first_wp.lat, first_wp.lon, second_wp.lat, second_wp.lon
        )

        self.aircraft = AircraftState(
            callsign=defn.callsign,
            aircraft_type=defn.aircraft_type,
            lat=first_wp.lat,
            lon=first_wp.lon,
            altitude_ft=defn.initial_alt_ft,
            groundspeed_kts=defn.initial_speed_kts,
            true_airspeed_kts=defn.initial_speed_kts,
            vertical_speed_fpm=0.0,
            true_heading_deg=round(initial_hdg, 1),
            magnetic_heading_deg=round(initial_hdg, 1),
            pitch_deg=1.0,
            roll_deg=0.0,
            flight_phase=first_wp.phase,
        )
        self.aircraft.update_magnetic_heading()

        # Apply initial radio tuning
        self.last_auto_tuned_wp_idx = 0
        if first_wp.nav1_tune:
            self.avionics.tune_nav1(first_wp.nav1_tune, first_wp.nav1_obs)
        if first_wp.dme1_tune:
            self.avionics.tune_dme1(first_wp.dme1_tune)
        if first_wp.adf1_tune:
            self.avionics.tune_adf1(first_wp.adf1_tune)

    def manual_tune(self, receiver: str, station_id: str, obs_deg: Optional[float] = None):
        """Allows manual user tuning of radio receivers without auto-tune wiping it."""
        if receiver == "auto":
            self.reset_auto_tune()
            return
        self.manual_tune_overridden = True
        if receiver == "nav1":
            self.avionics.tune_nav1(station_id, obs_deg)
        elif receiver == "nav2":
            self.avionics.tune_nav2(station_id, obs_deg)
        elif receiver == "dme1":
            self.avionics.tune_dme1(station_id)
        elif receiver == "adf1":
            self.avionics.tune_adf1(station_id)

    def reset_auto_tune(self):
        """Re-enables auto-tuning according to the active flight plan."""
        self.manual_tune_overridden = False
        if self.active_scenario and self.current_wp_idx < len(self.active_scenario.waypoints):
            target_wp = self.active_scenario.waypoints[self.current_wp_idx]
            if target_wp.nav1_tune:
                self.avionics.tune_nav1(target_wp.nav1_tune, target_wp.nav1_obs)
            if target_wp.dme1_tune:
                self.avionics.tune_dme1(target_wp.dme1_tune)
            if target_wp.adf1_tune:
                self.avionics.tune_adf1(target_wp.adf1_tune)

    def reset(self):
        if self.active_scenario:
            self.load_scenario(self.active_scenario.id)

    def set_speed_multiplier(self, mult: float):
        self.speed_multiplier = max(0.1, min(100.0, mult))

    def play(self):
        self.is_running = True

    def pause(self):
        self.is_running = False

    def step(self, dt_real_sec: float = 0.1) -> Dict[str, Any]:
        """Advances the simulation by dt_real_sec * speed_multiplier."""
        if not self.is_running or not self.active_scenario:
            return self.get_snapshot()

        sim_dt = dt_real_sec * self.speed_multiplier
        self.elapsed_time_sec += sim_dt

        wps = self.active_scenario.waypoints
        if self.current_wp_idx < len(wps):
            target_wp = wps[self.current_wp_idx]

            # Distance and bearing to target waypoint
            dist_to_wp_nm, brg_to_wp = great_circle_distance_bearing(
                self.aircraft.lat, self.aircraft.lon, target_wp.lat, target_wp.lon
            )

            # Auto-tune navaids ONLY upon transitioning to a new waypoint leg if not manually overridden
            if self.current_wp_idx != self.last_auto_tuned_wp_idx:
                self.last_auto_tuned_wp_idx = self.current_wp_idx
                if not self.manual_tune_overridden:
                    if target_wp.nav1_tune:
                        self.avionics.tune_nav1(target_wp.nav1_tune, target_wp.nav1_obs)
                    if target_wp.dme1_tune:
                        self.avionics.tune_dme1(target_wp.dme1_tune)
                    if target_wp.adf1_tune:
                        self.avionics.tune_adf1(target_wp.adf1_tune)

            # Guidance targets (Heading & Altitude)
            target_hdg = brg_to_wp
            effective_target_alt = target_wp.target_alt_ft
            d_along_nm = 999.0
            is_in_final_cone = False
            ils_thr_elev = 0.0

            if self.avionics.nav1_tuned_id in self.avionics._ils_stations:
                ils = self.avionics._ils_stations[self.avionics.nav1_tuned_id]
                ils_thr_elev = ils.thr_elev_ft

                # True physical runway centerline bearing (from threshold straight to localizer antenna)
                _, rwy_true_hdg = great_circle_distance_bearing(
                    ils.thr_lat, ils.thr_lon, ils.loc_rec.lat, ils.loc_rec.lon
                )
                recip_true = (rwy_true_hdg + 180.0) % 360.0

                # Compute along-track distance from runway threshold along final approach course (NM)
                dist_from_thr, brg_from_thr = great_circle_distance_bearing(
                    ils.thr_lat, ils.thr_lon, self.aircraft.lat, self.aircraft.lon
                )
                angle_off_final = math.radians((brg_from_thr - recip_true + 180.0) % 360.0 - 180.0)
                d_along_nm = dist_from_thr * math.cos(angle_off_final)

                # Only couple when within final approach capture sector: +/- 45 deg, -0.3 to 16 NM
                is_in_final_cone = (abs(angle_off_final) <= math.radians(45.0)) and (-0.5 <= d_along_nm <= 16.0)

                # 1. Localizer Lateral Coupling (True Runway Centerline Alignment)
                if target_wp.phase in ("LOCALIZER_CAPTURE", "FINAL_APPROACH", "THRESHOLD", "TOUCHDOWN"):
                    if is_in_final_cone:
                        # Cross-track error in nautical miles from runway centerline
                        # Line from thr to loc antenna points in the runway true heading direction
                        xtk_nm = cross_track_distance(
                            self.aircraft.lat, self.aircraft.lon,
                            ils.thr_lat, ils.thr_lon,
                            ils.loc_rec.lat, ils.loc_rec.lon
                        )
                        if d_along_nm > 0.0:
                            # P-controller on cross-track error to lock heading directly onto centerline
                            corr_deg = max(-20.0, min(20.0, xtk_nm * 150.0))
                            target_hdg = (rwy_true_hdg - corr_deg + 360.0) % 360.0
                        else:
                            # On runway surface rollout: tight steering down centerline
                            corr_deg = max(-10.0, min(10.0, xtk_nm * 300.0))
                            target_hdg = (rwy_true_hdg - corr_deg + 360.0) % 360.0

                # 2. Glide Slope Vertical Guidance (Intercept from Below & Zero-Lag Beam Tracking)
                if target_wp.phase in ("LOCALIZER_CAPTURE", "FINAL_APPROACH", "THRESHOLD", "TOUCHDOWN"):
                    if is_in_final_cone:
                        if d_along_nm > 0.0:
                            # Nominal 3.0° glide slope with 50 ft Threshold Crossing Height (TCH)
                            gs_nom = d_along_nm * 6076.11548 * math.tan(math.radians(3.0)) + ils.thr_elev_ft + 50.0
                            # Platform capture: hold 3,000 ft until intercepting 3.0° beam from below
                            effective_target_alt = min(3000.0, gs_nom)
                            effective_target_alt = max(ils.thr_elev_ft, effective_target_alt)

                            # When established on the 3.0° glide path, fly directly on the beam with nominal sink rate
                            if gs_nom <= 3000.0 and target_wp.phase in ("FINAL_APPROACH", "THRESHOLD"):
                                self.aircraft.altitude_ft = effective_target_alt
                                nominal_vs = -self.aircraft.groundspeed_kts * (6076.11548 / 3600.0) * math.tan(math.radians(3.0)) * 60.0
                                self.aircraft.vertical_speed_fpm = round(nominal_vs, 1)
                        elif d_along_nm > -0.20:
                            # Aerodynamic flare over first 1,200 ft of runway asphalt
                            flare_frac = min(1.0, max(0.0, -d_along_nm / 0.18))
                            effective_target_alt = ils.thr_elev_ft + 50.0 * ((1.0 - flare_frac) ** 2.2)
                            self.aircraft.altitude_ft = effective_target_alt
                            nominal_vs = -self.aircraft.groundspeed_kts * (6076.11548 / 3600.0) * math.tan(math.radians(3.0)) * 60.0
                            self.aircraft.vertical_speed_fpm = round(nominal_vs * (1.0 - flare_frac), 1)
                        else:
                            # Rolling out on runway surface
                            effective_target_alt = ils.thr_elev_ft
                            self.aircraft.altitude_ft = ils.thr_elev_ft
                            self.aircraft.vertical_speed_fpm = 0.0

            # Advance kinematics toward waypoint
            self.aircraft.flight_phase = target_wp.phase
            self.aircraft.step_kinematics(
                dt_sec=sim_dt,
                target_hdg_deg=target_hdg,
                target_alt_ft=effective_target_alt,
                target_speed_kts=target_wp.target_speed_kts,
            )

            # Re-sync exact glide slope / flare altitude at the updated aircraft position
            if self.avionics.nav1_tuned_id in self.avionics._ils_stations and is_in_final_cone:
                dist_from_thr_post, brg_from_thr_post = great_circle_distance_bearing(
                    ils.thr_lat, ils.thr_lon, self.aircraft.lat, self.aircraft.lon
                )
                angle_off_final_post = math.radians((brg_from_thr_post - recip_true + 180.0) % 360.0 - 180.0)
                d_along_post_nm = dist_from_thr_post * math.cos(angle_off_final_post)

                if target_wp.phase in ("FINAL_APPROACH", "THRESHOLD", "TOUCHDOWN"):
                    if d_along_post_nm > 0.0:
                        gs_nom_post = d_along_post_nm * 6076.11548 * math.tan(math.radians(3.0)) + ils.thr_elev_ft + 50.0
                        if gs_nom_post <= 3000.0:
                            self.aircraft.altitude_ft = gs_nom_post
                            nominal_vs = -self.aircraft.groundspeed_kts * (6076.11548 / 3600.0) * math.tan(math.radians(3.0)) * 60.0
                            self.aircraft.vertical_speed_fpm = round(nominal_vs, 1)
                    elif d_along_post_nm > -0.20:
                        flare_frac = min(1.0, max(0.0, -d_along_post_nm / 0.18))
                        self.aircraft.altitude_ft = ils.thr_elev_ft + 50.0 * ((1.0 - flare_frac) ** 2.2)
                        nominal_vs = -self.aircraft.groundspeed_kts * (6076.11548 / 3600.0) * math.tan(math.radians(3.0)) * 60.0
                        self.aircraft.vertical_speed_fpm = round(nominal_vs * (1.0 - flare_frac), 1)
                    else:
                        self.aircraft.altitude_ft = ils.thr_elev_ft
                        self.aircraft.vertical_speed_fpm = 0.0

            # Waypoint capture threshold
            captured = False
            max_step_dist = (self.aircraft.groundspeed_kts / 3600.0) * sim_dt * 1.5

            if target_wp.phase == "THRESHOLD":
                # Physically reached or crossed the runway threshold line
                if d_along_nm <= 0.005 or dist_to_wp_nm <= max_step_dist:
                    captured = True
            elif target_wp.phase == "TOUCHDOWN":
                # Touchdown inside touchdown zone on runway asphalt
                if d_along_nm <= -0.18 or dist_to_wp_nm <= max_step_dist:
                    captured = True
                    self.aircraft.altitude_ft = ils_thr_elev
                    self.aircraft.vertical_speed_fpm = 0.0
                    self.aircraft.pitch_deg = 0.0
                    self.aircraft.roll_deg = 0.0
            else:
                if dist_to_wp_nm <= max(0.3, max_step_dist):
                    captured = True

            # Runway rollout deceleration
            if target_wp.phase == "TOUCHDOWN":
                self.aircraft.groundspeed_kts = max(25.0, self.aircraft.groundspeed_kts - 12.0 * sim_dt)
                self.aircraft.true_airspeed_kts = self.aircraft.groundspeed_kts
                if d_along_nm <= -0.15:
                    self.aircraft.altitude_ft = ils_thr_elev
                    self.aircraft.vertical_speed_fpm = 0.0
                    self.aircraft.vertical_speed_fpm = 0.0

            if captured:
                self.current_wp_idx += 1
                if self.current_wp_idx >= len(wps):
                    self.is_running = False
                    self.aircraft.flight_phase = "COMPLETED"

        return self.get_snapshot()

    def seek_fraction(self, fraction: float):
        """Seeks to a normalized fraction [0.0, 1.0] along the flight plan."""
        fraction = max(0.0, min(1.0, fraction))
        if not self.active_scenario:
            return

        wps = self.active_scenario.waypoints
        total_legs = len(wps) - 1
        if total_legs <= 0:
            return

        exact_idx = fraction * total_legs
        leg_idx = min(int(exact_idx), total_legs - 1)
        sub_frac = exact_idx - leg_idx

        wp1 = wps[leg_idx]
        wp2 = wps[leg_idx + 1]

        # Interpolate coordinates
        new_lat, new_lon = interpolate_great_circle(wp1.lat, wp1.lon, wp2.lat, wp2.lon, sub_frac)
        # Interpolate altitude & speed
        new_alt = wp1.target_alt_ft + (wp2.target_alt_ft - wp1.target_alt_ft) * sub_frac
        new_spd = wp1.target_speed_kts + (wp2.target_speed_kts - wp1.target_speed_kts) * sub_frac

        _, hdg = great_circle_distance_bearing(new_lat, new_lon, wp2.lat, wp2.lon)

        self.current_wp_idx = leg_idx + 1
        self.last_auto_tuned_wp_idx = self.current_wp_idx
        self.manual_tune_overridden = False
        self.aircraft.lat = new_lat
        self.aircraft.lon = new_lon
        self.aircraft.altitude_ft = new_alt
        self.aircraft.groundspeed_kts = new_spd
        self.aircraft.true_airspeed_kts = new_spd
        self.aircraft.true_heading_deg = hdg
        self.aircraft.update_magnetic_heading()
        self.aircraft.flight_phase = wp2.phase

        # Tune to upcoming waypoint setup
        if wp2.nav1_tune:
            self.avionics.tune_nav1(wp2.nav1_tune, wp2.nav1_obs)
        if wp2.dme1_tune:
            self.avionics.tune_dme1(wp2.dme1_tune)
        if wp2.adf1_tune:
            self.avionics.tune_adf1(wp2.adf1_tune)

    def get_snapshot(self) -> Dict[str, Any]:
        """Produces full telemetry and scenario state payload."""
        avionics_eval = self.avionics.evaluate_all(self.aircraft)

        wps_list = []
        if self.active_scenario:
            for i, w in enumerate(self.active_scenario.waypoints):
                wps_list.append({
                    "name": w.name,
                    "lat": w.lat,
                    "lon": w.lon,
                    "target_alt_ft": w.target_alt_ft,
                    "target_speed_kts": w.target_speed_kts,
                    "phase": w.phase,
                    "nav1_tune": w.nav1_tune,
                    "nav1_obs": w.nav1_obs,
                    "briefing_note": w.briefing_note,
                    "is_current": (i == self.current_wp_idx),
                    "is_passed": (i < self.current_wp_idx),
                })

        target_wp_name = (
            self.active_scenario.waypoints[self.current_wp_idx].name
            if self.active_scenario and self.current_wp_idx < len(self.active_scenario.waypoints)
            else "TOUCHDOWN"
        )
        target_wp_note = (
            self.active_scenario.waypoints[self.current_wp_idx].briefing_note
            if self.active_scenario and self.current_wp_idx < len(self.active_scenario.waypoints)
            else "Flight plan complete."
        )

        return {
            "scenario": {
                "id": self.active_scenario.id if self.active_scenario else None,
                "title": self.active_scenario.title if self.active_scenario else "",
                "summary": self.active_scenario.summary if self.active_scenario else "",
                "flight_level": self.active_scenario.flight_level if self.active_scenario else "",
                "departure": self.active_scenario.departure if self.active_scenario else "",
                "destination": self.active_scenario.destination if self.active_scenario else "",
                "airspace_context": self.active_scenario.airspace_context if self.active_scenario else "",
                "avionics_focus": self.active_scenario.avionics_focus if self.active_scenario else "",
                "current_waypoint_index": self.current_wp_idx,
                "total_waypoints": len(self.active_scenario.waypoints) if self.active_scenario else 0,
                "target_waypoint_name": target_wp_name,
                "target_waypoint_note": target_wp_note,
                "is_running": self.is_running,
                "speed_multiplier": self.speed_multiplier,
                "manual_tune_overridden": self.manual_tune_overridden,
                "elapsed_time_sec": round(self.elapsed_time_sec, 1),
                "waypoints": wps_list,
            },
            "telemetry": avionics_eval,
        }

