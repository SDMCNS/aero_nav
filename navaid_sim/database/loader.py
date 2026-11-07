"""
Airspace and navigation data loader.
Ingests and cross-references FIR boundary data (FIR.csv), en-route navaids (Navaids.txt),
and detailed aerodrome data (EINN.txt, EIDW.txt, EICK.txt).
"""

import csv
import json
import os
import re
import math
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple

from navaid_sim.core.geo import (
    parse_dms_coord,
    get_regional_magnetic_variation,
    destination_point,
    great_circle_distance_bearing,
)


@dataclass
class NavaidRecord:
    id: str
    name: str
    type: str  # DVOR/DME, DVOR, DME, NDB, ILS_LOC, ILS_GP
    frequency: str
    freq_mhz: float
    lat: float
    lon: float
    elevation_ft: float = 0.0
    channel: Optional[str] = None
    declination: float = -3.0
    doc_range_nm: float = 100.0
    remarks: str = ""
    associated_airport: Optional[str] = None
    runway_id: Optional[str] = None
    runway_bearing_mag: Optional[float] = None
    runway_bearing_true: Optional[float] = None
    runway_thr_lat: Optional[float] = None
    runway_thr_lon: Optional[float] = None
    restrictions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class RunwayRecord:
    designation: str
    true_bearing_deg: float
    magnetic_bearing_deg: float
    dimensions_m: str
    thr_lat: float
    thr_lon: float
    end_lat: float
    end_lon: float
    thr_elevation_ft: float
    ils_loc_id: Optional[str] = None
    ils_loc_freq: Optional[float] = None
    ils_gp_freq: Optional[float] = None


@dataclass
class AirportRecord:
    identifier: str  # EINN, EIDW, EICK
    name: str
    arp_lat: float
    arp_lon: float
    elevation_ft: float
    magnetic_variation: str
    mag_var_deg: float
    comms: List[Dict[str, str]] = field(default_factory=list)
    runways: List[RunwayRecord] = field(default_factory=list)
    navaids: List[NavaidRecord] = field(default_factory=list)


@dataclass
class AirspaceBoundary:
    airspace_id: str  # EISNFIR, EISNUIR
    min_fl: int
    max_fl: int
    coordinates: List[Tuple[float, float]]  # [(lat, lon), ...]


@dataclass
class WaypointRecord:
    name: str
    lat: float
    lon: float
    type: str  # ENROUTE, OCEANIC_ENTRY, STAR, SID, APPROACH
    description: str = ""


