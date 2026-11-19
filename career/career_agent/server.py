"""Local dashboard + JSON API. Binds to 127.0.0.1 only; writes require a per-run token."""
import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import analytics, crm, db, documents, followup, profile

WEB = Path(__file__).parent / "web"


def state(conn):
    jobs = [crm._job(r) for r in conn.execute("SELECT * FROM jobs ORDER BY score IS NULL, score DESC, id DESC")]
    for j in jobs:
        j["description"] = (j["description"] or "")[:1500]
    apps = [dict(r) for r in conn.execute(
        "SELECT a.*, j.employer, j.title, j.url, j.score, j.comp_min, j.comp_max FROM applications a "
        "JOIN jobs j ON j.id=a.job_id ORDER BY a.updated_at DESC")]
    comms = [dict(r) for r in conn.execute(
        "SELECT c.id, c.application_id, c.ts, c.direction, c.channel, c.counterpart, c.subject, c.classification "
        "FROM communications c ORDER BY c.ts DESC LIMIT 200")]
    return {
        "overview": analytics.overview(conn), "jobs": jobs, "applications": apps, "statuses": crm.STATUSES,
        "documents": documents.listing(conn), "communications": comms,
        "interviews": [dict(r) for r in conn.execute(
            "SELECT i.*, j.employer, j.title FROM interviews i JOIN applications a ON a.id=i.application_id "
            "JOIN jobs j ON j.id=a.job_id ORDER BY i.scheduled_at")],
        "approvals": [dict(r) for r in conn.execute("SELECT * FROM approvals ORDER BY status='pending' DESC, id DESC "
                                                    "LIMIT 100")],
        "actions": followup.due_actions(conn), "settings": profile.settings(conn), "profile": profile.get(conn),
        "profile_missing": profile.missing_sections(conn),
        "audit": [dict(r) for r in conn.execute("SELECT id,ts,actor,action,target,detail FROM audit ORDER BY id DESC "
                                                "LIMIT 200")],
        "audit_intact": db.verify_audit(conn),
    }


def make_handler(conn, token):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype="application/json"):
            data = body if isinstance(body, bytes) else json.dumps(body, default=str).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline'; connect-src 'self'")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            try:
                if self.path in ("/", "/index.html"):
                    page = (WEB / "index.html").read_text().replace("__TOKEN__", token)
                    return self._send(200, page.encode(), "text/html; charset=utf-8")
                if self.path == "/api/state":
                    return self._send(200, state(conn))
                if self.path.startswith("/api/document/"):
                    return self._send(200, documents.get(conn, int(self.path.rsplit("/", 1)[1])))
                self._send(404, {"error": "not found"})
            except Exception as e:
                self._send(500, {"error": str(e)})

        def do_POST(self):
            if not secrets.compare_digest(self.headers.get("X-Career-Token", ""), token):
                return self._send(403, {"error": "bad token"})
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
                p = self.path
                if p == "/api/settings":
                    if body["key"] not in profile.DEFAULT_SETTINGS or body["key"] == "approvals":
                        raise ValueError("unknown or protected setting")
                    db.set_setting(conn, body["key"], body["value"])
                elif p == "/api/profile":
                    profile.set_section(conn, body["section"], body["value"])
                elif p == "/api/approve":
                    profile.approve(conn, body["what"])
                elif p == "/api/approval":
                    crm.resolve_approval(conn, int(body["id"]), body["status"], body.get("answer"))
                elif p == "/api/status":
                    crm.set_status(conn, int(body["id"]), body["status"], note=body.get("note"), actor="user")
                elif p == "/api/document/approve":
                    documents.approve(conn, int(body["id"]))
                else:
                    return self._send(404, {"error": "not found"})
                self._send(200, {"ok": True})
            except Exception as e:
                self._send(400, {"error": str(e)})
    return H


def serve(conn, port=8765):
    token = secrets.token_urlsafe(24)
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(conn, token))
    print(f"Career dashboard: http://127.0.0.1:{port}/")
    srv.serve_forever()
