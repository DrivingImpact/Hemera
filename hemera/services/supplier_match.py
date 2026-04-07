"""Supplier entity resolution — fuzzy matching against the registry.

Matches raw supplier names from accounting data to entities in the
Hemera supplier registry. Creates new entities for unmatched suppliers.
"""

import uuid
import re
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
from hemera.models.supplier import Supplier


# Common suffixes to strip for matching
STRIP_SUFFIXES = [
    " limited", " ltd", " plc", " llp", " inc", " corp",
    " trading as", " t/a", " uk", " (uk)",
    " services", " group", " holdings",
]


def match_supplier(
    raw_name: str,
    db: Session,
    threshold: float = 0.85,
) -> tuple[Supplier, str]:
    """Match a raw supplier name to a registry entity.

    Returns:
        (Supplier object, match_method: "exact"|"fuzzy"|"new")
    """
    if not raw_name or not raw_name.strip():
        return _create_supplier(raw_name or "Unknown", db), "new"

    clean = _normalise_name(raw_name)

    # 1. Exact match on normalised name
    existing = db.query(Supplier).filter(Supplier.name.ilike(clean)).first()
    if existing:
        return existing, "exact"

    # 2. Fuzzy match against all suppliers
    all_suppliers = db.query(Supplier).all()
    best_match: Supplier | None = None
    best_ratio = 0.0

    for s in all_suppliers:
        ratio = SequenceMatcher(
            None, clean.lower(), _normalise_name(s.name).lower()
        ).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = s

    if best_match and best_ratio >= threshold:
        return best_match, "fuzzy"

    # 3. No match — create new supplier entity
    return _create_supplier(raw_name, db), "new"


def match_suppliers_batch(
    raw_names: list[str],
    db: Session,
) -> dict[str, tuple[Supplier, str]]:
    """Match a batch of supplier names. Deduplicates first."""
    results = {}
    unique_names = set(n.strip() for n in raw_names if n and n.strip())
    for name in unique_names:
        supplier, method = match_supplier(name, db)
        results[name.strip()] = (supplier, method)
    return results


def _normalise_name(name: str) -> str:
    """Normalise a company name for matching."""
    clean = name.strip()
    lower = clean.lower()
    for suffix in STRIP_SUFFIXES:
        if lower.endswith(suffix):
            clean = clean[: -len(suffix)].strip()
            lower = clean.lower()
    clean = re.sub(r"[^\w\s]", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def _create_supplier(raw_name: str, db: Session) -> Supplier:
    """Create a new supplier entity in the registry."""
    supplier = Supplier(
        hemera_id=str(uuid.uuid4()),
        name=raw_name.strip(),
        status="unverified",
    )
    db.add(supplier)
    db.flush()
    return supplier
