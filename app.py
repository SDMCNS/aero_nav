import datetime
import json
import math
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import urllib.request

# --- MODERN HEADERS INJECTION FOR PYTHON 3.13+ ---
# Installs a default global opener with browser headers to avoid 403 blocks
opener = urllib.request.build_opener()
opener.addheaders = [
    (
        "User-Agent",
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            " AviationNavaidSim/2.0"
        ),
    ),
    ("Accept", "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"),
    ("Referer", "https://www.google.com/"),
]
urllib.request.install_opener(opener)

# Import tkintermapview for real map tiles
try:
  import tkintermapview
except ImportError:
  root = tk.Tk()
  root.withdraw()
  messagebox.showerror(
      "Missing Dependency",
      "The 'tkintermapview' library is required to show real maps.\n\nPlease"
      " install it via terminal:\npip install tkintermapview",
  )
  exit(1)

# --- DEFAULT NAVAID DATASET (Ireland + GNSS) ---
NAVAIDS = [
    {
        "name": "GNSS / GPS CONSTELLATION",
        "id": "GNSS",
        "type": "GNSS",
        "frequency": "1575.42MHz (L1 C/A)",
        "lat": 0.0,
        "lon": 0.0,
        "elevation": 0,
        "remarks": (
            "Multi-constellation GPS/GLONASS/Galileo space-based positioning."
        ),
    },
    {
        "name": "BALDONNEL DVOR/DME",
        "id": "BAL",
        "type": "DVOR/DME",
        "frequency": "115.8MHz CH 105X",
        "lat": 53.2999,
        "lon": -6.4478,
        "elevation": 300,
        "remarks": "DVOR unusable R150-R170 below 5500ft outside 20NM.",
    },
    {
        "name": "CLONMEL NDB",
        "id": "CML",
        "type": "NDB",
        "frequency": "387kHz",
        "lat": 52.4538,
        "lon": -7.4801,
        "elevation": 0,
        "remarks": "Range 50NM. ADF radio beacon.",
    },
    {
        "name": "CONNAUGHT DVOR/DME",
        "id": "CON",
        "type": "DVOR/DME",
        "frequency": "117.4MHz CH 121X",
        "lat": 53.9080,
        "lon": -8.8201,
        "elevation": 600,
        "remarks": "Standard Doppler VOR + DME interrogator.",
    },
    {
        "name": "CORK DVOR/DME",
        "id": "CRK",
        "type": "DVOR/DME",
        "frequency": "114.6MHz CH 93X",
        "lat": 51.8406,
        "lon": -8.4943,
        "elevation": 500,
        "remarks": "Standard DVOR/DME facility.",
    },
    {
        "name": "DONEGAL NDB",
        "id": "CFN",
        "type": "NDB",
        "frequency": "361kHz",
        "lat": 55.0440,
        "lon": -8.3393,
        "elevation": 0,
        "remarks": "DOC 25NM NDB.",
    },
    {
        "name": "DUBLIN DVOR/DME",
        "id": "DUB",
        "type": "DVOR/DME",
        "frequency": "114.9MHz CH 96X",
        "lat": 53.4994,
        "lon": -6.3071,
        "elevation": 200,
        "remarks": "Primary international airport navaid.",
    },
    {
        "name": "SHANNON DVOR/DME",
        "id": "SHA",
        "type": "DVOR/DME",
        "frequency": "113.3MHz CH 80X",
        "lat": 52.7210,
        "lon": -8.8852,
        "elevation": 200,
        "remarks": "Atlantic gateway VOR/DME.",
    },
    {
        "name": "WOLFTRAP DME",
        "id": "WTP",
        "type": "DME",
        "frequency": "116.3MHz CH 110X",
        "lat": 53.0959,
        "lon": -7.5913,
        "elevation": 1700,
        "remarks": "Standalone DME facility.",
    },
]


def parse_dms_coord(coord_input):
  if isinstance(coord_input, (int, float)):
    return float(coord_input), 0.0

  try:
    coord_str = str(coord_input).strip().upper()
    if "." in coord_str and "N" not in coord_str and "S" not in coord_str:
      return float(coord_str), 0.0

    lat_part = (
        coord_str.split("N")[0] if "N" in coord_str else coord_str.split("S")[0]
    )
    lon_part = (
        coord_str.split("W")[0] if "W" in coord_str else coord_str.split("E")[0]
    )

    lat_deg = float(lat_part[:2])
    lat_min = float(lat_part[2:4])
    lat_sec = float(lat_part[4:])
    lat = lat_deg + lat_min / 60.0 + lat_sec / 3600.0
    if "S" in coord_str:
      lat = -lat

    lon_deg = float(lon_part[:3])
    lon_min = float(lon_part[3:5])
    lon_sec = float(lon_part[5:])
    lon = lon_deg + lon_min / 60.0 + lon_sec / 3600.0
    if "W" in coord_str:
      lon = -lon

    return lat, lon
  except Exception:
    return 53.3498, -6.2603


def calculate_distance_bearing(lat1, lon1, lat2, lon2):
  R = 3440.065
  phi1, phi2 = math.radians(lat1), math.radians(lat2)
  dphi = math.radians(lat2 - lat1)
  dlam = math.radians(lon2 - lon1)

  a = max(
      0.0,
      min(
          1.0,
          math.sin(dphi / 2) ** 2
          + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2,
      ),
  )
  c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
  dist = R * c

  y = math.sin(dlam) * math.cos(phi2)
  x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(
      phi2
  ) * math.cos(dlam)
  bearing = (math.degrees(math.atan2(y, x)) + 360) % 360
  return dist, bearing


