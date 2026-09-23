"""Dashboard tabs; each exposes ``build(parent, ctx)``."""

from . import backtest_tab, data_tab, desk_tab, paper_tab, risk_tab, strategies_tab

__all__ = ["backtest_tab", "data_tab", "desk_tab", "paper_tab", "risk_tab", "strategies_tab"]
