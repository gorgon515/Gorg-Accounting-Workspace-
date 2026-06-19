"""Phase 15.5 backend unit tests — Runtime modes, Feature Flags, Release Channels,
Migrations, Plugin Upgrades, Feedback, Evolution, Stability, Ops Dashboard."""
import pytest

import runtime.engine
import feature_flags.engine
import release_channels.engine
import migrations.engine
import plugin_upgrades.engine
import feedback.engine
import evolution.engine
import stability.engine
import ops_dashboard.engine


@pytest.fixture(autouse=True)
def _reset(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime.engine, "_DB", tmp_path / "runtime.db")
    monkeypatch.setattr(feature_flags.engine, "_DB", tmp_path / "feature_flags.db")
    monkeypatch.setattr(release_channels.engine, "_DB", tmp_path / "release_channels.db")
    monkeypatch.setattr(migrations.engine, "_DB", tmp_path / "migrations.db")
    monkeypatch.setattr(plugin_upgrades.engine, "_DB", tmp_path / "plugin_upgrades.db")
    monkeypatch.setattr(feedback.engine, "_DB", tmp_path / "feedback.db")
    monkeypatch.setattr(evolution.engine, "_DB", tmp_path / "evolution.db")
    monkeypatch.setattr(stability.engine, "_DB", tmp_path / "stability.db")
    monkeypatch.setattr(ops_dashboard.engine, "_DB", tmp_path / "ops_dashboard.db")
    monkeypatch.setattr(ops_dashboard.engine, "_HELIOS_DIR", tmp_path)
    for m in (runtime.engine, feature_flags.engine, release_channels.engine,
              migrations.engine, plugin_upgrades.engine, feedback.engine,
              evolution.engine, stability.engine, ops_dashboard.engine):
        m._instance = None
    yield
    for m in (runtime.engine, feature_flags.engine, release_channels.engine,
              migrations.engine, plugin_upgrades.engine, feedback.engine,
              evolution.engine, stability.engine, ops_dashboard.engine):
        m._instance = None


# ── Runtime ──────────────────────────────────────────────────────────────────

class TestRuntime:
    def test_default_mode_is_production(self):
        from runtime.engine import get_runtime_engine
        m = get_runtime_engine().get_mode()
        assert m["mode"] == "production"
        assert m["is_production"] is True
        assert m["experimental_enabled"] is False

    def test_set_mode_sandbox_enables_experimental(self):
        from runtime.engine import get_runtime_engine
        r = get_runtime_engine()
        r.set_mode("sandbox")
        assert r.get_mode()["mode"] == "sandbox"
        assert r.is_experimental_enabled() is True

    def test_invalid_mode_raises(self):
        from runtime.engine import get_runtime_engine
        with pytest.raises(ValueError):
            get_runtime_engine().set_mode("nonsense")

    def test_startup_diagnostics_structure(self):
        from runtime.engine import get_runtime_engine
        d = get_runtime_engine().run_startup_diagnostics()
        assert "ok" in d
        assert set(d["checks"].keys()) >= {"dependencies", "database_integrity", "health"}

    def test_dependency_check_ok(self):
        from runtime.engine import get_runtime_engine
        dep = get_runtime_engine().dependency_check()
        assert dep["ok"] is True
        assert any(x["name"] == "fastapi" for x in dep["dependencies"])

    def test_db_integrity_check(self):
        from runtime.engine import get_runtime_engine
        res = get_runtime_engine().db_integrity_check()
        assert "ok" in res
        assert "databases" in res

    def test_safe_startup_reports_safe(self):
        from runtime.engine import get_runtime_engine
        res = get_runtime_engine().safe_startup()
        assert "safe" in res

    def test_crash_record_and_recover(self):
        from runtime.engine import get_runtime_engine
        r = get_runtime_engine()
        crash = r.record_crash("voice_os", "boom", severity="critical")
        assert crash["recovered"] is False
        rec = r.attempt_recovery(crash["id"])
        assert rec["recovered"] is True
        assert get_runtime_engine().stats()["unrecovered_crashes"] == 0

    def test_daily_driver_startup(self):
        from runtime.engine import get_runtime_engine
        r = get_runtime_engine()
        dd = r.daily_driver_startup()
        assert dd["mode"] == "daily_driver"
        assert dd["ready"] is True
        assert "briefing_preview" in dd
        assert r.get_mode()["mode"] == "daily_driver"

    def test_stats(self):
        from runtime.engine import get_runtime_engine
        r = get_runtime_engine()
        r.run_startup_diagnostics()
        s = r.stats()
        assert s["total_startups"] >= 1
        assert s["current_mode"] == "production"


