"""Shared fixtures: make the package importable without installing it."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pytest  # noqa: E402

from trade_dashboard_desktop import engine  # noqa: E402


@pytest.fixture
def data_service():
    return engine.DataService()


@pytest.fixture
def demo_bars(data_service):
    return data_service.get_bars("SPY", source="demo", days=200)
