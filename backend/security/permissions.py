"""Agent security model — runtime permission enforcement.

A permission matrix per agent over memory / tools / documents / execution /
approval / audit. The invariant across the whole platform: no agent may *approve*
or *execute* money/filing actions — execution caps at 'propose'; approval is human.
"""
from __future__ import annotations

MEM_NONE, MEM_READ, MEM_RW = "none", "read", "read-write"
EXEC_NONE, EXEC_PROPOSE = "none", "propose"  # 'approve'/'execute' are reserved for humans


class PermissionDenied(RuntimeError):
    pass


# agent -> capabilities. tools='all' or an explicit allowlist.
MATRIX: dict[str, dict] = {
    "chief_of_staff": {"memory": MEM_RW, "tools": "all", "documents": True, "execution": EXEC_PROPOSE, "approval": False, "audit": True},
    "accounting":     {"memory": MEM_READ, "tools": "all", "documents": True, "execution": EXEC_PROPOSE, "approval": False, "audit": True},
    "tax":            {"memory": MEM_READ, "tools": "all", "documents": True, "execution": EXEC_NONE, "approval": False, "audit": False},
    "fasb":           {"memory": MEM_READ, "tools": "all", "documents": True, "execution": EXEC_NONE, "approval": False, "audit": False},
    "sec":            {"memory": MEM_READ, "tools": "all", "documents": True, "execution": EXEC_NONE, "approval": False, "audit": False},
    "tax_research":   {"memory": MEM_READ, "tools": "all", "documents": True, "execution": EXEC_NONE, "approval": False, "audit": False},
    "document":       {"memory": MEM_READ, "tools": "all", "documents": True, "execution": EXEC_PROPOSE, "approval": False, "audit": True},
    "workpaper":      {"memory": MEM_READ, "tools": "all", "documents": True, "execution": EXEC_PROPOSE, "approval": False, "audit": True},
    "due_diligence":  {"memory": MEM_READ, "tools": "all", "documents": True, "execution": EXEC_NONE, "approval": False, "audit": True},
    "advisory":       {"memory": MEM_RW, "tools": "all", "documents": True, "execution": EXEC_PROPOSE, "approval": False, "audit": True},
    "quant":          {"memory": MEM_READ, "tools": "all", "documents": False, "execution": EXEC_NONE, "approval": False, "audit": False},
    "portfolio":      {"memory": MEM_READ, "tools": "all", "documents": False, "execution": EXEC_PROPOSE, "approval": False, "audit": True},
    "trading":        {"memory": MEM_READ, "tools": "all", "documents": False, "execution": EXEC_PROPOSE, "approval": False, "audit": True},
    "language_coach": {"memory": MEM_RW, "tools": "all", "documents": False, "execution": EXEC_NONE, "approval": False, "audit": False},
    "email":          {"memory": MEM_READ, "tools": "all", "documents": True, "execution": EXEC_PROPOSE, "approval": False, "audit": False},
    "calendar":       {"memory": MEM_READ, "tools": "all", "documents": False, "execution": EXEC_PROPOSE, "approval": False, "audit": False},
    "automation":     {"memory": MEM_READ, "tools": "all", "documents": False, "execution": EXEC_PROPOSE, "approval": False, "audit": False},
    "knowledge":      {"memory": MEM_RW, "tools": "all", "documents": True, "execution": EXEC_NONE, "approval": False, "audit": True},
    "research":       {"memory": MEM_READ, "tools": "all", "documents": False, "execution": EXEC_NONE, "approval": False, "audit": False},
}

_DEFAULT = {"memory": MEM_READ, "tools": [], "documents": False, "execution": EXEC_NONE, "approval": False, "audit": False}


def perms(agent: str) -> dict:
    return MATRIX.get(agent, _DEFAULT)


def can_access_memory(agent: str, mode: str = MEM_READ) -> bool:
    p = perms(agent)["memory"]
    if mode == MEM_READ:
        return p in (MEM_READ, MEM_RW)
    return p == MEM_RW


def can_use_tool(agent: str, tool: str) -> bool:
    t = perms(agent)["tools"]
    return t == "all" or tool in t


def can_access_documents(agent: str) -> bool:
    return bool(perms(agent)["documents"])


def can_propose(agent: str) -> bool:
    return perms(agent)["execution"] in (EXEC_PROPOSE,)


def can_approve(agent: str) -> bool:
    # Invariant: agents never approve — humans do.
    return False


def enforce(agent: str, capability: str, mode: str = MEM_READ) -> None:
    """Raise PermissionDenied if the agent lacks the capability."""
    ok = {
        "memory": lambda: can_access_memory(agent, mode),
        "documents": lambda: can_access_documents(agent),
        "propose": lambda: can_propose(agent),
        "approve": lambda: can_approve(agent),
    }.get(capability, lambda: False)()
    if not ok:
        raise PermissionDenied(f"agent '{agent}' is not permitted to '{capability}'")
