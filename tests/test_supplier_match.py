"""Tests for the supplier matcher — status preference tiebreakers.

Primary goal: prove the fix for the "DHL shows as dissolved" bug —
when multiple suppliers match the same raw name at the same (or very
similar) similarity, the matcher must prefer an active/unverified
entity over a dissolved/liquidated one.
"""

from types import SimpleNamespace

import pytest

from hemera.models.supplier import Supplier
from hemera.services.supplier_match import (
    _pick_best_candidate,
    _pick_best_by_status,
    _status_rank,
    match_supplier,
)


def _add_supplier(db, name: str, status: str) -> Supplier:
    s = Supplier(hemera_id=f"test-{name}-{status}", name=name, status=status)
    db.add(s)
    db.flush()
    return s


# ── Status rank ordering ────────────────────────────────────────────────


def test_status_rank_orders_active_above_dissolved():
    assert _status_rank("active") < _status_rank("dissolved")
    assert _status_rank("active") < _status_rank("liquidation")
    assert _status_rank("unverified") < _status_rank("dormant")
    assert _status_rank("dormant") < _status_rank("dissolved")
    # Unknown status sits between unverified and dormant
    assert _status_rank("unverified") <= _status_rank(None) <= _status_rank("dormant")
    assert _status_rank(None) < _status_rank("dissolved")


# ── _pick_best_candidate unit tests (no DB roundtrip) ───────────────────


def _fake_supplier(id_: int, status: str | None) -> SimpleNamespace:
    return SimpleNamespace(id=id_, status=status)


def test_pick_best_candidate_picks_active_on_tied_ratios():
    dissolved = _fake_supplier(1, "dissolved")
    active = _fake_supplier(2, "active")
    result = _pick_best_candidate([(dissolved, 0.95), (active, 0.95)])
    assert result is active


def test_pick_best_candidate_picks_active_on_close_ratios():
    # 0.04 gap — within the CLOSE_ENOUGH window, so status decides
    dissolved = _fake_supplier(1, "dissolved")
    active = _fake_supplier(2, "active")
    result = _pick_best_candidate([(dissolved, 0.98), (active, 0.94)])
    assert result is active


def test_pick_best_candidate_takes_top_when_gap_is_large():
    # 0.10 gap — outside the window, so the name-similar one wins
    # regardless of status
    dissolved_close = _fake_supplier(1, "dissolved")
    active_far = _fake_supplier(2, "active")
    result = _pick_best_candidate(
        [(dissolved_close, 0.95), (active_far, 0.85)]
    )
    assert result is dissolved_close


def test_pick_best_candidate_prefers_unverified_over_dissolved():
    unverified = _fake_supplier(1, "unverified")
    dissolved = _fake_supplier(2, "dissolved")
    result = _pick_best_candidate([(unverified, 0.90), (dissolved, 0.91)])
    assert result is unverified


def test_pick_best_candidate_single_candidate():
    only = _fake_supplier(1, "dissolved")
    result = _pick_best_candidate([(only, 0.88)])
    assert result is only


def test_pick_best_by_status_breaks_ties_on_id():
    a = _fake_supplier(2, "active")
    b = _fake_supplier(1, "active")
    result = _pick_best_by_status([a, b])
    assert result is b  # lower id wins tied-status


# ── match_supplier DB integration tests ────────────────────────────────


def test_exact_match_prefers_active_over_dissolved(db):
    """Two exact-name suppliers: one dissolved, one active.
    The matcher must return the active one — this is the actual
    "DHL shows as dissolved" bug scenario.
    """
    dissolved = _add_supplier(db, "DHL", "dissolved")
    active = _add_supplier(db, "DHL", "active")

    result, method = match_supplier("DHL", db)

    assert method == "exact"
    assert result.id == active.id
    assert result.status == "active"
    assert result.id != dissolved.id


def test_exact_match_prefers_unverified_over_dissolved(db):
    """If an active record hasn't been flagged active yet but exists as
    'unverified', it should still beat a known-dissolved collision.
    """
    dissolved = _add_supplier(db, "Acme Foods", "dissolved")
    unverified = _add_supplier(db, "Acme Foods", "unverified")

    result, method = match_supplier("Acme Foods", db)

    assert method == "exact"
    assert result.id == unverified.id
    assert result.id != dissolved.id


def test_fuzzy_match_picks_active_when_normalised_names_tie(db):
    """Two suppliers whose normalised forms are identical.
    E.g. 'DHL Express UK' and 'DHL Express Ltd' both normalise to
    'DHL Express'. A raw 'DHL Express' lookup falls through the exact
    path (because neither stored name matches exactly) and into fuzzy,
    where both score 1.0 on normalised comparison — so status must win.
    """
    dissolved = _add_supplier(db, "DHL Express UK", "dissolved")
    active = _add_supplier(db, "DHL Express Ltd", "active")

    result, method = match_supplier("DHL Express", db)

    # Not an exact match because stored names include suffixes
    assert method == "fuzzy"
    assert result.id == active.id
    assert result.id != dissolved.id


def test_no_match_creates_new_supplier(db):
    """Nothing close — new entity created, marked unverified."""
    _add_supplier(db, "Totally Different Ltd", "active")

    result, method = match_supplier("Brand New Vendor", db)

    assert method == "new"
    assert result.status == "unverified"
    assert result.name == "Brand New Vendor"


def test_empty_name_creates_unknown(db):
    result, method = match_supplier("", db)
    assert method == "new"
    assert result.name in ("Unknown", "")
