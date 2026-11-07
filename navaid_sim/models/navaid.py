"""
Object-oriented simulation models for aviation navigation facilities:
VOR/DVOR, DME, NDB, ILS (Localizer + Glide Path), and GNSS/SBAS.
"""

import math
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field

from navaid_sim.core.geo import (
    great_circle_distance_bearing,
    get_regional_magnetic_variation,
)
from navaid_sim.core.physics import (
    radio_line_of_sight_nm,
    calculate_slant_range_nm,
    free_space_path_loss_db,
    is_in_vor_cone_of_confusion,
    calculate_vor_deviation,
    calculate_ils_localizer_deviation,
    calculate_ils_glideslope_deviation,
    calculate_ndb_relative_bearing,
    compute_gnss_dop_metrics,
)
from navaid_sim.core.protocol import to_morse_code
from navaid_sim.database.loader import NavaidRecord


@dataclass
class VOREvaluation:
    is_received: bool
    is_in_los: bool
    is_in_doc: bool
    is_in_cone_of_confusion: bool
    is_terrain_restricted: bool
    radial_deg: float  # Magnetic radial from station
    true_bearing_to_station: float
    magnetic_bearing_to_station: float
    cdi_deflection_dots: float
    to_from_flag: str  # "TO", "FROM", "OFF"
    signal_strength_dbm: float
    snr_db: float
    morse_code: str
    failure_flag: bool  # True if warning flag dropped


@dataclass
class DMEEvaluation:
    is_received: bool
    is_in_los: bool
    is_in_doc: bool
    ground_dist_nm: float
    slant_range_nm: float
    altitude_diff_ft: float
    channel: str
    pulse_spacing_us: float  # 12 for X, 36 for Y
    reply_freq_mhz: float
    transponder_delay_us: float  # 50.0 us
    groundspeed_readout_kts: float
    time_to_station_min: float
    lock_status: str  # "LOCKED", "SEARCHING", "UNAVAILABLE"
    signal_strength_dbm: float
    morse_code: str


@dataclass
class NDBEvaluation:
    is_received: bool
    relative_bearing_deg: float
    qdm_magnetic_bearing: float
    qdr_magnetic_bearing: float
    true_bearing: float
    dist_nm: float
    field_strength_uv_m: float
    audio_tone_hz: int  # 1020 Hz
    morse_code: str
    advisory_night_effect: bool


@dataclass
class ILSEvaluation:
    is_received: bool
    loc_received: bool
    gp_received: bool
    loc_deflection_dots: float  # -5 to +5 (0.5 deg/dot)
    gp_deflection_dots: float   # -5 to +5 (0.14 deg/dot)
    loc_ddm: float             # Difference in depth of modulation
    gp_ddm: float
    runway_id: str
    runway_bearing_mag: float
    dist_to_touchdown_nm: float
    height_above_threshold_ft: float
    back_course: bool
    morse_code: str
    autoland_guidance_valid: bool


