"""Phase 10 — Public API, webhooks, and installer tests."""
from __future__ import annotations


# ---- API keys ----

def test_api_key_create(tmp_path):
    from public_api.api_keys import APIKeyManager
    km = APIKeyManager(str(tmp_path / "api.db"))
    created = km.create("CI key", owner_id="u1", scopes=["accounting:read"], rate_limit_rpm=120)
    assert created["api_key"].startswith("hk_")
    assert created["rate_limit_rpm"] == 120


def test_api_key_verify(tmp_path):
    from public_api.api_keys import APIKeyManager
    km = APIKeyManager(str(tmp_path / "api.db"))
    created = km.create("verify key", scopes=["reports:read"])
    result = km.verify(created["api_key"])
    assert result["valid"] is True
    assert result["scopes"] == ["reports:read"]


def test_api_key_invalid(tmp_path):
    from public_api.api_keys import APIKeyManager
    km = APIKeyManager(str(tmp_path / "api.db"))
    km.create("k", scopes=[])
    assert km.verify("hk_not_a_real_key")["valid"] is False


def test_api_key_revoke(tmp_path):
    from public_api.api_keys import APIKeyManager
    km = APIKeyManager(str(tmp_path / "api.db"))
    created = km.create("revoke key", scopes=[])
    assert km.revoke(created["key_id"]) is True
    assert km.verify(created["api_key"])["valid"] is False


def test_api_key_list_excludes_raw(tmp_path):
    from public_api.api_keys import APIKeyManager
    km = APIKeyManager(str(tmp_path / "api.db"))
    km.create("listed", scopes=[])
    keys = km.list()
    assert len(keys) == 1
    assert "key_hash" not in keys[0]
    assert "api_key" not in keys[0]


# ---- Rate limiting ----

def test_rate_limiter_allow():
    from public_api.rate_limit import RateLimiter
    rl = RateLimiter()
    result = rl.check("key-allow", rpm_limit=5)
    assert result["allowed"] is True
    assert result["current_rpm"] == 1


def test_rate_limiter_blocks_over_limit():
    from public_api.rate_limit import RateLimiter
    rl = RateLimiter()
    for _ in range(3):
        rl.check("key-block", rpm_limit=3)
    blocked = rl.check("key-block", rpm_limit=3)
    assert blocked["allowed"] is False


def test_rate_limiter_stats():
    from public_api.rate_limit import RateLimiter
    rl = RateLimiter()
    rl.check("key-stats", rpm_limit=10)
    stats = rl.get_stats("key-stats")
    assert stats["requests_last_minute"] == 1


# ---- Webhooks ----

def test_webhook_create(tmp_path):
    from public_api.webhooks import WebhookManager
    wm = WebhookManager(str(tmp_path / "api.db"))
    wh = wm.create("My hook", "https://example.com/hook", ["accounting.updated"], secret="s3cr3t")
    assert wh["url"] == "https://example.com/hook"
    assert wh["has_secret"] is True
    assert "secret" not in wh


def test_webhook_deliver(tmp_path):
    from public_api.webhooks import WebhookManager
    wm = WebhookManager(str(tmp_path / "api.db"))
    wh = wm.create("Deliver hook", "https://example.com/h", ["accounting.updated"], secret="key")
    result = wm.deliver(wh["id"], "accounting.updated", {"amount": 100})
    assert result["success"] is True
    assert result["signature"] is not None
    deliveries = wm.deliveries(wh["id"])
    assert len(deliveries) == 1


def test_webhook_deliver_unsubscribed_event(tmp_path):
    from public_api.webhooks import WebhookManager
    wm = WebhookManager(str(tmp_path / "api.db"))
    wh = wm.create("Hook", "https://example.com/h", ["backup.completed"])
    result = wm.deliver(wh["id"], "security.alert", {})
    assert result["success"] is False


def test_webhook_stats(tmp_path):
    from public_api.webhooks import WebhookManager
    wm = WebhookManager(str(tmp_path / "api.db"))
    wh = wm.create("Stat hook", "https://example.com/h", ["sync.completed"])
    wm.deliver(wh["id"], "sync.completed", {})
    stats = wm.stats(wh["id"])
    assert stats["total"] == 1
    assert stats["successful"] == 1


# ---- Installer ----

def test_install_validator():
    from installer.validate import get_validator
    result = get_validator().run_all()
    assert "passed" in result
    assert result["checks"]["python_version"]["ok"] is True


def test_setup_data_dir(tmp_path):
    from installer.setup import SetupManager
    sm = SetupManager()
    result = sm.initialize_data_directory(str(tmp_path / "data"))
    assert result["success"] is True
    assert "backups" in result["created_dirs"]


def test_setup_migrations():
    from installer.setup import get_setup_manager
    result = get_setup_manager().run_database_migrations()
    assert result["success"] is True
    assert result["migrations_run"] >= 1
