"""Account data: export, encrypted backup, restore, and global search."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.services.account_backup import (
    decrypt_backup,
    encrypt_backup,
    export_account,
    restore_account,
)
from app.services.search import global_search

router = APIRouter(prefix="/account", tags=["account"])


class ExportRequest(BaseModel):
    password: str | None = None  # provided => encrypted envelope


@router.post("/export")
def export_data(
    payload: ExportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    backup = export_account(db, user)
    if payload.password:
        return encrypt_backup(backup, payload.password)
    return backup


class ImportRequest(BaseModel):
    backup: dict
    password: str | None = None


@router.post("/import")
def import_data(
    payload: ImportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    backup = payload.backup
    if backup.get("encrypted"):
        if not payload.password:
            raise HTTPException(400, "backup is encrypted — password required")
        try:
            backup = decrypt_backup(backup, payload.password)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
    try:
        stats = restore_account(db, user, backup)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return {"restored": True, **stats}


@router.get("/search")
def search(
    q: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """One global search across dictionary (incl. inflected forms and
    fuzzy), grammar, lessons, texts, scenarios, and achievements."""
    if not q.strip():
        return {"query": q, "results": {}}
    return {"query": q, "results": global_search(db, user.id, q.strip())}
