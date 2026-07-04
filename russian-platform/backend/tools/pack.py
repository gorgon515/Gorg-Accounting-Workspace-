"""Content pack CLI.

Usage:
    python -m tools.pack build out.pack.json --name ru-core --version 1.0.0
    python -m tools.pack validate pack.json
    python -m tools.pack install pack.json
    python -m tools.pack rollback <name> [--force]
    python -m tools.pack list

Signing: set RLP_PACK_KEY to sign on build and verify on install.
"""
import json
import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import InstalledPack
from app.services.content_packs import (
    build_pack,
    install_pack,
    rollback_pack,
    validate_pack,
)


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    command = argv[0]

    with SessionLocal() as db:
        if command == "build":
            out = argv[1]
            name = argv[argv.index("--name") + 1]
            version = argv[argv.index("--version") + 1]
            pack = build_pack(db, name, version)
            with open(out, "w", encoding="utf-8") as fh:
                json.dump(pack, fh, ensure_ascii=False)
            print(f"built {out}: {pack['manifest']['counts']} "
                  f"({'signed' if 'signature' in pack['manifest'] else 'UNSIGNED'})")
            return 0

        if command in ("validate", "install"):
            with open(argv[1], encoding="utf-8") as fh:
                pack = json.load(fh)
            report = validate_pack(pack, db)
            for error in report.errors:
                print(f"ERROR   {error}")
            for warning in report.warnings:
                print(f"warning {warning}")
            if not report.ok:
                return 1
            if command == "install":
                record = install_pack(db, pack)
                print(f"installed '{record.name}' {record.version}: "
                      f"{ {k: len(v) for k, v in record.row_ids.items()} }")
            else:
                print("pack is valid")
            return 0

        if command == "rollback":
            try:
                removed = rollback_pack(db, argv[1], force="--force" in argv)
            except (LookupError, ValueError) as exc:
                print(f"ERROR   {exc}")
                return 1
            print(f"rolled back: {removed}")
            return 0

        if command == "list":
            for pack_row in db.scalars(select(InstalledPack)):
                print(f"{pack_row.name} {pack_row.version} ({pack_row.language}) "
                      f"{'signed' if pack_row.signed else 'unsigned'} "
                      f"installed {pack_row.installed_at:%Y-%m-%d}")
            return 0

    print(f"unknown command '{command}'")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
