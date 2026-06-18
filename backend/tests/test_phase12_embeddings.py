"""Phase 12 — Embedding pipeline tests (real local inference via TF-IDF + SVD)."""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))


def test_embed_single():
    from embeddings.pipeline import get_pipeline
    pipe = get_pipeline("local")
    result = pipe.embed("The revenue increased by 20% this quarter.")
    assert result.dim > 0
    assert len(result.embedding) == result.dim
    assert result.elapsed_ms >= 0
    assert result.model == "local"


def test_embed_batch():
    from embeddings.pipeline import get_pipeline
    pipe = get_pipeline("local")
    texts = ["Cash flow analysis", "Tax deduction planning", "Revenue growth strategy"]
    results = pipe.embed_batch(texts)
    assert len(results) == 3
    for r in results:
        assert len(r.embedding) == r.dim
        assert r.dim > 0


def test_dimension_consistent():
    from embeddings.pipeline import get_pipeline
    pipe = get_pipeline("local")
    r1 = pipe.embed("first sentence about finance")
    r2 = pipe.embed("second sentence about accounting")
    assert r1.dim == r2.dim


def test_embeddings_differ_across_texts():
    """Real embeddings should produce different vectors for different texts."""
    from embeddings.pipeline import get_pipeline
    pipe = get_pipeline("local")
    r1 = pipe.embed("tax deduction for home office expense")
    r2 = pipe.embed("quarterly revenue forecast projection model")
    # vectors should not be identical
    assert r1.embedding != r2.embedding


def test_cosine_similarity_finances_similar():
    """Semantically related finance texts should score higher than unrelated."""
    from embeddings.pipeline import get_pipeline
    import numpy as np
    pipe = get_pipeline("local")
    # Financial pair
    va = np.array(pipe.embed("quarterly tax payment due").embedding)
    vb = np.array(pipe.embed("quarterly estimated tax filing").embedding)
    score_related = float(np.dot(va, vb))
    # Unrelated pair
    vc = np.array(pipe.embed("quarterly tax payment due").embedding)
    vd = np.array(pipe.embed("cat sat on mat outside").embedding)
    score_unrelated = float(np.dot(vc, vd))
    # LSA: related texts should produce higher similarity
    assert score_related >= score_unrelated


def test_embedding_is_normalized():
    """Embeddings should be unit-normalized."""
    from embeddings.pipeline import get_pipeline
    import numpy as np
    pipe = get_pipeline("local")
    r = pipe.embed("normalized vector check for accounting revenue")
    norm = np.linalg.norm(r.embedding)
    assert abs(norm - 1.0) < 0.01


def test_list_models():
    from embeddings.pipeline import list_models
    models = list_models()
    assert len(models) >= 5
    keys = [m["key"] for m in models]
    assert "local" in keys
    assert "minilm" in keys


def test_benchmark():
    from embeddings.pipeline import get_pipeline
    result = get_pipeline("local").benchmark(n=5)
    assert result["samples"] == 5
    assert result["avg_ms_per_doc"] >= 0
    assert result["dim"] > 0


def test_stats():
    from embeddings.pipeline import get_pipeline
    pipe = get_pipeline("local")
    pipe.embed("stats test sentence for accounting")
    s = pipe.stats()
    assert s["total_embedded"] >= 1
    assert s["dim"] > 0


def test_quality_score():
    from embeddings.pipeline import get_pipeline
    pipe = get_pipeline("local")
    score = pipe.quality_score(
        "revenue income profit financial statement",
        "income revenue earnings profit loss",
    )
    assert -1.0 <= score <= 1.0
