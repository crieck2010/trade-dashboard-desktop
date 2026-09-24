"""Paper-service tests (engine layer, no tkinter)."""

from __future__ import annotations

import json

import pytest

from trade_dashboard_desktop import engine


@pytest.fixture
def cfg_path(tmp_path):
    p = tmp_path / "paper-config.json"
    p.write_text(json.dumps({
        "broker": {"name": "fake"},
        "data_source": "demo",
        "db_path": str(tmp_path / "trade-paper.db"),
        "symbols_equities": ["AAA"],
        "symbols_crypto": [],
    }))
    return str(p)


def test_paper_available():
    pytest.importorskip("trade_paper")
    ok, _ = engine.paper_available()
    assert ok  # trade-paper installed in the test env


def test_paper_status_fake_broker(cfg_path):
    pytest.importorskip("trade_paper")
    s = engine.paper_status(cfg_path)
    assert s["available"] and s["paper_only"]
    assert s["equity"] == 100000.0
    assert s["positions"] == []
    assert s["pending_approvals"] == 0


def test_paper_approve_roundtrip(cfg_path):
    pytest.importorskip("trade_paper")
    from trade_paper.config import PaperConfig
    from trade_paper.ledger import Ledger
    from trade_paper.models import Discovery

    cfg = PaperConfig.load(cfg_path)
    ledger = Ledger(cfg.db_path)
    d = Discovery(strategy="s", symbols=("AAA",), direction="long",
                  metrics={"sharpe_ratio": 1.5})
    ledger.record_discovery(d)
    aid = ledger.submit_approval(d, {"chain": "test"})
    ledger.close()

    out = engine.paper_approve(cfg_path, aid, reason="test")
    assert out["approved"] == aid
    rows = engine.paper_approvals(cfg_path, status="approved")["approvals"]
    assert len(rows) == 1 and rows[0]["decided_by"] == "user"


def test_paper_fidelity_empty(cfg_path):
    pytest.importorskip("trade_paper")
    f = engine.paper_fidelity(cfg_path)
    assert f["available"] and f["strategies"] == {}