# ── Feature Flags ────────────────────────────────────────────────────────────

class TestFeatureFlags:
    def test_create_and_get(self):
        from feature_flags.engine import get_feature_flags
        ff = get_feature_flags()
        f = ff.create_flag("new_hud", "New HUD", enabled=True)
        assert f["key"] == "new_hud"
        assert f["enabled"] is True
        assert ff.get_flag("new_hud")["name"] == "New HUD"

    def test_disabled_flag_not_enabled(self):
        from feature_flags.engine import get_feature_flags
        ff = get_feature_flags()
        ff.create_flag("beta_x", "Beta X", enabled=False)
        assert ff.is_enabled("beta_x") is False

    def test_kill_switch_overrides(self):
        from feature_flags.engine import get_feature_flags
        ff = get_feature_flags()
        ff.create_flag("risky", "Risky", enabled=True)
        ff.kill("risky")
        assert ff.is_enabled("risky") is False
        ff.revive("risky")
        assert ff.is_enabled("risky") is True

    def test_channel_gating(self):
        from feature_flags.engine import get_feature_flags
        ff = get_feature_flags()
        ff.create_flag("exp_feat", "Experimental", enabled=True, rollout="experimental")
        # stable channel should NOT see an experimental flag
        assert ff.is_enabled("exp_feat", channel="stable") is False
        # development channel sees everything
        assert ff.is_enabled("exp_feat", channel="development") is True

    def test_role_gating(self):
        from feature_flags.engine import get_feature_flags
        ff = get_feature_flags()
        ff.create_flag("admin_tool", "Admin Tool", enabled=True, roles=["admin"])
        assert ff.is_enabled("admin_tool", role="admin") is True
        assert ff.is_enabled("admin_tool", role="user") is False

    def test_workspace_gating(self):
        from feature_flags.engine import get_feature_flags
        ff = get_feature_flags()
        ff.create_flag("ws_feat", "WS Feat", enabled=True, workspaces=["ws1"])
        assert ff.is_enabled("ws_feat", workspace="ws1") is True
        assert ff.is_enabled("ws_feat", workspace="ws2") is False

    def test_analytics_records_evaluations(self):
        from feature_flags.engine import get_feature_flags
        ff = get_feature_flags()
        ff.create_flag("tracked", "Tracked", enabled=True)
        ff.is_enabled("tracked")
        ff.is_enabled("tracked")
        a = ff.analytics("tracked")
        assert a["evaluations"] >= 2

    def test_unknown_channel_rollout_raises(self):
        from feature_flags.engine import get_feature_flags
        ff = get_feature_flags()
        ff.create_flag("x", "X")
        with pytest.raises(ValueError):
            ff.set_rollout("x", "bogus")

    def test_stats(self):
        from feature_flags.engine import get_feature_flags
        ff = get_feature_flags()
        ff.create_flag("a", "A", enabled=True)
        ff.create_flag("b", "B", enabled=False)
        s = ff.stats()
        assert s["total_flags"] == 2
        assert s["enabled_flags"] == 1


# ── Release Channels ─────────────────────────────────────────────────────────

