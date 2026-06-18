"""Test isolation: route every HELIOS SQLite store to a fresh temp directory
before any application module imports and opens a connection. This keeps the
file-backed stores (accounting platform, intel, tasks, goals, scheduler, doc
intelligence, tax organizer) isolated and clean for each test session.
"""
import os
import tempfile

_dir = tempfile.mkdtemp(prefix="helios-tests-")
for _key in ("HELIOS_ACCT_DB", "HELIOS_INTEL_DB", "HELIOS_TASKS_DB", "HELIOS_GOALS_DB",
             "HELIOS_SCHED_DB", "HELIOS_DOCINTEL_DB", "HELIOS_TAXORG_DB"):
    os.environ.setdefault(_key, os.path.join(_dir, _key.lower() + ".db"))
