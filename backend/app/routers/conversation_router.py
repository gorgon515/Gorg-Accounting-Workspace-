from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from conversation.engine import get_conversation_engine

router = APIRouter(prefix="/api/conversation", tags=["conversation"])


def _e(e): return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/threads")
async def create_thread(request: Request):
    try:
        b = await request.json()
        return get_conversation_engine().create_thread(
            title=b.get("title", "New Thread"),
            mode=b.get("mode", "chat"),
            participants=b.get("participants", ["user", "assistant"]),
        )
    except Exception as e: return _e(e)


@router.get("/threads")
async def list_threads(status: str = "active", limit: int = 20):
    try: return get_conversation_engine().list_threads(status=status, limit=limit)
    except Exception as e: return _e(e)


@router.get("/threads/{tid}")
async def get_thread(tid: str):
    try:
        t = get_conversation_engine().get_thread(tid)
        return t or JSONResponse({"error": "Not found"}, status_code=404)
    except Exception as e: return _e(e)


@router.post("/threads/{tid}/messages")
async def send_message(tid: str, request: Request):
    try:
        b = await request.json()
        return get_conversation_engine().send_message(
            thread_id=tid,
            role=b.get("role", "user"),
            content=b.get("content", ""),
            agent_id=b.get("agent_id", ""),
            metadata=b.get("metadata", {}),
        )
    except Exception as e: return _e(e)


@router.get("/threads/{tid}/context")
async def get_context(tid: str, max_turns: int = 10):
    try: return get_conversation_engine().get_context(tid, max_turns=max_turns)
    except Exception as e: return _e(e)


@router.post("/threads/{tid}/close")
async def close_thread(tid: str, request: Request):
    try:
        b = await request.json()
        return get_conversation_engine().close_thread(tid, summary=b.get("summary", ""))
    except Exception as e: return _e(e)


@router.post("/threads/{tid}/summarize")
async def summarize_thread(tid: str):
    try: return get_conversation_engine().summarize_thread(tid)
    except Exception as e: return _e(e)


@router.get("/search")
async def search_threads(q: str = ""):
    try: return get_conversation_engine().search_threads(query=q)
    except Exception as e: return _e(e)


@router.get("/analytics")
async def analytics():
    try: return get_conversation_engine().analytics()
    except Exception as e: return _e(e)


@router.get("/stats")
async def stats():
    try: return get_conversation_engine().stats()
    except Exception as e: return _e(e)
