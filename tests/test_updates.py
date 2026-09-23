"""Update-check hook tests (network stubbed out)."""

from __future__ import annotations

import io
import json
import urllib.error

from trade_dashboard_desktop.engine import updates


def test_is_newer():
    assert updates.is_newer("v0.2.0", "0.1.0")
    assert updates.is_newer("0.1.1", "0.1.0")
    assert not updates.is_newer("v0.1.0", "0.1.0")
    assert not updates.is_newer("v0.0.9", "0.1.0")


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_check_for_updates_newer(monkeypatch):
    payload = {"tag_name": "v0.2.0", "html_url": "https://example.com/r"}
    monkeypatch.setattr(updates.urllib.request, "urlopen",
                        lambda req, timeout: _FakeResponse(payload))
    result = updates.check_for_updates("0.1.0")
    assert result["update_available"] is True
    assert result["latest"] == "v0.2.0"
    assert result["url"] == "https://example.com/r"


def test_check_for_updates_current(monkeypatch):
    payload = {"tag_name": "v0.1.0", "html_url": "https://example.com/r"}
    monkeypatch.setattr(updates.urllib.request, "urlopen",
                        lambda req, timeout: _FakeResponse(payload))
    result = updates.check_for_updates("0.1.0")
    assert result["update_available"] is False


def test_check_for_updates_offline(monkeypatch):
    def _raise(req, timeout):
        raise urllib.error.URLError("no route to host")

    monkeypatch.setattr(updates.urllib.request, "urlopen", _raise)
    result = updates.check_for_updates("0.1.0")
    assert "error" in result
