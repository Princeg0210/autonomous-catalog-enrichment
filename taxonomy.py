"""
taxonomy.py — Multi-category hierarchical taxonomy classifier with reasoning and confidence.
Maps product identity, verified specs, and text to exact leaf taxonomy classes.
"""
from typing import Tuple

# Hierarchical Taxonomy Rules: (Keyword regex/tokens, Category Path, Category ID, Confidence)
TAXONOMY_RULES = [
    # Appliances > Kitchen Appliances > Built-In Dishwashers
    (
        ["dishwasher", "dishwashers", "pdsh4816", "wdts7024", "cleanboost"],
        "Appliances & Consumer Electronics>Kitchen Appliances>Built-In Dishwashers",
        4125,
        0.98,
        "Identified as residential or commercial built-in dishwasher."
    ),
    # Appliances > Kitchen Appliances > Refrigerators
    (
        ["refrigerator", "fridge", "freezer", "french door", "ice maker"],
        "Appliances & Consumer Electronics>Kitchen Appliances>Refrigerators",
        4130,
        0.95,
        "Identified as food refrigeration unit."
    ),
    # Appliances > Laundry
    (
        ["washing machine", "washer", "speed queen", "front load washer"],
        "Appliances & Consumer Electronics>Laundry>Washing Machines",
        4210,
        0.95,
        "Identified as laundry washing equipment."
    ),
    (
        ["dryer", "tumble dryer", "electric dryer", "gas dryer"],
        "Appliances & Consumer Electronics>Laundry>Dryers",
        4211,
        0.95,
        "Identified as laundry dryer equipment."
    ),
    # Tools & Hardware > Abrasives > Sanding Discs
    (
        ["sanding disc", "stikit", "cubitron", "hookit", "film disc", "775l", "abranet", "mirka", "3mabr"],
        "Tools & Hardware>Abrasives>Sanding Discs",
        7410,
        0.97,
        "Identified as coated abrasive sanding/finishing disc."
    ),
    # Tools & Hardware > Abrasives > Cut-Off & Grinding
    (
        ["cut-off", "cutoff", "grinding wheel", "flap disc", "depressed center wheel"],
        "Tools & Hardware>Abrasives>Cut-Off Wheels & Grinding Discs",
        7420,
        0.95,
        "Identified as bonded cutting or grinding wheel."
    ),
    # Tools & Hardware > Abrasives > Sanding Belts
    (
        ["sanding belt", "sanding belts", "abrasive belt", "dcb518"],
        "Tools & Hardware>Abrasives>Sanding Belts",
        7415,
        0.97,
        "Identified as coated abrasive sanding belt."
    ),
    # Tools & Hardware > Cutting Tools > Saw Blades
    (
        ["saw blade", "reciprocating blade", "steel demon", "circular saw blade", "carbide blade"],
        "Tools & Hardware>Cutting Tools>Saw Blades",
        7301,
        0.98,
        "Identified as power saw cutting blade."
    ),
    # Tools & Hardware > Fastening & Drilling > Drill Bits
    (
        ["drill bit", "driver bit", "hex shank", "impact duty", "twist bit", "sds-plus"],
        "Tools & Hardware>Fastening Tools>Drill Bits",
        7310,
        0.95,
        "Identified as rotary drilling or driving tool."
    ),
    # Tools & Hardware > Power Tools > Cordless Drills
    (
        ["cordless drill", "impact driver", "hammer drill", "m18 fuel", "m12 fuel", "2804-20", "2953-20"],
        "Tools & Hardware>Power Tools>Cordless Drills & Drivers",
        7105,
        0.98,
        "Identified as handheld cordless power drill or driver."
    ),
    # Building Materials > Decking & Railing > Composite Decking
    (
        ["decking", "deck board", "trex", "timbertech", "transcend", "fascia", "grooved edge"],
        "Building Materials>Decking & Railing>Composite Decking",
        6100,
        0.96,
        "Identified as architectural composite decking product."
    ),
    # Electrical & Lighting > Lamps & Light Bulbs
    (
        ["light bulb", "lamp", "led bulb", "a19", "par38", "satco", "philips lighting", "lumens"],
        "Electrical & Lighting>Lamps & Light Bulbs",
        8501,
        0.95,
        "Identified as illumination lamp or light bulb."
    ),
    # Electrical & Lighting > Lighting Fixtures
    (
        ["chandelier", "pendant", "vanity light", "sconce", "kichler", "flush mount", "downlight"],
        "Electrical & Lighting>Lighting Fixtures>Commercial Fixtures",
        8520,
        0.95,
        "Identified as luminaires and lighting fixtures."
    ),
    # Adhesives & Sealants > Tapes
    (
        ["tape", "duct tape", "masking tape", "electrical tape", "vhb", "gorilla tape"],
        "Adhesives & Sealants>Tapes>Industrial Tapes",
        9100,
        0.95,
        "Identified as industrial pressure sensitive adhesive tape."
    ),
]

FALLBACK_TAXONOMY = (
    "General Industrial Equipment>Uncategorized",
    9999,
    0.30,
    "Unable to match specific leaf category from product tokens."
)


def classify_product_taxonomy(sku: str, manufacturer: str, brand: str, text: str = "") -> Tuple[str, int, float, str]:
    """
    Classify a product into its hierarchical taxonomy category based on identity and extracted text.
    Returns: (taxonomy_path, category_id, confidence, reasoning)
    """
    haystack = f"{sku} {manufacturer} {brand} {text}".lower()

    for tokens, path, cat_id, conf, reason in TAXONOMY_RULES:
        for token in tokens:
            if token in haystack:
                return path, cat_id, conf, f"Matched token '{token}': {reason}"

    return FALLBACK_TAXONOMY
