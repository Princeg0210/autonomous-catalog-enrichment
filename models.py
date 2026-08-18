"""
models.py — Database layer. Mirrors schema.md exactly.
Uses psycopg2 (already in tasks.py) — no new dependency.
ponytail: no ORM/repository pattern; psycopg2 execute() is sufficient for a hackathon pipeline.
         Upgrade path: swap get_conn() for SQLAlchemy engine when connection pooling matters.
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/enrichment_db")

# ── DDL ──────────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS taxonomy_categories (
    category_id SERIAL PRIMARY KEY,
    classpath   VARCHAR(512) NOT NULL UNIQUE,
    depth       INT NOT NULL DEFAULT 1,
    parent_id   INT REFERENCES taxonomy_categories(category_id)
);

CREATE TABLE IF NOT EXISTS products (
    product_id        SERIAL PRIMARY KEY,
    mfg_part_num      VARCHAR(100) NOT NULL,
    part_manuf        VARCHAR(255) NOT NULL,
    manufacturer_name VARCHAR(255),
    brand_name        VARCHAR(255),
    category_id       INT REFERENCES taxonomy_categories(category_id),
    source_url        VARCHAR(1024),
    status            VARCHAR(50) DEFAULT 'pending',
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS product_attributes (
    attribute_id    SERIAL PRIMARY KEY,
    product_id      INT REFERENCES products(product_id) ON DELETE CASCADE,
    attribute_label VARCHAR(255) NOT NULL,
    attribute_value VARCHAR(1024) NOT NULL,
    attribute_uom   VARCHAR(50),
    ref_url         TEXT,
    extracted_by    VARCHAR(255) DEFAULT 'ai-agent',
    confidence      NUMERIC(3,2) DEFAULT 1.0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS product_descriptions (
    product_id        INT PRIMARY KEY REFERENCES products(product_id) ON DELETE CASCADE,
    short_desc        VARCHAR(50),
    long_desc         VARCHAR(250),
    mobile_desc       VARCHAR(30),
    invoice_desc      VARCHAR(100),
    retail_desc       VARCHAR(150),
    marketing_desc    TEXT,
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hitl_queue (
    id          SERIAL PRIMARY KEY,
    product_id  INT REFERENCES products(product_id) ON DELETE CASCADE,
    reason      TEXT NOT NULL,
    resolved    BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_mpn    ON products(mfg_part_num);
CREATE INDEX IF NOT EXISTS idx_products_manuf  ON products(part_manuf);
CREATE INDEX IF NOT EXISTS idx_attrs_product   ON product_attributes(product_id);
"""

# ── Connection helper ─────────────────────────────────────────────────────────

def get_conn():
    """Return a psycopg2 connection. Caller owns the lifecycle."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def init_db():
    """Create tables if they don't exist. Call once at startup."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(SCHEMA_SQL)
        conn.commit()


def get_or_create_category(conn, classpath: str, depth: int = 3) -> int:
    """Get existing taxonomy category_id or create new record."""
    with conn.cursor() as cur:
        cur.execute("SELECT category_id FROM taxonomy_categories WHERE classpath = %s", (classpath,))
        row = cur.fetchone()
        if row:
            return row["category_id"]
        cur.execute(
            "INSERT INTO taxonomy_categories (classpath, depth) VALUES (%s, %s) ON CONFLICT (classpath) DO UPDATE SET depth = EXCLUDED.depth RETURNING category_id",
            (classpath, depth)
        )
        new_row = cur.fetchone()
        return new_row["category_id"]


def insert_product(conn, mfg_part_num: str, part_manuf: str, brand_name: str, source_url: str, category_id: int = None, status: str = "APPROVED") -> int:
    """Insert or update product cleanly without leaving stale attributes from previous runs."""
    with conn.cursor() as cur:
        cur.execute("SELECT product_id FROM products WHERE mfg_part_num = %s AND part_manuf = %s", (mfg_part_num, part_manuf))
        row = cur.fetchone()
        if row:
            p_id = row["product_id"]
            cur.execute(
                """UPDATE products 
                   SET brand_name = %s, source_url = %s, category_id = %s, status = %s, updated_at = NOW() 
                   WHERE product_id = %s""",
                (brand_name, source_url, category_id, status, p_id)
            )
            # Delete old attributes and descriptions to prevent stale state leakage
            cur.execute("DELETE FROM product_attributes WHERE product_id = %s", (p_id,))
            cur.execute("DELETE FROM product_descriptions WHERE product_id = %s", (p_id,))
            return p_id
        else:
            cur.execute(
                """INSERT INTO products (mfg_part_num, part_manuf, brand_name, source_url, category_id, status)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   RETURNING product_id""",
                (mfg_part_num, part_manuf, brand_name, source_url, category_id, status)
            )
            row = cur.fetchone()
            return row["product_id"]


