"""
attribute_classifier.py — Semantic attribute classification and validation engine.
Enforces strict semantic separation between Technical Attributes, Features, Certifications,
Product Identity, and Marketing Copy before any item enters the Technical Attributes table.
"""
import re
from enum import Enum
from typing import Tuple, Optional, Set
from normalizer import normalize_value_uom


class ItemCategory(str, Enum):
    TECHNICAL_ATTRIBUTE = "TECHNICAL_ATTRIBUTE"
    FEATURE = "FEATURE"
    CERTIFICATION = "CERTIFICATION"
    PRODUCT_IDENTITY = "PRODUCT_IDENTITY"
    MARKETING_COPY = "MARKETING_COPY"
    UNKNOWN = "UNKNOWN"


# Known technical attribute canonical names
VALID_TECHNICAL_SPECS: Set[str] = {
    "voltage rating", "voltage", "amperage rating", "amperage", "current rating",
    "width", "depth", "height", "depth with door open", "minimum height", "maximum height",
    "upper rack minimum height", "lower rack minimum height", "upper rack maximum height", "lower rack maximum height",
    "sound level", "noise level",
    "material", "color", "finish", "mounting type", "plug type",
    "number of wash cycles", "wash cycles", "capacity", "tub material",
    "annual energy consumption", "delay start duration", "delay start hours",
    "grit", "diameter", "length", "teeth per inch", "tpi", "attachment type",
    "backing material", "abrasive material", "package quantity", "blade diameter",
    "battery voltage", "chuck size", "drive size", "lumens", "wattage", "bulb shape"
}

# Unit compatibility rules for technical attributes
ATTRIBUTE_UNIT_MAP = {
    "voltage rating": {"V", "kV", "mV"},
    "amperage rating": {"A", "mA"},
    "sound level": {"dBA", "dB"},
    "width": {"in", "mm", "cm", "ft"},
    "depth": {"in", "mm", "cm", "ft"},
    "height": {"in", "mm", "cm", "ft"},
    "depth with door open": {"in", "mm", "cm", "ft"},
    "minimum height": {"in", "mm", "cm", "ft"},
    "maximum height": {"in", "mm", "cm", "ft"},
    "upper rack minimum height": {"in", "mm", "cm", "ft"},
    "lower rack minimum height": {"in", "mm", "cm", "ft"},
    "upper rack maximum height": {"in", "mm", "cm", "ft"},
    "lower rack maximum height": {"in", "mm", "cm", "ft"},
    "annual energy consumption": {"kWh/year", "kW-hr", "kWh"},
    "delay start duration": {"hr", "hours", "hour"},
    "grit": {"Grit", "Mesh"},
    "diameter": {"in", "mm", "cm"},
    "length": {"in", "mm", "cm", "ft"},
    "teeth per inch": {"TPI"},
    "package quantity": {"Box", "Count", "pk", "Pack"},
    "lumens": {"lm", "lumens"},
    "wattage": {"W", "kW"},
}

# Known unitless technical attributes
UNITLESS_TECHNICAL_SPECS = {
    "material", "color", "finish", "mounting type", "plug type",
    "number of wash cycles", "tub material", "attachment type",
    "backing material", "abrasive material", "product type", "series"
}

# Known certification keywords
CERTIFICATION_KEYWORDS = {
    "energy star", "ul listed", "cul listed", "nsf certified", "asse 1006",
    "cee tier", "energy star certified", "osha", "ansi", "etl", "csa"
}


