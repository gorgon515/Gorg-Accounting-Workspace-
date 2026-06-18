from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/rag", tags=["rag"])


class QueryRequest(BaseModel):
    question: str
    n_results: int = 8
    domain: Optional[str] = None
    semantic_only: bool = False
    include_memory: bool = True


class SearchRequest(BaseModel):
    query: str
    n_results: int = 10
    domain: Optional[str] = None


class EmbedRequest(BaseModel):
    text: str
    model: str = "minilm"


class BatchEmbedRequest(BaseModel):
    texts: list[str]
    model: str = "minilm"


@router.post("/query")
def query(req: QueryRequest):
    from rag.platform import get_rag
    return get_rag().query(req.question, req.n_results, req.domain,
                           req.semantic_only, req.include_memory)


@router.post("/search")
def search(req: SearchRequest):
    from rag.platform import get_rag
    return {"results": get_rag().search(req.query, req.n_results, req.domain)}


@router.post("/embed")
def embed(req: EmbedRequest):
    from embeddings.pipeline import get_pipeline
    result = get_pipeline(req.model).embed(req.text)
    return {
        "text": result.text, "model": result.model, "dim": result.dim,
        "elapsed_ms": result.elapsed_ms,
        "embedding_preview": result.embedding[:8],
    }


@router.post("/embed/batch")
def embed_batch(req: BatchEmbedRequest):
    from embeddings.pipeline import get_pipeline
    results = get_pipeline(req.model).embed_batch(req.texts)
    return {
        "count": len(results), "model": req.model,
        "results": [{"text": r.text, "dim": r.dim, "elapsed_ms": r.elapsed_ms,
                     "embedding_preview": r.embedding[:4]} for r in results],
    }


@router.get("/models")
def list_models():
    from embeddings.pipeline import list_models
    return {"models": list_models()}


@router.get("/models/{model}/benchmark")
def benchmark(model: str, n: int = 20):
    from embeddings.pipeline import get_pipeline
    return get_pipeline(model).benchmark(n)


@router.get("/models/{model}/stats")
def model_stats(model: str):
    from embeddings.pipeline import get_pipeline
    return get_pipeline(model).stats()


@router.get("/collections")
def list_collections():
    from vector_memory.store import list_collections
    return {"collections": list_collections()}


@router.get("/metrics")
def metrics():
    from rag.platform import get_rag
    return get_rag().retrieval_metrics()
