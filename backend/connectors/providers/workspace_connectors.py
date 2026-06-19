"""
Collaboration and workspace connectors.
Framework is complete; each requires credentials to activate.
"""
from __future__ import annotations
from connectors.base import BaseConnector, ConnectorMeta
from connectors.registry import register_provider


def _make_workspace_connector(cid: str, name: str, kind: str, desc: str,
                               auth: str = "oauth2", perms: list[str] | None = None):
    class _Connector(BaseConnector):
        meta = ConnectorMeta(
            id=cid, name=name, kind=kind, category="workspace",
            description=desc, auth_type=auth, requires_credential=True,
            permissions=perms or ["read"],
        )

        def _fetch(self, **kwargs) -> list[dict]:
            raise NotImplementedError(f"{name} requires credentials. Activate via Connector Center.")

        def _health(self):
            raise ConnectionError(f"{name} requires credentials.")

    _Connector.__name__ = f"{cid.replace('-', '_').title()}Connector"
    return _Connector


# First-party connectors — framework registered, require credentials
_WORKSPACE_DEFS = [
    ("google_workspace", "Google Workspace", "workspace", "Gmail, Drive, Calendar, Docs"),
    ("microsoft_365", "Microsoft 365", "workspace", "Outlook, Teams, OneDrive, SharePoint"),
    ("slack", "Slack", "messaging", "Channels, messages, files", "oauth2", ["read_messages"]),
    ("discord", "Discord", "messaging", "Servers, channels", "bot_token", ["read_messages"]),
    ("notion", "Notion", "knowledge", "Pages, databases", "api_key", ["read_pages"]),
    ("obsidian", "Obsidian", "knowledge", "Local vault sync", "none", ["read_files"]),
    ("github", "GitHub", "devtools", "Repos, issues, PRs", "oauth2", ["read_repos"]),
    ("gitlab", "GitLab", "devtools", "Repos, issues, pipelines", "oauth2", ["read_repos"]),
    ("jira", "Jira", "project_management", "Issues, sprints, boards", "api_key", ["read_issues"]),
    ("confluence", "Confluence", "knowledge", "Pages, spaces", "api_key", ["read_pages"]),
    ("dropbox", "Dropbox", "storage", "Files, shared folders", "oauth2", ["read_files"]),
    ("onedrive", "OneDrive", "storage", "Files, SharePoint libraries", "oauth2", ["read_files"]),
    ("n8n", "N8N Automation", "automation", "Workflows, executions", "api_key", ["read_workflows"]),
]

for _def in _WORKSPACE_DEFS:
    _cls = _make_workspace_connector(*_def)
    register_provider(_cls)
    # expose class so it can be imported
    globals()[_cls.__name__] = _cls
