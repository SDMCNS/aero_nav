"""
Unit test suite for the Aviation Navaid & Avionics Simulator.
"""

import math
import os
import unittest

from navaid_sim.core.geo import (
    parse_dms_coord,
    great_circle_distance_bearing,
    destination_point,
    cross_track_distance,
    get_regional_magnetic_variation,
)
from navaid_sim.core.physics import (
    radio_line_of_sight_nm,
    calculate_slant_range_nm,
    is_in_vor_cone_of_confusion,
    calculate_vor_deviation,
    calculate_ils_localizer_deviation,
    calculate_ils_glideslope_deviation,
    calculate_ndb_relative_bearing,
)
from navaid_sim.core.protocol import (
    encode_arinc429_vor_bearing,
    encode_arinc429_dme_distance,
    encode_arinc429_loc_deviation,
    encode_arinc429_gs_deviation,
    encode_arinc429_adf_bearing,
    calculate_nmea_checksum,
    generate_nmea_sentences,
    to_morse_code,
)
from navaid_sim.database.loader import AirspaceDatabase
from navaid_sim.scenarios.runner import ScenarioRunner
from navaid_sim.scenarios.definitions import ALL_SCENARIOS


class TestNavaidSimulation(unittest.TestCase):

    def setUp(self):
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.db = AirspaceDatabase(self.root_dir)

    def test_dms_coord_parsing(self):
        # Shannon format
        c1 = parse_dms_coord("524207N 0085529W")
        self.assertIsNotNone(c1)
        self.assertAlmostEqual(c1[0], 52.701944, places=4)
        self.assertAlmostEqual(c1[1], -8.924722, places=4)

        # Dublin decimal seconds format
        c2 = parse_dms_coord("532520.75N 0061724.27W")
        self.assertIsNotNone(c2)
        self.assertAlmostEqual(c2[0], 53.42243, places=4)
        self.assertAlmostEqual(c2[1], -6.290075, places=4)

    def test_great_circle_navigation(self):
        # Distance between Dublin and Shannon (~103 NM)
        dist, brg = great_circle_distance_bearing(53.4214, -6.2700, 52.7019, -8.9247)
        self.assertTrue(100.0 < dist < 110.0)
        self.assertTrue(240.0 < brg < 260.0)

        # Destination point check
        dest_lat, dest_lon = destination_point(53.4214, -6.2700, brg, dist)
        self.assertAlmostEqual(dest_lat, 52.7019, places=2)
        self.assertAlmostEqual(dest_lon, -8.9247, places=2)

    def test_physics_slant_range_and_los(self):
        # Directly overhead at 30,000 ft (dist ground = 0 NM)
        slant = calculate_slant_range_nm(0.0, 30000.0)
        self.assertAlmostEqual(slant, 30000.0 / 6076.115, places=2)

        # Line of sight at FL370 with station at 200 ft
        los = radio_line_of_sight_nm(37000.0, 200.0)
        self.assertTrue(los > 240.0)

        # Cone of confusion test directly over station
        in_cone = is_in_vor_cone_of_confusion(ground_dist_nm=0.5, alt_diff_ft=30000.0)
        self.assertTrue(in_cone)

        out_of_cone = is_in_vor_cone_of_confusion(ground_dist_nm=15.0, alt_diff_ft=30000.0)
        self.assertFalse(out_of_cone)

    def test_vor_deviation_and_to_from(self):
        # Radial 090, dialed OBS 090 -> centered needle (0 dots), FROM flag
        defl, to_from, amb = calculate_vor_deviation(90.0, 90.0)
        self.assertAlmostEqual(defl, 0.0, places=1)
        self.assertEqual(to_from, "FROM")

        # Radial 090, dialed OBS 270 -> flying inbound to station (TO flag)
        defl_to, to_from_to, _ = calculate_vor_deviation(90.0, 270.0)
        self.assertAlmostEqual(defl_to, 0.0, places=1)
        self.assertEqual(to_from_to, "TO")

        # 4 degrees right of course -> 2 dots deflection
        defl_off, _, _ = calculate_vor_deviation(94.0, 90.0)
        self.assertTrue(defl_off < 0)  # Fly left toward course

    def test_ils_localizer_and_glideslope(self):
        # Aircraft exactly on runway centerline heading 236° at 8 NM
        defl_loc, loc_valid = calculate_ils_localizer_deviation(
            aircraft_bearing_from_threshold=56.0,
            runway_magnetic_heading=236.0,
            ground_dist_nm=8.0,
        )
        self.assertTrue(loc_valid)
        self.assertAlmostEqual(defl_loc, 0.0, places=1)

        # Glideslope at 3 NM: 3 NM * 6076 * tan(3 deg) ≈ 955 ft + threshold
        dist_ft = 3.0 * 6076.115
        expected_alt = dist_ft * math.tan(math.radians(3.0)) + 46.0
        defl_gs, gp_valid = calculate_ils_glideslope_deviation(
            aircraft_alt_ft=expected_alt,
            threshold_alt_ft=46.0,
            ground_dist_to_touchdown_nm=3.0,
        )
        self.assertTrue(gp_valid)
        self.assertAlmostEqual(defl_gs, 0.0, places=1)

    def test_arinc429_word_generation(self):
        word_vor = encode_arinc429_vor_bearing(123.45, sdi=1)
        self.assertEqual(word_vor["label_octal"], "212")
        self.assertEqual(len(word_vor["raw_bin"]), 32)
        self.assertTrue(word_vor["raw_hex"].startswith("0x"))

        word_dme = encode_arinc429_dme_distance(42.3, sdi=1)
        self.assertEqual(word_dme["label_octal"], "037")
        self.assertEqual(len(word_dme["raw_bin"]), 32)

        # Check odd parity
        ones = word_dme["raw_bin"].count("1")
        self.assertEqual(ones % 2, 1)

    def test_nmea_0183(self):
        gga_raw = "GPGGA,120000.00,5325.2000,N,00620.4876,W,1,10,0.8,500.0,M,48.2,M,,"
        csum = calculate_nmea_checksum(gga_raw)
        self.assertEqual(len(csum), 2)

        sentences = generate_nmea_sentences(53.42, -6.27, 3000.0, 220.0, 240.0)
        self.assertTrue(sentences["GGA"].startswith("$GPGGA,"))
        self.assertTrue(sentences["RMC"].startswith("$GPRMC,"))
        self.assertTrue("*" in sentences["GGA"])

    def test_database_ingestion(self):
        # Verify EISNFIR and EISNUIR are loaded
        self.assertIn("EISNFIR", self.db.fir_boundaries)
        self.assertIn("EISNUIR", self.db.fir_boundaries)
        self.assertEqual(self.db.fir_boundaries["EISNFIR"].min_fl, 0)
        self.assertEqual(self.db.fir_boundaries["EISNFIR"].max_fl, 245)

        # Verify airports
        self.assertIn("EINN", self.db.airports)
        self.assertIn("EIDW", self.db.airports)
        self.assertIn("EICK", self.db.airports)

        # Verify key navaids
        # SHA, DUB, BAL, CML, WTP
        navaid_ids = set(n.id for n in self.db.navaids.values())
        self.assertIn("SHA", navaid_ids)
        self.assertIn("DUB", navaid_ids)
        self.assertIn("CML", navaid_ids)
        self.assertIn("WTP", navaid_ids)
        self.assertIn("ISW", navaid_ids)  # EINN ILS 24 LOC
        self.assertIn("ISE", navaid_ids)  # EINN ILS 06 LOC

    def test_scenario_execution(self):
        runner = ScenarioRunner(self.db)
        for sc_id in ALL_SCENARIOS.keys():
            runner.load_scenario(sc_id)
            runner.play()
            runner.set_speed_multiplier(5.0)
            snap = runner.step(1.0)
            self.assertEqual(snap["scenario"]["id"], sc_id)
            self.assertIn("aircraft", snap["telemetry"])
            self.assertIn("arinc429_bus", snap["telemetry"])
            self.assertIn("nmea_0183", snap["telemetry"])

    def test_scenario_2_finals_glideslope_profile(self):
        """Tests that Scenario 2 tracks the 3.0° ILS glide slope down to threshold and touchdown."""
        runner = ScenarioRunner(self.db)
        runner.load_scenario("a320_shannon_arrival")
        # Seek to 0.70 (on final approach, approaching FAF24)
        runner.seek_fraction(0.70)
        runner.set_speed_multiplier(2.0)
        runner.play()

        observed_finals = []
        for _ in range(1200):
            if not runner.is_running:
                break
            snap = runner.step(0.1)
            ac = snap["telemetry"]["aircraft"]
            nav1 = snap["telemetry"]["nav1"]
            if nav1["mode"] == "ILS" and nav1["evaluation"]:
                ev = nav1["evaluation"]
                observed_finals.append((ev["dist_to_touchdown_nm"], ac["altitude_ft"], ev["gp_deflection_dots"]))

        # Check that we observed final approach tracking
        self.assertTrue(len(observed_finals) > 50)
        # Verify touchdown was achieved at runway elevation (15 ft)
        self.assertAlmostEqual(runner.aircraft.altitude_ft, 15.0, delta=5.0)
        self.assertEqual(runner.aircraft.flight_phase, "COMPLETED")

        # Verify glide slope deviations stayed centered (< 1.5 dots) while tracking ILS on finals
        stable_points = [pt for pt in observed_finals if 0.5 <= pt[0] <= 5.0]
        self.assertTrue(len(stable_points) > 10)
        for d, alt, gp_dots in stable_points:
            self.assertTrue(abs(gp_dots) < 1.5, f"GP deviation too large at {d} NM: {gp_dots} dots")

    def test_manual_tuning_persistence(self):
        """Verifies manual tuning is not wiped across 50 steps."""
        runner = ScenarioRunner(self.db)
        runner.load_scenario("a320_shannon_arrival")
        runner.play()
        runner.step(0.1)

        runner.manual_tune("nav1", "DUB", 90.0)
        self.assertEqual(runner.avionics.nav1_tuned_id, "DUB")
        self.assertTrue(runner.manual_tune_overridden)

        for _ in range(50):
            runner.step(0.1)

        self.assertEqual(runner.avionics.nav1_tuned_id, "DUB")
        self.assertTrue(runner.manual_tune_overridden)

        # Test restoring auto-tune
        runner.reset_auto_tune()
        self.assertFalse(runner.manual_tune_overridden)
        runner.step(0.1)
        self.assertIn(runner.avionics.nav1_tuned_id, ["SHA", "ISW"])


if __name__ == "__main__":
    unittest.main()