class VORStation:
    def __init__(self, record: NavaidRecord):
        self.record = record
        self.id = record.id
        self.name = record.name
        self.lat = record.lat
        self.lon = record.lon
        self.elev_ft = record.elevation_ft
        self.freq_mhz = record.freq_mhz
        self.declination = record.declination
        self.doc_nm = record.doc_range_nm
        self.morse = to_morse_code(record.id)

    def evaluate(
        self, ac_lat: float, ac_lon: float, ac_alt_ft: float, obs_deg: float
    ) -> VOREvaluation:
        dist_nm, brg_ac_to_st = great_circle_distance_bearing(
            ac_lat, ac_lon, self.lat, self.lon
        )
        _, brg_st_to_ac = great_circle_distance_bearing(
            self.lat, self.lon, ac_lat, ac_lon
        )

        # Magnetic radial from station = True bearing from station - Station Declination
        mag_radial = (brg_st_to_ac - self.declination + 360.0) % 360.0
        mag_bearing_to_st = (brg_ac_to_st - self.declination + 360.0) % 360.0

        # Line of sight check
        los_nm = radio_line_of_sight_nm(ac_alt_ft, self.elev_ft)
        in_los = dist_nm <= los_nm
        in_doc = dist_nm <= self.doc_nm

        # Cone of confusion
        in_cone = is_in_vor_cone_of_confusion(dist_nm, ac_alt_ft - self.elev_ft)

        # Terrain restriction check (e.g. BAL DVOR unusable R150-R170 below 5500ft outside 20NM)
        is_restricted = False
        for restr in self.record.restrictions:
            if restr.get("type") == "SECTOR_UNUSABLE":
                r_from = restr["from_radial"]
                r_to = restr["to_radial"]
                min_alt = restr.get("min_alt_ft", 0.0)
                min_dist = restr.get("min_dist_nm", 0.0)

                # Check if radial in sector
                in_sector = False
                if r_from <= r_to:
                    in_sector = r_from <= mag_radial <= r_to
                else:
                    in_sector = mag_radial >= r_from or mag_radial <= r_to

                if in_sector and ac_alt_ft < min_alt and dist_nm > min_dist:
                    is_restricted = True
                    break

        # CDI and TO/FROM
        deflection, to_from, in_ambiguity = calculate_vor_deviation(mag_radial, obs_deg)

        # Signal calculations
        fspl = free_space_path_loss_db(dist_nm, self.freq_mhz or 113.0)
        # Tx power ~ 100W (50 dBm), Tx gain 3 dBi, Rx gain 0 dBi
        rx_power = 50.0 + 3.0 - fspl
        snr = max(0.0, rx_power - (-110.0))  # Noise floor ~ -110 dBm

        is_received = in_los and in_doc and not is_restricted and snr > 12.0
        failure_flag = (not is_received) or in_cone or in_ambiguity

        if in_cone:
            to_from = "OFF"
            deflection = 0.0

        return VOREvaluation(
            is_received=is_received,
            is_in_los=in_los,
            is_in_doc=in_doc,
            is_in_cone_of_confusion=in_cone,
            is_terrain_restricted=is_restricted,
            radial_deg=round(mag_radial, 2),
            true_bearing_to_station=round(brg_ac_to_st, 2),
            magnetic_bearing_to_station=round(mag_bearing_to_st, 2),
            cdi_deflection_dots=round(deflection, 2),
            to_from_flag=to_from,
            signal_strength_dbm=round(rx_power, 1),
            snr_db=round(snr, 1),
            morse_code=self.morse,
            failure_flag=failure_flag,
        )


class DMEStation:
    def __init__(self, record: NavaidRecord):
        self.record = record
        self.id = record.id
        self.name = record.name
        self.lat = record.lat
        self.lon = record.lon
        self.elev_ft = record.elevation_ft
        self.freq_mhz = record.freq_mhz
        self.channel = record.channel or "80X"
        self.doc_nm = record.doc_range_nm
        self.morse = to_morse_code(record.id)

    def evaluate(
        self,
        ac_lat: float,
        ac_lon: float,
        ac_alt_ft: float,
        ac_groundspeed_kts: float = 250.0,
    ) -> DMEEvaluation:
        ground_dist_nm, _ = great_circle_distance_bearing(
            ac_lat, ac_lon, self.lat, self.lon
        )
        alt_diff_ft = ac_alt_ft - self.elev_ft
        slant_range_nm = calculate_slant_range_nm(ground_dist_nm, alt_diff_ft)

        los_nm = radio_line_of_sight_nm(ac_alt_ft, self.elev_ft)
        in_los = ground_dist_nm <= los_nm
        in_doc = ground_dist_nm <= self.doc_nm

        # Channel pulse spacing
        is_y_channel = "Y" in self.channel.upper()
        pulse_spacing = 36.0 if is_y_channel else 12.0

        # Frequency pair
        reply_freq = (
            self.freq_mhz + 63.0 if self.freq_mhz < 1000.0 else self.freq_mhz
        )

        fspl = free_space_path_loss_db(slant_range_nm, 1030.0)
        # Interrogator Tx 300W (54.8 dBm), Transponder 1kW (60 dBm)
        rx_power = 60.0 + 9.0 - fspl

        is_received = in_los and in_doc and rx_power > -95.0
        lock_status = "LOCKED" if is_received else "SEARCHING"

        # Time to station estimate
        tts_min = (
            (slant_range_nm / max(10.0, ac_groundspeed_kts)) * 60.0
            if is_received
            else 0.0
        )

        return DMEEvaluation(
            is_received=is_received,
            is_in_los=in_los,
            is_in_doc=in_doc,
            ground_dist_nm=round(ground_dist_nm, 2),
            slant_range_nm=round(slant_range_nm, 2) if is_received else 0.0,
            altitude_diff_ft=round(alt_diff_ft, 1),
            channel=self.channel,
            pulse_spacing_us=pulse_spacing,
            reply_freq_mhz=round(reply_freq, 3),
            transponder_delay_us=50.0,
            groundspeed_readout_kts=round(ac_groundspeed_kts, 1) if is_received else 0.0,
            time_to_station_min=round(tts_min, 1) if is_received else 0.0,
            lock_status=lock_status,
            signal_strength_dbm=round(rx_power, 1),
            morse_code=self.morse,
        )


