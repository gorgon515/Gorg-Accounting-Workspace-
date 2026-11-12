"""Command line entry point: python -m career_agent.cli <command>"""
import argparse
import json
import sys

from . import analytics, crm, db, discovery, documents, followup, profile, rules, server


def main(argv=None):
    ap = argparse.ArgumentParser(prog="career")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    s = sub.add_parser("serve"); s.add_argument("--port", type=int, default=8765)
    sub.add_parser("status")
    s = sub.add_parser("profile-set"); s.add_argument("section"); s.add_argument("json_file")
    sub.add_parser("profile-show")
    s = sub.add_parser("approve"); s.add_argument("what", choices=["profile", "master_documents", "submission_rules"])
    s = sub.add_parser("discover"); s.add_argument("--title-filter")
    s = sub.add_parser("ingest"); s.add_argument("json_file"); s.add_argument("--source")
    s = sub.add_parser("score"); s.add_argument("--job", type=int); s.add_argument("--rated")
    s = sub.add_parser("gate"); s.add_argument("application", type=int)
    sub.add_parser("due")
    sub.add_parser("audit-verify")
    a = ap.parse_args(argv)
    conn = db.connect()
    out = None
    if a.cmd == "init":
        out = {"db": str(db.DATA_DIR / "career.db"), "profile_missing": profile.missing_sections(conn)}
    elif a.cmd == "serve":
        return server.serve(conn, a.port)
    elif a.cmd == "status":
        out = analytics.overview(conn)
    elif a.cmd == "profile-set":
        profile.set_section(conn, a.section, json.load(open(a.json_file)))
        out = {"saved": a.section, "missing": profile.missing_sections(conn)}
    elif a.cmd == "profile-show":
        out = profile.get(conn)
    elif a.cmd == "approve":
        profile.approve(conn, a.what)
        out = profile.settings(conn)["approvals"]
    elif a.cmd == "discover":
        out = discovery.run_watchlist(conn, profile.settings(conn)["watchlist"], a.title_filter)
    elif a.cmd == "ingest":
        out = discovery.ingest(conn, json.load(open(a.json_file)), a.source)
    elif a.cmd == "score":
        ids = [a.job] if a.job else [r["id"] for r in conn.execute("SELECT id FROM jobs WHERE closed_at IS NULL")]
        rated = json.loads(a.rated) if a.rated else None
        out = {i: crm.evaluate(conn, i, rated) for i in ids}
    elif a.cmd == "gate":
        out = rules.gate(conn, a.application)
    elif a.cmd == "due":
        out = followup.due_actions(conn)
    elif a.cmd == "audit-verify":
        out = {"audit_chain_intact": db.verify_audit(conn)}
    json.dump(out, sys.stdout, indent=2, default=str)
    print()


if __name__ == "__main__":
    main()