def generate_arinc429_word(label_octal, data_value):
  label_int = int(label_octal, 8)
  label_bits = format(label_int, "08b")[::-1]
  sdi_bits = "01"
  data_int = int(max(0, min(data_value, 524287)))
  data_bits = format(data_int, "019b")
  ssm_bits = "10"
  payload = label_bits + sdi_bits + data_bits + ssm_bits
  ones_count = payload.count("1")
  parity_bit = "0" if (ones_count % 2 != 0) else "1"
  full_word_bin = payload + parity_bit
  hex_val = f"0x{int(full_word_bin, 2):08X}"
  return full_word_bin, hex_val


class AviationSimApp:

  def __init__(self, root):
    self.root = root
    self.root.title("✈️ Advanced Cockpit Avionics Simulator & Technical Suite")
    self.root.geometry("1520x1020")
    self.root.configure(bg="#070a13")

    self.start_pos = (53.3498, -6.2603)
    self.end_pos = (52.7210, -8.8852)
    self.current_pos = list(self.start_pos)
    self.sim_speed_kts = 180.0
    self.speed_multiplier = 1.0
    self.altitude_ft = 6000.0
    self.aircraft_hdg = 0.0
    self.vor_obs = 90.0
    self.is_running = False
    self.flight_progress = 0.0
    self.selected_navaid = NAVAIDS[0]

    self.click_mode = None

    self.navaid_markers = []
    self.start_marker = None
    self.dest_marker = None
    self.aircraft_marker = None
    self.route_path = None

    self.create_dashboard()
    self.update_simulation_loop()

  def create_dashboard(self):
    style = ttk.Style()
    style.theme_use("clam")

    style.configure(".", background="#070a13", foreground="#cbd5e1")
    style.configure("TLabelframe", background="#0b101d", bordercolor="#1e293b")
    style.configure(
        "TLabelframe.Label",
        background="#0b101d",
        foreground="#38bdf8",
        font=("Segoe UI", 9, "bold"),
    )
    style.configure(
        "TButton",
        background="#1e293b",
        foreground="#f8fafc",
        borderwidth=1,
        font=("Segoe UI", 9, "bold"),
    )
    style.map(
        "TButton",
        background=[("active", "#334155")],
        foreground=[("active", "#38bdf8")],
    )

    main_paned = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
    main_paned.pack(fill="both", expand=True, padx=6, pady=6)

    # --- MAP CONTAINER ---
    self.map_container = ttk.LabelFrame(
        main_paned,
        text=(
            " 🌍 Tactical Flight Map | Status: Ready (Select Route Button"
            " Below) "
        ),
    )
    main_paned.add(self.map_container, weight=3)

    self.map_widget = tkintermapview.TkinterMapView(
        self.map_container, corner_radius=0
    )
    self.map_widget.pack(fill="both", expand=True, padx=2, pady=2)

    # Google Maps tile server
    self.map_widget.set_tile_server(
        "https://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}&s=Ga",
        max_zoom=22,
    )
    self.map_widget.set_position(53.4, -7.8)
    self.map_widget.set_zoom(7)

    self.map_widget.add_left_click_map_command(self.on_map_left_click)

    # --- NOTEBOOK TABS ---
    self.notebook = ttk.Notebook(main_paned)
    main_paned.add(self.notebook, weight=3)

    sim_tab = ttk.Frame(self.notebook)
    self.notebook.add(sim_tab, text=" 🧭 Live Simulation & Avionics ")

    bottom_paned = ttk.PanedWindow(sim_tab, orient=tk.HORIZONTAL)
    bottom_paned.pack(fill="both", expand=True, padx=2, pady=2)

    # 1. Controls Panel
    ctrl_frame = ttk.LabelFrame(
        bottom_paned, text=" 🎛️ Flight & Navaid Configuration "
    )
    bottom_paned.add(ctrl_frame, weight=1)

    mode_frame = ttk.LabelFrame(ctrl_frame, text=" Route Editing ")
    mode_frame.pack(fill="x", padx=6, pady=4)

    self.btn_mode_start = ttk.Button(
        mode_frame, text="📍 Set Start", command=self.set_mode_start
    )
    self.btn_mode_start.pack(side="left", expand=True, fill="x", padx=2, pady=2)

    self.btn_mode_dest = ttk.Button(
        mode_frame, text="🏁 Set Destination", command=self.set_mode_dest
    )
    self.btn_mode_dest.pack(side="left", expand=True, fill="x", padx=2, pady=2)

    btn_upload = ttk.Button(
        ctrl_frame,
        text="📁 Load Custom JSON...",
        command=self.load_custom_navaids_file,
    )
    btn_upload.pack(fill="x", padx=6, pady=4)

    param_grid = ttk.Frame(ctrl_frame)
    param_grid.pack(fill="x", padx=6, pady=4)

    ttk.Label(param_grid, text="Altitude (ft):", foreground="#f8fafc").grid(
        row=0, column=0, sticky="w", pady=2
    )
    self.alt_var = tk.StringVar(value="6000")
    entry_alt = tk.Entry(
        param_grid,
        textvariable=self.alt_var,
        width=8,
        bg="#04070e",
        fg="#38bdf8",
        insertbackground="white",
        font=("Consolas", 10, "bold"),
    )
    entry_alt.grid(row=0, column=1, padx=4, pady=2)

    ttk.Label(param_grid, text="Speed (kts):", foreground="#f8fafc").grid(
        row=1, column=0, sticky="w", pady=2
    )
    self.spd_var = tk.StringVar(value="180")
    entry_spd = tk.Entry(
        param_grid,
        textvariable=self.spd_var,
        width=8,
        bg="#04070e",
        fg="#38bdf8",
        insertbackground="white",
        font=("Consolas", 10, "bold"),
    )
    entry_spd.grid(row=1, column=1, padx=4, pady=2)

    ttk.Label(param_grid, text="Speed Mult:", foreground="#f8fafc").grid(
        row=2, column=0, sticky="w", pady=2
    )
    self.mult_cb = ttk.Combobox(
        param_grid,
        values=["0.1x", "0.5x", "1x", "2x", "5x", "10x", "50x", "100x"],
        width=6,
        state="readonly",
    )
    self.mult_cb.grid(row=2, column=1, padx=4, pady=2)
    self.mult_cb.set("1x")
    self.mult_cb.bind("<<ComboboxSelected>>", self.on_multiplier_change)

    ttk.Label(param_grid, text="Heading (°):", foreground="#f8fafc").grid(
        row=3, column=0, sticky="w", pady=2
    )
    hdg_frame = ttk.Frame(param_grid)
    hdg_frame.grid(row=3, column=1, padx=4, pady=2, sticky="w")
    self.hdg_spin = ttk.Spinbox(
        hdg_frame,
        from_=0,
        to=359,
        increment=1,
        width=5,
        command=self.update_aircraft_params_from_inputs,
    )
    self.hdg_spin.set(0)
    self.hdg_spin.pack(side="left")
    self.hdg_spin.bind(
        "<KeyRelease>", lambda e: self.update_aircraft_params_from_inputs()
    )
    ttk.Button(
        hdg_frame,
        text="Rst",
        width=3,
        command=lambda: [
            self.hdg_spin.set(0),
            self.update_aircraft_params_from_inputs(),
        ],
    ).pack(side="left", padx=2)

    ttk.Label(param_grid, text="VOR OBS (°):", foreground="#f8fafc").grid(
        row=4, column=0, sticky="w", pady=2
    )
    obs_frame = ttk.Frame(param_grid)
    obs_frame.grid(row=4, column=1, padx=4, pady=2, sticky="w")
    self.obs_spin = ttk.Spinbox(
        obs_frame,
        from_=0,
        to=359,
        increment=1,
        width=5,
        command=self.update_aircraft_params_from_inputs,
    )
    self.obs_spin.set(90)
    self.obs_spin.pack(side="left")
    self.obs_spin.bind(
        "<KeyRelease>", lambda e: self.update_aircraft_params_from_inputs()
    )
    ttk.Button(
        obs_frame,
        text="Rst",
        width=3,
        command=lambda: [
            self.obs_spin.set(90),
            self.update_aircraft_params_from_inputs(),
        ],
    ).pack(side="left", padx=2)

    btn_box = ttk.Frame(ctrl_frame)
    btn_box.pack(fill="x", padx=6, pady=4)
    self.btn_toggle_sim = ttk.Button(
        btn_box, text="▶ Start Flight", command=self.toggle_simulation
    )
    self.btn_toggle_sim.pack(side="left", expand=True, fill="x", padx=2)
    ttk.Button(btn_box, text="↺ Reset", command=self.reset_flight).pack(
        side="left", expand=True, fill="x", padx=2
    )

    ttk.Label(
        ctrl_frame,
        text="Active Navigation Aid:",
        font=("Segoe UI", 9, "bold"),
    ).pack(anchor="w", padx=6, pady=(4, 2))

    list_frame = ttk.Frame(ctrl_frame)
    list_frame.pack(fill="both", expand=True, padx=6, pady=4)

    self.navaid_listbox = tk.Listbox(
        list_frame,
        bg="#04070e",
        fg="#38bdf8",
        font=("Consolas", 9, "bold"),
        selectbackground="#1e293b",
        selectforeground="#ffffff",
        highlightthickness=0,
        bd=0,
    )
    self.navaid_listbox.pack(side="left", fill="both", expand=True)
    scrollbar = ttk.Scrollbar(
        list_frame, orient="vertical", command=self.navaid_listbox.yview
    )
    scrollbar.pack(side="right", fill="y")
    self.navaid_listbox.config(yscrollcommand=scrollbar.set)

    self.populate_navaid_listbox()
    self.navaid_listbox.bind("<<ListboxSelect>>", self.on_navaid_select)

    # 2. Cockpit Instruments Panel
    inst_frame = ttk.LabelFrame(bottom_paned, text=" ✈️ Primary Flight Display ")
    bottom_paned.add(inst_frame, weight=1)

    self.inst_canvas = tk.Canvas(
        inst_frame,
        width=340,
        height=340,
        bg="#04070e",
        highlightthickness=0,
    )
    self.inst_canvas.pack(fill="both", expand=True, padx=4, pady=4)

    # 3. Protocol Inspector Panel
    proto_frame = ttk.LabelFrame(
        bottom_paned, text=" 📊 Avionics Bus / Data Log "
    )
    bottom_paned.add(proto_frame, weight=1)

    self.proto_text = tk.Text(
        proto_frame,
        bg="#04070e",
        fg="#34d399",
        font=("Consolas", 8),
        insertbackground="white",
        highlightthickness=0,
        bd=0,
    )
    self.proto_text.pack(fill="both", expand=True, padx=4, pady=4)

    # Documentation Tabs
    self.create_manual_tab(
        " 🧭 VOR / DME Manual ",
        (
            "================================================================================\n"
            "   VHF OMNIDIRECTIONAL RANGE (VOR) & DISTANCE MEASURING EQUIPMENT"
            " (DME)\n"
            "   TECHNICAL FLIGHT MANUAL & AIRBORNE SYSTEM ARCHITECTURE\n"
            "================================================================================\n\n"
            "1. FUNDAMENTAL RADIO PRINCIPLE (PHASE COMPARISON):\n"
            "   A VOR transmitter operates in the VHF band (108.000 to 117.975"
            " MHz) with 50 kHz spacing.\n"
            "   The ground station emits two distinct 30 Hz signals"
            " simultaneously:\n"
            "     a) REFERENCE PHASE SIGNAL: An omnidirectional 30 Hz frequency"
            " modulation on a\n"
            "        9960 Hz subcarrier broadcast identically in all 360"
            " degrees azimuth.\n"
            "     b) VARIABLE PHASE SIGNAL: A directional beam created by an"
            " array of antennas\n"
            "        mechanically or electronically rotated at 30 revolutions"
            " per second (1800 RPM),\n"
            "        creating a 30 Hz amplitude-modulated pattern in space.\n\n"
            "   The airborne receiver compares the phase relationship"
            " between the reference signal\n"
            "   and the variable signal. When the variable beam points directly"
            " towards Magnetic\n"
            "   North, the two signals are in exact phase (0° phase shift). As"
            " the aircraft moves\n"
            "   clockwise around the station, the phase shift matches the"
            " aircraft's magnetic radial\n"
            "   relative to the VOR station (e.g., at Radial 090, variable lags"
            " reference by 90°).\n\n"
            "2. COCKPIT INSTRUMENTATION (CDI & OBS):\n"
            "   - OBS (Omni Bearing Selector): Knob used by the pilot to dial"
            " the intended course.\n"
            "   - CDI (Course Deviation Indicator): Vertical needle that"
            " indicates angular track\n"
            "     error. Full deflection across 5 dots represents a 10°"
            " deviation (2° per dot).\n"
            "   - TO/FROM INDICATOR: Resolves 180° ambiguity. If the selected"
            " OBS course leads toward\n"
            "     the VOR station, 'TO' displays; flying past the station flips"
            " the flag to 'FROM'.\n\n"
            "3. DME (DISTANCE MEASURING EQUIPMENT) PULSE RANGING:\n"
            "   - Frequency Band: UHF 960 to 1215 MHz (paired with paired VOR"
            " VHF channel).\n"
            "   - Airborne Interrogator: Transmits 12 µs pulse pairs at random"
            " repetition rates\n"
            "     (jittered interrogation) to the ground transponder.\n"
            "   - Ground Station: Receives pulse pairs, applies an accurate 50"
            " µs fixed transponder\n"
            "     delay, and transmits reply pulses on a frequency offset by ±63"
            " MHz.\n"
            "   - Distance Calculation: The aircraft computes transit time:\n"
            "        Slant Range = ((Total Transit Time - 50 µs) × Speed of"
            " Light) / 2\n"
            "   - SLANT-RANGE ERROR: Direct straight-line distance, including"
            " altitude.\n"
            "     Directly over a station at 6,000 ft (~1 NM above ground), DME"
            " will read 1.0 NM.\n\n"
            "4. ARINC 429 AVIONICS DIGITAL BUS INTERFACE:\n"
            "   - Label 212 (Octal): VOR Bearing Output (32-bit BCD/BNR word"
            " updating at 20 Hz).\n"
            "   - Label 037 (Octal): DME Slant Range (resolution 0.1 NM,"
            " transmitted to EFIS).\n"
            "   - Label 030 (Octal): VHF Nav Frequency selected on control"
            " panel."
        ),
    )

    self.create_manual_tab(
        " 📻 NDB / ADF Manual ",
        (
            "================================================================================\n"
            "   NON-DIRECTIONAL BEACON (NDB) & AUTOMATIC DIRECTION FINDER"
            " (ADF)\n"
            "   TECHNICAL MANUAL & RADIO WAVE PROPAGATION\n"
            "================================================================================\n\n"
            "1. TRANSMISSION CHARACTERISTICS:\n"
            "   - Frequency Band: Low Frequency (LF) and Medium Frequency"
            " (MF): 190 kHz to 1750 kHz.\n"
            "   - Emits an omnidirectional ground wave (vertically polarized)"
            " that follows the\n"
            "     curvature of the Earth, providing reception over terrain and"
            " past the line-of-sight.\n"
            "   - Identification: Modulated by an audio tone (typically 1020 Hz"
            " or 400 Hz) keyed with\n"
            "     a 2- or 3-letter Morse code sequence broadcast at regular"
            " intervals.\n\n"
            "2. AIRBORNE RECEIVER & ANTENNA OPERATION:\n"
            "   - LOOP ANTENNA: A directional bidirectional antenna consisting"
            " of wound ferrite\n"
            "     coils. A signal induced in the loop produces a characteristic"
            " 'figure-8' reception\n"
            "     pattern with two distinct null points (points of zero signal"
            " strength).\n"
            "   - SENSE ANTENNA: An omnidirectional wire or blade antenna with a"
            " circular reception\n"
            "     pattern. Combining the sense antenna pattern with the loop"
            " pattern creates a\n"
            "     cardioid (heart-shaped) pattern, resolving the 180° ambiguity"
            " and identifying the\n"
            "     true station direction.\n"
            "   - SERVO / DIGITAL TRACKING: Modern ADFs electronically steer"
            " balanced diode bridges\n"
            "     to align the needle on the Relative Bearing Indicator (RBI)"
            " or Radio Magnetic\n"
            "     Indicator (RMI) toward the null point.\n\n"
            "3. MATHEMATICAL BEARINGS:\n"
            "   - Relative Bearing (RB): The angle between aircraft nose (000°)"
            " and the NDB station.\n"
            "   - Magnetic Bearing (QDM): Magnetic track to steer to fly"
            " directly to the station:\n"
            "        QDM = Aircraft Magnetic Heading (HDG) + Relative"
            " Bearing (RB)\n"
            "        (If QDM > 360°, subtract 360°).\n"
            "   - Magnetic Bearing From (QDR): The radial or track outward from"
            " station:\n"
            "        QDR = (QDM ± 180°) % 360°\n\n"
            "4. OPERATIONAL LIMITATIONS & PROPAGATION ERRORS:\n"
            "   - Night Effect: Ionospheric reflection of skywaves causes phase"
            " interference.\n"
            "   - Coastal Refraction: Radio waves bend toward coastal terrain as"
            " conductivity varies.\n"
            "   - Thunderstorm / Static Error: ADF needle points directly"
            " toward lightning discharges.\n"
            "   - Dip / Bank Error: As the aircraft banks in a turn, the loop"
            " tilts, introducing error."
        ),
    )

    self.create_manual_tab(
        " 🛰️ GNSS & NMEA 0183 ",
        (
            "================================================================================\n"
            "   GLOBAL NAVIGATION SATELLITE SYSTEM (GNSS) & NMEA 0183"
            " PROTOCOL\n"
            "   MULTI-CONSTELLATION SPACE VEHICLE POSITIONING & TIME SYNCHRONY\n"
            "================================================================================\n\n"
            "1. PRINCIPLE OF PSEUDORANGE TRILATERATION:\n"
            "   A GNSS receiver solves for 4 unknowns:\n"
            "   Latitude (X), Longitude (Y), Altitude (Z), and Receiver Clock"
            " Bias (Δt).\n"
            "   - Each Space Vehicle (SV) broadcasts an atomic-timed C/A code"
            " on L1 (1575.42 MHz).\n"
            "   - The receiver cross-correlates incoming pseudo-random noise"
            " (PRN) against internal\n"
            "     replicas to calculate signal arrival delay (ΔT):\n"
            "        Pseudorange (P) = Speed of Light (c) × (Time Received -"
            " Time Transmitted)\n"
            "   - 4 SVs are mandatory: 3 spheres intersect at two points, and"
            " the 4th satellite\n"
            "     resolves local quartz clock error against atomic GPS time.\n\n"
            "2. DILUTION OF PRECISION (DOP):\n"
            "   Geometric spread of visible satellites affects measurement"
            " variance:\n"
            "   - GDOP: Geometric DOP (Overall 3D position and clock uncertainty"
            " factor).\n"
            "   - HDOP: Horizontal DOP (Position fix accuracy on the horizontal"
            " plane, <1.0 is ideal).\n"
            "   - VDOP: Vertical DOP (Altitude precision; typically higher due"
            " to ground geometry).\n\n"
            "3. NMEA 0183 SERIAL DATA TRANSMISSION:\n"
            "   - $GPGGA: Global Positioning System Fix Data\n"
            "     Format:"
            " $GPGGA,hhmmss.ss,llll.ll,a,yyyyy.yy,a,x,xx,x.x,x.x,M,x.x,M,x.x,xxxx*hh\n"
            "     Transmits UTC time, coordinates, fix quality (1=SPS, 2=DGPS,"
            " 4=RTK), SV count, HDOP, altitude.\n"
            "   - $GPRMC: Recommended Minimum Specific GNSS Data\n"
            "     Format: $GPRMC,hhmmss.ss,A,llll.ll,a,yyyyy.yy,a,x.x,x.x,ddmmyy,,,a*hh\n"
            "     Transmits UTC time, status (A=Valid), coordinates, speed over"
            " ground, course, date."
        ),
    )

    self.update_map_markers()
    self.update_instruments()

  def create_manual_tab(self, tab_title, manual_text):
    frame = ttk.Frame(self.notebook)
    self.notebook.add(frame, text=tab_title)

    text_widget = tk.Text(
        frame,
        bg="#04070e",
        fg="#38bdf8",
        font=("Consolas", 9),
        padx=14,
        pady=14,
        wrap="word",
        bd=0,
        highlightthickness=0,
    )
    text_widget.insert("1.0", manual_text)
    text_widget.config(state="disabled")

    scrollbar = ttk.Scrollbar(
        frame, orient="vertical", command=text_widget.yview
    )
    scrollbar.pack(side="right", fill="y")
    text_widget.config(yscrollcommand=scrollbar.set)
    text_widget.pack(side="left", fill="both", expand=True)

  def set_mode_start(self):
    self.click_mode = "START"
    self.map_container.config(
        text=(
            " 🌍 Tactical Flight Map | 🟡 [ARMED] Click map to set Flight Start"
            " Point "
        )
    )

  def set_mode_dest(self):
    self.click_mode = "DEST"
    self.map_container.config(
        text=(
            " 🌍 Tactical Flight Map | 🟠 [ARMED] Click map to set Flight End"
            " Point "
        )
    )

  def populate_navaid_listbox(self):
    self.navaid_listbox.delete(0, tk.END)
    for nav in NAVAIDS:
      self.navaid_listbox.insert(
          tk.END, f"{nav['id']:<4} | {nav['type']:<8} | {nav['name']}"
      )

  def load_custom_navaids_file(self):
    file_path = filedialog.askopenfilename(
        title="Select Navigation Aids JSON File",
        filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
    )
    if not file_path:
      return
    try:
      with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

      global NAVAIDS
      new_navaids = []
      for item in data:
        lat, lon = parse_dms_coord(
            item.get("coordinates", "531759.6N 0062652.0W")
        )
        name_upper = item.get("name", "").upper()
        if "GNSS" in name_upper or "GPS" in name_upper:
          nav_type = "GNSS"
        elif "DVOR" in name_upper or "VOR" in name_upper:
          nav_type = "DVOR/DME" if "DME" in name_upper else "VOR"
        elif "DME" in name_upper:
          nav_type = "DME"
        elif "NDB" in name_upper:
          nav_type = "NDB"
        else:
          nav_type = "NDB"

        elev_str = item.get("elevation_dme_antenna")
        elevation = 0.0
        if elev_str:
          try:
            elevation = float(
                str(elev_str).lower().replace("ft", "").strip()
            )
          except Exception:
            elevation = 0.0

        new_navaids.append({
            "name": item.get("name", "UNKNOWN"),
            "id": item.get("id", "UNK"),
            "type": nav_type,
            "frequency": item.get(
                "frequency_or_channel", item.get("frequency", "118.0MHz")
            ),
            "lat": lat,
            "lon": lon,
            "elevation": elevation,
            "remarks": item.get("remarks", ""),
        })

      if new_navaids:
        NAVAIDS = new_navaids
        self.selected_navaid = NAVAIDS[0]
        self.populate_navaid_listbox()
        self.update_map_markers()
        self.update_instruments()
        messagebox.showinfo(
            "Success",
            f"Loaded {len(NAVAIDS)} navigation aids successfully!",
        )
    except Exception as e:
      messagebox.showerror("Error", f"Failed to parse JSON file:\n{e}")

  def on_multiplier_change(self, event):
    val_str = self.mult_cb.get().replace("x", "")
    try:
      self.speed_multiplier = float(val_str)
    except ValueError:
      self.speed_multiplier = 1.0

  def update_aircraft_params_from_inputs(self):
    try:
      self.aircraft_hdg = float(self.hdg_spin.get()) % 360
      self.vor_obs = float(self.obs_spin.get()) % 360
      self.update_instruments()
    except ValueError:
      pass

  def on_map_left_click(self, coords):
    if self.click_mode == "START":
      self.start_pos = coords
      self.current_pos = list(self.start_pos)
      self.flight_progress = 0.0
      self.click_mode = None
      self.map_container.config(
          text=" 🌍 Tactical Flight Map | ✅ Start Point Updated "
      )
      self.update_map_markers()
      self.update_instruments()
    elif self.click_mode == "DEST":
      self.end_pos = coords
      self.click_mode = None
      self.map_container.config(
          text=" 🌍 Tactical Flight Map | ✅ Destination Point Updated "
      )
      self.update_map_markers()
      self.update_instruments()
    else:
      messagebox.showwarning(
          "Action Required",
          "Please click either 'Set Start' or 'Set Destination' button first"
          " before clicking the map.",
      )

  def toggle_simulation(self):
    try:
      self.altitude_ft = float(self.alt_var.get())
      self.sim_speed_kts = float(self.spd_var.get())
    except ValueError:
      messagebox.showerror("Invalid Input", "Please enter valid numbers.")
      return

    self.is_running = not self.is_running
    self.btn_toggle_sim.config(
        text="⏸ Pause Flight" if self.is_running else "▶ Start Flight"
    )

  def reset_flight(self):
    self.is_running = False
    self.flight_progress = 0.0
    self.current_pos = list(self.start_pos)
    self.click_mode = None
    self.map_container.config(
        text=(
            " 🌍 Tactical Flight Map | Status: Ready (Select Route Button"
            " Below) "
        )
    )
    self.btn_toggle_sim.config(text="▶ Start Flight")
    self.update_map_markers()
    self.update_instruments()

  def update_map_markers(self):
    for m in self.navaid_markers:
      m.delete()
    self.navaid_markers.clear()

    if self.start_marker:
      self.start_marker.delete()
    if self.dest_marker:
      self.dest_marker.delete()
    if self.aircraft_marker:
      self.aircraft_marker.delete()
    if self.route_path:
      self.route_path.delete()

    for nav in NAVAIDS:
      if nav["type"] == "GNSS":
        continue
      is_selected = (
          nav == self.selected_navaid or nav["id"] == self.selected_navaid["id"]
      )
      col = "#059669" if is_selected else "#1d4ed8"
      marker = self.map_widget.set_marker(
          nav["lat"],
          nav["lon"],
          text=f" {nav['id']} ",
          text_color="#0f172a",
          marker_color_circle=col,
          marker_color_outside="#0f172a",
      )
      self.navaid_markers.append(marker)

    self.start_marker = self.map_widget.set_marker(
        self.start_pos[0],
        self.start_pos[1],
        text=" [DEP] ",
        text_color="#0f172a",
        marker_color_circle="#0284c7",
        marker_color_outside="#0f172a",
    )
    self.dest_marker = self.map_widget.set_marker(
        self.end_pos[0],
        self.end_pos[1],
        text=" [ARR] ",
        text_color="#0f172a",
        marker_color_circle="#b91c1c",
        marker_color_outside="#0f172a",
    )
    self.route_path = self.map_widget.set_path(
        [self.start_pos, self.end_pos], color="#0284c7", width=3
    )

    self.aircraft_marker = self.map_widget.set_marker(
        self.current_pos[0],
        self.current_pos[1],
        text=" [ACFT] ",
        text_color="#0f172a",
        marker_color_circle="#dc2626",
        marker_color_outside="#ffffff",
    )

  def update_simulation_loop(self):
    if not self.root.winfo_exists():
      return
    if self.is_running:
      total_dist, bearing = calculate_distance_bearing(
          self.start_pos[0], self.start_pos[1], self.end_pos[0], self.end_pos[1]
      )
      if total_dist > 0.1:
        effective_speed = self.sim_speed_kts * self.speed_multiplier
        step_dist = (effective_speed * 0.1) / 3600.0
        self.flight_progress += step_dist / total_dist
        if self.flight_progress >= 1.0:
          self.flight_progress = 1.0
          self.is_running = False
          self.btn_toggle_sim.config(text="▶ Start Flight")

        cur_lat = (
            self.start_pos[0]
            + self.flight_progress * (self.end_pos[0] - self.start_pos[0])
        )
        cur_lon = (
            self.start_pos[1]
            + self.flight_progress * (self.end_pos[1] - self.start_pos[1])
        )
        self.current_pos = [cur_lat, cur_lon]

        self.aircraft_hdg = bearing
        self.hdg_spin.set(f"{bearing:.0f}")

        if self.aircraft_marker:
          self.aircraft_marker.set_position(cur_lat, cur_lon)

        self.update_instruments()

    self.root.after(100, self.update_simulation_loop)

  def on_navaid_select(self, event):
    selection = self.navaid_listbox.curselection()
    if selection:
      idx = selection[0]
      if idx < len(NAVAIDS):
        self.selected_navaid = NAVAIDS[idx]
        self.update_map_markers()
        self.update_instruments()

  def update_instruments(self):
    if not hasattr(self, "inst_canvas"):
      return

    nav = self.selected_navaid
    ac_lat, ac_lon = self.current_pos
    nav_type = nav["type"]
    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]

    if nav_type != "GNSS":
      dist_nm, true_brg = calculate_distance_bearing(
          ac_lat, ac_lon, nav["lat"], nav["lon"]
      )
      alt_diff_nm = abs(self.altitude_ft - nav.get("elevation", 0)) / 6076.12
      slant_range_nm = math.sqrt(dist_nm**2 + alt_diff_nm**2)
    else:
      dist_nm, true_brg, slant_range_nm = 0.0, self.aircraft_hdg, 0.0

    self.inst_canvas.delete("all")
    cx, cy, r = 170, 170, 135
    self.inst_canvas.create_oval(
        cx - r, cy - r, cx + r, cy + r, fill="#04070e", outline="#1e293b", width=3
    )

    try:
      self.vor_obs = float(self.obs_spin.get()) % 360
      self.aircraft_hdg = float(self.hdg_spin.get()) % 360
    except ValueError:
      pass

    if nav_type == "GNSS":
      self.inst_canvas.create_text(
          cx,
          cy - 115,
          text="GNSS MULTI-SBAS SKYPLOT",
          fill="#38bdf8",
          font=("Segoe UI", 9, "bold"),
      )
      self.inst_canvas.create_oval(
          cx - 90, cy - 90, cx + 90, cy + 90, outline="#1e293b", width=1
      )
      self.inst_canvas.create_oval(
          cx - 50, cy - 50, cx + 50, cy + 50, outline="#1e293b", width=1
      )
      self.inst_canvas.create_line(
          cx - 90, cy, cx + 90, cy, fill="#1e293b", dash=(2, 2)
      )
      self.inst_canvas.create_line(
          cx, cy - 90, cx, cy + 90, fill="#1e293b", dash=(2, 2)
      )

      satellites = [
          ("G03", cx + 40, cy - 50, True),
          ("G12", cx - 60, cy - 30, True),
          ("G22", cx + 20, cy + 60, True),
          ("G28", cx - 40, cy + 40, True),
          ("R01", cx - 70, cy - 70, True),
          ("E09", cx + 65, cy + 20, True),
          ("E15", cx - 10, cy - 75, True),
          ("G07", cx + 75, cy - 10, True),
      ]
      for sv, sx, sy, locked in satellites:
        col = "#34d399" if locked else "#f43f5e"
        self.inst_canvas.create_oval(
            sx - 6, sy - 6, sx + 6, sy + 6, fill=col, outline="white"
        )
        self.inst_canvas.create_text(
            sx, sy - 12, text=sv, fill="#f8fafc", font=("Consolas", 7, "bold")
        )

      self.inst_canvas.create_rectangle(
          cx - 75, cy + 72, cx + 75, cy + 115, fill="#04070e", outline="#1e293b"
      )
      self.inst_canvas.create_text(
          cx,
          cy + 85,
          text="FIX: 3D RTK | Sats: 8/12",
          fill="#34d399",
          font=("Consolas", 9, "bold"),
      )
      self.inst_canvas.create_text(
          cx,
          cy + 102,
          text="HDOP: 0.7 | VDOP: 1.1",
          fill="#38bdf8",
          font=("Consolas", 9, "bold"),
      )

      utc_t = datetime.datetime.now(datetime.timezone.utc)
      t_str = utc_t.strftime("%H%M%S.00")
      d_str = utc_t.strftime("%d%m%y")
      lat_deg = int(abs(ac_lat))
      lat_min = (abs(ac_lat) - lat_deg) * 60
      lat_h = "N" if ac_lat >= 0 else "S"
      lat_nmea = f"{lat_deg:02d}{lat_min:06.3f},{lat_h}"

      lon_deg = int(abs(ac_lon))
      lon_min = (abs(ac_lon) - lon_deg) * 60
      lon_h = "E" if ac_lon >= 0 else "W"
      lon_nmea = f"{lon_deg:03d}{lon_min:06.3f},{lon_h}"

      gga = (
          f"$GPGGA,{t_str},{lat_nmea},{lon_nmea},1,08,0.7,{self.altitude_ft*0.3048:.1f},M,48.2,M,,*5C"
      )
      rmc = (
          f"$GPRMC,{t_str},A,{lat_nmea},{lon_nmea},{self.sim_speed_kts:.1f},{self.aircraft_hdg:.1f},{d_str},,,A*7E"
      )

      log_entry = (
          f"[{timestamp}] GNSS RECEIVER (MULTI-SBAS)\n"
          f"  -> Receiver State: Autonomous 3D Position Fix\n"
          f"  -> NMEA 0183 GGA: {gga}\n"
          f"  -> NMEA 0183 RMC: {rmc}\n"
          f"  <- Calculated Lat/Lon: {ac_lat:.4f}°, {ac_lon:.4f}°\n"
          f"  <- Altitude MSL: {self.altitude_ft:.0f} ft"
          f" ({self.altitude_ft*0.3048:.1f} m)\n"
          "--------------------------------------------------\n"
      )

    elif "DVOR" in nav_type or "VOR" in nav_type:
      bearing_from = (true_brg + 180) % 360
      diff = (bearing_from - self.vor_obs + 540) % 360 - 180
      deflection = max(-5.0, min(5.0, diff / 2.0))

      self.inst_canvas.create_text(
          cx,
          cy - 110,
          text=f"VOR/DME ({nav['id']})",
          fill="#38bdf8",
          font=("Segoe UI", 9, "bold"),
      )
      for d in [-2, -1, 0, 1, 2]:
        dx = cx + (d * 20)
        self.inst_canvas.create_line(
            dx, cy - 30, dx, cy + 30, fill="#334155", width=2
        )
      self.inst_canvas.create_line(
          cx, cy - 40, cx, cy + 40, fill="#ffffff", width=2, dash=(2, 2)
      )

      needle_x = cx + (deflection * 20)
      self.inst_canvas.create_line(
          needle_x, cy - 45, needle_x, cy + 45, fill="#facc15", width=3
      )

      to_from = "FROM" if abs(diff) < 90 else "TO"
      self.inst_canvas.create_text(
          cx + 45,
          cy,
          text=to_from,
          fill="#38bdf8",
          font=("Segoe UI", 9, "bold"),
      )

      self.inst_canvas.create_rectangle(
          cx - 60, cy + 70, cx + 60, cy + 102, fill="#04070e", outline="#1e293b"
      )
      self.inst_canvas.create_text(
          cx,
          cy + 86,
          text=f"DME: {slant_range_nm:.1f} NM",
          fill="#34d399",
          font=("Consolas", 10, "bold"),
      )

      _, bin_vor = generate_arinc429_word("212", true_brg * 10)
      _, bin_dme = generate_arinc429_word("037", slant_range_nm * 10)

      log_entry = (
          f"[{timestamp}] DVOR/DME [{nav['id']}]\n"
          f"  -> Interrogation: 1030 MHz (12µs pulse spacing)\n"
          f"  -> ARINC 429 LBL 212 (VOR): {bin_vor}\n"
          f"  -> ARINC 429 LBL 037 (DME): {bin_dme}\n"
          f"  <- Reply: 1041-1150 MHz (Slant Rng: {slant_range_nm:.2f} NM)\n"
          f"  <- Computed Radial: {true_brg:.1f}° True (OBS: {self.vor_obs:.0f}°)\n"
          "--------------------------------------------------\n"
      )

    elif "DME" in nav_type:
      self.inst_canvas.create_text(
          cx,
          cy - 100,
          text=f"DME INTERROGATOR ({nav['id']})",
          fill="#38bdf8",
          font=("Segoe UI", 9, "bold"),
      )
      self.inst_canvas.create_oval(
          cx - 85,
          cy - 85,
          cx + 85,
          cy + 85,
          outline="#334155",
          width=5,
          fill="#04070e",
      )
      self.inst_canvas.create_text(
          cx,
          cy - 10,
          text=f"{slant_range_nm:.2f}",
          fill="#34d399",
          font=("Consolas", 26, "bold"),
      )
      self.inst_canvas.create_text(
          cx,
          cy + 25,
          text="NAUTICAL MILES",
          fill="#94a3b8",
          font=("Segoe UI", 8),
      )

      _, bin_dme = generate_arinc429_word("037", slant_range_nm * 10)
      log_entry = (
          f"[{timestamp}] STANDALONE DME [{nav['id']}]\n"
          f"  -> Interrogation: 1030 MHz RF Pulse Pair\n"
          f"  -> ARINC 429 LBL 037 (Distance): {bin_dme}\n"
          f"  <- Ground Transponder Delay: 50µs\n"
          f"  <- Slant Range Reply: {slant_range_nm:.2f} NM\n"
          "--------------------------------------------------\n"
      )

    else:
      self.inst_canvas.create_text(
          cx,
          cy - 110,
          text=f"NDB / ADF RMI ({nav['id']})",
          fill="#f43f5e",
          font=("Segoe UI", 9, "bold"),
      )
      self.inst_canvas.create_oval(
          cx - 85, cy - 85, cx + 85, cy + 85, outline="#334155", width=2
      )
      self.inst_canvas.create_text(
          cx, cy - 70, text="0", fill="white", font=("Segoe UI", 8)
      )
      self.inst_canvas.create_text(
          cx + 70, cy, text="90", fill="white", font=("Segoe UI", 8)
      )
      self.inst_canvas.create_text(
          cx, cy + 70, text="180", fill="white", font=("Segoe UI", 8)
      )
      self.inst_canvas.create_text(
          cx - 70, cy, text="270", fill="white", font=("Segoe UI", 8)
      )

      rel_bearing = (true_brg - self.aircraft_hdg + 360) % 360
      rad = math.radians(rel_bearing - 90)
      nx = cx + 60 * math.cos(rad)
      ny = cy + 60 * math.sin(rad)
      nx_tail = cx - 30 * math.cos(rad)
      ny_tail = cy - 30 * math.sin(rad)

      self.inst_canvas.create_line(
          nx_tail, ny_tail, nx, ny, fill="#f43f5e", width=3
      )
      self.inst_canvas.create_oval(
          cx - 4, cy - 4, cx + 4, cy + 4, fill="#ffffff"
      )

      self.inst_canvas.create_text(
          cx,
          cy + 102,
          text=f"Brg: {true_brg:.1f}° | Rel: {rel_bearing:.1f}°",
          fill="#f43f5e",
          font=("Consolas", 8, "bold"),
      )

      morse_id = "-.. -" if "D" in nav["id"] else "--."
      signal_strength_uv = max(10.0, 5000.0 / (dist_nm + 1.0))
      log_entry = (
          f"[{timestamp}] NDB RADIO BEACON [{nav['id']}]\n"
          f"  -> Frequency Band: {nav['frequency']} (MF/LF Carrier Wave)\n"
          f"  -> Audio Tone Modulation: 1020 Hz (Morse ID: {morse_id})\n"
          f"  <- Received Field Strength: {signal_strength_uv:.1f} µV/m\n"
          f"  <- ADF Loop Antenna Null Bearing: {true_brg:.1f}° True\n"
          "--------------------------------------------------\n"
      )

    self.proto_text.insert("1.0", log_entry)
    lines = self.proto_text.get("1.0", tk.END).split("\n")
    if len(lines) > 30:
      self.proto_text.delete("25.0", tk.END)


if __name__ == "__main__":
  root = tk.Tk()
  app = AviationSimApp(root)
  root.mainloop()