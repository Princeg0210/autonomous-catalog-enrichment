"""
normalizer.py — Deterministic Value and UOM normalization per rules.md §2.1.
Separates numeric and fractional values from units of measure without using non-deterministic LLMs.
"""
import re
from typing import Tuple

# Unit dictionary for standardization
UOM_CANONICAL_MAP = {
    # Electrical
    "v": "V", "volt": "V", "volts": "V", "vac": "V", "vdc": "V", "kv": "kV",
    "a": "A", "amp": "A", "amps": "A", "amperes": "A", "ma": "mA",
    "w": "W", "watt": "W", "watts": "W", "kw": "kW", "kwh": "kW-hr", "kw-hr": "kW-hr",
    "hz": "Hz", "hertz": "Hz",
    # Sound
    "dba": "dBA", "db": "dBA", "decibel": "dBA", "decibels": "dBA",
    # Dimensions & Length
    "in": "in", "inch": "in", "inches": "in", "\"": "in", "''": "in",
    "ft": "ft", "feet": "ft", "foot": "ft", "'": "ft",
    "mm": "mm", "millimeter": "mm", "millimeters": "mm",
    "cm": "cm", "centimeter": "cm", "centimeters": "cm",
    "m": "m", "meter": "m", "meters": "m",
    # Weight
    "lb": "lb", "lbs": "lb", "pound": "lb", "pounds": "lb",
    "oz": "oz", "ounce": "oz", "ounces": "oz",
    "kg": "kg", "kilogram": "kg", "kilograms": "kg",
    "g": "g", "gram": "g", "grams": "g",
    # Speed & Mechanical
    "rpm": "RPM", "fpm": "FPM", "psi": "PSI", "bar": "bar", "cfm": "CFM",
    "tpi": "TPI",
    # Abrasives & Particle
    "grit": "Grit", "mesh": "Mesh",
    # Packaging / Counts
    "pk": "pk", "pack": "pk", "box": "Box", "ct": "Count", "count": "Count",
    "cycle": "Wash Cycles", "cycles": "Wash Cycles", "wash cycles": "Wash Cycles",
    "hr": "hr", "hrs": "hr", "hour": "hr", "hours": "hr",
    "deg": "°", "degree": "°", "degrees": "°",
}

# Regex for matching value and UOM:
# Group 1: Value (integer, decimal, fraction e.g. 33-7/16, or range e.g. 1 to 12)
# Group 2: Unit of measure
_VALUE_UOM_RE = re.compile(
    r"^([\d]+(?:[.\-\/][\d]+)*(?:\s*(?:to|-)\s*[\d]+(?:[.\-\/][\d]+)*)?)\s*"
    r"([a-zA-Z°%\"'/-]+(?:\s*[a-zA-Z°%\"'/-]+)*)?$"
)

# Prefix grit pattern e.g. "P150", "P80"
_GRIT_PREFIX_RE = re.compile(r"^[pP](\d+)$")


def normalize_value_uom(raw_value: str, label_hint: str = "") -> Tuple[str, str]:
    """
    Split and normalize a raw attribute string into (value, uom).
    Example:
      '120 Volts'      -> ('120', 'V')
      '33-7/16 in'     -> ('33-7/16', 'in')
      'P150'           -> ('150', 'Grit')
      '15 A'           -> ('15', 'A')
      'Stainless Steel'-> ('Stainless Steel', '')
    """
    if not raw_value:
        return "", ""

    raw_str = str(raw_value).strip()

    # Special case: Grit format like P150 or 150 Grit
    m_grit = _GRIT_PREFIX_RE.match(raw_str)
    if m_grit:
        return m_grit.group(1), "Grit"

    # Match standard value + unit
    m = _VALUE_UOM_RE.match(raw_str)
    if m:
        val = m.group(1).strip()
        raw_uom = (m.group(2) or "").strip().lower()

        # Check label hint if UOM was omitted in the value itself
        if not raw_uom and label_hint:
            lh = label_hint.lower()
            if "voltage" in lh:
                raw_uom = "v"
            elif "amperage" in lh or "current" in lh:
                raw_uom = "a"
            elif "sound" in lh or "noise" in lh:
                raw_uom = "dba"
            elif "height" in lh or "width" in lh or "depth" in lh or "diameter" in lh:
                raw_uom = "in"
            elif "grit" in lh:
                raw_uom = "grit"

        canon_uom = UOM_CANONICAL_MAP.get(raw_uom, raw_uom.upper() if len(raw_uom) <= 3 else raw_uom.title())
        return val, canon_uom

    # Categorical or non-numeric passthrough
    return raw_str, ""


# Self-checks (ponytail: keep one runnable assert block for validation)
assert normalize_value_uom("120 Volts") == ("120", "V")
assert normalize_value_uom("120V") == ("120", "V")
assert normalize_value_uom("33-7/16 in") == ("33-7/16", "in")
assert normalize_value_uom("P150") == ("150", "Grit")
assert normalize_value_uom("47 dBA") == ("47", "dBA")
assert normalize_value_uom("15A") == ("15", "A")
assert normalize_value_uom("Stainless Steel") == ("Stainless Steel", "")
