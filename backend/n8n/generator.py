"""AI workflow generator — emits valid, importable N8N workflow JSON.

Produces real N8N node graphs (not pseudo-code) for common intents. The flagship
example builds a monthly/daily accounting-briefing workflow:
Schedule Trigger → HTTP Request (HELIOS sidecar briefing) → Code (format) →
Email Send. Output imports directly into N8N.
"""
from __future__ import annotations

import uuid
from typing import Optional


def _node(name: str, ntype: str, parameters: dict, position: list[int], type_version: float = 1) -> dict:
    return {
        "parameters": parameters,
        "id": str(uuid.uuid4()),
        "name": name,
        "type": ntype,
        "typeVersion": type_version,
        "position": position,
    }


def _linear_connections(node_names: list[str]) -> dict:
    """Wire nodes in a straight pipeline a → b → c."""
    conns: dict = {}
    for i in range(len(node_names) - 1):
        conns[node_names[i]] = {"main": [[{"node": node_names[i + 1], "type": "main", "index": 0}]]}
    return conns


def build_workflow(name: str, nodes: list[dict]) -> dict:
    return {
        "name": name,
        "nodes": nodes,
        "connections": _linear_connections([n["name"] for n in nodes]),
        "settings": {"executionOrder": "v1"},
        "active": False,
        "tags": ["helios"],
    }


def schedule_trigger(cron: str = "0 7 * * *", name: str = "Schedule") -> dict:
    return _node(name, "n8n-nodes-base.scheduleTrigger",
                 {"rule": {"interval": [{"field": "cronExpression", "expression": cron}]}},
                 [240, 300], type_version=1.1)


def http_get(url: str, name: str = "HTTP Request") -> dict:
    return _node(name, "n8n-nodes-base.httpRequest",
                 {"url": url, "method": "GET", "options": {}}, [460, 300], type_version=4.1)


def code_node(js: str, name: str = "Format") -> dict:
    return _node(name, "n8n-nodes-base.code", {"jsCode": js}, [680, 300], type_version=2)


def email_send(to: str, subject: str, name: str = "Send Email") -> dict:
    return _node(name, "n8n-nodes-base.emailSend",
                 {"toEmail": to, "subject": subject, "text": "={{ $json.body }}", "options": {}},
                 [900, 300], type_version=2)


def accounting_briefing_workflow(*, sidecar_url: str = "http://127.0.0.1:8420",
                                 email_to: str = "you@example.com",
                                 cron: str = "0 7 * * *") -> dict:
    """Daily accounting-briefing workflow:
    Schedule → fetch HELIOS briefing → format → email."""
    fmt_js = (
        "const b = $json;\n"
        "const lines = [b.executive_summary, '', 'Key changes:'];\n"
        "for (const k of (b.key_changes||[])) lines.push(`- ${k.title} (${k.source})`);\n"
        "lines.push('', 'Action items:');\n"
        "for (const a of (b.action_items||[])) lines.push(`- ${a}`);\n"
        "return [{ json: { body: lines.join('\\n') } }];"
    )
    nodes = [
        schedule_trigger(cron),
        http_get(f"{sidecar_url}/accounting/briefing", name="HELIOS Briefing"),
        code_node(fmt_js, name="Format Briefing"),
        email_send(email_to, "HELIOS Daily Accounting Briefing", name="Email Briefing"),
    ]
    return build_workflow("HELIOS — Daily Accounting Briefing", nodes)


# Map a high-level intent to a workflow: collect → process → report → distribute.
def from_spec(spec: dict) -> dict:
    """spec: {name, schedule(cron), collect_url, email_to, transform_js?}"""
    name = spec.get("name", "HELIOS Workflow")
    nodes = [schedule_trigger(spec.get("schedule", "0 7 * * *"))]
    if spec.get("collect_url"):
        nodes.append(http_get(spec["collect_url"], name="Collect"))
    nodes.append(code_node(spec.get("transform_js", "return items;"), name="Process"))
    if spec.get("email_to"):
        nodes.append(email_send(spec["email_to"], spec.get("subject", name), name="Distribute"))
    return build_workflow(name, nodes)