class AirspaceDatabase:
    """Central repository of Irish airspace geometry, facilities, and procedures."""

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            # Check bundled package data directory first
            bundled = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
            if os.path.exists(os.path.join(bundled, "FIR.csv")):
                data_dir = bundled
            else:
                data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.data_dir = data_dir

        self.fir_boundaries: Dict[str, AirspaceBoundary] = {}
        self.navaids: Dict[str, NavaidRecord] = {}
        self.airports: Dict[str, AirportRecord] = {}
        self.waypoints: Dict[str, WaypointRecord] = {}

        self.load_all()

    def load_all(self):
        self._load_fir_csv()
        self._load_enroute_navaids()
        self._load_airports()
        self._load_standard_waypoints()

    def _load_fir_csv(self):
        csv_path = os.path.join(self.data_dir, "FIR.csv")
        if not os.path.exists(csv_path):
            return

        boundaries: Dict[str, List[Dict[str, Any]]] = {}
        with open(csv_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                airspace_id = row.get("Airspace ID", "").strip()
                if not airspace_id.startswith("EI"):
                    continue

                try:
                    seq = int(row.get("Sequence Number", 0))
                    lat = float(row.get("Latitude", 0.0))
                    lon = float(row.get("Longitude", 0.0))
                    min_fl = int(row.get("Min Flight Level", 0))
                    max_fl = int(row.get("Max Flight Level", 999))
                except ValueError:
                    continue

                if airspace_id not in boundaries:
                    boundaries[airspace_id] = []
                boundaries[airspace_id].append({
                    "seq": seq,
                    "lat": lat,
                    "lon": lon,
                    "min_fl": min_fl,
                    "max_fl": max_fl,
                })

        for aid, pts in boundaries.items():
            pts.sort(key=lambda x: x["seq"])
            coords = [(p["lat"], p["lon"]) for p in pts]
            min_fl = pts[0]["min_fl"]
            max_fl = pts[0]["max_fl"]
            self.fir_boundaries[aid] = AirspaceBoundary(
                airspace_id=aid,
                min_fl=min_fl,
                max_fl=max_fl,
                coordinates=coords,
            )

    def _parse_elevation(self, elev_str: Optional[str]) -> float:
        if not elev_str:
            return 0.0
        m = re.search(r"(\d+)\s*(?:ft|FT)", elev_str)
        if m:
            return float(m.group(1))
        try:
            return float(elev_str)
        except ValueError:
            return 0.0

    def _parse_frequency_mhz(self, freq_str: Optional[str]) -> float:
        if not freq_str:
            return 0.0
        # Check for kHz
        m_khz = re.search(r"([0-9.]+)\s*k(?:Hz|HZ)", freq_str)
        if m_khz:
            return float(m_khz.group(1)) / 1000.0
        # Check for MHz
        m_mhz = re.search(r"([0-9.]+)\s*M(?:Hz|HZ)", freq_str)
        if m_mhz:
            return float(m_mhz.group(1))
        try:
            return float(freq_str)
        except ValueError:
            return 0.0

    def _parse_restrictions_from_remarks(self, remarks: str) -> List[Dict[str, Any]]:
        restrictions = []
        if not remarks:
            return restrictions

        # Example: BAL DVOR unusable in sector R150 to R170 below 5500ft AMSL outside 20NM
        m_bal = re.search(r"unusable in sector R(\d+) to R(\d+) below (\d+)ft.*?outside (\d+)NM", remarks)
        if m_bal:
            restrictions.append({
                "type": "SECTOR_UNUSABLE",
                "from_radial": float(m_bal.group(1)),
                "to_radial": float(m_bal.group(2)),
                "min_alt_ft": float(m_bal.group(3)),
                "min_dist_nm": float(m_bal.group(4)),
                "reason": "Terrain shadowing",
            })

        # Example: KLY NDB Aircraft may not obtain guidance beyond 45NM below 8000ft, in the sector between bearings 180° and 270° M
        m_kly = re.search(r"beyond (\d+)NM below (\d+)ft.*?sector between bearings (\d+)° and (\d+)°", remarks)
        if m_kly:
            restrictions.append({
                "type": "SECTOR_UNUSABLE",
                "from_radial": float(m_kly.group(3)),
                "to_radial": float(m_kly.group(4)),
                "min_alt_ft": float(m_kly.group(2)),
                "min_dist_nm": float(m_kly.group(1)),
                "reason": "Mountains terrain shielding",
            })

        return restrictions

    def _load_enroute_navaids(self):
        json_path = os.path.join(self.data_dir, "Navaids.txt")
        if not os.path.exists(json_path):
            return

        with open(json_path, mode="r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            nid = item.get("id")
            name = item.get("name", "")
            raw_coords = item.get("coordinates")
            coords = parse_dms_coord(raw_coords)
            if not coords:
                continue

            # Determine type
            if "DVOR/DME" in name or "DVOR/DME" in item.get("frequency_or_channel", ""):
                nav_type = "DVOR/DME"
            elif "DVOR" in name or "VOR" in name:
                nav_type = "DVOR"
            elif "DME" in name:
                nav_type = "DME"
            elif "NDB" in name:
                nav_type = "NDB"
            else:
                nav_type = "VOR"

            freq_raw = item.get("frequency_or_channel", "")
            freq_mhz = self._parse_frequency_mhz(freq_raw)
            channel = None
            m_ch = re.search(r"CH\s*(\w+)", freq_raw)
            if m_ch:
                channel = m_ch.group(1)

            elevation_ft = self._parse_elevation(item.get("elevation_dme_antenna"))
            remarks = item.get("remarks") or ""

            # Declination
            declination = get_regional_magnetic_variation(coords[0], coords[1])
            m_decl = re.search(r"decl\.?:?\s*(\d+)°W", remarks)
            if m_decl:
                declination = -float(m_decl.group(1))

            # DOC Range
            doc_range = 100.0 if "DME" in nav_type or "VOR" in nav_type else 50.0
            m_doc = re.search(r"DOC\s*(\d+)NM?", remarks)
            if m_doc:
                doc_range = float(m_doc.group(1))
            elif "Range 50NM" in remarks:
                doc_range = 50.0

            restrictions = self._parse_restrictions_from_remarks(remarks)

            record_key = f"{nid}_{nav_type.replace('/', '_')}"
            rec = NavaidRecord(
                id=nid,
                name=name,
                type=nav_type,
                frequency=freq_raw,
                freq_mhz=freq_mhz,
                lat=coords[0],
                lon=coords[1],
                elevation_ft=elevation_ft,
                channel=channel,
                declination=declination,
                doc_range_nm=doc_range,
                remarks=remarks,
                restrictions=restrictions,
            )
            self.navaids[record_key] = rec

    def _load_airports(self):
        airport_files = ["EINN.txt", "EIDW.txt", "EICK.txt"]
        for ap_file in airport_files:
            file_path = os.path.join(self.data_dir, ap_file)
            if not os.path.exists(file_path):
                continue

            with open(file_path, mode="r", encoding="utf-8") as f:
                data = json.load(f)

            ident = data.get("aerodrome_identifier")
            name = data.get("name", "")
            geo_data = data.get("geographical_and_administrative_data", {})
            arp_coords = parse_dms_coord(geo_data.get("arp_coordinates"))
            if not arp_coords:
                continue

            elev_str = geo_data.get("elevation_reference_temperature_mean_low", "")
            elev_ft = self._parse_elevation(elev_str)
            mag_var = geo_data.get("magnetic_variation", "03° W")
            m_mv = re.search(r"(\d+)º?\s*W", mag_var)
            mag_var_deg = -float(m_mv.group(1)) if m_mv else get_regional_magnetic_variation(arp_coords[0], arp_coords[1])

            # Comms facilities
            comms = []
            for c in data.get("ats_communications_facilities", []):
                comms.append({
                    "service": c.get("service", ""),
                    "call_sign": c.get("call_sign", ""),
                    "frequency": c.get("frequency", ""),
                    "hours": c.get("hours", ""),
                })

            # Runways
            runway_records = []
            for r in data.get("runway_physical_characteristics", []):
                desig = r.get("designation", "")
                true_brg_str = r.get("true_bearing", "0")
                m_brg = re.search(r"([0-9.]+)", true_brg_str)
                true_brg = float(m_brg.group(1)) if m_brg else 0.0
                mag_brg = (true_brg - mag_var_deg + 360.0) % 360.0

                thr_c = parse_dms_coord(r.get("thr_coordinates")) or arp_coords
                end_c = parse_dms_coord(r.get("rwy_end_coordinates")) or thr_c
                thr_elev = self._parse_elevation(r.get("thr_elevation"))

                rwy_rec = RunwayRecord(
                    designation=desig,
                    true_bearing_deg=true_brg,
                    magnetic_bearing_deg=round(mag_brg, 2),
                    dimensions_m=r.get("dimensions", ""),
                    thr_lat=thr_c[0],
                    thr_lon=thr_c[1],
                    end_lat=end_c[0],
                    end_lon=end_c[1],
                    thr_elevation_ft=thr_elev or elev_ft,
                )
                runway_records.append(rwy_rec)

            airport_navaids = []
            # Radio Navigation and landing aids
            for aid in data.get("radio_navigation_and_landing_aids", []):
                aid_type = aid.get("type", "")
                aid_id = aid.get("id", "")
                raw_c = aid.get("coordinates")
                c = parse_dms_coord(raw_c)
                if not c:
                    continue

                freq_raw = aid.get("frequency", "")
                freq_mhz = self._parse_frequency_mhz(freq_raw)
                elev_ft_aid = self._parse_elevation(aid.get("elevation")) or elev_ft

                nav_cat = "OTHER"
                if "DVOR/DME" in aid_type or "DVOR" in aid_type:
                    nav_cat = "DVOR/DME"
                elif "ILS LOC" in aid_type:
                    nav_cat = "ILS_LOC"
                elif "ILS GP" in aid_type:
                    nav_cat = "ILS_GP"

                # Link with runway if it's ILS
                rwy_id = None
                rwy_mag_hdg = None
                rwy_true_hdg = None
                rwy_thr_lat = None
                rwy_thr_lon = None
                rwy_thr_elev = None
                m_rwy = re.search(r"RWY\s*(\d+[LRC]?)", aid_type)
                if m_rwy:
                    rwy_id = m_rwy.group(1)
                    for rw in runway_records:
                        if rw.designation == rwy_id:
                            rwy_mag_hdg = rw.magnetic_bearing_deg
                            rwy_true_hdg = rw.true_bearing_deg
                            rwy_thr_lat = rw.thr_lat
                            rwy_thr_lon = rw.thr_lon
                            rwy_thr_elev = rw.thr_elevation_ft
                            if nav_cat == "ILS_LOC":
                                rw.ils_loc_id = aid_id
                                rw.ils_loc_freq = freq_mhz
                            elif nav_cat == "ILS_GP":
                                rw.ils_gp_freq = freq_mhz

                record_key = f"{ident}_{aid_id or nav_cat}_{rwy_id or ''}".rstrip("_")
                nav_rec = NavaidRecord(
                    id=aid_id or f"{ident}_{nav_cat}",
                    name=f"{ident} {aid_type}",
                    type=nav_cat,
                    frequency=freq_raw,
                    freq_mhz=freq_mhz,
                    lat=c[0],
                    lon=c[1],
                    elevation_ft=rwy_thr_elev if rwy_thr_elev is not None else elev_ft_aid,
                    declination=mag_var_deg,
                    doc_range_nm=25.0 if "ILS" in nav_cat else 100.0,
                    remarks=f"Aerodrome {ident} landing aid",
                    associated_airport=ident,
                    runway_id=rwy_id,
                    runway_bearing_mag=rwy_mag_hdg,
                    runway_bearing_true=rwy_true_hdg,
                    runway_thr_lat=rwy_thr_lat,
                    runway_thr_lon=rwy_thr_lon,
                )
                self.navaids[record_key] = nav_rec
                airport_navaids.append(nav_rec)

            ap_rec = AirportRecord(
                identifier=ident,
                name=name,
                arp_lat=arp_coords[0],
                arp_lon=arp_coords[1],
                elevation_ft=elev_ft,
                magnetic_variation=mag_var,
                mag_var_deg=mag_var_deg,
                comms=comms,
                runways=runway_records,
                navaids=airport_navaids,
            )
            self.airports[ident] = ap_rec

    def _load_standard_waypoints(self):
        """Loads official waypoints from IE_Waypoints.txt and supplements terminal fixes."""
        wp_file = os.path.join(self.data_dir, "IE_Waypoints.txt")
        if os.path.exists(wp_file):
            try:
                with open(wp_file, mode="r", encoding="utf-8") as f:
                    wp_data = json.load(f)
                for item in wp_data:
                    name = item.get("name_code_designator", "").strip()
                    raw_coords = item.get("coordinates")
                    coords = parse_dms_coord(raw_coords)
                    if not coords or not name:
                        continue
                    remarks = (item.get("remarks") or "").strip()
                    wp_type = "ENROUTE"
                    if "Oceanic" in remarks:
                        wp_type = "OCEANIC"
                    elif "Holding" in remarks:
                        wp_type = "HOLDING"
                    elif "Avoidance" in remarks:
                        wp_type = "AVOIDANCE"

                    self.waypoints[name] = WaypointRecord(
                        name=name,
                        lat=coords[0],
                        lon=coords[1],
                        type=wp_type,
                        description=remarks or f"Irish FIR Fix {name}",
                    )
            except Exception as e:
                print(f"Warning: Failed loading IE_Waypoints.txt: {e}")

        # Supplement with precision ILS terminal final approach fixes aligned on runway extended centerlines
        for ap in self.airports.values():
            for rw in ap.runways:
                if rw.ils_loc_id and rw.thr_lat and rw.thr_lon and rw.end_lat and rw.end_lon:
                    _, out_brg = great_circle_distance_bearing(rw.end_lat, rw.end_lon, rw.thr_lat, rw.thr_lon)
                    faf_lat, faf_lon = destination_point(rw.thr_lat, rw.thr_lon, out_brg, 5.0)
                    nominal_alt = rw.thr_elevation_ft + 50.0 + 5.0 * 6076.11548 * math.tan(math.radians(3.0))
                    faf_name = f"FAF{rw.designation}"
                    self.waypoints[faf_name] = WaypointRecord(
                        name=faf_name,
                        lat=round(faf_lat, 6),
                        lon=round(faf_lon, 6),
                        type="APPROACH",
                        description=f"{ap.name} ILS RWY {rw.designation} Final Approach Fix (5.0 NM, {nominal_alt:.0f}ft)",
                    )

    def to_geojson(self) -> Dict[str, Any]:
        """Exports airspace boundaries, navaids, and airports as standard GeoJSON."""
        features = []

        # Boundaries
        for aid, b in self.fir_boundaries.items():
            features.append({
                "type": "Feature",
                "properties": {
                    "feature_type": "AIRSPACE_BOUNDARY",
                    "id": aid,
                    "min_fl": b.min_fl,
                    "max_fl": b.max_fl,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[lon, lat] for lat, lon in b.coordinates]],
                },
            })

        # Navaids
        for key, n in self.navaids.items():
            features.append({
                "type": "Feature",
                "properties": {
                    "feature_type": "NAVAID",
                    "key": key,
                    "id": n.id,
                    "name": n.name,
                    "type": n.type,
                    "frequency": n.frequency,
                    "elevation_ft": n.elevation_ft,
                    "doc_range_nm": n.doc_range_nm,
                    "declination": n.declination,
                    "associated_airport": n.associated_airport,
                    "runway_id": n.runway_id,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [n.lon, n.lat],
                },
            })

        # Airports
        for ident, ap in self.airports.items():
            features.append({
                "type": "Feature",
                "properties": {
                    "feature_type": "AIRPORT",
                    "id": ident,
                    "name": ap.name,
                    "elevation_ft": ap.elevation_ft,
                    "magnetic_variation": ap.magnetic_variation,
                    "runways": [asdict(r) for r in ap.runways],
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [ap.arp_lon, ap.arp_lat],
                },
            })

        # Waypoints
        for name, wp in self.waypoints.items():
            features.append({
                "type": "Feature",
                "properties": {
                    "feature_type": "WAYPOINT",
                    "name": name,
                    "type": wp.type,
                    "description": wp.description,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [wp.lon, wp.lat],
                },
            })

        return {"type": "FeatureCollection", "features": features}