class NDBStation:
    def __init__(self, record: NavaidRecord):
        self.record = record
        self.id = record.id
        self.name = record.name
        self.lat = record.lat
        self.lon = record.lon
        self.freq_khz = (record.freq_mhz or 0.387) * 1000.0
        self.doc_nm = record.doc_range_nm
        self.morse = to_morse_code(record.id)

    def evaluate(
        self, ac_lat: float, ac_lon: float, ac_hdg_mag: float
    ) -> NDBEvaluation:
        dist_nm, brg_to_st = great_circle_distance_bearing(
            ac_lat, ac_lon, self.lat, self.lon
        )
        mag_var = get_regional_magnetic_variation(ac_lat, ac_lon)
        mag_brg_to_st = (brg_to_st - mag_var + 360.0) % 360.0

        rel_brg = calculate_ndb_relative_bearing(ac_hdg_mag, mag_brg_to_st)
        qdm = (ac_hdg_mag + rel_brg) % 360.0
        qdr = (qdm + 180.0) % 360.0

        # Groundwave attenuation: field strength in uV/m
        # E = 300 * sqrt(P_kW) / d_km
        dist_km = max(0.5, dist_nm * 1.852)
        field_strength = (300.0 * math.sqrt(0.1)) / dist_km * 1000.0  # uV/m
        # Ground absorption factor
        field_strength *= math.exp(-dist_km / 120.0)

        is_received = dist_nm <= (self.doc_nm * 1.3) and field_strength > 25.0

        return NDBEvaluation(
            is_received=is_received,
            relative_bearing_deg=round(rel_brg, 1),
            qdm_magnetic_bearing=round(qdm, 1),
            qdr_magnetic_bearing=round(qdr, 1),
            true_bearing=round(brg_to_st, 1),
            dist_nm=round(dist_nm, 2),
            field_strength_uv_m=round(field_strength, 1),
            audio_tone_hz=1020,
            morse_code=self.morse,
            advisory_night_effect=dist_nm > 40.0,
        )