class TestReleaseChannels:
    def test_four_channels(self):
        from release_channels.engine import get_release_channels
        chans = get_release_channels().list_channels()
        names = {c["name"] for c in chans}
        assert names == {"stable", "beta", "experimental", "development"}

    def test_assign_user_channel(self):
        from release_channels.engine import get_release_channels
        rc = get_release_channels()
        rc.set_user_channel("vincent", "beta")
        assert rc.get_user_channel("vincent") == "beta"

    def test_default_channel_is_stable(self):
        from release_channels.engine import get_release_channels
        rc = get_release_channels()
        assert rc.get_user_channel("unknown_user") == "stable"

    def test_invalid_channel_raises(self):
        from release_channels.engine import get_release_channels
        with pytest.raises(ValueError):
            get_release_channels().set_channel("user", "x", "bogus")

    def test_pin_and_rollback(self):
        from release_channels.engine import get_release_channels
        rc = get_release_channels()
        rc.pin_version("workspace", "ws1", "15.4.0")
        assert rc.get_pin("workspace", "ws1")["version"] == "15.4.0"
        out = rc.rollback("workspace", "ws1")
        assert out["rolled_back"] is True
        assert rc.get_pin("workspace", "ws1") is None

    def test_channel_allows_ordering(self):
        from release_channels.engine import get_release_channels
        rc = get_release_channels()
        # development channel allows experimental features
        assert rc.channel_allows("development", "experimental") is True
        # stable channel does not allow experimental features
        assert rc.channel_allows("stable", "experimental") is False

    def test_stats(self):
        from release_channels.engine import get_release_channels
        rc = get_release_channels()
        rc.set_user_channel("u1", "beta")
        rc.set_workspace_channel("w1", "experimental")
        s = rc.stats()
        assert s["total_assignments"] == 2


# ── Migrations ───────────────────────────────────────────────────────────────

class TestMigrations:
    def test_register_and_apply(self, tmp_path):
        from migrations.engine import get_migration_engine
        me = get_migration_engine()
        target = str(tmp_path / "target.db")
        m = me.register_migration(
            "create_widgets", 1,
            up_sql="CREATE TABLE widget (id INTEGER);",
            down_sql="DROP TABLE widget;")
        res = me.apply_migration(m["id"], target_db=target)
        assert res["status"] == "applied"
        assert res["integrity_ok"] is True
        assert me.current_version() == 1

    def test_apply_then_rollback(self, tmp_path):
        from migrations.engine import get_migration_engine
        me = get_migration_engine()
        target = str(tmp_path / "t2.db")
        m = me.register_migration("t", 2, "CREATE TABLE a (x INTEGER);", "DROP TABLE a;")
        me.apply_migration(m["id"], target_db=target)
        rb = me.rollback_migration(m["id"], target_db=target)
        assert rb["status"] == "rolled_back"

    def test_apply_failure_is_graceful(self, tmp_path):
        from migrations.engine import get_migration_engine
        me = get_migration_engine()
        target = str(tmp_path / "t3.db")
        m = me.register_migration("bad", 3, "THIS IS NOT SQL;", "")
        res = me.apply_migration(m["id"], target_db=target)
        assert res["status"] == "failed"
        assert "error" in res

    def test_validate_migration(self):
        from migrations.engine import get_migration_engine
        me = get_migration_engine()
        m = me.register_migration("v", 4, "CREATE TABLE z (id INTEGER);", "DROP TABLE z;")
        v = me.validate_migration(m["id"])
        assert v["valid"] is True
        assert v["has_rollback"] is True

    def test_pending_and_applied(self, tmp_path):
        from migrations.engine import get_migration_engine
        me = get_migration_engine()
        target = str(tmp_path / "t5.db")
        m1 = me.register_migration("m1", 5, "CREATE TABLE q (id INTEGER);", "")
        me.register_migration("m2", 6, "CREATE TABLE r (id INTEGER);", "")
        me.apply_migration(m1["id"], target_db=target)
        assert len(me.applied()) == 1
        assert len(me.pending()) == 1

    def test_stats(self):
        from migrations.engine import get_migration_engine
        me = get_migration_engine()
        me.register_migration("s", 7, "CREATE TABLE s (id INTEGER);", "")
        s = me.stats()
        assert s["total"] == 1
        assert s["pending"] == 1


