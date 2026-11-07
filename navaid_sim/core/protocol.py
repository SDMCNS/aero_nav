"""
Avionics digital bus protocols and streaming formats.
Implements high-fidelity ARINC 429 32-bit word encoding/decoding,
NMEA 0183 sentence generation, and station audio Morse code generation.
"""

import datetime
from typing import Dict, Any, Tuple


# Standard ARINC 429 SSM definitions
SSM_FAILURE_WARNING = 0b00  # 0: Hardware failure / flag dropped
SSM_NO_COMPUTED_DATA = 0b01  # 1: Out of range / unlocking / station not tuned
SSM_FUNCTIONAL_TEST = 0b10  # 2: Self-test mode
SSM_NORMAL_OPERATION = 0b11  # 3: Normal valid navigation data

# Morse Code lookup table
MORSE_MAP = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".",
    "F": "..-.", "G": "--.", "H": "....", "I": "..", "J": ".---",
    "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---",
    "P": ".--.", "Q": "--.-", "R": ".-.", "S": "...", "T": "-",
    "U": "..-", "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--",
    "Z": "--..", "0": "-----", "1": ".----", "2": "..---", "3": "...--",
    "4": "....-", "5": ".....", "6": "-....", "7": "--...", "8": "---..",
    "9": "----.", " ": " ",
}


def to_morse_code(text: str) -> str:
    """Converts a text string or callsign into Morse code dots and dashes."""
    return " ".join(MORSE_MAP.get(c.upper(), "?") for c in text.strip())


def calculate_arinc429_odd_parity(bit_string_31: str) -> str:
    """Calculates odd parity bit for a 31-bit ARINC 429 payload."""
    ones = bit_string_31.count("1")
    return "0" if (ones % 2 != 0) else "1"


def reverse_bits_8(val: int) -> str:
    """Reverses 8 bits for ARINC 429 octal label transmission (LSB first)."""
    binary = format(val, "08b")
    return binary[::-1]


def encode_arinc429_word(
    label_octal: str,
    sdi: int,
    data_bits_19: str,
    ssm: int = SSM_NORMAL_OPERATION,
) -> Dict[str, Any]:
    """
    Constructs a compliant 32-bit ARINC 429 digital word:
    - Bits 1-8: Label (in octal, reversed)
    - Bits 9-10: SDI (Source/Destination Identifier)
    - Bits 11-29: Data (19 bits)
    - Bits 30-31: SSM (Sign/Status Matrix)
    - Bit 32: Parity (Odd)
    """
    label_val = int(label_octal, 8)
    label_bits = reverse_bits_8(label_val)
    sdi_bits = format(sdi & 0b11, "02b")
    data_bits = data_bits_19.zfill(19)[:19]
    ssm_bits = format(ssm & 0b11, "02b")

    payload_31 = label_bits + sdi_bits + data_bits + ssm_bits
    parity_bit = calculate_arinc429_odd_parity(payload_31)
    full_word_32 = payload_31 + parity_bit

    word_int = int(full_word_32, 2)
    hex_str = f"0x{word_int:08X}"

    return {
        "raw_hex": hex_str,
        "raw_bin": full_word_32,
        "label_octal": label_octal,
        "label_bits": label_bits,
        "sdi": sdi,
        "sdi_bits": sdi_bits,
        "data_bits": data_bits,
        "ssm": ssm,
        "ssm_name": {
            SSM_NORMAL_OPERATION: "NORMAL_OPERATION",
            SSM_NO_COMPUTED_DATA: "NO_COMPUTED_DATA",
            SSM_FAILURE_WARNING: "FAILURE_WARNING",
            SSM_FUNCTIONAL_TEST: "FUNCTIONAL_TEST",
        }.get(ssm, "UNKNOWN"),
        "parity": int(parity_bit),
    }