def insert_attributes(conn, product_id: int, attributes: list, ref_url: str = None):
    """Insert verified attributes with full provenance and confidence metrics."""
    with conn.cursor() as cur:
        for a in attributes:
            if hasattr(a, "attribute_name"):
                label = a.attribute_name
                val = a.value
                uom = a.unit
                conf = a.confidence
                sku = a.sku
                src_url = a.source_url or ref_url or ""
                src_type = a.source_type or "verified_spec"
                src_lvl = getattr(a, "source_level", 3)
                v_status = getattr(a, "verification_status", "VERIFIED")
            else:
                label = a.get("label", a.get("attribute", ""))
                val = a.get("value", "")
                uom = a.get("uom", a.get("unit", ""))
                conf = a.get("confidence", 0.95)
                sku = a.get("sku", "")
                src_url = a.get("source_url", ref_url or "")
                src_type = a.get("source_type", "verified_spec")
                src_lvl = a.get("source_level", 3)
                v_status = a.get("verification_status", "VERIFIED")

            extracted_by = f"provenance:[{sku}|{src_type}|L{src_lvl}|{v_status}]" if sku else f"provenance:[verified|L{src_lvl}|{v_status}]"

            cur.execute(
                """INSERT INTO product_attributes
                   (product_id, attribute_label, attribute_value, attribute_uom, ref_url, extracted_by, confidence)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (product_id, label, str(val), uom or "", src_url, extracted_by, float(conf))
            )


def insert_descriptions(conn, product_id: int, descs: dict):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO product_descriptions
               (product_id, short_desc, long_desc, mobile_desc, invoice_desc, retail_desc)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (product_id) DO UPDATE SET
                   short_desc=EXCLUDED.short_desc, long_desc=EXCLUDED.long_desc,
                   mobile_desc=EXCLUDED.mobile_desc, invoice_desc=EXCLUDED.invoice_desc,
                   retail_desc=EXCLUDED.retail_desc, updated_at=NOW()""",
            (product_id, descs["short"], descs["long"],
             descs["mobile"], descs["invoice"], descs["retail"])
        )


def insert_hitl(conn, product_id: int, reason: str):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO hitl_queue (product_id, reason) VALUES (%s, %s)",
            (product_id, reason)
        )



# ── Query helpers for Frontend Dashboard ────────────────────────────────────

def list_products(conn, limit: int = 100):
    with conn.cursor() as cur:
        cur.execute(
            """SELECT p.product_id, p.mfg_part_num, p.part_manuf, p.brand_name, p.status,
                      p.source_url, p.created_at, p.updated_at,
                      t.classpath as category_path,
                      COUNT(CASE WHEN LOWER(a.attribute_label) NOT IN ('feature', 'certification', 'features', 'certifications') THEN a.attribute_id END) as attribute_count
               FROM products p
               LEFT JOIN taxonomy_categories t ON p.category_id = t.category_id
               LEFT JOIN product_attributes a ON p.product_id = a.product_id
               GROUP BY p.product_id, t.classpath
               ORDER BY p.updated_at DESC
               LIMIT %s""",
            (limit,)
        )
        return cur.fetchall()


def get_product_detail(conn, product_id: int):
    with conn.cursor() as cur:
        cur.execute(
            """SELECT p.*, t.classpath as category_path
               FROM products p
               LEFT JOIN taxonomy_categories t ON p.category_id = t.category_id
               WHERE p.product_id = %s""",
            (product_id,)
        )
        product = cur.fetchone()
        if not product:
            return None

        cur.execute(
            """SELECT attribute_id, attribute_label, attribute_value, attribute_uom,
                      ref_url, extracted_by, confidence
               FROM product_attributes
               WHERE product_id = %s
               ORDER BY attribute_id ASC""",
            (product_id,)
        )
        raw_attributes = cur.fetchall()

        cur.execute(
            "SELECT * FROM product_descriptions WHERE product_id = %s",
            (product_id,)
        )
        descriptions = cur.fetchone() or {}

        technical_attributes = []
        features = []
        certifications = []

        for a in raw_attributes:
            label = (a["attribute_label"] or "").strip()
            val = (a["attribute_value"] or "").strip()
            lbl_lower = label.lower()
            conf = float(a["confidence"] or 0.95)
            prov = a["extracted_by"] or "provenance:[verified]"
            ref = a["ref_url"] or ""

            if lbl_lower in ("feature", "features") or "feature:" in lbl_lower:
                features.append({
                    "feature": val,
                    "confidence": conf,
                    "provenance": prov,
                    "ref_url": ref,
                    "attribute_id": a["attribute_id"]
                })
            elif lbl_lower in ("certification", "certifications", "certified", "standard") or "cert:" in lbl_lower:
                certifications.append({
                    "certification": val,
                    "confidence": conf,
                    "provenance": prov,
                    "ref_url": ref,
                    "attribute_id": a["attribute_id"]
                })
            else:
                technical_attributes.append({
                    "attribute": label,
                    "value": val,
                    "unit": a["attribute_uom"] or "",
                    "confidence": conf,
                    "provenance": prov,
                    "ref_url": ref,
                    "attribute_id": a["attribute_id"],
                    # Backwards compatibility fields
                    "attribute_label": label,
                    "attribute_value": val,
                    "attribute_uom": a["attribute_uom"] or "",
                    "extracted_by": prov,
                })

        return {
            "product": product,
            "technical_attributes": technical_attributes,
            "features": features,
            "certifications": certifications,
            "attributes": technical_attributes, # alias for backward-compatibility
            "descriptions": descriptions,
        }


def list_hitl_items(conn):
    with conn.cursor() as cur:
        cur.execute(
            """SELECT h.id, h.product_id, h.reason, h.resolved, h.created_at,
                      p.mfg_part_num, p.part_manuf, p.brand_name
               FROM hitl_queue h
               LEFT JOIN products p ON h.product_id = p.product_id
               ORDER BY h.resolved ASC, h.created_at DESC
               LIMIT 100"""
        )
        return cur.fetchall()


def get_stats(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) as total_products FROM products")
        total_p = cur.fetchone()["total_products"]

        cur.execute("SELECT count(*) as total_attributes FROM product_attributes")
        total_a = cur.fetchone()["total_attributes"]

        cur.execute("SELECT count(*) as pending_hitl FROM hitl_queue WHERE resolved=FALSE")
        pending_h = cur.fetchone()["pending_hitl"]

        cur.execute("SELECT count(*) as total_descriptions FROM product_descriptions")
        total_d = cur.fetchone()["total_descriptions"]

        return {
            "total_products": total_p,
            "total_attributes": total_a,
            "pending_hitl": pending_h,
            "total_descriptions": total_d,
        }

