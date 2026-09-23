"""License hook tests (key file redirected to a tmp dir)."""

from __future__ import annotations

import pytest

from trade_dashboard_desktop.engine import licensing


@pytest.fixture
def key_file(tmp_path, monkeypatch):
    monkeypatch.setattr(licensing, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(licensing, "KEY_FILE", tmp_path / "license.key")
    return tmp_path / "license.key"


def test_format_valid_accepts_shape():
    assert licensing.format_valid("TD-AB12-CD34-EF56")
    assert licensing.format_valid("td-ab12-cd34-ef56")  # case-insensitive


def test_format_valid_rejects():
    assert not licensing.format_valid("nope")
    assert not licensing.format_valid("TD-SHORT")
    assert not licensing.format_valid("")


def test_check_key_none_is_community():
    status = licensing.check_key(None)
    assert status.tier == "community" and not status.valid


def test_save_and_load_roundtrip(key_file):
    status = licensing.save_key("TD-AB12-CD34-EF56")
    assert status.valid and status.tier == "pro"
    assert licensing.load_key() == "TD-AB12-CD34-EF56"
    assert licensing.current_status().valid


def test_save_rejects_bad_key(key_file):
    status = licensing.save_key("bogus")
    assert not status.valid
    assert not key_file.exists()


def test_clear_key(key_file):
    licensing.save_key("TD-AB12-CD34-EF56")
    licensing.clear_key()
    assert licensing.load_key() is None
    assert licensing.current_status().tier == "community"
