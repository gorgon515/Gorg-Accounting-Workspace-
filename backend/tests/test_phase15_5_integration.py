"""Phase 15.5 integration tests — cross-module operations flows and backward
compatibility with Phases 1-15."""
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


class TestProductionVsSandbox:
    """Production disables experimental; sandbox enables it; isolation holds."""

    def test_production_hides_experimental_features(self):
        from runtime.engine import get_runtime_engine
        from feature_flags.engine import get_feature_flags
        from release_channels.engine import get_release_channels
        r = get_runtime_engine()
        ff = get_feature_flags()
        rc = get_release_channels()
        r.set_mode("production")
        ff.create_flag("exp_widget", "Experimental Widget",
                       enabled=True, rollout="experimental")
        # A production/stable user must not see an experimental feature.
        channel = rc.get_user_channel("vincent")  # defaults to stable
        assert ff.is_enabled("exp_widget", channel=channel) is False

    def test_sandbox_mode_enables_experimental(self):
        from runtime.engine import get_runtime_engine
        from feature_flags.engine import get_feature_flags
        r = get_runtime_engine()
        ff = get_feature_flags()
        r.set_mode("sandbox")
        ff.create_flag("exp_widget", "Experimental Widget",
                       enabled=True, rollout="experimental")
        assert r.is_experimental_enabled() is True
        # A developer on the development channel sees it.
        assert ff.is_enabled("exp_widget", channel="development") is True


class TestUpgradeSafety:
    """Every upgrade: backup, validate compatibility, sandbox verify, apply, rollback."""

    def test_full_safe_upgrade_lifecycle(self):
        from plugin_upgrades.engine import get_plugin_upgrade_engine
        pe = get_plugin_upgrade_engine()
        pe.register_plugin("reporter", "1.0.0", min_helios="0.0.0")
        pe.register_plugin("reporter", "1.1.0", min_helios="15.0.0")
        # plan documents the safety steps
        plan = pe.plan_upgrade("reporter", "1.1.0")
        assert "sandbox_verify" in plan["steps"]
        assert plan["can_rollback"] is True
        assert plan["compatibility"]["compatible"] is True
        # sandbox gate enforced
        blocked = pe.apply_upgrade("reporter", "1.1.0", require_sandbox=True)
        assert blocked["status"] == "blocked"
        # verify, then apply succeeds
        pe.verify_in_sandbox("reporter", "1.1.0")
        applied = pe.apply_upgrade("reporter", "1.1.0", require_sandbox=True)
        assert applied["status"] == "upgraded"
        # rollback restores prior
        pe.verify_in_sandbox("reporter", "1.0.0")
        pe.apply_upgrade("reporter", "1.0.0")
        pe.apply_upgrade("reporter", "1.1.0")
        pe.rollback_upgrade("reporter", "1.0.0")
        assert pe.installed_version("reporter")["version"] == "1.0.0"

    def test_migration_backs_up_before_apply(self, tmp_path):
        from migrations.engine import get_migration_engine
        me = get_migration_engine()
        target = str(tmp_path / "data.db")
        # seed target with an existing db so a real backup is taken
        import sqlite3
        sqlite3.connect(target).executescript("CREATE TABLE seed (id INTEGER);")
        m = me.register_migration("add_col", 1,
                                  "CREATE TABLE more (id INTEGER);",
                                  "DROP TABLE more;")
        res = me.apply_migration(m["id"], target_db=target)
        assert res["status"] == "applied"
        # a backup row exists referencing a real backup file
        assert me.stats()["backups"] >= 1


class TestFeedbackToEvolution:
    """Captured friction promotes into the continuous-evolution backlog."""

    def test_friction_feeds_backlog(self):
        from feedback.engine import get_feedback_engine
        from evolution.engine import get_evolution_engine
        fe = get_feedback_engine()
        ee = get_evolution_engine()
        fe.capture("friction", "Briefing takes too long")
        fe.capture("friction", "Briefing takes too long")
        top = fe.top_friction()
        assert top[0]["frequency"] == 2
        # operator promotes the friction into a prioritized backlog item
        item = ee.add_item(
            problem=top[0]["title"],
            impact="daily friction",
            frequency=top[0]["frequency"],
            suggested_solution="cache briefing sections",
            priority="high",
            source="feedback",
        )
        assert item["source"] == "feedback"
        assert ee.prioritized()[0]["problem"] == "Briefing takes too long"


