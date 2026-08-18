"""
test_product_isolation.py — Comprehensive regression test suite for Strict Product Isolation.
Verifies that no attributes, search results, or descriptions leak between SKUs.
"""
import sys
import unittest
from context import ProductContext, ProductAttribute
from discovery import discover_and_extract_product, generate_search_queries
from taxonomy import classify_product_taxonomy
from copywriter import synthesize_all_descriptions
from quality_gate import run_quality_gate
from normalizer import normalize_value_uom


class TestStrictProductIsolation(unittest.TestCase):

    def setUp(self):
        # Fresh setup for each test
        pass

    def test_01_sequential_processing_frigidaire_then_3m(self):
        """Test Product A (Frigidaire Dishwasher) followed by Product B (3M Sanding Disc)."""
        # --- 1. Process Product A (Frigidaire) ---
        ctx_a = ProductContext.create(
            sku="PDSH4816AF",
            manufacturer="Rheem Manufacturing",
            brand="FRIGIDAIRE®"
        )
        discover_and_extract_product(ctx_a)
        tax_path_a, cat_id_a, conf_a, _ = classify_product_taxonomy(ctx_a.sku, ctx_a.manufacturer, ctx_a.brand)
        ctx_a.taxonomy_path = tax_path_a
        ctx_a.taxonomy_id = cat_id_a
        synthesize_all_descriptions(ctx_a)
        status_a, violations_a, flags_a = run_quality_gate(ctx_a)

        # Verify Product A specs
        attrs_a = {a.attribute_name: a.value for a in ctx_a.normalized_attributes}
        self.assertIn("Voltage Rating", attrs_a)
        self.assertEqual(attrs_a["Voltage Rating"], "120")
        self.assertIn("Amperage Rating", attrs_a)
        self.assertEqual(attrs_a["Amperage Rating"], "15")
        self.assertIn("Width", attrs_a)
        self.assertEqual(attrs_a["Width"], "24")
        self.assertIn("Depth", attrs_a)
        self.assertEqual(attrs_a["Depth"], "24-1/4")
        self.assertIn("Upper Rack Minimum Height", attrs_a)
        self.assertEqual(attrs_a["Upper Rack Minimum Height"], "8-1/2")
        self.assertIn("Lower Rack Minimum Height", attrs_a)
        self.assertEqual(attrs_a["Lower Rack Minimum Height"], "11-1/4")
        self.assertIn("Annual Energy Consumption", attrs_a)
        self.assertEqual(attrs_a["Annual Energy Consumption"], "240")
        self.assertIn("Delay Start Duration", attrs_a)
        self.assertEqual(attrs_a["Delay Start Duration"], "1–12")

        # Verify deduplication: no generic overlapping rack heights
        all_attr_names_a = [a.attribute_name for a in ctx_a.normalized_attributes]
        self.assertNotIn("Upper Rack Height", all_attr_names_a, "Generic 'Upper Rack Height' must be deduplicated!")
        self.assertNotIn("Lower Rack Height", all_attr_names_a, "Generic 'Lower Rack Height' must be deduplicated!")

        # Verify structured features and certifications
        features_a = [a.value for a in ctx_a.normalized_attributes if a.attribute_name == "Feature"]
        certs_a = [a.value for a in ctx_a.normalized_attributes if a.attribute_name == "Certification"]
        self.assertIn("CleanBoost", features_a)
        self.assertIn("ENERGY STAR Certified", certs_a)
        self.assertIn("UL Listed", certs_a)
        self.assertIn("NSF Certified", certs_a)

        self.assertEqual(ctx_a.taxonomy_path, "Appliances & Consumer Electronics>Kitchen Appliances>Built-In Dishwashers")
        self.assertIn("Dishwasher", ctx_a.generated_descriptions["short"])

        # --- 2. Process Product B (3M) ---
        ctx_b = ProductContext.create(
            sku="3MABR-7100075678",
            manufacturer="Jam Industrial Supply LLC (JAMIN)",
            brand="3M"
        )
        discover_and_extract_product(ctx_b)
        tax_path_b, cat_id_b, conf_b, _ = classify_product_taxonomy(ctx_b.sku, ctx_b.manufacturer, ctx_b.brand)
        ctx_b.taxonomy_path = tax_path_b
        ctx_b.taxonomy_id = cat_id_b
        synthesize_all_descriptions(ctx_b)
        status_b, violations_b, flags_b = run_quality_gate(ctx_b)

        # Verify Product B specs
        attrs_b = {a.attribute_name: a.value for a in ctx_b.normalized_attributes}

        # CRITICAL ASSERTIONS: Zero Leakage from Product A into Product B!
        self.assertNotIn("Voltage Rating", attrs_b, "Product B (3M) MUST NOT have Voltage Rating from Dishwasher!")
        self.assertNotIn("Amperage Rating", attrs_b, "Product B (3M) MUST NOT have Amperage Rating from Dishwasher!")
        self.assertNotIn("Sound Level", attrs_b, "Product B (3M) MUST NOT have Sound Level from Dishwasher!")
        self.assertNotIn("Mounting Type", attrs_b, "Product B (3M) MUST NOT have Leg mounting from Dishwasher!")
        self.assertNotIn("Number of Wash Cycles", attrs_b, "Product B (3M) MUST NOT have Wash Cycles from Dishwasher!")

        # Verify Product B has its OWN abrasive specs
        self.assertIn("Grit", attrs_b)
        self.assertEqual(attrs_b["Grit"], "150")
        self.assertEqual(ctx_b.taxonomy_path, "Tools & Hardware>Abrasives>Sanding Discs")
        self.assertIn("3M", ctx_b.generated_descriptions["short"])
        self.assertIn("Sanding Disc", ctx_b.generated_descriptions["short"])
        self.assertNotIn("Dishwasher", ctx_b.generated_descriptions["long"])

        # Check Provenance SKU integrity
        for attr in ctx_b.normalized_attributes:
            self.assertEqual(attr.sku, "3MABR-7100075678")

    def test_02_reverse_order_processing_3m_then_frigidaire(self):
        """Test Product B (3M) followed by Product A (Frigidaire) in reverse order."""
        # --- 1. Process Product B (3M) ---
        ctx_b = ProductContext.create(
            sku="3MABR-7100075678",
            manufacturer="Jam Industrial Supply LLC (JAMIN)",
            brand="3M"
        )
        discover_and_extract_product(ctx_b)
        tax_path_b, cat_id_b, _, _ = classify_product_taxonomy(ctx_b.sku, ctx_b.manufacturer, ctx_b.brand)
        ctx_b.taxonomy_path = tax_path_b
        synthesize_all_descriptions(ctx_b)
        run_quality_gate(ctx_b)

        attrs_b = {a.attribute_name: a.value for a in ctx_b.normalized_attributes}
        self.assertIn("Grit", attrs_b)
        self.assertNotIn("Voltage Rating", attrs_b)

        # --- 2. Process Product A (Frigidaire) ---
        ctx_a = ProductContext.create(
            sku="PDSH4816AF",
            manufacturer="Rheem Manufacturing",
            brand="FRIGIDAIRE®"
        )
        discover_and_extract_product(ctx_a)
        tax_path_a, cat_id_a, _, _ = classify_product_taxonomy(ctx_a.sku, ctx_a.manufacturer, ctx_a.brand)
        ctx_a.taxonomy_path = tax_path_a
        synthesize_all_descriptions(ctx_a)
        run_quality_gate(ctx_a)

        attrs_a = {a.attribute_name: a.value for a in ctx_a.normalized_attributes}
        self.assertNotIn("Grit", attrs_a, "Product A (Dishwasher) MUST NOT have Grit from 3M Abrasive!")
        self.assertNotIn("Attachment Type", attrs_a, "Product A (Dishwasher) MUST NOT have Stikit from 3M Abrasive!")
        self.assertIn("Voltage Rating", attrs_a)
        self.assertEqual(attrs_a["Voltage Rating"], "120")

    def test_03_search_queries_and_cache_keys_independent(self):
        """Verify search queries and cache keys are uniquely generated per SKU."""
        ctx_a = ProductContext.create("PDSH4816AF", "Rheem Manufacturing", "FRIGIDAIRE®")
        q_a = generate_search_queries(ctx_a)

        ctx_b = ProductContext.create("3MABR-7100075678", "Jam Industrial Supply LLC", "3M")
        q_b = generate_search_queries(ctx_b)

        self.assertTrue(all("PDSH4816AF" in q for q in q_a))
        self.assertTrue(all("3MABR-7100075678" in q for q in q_b))
        self.assertFalse(any("PDSH4816AF" in q for q in q_b))

        key_a = f"product_cache:{ctx_a.manufacturer.lower()}:{ctx_a.sku.lower()}"
        key_b = f"product_cache:{ctx_b.manufacturer.lower()}:{ctx_b.sku.lower()}"
        self.assertNotEqual(key_a, key_b)

    def test_04_cross_sku_contamination_detection(self):
        """Verify quality gate detects and rejects illegally injected cross-SKU attributes."""
        ctx = ProductContext.create("3MABR-7100075678", "Jam Industrial Supply LLC", "3M")
        ctx.taxonomy_path = "Tools & Hardware>Abrasives>Sanding Discs"

        # Illegally add dishwasher attributes to abrasive product
        ctx.normalized_attributes.append(
            ProductAttribute("Voltage Rating", "120", "V", 0.95, "PDSH4816AF", "leaked_source")
        )
        ctx.normalized_attributes.append(
            ProductAttribute("Grit", "150", "Grit", 0.95, "3MABR-7100075678", "verified_source")
        )

        synthesize_all_descriptions(ctx)
        status, violations, flags = run_quality_gate(ctx)

        # Must be flagged as NEEDS_REVIEW and contaminated attribute stripped
        self.assertEqual(status, "NEEDS_REVIEW")
        self.assertTrue(any("Cross-SKU Contamination" in f for f in flags))
        remaining_labels = [a.attribute_name for a in ctx.normalized_attributes]
        self.assertNotIn("Voltage Rating", remaining_labels, "Quality gate must remove contaminated voltage attribute!")
        self.assertIn("Grit", remaining_labels)

    def test_05_atomic_spec_and_compound_splitting(self):
        """Verify only real atomic specifications are created and compound specs are split."""
        from discovery import atomize_specification

        # 1. Compound Size splitting
        size_attrs = atomize_specification("Size", "24 in W x 24-1/4 in D", "", "TEST-1", "spec", "http://test")
        size_map = {a.attribute_name: (a.value, a.unit) for a in size_attrs}
        self.assertIn("Width", size_map)
        self.assertEqual(size_map["Width"], ("24", "in"))
        self.assertIn("Depth", size_map)
        self.assertEqual(size_map["Depth"], ("24-1/4", "in"))
        self.assertNotIn("Size", size_map)

        # 2. Blacklisted marketing / series / model / additional info filtering & splitting
        compound_text = "240 kW-hr Annual Energy, 1 to 12 hr Delay Start Hours"
        info_attrs = atomize_specification("Additional Information", compound_text, "", "TEST-1", "spec", "http://test")
        info_map = {a.attribute_name: (a.value, a.unit) for a in info_attrs}
        self.assertNotIn("Additional Information", info_map, "Never create 'Additional Information' as an attribute name!")
        self.assertIn("Annual Energy Consumption", info_map)
        self.assertEqual(info_map["Annual Energy Consumption"], ("240", "kWh/year"))
        self.assertIn("Delay Start Duration", info_map)
        self.assertEqual(info_map["Delay Start Duration"], ("1–12", "hr"))

        # 3. Reject title / series / model noise
        model_attrs = atomize_specification("Model", "", "", "TEST-1", "spec", "http://test")
        self.assertEqual(len(model_attrs), 0, "Never create empty or non-spec Model attribute!")

    def test_06_idempotent_processing_no_duplicates(self):
        """Verify processing the same SKU twice produces consistent results without duplicating attributes."""
        # First processing pass
        ctx1 = ProductContext.create("PDSH4816AF", "Rheem Manufacturing", "FRIGIDAIRE®")
        discover_and_extract_product(ctx1)
        count1 = len(ctx1.normalized_attributes)
        names1 = sorted([a.attribute_name for a in ctx1.normalized_attributes])

        # Second processing pass on exact same SKU
        ctx2 = ProductContext.create("PDSH4816AF", "Rheem Manufacturing", "FRIGIDAIRE®")
        discover_and_extract_product(ctx2)
        count2 = len(ctx2.normalized_attributes)
        names2 = sorted([a.attribute_name for a in ctx2.normalized_attributes])
        self.assertEqual(count1, count2, "Attribute count must be identical between runs.")
        self.assertEqual(names1, names2, "Attribute names must be identical between runs.")
        self.assertEqual(len(ctx2.normalized_attributes), len(set((a.attribute_name, a.value, a.unit) for a in ctx2.normalized_attributes)))

    def test_07_whirlpool_wdts7024rz_clean_specs_no_marketing_or_feature_leakage(self):
        """Verify WDTS7024RZ produces clean technical attributes without marketing copy or feature leakage."""
        ctx = ProductContext.create("WDTS7024RZ", "Whirlpool Corporation", "Whirlpool®")
        discover_and_extract_product(ctx)
        tax_path, cat_id, _, _ = classify_product_taxonomy(ctx.sku, ctx.manufacturer, ctx.brand)
        ctx.taxonomy_path = tax_path
        synthesize_all_descriptions(ctx)
        status, violations, flags = run_quality_gate(ctx)

        attrs = {a.attribute_name: (a.value, a.unit) for a in ctx.normalized_attributes}

        # 1. Clean atomic technical specs present
        self.assertIn("Voltage Rating", attrs)
        self.assertEqual(attrs["Voltage Rating"], ("120", "V"))
        self.assertIn("Amperage Rating", attrs)
        self.assertEqual(attrs["Amperage Rating"], ("10", "A"))
        self.assertIn("Sound Level", attrs)
        self.assertEqual(attrs["Sound Level"], ("41", "dBA"))
        self.assertIn("Width", attrs)
        self.assertEqual(attrs["Width"], ("23-7/8", "in"))
        self.assertIn("Depth", attrs)
        self.assertEqual(attrs["Depth"], ("22-5/8", "in"))
        self.assertIn("Depth With Door Open", attrs)
        self.assertEqual(attrs["Depth With Door Open"], ("50-3/16", "in"))
        self.assertIn("Minimum Height", attrs)
        self.assertEqual(attrs["Minimum Height"], ("33-7/16", "in"))
        self.assertIn("Material", attrs)
        self.assertEqual(attrs["Material"], ("Stainless Steel", ""))
        self.assertIn("Color", attrs)
        self.assertEqual(attrs["Color"], ("Stainless Steel", ""))

        # 2. Strict Protection: NO product titles, marketing copy, or feature lists in attributes
        all_attr_names = [a.attribute_name for a in ctx.normalized_attributes]
        self.assertFalse(any("Whirlpool® Eco Series" in name for name in all_attr_names))
        self.assertFalse(any("Load more and run less" in name for name in all_attr_names))
        self.assertFalse(any("Sani Rinse" in name for name in all_attr_names))
        self.assertFalse(any("Normal Cycle" in name for name in all_attr_names))

        # 3. Features separated into features list
        self.assertTrue(len(ctx.features) >= 5)
        self.assertTrue(any("3rd rack" in f.lower() for f in ctx.features))
        self.assertTrue(any("sensor cycle" in f.lower() for f in ctx.features))
        self.assertTrue(any("sani rinse" in f.lower() for f in ctx.features))

    def test_08_source_hierarchy_and_verification_status(self):
        """Verify attributes have source quality levels, verification status, and evidence-based confidence."""
        ctx = ProductContext.create("3MABR-7100075678", "Jam Industrial Supply LLC (JAMIN)", "3M")
        discover_and_extract_product(ctx)
        tax_path, cat_id, _, _ = classify_product_taxonomy(ctx.sku, ctx.manufacturer, ctx.brand)
        ctx.taxonomy_path = tax_path
        synthesize_all_descriptions(ctx)
        status, violations, flags = run_quality_gate(ctx)

        attr_map = {a.attribute_name: a for a in ctx.normalized_attributes}

        # 1. Product Description / Spec source -> Level 4, VERIFIED, confidence 0.88-0.95
        grit_attr = attr_map.get("Grit")
        self.assertIsNotNone(grit_attr)
        self.assertEqual(grit_attr.source_level, 4)
        self.assertEqual(grit_attr.verification_status, "VERIFIED")
        self.assertTrue(0.88 <= grit_attr.confidence <= 0.95)

        # 2. Category Standard -> Level 6, INFERRED, confidence 0.60-0.80
        dia_attr = attr_map.get("Diameter")
        self.assertIsNotNone(dia_attr)
        self.assertEqual(dia_attr.source_level, 6)
        self.assertEqual(dia_attr.verification_status, "INFERRED")
        self.assertTrue(0.60 <= dia_attr.confidence <= 0.80)

    def test_09_conflict_handling_triggers_review(self):
        """Verify that conflicting high-authority sources on the same attribute trigger review."""
        from deduplicator import deduplicate_and_clean_attributes

        conflicts = []
        # Level 1 (Manufacturer PDF) says 5 in, Level 3 (Dataset) says 6 in
        attrs = [
            ProductAttribute("Diameter", "5", "in", 0.98, "SKU-1", "manufacturer_pdf", source_level=1),
            ProductAttribute("Diameter", "6", "in", 0.95, "SKU-1", "authoritative_dataset", source_level=3),
        ]
        resolved = deduplicate_and_clean_attributes(attrs, conflict_collector=conflicts)
        # Higher authority (Level 1) is chosen
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].value, "5")
        # Conflict is logged
        self.assertEqual(len(conflicts), 1)
        self.assertIn("Source Conflict", conflicts[0])

    def test_10_dcb518asts06g_authoritative_sanding_belt_isolation(self):
        """Verify DCB518ASTS06G consistently produces Sanding Belt specs without disc contamination."""
        ctx = ProductContext.create("DCB518ASTS06G", "Freud Inc (2435)", "Diablo")
        discover_and_extract_product(ctx)
        tax_path, cat_id, tax_conf, tax_reason = classify_product_taxonomy(ctx.sku, ctx.manufacturer, ctx.brand, text="Sanding Belt")
        ctx.taxonomy_path = tax_path
        ctx.taxonomy_id = cat_id
        descs = synthesize_all_descriptions(ctx)
        status, violations, flags = run_quality_gate(ctx)

        # 1. Taxonomy must be Sanding Belts
        self.assertEqual(ctx.taxonomy_path, "Tools & Hardware>Abrasives>Sanding Belts")

        # 2. Verified atomic specs extracted from description
        attrs = {a.attribute_name: (a.value, a.unit) for a in ctx.normalized_attributes}
        self.assertIn("Width", attrs)
        self.assertEqual(attrs["Width"], ("1/2", "in"))
        self.assertIn("Length", attrs)
        self.assertEqual(attrs["Length"], ("18", "in"))
        self.assertIn("Package Quantity", attrs)
        self.assertEqual(attrs["Package Quantity"], ("6", "Pack"))

        # 3. Critical: ZERO cross-contamination from 3M Sanding Disc
        all_attr_names = [a.attribute_name for a in ctx.normalized_attributes]
        self.assertNotIn("Grit", all_attr_names, "Must not have 3M Grit!")
        self.assertNotIn("Attachment Type", all_attr_names, "Must not have 3M Stikit attachment!")
        self.assertNotIn("Abrasive Material", all_attr_names, "Must not have 3M Cubitron II mineral!")
        self.assertNotIn("Diameter", all_attr_names, "Must not have 5 in disc diameter!")

        # 4. Idempotent check
        ctx2 = ProductContext.create("DCB518ASTS06G", "Freud Inc (2435)", "Diablo")
        discover_and_extract_product(ctx2)
        self.assertEqual(len(ctx.normalized_attributes), len(ctx2.normalized_attributes))


if __name__ == "__main__":
    unittest.main(verbosity=2)

