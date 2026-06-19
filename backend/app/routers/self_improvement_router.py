from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/self-improvement", tags=["self-improvement"])


class AccuracyRecord(BaseModel):
    kind: str
    predicted: float
    actual: float
    domain: str = "general"
    context: dict = {}


class TrainingPriority(BaseModel):
    domain: str
    topic: str
    reason: str = ""
    priority: float = 0.5


@router.post("/record")
def record(req: AccuracyRecord):
    from self_improvement.engine import get_self_improvement_engine
    return get_self_improvement_engine().record_accuracy(
        req.kind, req.predicted, req.actual, req.domain, req.context
    )


@router.get("/accuracy")
def accuracy(window: int = 30):
    from self_improvement.engine import get_self_improvement_engine
    return {"accuracy_by_kind": get_self_improvement_engine().accuracy_by_kind(window)}


@router.get("/trend/{kind}")
def trend(kind: str, window: int = 14):
    from self_improvement.engine import get_self_improvement_engine
    return {"kind": kind, "trend": get_self_improvement_engine().trend(kind, window)}


@router.get("/history")
def history(kind: Optional[str] = None, limit: int = 50):
    from self_improvement.engine import get_self_improvement_engine
    return {"records": get_self_improvement_engine().history(kind, limit)}


@router.post("/opportunities/generate")
def generate_opportunities():
    from self_improvement.engine import get_self_improvement_engine
    return {"opportunities": get_self_improvement_engine().generate_opportunities()}


@router.get("/opportunities")
def list_opportunities(status: str = "open"):
    from self_improvement.engine import get_self_improvement_engine
    return {"opportunities": get_self_improvement_engine().list_opportunities(status)}


@router.post("/training-priorities")
def add_priority(req: TrainingPriority):
    from self_improvement.engine import get_self_improvement_engine
    return get_self_improvement_engine().add_training_priority(
        req.domain, req.topic, req.reason, req.priority
    )


@router.get("/training-priorities")
def list_priorities(limit: int = 20):
    from self_improvement.engine import get_self_improvement_engine
    return {"priorities": get_self_improvement_engine().training_priorities(limit)}


@router.post("/cycle")
def run_cycle():
    from self_improvement.engine import get_self_improvement_engine
    return get_self_improvement_engine().run_learning_cycle()


@router.get("/dashboard")
def dashboard():
    from self_improvement.engine import get_self_improvement_engine
    return get_self_improvement_engine().dashboard()
