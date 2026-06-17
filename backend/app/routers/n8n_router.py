"""N8N integration endpoints: status, workflow CRUD/monitor, and AI generation."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter

from ..models import WorkflowSpecRequest
from n8n.client import N8NClient, N8NUnavailable
from n8n import generator

router = APIRouter(prefix="/n8n", tags=["n8n"])
_client = N8NClient()


@router.get("/status")
def status() -> dict:
    return _client.status()


@router.get("/workflows")
def workflows() -> dict:
    try:
        return {"workflows": _client.list_workflows()}
    except N8NUnavailable as exc:
        return {"workflows": [], "error": str(exc)}


@router.get("/executions")
def executions(workflow_id: Optional[str] = None) -> dict:
    try:
        return {"executions": _client.list_executions(workflow_id)}
    except N8NUnavailable as exc:
        return {"executions": [], "error": str(exc)}


@router.post("/generate")
def generate(req: WorkflowSpecRequest) -> dict:
    """Generate importable N8N workflow JSON from a high-level spec (no N8N needed)."""
    if req.kind == "accounting_briefing":
        return generator.accounting_briefing_workflow(email_to=req.email_to or "you@example.com",
                                                      cron=req.schedule)
    return generator.from_spec(req.model_dump())


@router.post("/workflows")
def create(req: WorkflowSpecRequest) -> dict:
    """Generate a workflow and create it in N8N (requires N8N configured)."""
    wf = (generator.accounting_briefing_workflow(email_to=req.email_to or "you@example.com", cron=req.schedule)
          if req.kind == "accounting_briefing" else generator.from_spec(req.model_dump()))
    try:
        created = _client.create_workflow(wf)
        return {"created": created}
    except N8NUnavailable as exc:
        return {"created": None, "generated": wf, "error": str(exc)}
