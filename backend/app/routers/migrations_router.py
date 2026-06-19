from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from migrations.engine import get_migration_engine

router = APIRouter(prefix="/api/migrations", tags=["migrations"])


def _e(e): return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/")
async def register_migration(request: Request):
    try:
        b = await request.json()
        return get_migration_engine().register_migration(
            name=b.get("name", ""),
            version=b.get("version", 0),
            up_sql=b.get("up_sql", ""),
            down_sql=b.get("down_sql", ""),
            mtype=b.get("mtype", "schema"),
        )
    except Exception as e: return _e(e)


@router.get("/")
async def list_migrations(status: str = None):
    try: return get_migration_engine().list_migrations(status=status)
    except Exception as e: return _e(e)


@router.get("/pending")
async def pending():
    try: return get_migration_engine().pending()
    except Exception as e: return _e(e)


@router.get("/applied")
async def applied():
    try: return get_migration_engine().applied()
    except Exception as e: return _e(e)


@router.get("/current-version")
async def current_version():
    try: return {"current_version": get_migration_engine().current_version()}
    except Exception as e: return _e(e)


@router.get("/history")
async def history(limit: int = 50):
    try: return get_migration_engine().history(limit=limit)
    except Exception as e: return _e(e)


@router.get("/stats")
async def stats():
    try: return get_migration_engine().stats()
    except Exception as e: return _e(e)


@router.get("/{mig_id}")
async def get_migration(mig_id: str):
    try: return get_migration_engine().get_migration(mig_id)
    except Exception as e: return _e(e)


@router.post("/{mig_id}/apply")
async def apply_migration(mig_id: str, request: Request):
    try:
        try: b = await request.json()
        except Exception: b = {}
        return get_migration_engine().apply_migration(
            mig_id, target_db=b.get("target_db")
        )
    except Exception as e: return _e(e)


@router.post("/{mig_id}/rollback")
async def rollback_migration(mig_id: str, request: Request):
    try:
        try: b = await request.json()
        except Exception: b = {}
        return get_migration_engine().rollback_migration(
            mig_id, target_db=b.get("target_db")
        )
    except Exception as e: return _e(e)


@router.post("/{mig_id}/validate")
async def validate_migration(mig_id: str):
    try: return get_migration_engine().validate_migration(mig_id)
    except Exception as e: return _e(e)
