"""FASB knowledge graph.

Connects ASC topics ↔ ASUs ↔ industries ↔ financial-statement areas ↔
disclosures ↔ audit implications ↔ tax implications into a typed node/edge graph
with a visualizable export. Seeded from the ASC knowledge base and extensible
with live ASUs from collected intel items.
"""
from __future__ import annotations

from typing import Optional

from app.services.accounting_research import ASC_TOPICS

# Per-ASC relationships used to build the graph edges.
_SEED: dict[str, dict] = {
    "606": {
        "fs_area": ["Revenue", "Contract assets & liabilities"],
        "industries": ["Software & technology", "Real estate"],
        "disclosures": ["Disaggregation of revenue", "Remaining performance obligations", "Significant judgments"],
        "audit": ["Revenue recognition risk", "Cutoff testing"],
        "tax": ["Book-tax timing differences"],
        "exam": "FAR",
    },
    "842": {
        "fs_area": ["Right-of-use assets", "Lease liabilities"],
        "industries": ["Real estate", "Energy & utilities"],
        "disclosures": ["Lease cost components", "Maturity analysis", "Discount rate & term"],
        "audit": ["Completeness of lease population", "Discount-rate reasonableness"],
        "tax": ["Lease classification differences"],
        "exam": "FAR",
    },
    "326": {
        "fs_area": ["Allowance for credit losses"],
        "industries": ["Financial institutions", "Insurance"],
        "disclosures": ["Credit-quality indicators", "Allowance roll-forward", "Methodology"],
        "audit": ["Estimate of expected losses", "Model & assumption testing"],
        "tax": ["Bad-debt timing differences"],
        "exam": "FAR/AUD",
    },
    "350": {
        "fs_area": ["Goodwill", "Intangible assets"],
        "industries": ["Software & technology", "Healthcare"],
        "disclosures": ["Goodwill by reporting unit", "Impairment events"],
        "audit": ["Impairment testing", "Fair-value estimates"],
        "tax": ["Goodwill amortization differences"],
        "exam": "FAR",
    },
    "718": {
        "fs_area": ["Compensation expense", "Additional paid-in capital"],
        "industries": ["Software & technology"],
        "disclosures": ["Award terms", "Valuation assumptions", "Unrecognized cost"],
        "audit": ["Grant-date fair value", "Forfeiture estimates"],
        "tax": ["Excess tax benefits/deficiencies"],
        "exam": "FAR/REG",
    },
}

_REL = {
    "fs_area": "affects", "industries": "impacts", "disclosures": "requires",
    "audit": "audit_implication", "tax": "tax_implication", "exam": "tested_on",
}


def _nid(kind: str, label: str) -> str:
    return f"{kind}:{label}"


def build_graph(items: Optional[list[dict]] = None) -> dict:
    """Return {nodes, edges}. Optionally attach live ASUs (from intel items)."""
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def add_node(kind: str, label: str) -> str:
        nid = _nid(kind, label)
        nodes.setdefault(nid, {"id": nid, "kind": kind, "label": label})
        return nid

    def add_edge(src: str, dst: str, rel: str) -> None:
        edges.append({"source": src, "target": dst, "rel": rel})

    for code, rels in _SEED.items():
        topic = ASC_TOPICS.get(code)
        label = f"ASC {code}" + (f" — {topic['title']}" if topic else "")
        asc_id = add_node("asc", label)
        for field, names in rels.items():
            if field == "exam":
                add_edge(asc_id, add_node("exam", names), _REL["exam"])
                continue
            for name in names:
                add_edge(asc_id, add_node(field if field != "fs_area" else "fs_area", name), _REL[field])

    # Attach live ASUs: ASU node → the ASC topics it touches.
    for it in items or []:
        if it.get("asu_number"):
            asu_id = add_node("asu", f"ASU {it['asu_number']}")
            for code in it.get("asc_codes", []):
                target = next((n for n in nodes if n.startswith("asc:") and f"ASC {code}" in nodes[n]["label"]), None)
                if target:
                    add_edge(asu_id, target, "amends")

    return {"nodes": list(nodes.values()), "edges": edges}


def neighbors(node_id: str, items: Optional[list[dict]] = None) -> dict:
    g = build_graph(items)
    related = [e for e in g["edges"] if e["source"] == node_id or e["target"] == node_id]
    ids = {node_id} | {e["source"] for e in related} | {e["target"] for e in related}
    return {"nodes": [n for n in g["nodes"] if n["id"] in ids], "edges": related}


def subgraph_for_asc(code: str, items: Optional[list[dict]] = None) -> dict:
    g = build_graph(items)
    asc_node = next((n["id"] for n in g["nodes"] if n["kind"] == "asc" and f"ASC {code}" in n["label"]), None)
    return neighbors(asc_node, items) if asc_node else {"nodes": [], "edges": []}
