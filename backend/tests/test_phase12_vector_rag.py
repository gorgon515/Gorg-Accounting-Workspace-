"""Phase 12 — Vector memory, RAG retrieval, knowledge engine, synthesis, self-improvement tests."""
from __future__ import annotations
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))


# ── Vector Memory ──────────────────────────────────────────────────────────────

def test_vector_add_and_search():
    from embeddings.pipeline import get_pipeline
    from vector_memory.store import VectorMemory
    vm = VectorMemory("test_col", "test")
    pipe = get_pipeline("local")
    texts = [
        "Accounts receivable collection strategy for business",
        "Tax deduction opportunities for small business owners",
        "Cash flow forecasting model for quarterly planning",
    ]
    for text in texts:
        emb = pipe.embed(text).embedding
        vm.add(text=text, embedding=emb, source="test", domain="accounting")
    results = vm.search(pipe.embed("cash flow quarterly forecast").embedding, n_results=3)
    assert len(results) >= 1
    assert results[0]["score"] >= 0.0


def test_vector_get_and_delete():
    from embeddings.pipeline import get_pipeline
    from vector_memory.store import VectorMemory
    vm = VectorMemory("test_get_del", "test")
    pipe = get_pipeline("local")
    text = "Delete this test accounting document"
    emb = pipe.embed(text).embedding
    doc_id = vm.add(text=text, embedding=emb, doc_id="del-test-001")
    assert doc_id == "del-test-001"
    got = vm.get("del-test-001")
    assert got is not None
    assert got["text"] == text
    vm.delete("del-test-001")
    got2 = vm.get("del-test-001")
    assert got2 is None


def test_vector_domain_filter():
    from embeddings.pipeline import get_pipeline
    from vector_memory.store import VectorMemory
    vm = VectorMemory("test_domain", "test")
    pipe = get_pipeline("local")
    vm.add("Tax planning document strategy", pipe.embed("Tax planning strategy").embedding, domain="tax")
    vm.add("Market analysis report equity", pipe.embed("Market analysis equity report").embedding, domain="markets")
    results = vm.search(pipe.embed("tax planning").embedding, n_results=5, domain="tax")
    for r in results:
        assert r["metadata"].get("domain") == "tax"


def test_vector_batch_add():
    from embeddings.pipeline import get_pipeline
    from vector_memory.store import VectorMemory
    vm = VectorMemory("test_batch", "test")
    pipe = get_pipeline("local")
    texts = ["Batch financial doc one", "Batch accounting doc two", "Batch tax doc three"]
    embs = [pipe.embed(t).embedding for t in texts]
    ids = vm.add_batch(texts, embs, sources=["src"] * 3, domains=["general"] * 3)
    assert len(ids) == 3


def test_vector_stats():
    from vector_memory.store import VectorMemory
    vm = VectorMemory("test_col", "test")
    s = vm.stats()
    assert "collection" in s
    assert "chroma_count" in s


# ── Knowledge Engine ───────────────────────────────────────────────────────────

def test_knowledge_ingest_and_get():
    from knowledge.engine import KnowledgeEngine
    ke = KnowledgeEngine()
    item = ke.ingest(
        title="Revenue Recognition Policy",
        content="Revenue is recognized when performance obligations are satisfied per ASC 606.",
        domain="accounting",
        kind="policy",
        source="internal",
        confidence=0.95,
    )
    assert item["id"]
    assert item["title"] == "Revenue Recognition Policy"
    assert item["quality_score"] > 0
    fetched = ke.get(item["id"])
    assert fetched["domain"] == "accounting"
    assert fetched["kind"] == "policy"


def test_knowledge_list_and_filter():
    from knowledge.engine import KnowledgeEngine
    ke = KnowledgeEngine()
    ke.ingest("Tax Loss Carryforward", "Losses may be carried forward to offset future income.",
              domain="tax", kind="fact")
    ke.ingest("Entity Selection Guide", "Choose LLC vs S-Corp based on tax efficiency.",
              domain="tax", kind="procedure")
    items = ke.list(domain="tax")
    assert len(items) >= 1


