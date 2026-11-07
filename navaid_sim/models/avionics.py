"""
Cockpit avionics architecture and receiver integration suite.
Manages NAV1, NAV2, DME1, ADF1, and GNSS receivers, connects with the database of stations,
and generates real-time ARINC 429 digital bus words and NMEA sentences.
"""

import datetime
from typing import Dict, Any, Optional, List

from navaid_sim.core.protocol import (
    encode_arinc429_vor_bearing,
    encode_arinc429_dme_distance,
    encode_arinc429_loc_deviation,
    encode_arinc429_gs_deviation,
    encode_arinc429_adf_bearing,
    encode_arinc429_nav_frequency,
    generate_nmea_sentences,
)
from navaid_sim.database.loader import AirspaceDatabase, NavaidRecord
from navaid_sim.models.aircraft import AircraftState
from navaid_sim.models.navaid import (
    VORStation,
    DMEStation,
    NDBStation,
    ILSStation,
    GNSSSystem,
    VOREvaluation,
    DMEEvaluation,
    NDBEvaluation,
    ILSEvaluation,
)


class AvionicsSuite:
    """Simulates the airborne navigation radio management and digital telemetry bus."""

    def __init__(self, db: AirspaceDatabase):
        self.db = db

        # Tuned station IDs or keys
        self.nav1_tuned_id: str = "SHA"
        self.nav1_obs_deg: float = 236.0
        self.nav2_tuned_id: str = "DUB"
        self.nav2_obs_deg: float = 90.0

        self.dme1_tuned_id: str = "SHA"
        self.adf1_tuned_id: str = "CML"

        self.gnss_system = GNSSSystem()

        # Cache station instances
        self._vor_stations: Dict[str, VORStation] = {}
        self._dme_stations: Dict[str, DMEStation] = {}
        self._ndb_stations: Dict[str, NDBStation] = {}
        self._ils_stations: Dict[str, ILSStation] = {}
        self._init_stations()

    def _init_stations(self):
        for key, rec in self.db.navaids.items():
            if "DVOR" in rec.type or "VOR" in rec.type:
                self._vor_stations[rec.id] = VORStation(rec)
            if "DME" in rec.type:
                self._dme_stations[rec.id] = DMEStation(rec)
            if "NDB" in rec.type:
                self._ndb_stations[rec.id] = NDBStation(rec)
            if rec.type == "ILS_LOC":
                # Find matching GP
                gp_rec = None
                for other in self.db.navaids.values():
                    if (
                        other.associated_airport == rec.associated_airport
                        and other.runway_id == rec.runway_id
                        and other.type == "ILS_GP"
                    ):
                        gp_rec = other
                        break
                self._ils_stations[rec.id] = ILSStation(rec, gp_rec)

    def tune_nav1(self, station_id: str, obs_deg: Optional[float] = None):
        self.nav1_tuned_id = station_id
        if station_id in self._dme_stations:
            self.dme1_tuned_id = station_id
        if obs_deg is not None:
            self.nav1_obs_deg = obs_deg % 360.0

    def tune_nav2(self, station_id: str, obs_deg: Optional[float] = None):
        self.nav2_tuned_id = station_id
        if obs_deg is not None:
            self.nav2_obs_deg = obs_deg % 360.0

    def tune_dme1(self, station_id: str):
        self.dme1_tuned_id = station_id

    def tune_adf1(self, station_id: str):
        self.adf1_tuned_id = station_id

    def evaluate_all(self, aircraft: AircraftState) -> Dict[str, Any]:
        """
        Evaluates current radio reception, instrument readouts, and ARINC 429 digital bus words.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        timestamp_iso = now.isoformat()

        # 1. Evaluate NAV1 (VOR or ILS)
        nav1_eval = None
        nav1_mode = "NONE"
        nav1_station_info = None

        if self.nav1_tuned_id in self._ils_stations:
            ils = self._ils_stations[self.nav1_tuned_id]
            nav1_eval = ils.evaluate(aircraft.lat, aircraft.lon, aircraft.altitude_ft)
            nav1_mode = "ILS"
            nav1_station_info = {
                "id": ils.id,
                "name": ils.name,
                "type": "ILS",
                "frequency": ils.loc_rec.frequency,
                "freq_mhz": ils.loc_rec.freq_mhz,
                "runway_id": ils.rwy_id,
                "inbound_track_mag": ils.rwy_bearing_mag,
            }
        elif self.nav1_tuned_id in self._vor_stations:
            vor = self._vor_stations[self.nav1_tuned_id]
            nav1_eval = vor.evaluate(aircraft.lat, aircraft.lon, aircraft.altitude_ft, self.nav1_obs_deg)
            nav1_mode = "VOR"
            nav1_station_info = {
                "id": vor.id,
                "name": vor.name,
                "type": vor.record.type,
                "frequency": vor.record.frequency,
                "freq_mhz": vor.freq_mhz,
            }

        # 2. Evaluate NAV2 (VOR)
        nav2_eval = None
        nav2_station_info = None
        if self.nav2_tuned_id in self._vor_stations:
            vor2 = self._vor_stations[self.nav2_tuned_id]
            nav2_eval = vor2.evaluate(aircraft.lat, aircraft.lon, aircraft.altitude_ft, self.nav2_obs_deg)
            nav2_station_info = {
                "id": vor2.id,
                "name": vor2.name,
                "type": vor2.record.type,
                "frequency": vor2.record.frequency,
                "freq_mhz": vor2.freq_mhz,
            }

        # 3. Evaluate DME1
        dme1_eval = None
        dme1_station_info = None
        if self.dme1_tuned_id in self._dme_stations:
            dme = self._dme_stations[self.dme1_tuned_id]
            dme1_eval = dme.evaluate(aircraft.lat, aircraft.lon, aircraft.altitude_ft, aircraft.groundspeed_kts)
            dme1_station_info = {
                "id": dme.id,
                "name": dme.name,
                "channel": dme.channel,
                "freq_mhz": dme.freq_mhz,
            }

        # 4. Evaluate ADF1
        adf1_eval = None
        adf1_station_info = None
        if self.adf1_tuned_id in self._ndb_stations:
            ndb = self._ndb_stations[self.adf1_tuned_id]
            adf1_eval = ndb.evaluate(aircraft.lat, aircraft.lon, aircraft.magnetic_heading_deg)
            adf1_station_info = {
                "id": ndb.id,
                "name": ndb.name,
                "frequency_khz": ndb.freq_khz,
            }

        # 5. Evaluate GNSS
        gnss_eval = self.gnss_system.evaluate(aircraft.lat, aircraft.lon, aircraft.altitude_ft)

        # 6. Generate ARINC 429 Bus Words
        arinc_words = []

        # Label 030: NAV1 Frequency
        freq_mhz = nav1_station_info.get("freq_mhz", 113.3) if nav1_station_info else 113.3
        arinc_words.append(encode_arinc429_nav_frequency(freq_mhz, sdi=1))

        if nav1_mode == "VOR" and isinstance(nav1_eval, VOREvaluation):
            # Label 212: VOR Bearing
            arinc_words.append(
                encode_arinc429_vor_bearing(
                    nav1_eval.radial_deg, sdi=1, is_valid=not nav1_eval.failure_flag
                )
            )
        elif nav1_mode == "ILS" and isinstance(nav1_eval, ILSEvaluation):
            # Label 173: LOC Deviation
            arinc_words.append(
                encode_arinc429_loc_deviation(
                    nav1_eval.loc_deflection_dots, sdi=1, is_valid=nav1_eval.loc_received
                )
            )
            # Label 174: GS Deviation
            arinc_words.append(
                encode_arinc429_gs_deviation(
                    nav1_eval.gp_deflection_dots, sdi=1, is_valid=nav1_eval.gp_received
                )
            )

        if isinstance(dme1_eval, DMEEvaluation):
            # Label 037: DME Distance
            arinc_words.append(
                encode_arinc429_dme_distance(
                    dme1_eval.slant_range_nm, sdi=1, is_valid=dme1_eval.is_received
                )
            )

        if isinstance(adf1_eval, NDBEvaluation):
            # Label 162: ADF Relative Bearing
            arinc_words.append(
                encode_arinc429_adf_bearing(
                    adf1_eval.relative_bearing_deg, sdi=1, is_valid=adf1_eval.is_received
                )
            )

        # 7. Generate NMEA Sentences
        nmea_sentences = generate_nmea_sentences(
            lat=aircraft.lat,
            lon=aircraft.lon,
            alt_ft=aircraft.altitude_ft,
            speed_kts=aircraft.groundspeed_kts,
            track_deg=aircraft.true_heading_deg,
            hdop=gnss_eval["hdop"],
            num_sats=gnss_eval["satellites_tracked"],
            timestamp=now,
        )

        # 8. All Nearby Facilities Reception Matrix (Full scan of available navaids)
        reception_matrix = []
        for key, rec in self.db.navaids.items():
            if "DVOR" in rec.type or "VOR" in rec.type:
                st = self._vor_stations.get(rec.id)
                if st:
                    ev = st.evaluate(aircraft.lat, aircraft.lon, aircraft.altitude_ft, 0.0)
                    reception_matrix.append({
                        "id": rec.id,
                        "name": rec.name,
                        "type": rec.type,
                        "freq": rec.frequency,
                        "received": ev.is_received,
                        "signal_dbm": ev.signal_strength_dbm,
                        "bearing_mag": ev.radial_deg,
                        "in_cone": ev.is_in_cone_of_confusion,
                        "restricted": ev.is_terrain_restricted,
                    })
            elif "DME" in rec.type and "DVOR" not in rec.type:
                st = self._dme_stations.get(rec.id)
                if st:
                    ev = st.evaluate(aircraft.lat, aircraft.lon, aircraft.altitude_ft, aircraft.groundspeed_kts)
                    reception_matrix.append({
                        "id": rec.id,
                        "name": rec.name,
                        "type": "DME",
                        "freq": rec.frequency,
                        "received": ev.is_received,
                        "distance_nm": ev.slant_range_nm,
                        "signal_dbm": ev.signal_strength_dbm,
                        "lock_status": ev.lock_status,
                    })
            elif "NDB" in rec.type:
                st = self._ndb_stations.get(rec.id)
                if st:
                    ev = st.evaluate(aircraft.lat, aircraft.lon, aircraft.magnetic_heading_deg)
                    reception_matrix.append({
                        "id": rec.id,
                        "name": rec.name,
                        "type": "NDB",
                        "freq": rec.frequency,
                        "received": ev.is_received,
                        "dist_nm": ev.dist_nm,
                        "field_strength_uv": ev.field_strength_uv_m,
                        "rel_bearing": ev.relative_bearing_deg,
                    })

        return {
            "timestamp": timestamp_iso,
            "aircraft": {
                "callsign": aircraft.callsign,
                "type": aircraft.aircraft_type,
                "lat": round(aircraft.lat, 5),
                "lon": round(aircraft.lon, 5),
                "altitude_ft": round(aircraft.altitude_ft, 1),
                "groundspeed_kts": round(aircraft.groundspeed_kts, 1),
                "true_airspeed_kts": round(aircraft.true_airspeed_kts, 1),
                "true_heading_deg": round(aircraft.true_heading_deg, 1),
                "magnetic_heading_deg": round(aircraft.magnetic_heading_deg, 1),
                "pitch_deg": round(aircraft.pitch_deg, 1),
                "roll_deg": round(aircraft.roll_deg, 1),
                "vertical_speed_fpm": round(aircraft.vertical_speed_fpm, 1),
                "flight_phase": aircraft.flight_phase,
                "transponder_code": aircraft.transponder_code,
            },
            "nav1": {
                "mode": nav1_mode,
                "station": nav1_station_info,
                "obs_deg": self.nav1_obs_deg,
                "evaluation": nav1_eval.__dict__ if nav1_eval else None,
            },
            "nav2": {
                "station": nav2_station_info,
                "obs_deg": self.nav2_obs_deg,
                "evaluation": nav2_eval.__dict__ if nav2_eval else None,
            },
            "dme1": {
                "station": dme1_station_info,
                "evaluation": dme1_eval.__dict__ if dme1_eval else None,
            },
            "adf1": {
                "station": adf1_station_info,
                "evaluation": adf1_eval.__dict__ if adf1_eval else None,
            },
            "gnss": gnss_eval,
            "arinc429_bus": arinc_words,
            "nmea_0183": nmea_sentences,
            "reception_matrix": reception_matrix,
        }