# ── Plugin Upgrades ──────────────────────────────────────────────────────────

class TestPluginUpgrades:
    def test_register_and_compatibility(self):
        from plugin_upgrades.engine import get_plugin_upgrade_engine
        pe = get_plugin_upgrade_engine()
        pe.register_plugin("acme", "1.0.0", min_helios="15.0.0")
        c = pe.check_compatibility("acme", "1.0.0", helios_version="15.5.0")
        assert c["compatible"] is True

    def test_incompatible_min_helios(self):
        from plugin_upgrades.engine import get_plugin_upgrade_engine
        pe = get_plugin_upgrade_engine()
        pe.register_plugin("future", "2.0.0", min_helios="99.0.0")
        c = pe.check_compatibility("future", "2.0.0", helios_version="15.5.0")
        assert c["compatible"] is False

    def test_sandbox_gate_blocks_apply(self):
        from plugin_upgrades.engine import get_plugin_upgrade_engine
        pe = get_plugin_upgrade_engine()
        pe.register_plugin("p", "1.0.0", min_helios="0.0.0")
        res = pe.apply_upgrade("p", "1.0.0", require_sandbox=True)
        assert res["status"] == "blocked"
        assert "sandbox" in res["reason"].lower()

    def test_sandbox_verify_then_apply(self):
        from plugin_upgrades.engine import get_plugin_upgrade_engine
        pe = get_plugin_upgrade_engine()
        pe.register_plugin("p", "1.0.0", min_helios="0.0.0")
        pe.verify_in_sandbox("p", "1.0.0")
        res = pe.apply_upgrade("p", "1.0.0", require_sandbox=True)
        assert res["status"] == "upgraded"
        assert pe.installed_version("p")["version"] == "1.0.0"

    def test_upgrade_then_rollback(self):
        from plugin_upgrades.engine import get_plugin_upgrade_engine
        pe = get_plugin_upgrade_engine()
        pe.register_plugin("p", "1.0.0", min_helios="0.0.0")
        pe.register_plugin("p", "2.0.0", min_helios="0.0.0")
        pe.verify_in_sandbox("p", "1.0.0")
        pe.verify_in_sandbox("p", "2.0.0")
        pe.apply_upgrade("p", "1.0.0")
        pe.apply_upgrade("p", "2.0.0")
        assert pe.installed_version("p")["version"] == "2.0.0"
        pe.rollback_upgrade("p", "1.0.0")
        assert pe.installed_version("p")["version"] == "1.0.0"

    def test_dependency_resolution(self):
        from plugin_upgrades.engine import get_plugin_upgrade_engine
        pe = get_plugin_upgrade_engine()
        pe.register_plugin("base", "1.0.0", min_helios="0.0.0")
        pe.register_plugin("dependent", "1.0.0",
                           dependencies={"base": "1.0.0"}, min_helios="0.0.0")
        r = pe.resolve_dependencies("dependent", "1.0.0")
        assert r["resolved"] is True

    def test_stats(self):
        from plugin_upgrades.engine import get_plugin_upgrade_engine
        pe = get_plugin_upgrade_engine()
        pe.register_plugin("a", "1.0.0", min_helios="0.0.0")
        s = pe.stats()
        assert s["total_plugins"] == 1


# ── Feedback ─────────────────────────────────────────────────────────────────

