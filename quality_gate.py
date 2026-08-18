"""
quality_gate.py — Multi-stage quality gate and Cross-SKU contamination detector.
Ensures zero data leakage, validates LOV alignment, and enforces mandatory requirements.
"""
from typing import Tuple, List, Dict, Set
from context import ProductContext

# LOV reference tables
LOV_MAP: Dict[str, Set[str]] = {
    "Color": {"White", "Black", "Stainless Steel", "Bisque", "Silver", "Grey"},
    "Material": {"Stainless Steel", "Plastic", "Aluminum", "Carbon Steel", "Ceramic", "Carbide Tipped", "Film"},
    "Mounting Type": {"Leg", "Built-In", "Freestanding", "Wall-Mount", "Countertop"},
    "Attachment Type": {"Stikit (PSA)", "Hookit (Hook and Loop)", "Direct Mount", "Flange"},
}

# Category incompatible attribute matrix for Cross-SKU Contamination Detection
INCOMPATIBLE_CATEGORY_ATTRS = {
    "Tools & Hardware>Abrasives": {"Voltage Rating", "Amperage Rating", "Sound Level", "Mounting Type", "Number of Wash Cycles"},
    "Tools & Hardware>Cutting Tools": {"Voltage Rating", "Sound Level", "Number of Wash Cycles", "Mounting Type"},
    "Adhesives & Sealants>Tapes": {"Voltage Rating", "Amperage Rating", "Sound Level", "Number of Wash Cycles"},
    "Appliances & Consumer Electronics": {"Grit", "Teeth Per Inch", "Attachment Type"},
}

# Recent SKU signature store for runtime contamination detection
_RECENT_SKU_SIGNATURES: List[Dict] = []


def run_quality_gate(context: ProductContext) -> Tuple[str, List[str], List[str]]:
    """
    Execute full quality gate:
    1. Identity & Provenance check
    2. LOV validation
    3. Category schema compatibility check
    4. Cross-SKU contamination detection
    5. Description length validation

    Returns: (status: "APPROVED" | "NEEDS_REVIEW", violations, contamination_flags)
    """
    violations: List[str] = []
    contamination_flags: List[str] = []

    attr_labels = {a.attribute_name for a in context.normalized_attributes}
    attr_dict = {a.attribute_name: a.value for a in context.normalized_attributes}

    # 1. Identity & Provenance Check
    if not context.sku or not context.manufacturer:
        violations.append("Missing core product identity (SKU or Manufacturer).")

    if not context.normalized_attributes:
        violations.append("No verified technical attributes found.")

    for attr in context.normalized_attributes:
        if attr.sku != context.sku:
            contamination_flags.append(
                f"Provenance SKU mismatch: attribute '{attr.attribute_name}' has SKU '{attr.sku}' != current '{context.sku}'"
            )

    # 2. LOV Validation
    for attr in context.normalized_attributes:
        lov = LOV_MAP.get(attr.attribute_name)
        if lov is not None:
            lov_lower_map = {item.lower(): item for item in lov}
            val_lower = attr.value.lower().strip()
            if val_lower in lov_lower_map:
                # Canonicalize casing to approved LOV
                attr.value = lov_lower_map[val_lower]
            else:
                anomaly = f"LOV anomaly: '{attr.attribute_name}' = '{attr.value}' not in approved LOV"
                context.lov_anomalies.append(anomaly)
                attr.confidence = 0.5

    # 3. Category Incompatibility & Cross-SKU Contamination Check
    for cat_prefix, bad_attrs in INCOMPATIBLE_CATEGORY_ATTRS.items():
        if context.taxonomy_path.startswith(cat_prefix):
            leaked = bad_attrs.intersection(attr_labels)
            if leaked:
                msg = f"Cross-SKU Contamination: Category '{context.taxonomy_path}' illegally contains incompatible attributes: {leaked}"
                contamination_flags.append(msg)
                # Remove contaminated attributes immediately
                context.normalized_attributes = [
                    a for a in context.normalized_attributes if a.attribute_name not in leaked
                ]

    # 4. Compare with recent SKU signatures
    current_sig = {
        "sku": context.sku,
        "taxonomy": context.taxonomy_path,
        "attrs": {a.attribute_name: a.value for a in context.normalized_attributes}
    }

    for prev in _RECENT_SKU_SIGNATURES[-10:]:
        if prev["sku"] != context.sku and prev["taxonomy"] != context.taxonomy_path:
            # Check if 3+ specific values match identically across completely different categories
            matching_vals = 0
            for k, v in current_sig["attrs"].items():
                if k in prev["attrs"] and prev["attrs"][k] == v and v not in ("Standard", "White", "Black"):
                    matching_vals += 1
            if matching_vals >= 3:
                msg = f"Suspicious identical spec cluster detected between {context.sku} and {prev['sku']}"
                contamination_flags.append(msg)

    # Record current signature
    _RECENT_SKU_SIGNATURES.append(current_sig)
    if len(_RECENT_SKU_SIGNATURES) > 50:
        _RECENT_SKU_SIGNATURES.pop(0)

    # 5. Source Hierarchy & Verification Status Check
    for attr in context.normalized_attributes:
        if attr.source_level in (6, 7):
            attr.verification_status = "INFERRED"
            if attr.confidence > 0.80:
                attr.confidence = 0.75
        elif attr.source_level in (1, 2, 3, 4, 5):
            attr.verification_status = "VERIFIED"

        if attr.value == "UNKNOWN" or attr.verification_status == "UNKNOWN":
            violations.append(f"Attribute '{attr.attribute_name}' has UNKNOWN value/status.")

    # 6. Required Descriptions Check
    for req_desc in ["short", "long", "mobile", "invoice"]:
        if not context.generated_descriptions.get(req_desc):
            violations.append(f"Missing required description channel: {req_desc}")

    context.validation_results = violations
    context.contamination_flags = contamination_flags

    # Determine final status
    if contamination_flags or violations or context.lov_anomalies:
        status = "NEEDS_REVIEW"
    else:
        status = "APPROVED"

    context.status = status
    return status, violations, contamination_flags