class ILSStation:
    def __init__(
        self,
        loc_record: NavaidRecord,
        gp_record: Optional[NavaidRecord] = None,
    ):
        self.loc_rec = loc_record
        self.gp_rec = gp_record
        self.id = loc_record.id
        self.name = loc_record.name
        self.rwy_id = loc_record.runway_id or "24"
        self.rwy_bearing_mag = loc_record.runway_bearing_mag or 236.0
        self.thr_lat = loc_record.runway_thr_lat or loc_record.lat
        self.thr_lon = loc_record.runway_thr_lon or loc_record.lon
        self.thr_elev_ft = loc_record.elevation_ft
        self.morse = to_morse_code(loc_record.id)

        # True physical runway centerline bearing (from threshold straight to localizer antenna)
        if loc_record.runway_thr_lat is not None and (
            loc_record.runway_thr_lat != loc_record.lat or loc_record.runway_thr_lon != loc_record.lon
        ):
            _, true_brg = great_circle_distance_bearing(
                self.thr_lat, self.thr_lon, loc_record.lat, loc_record.lon
            )
            self.rwy_bearing_true = round(true_brg, 4)
        else:
            self.rwy_bearing_true = (
                loc_record.runway_bearing_true
                if loc_record.runway_bearing_true is not None
                else ((self.rwy_bearing_mag + (loc_record.declination or -4.0) + 360.0) % 360.0)
            )

    def evaluate(
        self, ac_lat: float, ac_lon: float, ac_alt_ft: float
    ) -> ILSEvaluation:
        dist_nm, brg_from_thr = great_circle_distance_bearing(
            self.thr_lat, self.thr_lon, ac_lat, ac_lon
        )

        # Inbound course and reciprocal (true bearing along runway physical centerline)
        inbound_true = self.rwy_bearing_true
        recip_true = (inbound_true + 180.0) % 360.0

        # Along-track distance from runway threshold along final approach course (NM)
        # Angle from threshold towards aircraft relative to approach direction
        angle_off_recip = (brg_from_thr - recip_true + 540.0) % 360.0 - 180.0
        d_along_thr_nm = dist_nm * math.cos(math.radians(angle_off_recip))

        # Localizer antenna is positioned at the stop end of the runway
        # Bearing from localizer antenna to aircraft relative to approach axis
        dist_from_loc, brg_from_loc = great_circle_distance_bearing(
            self.loc_rec.lat, self.loc_rec.lon, ac_lat, ac_lon
        )
        delta_angle = (brg_from_loc - recip_true + 540.0) % 360.0 - 180.0

        # Localizer coverage check: +/- 35° within 10 NM; +/- 10° up to 25 NM; valid on runway rollout
        abs_delta = abs(delta_angle)
        loc_valid = False
        if dist_nm <= 10.0 and abs_delta <= 35.0:
            loc_valid = True
        elif dist_nm <= 25.0 and abs_delta <= 10.0:
            loc_valid = True
        elif d_along_thr_nm >= -0.3 and abs_delta <= 10.0:
            # Aircraft on runway surface during threshold crossing and rollout
            loc_valid = True

        # Needle deflects toward runway centerline (0.5 deg/dot on 5 dots)
        loc_deflection = max(-5.0, min(5.0, -delta_angle / 0.5))

        # Distance to Glide Path Touchdown Aim Point (300m = 0.162 NM past threshold)
        dist_to_tdz_nm = d_along_thr_nm + 0.162
        dist_to_tdz_ft = max(50.0, dist_to_tdz_nm * 6076.11548)

        # Glideslope deviation
        h_above_thr = max(0.0, ac_alt_ft - self.thr_elev_ft)
        current_gp_angle = math.degrees(math.atan2(h_above_thr, dist_to_tdz_ft))

        # Coverage check: within 12 NM, valid localizer, and sensible glideslope angle
        gp_valid = (dist_to_tdz_nm <= 12.0 and 1.35 <= current_gp_angle <= 6.0 and loc_valid)

        # Deviation from nominal 3.0° glide slope (0.14 deg/dot on 5 dots)
        # Above path -> needle deflects DOWN (-); Below path -> needle deflects UP (+)
        gp_deflection = max(-5.0, min(5.0, (3.0 - current_gp_angle) / 0.14))

        # Difference in depth of modulation (DDM)
        loc_ddm = (loc_deflection / 5.0) * 0.155
        gp_ddm = (gp_deflection / 5.0) * 0.175

        autoland_valid = (
            loc_valid
            and gp_valid
            and abs(loc_deflection) < 0.5
            and abs(gp_deflection) < 0.5
            and d_along_thr_nm <= 10.0
        )

        return ILSEvaluation(
            is_received=loc_valid,
            loc_received=loc_valid,
            gp_received=gp_valid,
            loc_deflection_dots=round(loc_deflection, 2),
            gp_deflection_dots=round(gp_deflection, 2),
            loc_ddm=round(loc_ddm, 4),
            gp_ddm=round(gp_ddm, 4),
            runway_id=self.rwy_id,
            runway_bearing_mag=round(self.rwy_bearing_mag, 1),
            dist_to_touchdown_nm=round(max(0.0, d_along_thr_nm), 2),
            height_above_threshold_ft=round(h_above_thr, 1),
            back_course=False,
            morse_code=self.morse,
            autoland_guidance_valid=autoland_valid,
        )