def test_knowledge_link():
    from knowledge.engine import KnowledgeEngine
    ke = KnowledgeEngine()
    a = ke.ingest("Document A linked", "First related document content.", domain="general")
    b = ke.ingest("Document B linked", "Second related document content.", domain="general")
    ke.link(a["id"], b["id"], "related_to")
    links = ke.links(a["id"])
    assert len(links) >= 1
    assert any(l["relation"] == "related_to" for l in links)


def test_knowledge_update():
    from knowledge.engine import KnowledgeEngine
    ke = KnowledgeEngine()
    item = ke.ingest("Updateable Knowledge Doc", "Original content for update test.", domain="general")
    old_quality = item["quality_score"]
    updated = ke.update(item["id"], confidence=0.99, authority=0.95)
    assert updated["confidence"] == pytest.approx(0.99, abs=0.01)
    assert updated["quality_score"] >= old_quality


def test_knowledge_add_and_resolve_gap():
    from knowledge.engine import KnowledgeEngine
    ke = KnowledgeEngine()
    gap = ke.add_gap("tax", "No information on crypto tax treatment", priority=0.8)
    assert gap["domain"] == "tax"
    gaps = ke.gaps("open")
    assert len(gaps) >= 1


def test_knowledge_health():
    from knowledge.engine import KnowledgeEngine
    ke = KnowledgeEngine()
    ke.ingest("Health Check Document", "Some content for health check metrics.", domain="strategy")
    h = ke.health()
    assert h["total_items"] >= 1
    assert "by_domain" in h
    assert "avg_quality" in h
    assert "vector_count" in ke.stats()


# ── Institutional Memory ───────────────────────────────────────────────────────

def test_institutional_memory_record_and_get():
    from knowledge.memory import InstitutionalMemory
    mem = InstitutionalMemory()
    event = mem.record(
        event_type="decision",
        title="Adopted FIFO inventory method",
        description="Chose FIFO over LIFO for inventory valuation.",
        decision="Use FIFO",
        rationale="Better matches current cost with revenue.",
        confidence=0.9,
        who="CFO",
        domain="accounting",
    )
    assert event["id"]
    fetched = mem.get(event["id"])
    assert fetched["event_type"] == "decision"
    assert fetched["who"] == "CFO"


def test_institutional_memory_keyword_search():
    from knowledge.memory import InstitutionalMemory
    mem = InstitutionalMemory()
    mem.record("lesson_learned", "Always reconcile monthly bank statements",
               "Bank reconciliation is critical to accurate accounting.",
               domain="accounting")
    results = mem.search_by_keyword("reconcil")
    assert len(results) >= 1


def test_institutional_memory_update_outcome():
    from knowledge.memory import InstitutionalMemory
    mem = InstitutionalMemory()
    event = mem.record("recommendation", "Increase prices by 5%", "Based on cost analysis.")
    updated = mem.update_outcome(event["id"], outcome="Revenue up 8%", confidence=0.95)
    assert updated["outcome"] == "Revenue up 8%"


def test_institutional_memory_stats():
    from knowledge.memory import InstitutionalMemory
    mem = InstitutionalMemory()
    s = mem.stats()
    assert "total_events" in s
    assert s["total_events"] >= 1
    assert "by_type" in s


# ── Self-Improvement Engine ────────────────────────────────────────────────────

def test_self_improvement_record_accuracy():
    from self_improvement.engine import SelfImprovementEngine
    eng = SelfImprovementEngine()
    rec = eng.record_accuracy("forecast", predicted=100.0, actual=95.0, domain="finance")
    assert rec["accuracy"] == pytest.approx(0.95, abs=0.02)
    assert rec["kind"] == "forecast"


def test_self_improvement_perfect_accuracy():
    from self_improvement.engine import SelfImprovementEngine
    eng = SelfImprovementEngine()
    rec = eng.record_accuracy("recommendation", predicted=50.0, actual=50.0)
    assert rec["accuracy"] == pytest.approx(1.0, abs=0.01)


