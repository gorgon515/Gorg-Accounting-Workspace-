import sqlite3, uuid, time, json, os, platform
from pathlib import Path
from typing import Optional

_DB = Path.home() / ".helios" / "desktop.db"


class DesktopEngine:
    _instance = None

    def __init__(self):
        self._db = str(_DB)
        _DB.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._clipboard = ""

    def _init_db(self):
        with sqlite3.connect(self._db) as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS desktop_approval (
                id TEXT PRIMARY KEY, action_type TEXT, payload_json TEXT,
                status TEXT DEFAULT 'pending', created_at REAL,
                resolved_at REAL, note TEXT
            );
            CREATE TABLE IF NOT EXISTS automation (
                id TEXT PRIMARY KEY, name TEXT, trigger TEXT,
                steps_json TEXT, require_approval INTEGER DEFAULT 1,
                created_at REAL, last_run_at REAL, run_count INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS app_launch_log (
                id TEXT PRIMARY KEY, name TEXT, path TEXT,
                args_json TEXT, status TEXT, ts REAL
            );
            """)

    def _request_approval(self, action_type: str, payload: dict) -> dict:
        aid = str(uuid.uuid4())
        now = time.time()
        with sqlite3.connect(self._db) as c:
            c.execute(
                "INSERT INTO desktop_approval VALUES (?,?,?,'pending',?,NULL,NULL)",
                (aid, action_type, json.dumps(payload), now)
            )
        return {"id": aid, "action_type": action_type, "status": "pending_approval",
                "message": f"Action '{action_type}' requires human approval.", "payload": payload}

    # ── app launch ────────────────────────────────────────────────────────
    def launch_app(self, name: str, path: str = "", args: Optional[list] = None,
                   require_approval: bool = True) -> dict:
        payload = {"name": name, "path": path or name, "args": args or []}
        if require_approval:
            return self._request_approval("launch_app", payload)
        lid = str(uuid.uuid4())
        with sqlite3.connect(self._db) as c:
            c.execute(
                "INSERT INTO app_launch_log VALUES (?,?,?,?,'launched',?)",
                (lid, name, path or name, json.dumps(args or []), time.time())
            )
        return {"id": lid, "name": name, "status": "launched", "ts": time.time()}

    def list_running_apps(self) -> list:
        try:
            import psutil
            apps = []
            seen = set()
            for proc in psutil.process_iter(["pid", "name", "status"]):
                try:
                    info = proc.info
                    n = info.get("name", "")
                    if n and n not in seen and info.get("status") == "running":
                        apps.append({"pid": info["pid"], "name": n})
                        seen.add(n)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            return apps[:20]
        except ImportError:
            return [{"pid": 1, "name": "system", "note": "psutil not installed"}]

    def focus_window(self, window_title: str) -> dict:
        return {"action": "focus", "window_title": window_title,
                "status": "simulated", "note": "Requires desktop integration (Electron/native bridge)"}

    # ── clipboard ─────────────────────────────────────────────────────────
    def clipboard_read(self) -> dict:
        try:
            import subprocess
            result = subprocess.run(
                ["xclip", "-selection", "clipboard", "-o"],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                self._clipboard = result.stdout
                return {"content": self._clipboard, "source": "xclip"}
        except Exception:
            pass
        return {"content": self._clipboard, "source": "internal_cache"}

    def clipboard_write(self, content: str, require_approval: bool = True) -> dict:
        payload = {"content": content[:200] + ("…" if len(content) > 200 else "")}
        if require_approval:
            return self._request_approval("clipboard_write", payload)
        self._clipboard = content
        try:
            import subprocess
            proc = subprocess.Popen(["xclip", "-selection", "clipboard"],
                                    stdin=subprocess.PIPE, timeout=2)
            proc.communicate(input=content.encode())
        except Exception:
            pass
        return {"status": "written", "length": len(content)}

    # ── file navigation ───────────────────────────────────────────────────
    def open_file(self, path: str, app: str = "", require_approval: bool = True) -> dict:
        payload = {"path": path, "app": app}
        if require_approval:
            return self._request_approval("open_file", payload)
        return {"path": path, "status": "opened", "note": "Requires desktop bridge for actual open"}

    def list_directory(self, path: str = "") -> dict:
        target = Path(path or Path.home())
        try:
            entries = []
            for entry in sorted(target.iterdir())[:50]:
                entries.append({
                    "name": entry.name,
                    "type": "directory" if entry.is_dir() else "file",
                    "size": entry.stat().st_size if entry.is_file() else None,
                })
            return {"path": str(target), "entries": entries, "count": len(entries)}
        except PermissionError:
            return {"path": str(target), "entries": [], "error": "Permission denied"}
        except Exception as e:
            return {"path": str(target), "entries": [], "error": str(e)}

    def search_files(self, query: str, path: str = "", ext: str = "") -> list:
        target = Path(path or Path.home())
        pattern = f"*{query}*" if query else "*"
        if ext:
            pattern = f"*{query}*.{ext.lstrip('.')}"
        results = []
        try:
            for p in list(target.rglob(pattern))[:30]:
                results.append({"path": str(p), "name": p.name,
                                 "type": "directory" if p.is_dir() else "file"})
        except Exception:
            pass
        return results

    # ── system monitoring ─────────────────────────────────────────────────
    def get_system_info(self) -> dict:
        info = {
            "platform": platform.system(),
            "platform_version": platform.version()[:60],
            "processor": platform.processor() or "unknown",
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "disk_percent": 0.0,
        }
        try:
            import psutil
            info["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            info["memory_percent"] = mem.percent
            info["memory_total_gb"] = round(mem.total / 1e9, 1)
            info["memory_used_gb"] = round(mem.used / 1e9, 1)
            disk = psutil.disk_usage("/")
            info["disk_percent"] = disk.percent
            info["disk_total_gb"] = round(disk.total / 1e9, 1)
            info["disk_free_gb"] = round(disk.free / 1e9, 1)
        except ImportError:
            pass
        return info

    def monitor_resources(self) -> dict:
        return {**self.get_system_info(), "ts": time.time()}

    # ── automations ───────────────────────────────────────────────────────
    def create_automation(self, name: str, trigger: str, steps: list,
                          require_approval: bool = True) -> dict:
        aid = str(uuid.uuid4())
        now = time.time()
        with sqlite3.connect(self._db) as c:
            c.execute(
                "INSERT INTO automation VALUES (?,?,?,?,?,?,NULL,0)",
                (aid, name, trigger, json.dumps(steps), int(require_approval), now)
            )
        return self._get_automation(aid)

    def _get_automation(self, aid: str) -> Optional[dict]:
        with sqlite3.connect(self._db) as c:
            row = c.execute("SELECT * FROM automation WHERE id=?", (aid,)).fetchone()
        if not row:
            return None
        cols = ["id","name","trigger","steps_json","require_approval","created_at","last_run_at","run_count"]
        d = dict(zip(cols, row))
        d["steps"] = json.loads(d.pop("steps_json"))
        d["require_approval"] = bool(d["require_approval"])
        return d

    def list_automations(self) -> list:
        with sqlite3.connect(self._db) as c:
            rows = c.execute("SELECT * FROM automation ORDER BY created_at").fetchall()
        cols = ["id","name","trigger","steps_json","require_approval","created_at","last_run_at","run_count"]
        result = []
        for row in rows:
            d = dict(zip(cols, row))
            d["steps"] = json.loads(d.pop("steps_json"))
            d["require_approval"] = bool(d["require_approval"])
            result.append(d)
        return result

    def run_automation(self, aid: str, require_approval: bool = True) -> dict:
        auto = self._get_automation(aid)
        if not auto:
            return {"error": "Automation not found"}
        if auto["require_approval"] or require_approval:
            return self._request_approval("run_automation", {"automation_id": aid, "name": auto["name"]})
        now = time.time()
        with sqlite3.connect(self._db) as c:
            c.execute(
                "UPDATE automation SET last_run_at=?, run_count=run_count+1 WHERE id=?",
                (now, aid)
            )
        return {"automation_id": aid, "name": auto["name"],
                "status": "executed", "steps_count": len(auto["steps"])}

    # ── approvals ─────────────────────────────────────────────────────────
    def list_approvals(self, status: str = "pending") -> list:
        with sqlite3.connect(self._db) as c:
            rows = c.execute(
                "SELECT * FROM desktop_approval WHERE status=? ORDER BY created_at DESC",
                (status,)
            ).fetchall()
        cols = ["id","action_type","payload_json","status","created_at","resolved_at","note"]
        result = []
        for row in rows:
            d = dict(zip(cols, row))
            d["payload"] = json.loads(d.pop("payload_json"))
            result.append(d)
        return result

    def approve(self, action_id: str, note: str = "") -> dict:
        now = time.time()
        with sqlite3.connect(self._db) as c:
            n = c.execute(
                "UPDATE desktop_approval SET status='approved', resolved_at=?, note=? WHERE id=?",
                (now, note, action_id)
            ).rowcount
        if not n:
            return {"error": "Approval not found"}
        return {"id": action_id, "status": "approved", "resolved_at": now}

    def reject(self, action_id: str, note: str = "") -> dict:
        now = time.time()
        with sqlite3.connect(self._db) as c:
            n = c.execute(
                "UPDATE desktop_approval SET status='rejected', resolved_at=?, note=? WHERE id=?",
                (now, note, action_id)
            ).rowcount
        if not n:
            return {"error": "Approval not found"}
        return {"id": action_id, "status": "rejected", "resolved_at": now}

    def stats(self) -> dict:
        with sqlite3.connect(self._db) as c:
            pending = c.execute(
                "SELECT COUNT(*) FROM desktop_approval WHERE status='pending'"
            ).fetchone()[0]
            total_approvals = c.execute("SELECT COUNT(*) FROM desktop_approval").fetchone()[0]
            automations = c.execute("SELECT COUNT(*) FROM automation").fetchone()[0]
            launches = c.execute("SELECT COUNT(*) FROM app_launch_log").fetchone()[0]
        return {"pending_approvals": pending, "total_approvals": total_approvals,
                "automations": automations, "app_launches": launches,
                "platform": platform.system()}


_instance: Optional[DesktopEngine] = None


def get_desktop_engine() -> DesktopEngine:
    global _instance
    if _instance is None:
        _instance = DesktopEngine()
    return _instance