class GNSSSystem:
    """Multi-constellation GPS & Galileo satellite navigation system."""

    def __init__(self):
        # Realistic representative constellation satellites over Ireland
        self.satellites = [
            {"prn": "G03", "constellation": "GPS", "azimuth": 42.0, "elevation": 68.0, "snr_db": 49.0, "tracked": True},
            {"prn": "G07", "constellation": "GPS", "azimuth": 115.0, "elevation": 45.0, "snr_db": 46.0, "tracked": True},
            {"prn": "G09", "constellation": "GPS", "azimuth": 185.0, "elevation": 72.0, "snr_db": 50.0, "tracked": True},
            {"prn": "G12", "constellation": "GPS", "azimuth": 260.0, "elevation": 32.0, "snr_db": 43.0, "tracked": True},
            {"prn": "G15", "constellation": "GPS", "azimuth": 310.0, "elevation": 55.0, "snr_db": 47.0, "tracked": True},
            {"prn": "G18", "constellation": "GPS", "azimuth": 15.0, "elevation": 28.0, "snr_db": 41.0, "tracked": True},
            {"prn": "G22", "constellation": "GPS", "azimuth": 140.0, "elevation": 50.0, "snr_db": 48.0, "tracked": True},
            {"prn": "G28", "constellation": "GPS", "azimuth": 215.0, "elevation": 60.0, "snr_db": 49.0, "tracked": True},
            {"prn": "E09", "constellation": "Galileo", "azimuth": 80.0, "elevation": 38.0, "snr_db": 44.0, "tracked": True},
            {"prn": "E15", "constellation": "Galileo", "azimuth": 335.0, "elevation": 42.0, "snr_db": 45.0, "tracked": True},
        ]

    def evaluate(self, ac_lat: float, ac_lon: float, ac_alt_ft: float) -> Dict[str, Any]:
        dop = compute_gnss_dop_metrics(self.satellites)
        tracked_count = len([s for s in self.satellites if s["tracked"]])

        # Receiver Autonomous Integrity Monitoring (RAIM)
        # Horizontal Protection Level (HPL) ~ 3.5 * HDOP * sigma_pseudorange (~5m)
        hpl_m = round(dop["hdop"] * 15.0, 1)
        vpl_m = round(dop["vdop"] * 22.0, 1)

        # Alert limit checks (HAL): En-route = 2 NM (3704m), Terminal = 1 NM (1852m), Approach = 0.3 NM (556m)
        raim_status = "INTEGRITY_OK" if hpl_m < 556.0 else "INTEGRITY_CAUTION"

        return {
            "mode": "3D_FIX_SBAS_AUGMENTED",
            "satellites_tracked": tracked_count,
            "satellites_total": len(self.satellites),
            "hdop": dop["hdop"],
            "vdop": dop["vdop"],
            "pdop": dop["pdop"],
            "hpl_meters": hpl_m,
            "vpl_meters": vpl_m,
            "raim_status": raim_status,
            "satellites": self.satellites,
            "geodetic_lat": ac_lat,
            "geodetic_lon": ac_lon,
            "altitude_msl_ft": ac_alt_ft,
            "altitude_msl_m": round(ac_alt_ft * 0.3048, 1),
        }

