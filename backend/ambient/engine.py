import sqlite3, uuid, time, json
from datetime import datetime, date
from pathlib import Path
from typing import Optional

_DB = Path.home() / ".helios" / "ambient.db"


class AmbientEngine:
    _instance = None

    def __init__(self):
        self._db = str(_DB)
        _DB.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self._db) as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS briefing (
                id TEXT PRIMARY KEY, generated_at REAL, sections_json TEXT,
                voice_text TEXT, word_count INTEGER
            );
            CREATE TABLE IF NOT EXISTS reminder (
                id TEXT PRIMARY KEY, title TEXT, body TEXT, remind_at REAL,
                category TEXT, repeat TEXT DEFAULT 'none',
                created_at REAL, dismissed_at REAL, last_triggered_at REAL
            );
            CREATE TABLE IF NOT EXISTS alert (
                id TEXT PRIMARY KEY, alert_type TEXT, title TEXT, body TEXT,
                source TEXT, severity TEXT DEFAULT 'info',
                created_at REAL, acknowledged_at REAL
            );
            """)

    # ── briefing ──────────────────────────────────────────────────────────
    def generate_briefing(self, include_sections: Optional[list] = None) -> dict:
        all_sections = ["calendar", "tasks", "goals", "market", "portfolio",
                        "accounting", "tax", "research", "approvals", "system_health"]
        sections_to_build = include_sections or all_sections
        sections: dict = {}

        for s in sections_to_build:
            sections[s] = self._build_section(s)

        today = date.today().strftime("%B %d, %Y")
        voice_parts = [f"Good morning. Here is your HELIOS briefing for {today}."]
        for name, sec in sections.items():
            items = sec.get("items", [])
            if items:
                voice_parts.append(f"{sec['title']}. {'. '.join(str(i) for i in items[:5])}.")

        voice_text = " ".join(voice_parts)
        word_count = len(voice_text.split())

        bid = str(uuid.uuid4())
        now = time.time()
        with sqlite3.connect(self._db) as c:
            c.execute("INSERT INTO briefing VALUES (?,?,?,?,?)",
                      (bid, now, json.dumps(sections), voice_text, word_count))

        return {"id": bid, "generated_at": now, "sections": sections,
                "voice_text": voice_text, "word_count": word_count}

    def _build_section(self, name: str) -> dict:
        titles = {
            "calendar": "Calendar", "tasks": "Tasks", "goals": "Goals",
            "market": "Market Overview", "portfolio": "Portfolio Updates",
            "accounting": "Accounting", "tax": "Tax Developments",
            "research": "Research Alerts", "approvals": "Approval Queue",
            "system_health": "System Health",
        }
        items = []
        summary = ""
        try:
            if name == "tasks":
                from tasks.engine import get_tasks_engine
                data = get_tasks_engine().list_tasks(status="pending")
                items = [t["title"] for t in (data if isinstance(data, list) else [])[:5]]
                summary = f"{len(items)} pending tasks"
            elif name == "goals":
                from goals.engine import get_goals_engine
                data = get_goals_engine().list_goals(status="active")
                items = [g["title"] for g in (data if isinstance(data, list) else [])[:3]]
                summary = f"{len(items)} active goals"
            elif name == "approvals":
                from execution.approvals import get_approval_engine
                data = get_approval_engine().list_pending()
                items = [a.get("title", a.get("action_type", "approval")) for a in (data if isinstance(data, list) else [])[:5]]
                summary = f"{len(items)} pending approvals"
            elif name == "system_health":
                from health.monitor import get_health_monitor
                h = get_health_monitor().check()
                score = h.get("score", 100)
                items = [f"Health score: {score}/100"]
                summary = f"System health: {score}/100"
            elif name == "market":
                items = ["Market data available via Connector Center"]
                summary = "Check market connectors for live data"
            elif name == "portfolio":
                from portfolio.engine import get_portfolio_engine
                pe = get_portfolio_engine()
                stats = pe.stats() if hasattr(pe, "stats") else {}
                count = stats.get("total_portfolios", 0)
                items = [f"{count} portfolio(s) tracked"] if count else []
                summary = f"{count} portfolios"
            elif name == "accounting":
                items = ["Review accounting workbench for updates"]
                summary = "Accounting module active"
            elif name == "tax":
                items = ["Tax research and workpapers available"]
                summary = "Tax module active"
            elif name == "research":
                from research.missions import get_mission_engine
                data = get_mission_engine().list_missions(status="running")
                items = [m["title"] for m in (data if isinstance(data, list) else [])[:3]]
                summary = f"{len(items)} active research missions"
            elif name == "calendar":
                items = ["Calendar data available via integrations"]
                summary = "Check calendar connector"
        except Exception:
            pass

        return {"title": titles.get(name, name.title()), "items": items, "summary": summary}

    def get_latest_briefing(self) -> Optional[dict]:
        with sqlite3.connect(self._db) as c:
            row = c.execute(
                "SELECT * FROM briefing ORDER BY generated_at DESC LIMIT 1"
            ).fetchone()
        if not row:
            return None
        cols = ["id", "generated_at", "sections_json", "voice_text", "word_count"]
        d = dict(zip(cols, row))
        d["sections"] = json.loads(d.pop("sections_json"))
        return d

    def briefing_history(self, limit: int = 10) -> list:
        with sqlite3.connect(self._db) as c:
            rows = c.execute(
                "SELECT id, generated_at, word_count FROM briefing ORDER BY generated_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [{"id": r[0], "generated_at": r[1], "word_count": r[2]} for r in rows]

    # ── reminders ─────────────────────────────────────────────────────────
    def add_reminder(self, title: str, body: str = "", remind_at: float = 0,
                     category: str = "general", repeat: str = "none") -> dict:
        rid = str(uuid.uuid4())
        now = time.time()
        remind_at = remind_at or (now + 3600)
        with sqlite3.connect(self._db) as c:
            c.execute(
                "INSERT INTO reminder VALUES (?,?,?,?,?,?,?,NULL,NULL)",
                (rid, title, body, remind_at, category, repeat, now)
            )
        return self._get_reminder(rid)

    def _get_reminder(self, rid: str) -> Optional[dict]:
        with sqlite3.connect(self._db) as c:
            row = c.execute("SELECT * FROM reminder WHERE id=?", (rid,)).fetchone()
        if not row:
            return None
        cols = ["id","title","body","remind_at","category","repeat","created_at","dismissed_at","last_triggered_at"]
        return dict(zip(cols, row))

    def list_reminders(self, active_only: bool = True) -> list:
        with sqlite3.connect(self._db) as c:
            if active_only:
                rows = c.execute(
                    "SELECT * FROM reminder WHERE dismissed_at IS NULL ORDER BY remind_at"
                ).fetchall()
            else:
                rows = c.execute("SELECT * FROM reminder ORDER BY remind_at").fetchall()
        cols = ["id","title","body","remind_at","category","repeat","created_at","dismissed_at","last_triggered_at"]
        return [dict(zip(cols, r)) for r in rows]

    def dismiss_reminder(self, rid: str) -> bool:
        now = time.time()
        with sqlite3.connect(self._db) as c:
            n = c.execute(
                "UPDATE reminder SET dismissed_at=? WHERE id=?", (now, rid)
            ).rowcount
        return bool(n)

    def check_triggers(self) -> list:
        now = time.time()
        active = self.list_reminders(active_only=True)
        triggered = [r for r in active if r["remind_at"] <= now]
        for r in triggered:
            with sqlite3.connect(self._db) as c:
                c.execute("UPDATE reminder SET last_triggered_at=? WHERE id=?", (now, r["id"]))
        return triggered

    # ── alerts ────────────────────────────────────────────────────────────
    def record_alert(self, alert_type: str, title: str, body: str = "",
                     source: str = "", severity: str = "info") -> dict:
        aid = str(uuid.uuid4())
        now = time.time()
        with sqlite3.connect(self._db) as c:
            c.execute(
                "INSERT INTO alert VALUES (?,?,?,?,?,?,?,NULL)",
                (aid, alert_type, title, body, source, severity, now)
            )
        return {"id": aid, "alert_type": alert_type, "title": title,
                "body": body, "source": source, "severity": severity, "created_at": now}

    def list_alerts(self, limit: int = 50) -> list:
        with sqlite3.connect(self._db) as c:
            rows = c.execute(
                "SELECT * FROM alert ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        cols = ["id","alert_type","title","body","source","severity","created_at","acknowledged_at"]
        return [dict(zip(cols, r)) for r in rows]

    def acknowledge_alert(self, aid: str) -> bool:
        now = time.time()
        with sqlite3.connect(self._db) as c:
            n = c.execute(
                "UPDATE alert SET acknowledged_at=? WHERE id=?", (now, aid)
            ).rowcount
        return bool(n)

    # ── stats ─────────────────────────────────────────────────────────────
    def stats(self) -> dict:
        with sqlite3.connect(self._db) as c:
            briefings = c.execute("SELECT COUNT(*) FROM briefing").fetchone()[0]
            reminders = c.execute("SELECT COUNT(*) FROM reminder WHERE dismissed_at IS NULL").fetchone()[0]
            alerts = c.execute("SELECT COUNT(*) FROM alert WHERE acknowledged_at IS NULL").fetchone()[0]
            total_alerts = c.execute("SELECT COUNT(*) FROM alert").fetchone()[0]
        return {"briefings_generated": briefings, "active_reminders": reminders,
                "unacknowledged_alerts": alerts, "total_alerts": total_alerts}


_instance: Optional[AmbientEngine] = None


def get_ambient_engine() -> AmbientEngine:
    global _instance
    if _instance is None:
        _instance = AmbientEngine()
    return _instance