class TestFeedback:
    def test_capture_basic(self):
        from feedback.engine import get_feedback_engine
        fe = get_feedback_engine()
        f = fe.capture("error", "Crash on save", severity="high")
        assert f["kind"] == "error"
        assert f["frequency"] == 1
        assert f["status"] == "open"

    def test_dedup_increments_frequency(self):
        from feedback.engine import get_feedback_engine
        fe = get_feedback_engine()
        fe.capture("friction", "Slow report load")
        f2 = fe.capture("friction", "Slow report load")
        assert f2["frequency"] == 2

    def test_invalid_kind_raises(self):
        from feedback.engine import get_feedback_engine
        with pytest.raises(ValueError):
            get_feedback_engine().capture("nonsense", "x")

    def test_resolve(self):
        from feedback.engine import get_feedback_engine
        fe = get_feedback_engine()
        f = fe.capture("failure", "Export failed")
        r = fe.resolve(f["id"], suggested_fix="retry with backoff")
        assert r["status"] == "resolved"
        assert r["suggested_fix"] == "retry with backoff"

    def test_top_failures(self):
        from feedback.engine import get_feedback_engine
        fe = get_feedback_engine()
        fe.capture("failure", "A")
        fe.capture("failure", "A")
        fe.capture("failure", "B")
        top = fe.top_failures()
        assert top[0]["title"] == "A"

    def test_summary_and_stats(self):
        from feedback.engine import get_feedback_engine
        fe = get_feedback_engine()
        fe.capture("usage", "Opened HUD")
        fe.capture("suggestion", "Add dark mode")
        s = fe.summary()
        assert s["total"] == 2
        assert fe.stats()["total"] == 2


# ── Evolution ────────────────────────────────────────────────────────────────

class TestEvolution:
    def test_add_and_get(self):
        from evolution.engine import get_evolution_engine
        ee = get_evolution_engine()
        i = ee.add_item("Briefing too slow", impact="daily", priority="high")
        assert i["problem"] == "Briefing too slow"
        assert i["status"] == "backlog"
        assert ee.get_item(i["id"])["priority"] == "high"

    def test_invalid_priority_raises(self):
        from evolution.engine import get_evolution_engine
        with pytest.raises(ValueError):
            get_evolution_engine().add_item("x", priority="ultra")

    def test_status_transition(self):
        from evolution.engine import get_evolution_engine
        ee = get_evolution_engine()
        i = ee.add_item("Fix X")
        ee.set_status(i["id"], "in_progress")
        assert ee.get_item(i["id"])["status"] == "in_progress"

    def test_assign(self):
        from evolution.engine import get_evolution_engine
        ee = get_evolution_engine()
        i = ee.add_item("Fix Y")
        ee.assign(i["id"], "vincent")
        assert ee.get_item(i["id"])["owner"] == "vincent"

    def test_prioritized_orders_by_score(self):
        from evolution.engine import get_evolution_engine
        ee = get_evolution_engine()
        ee.add_item("low", priority="low", frequency=1)
        ee.add_item("crit", priority="critical", frequency=5)
        p = ee.prioritized()
        assert p[0]["problem"] == "crit"

    def test_done_excluded_from_prioritized(self):
        from evolution.engine import get_evolution_engine
        ee = get_evolution_engine()
        i = ee.add_item("done item", priority="critical")
        ee.set_status(i["id"], "done")
        assert all(x["id"] != i["id"] for x in ee.prioritized())

    def test_roadmap_and_stats(self):
        from evolution.engine import get_evolution_engine
        ee = get_evolution_engine()
        ee.add_item("a")
        rm = ee.roadmap()
        assert "backlog" in rm
        assert ee.stats()["total"] == 1


# ── Stability ────────────────────────────────────────────────────────────────

