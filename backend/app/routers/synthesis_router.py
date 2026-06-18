from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/synthesis", tags=["synthesis"])


class SynthesisRequest(BaseModel):
    query: str
    n_sources: int = 8
    domain: Optional[str] = None


@router.post("/synthesize")
def synthesize(req: SynthesisRequest):
    from synthesis.engine import get_synthesis_engine
    return get_synthesis_engine().synthesize(req.query, req.n_sources, req.domain)


@router.get("/reports")
def list_reports(domain: Optional[str] = None, limit: int = 20):
    from synthesis.engine import get_synthesis_engine
    return {"reports": get_synthesis_engine().list_reports(domain, limit)}


@router.get("/reports/{report_id}")
def get_report(report_id: str):
    from synthesis.engine import get_synthesis_engine
    report = get_synthesis_engine().get_report(report_id)
    if not report:
        from fastapi import HTTPException
        raise HTTPException(404, "Not found")
    return report


@router.get("/stats")
def stats():
    from synthesis.engine import get_synthesis_engine
    return get_synthesis_engine().stats()