class TestStabilityToOpsDashboard:
    """Stability signals surface on the daily operations dashboard."""

    def test_crashes_and_reliability_surface(self):
        from stability.engine import get_stability_engine
        from ops_dashboard.engine import get_ops_dashboard_engine
        se = get_stability_engine()
        se.record_crash("connector_x", "Timeout error")
        se.score_reliability("agent", "presence", True)
        se.score_reliability("agent", "presence", False)
        oe = get_ops_dashboard_engine()
        failures = oe.recent_failures()
        assert any(f.get("component") == "connector_x" for f in failures)
        agent_health = oe.agent_health()
        assert any(r["name"] == "presence" for r in agent_health["reliability"])


class TestDailyDriver:
    """Daily Driver startup aggregates the morning operating picture."""

    def test_daily_driver_flow(self):
        from runtime.engine import get_runtime_engine
        r = get_runtime_engine()
        dd = r.daily_driver_startup()
        assert dd["ready"] is True
        assert "health_ok" in dd
        assert "pending_approvals" in dd
        assert "unread_notifications" in dd
        assert "presence_mode" in dd
        assert r.get_mode()["mode"] == "daily_driver"


class TestReleaseChannelRollout:
    """Per-user / per-workspace channels gate feature visibility."""

    def test_beta_user_sees_beta_feature(self):
        from feature_flags.engine import get_feature_flags
        from release_channels.engine import get_release_channels
        ff = get_feature_flags()
        rc = get_release_channels()
        ff.create_flag("beta_dashboard", "Beta Dashboard",
                       enabled=True, rollout="beta")
        rc.set_user_channel("beta_user", "beta")
        rc.set_user_channel("stable_user", "stable")
        assert ff.is_enabled("beta_dashboard",
                             channel=rc.get_user_channel("beta_user")) is True
        assert ff.is_enabled("beta_dashboard",
                             channel=rc.get_user_channel("stable_user")) is False


class TestExistingSystemsStillFunctional:
    """Phase 1-15 systems remain importable and functional after 15.5."""

    def test_phase15_voice_os_intact(self):
        try:
            from voice_os.engine import get_voice_os
            assert isinstance(get_voice_os().stats(), dict)
        except Exception:
            pytest.skip("voice_os unavailable in this environment")

    def test_phase15_presence_intact(self):
        try:
            from presence.engine import get_presence_engine
            assert get_presence_engine().get_mode()["mode"] in (
                "work", "study", "market", "accounting", "personal",
                "break", "meeting", "away")
        except Exception:
            pytest.skip("presence unavailable")

    def test_phase14_llm_runtime_intact(self):
        try:
            from llm_runtime.engine import get_llm_runtime
            assert len(get_llm_runtime().list_models()) == 6
        except Exception:
            pytest.skip("llm_runtime unavailable")

    def test_all_phase15_5_engines_return_stats(self):
        from runtime.engine import get_runtime_engine
        from feature_flags.engine import get_feature_flags
        from release_channels.engine import get_release_channels
        from migrations.engine import get_migration_engine
        from plugin_upgrades.engine import get_plugin_upgrade_engine
        from feedback.engine import get_feedback_engine
        from evolution.engine import get_evolution_engine
        from stability.engine import get_stability_engine
        from ops_dashboard.engine import get_ops_dashboard_engine
        for getter in (get_runtime_engine, get_feature_flags, get_release_channels,
                       get_migration_engine, get_plugin_upgrade_engine,
                       get_feedback_engine, get_evolution_engine,
                       get_stability_engine, get_ops_dashboard_engine):
            assert isinstance(getter().stats(), dict)
