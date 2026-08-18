# Business Rules and Schema Validation Guide

To ensure absolute database consistency and pass the strict 40% Output Accuracy evaluation framework, all automated pipeline agents must adhere to the following business and formatting rules.

---

## 1. Description Composition Rules

All programmatic description formats must be synthesized without markdown, special symbols, or HTML tags.

### 1.1 Short Description (SHORT_DESC)
* **Maximum Length:** 50 characters.
* **Required Syntax:** Prepend `BRAND_NAME` + `MANUFACTURER_PART_NUMBER` + core noun.
* **Example:** `FRIGIDAIRE® PDSH4816AF Built-In Dishwasher`

### 1.2 Long Description (LONG_DESC1)
* **Maximum Length:** 250 characters.
* **Required Content:** Must incorporate key voltage, amperage, physical measurements, mounting types, and distinct features.
* **Constraint:** Must read as professional, grammatically complete prose without shorthand abbreviations.

### 1.3 Mobile Description (MOBILE_DESC)
* **Maximum Length:** 30 characters.
* **Required Syntax:** Extreme compression of brand and main function.
* **Example:** `Frigidaire Dishwasher`

### 1.4 Invoice Description (INVOICE_DESC)
* **Maximum Length:** 100 characters.
* **Required Syntax:** Caps-lock only. Must contain core physical dimensions separated by spaces.
* **Example:** `DISHWASHER LEG 5 SST 120V 15A 50-1/4IN`

---

## 2. Attribute and UOM Extraction Rules

### 2.1 Separation of Value and Unit
Every attribute with physical dimensions or electrical traits must be divided:
* **Value Column:** Numeric value only. Decimals are allowed (e.g., `120`, `50.25`, `10-3/8`).
* **UOM Column:** Denotes the corresponding normalized scale (e.g., `V`, `A`, `in`, `dBA`). No unit names (use `V`, not `Volts`).

### 2.2 LOV (List of Values) Alignment
* If the extracted attribute is a categorical field (e.g. `Color` or `Material`), the value must match the predetermined List of Values established for that category schema.
* If a scraper finds an authoritative value not current in the LOV, the system must **flag the item as a new value anomaly** and route it to the Human-In-The-Loop queue, rather than silently writing an unverified category label.

---

## 3. Strict Safety and Compliance Rules

Before parsing, downloading, or generating any technical specifications, descriptions, or digital assets, the pipeline screening layers must block and immediately refuse any request or crawled content violating core safety standards:
1. **Illegal Activities:** Any content containing instructions for the production of illegal weapons, self-harm, or terrorist support.
2. **Nudity and Adult Material:** Graphic sexual acts or nudity (excluding highly academic medical/scientific diagrams).
3. **Harmful Chemicals:** Scraped SDS sheets describing compounds must flag hazardous warnings but must never detail formulation steps for illegal substances.