def test_self_improvement_accuracy_by_kind():
    from self_improvement.engine import SelfImprovementEngine
    eng = SelfImprovementEngine()
    eng.record_accuracy("retrieval", predicted=80.0, actual=82.0)
    acc = eng.accuracy_by_kind()
    assert len(acc) >= 1


def test_self_improvement_trend_insufficient():
    from self_improvement.engine import SelfImprovementEngine
    eng = SelfImprovementEngine()
    t = eng.trend("never_recorded_metric_xyz")
    assert t == "insufficient_data"


def test_self_improvement_generate_opportunities():
    from self_improvement.engine import SelfImprovementEngine
    eng = SelfImprovementEngine()
    for _ in range(3):
        eng.record_accuracy("search_quality", predicted=100.0, actual=40.0)
    opps = eng.generate_opportunities()
    low_acc_kinds = [o["kind"] for o in opps]
    assert "search_quality" in low_acc_kinds


def test_self_improvement_training_priority():
    from self_improvement.engine import SelfImprovementEngine
    eng = SelfImprovementEngine()
    tp = eng.add_training_priority("tax", "crypto taxation rules", "gap in knowledge base", 0.9)
    assert tp["domain"] == "tax"
    priorities = eng.training_priorities()
    assert len(priorities) >= 1


def test_self_improvement_learning_cycle():
    from self_improvement.engine import SelfImprovementEngine
    eng = SelfImprovementEngine()
    result = eng.run_learning_cycle()
    assert "accuracy_by_kind" in result
    assert "improvements_proposed" in result


def test_self_improvement_dashboard():
    from self_improvement.engine import SelfImprovementEngine
    eng = SelfImprovementEngine()
    d = eng.dashboard()
    assert "accuracy_by_kind" in d
    assert "overall_accuracy" in d
    assert "open_opportunities" in d


# ── Hybrid Retrieval ───────────────────────────────────────────────────────────

def test_hybrid_retriever_finds_relevant():
    from knowledge.engine import KnowledgeEngine
    ke = KnowledgeEngine()
    ke.ingest("Quarterly Tax Filing", "Estimated quarterly taxes are due April 15, June 15.",
              domain="tax")
    ke.ingest("Annual Budget Planning", "Budget cycles run from January to December for accounting.",
              domain="finance")
    ke.ingest("Invoice Management", "Invoices should be collected within 30 days of billing.",
              domain="accounting")

    from rag.retriever import HybridRetriever
    ret = HybridRetriever("knowledge")
    docs = ret.retrieve("tax filing quarterly", n_results=3)
    assert len(docs) >= 1
    top_text = docs[0].text.lower()
    assert any(w in top_text for w in ["tax", "quarterly", "due", "april", "june"])


def test_rag_platform_query():
    from rag.platform import RAGPlatform
    rag = RAGPlatform("knowledge")
    result = rag.query("budget planning annual accounting cycle", n_results=3, include_memory=False)
    assert "context" in result
    assert "citations" in result
    assert "confidence" in result
    assert 0.0 <= result["hallucination_risk"] <= 1.0
    assert "question" in result


def test_rag_search():
    from rag.platform import RAGPlatform
    rag = RAGPlatform("knowledge")
    results = rag.search("invoice collection accounts receivable", n_results=5)
    assert isinstance(results, list)
    for r in results:
        assert "text" in r
        assert "score" in r
        assert r["score"] >= 0.0


def test_synthesis_engine():
    from synthesis.engine import SynthesisEngine
    eng = SynthesisEngine()
    report = eng.synthesize("invoice collection and accounts receivable billing", n_sources=3)
    assert report["id"]
    assert report["summary"]
    assert "citations" in report
    assert "confidence" in report
    assert "hallucination_risk" in report

    fetched = eng.get_report(report["id"])
    assert fetched is not None
    assert fetched["query"] == report["query"]


def test_synthesis_list_and_stats():
    from synthesis.engine import SynthesisEngine
    eng = SynthesisEngine()
    eng.synthesize("tax planning strategy annual", n_sources=3)
    reports = eng.list_reports()
    assert len(reports) >= 1
    s = eng.stats()
    assert s["total_reports"] >= 1
