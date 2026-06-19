from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from voice_agents.agents import get_voice_agent, list_voice_agents

router = APIRouter(prefix="/api/voice-agents", tags=["voice_agents"])


def _e(e): return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/")
async def list_agents():
    try: return list_voice_agents()
    except Exception as e: return _e(e)


@router.post("/{key}/run")
async def run_agent(key: str, request: Request):
    try:
        b = await request.json()
        agent = get_voice_agent(key)
        result = agent.run(
            trigger=b.get("trigger", "manual"),
            inputs=b.get("inputs", {}),
        )
        return result.to_dict()
    except KeyError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    except Exception as e:
        return _e(e)


@router.get("/{key}/runs")
async def agent_runs(key: str, limit: int = 20):
    try:
        agent = get_voice_agent(key)
        return agent.list_runs(limit=limit)
    except KeyError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    except Exception as e:
        return _e(e)


@router.get("/{key}/actions")
async def agent_actions(key: str, status: str = "pending"):
    try:
        agent = get_voice_agent(key)
        return agent.list_proposed_actions(status=status)
    except KeyError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    except Exception as e:
        return _e(e)