class TestStability:
    def test_record_crash_and_analysis(self):
        from stability.engine import get_stability_engine
        se = get_stability_engine()
        se.record_crash("voice_os", "RuntimeError: x", severity="error")
        se.record_crash("voice_os", "RuntimeError: x", severity="error")
        a = se.crash_analysis()
        assert a["total"] == 2
        assert a["by_component"]["voice_os"] == 2

    def test_failure_clustering(self):
        from stability.engine import get_stability_engine
        se = get_stability_engine()
        se.record_crash("conn", "Timeout")
        se.record_crash("conn", "Timeout")
        se.record_crash("conn", "Other")
        clusters = se.cluster_failures()
        assert clusters[0]["count"] == 2

    def test_slow_workflows(self):
        from stability.engine import get_stability_engine
        se = get_stability_engine()
        se.record_workflow("fast", 100)
        se.record_workflow("slow", 5000)
        slow = se.slow_workflows(threshold_ms=1000)
        names = {s["name"] for s in slow}
        assert "slow" in names and "fast" not in names

    def test_long_running_tasks(self):
        from stability.engine import get_stability_engine
        se = get_stability_engine()
        se.record_task("quick", 100)
        se.record_task("long", 9000)
        longt = se.long_running_tasks(threshold_ms=5000)
        assert longt[0]["name"] == "long"

    def test_memory_leak_detection(self):
        from stability.engine import get_stability_engine
        se = get_stability_engine()
        for v in [100, 150, 200, 260, 330]:
            se.record_memory_sample(v)
        res = se.detect_memory_leak()
        assert res["leak_suspected"] is True
        assert res["growth_mb"] > 0

    def test_no_leak_when_flat(self):
        from stability.engine import get_stability_engine
        se = get_stability_engine()
        for v in [100, 100, 100, 100]:
            se.record_memory_sample(v)
        assert se.detect_memory_leak()["leak_suspected"] is False

    def test_reliability_scoring(self):
        from stability.engine import get_stability_engine
        se = get_stability_engine()
        se.score_reliability("agent", "voice_concierge", True)
        se.score_reliability("agent", "voice_concierge", False)
        scores = se.agent_reliability()
        assert scores[0]["score"] == 0.5
        assert scores[0]["total"] == 2

    def test_stats(self):
        from stability.engine import get_stability_engine
        se = get_stability_engine()
        se.record_crash("x", "y")
        assert se.stats()["crashes"] == 1


# ── Ops Dashboard ────────────────────────────────────────────────────────────

class TestOpsDashboard:
    def test_overview_has_all_sections(self):
        from ops_dashboard.engine import get_ops_dashboard_engine
        ov = get_ops_dashboard_engine().overview()
        for key in ("system_health", "agent_health", "connector_health",
                    "voice_health", "memory_growth", "storage_usage",
                    "knowledge_growth", "most_used_features",
                    "recent_failures", "pending_approvals"):
            assert key in ov

    def test_storage_usage_counts_dbs(self, tmp_path):
        from ops_dashboard.engine import get_ops_dashboard_engine
        # create a couple of db files in the patched _HELIOS_DIR
        (tmp_path / "a.db").write_bytes(b"x" * 100)
        (tmp_path / "b.db").write_bytes(b"y" * 200)
        su = get_ops_dashboard_engine().storage_usage()
        assert su["database_count"] >= 2
        assert su["total_bytes"] >= 300

    def test_snapshot_and_history(self):
        from ops_dashboard.engine import get_ops_dashboard_engine
        oe = get_ops_dashboard_engine()
        snap = oe.snapshot()
        assert "overview" in snap
        assert len(oe.snapshot_history()) == 1

    def test_recent_failures_pulls_crashes(self):
        from ops_dashboard.engine import get_ops_dashboard_engine
        from stability.engine import get_stability_engine
        get_stability_engine().record_crash("mod", "kaboom")
        failures = get_ops_dashboard_engine().recent_failures()
        assert any(f.get("component") == "mod" for f in failures)

    def test_stats(self):
        from ops_dashboard.engine import get_ops_dashboard_engine
        s = get_ops_dashboard_engine().stats()
        assert "snapshots" in s
        assert "storage_mb" in s
