"""Supplier entity resolution — fuzzy matching against the registry.

Matches raw supplier names from accounting data to entities in the
Hemera supplier registry. Creates new entities for unmatched suppliers.

Status preference rules (fixes the "DHL shows as dissolved" bug):
  When multiple suppliers match (either exact or fuzzy), prefer the
  active/unverified entities over dissolved or liquidated ones. A
  dissolved company is rarely the actual supplier someone is paying —
  it's almost always a name collision with a real active entity on
  Companies House.
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


# Supplier.status ranking for tie-breaking — lower is preferred.
# Unknown/None statuses are treated as "neutral" (between active and dissolved).
_STATUS_RANK: dict[str | None, int] = {
    "active": 0,
    "unverified": 1,
    "dormant": 3,
    "in administration": 4,
    "administration": 4,
    "liquidation": 5,
    "in liquidation": 5,
    "dissolved": 6,
    "struck off": 6,
}
_STATUS_UNKNOWN_RANK = 2


def _status_rank(status: str | None) -> int:
    if status is None:
        return _STATUS_UNKNOWN_RANK
    return _STATUS_RANK.get(status.strip().lower(), _STATUS_UNKNOWN_RANK)


def match_supplier(
    raw_name: str,
    db: Session,
    threshold: float = 0.85,
) -> tuple[Supplier, str]:
    """Match a raw supplier name to a registry entity.

    Returns:
        (Supplier object, match_method: "exact"|"fuzzy"|"new")

    When multiple candidates match at (approximately) the same score,
    prefer entities with a healthier status (active > unverified >
    unknown > dormant > administration > liquidation > dissolved).
    """
    if not raw_name or not raw_name.strip():
        return _create_supplier(raw_name or "Unknown", db), "new"

    clean = _normalise_name(raw_name)

    # 1. Exact match on normalised name — if multiple, prefer healthy status
    exact_matches = db.query(Supplier).filter(Supplier.name.ilike(clean)).all()
    if exact_matches:
        best = _pick_best_by_status(exact_matches)
        return best, "exact"

    # 2. Fuzzy match against all suppliers
    all_suppliers = db.query(Supplier).all()
    candidates: list[tuple[Supplier, float]] = []
    for s in all_suppliers:
        ratio = SequenceMatcher(
            None, clean.lower(), _normalise_name(s.name).lower()
        ).ratio()
        if ratio >= threshold:
            candidates.append((s, ratio))

    if candidates:
        best = _pick_best_candidate(candidates)
        return best, "fuzzy"

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


# ── Tie-breaking helpers ────────────────────────────────────────────────


def _pick_best_by_status(suppliers: list[Supplier]) -> Supplier:
    """Among equally-named suppliers, pick the one with the healthiest status.

    Secondary tiebreaker: lowest id (stable / oldest first).
    """
    return sorted(
        suppliers,
        key=lambda s: (_status_rank(s.status), s.id or 0),
    )[0]


def _pick_best_candidate(candidates: list[tuple[Supplier, float]]) -> Supplier:
    """Pick the best fuzzy match, giving status weight above a small ratio delta.

    Logic:
      - If the top candidate is more than 0.05 ahead in ratio, always take it.
        This stops a tiny "DHL" vs "DHL Ltd" preference from flipping to a
        wildly worse match.
      - Otherwise, consider every candidate within 0.05 of the top ratio and
        pick the one with the healthiest status. This is the case that fixes
        the "DHL shows as dissolved" bug: two entities both match "DHL" at
        ratio ~0.95, one dissolved, one active — we want the active one.
      - Further tiebreaker: higher ratio, then lowest id.
    """
    candidates_sorted = sorted(candidates, key=lambda c: c[1], reverse=True)
    top_ratio = candidates_sorted[0][1]

    CLOSE_ENOUGH = 0.05
    close_candidates = [c for c in candidates_sorted if top_ratio - c[1] <= CLOSE_ENOUGH]

    if len(close_candidates) == 1:
        return close_candidates[0][0]

    # Multiple candidates are effectively tied on name similarity — let status win
    def sort_key(c: tuple[Supplier, float]) -> tuple[int, float, int]:
        supplier, ratio = c
        # status_rank ascending (healthier first)
        # ratio descending (closer first)
        # id ascending (stable)
        return (_status_rank(supplier.status), -ratio, supplier.id or 0)

    return sorted(close_candidates, key=sort_key)[0][0]


# ── Name normalisation ──────────────────────────────────────────────────


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
