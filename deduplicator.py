"""
deduplicator.py — Attribute deduplication, semantic validation, source hierarchy conflict resolution.
Removes duplicate and overlapping attributes, resolves source conflicts by authority level,
and flags equal-authority discrepancies for HITL review.
"""
from typing import List, Dict, Tuple, Optional
from context import ProductAttribute


def deduplicate_and_clean_attributes(attributes: List[ProductAttribute], conflict_collector: Optional[List[str]] = None) -> List[ProductAttribute]:
    """
    Deduplicate and semantically validate extracted product attributes:
    1. Filter out malformed, empty, or meaningless entries.
    2. Prefer specific attribute names over generic ones (e.g. 'Upper Rack Minimum Height' over 'Upper Rack Height').
    3. Resolve conflicting values for the same attribute using Source Hierarchy (Levels 1 to 7).
    4. Flag equal-tier high-authority conflicts for human review.
    5. Drop exact duplicates preserving highest authority and confidence.
    """
    if not attributes:
        return []

    # Step 1: Filter out invalid / malformed attributes
    valid_attrs = []
    for a in attributes:
        name = a.attribute_name.strip()
        val = a.value.strip()
        if not name or not val:
            continue
        # Reject self-referencing attributes like "Model: Model" or "Series: Series"
        if name.lower() == val.lower() and name.lower() in ("model", "series", "brand", "product", "features"):
            continue
        valid_attrs.append(a)

    # Step 2: Specific vs Generic Overlap Resolution
    # Group by (normalized_value, normalized_unit)
    value_groups: Dict[Tuple[str, str], List[ProductAttribute]] = {}
    for a in valid_attrs:
        key = (a.value.strip().lower(), a.unit.strip().lower())
        value_groups.setdefault(key, []).append(a)

    to_drop_ids = set()

    for (val, uom), group in value_groups.items():
        if len(group) > 1:
            for i, a1 in enumerate(group):
                for j, a2 in enumerate(group):
                    if i != j:
                        n1, n2 = a1.attribute_name.lower(), a2.attribute_name.lower()
                        # Case: "Upper Rack Minimum Height" is more specific than "Upper Rack Height"
                        if "min" in n1 or "max" in n1 or "minimum" in n1 or "maximum" in n1:
                            if ("min" not in n2 and "max" not in n2) and (
                                "upper rack" in n1 and "upper rack" in n2 or
                                "lower rack" in n1 and "lower rack" in n2 or
                                "height" in n1 and "height" in n2
                            ):
                                to_drop_ids.add(id(a2))

    filtered_after_hierarchy = [a for a in valid_attrs if id(a) not in to_drop_ids]

    # Step 3: Source Hierarchy Conflict Resolution for same attribute_name
    # Group by attribute_name (multi-instance types like Certification/Feature are grouped by name+val)
    attr_name_groups: Dict[str, List[ProductAttribute]] = {}
    for a in filtered_after_hierarchy:
        if a.attribute_name.lower() in ("certification", "feature"):
            key = f"{a.attribute_name.strip().lower()}::{a.value.strip().lower()}"
        else:
            key = a.attribute_name.strip().lower()
        attr_name_groups.setdefault(key, []).append(a)

    resolved_attributes: List[ProductAttribute] = []

    for name_lower, group in attr_name_groups.items():
        if len(group) == 1:
            resolved_attributes.append(group[0])
            continue

        # Sort group by source_level ascending (1 is best, 7 is lowest), then confidence descending
        sorted_group = sorted(group, key=lambda x: (x.source_level, -x.confidence))
        best = sorted_group[0]

        # Check for conflict between high-authority sources (source_level <= 3) with different values
        high_auth_diffs = [
            x for x in sorted_group
            if x.source_level <= 3 and x.value.strip().lower() != best.value.strip().lower()
        ]
        if high_auth_diffs and conflict_collector is not None:
            conflict_msg = (
                f"Source Conflict on '{best.attribute_name}': "
                f"'{best.value}' ({best.source_type} Level {best.source_level}) vs "
                f"'{high_auth_diffs[0].value}' ({high_auth_diffs[0].source_type} Level {high_auth_diffs[0].source_level})"
            )
            conflict_collector.append(conflict_msg)

        resolved_attributes.append(best)

    return resolved_attributes
