"""
context.py — ProductContext & ProductAttribute dataclasses for strict SKU isolation.
Every SKU processed gets its own isolated ProductContext instance. No shared mutable state.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


SOURCE_LEVEL_MAP = {
    "manufacturer_pdf": (1, 0.98, "VERIFIED"),
    "manufacturer_spec": (1, 0.98, "VERIFIED"),
    "official_product_page": (2, 0.96, "VERIFIED"),
    "manufacturer_html": (2, 0.96, "VERIFIED"),
    "authoritative_dataset": (3, 0.95, "VERIFIED"),
    "catalog_dataset": (3, 0.95, "VERIFIED"),
    "product_description": (4, 0.90, "VERIFIED"),
    "verified_description": (4, 0.90, "VERIFIED"),
    "distributor": (5, 0.82, "VERIFIED"),
    "category_standard": (6, 0.75, "INFERRED"),
    "ai_inference": (7, 0.65, "INFERRED"),
    "product_identifier": (4, 0.90, "VERIFIED"),
    "unknown": (7, 0.20, "UNKNOWN"),
}


@dataclass
class ProductAttribute:
    attribute_name: str
    value: str
    unit: str
    confidence: float
    sku: str
    source_type: str = "manufacturer_spec"
    source_url: str = ""
    document_name: str = ""
    page: Optional[int] = None
    evidence: str = ""
    measurement_type: str = ""
    attribute_type: str = "specification"  # specification | feature | certification | series | product_type
    source_level: int = 3
    verification_status: str = "VERIFIED"  # VERIFIED | INFERRED | UNKNOWN
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self):
        # Automatically assign source level, verification status, and confidence range if not explicitly overridden
        if self.source_type in SOURCE_LEVEL_MAP:
            lvl, default_conf, default_status = SOURCE_LEVEL_MAP[self.source_type]
            if self.source_level == 3 and lvl != 3:
                self.source_level = lvl
            if self.verification_status == "VERIFIED" and default_status != "VERIFIED":
                self.verification_status = default_status
            if self.confidence == 0.0 or self.confidence == 0.98:
                self.confidence = default_conf

    def to_dict(self) -> dict:
        return {
            "attribute": self.attribute_name,
            "value": self.value,
            "unit": self.unit,
            "confidence": self.confidence,
            "sku": self.sku,
            "source_type": self.source_type,
            "source_url": self.source_url,
            "source_level": self.source_level,
            "verification_status": self.verification_status,
            "document": self.document_name,
            "page": self.page,
            "evidence": self.evidence,
            "measurement_type": self.measurement_type,
            "attribute_type": self.attribute_type,
            "timestamp": self.timestamp,
        }


@dataclass
class ProductContext:
    sku: str
    manufacturer: str
    brand: str
    raw_input: Dict[str, Any] = field(default_factory=dict)
    search_queries: List[str] = field(default_factory=list)
    discovered_sources: List[Dict[str, Any]] = field(default_factory=list)
    validated_sources: List[Dict[str, Any]] = field(default_factory=list)
    documents: List[Dict[str, Any]] = field(default_factory=list)
    extracted_text: str = ""
    extracted_attributes: List[ProductAttribute] = field(default_factory=list)
    normalized_attributes: List[ProductAttribute] = field(default_factory=list)
    features: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    marketing_copy: List[str] = field(default_factory=list)
    taxonomy_path: str = "General Industrial Equipment>Uncategorized"
    taxonomy_id: int = 9999
    taxonomy_confidence: float = 0.5
    taxonomy_reasoning: str = ""
    generated_descriptions: Dict[str, str] = field(default_factory=dict)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    validation_results: List[str] = field(default_factory=list)
    contamination_flags: List[str] = field(default_factory=list)
    lov_anomalies: List[str] = field(default_factory=list)
    provenance: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "PENDING"
    error_message: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def create(cls, sku: str, manufacturer: str, brand: str = "", raw_input: dict = None) -> "ProductContext":
        """Factory method to guarantee a completely isolated, clean context for a SKU."""
        return cls(
            sku=sku.strip(),
            manufacturer=manufacturer.strip(),
            brand=brand.strip() or manufacturer.strip(),
            raw_input=raw_input or {}
        )
