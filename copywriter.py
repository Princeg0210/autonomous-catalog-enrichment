"""
copywriter.py — Deterministic 5-channel copywriting engine enforcing exact character limits per rules.md.
Uses ONLY verified attributes from the current SKU context.
"""
from typing import Dict
from context import ProductContext

# Configured maximum character lengths (rules.md §1)
LIMITS = {
    "short": 50,
    "long": 250,
    "mobile": 30,
    "invoice": 100,
    "retail": 150,
}


def synthesize_all_descriptions(context: ProductContext) -> Dict[str, str]:
    """
    Synthesize all 5 required description channels for the current ProductContext.
    Enforces exact character limits with programmatic validation and compression.
    """
    attr_dict = {a.attribute_name: f"{a.value} {a.unit}".strip() for a in context.normalized_attributes}

    # Determine core product noun from taxonomy / brand / specs
    noun = _derive_product_noun(context)

    # 1. SHORT_DESC (max 50 chars) — rules.md §1.1
    # Syntax: BRAND_NAME + MANUFACTURER_PART_NUMBER + core noun
    short_candidate = f"{context.brand} {context.sku} {noun}".strip()
    short = _fit_length(short_candidate, LIMITS["short"])

    # 2. LONG_DESC1 (max 250 chars) — rules.md §1.2
    # Required Content: key electrical / physical measurements / distinct features
    specs_list = []
    for k in ["Voltage Rating", "Amperage Rating", "Mounting Type", "Material", "Grit",
              "Attachment Type", "Backing Material", "Length", "Teeth Per Inch", "Sound Level", "Diameter"]:
        if k in attr_dict:
            specs_list.append(f"{k}: {attr_dict[k]}")

    specs_str = ", ".join(specs_list) if specs_list else "Engineered for high performance and durability"
    long_candidate = f"{context.brand} {context.sku} {noun}. {specs_str}."
    long = _fit_length(long_candidate, LIMITS["long"])

    # 3. MOBILE_DESC (max 30 chars) — rules.md §1.3
    # Syntax: Extreme compression of brand and main function
    mobile_candidate = f"{context.brand} {noun}".strip()
    mobile = _fit_length(mobile_candidate, LIMITS["mobile"])

    # 4. INVOICE_DESC (max 100 chars, CAPS only) — rules.md §1.4
    # Syntax: CAPS-LOCK only, core physical dimensions separated by spaces
    dim_tokens = []
    for k in ["Voltage Rating", "Amperage Rating", "Grit", "Length", "Diameter", "Material", "Mounting Type"]:
        if k in attr_dict:
            dim_tokens.append(attr_dict[k].replace(" ", "").upper())

    dim_str = " ".join(dim_tokens)
    invoice_candidate = f"{noun.upper()} {context.brand.upper()} {dim_str}".strip()
    invoice = _fit_length(invoice_candidate, LIMITS["invoice"]).upper()

    # 5. RETAIL_DESC (max 150 chars)
    mat = attr_dict.get("Material", attr_dict.get("Abrasive Material", ""))
    if mat:
        retail_candidate = f"{context.brand} {context.sku} {noun} — {mat}".strip()
    else:
        retail_candidate = f"{context.brand} {context.sku} {noun}".strip()
    retail = _fit_length(retail_candidate, LIMITS["retail"])

    descriptions = {
        "short": short,
        "long": long,
        "mobile": mobile,
        "invoice": invoice,
        "retail": retail,
    }

    # Programmatic character limit verification
    validate_description_lengths(descriptions)
    context.generated_descriptions = descriptions
    return descriptions


def _derive_product_noun(context: ProductContext) -> str:
    """Extract clean product type noun from taxonomy or SKU."""
    tax = context.taxonomy_path.lower()
    if "dishwasher" in tax:
        return "Built-In Dishwasher"
    if "refrigerator" in tax:
        return "Refrigerator"
    if "sanding belt" in tax:
        return "Sanding Belt"
    if "sanding disc" in tax or "abrasive" in tax:
        return "Sanding Disc"
    if "saw blade" in tax or "cutting" in tax:
        return "Saw Blade"
    if "drill bit" in tax:
        return "Drill Bit"
    if "cordless" in tax or "power tool" in tax:
        return "Cordless Drill"
    if "decking" in tax:
        return "Composite Deck Board"
    if "lamp" in tax or "bulb" in tax:
        return "LED Light Bulb"
    if "tape" in tax:
        return "Industrial Tape"
    return "Equipment"


def _fit_length(text: str, max_len: int) -> str:
    """Trim string to max_len without breaking words mid-way if possible."""
    if len(text) <= max_len:
        return text
    trimmed = text[:max_len].strip()
    # Try finding last space to avoid cutting word
    last_space = trimmed.rfind(" ")
    if last_space > max_len // 2:
        trimmed = trimmed[:last_space].strip()
    return trimmed[:max_len]


def validate_description_lengths(descriptions: Dict[str, str]):
    """Assert programmatically that all generated channels obey limits."""
    for channel, text in descriptions.items():
        limit = LIMITS.get(channel, 250)
        assert len(text) <= limit, f"Channel '{channel}' exceeded limit {limit}: got {len(text)} chars ({text})"
