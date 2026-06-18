"""
Self-Improvement Engine: track accuracy of recommendations/forecasts/retrievals;
generate knowledge gaps, improvement opportunities, and training priorities.
"""
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Optional

_DB = Path(".data/self_improvement.db")


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(_DB))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("""
        CREATE TABLE IF NOT EXISTS accuracy_record (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            predicted REAL,
            actual REAL,
            accuracy REAL,
            context TEXT DEFAULT '{}',
            domain TEXT DEFAULT 'general',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS improvement_opportunity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            description TEXT NOT NULL,
            priority REAL DEFAULT 0.5,
            domain TEXT DEFAULT 'general',
            status TEXT DEFAULT 'open',
            identified_at TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS training_priority (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            topic TEXT NOT NULL,
            reason TEXT,
            priority REAL DEFAULT 0.5,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS learning_cycle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_date TEXT DEFAULT (date('now')),
            accuracy_by_kind TEXT DEFAULT '{}',
            trend TEXT DEFAULT 'stable',
            gaps_identified INTEGER DEFAULT 0,
            improvements_proposed INTEGER DEFAULT 0
        )
    """)
    c.commit()
    return c


class SelfImprovementEngine:
    def record_accuracy(
        self,
        kind: str,
        predicted: float,
        actual: float,
        domain: str = "general",
        context: Optional[dict] = None,
    ) -> dict:
        rec_id = str(uuid.uuid4())
        accuracy = 1.0 - abs(actual - predicted) / max(abs(actual), abs(predicted), 1.0)
        accuracy = round(max(0.0, min(1.0, accuracy)), 4)
        db = _conn()
        db.execute(
            """INSERT INTO accuracy_record(id, kind, predicted, actual, accuracy, context, domain)
               VALUES(?,?,?,?,?,?,?)""",
            (rec_id, kind, predicted, actual, accuracy, json.dumps(context or {}), domain),
        )
        db.commit()
        db.close()
        return {"id": rec_id, "kind": kind, "predicted": predicted,
                "actual": actual, "accuracy": accuracy, "domain": domain}

    def accuracy_by_kind(self, window: int = 30) -> dict[str, float]:
        db = _conn()
        rows = db.execute(
            """SELECT kind, AVG(accuracy) as avg_acc FROM accuracy_record
               WHERE created_at >= datetime('now', ?)
               GROUP BY kind""",
            (f"-{window} days",),
        ).fetchall()
        db.close()
        return {r["kind"]: round(r["avg_acc"], 4) for r in rows}

    def trend(self, kind: str, window: int = 14) -> str:
        db = _conn()
        rows = db.execute(
            """SELECT accuracy FROM accuracy_record
               WHERE kind=? AND created_at >= datetime('now', ?)
               ORDER BY created_at ASC""",
            (kind, f"-{window} days"),
        ).fetchall()
        db.close()
        accs = [r["accuracy"] for r in rows]
        if len(accs) < 4:
            return "insufficient_data"
        mid = len(accs) // 2
        early = sum(accs[:mid]) / mid
        late = sum(accs[mid:]) / (len(accs) - mid)
        if late > early + 0.05:
            return "improving"
        if late < early - 0.05:
            return "declining"
        return "stable"

    def history(self, kind: Optional[str] = None, limit: int = 50) -> list[dict]:
        db = _conn()
        if kind:
            rows = db.execute(
                "SELECT * FROM accuracy_record WHERE kind=? ORDER BY created_at DESC LIMIT ?",
                (kind, limit),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM accuracy_record ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        db.close()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["context"] = json.loads(d["context"])
            except Exception:
                d["context"] = {}
            result.append(d)
        return result

    def generate_opportunities(self) -> list[dict]:
        acc = self.accuracy_by_kind()
        db = _conn()
        opportunities = []
        for kind, avg_acc in acc.items():
            if avg_acc < 0.7:
                desc = f"{kind} accuracy is {avg_acc:.1%} — below 70% threshold. Review inputs and model quality."
                db.execute(
                    """INSERT INTO improvement_opportunity(kind, description, priority, domain)
                       VALUES(?,?,?,?)""",
                    (kind, desc, round(1 - avg_acc, 3), kind.split("_")[0]),
                )
                opportunities.append({"kind": kind, "description": desc, "priority": round(1 - avg_acc, 3)})
        db.commit()
        db.close()
        return opportunities

    def list_opportunities(self, status: str = "open") -> list[dict]:
        db = _conn()
        rows = db.execute(
            "SELECT * FROM improvement_opportunity WHERE status=? ORDER BY priority DESC",
            (status,),
        ).fetchall()
        db.close()
        return [dict(r) for r in rows]

    def add_training_priority(self, domain: str, topic: str, reason: str = "", priority: float = 0.5) -> dict:
        db = _conn()
        db.execute(
            "INSERT INTO training_priority(domain, topic, reason, priority) VALUES(?,?,?,?)",
            (domain, topic, reason, priority),
        )
        db.commit()
        row = db.execute("SELECT * FROM training_priority ORDER BY rowid DESC LIMIT 1").fetchone()
        db.close()
        return dict(row)

    def training_priorities(self, limit: int = 20) -> list[dict]:
        db = _conn()
        rows = db.execute(
            "SELECT * FROM training_priority ORDER BY priority DESC LIMIT ?", (limit,)
        ).fetchall()
        db.close()
        return [dict(r) for r in rows]

    def run_learning_cycle(self) -> dict:
        acc = self.accuracy_by_kind()
        trends = {k: self.trend(k) for k in acc}
        opps = self.generate_opportunities()
        db = _conn()
        db.execute(
            """INSERT INTO learning_cycle
               (accuracy_by_kind, trend, gaps_identified, improvements_proposed)
               VALUES(?,?,?,?)""",
            (json.dumps(acc), json.dumps(trends), 0, len(opps)),
        )
        db.commit()
        db.close()
        return {
            "accuracy_by_kind": acc,
            "trends": trends,
            "improvements_proposed": len(opps),
            "opportunities": opps,
        }

    def dashboard(self) -> dict:
        acc = self.accuracy_by_kind()
        db = _conn()
        opps = db.execute(
            "SELECT COUNT(*) FROM improvement_opportunity WHERE status='open'"
        ).fetchone()[0]
        priorities = db.execute(
            "SELECT COUNT(*) FROM training_priority"
        ).fetchone()[0]
        cycles = db.execute(
            "SELECT COUNT(*) FROM learning_cycle"
        ).fetchone()[0]
        db.close()
        return {
            "accuracy_by_kind": acc,
            "overall_accuracy": round(sum(acc.values()) / max(len(acc), 1), 4),
            "open_opportunities": opps,
            "training_priorities": priorities,
            "learning_cycles": cycles,
        }


_instance: Optional["SelfImprovementEngine"] = None


def get_self_improvement_engine() -> "SelfImprovementEngine":
    global _instance
    if _instance is None:
        _instance = SelfImprovementEngine()
    return _instance
