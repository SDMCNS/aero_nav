import unittest
from navaid_sim.database.loader import AirspaceDatabase
from navaid_sim.scenarios.runner import ScenarioRunner


class TestScenarioApproaches(unittest.TestCase):
    def test_scenario2_a320_ils_rwy24_touchdown(self):
        db = AirspaceDatabase()
        runner = ScenarioRunner(db)
        runner.load_scenario("scenario-2")
        runner.set_speed_multiplier(20.0)
        runner.play()

        intercept_checked = False
        final_approach_reached = False
        touchdown_reached = False
        final_alt = None

        for step in range(500):
            if not runner.is_running:
                break
            snap = runner.step(dt_real_sec=0.5)
            ac = snap["telemetry"]["aircraft"]
            nav1 = snap["telemetry"]["nav1"]
            ev = nav1.get("evaluation") or {}
            phase = ac["flight_phase"]
            alt = ac["altitude_ft"]

            if phase == "LOCALIZER_CAPTURE":
                intercept_checked = True
                loc_dots = abs(ev.get("loc_deflection_dots", 99))
                self.assertLess(loc_dots, 3.5)

            if phase == "FINAL_APPROACH":
                final_approach_reached = True
                loc_dots = abs(ev.get("loc_deflection_dots", 99))
                gp_dots = abs(ev.get("gp_deflection_dots", 99))
                self.assertLess(loc_dots, 1.0)
                self.assertLess(gp_dots, 2.5)

                dist = ev.get("dist_to_touchdown_nm", 99)
                if 4.8 <= dist <= 5.2:
                    # At FAF24 (5.0 NM), nominal GS is 1,657 ft
                    self.assertAlmostEqual(alt, 1657.0, delta=60.0)
                    self.assertLess(abs(gp_dots), 0.5)

            if phase in ["THRESHOLD", "TOUCHDOWN"]:
                touchdown_reached = True

            if phase in ["TOUCHDOWN", "COMPLETED"]:
                final_alt = alt

        if final_alt is None:
            final_alt = runner.aircraft.altitude_ft

        self.assertTrue(intercept_checked, "Scenario 2 did not capture localizer")
        self.assertTrue(final_approach_reached, "Scenario 2 did not reach final approach")
        self.assertTrue(touchdown_reached, "Scenario 2 did not reach runway threshold / touchdown")
        self.assertIsNotNone(final_alt)
        # Shannon Rwy 24 elevation is 15 ft AMSL; final altitude must be 15 ft (touchdown zone)!
        self.assertLessEqual(final_alt, 20.0, f"Scenario 2 final altitude was {final_alt} ft, expected <= 20 ft!")
        # Touchdown / rollout position must be on Runway 24 asphalt (between lat 52.710 and 52.695)
        self.assertAlmostEqual(runner.aircraft.lat, 52.706, delta=0.006)
        self.assertAlmostEqual(runner.aircraft.lon, -8.916, delta=0.008)

    def test_scenario3_city_hopper_ils_rwy06_touchdown(self):
        db = AirspaceDatabase()
        runner = ScenarioRunner(db)
        runner.load_scenario("scenario-3")
        runner.set_speed_multiplier(20.0)
        runner.play()

        downwind_checked = False
        base_checked = False
        intercept_checked = False
        final_approach_reached = False
        touchdown_reached = False
        final_alt = None

        for step in range(600):
            if not runner.is_running:
                break
            snap = runner.step(dt_real_sec=0.5)
            ac = snap["telemetry"]["aircraft"]
            nav1 = snap["telemetry"]["nav1"]
            ev = nav1.get("evaluation") or {}
            phase = ac["flight_phase"]
            alt = ac["altitude_ft"]

            if phase == "DOWNWIND_VECTOR":
                downwind_checked = True
            if phase == "BASE_LEG_TURN":
                base_checked = True
            if phase == "LOCALIZER_CAPTURE":
                intercept_checked = True
                loc_dots = abs(ev.get("loc_deflection_dots", 99))
                self.assertLess(loc_dots, 3.5)

            if phase == "FINAL_APPROACH":
                final_approach_reached = True
                loc_dots = abs(ev.get("loc_deflection_dots", 99))
                gp_dots = abs(ev.get("gp_deflection_dots", 99))
                self.assertLess(loc_dots, 1.0)
                self.assertLess(gp_dots, 2.5)

                dist = ev.get("dist_to_touchdown_nm", 99)
                if 4.8 <= dist <= 5.2:
                    # At FAF06 (5.0 NM), nominal GS is 1,688 ft
                    self.assertAlmostEqual(alt, 1688.0, delta=60.0)
                    self.assertLess(abs(gp_dots), 0.5)

            if phase in ["THRESHOLD", "TOUCHDOWN"]:
                touchdown_reached = True

            if phase in ["TOUCHDOWN", "COMPLETED"]:
                final_alt = alt

        if final_alt is None:
            final_alt = runner.aircraft.altitude_ft

        self.assertTrue(downwind_checked, "Scenario 3 did not fly downwind vector")
        self.assertTrue(base_checked, "Scenario 3 did not fly base turn")
        self.assertTrue(intercept_checked, "Scenario 3 did not capture localizer")
        self.assertTrue(final_approach_reached, "Scenario 3 did not reach final approach")
        self.assertTrue(touchdown_reached, "Scenario 3 did not reach runway threshold / touchdown")
        self.assertIsNotNone(final_alt)
        # Shannon Rwy 06 elevation is 46 ft AMSL; final altitude must be 46 ft (touchdown zone)!
        self.assertLessEqual(final_alt, 50.0, f"Scenario 3 final altitude was {final_alt} ft, expected <= 50 ft!")
        # Touchdown position must be within 0.003 deg of Runway 06 centerline
        self.assertAlmostEqual(runner.aircraft.lat, 52.695, delta=0.003)
        self.assertAlmostEqual(runner.aircraft.lon, -8.939, delta=0.003)

    def test_faf_runway_centerline_alignment(self):
        """Verifies that all standard FAF terminal waypoints lie on the extended runway centerline."""
        from navaid_sim.core.geo import cross_track_distance, great_circle_distance_bearing

        db = AirspaceDatabase()
        test_cases = [
            ("FAF24", "EINN_ISW_24"),
            ("FAF06", "EINN_ISE_06"),
            ("FAF28L", "EIDW_IDW_28L"),
        ]
        for faf_name, loc_id in test_cases:
            self.assertIn(faf_name, db.waypoints)
            self.assertIn(loc_id, db.navaids)
            faf = db.waypoints[faf_name]
            ils = db.navaids[loc_id]
            xtk = cross_track_distance(
                faf.lat, faf.lon, ils.runway_thr_lat, ils.runway_thr_lon, ils.lat, ils.lon
            )
            dist, _ = great_circle_distance_bearing(
                ils.runway_thr_lat, ils.runway_thr_lon, faf.lat, faf.lon
            )
            # Must be 5.0 NM nominal out and within 10 meters cross-track of true centerline
            self.assertAlmostEqual(dist, 5.0, delta=0.1, msg=f"{faf_name} distance is not ~5 NM")
            self.assertLess(
                abs(xtk * 1852.0), 10.0, msg=f"{faf_name} cross-track error {xtk*1852.0:.1f}m > 10m"
            )


if __name__ == "__main__":
    unittest.main()