def encode_arinc429_vor_bearing(
    bearing_deg: float,
    sdi: int = 1,
    is_valid: bool = True,
) -> Dict[str, Any]:
    """
    ARINC 429 Label 212 (Octal): VOR Omnibearing / Radial.
    Resolution: 180° / 2^11 ≈ 0.044° (BNR 12 bits or 18 bits full range 0-359.9°).
    """
    ssm = SSM_NORMAL_OPERATION if is_valid else SSM_NO_COMPUTED_DATA
    # Scale 0-360 degrees into 19-bit BNR
    scale = (2**19 - 1) / 360.0
    val_int = int(max(0.0, min(359.999, bearing_deg)) * scale)
    data_bits = format(val_int, "019b")
    word = encode_arinc429_word("212", sdi, data_bits, ssm)
    word["parameter"] = "VOR_BEARING"
    word["decoded_value"] = round(bearing_deg, 2)
    word["units"] = "DEG"
    return word


def encode_arinc429_dme_distance(
    distance_nm: float,
    sdi: int = 1,
    is_valid: bool = True,
) -> Dict[str, Any]:
    """
    ARINC 429 Label 037 (Octal): DME Slant Range Distance.
    Scale: 0 to 512 NM with 0.125 NM or 0.0625 NM resolution.
    """
    ssm = SSM_NORMAL_OPERATION if is_valid else SSM_NO_COMPUTED_DATA
    # Scale 0 to 512 NM across 19 bits
    scale = (2**19 - 1) / 512.0
    val_int = int(max(0.0, min(512.0, distance_nm)) * scale)
    data_bits = format(val_int, "019b")
    word = encode_arinc429_word("037", sdi, data_bits, ssm)
    word["parameter"] = "DME_DISTANCE"
    word["decoded_value"] = round(distance_nm, 2)
    word["units"] = "NM"
    return word


def encode_arinc429_loc_deviation(
    deflection_dots: float,
    sdi: int = 1,
    is_valid: bool = True,
) -> Dict[str, Any]:
    """
    ARINC 429 Label 173 (Octal): Localizer Deviation (DDM / fractions of full scale).
    -5.0 dots to +5.0 dots (or +/- 0.4 DDM).
    """
    ssm = SSM_NORMAL_OPERATION if is_valid else SSM_NO_COMPUTED_DATA
    # Signed 18-bit + sign bit
    norm = max(-1.0, min(1.0, deflection_dots / 5.0))
    int_val = int(norm * 262143)
    if int_val < 0:
        int_val = (1 << 19) + int_val
    data_bits = format(int_val & 0x7FFFF, "019b")
    word = encode_arinc429_word("173", sdi, data_bits, ssm)
    word["parameter"] = "LOC_DEVIATION"
    word["decoded_value"] = round(deflection_dots, 2)
    word["units"] = "DOTS"
    return word


def encode_arinc429_gs_deviation(
    deflection_dots: float,
    sdi: int = 1,
    is_valid: bool = True,
) -> Dict[str, Any]:
    """
    ARINC 429 Label 174 (Octal): Glideslope Deviation.
    -5.0 dots to +5.0 dots.
    """
    ssm = SSM_NORMAL_OPERATION if is_valid else SSM_NO_COMPUTED_DATA
    norm = max(-1.0, min(1.0, deflection_dots / 5.0))
    int_val = int(norm * 262143)
    if int_val < 0:
        int_val = (1 << 19) + int_val
    data_bits = format(int_val & 0x7FFFF, "019b")
    word = encode_arinc429_word("174", sdi, data_bits, ssm)
    word["parameter"] = "GS_DEVIATION"
    word["decoded_value"] = round(deflection_dots, 2)
    word["units"] = "DOTS"
    return word


def encode_arinc429_adf_bearing(
    rel_bearing_deg: float,
    sdi: int = 1,
    is_valid: bool = True,
) -> Dict[str, Any]:
    """
    ARINC 429 Label 162 (Octal): ADF Relative Bearing.
    0 to 359.9°.
    """
    ssm = SSM_NORMAL_OPERATION if is_valid else SSM_NO_COMPUTED_DATA
    scale = (2**19 - 1) / 360.0
    val_int = int(max(0.0, min(359.999, rel_bearing_deg)) * scale)
    data_bits = format(val_int, "019b")
    word = encode_arinc429_word("162", sdi, data_bits, ssm)
    word["parameter"] = "ADF_RELATIVE_BEARING"
    word["decoded_value"] = round(rel_bearing_deg, 2)
    word["units"] = "DEG"
    return word


