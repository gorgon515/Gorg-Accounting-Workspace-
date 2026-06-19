from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from voice_os.engine import get_voice_os

router = APIRouter(prefix="/api/voice", tags=["voice"])


def _e(e): return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/status")
async def status():
    try: return get_voice_os().get_mode()
    except Exception as e: return _e(e)


@router.post("/mode")
async def set_mode(request: Request):
    try:
        b = await request.json()
        return get_voice_os().set_mode(b.get("mode", "idle"))
    except Exception as e: return _e(e)


@router.get("/capabilities")
async def capabilities():
    try: return get_voice_os().capabilities()
    except Exception as e: return _e(e)


@router.get("/profiles")
async def list_profiles():
    try: return get_voice_os().list_profiles()
    except Exception as e: return _e(e)


@router.post("/profiles")
async def create_profile(request: Request):
    try:
        b = await request.json()
        return get_voice_os().create_profile(
            name=b.get("name", "Default"),
            stt_engine=b.get("stt_engine", "whisper"),
            tts_engine=b.get("tts_engine", "system"),
            voice_name=b.get("voice_name", "default"),
            wake_word=b.get("wake_word", "helios"),
            language=b.get("language", "en"),
        )
    except Exception as e: return _e(e)


@router.get("/profiles/{pid}")
async def get_profile(pid: str):
    try:
        p = get_voice_os().get_profile(pid)
        return p or JSONResponse({"error": "Not found"}, status_code=404)
    except Exception as e: return _e(e)


@router.put("/profiles/{pid}")
async def update_profile(pid: str, request: Request):
    try:
        b = await request.json()
        return get_voice_os().update_profile(pid, **b)
    except Exception as e: return _e(e)


@router.post("/profiles/{pid}/activate")
async def activate_profile(pid: str):
    try:
        ok = get_voice_os().set_active_profile(pid)
        return {"success": ok, "profile_id": pid}
    except Exception as e: return _e(e)


@router.post("/stt-engine")
async def set_stt(request: Request):
    try:
        b = await request.json()
        return get_voice_os().set_stt_engine(b.get("engine", "whisper"))
    except Exception as e: return _e(e)


@router.post("/tts-engine")
async def set_tts(request: Request):
    try:
        b = await request.json()
        return get_voice_os().set_tts_engine(b.get("engine", "system"))
    except Exception as e: return _e(e)


@router.post("/synthesize")
async def synthesize(request: Request):
    try:
        b = await request.json()
        return get_voice_os().synthesize(
            text=b.get("text", ""),
            voice=b.get("voice", ""),
            engine=b.get("engine", ""),
        )
    except Exception as e: return _e(e)


@router.post("/transcribe")
async def transcribe(request: Request):
    try:
        b = await request.json()
        return get_voice_os().transcribe(
            audio_path=b.get("audio_path", ""),
            text_input=b.get("text_input", ""),
            engine=b.get("engine", ""),
        )
    except Exception as e: return _e(e)


@router.post("/wake")
async def wake(request: Request):
    try:
        b = await request.json()
        return get_voice_os().record_wake_event(
            keyword=b.get("keyword", "helios"),
            confidence=b.get("confidence", 1.0),
        )
    except Exception as e: return _e(e)


@router.get("/wake/history")
async def wake_history(limit: int = 50):
    try: return get_voice_os().wake_history(limit=limit)
    except Exception as e: return _e(e)


@router.post("/sessions")
async def start_session(request: Request):
    try:
        b = await request.json()
        return get_voice_os().start_session(profile_id=b.get("profile_id", ""))
    except Exception as e: return _e(e)


@router.get("/sessions")
async def list_sessions(limit: int = 20):
    try: return get_voice_os().list_sessions(limit=limit)
    except Exception as e: return _e(e)


@router.get("/sessions/{sid}")
async def get_session(sid: str):
    try:
        s = get_voice_os().get_session(sid)
        return s or JSONResponse({"error": "Not found"}, status_code=404)
    except Exception as e: return _e(e)


@router.post("/sessions/{sid}/end")
async def end_session(sid: str, request: Request):
    try:
        b = await request.json()
        return get_voice_os().end_session(sid, summary=b.get("summary", ""))
    except Exception as e: return _e(e)


@router.post("/sessions/{sid}/turns")
async def add_turn(sid: str, request: Request):
    try:
        b = await request.json()
        return get_voice_os().add_turn(
            session_id=sid,
            role=b.get("role", "user"),
            content=b.get("content", ""),
            latency_ms=b.get("latency_ms", 0),
            engine=b.get("engine", ""),
        )
    except Exception as e: return _e(e)


@router.get("/stats")
async def stats():
    try: return get_voice_os().stats()
    except Exception as e: return _e(e)
