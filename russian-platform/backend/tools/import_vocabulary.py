"""Bulk vocabulary importer.

Usage:
    python -m tools.import_vocabulary dataset.json           # validate only
    python -m tools.import_vocabulary dataset.json --apply   # validate + insert

Dataset: JSON array of compact rows (see docs/CONTENT_PIPELINE.md):
    [["молоко́", "n", "milk", "food", "A1", {"examples": [["...", "..."]]}], ...]

Exit code 0 = validation passed (and applied, with --apply); 1 = errors.
"""
import json
import sys

from app.core.database import SessionLocal
from app.services.content_import import apply_vocabulary, validate_vocabulary_dataset


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    path = argv[0]
    apply_changes = "--apply" in argv

    with open(path, encoding="utf-8") as fh:
        items = json.load(fh)

    with SessionLocal() as db:
        report = validate_vocabulary_dataset(items, db)
        for error in report.errors:
            print(f"ERROR   {error}")
        for warning in report.warnings:
            print(f"warning {warning}")
        print(report.summary())
        if not report.ok:
            return 1
        if apply_changes:
            inserted = apply_vocabulary(db, report.valid_items)
            print(f"inserted {inserted} lexemes")
        else:
            print("dry run — pass --apply to insert")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
