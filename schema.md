# Data Schema Definition

## 1. Database Schema Design (SQL)

To support the 252-column output structure while maintaining highly structured and scalable relational integrity, the backend persistent storage uses the following Postgres schema.

```sql
-- 1. Taxonomy Category Master Table
CREATE TABLE taxonomy_categories (
    category_id SERIAL PRIMARY KEY,
    classpath VARCHAR(512) NOT NULL UNIQUE, -- Path format: "Appliances>Kitchen Appliances>Built-In Dishwashers"
    depth INT NOT NULL,
    parent_id INT REFERENCES taxonomy_categories(category_id)
);

-- 2. Products Core Table
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    mfg_part_num VARCHAR(100) NOT NULL,
    part_manuf VARCHAR(255) NOT NULL,
    manufacturer_name VARCHAR(255),
    brand_name VARCHAR(255),
    trade_name VARCHAR(255),
    category_id INT REFERENCES taxonomy_categories(category_id),
    source_url VARCHAR(1024), -- Primary crawl url
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Dynamic Product Attributes Table
CREATE TABLE product_attributes (
    attribute_id SERIAL PRIMARY KEY,
    product_id INT REFERENCES products(product_id) ON DELETE CASCADE,
    attribute_label VARCHAR(255) NOT NULL,
    attribute_value VARCHAR(1024) NOT NULL,
    attribute_uom VARCHAR(50),
    ref_url VARCHAR(1024), -- Absolute source traceability link
    extracted_by VARCHAR(50) DEFAULT 'ai-agent', -- 'ai-agent', 'human-reviewer', 'fallback'
    confidence_score NUMERIC(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Narrative Descriptions Table
CREATE TABLE product_descriptions (
    product_id INT REFERENCES products(product_id) ON DELETE CASCADE PRIMARY KEY,
    short_desc VARCHAR(50) NOT NULL,
    long_desc VARCHAR(250) NOT NULL,
    mobile_desc VARCHAR(30),
    invoice_desc VARCHAR(100),
    retail_desc VARCHAR(150),
    marketing_description TEXT,
    features TEXT[], -- JSON/Array representation of features 1 to 20
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Digital Assets Table
CREATE TABLE digital_assets (
    asset_id SERIAL PRIMARY KEY,
    product_id INT REFERENCES products(product_id) ON DELETE CASCADE,
    asset_type VARCHAR(50) NOT NULL, -- 'primary_image', 'alternate_image_1', 'sds', 'spec_sheet'
    file_path VARCHAR(512) NOT NULL, -- S3/Object Storage path
    source_url VARCHAR(1024) NOT NULL, -- Scraped URL
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for high-throughput lookup optimization
CREATE INDEX idx_products_mpn ON products(mfg_part_num);
CREATE INDEX idx_products_manuf ON products(part_manuf);
CREATE INDEX idx_attributes_product ON product_attributes(product_id);
```

---

## 2. Dynamic CSV Serialization Model

To compile these relational database records back into the strict **252-column CSV Delivery Format** required by the Unilog specifications, the system uses an exporter module that dynamically pivots the attributes:

1. **Identification Columns (Cols 1-23):** Populates metadata mapped directly from the `products` table (e.g., `Mfg_Part_Num`, `MANUFACTURER_NAME`, `BRAND_NAME`, `Classpath`).
2. **Descriptions (Cols 24-51):** Serializes descriptions from `product_descriptions` (incorporating `SHORT_DESC`, `LONG_DESC1`, `MOBILE_DESC`, `INVOICE_DESC`, `RETAIL_DESC`, and the 20 distinct `ITEM_FEATURES` arrays).
3. **Product Attributes (Cols 52-201):** The exporter retrieves all key-value-uom triples from `product_attributes`, sorts them alphabetically or by schema priority, and assigns them sequentially into the 50 predefined paired groups:
   * `ATTRIBUTE_LABEL X`
   * `ATTRIBUTE_VALUE X`
   * `ATTRIBUTE_UOM X` (where $X$ ranges from 1 to 50).
4. **Physical Dimensions & Logistics (Cols 202-218):** Translates physical traits like standard packaging information, length, weight, height, and volume with normalized units.
5. **Assets & Documentation (Cols 219-252):** Dynamically references URLs and filenames saved in `digital_assets` (e.g., `Product Image`, `Alternate Image 1`, `SDS`, `Specification Sheet`, `Video Link`).
