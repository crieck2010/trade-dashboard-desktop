"""UI structural tests.  Widget construction is skipped when no display exists."""

from __future__ import annotations

import pytest

from trade_dashboard_desktop.ui import charts  # noqa: F401  (import check)
from trade_dashboard_desktop.ui import helpers
from trade_dashboard_desktop.ui.tabs import (
    backtest_tab,
    data_tab,
    desk_tab,
    live_tab,
    paper_tab,
    research_tab,
    risk_tab,
    strategies_tab,
)


def test_all_tabs_expose_build():
    for module in (backtest_tab, data_tab, desk_tab, live_tab, paper_tab,
                   research_tab, risk_tab, strategies_tab):
        assert callable(getattr(module, "build", None)), module.__name__


def test_parse_symbols():
    assert helpers.parse_symbols("SPY, aapl; msft") == ["SPY", "AAPL", "MSFT"]
    assert helpers.parse_symbols("  ") == []


def test_parse_params():
    params = helpers.parse_params("entry=20, exit=10, mode=fast, ratio=1.5")
    assert params == {"entry": 20, "exit": 10, "mode": "fast", "ratio": 1.5}
    assert helpers.parse_params("not-a-pair, =3") == {}


def test_app_imports_without_display():
    from trade_dashboard_desktop.ui import app as app_module

    assert hasattr(app_module, "TradeDeskApp")
    assert callable(app_module.main)


def _needs_display():
    import tkinter as tk

    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display available")
    return root


def test_app_builds_all_tabs_when_displayed():
    # Only runs where a display exists (dev machines, Windows .exe smoke).
    root = _needs_display()
    try:
        from tkinter import ttk

        from trade_dashboard_desktop.ui.app import TradeDeskApp

        application = TradeDeskApp(skip_update_check=True)
        application.update_idletasks()
        notebooks = [w for w in application.winfo_children()
                     if isinstance(w, ttk.Notebook)]
        assert len(notebooks) == 1
        assert len(notebooks[0].tabs()) == 8  # incl. Live
        application.destroy()
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def test_live_tab_threading_contract_headless():
    """Stream thread -> LatestPriceCache -> reader, no tkinter required."""
    pytest.importorskip("trade_stream")
    import threading
    import time

    import trade_stream as ts

    from trade_dashboard_desktop.ui.tabs import live_tab

    bus = ts.MessageBus()
    cache = ts.LatestPriceCache(bus)
    stop = threading.Event()
    stats, lock = {"restarts": 0, "ticks": 0}, threading.Lock()
    thread = threading.Thread(
        target=live_tab._pump,
        args=(stop, ts, bus, live_tab.DEMO_SYMBOLS, stats, lock),
        daemon=True)
    thread.start()
    deadline = time.time() + 10.0
    seen = set()
    while time.time() < deadline:
        seen |= set(cache.symbols)
        if seen == set(live_tab.DEMO_SYMBOLS) and stats["restarts"] >= 1:
            break
        time.sleep(0.05)
    stop.set()
    thread.join(timeout=5.0)
    bus.close()
    assert set(cache.symbols) == set(live_tab.DEMO_SYMBOLS)
    assert stats["ticks"] > 0
    assert stats["restarts"] >= 1  # finite demo feed exhausted + restarted
    for s in live_tab.DEMO_SYMBOLS:
        price, ts_ = cache.get(s)
        assert price > 0 and ts_ > 0