def classify_extracted_item(raw_label: str, raw_val: str) -> Tuple[ItemCategory, str, str, str]:
    """
    Classify any raw item into:
    TECHNICAL_ATTRIBUTE | FEATURE | CERTIFICATION | PRODUCT_IDENTITY | MARKETING_COPY | UNKNOWN
    Returns: (category, canonical_name, clean_val, unit)
    """
    label = (raw_label or "").strip()
    val = (raw_val or "").strip()

    if not label and not val:
        return ItemCategory.UNKNOWN, "", "", ""

    # Check for Marketing Copy (sentences, paragraphs)
    if len(label) > 60 or len(val) > 200 or any(kw in label.lower() for kw in ("load more", "run less", "engineered with", "featuring our", "designed to")):
        return ItemCategory.MARKETING_COPY, "", "", ""

    # Check for Product Identity (Product Type, Series)
    lbl_lower = label.lower()
    if lbl_lower == "product type" or (lbl_lower in ("dishwasher", "washing machine", "dryer", "refrigerator", "sanding disc") and not val):
        p_type = val or label
        return ItemCategory.PRODUCT_IDENTITY, "Product Type", p_type, ""

    if lbl_lower == "series" or (lbl_lower.endswith("series") and len(label) < 30 and not val):
        series_val = val or label
        return ItemCategory.PRODUCT_IDENTITY, "Series", series_val, ""

    # Check for Certifications
    combined = f"{label} {val}".lower()
    for cert_kw in CERTIFICATION_KEYWORDS:
        if cert_kw in combined:
            cert_name = val if cert_kw in val.lower() else label
            return ItemCategory.CERTIFICATION, "Certification", cert_name.strip(), ""

    # Check if this is a standalone Feature
    if lbl_lower in ("feature", "features") or lbl_lower.startswith("with ") or "cleanboost" in combined or "rack with" in combined:
        feat_name = val or label.replace("With ", "")
        return ItemCategory.FEATURE, "Feature", feat_name.strip(), ""

    # Validate against Technical Attributes
    if lbl_lower in VALID_TECHNICAL_SPECS:
        norm_val, norm_uom = normalize_value_uom(val, label_hint=label)
        
        # Verify unit compatibility
        allowed_units = ATTRIBUTE_UNIT_MAP.get(lbl_lower)
        if allowed_units:
            if not norm_uom or norm_uom not in allowed_units:
                # If value is numeric, assign default primary unit
                if re.match(r"^[\d]+(?:[.\-\/][\d]+)*$", norm_val):
                    norm_uom = list(allowed_units)[0]
                else:
                    return ItemCategory.UNKNOWN, "", "", ""
        elif lbl_lower not in UNITLESS_TECHNICAL_SPECS and norm_uom:
            pass

        # Verify semantic value sanity
        if not _is_semantic_value_valid(lbl_lower, norm_val):
            return ItemCategory.UNKNOWN, "", "", ""

        canonical_name = _canonical_name(lbl_lower)
        return ItemCategory.TECHNICAL_ATTRIBUTE, canonical_name, norm_val, norm_uom

    # Fallback: check if label looks like a feature
    if len(label) > 10 and not val and not re.search(r"\d", label):
        return ItemCategory.FEATURE, "Feature", label, ""

    return ItemCategory.UNKNOWN, "", "", ""


def _is_semantic_value_valid(attr_name: str, value: str) -> bool:
    """Verify that the value is semantically reasonable for the attribute."""
    if not value or len(value) > 50:
        return False

    # Electrical ratings must be positive numbers
    if attr_name in ("voltage rating", "voltage", "amperage rating", "amperage"):
        return bool(re.match(r"^\d+(?:\.\d+)?$", value))

    # Sound level must be reasonable decibel rating (10 - 120 dBA)
    if attr_name in ("sound level", "noise level"):
        if re.match(r"^\d+$", value):
            return 10 <= int(value) <= 120
        return False

    # Dimensions must be numeric or fraction
    if attr_name in ("width", "depth", "height", "depth with door open", "minimum height", "maximum height", "diameter", "length"):
        return bool(re.match(r"^[\d]+(?:[.\-\/][\d]+)*$", value))

    # Reject if value contains sentence fragments
    if any(stop in value.lower() for stop in ("with our", "provides dedicated", "helps fit", "family piles up")):
        return False

    return True


def _canonical_name(name_lower: str) -> str:
    """Return clean, professional title for attribute name."""
    mapping = {
        "voltage rating": "Voltage Rating",
        "voltage": "Voltage Rating",
        "amperage rating": "Amperage Rating",
        "amperage": "Amperage Rating",
        "mounting type": "Mounting Type",
        "depth with door open": "Depth With Door Open",
        "minimum height": "Minimum Height",
        "maximum height": "Maximum Height",
        "upper rack minimum height": "Upper Rack Minimum Height",
        "lower rack minimum height": "Lower Rack Minimum Height",
        "upper rack maximum height": "Upper Rack Maximum Height",
        "lower rack maximum height": "Lower Rack Maximum Height",
        "sound level": "Sound Level",
        "number of wash cycles": "Number of Wash Cycles",
        "annual energy consumption": "Annual Energy Consumption",
        "delay start duration": "Delay Start Duration",
        "product type": "Product Type",
        "series": "Series",
    }
    return mapping.get(name_lower, name_lower.title())
