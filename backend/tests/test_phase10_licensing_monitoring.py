"""Phase 10 — Licensing, monitoring, and auto-update tests."""
from __future__ import annotations

import pytest


# ---- Licensing ----

def test_edition_list():
    from licensing.editions import list_editions
    editions = list_editions()
    names = {e["name"] for e in editions}
    assert names == {"professional", "firm", "enterprise"}


def test_license_generate_and_verify(tmp_path):
    from licensing.license_manager import LicenseManager
    lm = LicenseManager(str(tmp_path / "lic.db"))
    key = lm.generate("org_1", "Acme", "firm", seats=5, valid_days=30)
    result = lm.verify(key)
    assert result["valid"] is True
    assert result["payload"]["edition"] == "firm"
    assert result["payload"]["seats"] == 5


def test_license_activate(tmp_path):
    from licensing.license_manager import LicenseManager
    lm = LicenseManager(str(tmp_path / "lic.db"))
    key = lm.generate("org_2", "Beta Co", "professional", seats=1)
    act = lm.activate(key, machine_id="machine-xyz")
    assert act["success"] is True
    active = lm.get_active()
    assert active is not None
    assert active["edition"] == "professional"


def test_license_invalid(tmp_path):
    from licensing.license_manager import LicenseManager
    lm = LicenseManager(str(tmp_path / "lic.db"))
    key = lm.generate("org_3", "Gamma", "firm", seats=3)
    tampered = key[:-4] + "0000"
    result = lm.verify(tampered)
    assert result["valid"] is False


def test_license_seat_overflow(tmp_path):
    from licensing.license_manager import LicenseManager
    lm = LicenseManager(str(tmp_path / "lic.db"))
    with pytest.raises(ValueError):
        lm.generate("org_4", "TooMany", "professional", seats=99)


# ---- Monitoring: errors ----

def test_error_record_and_list(tmp_path):
    from monitoring.error_tracker import ErrorTracker
    et = ErrorTracker(str(tmp_path / "mon.db"))
    eid = et.record("ValueError", "bad input", component="accounting", severity="error")
    assert eid > 0
    errors = et.list(component="accounting")
    assert len(errors) == 1
    assert errors[0]["message"] == "bad input"


def test_error_resolve(tmp_path):
    from monitoring.error_tracker import ErrorTracker
    et = ErrorTracker(str(tmp_path / "mon.db"))
    eid = et.record("KeyError", "missing", severity="warning")
    assert et.resolve(eid, resolved_by="admin") is True
    err = et.get(eid)
    assert err["resolved"] is True


def test_error_stats(tmp_path):
    from monitoring.error_tracker import ErrorTracker
    et = ErrorTracker(str(tmp_path / "mon.db"))
    et.record("E1", "m1", severity="critical")
    et.record("E2", "m2", severity="error")
    stats = et.stats()
    assert stats["total"] == 2
    assert stats["unresolved"] == 2
    assert "critical" in stats["by_severity"]


# ---- Monitoring: performance ----

def test_performance_sample(tmp_path):
    from monitoring.performance import PerformanceSampler
    ps = PerformanceSampler(str(tmp_path / "mon.db"))
    for v in [10, 20, 30, 40, 100]:
        ps.record_sample("api.latency", v, component="api")
    pct = ps.get_percentiles("api.latency")
    assert pct["count"] == 5
    assert pct["min"] == 10
    assert pct["max"] == 100
    assert pct["p50"] >= 20


# ---- Monitoring: incidents ----

def test_incident_lifecycle(tmp_path):
    from monitoring.incidents import IncidentManager
    im = IncidentManager(str(tmp_path / "mon.db"))
    inc = im.create("DB down", "Database unreachable", severity="high", component="db")
    assert inc["status"] == "open"
    im.update_status(inc["id"], "investigating")
    assert im.resolve(inc["id"], "Restarted DB", resolved_by="ops") is True
    got = im.get(inc["id"])
    assert got["status"] == "resolved"


def test_incident_timeline(tmp_path):
    from monitoring.incidents import IncidentManager
    im = IncidentManager(str(tmp_path / "mon.db"))
    inc = im.create("Latency spike", severity="medium")
    im.add_timeline_event(inc["id"], "note", "investigating root cause", actor="eng")
    got = im.get(inc["id"])
    # created event + the added note
    assert len(got["timeline"]) >= 2


def test_incident_mttr(tmp_path):
    from monitoring.incidents import IncidentManager
    im = IncidentManager(str(tmp_path / "mon.db"))
    inc = im.create("Quick fix", severity="low")
    im.resolve(inc["id"], "fixed")
    stats = im.mttr_stats()
    assert stats["total_resolved"] >= 1


# ---- Updates ----

def test_update_check(tmp_path):
    from updates.updater import AutoUpdater
    up = AutoUpdater(str(tmp_path / "upd.db"))
    result = up.check_for_updates("stable")
    assert "update_available" in result
    assert result["current_version"]
    assert result["latest_version"]


def test_update_channels():
    from updates.channels import list_channels
    chans = {c["name"] for c in list_channels()}
    assert chans == {"stable", "beta", "dev"}


def test_update_settings(tmp_path):
    from updates.updater import AutoUpdater
    up = AutoUpdater(str(tmp_path / "upd.db"))
    up.update_settings(channel="beta", auto_install=True)
    settings = up.get_settings()
    assert settings["channel"] == "beta"
    assert settings["auto_install"] is True


def test_update_download_install_rollback(tmp_path):
    from updates.updater import AutoUpdater
    up = AutoUpdater(str(tmp_path / "upd.db"))
    dl = up.download_update("0.9.0", "stable")
    assert dl["success"] is True
    assert len(dl["checksum"]) == 64
    inst = up.install_update("0.9.0")
    assert inst["success"] is True
    rb = up.rollback()
    assert rb["success"] is True
