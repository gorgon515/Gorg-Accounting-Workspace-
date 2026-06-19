from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from desktop.engine import get_desktop_engine

router = APIRouter(prefix="/api/desktop", tags=["desktop"])


def _e(e): return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/launch")
async def launch_app(request: Request):
    try:
        b = await request.json()
        return get_desktop_engine().launch_app(
            name=b.get("name", ""),
            path=b.get("path", ""),
            args=b.get("args", []),
            require_approval=b.get("require_approval", True),
        )
    except Exception as e: return _e(e)


@router.get("/apps")
async def list_apps():
    try: return get_desktop_engine().list_running_apps()
    except Exception as e: return _e(e)


@router.post("/focus")
async def focus_window(request: Request):
    try:
        b = await request.json()
        return get_desktop_engine().focus_window(b.get("window_title", ""))
    except Exception as e: return _e(e)


@router.get("/clipboard")
async def read_clipboard():
    try: return get_desktop_engine().clipboard_read()
    except Exception as e: return _e(e)


@router.post("/clipboard")
async def write_clipboard(request: Request):
    try:
        b = await request.json()
        return get_desktop_engine().clipboard_write(
            content=b.get("content", ""),
            require_approval=b.get("require_approval", True),
        )
    except Exception as e: return _e(e)


@router.post("/open-file")
async def open_file(request: Request):
    try:
        b = await request.json()
        return get_desktop_engine().open_file(
            path=b.get("path", ""),
            app=b.get("app", ""),
            require_approval=b.get("require_approval", True),
        )
    except Exception as e: return _e(e)


@router.get("/directory")
async def list_dir(path: str = ""):
    try: return get_desktop_engine().list_directory(path=path)
    except Exception as e: return _e(e)


@router.get("/search-files")
async def search_files(q: str = "", path: str = "", ext: str = ""):
    try: return get_desktop_engine().search_files(query=q, path=path, ext=ext)
    except Exception as e: return _e(e)


@router.get("/system-info")
async def system_info():
    try: return get_desktop_engine().get_system_info()
    except Exception as e: return _e(e)


@router.get("/resources")
async def resources():
    try: return get_desktop_engine().monitor_resources()
    except Exception as e: return _e(e)


@router.post("/automations")
async def create_automation(request: Request):
    try:
        b = await request.json()
        return get_desktop_engine().create_automation(
            name=b.get("name", ""),
            trigger=b.get("trigger", "manual"),
            steps=b.get("steps", []),
            require_approval=b.get("require_approval", True),
        )
    except Exception as e: return _e(e)


@router.get("/automations")
async def list_automations():
    try: return get_desktop_engine().list_automations()
    except Exception as e: return _e(e)


@router.post("/automations/{aid}/run")
async def run_automation(aid: str, request: Request):
    try:
        b = await request.json()
        return get_desktop_engine().run_automation(
            aid=aid, require_approval=b.get("require_approval", True)
        )
    except Exception as e: return _e(e)


@router.get("/approvals")
async def list_approvals(status: str = "pending"):
    try: return get_desktop_engine().list_approvals(status=status)
    except Exception as e: return _e(e)


@router.post("/approvals/{aid}/approve")
async def approve(aid: str, request: Request):
    try:
        b = await request.json()
        return get_desktop_engine().approve(aid, note=b.get("note", ""))
    except Exception as e: return _e(e)


@router.post("/approvals/{aid}/reject")
async def reject(aid: str, request: Request):
    try:
        b = await request.json()
        return get_desktop_engine().reject(aid, note=b.get("note", ""))
    except Exception as e: return _e(e)


@router.get("/stats")
async def stats():
    try: return get_desktop_engine().stats()
    except Exception as e: return _e(e)