def encode_arinc429_nav_frequency(
    freq_mhz: float,
    sdi: int = 1,
) -> Dict[str, Any]:
    """
    ARINC 429 Label 030 (Octal): VHF NAV Tuned Frequency.
    BCD format e.g. 113.30 MHz -> 113.30.
    """
    # 108.00 - 117.95
    # Encode into BCD
    khz = int(round(freq_mhz * 1000.0))
    bcd_str = f"{khz:06d}"[-5:]  # 5 digits: 13300 or 14900
    val_int = int(bcd_str, 16)
    data_bits = format(val_int & 0x7FFFF, "019b")
    word = encode_arinc429_word("030", sdi, data_bits, SSM_NORMAL_OPERATION)
    word["parameter"] = "NAV_TUNED_FREQ"
    word["decoded_value"] = round(freq_mhz, 3)
    word["units"] = "MHZ"
    return word


def calculate_nmea_checksum(sentence: str) -> str:
    """Computes XOR 8-bit checksum for an NMEA 0183 sentence."""
    csum = 0
    # Strip leading $ and trailing *hh if present
    s = sentence.strip()
    if s.startswith("$"):
        s = s[1:]
    if "*" in s:
        s = s.split("*")[0]
    for ch in s:
        csum ^= ord(ch)
    return f"{csum:02X}"


def generate_nmea_sentences(
    lat: float,
    lon: float,
    alt_ft: float,
    speed_kts: float,
    track_deg: float,
    hdop: float = 0.8,
    num_sats: int = 10,
    timestamp: datetime.datetime = None,
) -> Dict[str, str]:
    """
    Generates standard NMEA 0183 sentences ($GPGGA, $GPRMC, $GPGSA).
    """
    if timestamp is None:
        timestamp = datetime.datetime.now(datetime.timezone.utc)

    t_str = timestamp.strftime("%H%M%S.00")
    d_str = timestamp.strftime("%d%m%y")

    # Lat: DDMM.MMMM, N/S
    lat_deg = int(abs(lat))
    lat_min = (abs(lat) - lat_deg) * 60.0
    lat_hemi = "N" if lat >= 0 else "S"
    lat_nmea = f"{lat_deg:02d}{lat_min:07.4f},{lat_hemi}"

    # Lon: DDDMM.MMMM, E/W
    lon_deg = int(abs(lon))
    lon_min = (abs(lon) - lon_deg) * 60.0
    lon_hemi = "E" if lon >= 0 else "W"
    lon_nmea = f"{lon_deg:03d}{lon_min:07.4f},{lon_hemi}"

    alt_m = alt_ft * 0.3048

    # GGA - Global Positioning System Fix Data
    # 1=GPS SPS, num_sats, hdop, alt_m, M, geoidal_sep, M, dgps_age, dgps_id
    raw_gga = f"GPGGA,{t_str},{lat_nmea},{lon_nmea},1,{num_sats:02d},{hdop:.1f},{alt_m:.1f},M,48.2,M,,"
    gga = f"${raw_gga}*{calculate_nmea_checksum(raw_gga)}"

    # RMC - Recommended Minimum Specific GNSS Data
    # Status: A=valid, speed in knots, track angle in degrees true, date, mag_var, mag_hemi
    raw_rmc = f"GPRMC,{t_str},A,{lat_nmea},{lon_nmea},{speed_kts:.1f},{track_deg:.1f},{d_str},3.0,W,A"
    rmc = f"${raw_rmc}*{calculate_nmea_checksum(raw_rmc)}"

    # GSA - GNSS DOP and Active Satellites
    # Mode: A=automatic 2D/3D, Fix: 3=3D fix, 12 PRN slots, PDOP, HDOP, VDOP
    raw_gsa = f"GPGSA,A,3,03,07,09,12,15,18,22,28,,,,,1.4,{hdop:.1f},1.1"
    gsa = f"${raw_gsa}*{calculate_nmea_checksum(raw_gsa)}"

    return {
        "GGA": gga,
        "RMC": rmc,
        "GSA": gsa,
    }

