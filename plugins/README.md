# HELIOS Plugins

HELIOS plugins extend the platform with new tools, data sources, and UI views. Every
plugin ships a `plugin.json` manifest and a Python entry point that subclasses one of
the SDK base classes.

## Manifest format (`plugin.json`)

```json
{
  "name": "example-tool",
  "version": "1.0.0",
  "description": "What the plugin does.",
  "author": "Your Name",
  "entry_point": "main.py",
  "permissions": ["accounting:read", "memory:read"],
  "min_helios_version": "0.8.0",
  "tags": ["example"],
  "license": "MIT"
}
```

Required fields: `name`, `version` (semver `X.Y.Z`), `description`, `author`,
`entry_point`, `permissions`.

## Available permissions

| Permission | Grants |
|---|---|
| `accounting:read` / `accounting:write` | Read/modify accounting data |
| `vault:read` | Read secrets from the vault |
| `memory:read` / `memory:write` | Read/write long-term memory |
| `reports:read` | Read generated reports |
| `network:outbound` | Make outbound network calls |
| `filesystem:read` / `filesystem:write` | Read/write the plugin sandbox dir |
| `sidecar:call` | Call the HELIOS sidecar API |
| `ui:render` | Contribute a UI view |

Plugins only receive the permissions declared in their manifest, and the sandbox
blocks (and audits) any call that requests a permission that was not granted.

## SDK usage

```python
from plugins.sdk import ToolPlugin

class MyPlugin(ToolPlugin):
    def on_enable(self):
        print("enabled")

    def get_tools(self):
        return [{"name": "summary", "description": "...", "handler": self.summary}]

    def summary(self, context):
        if context.has_permission("accounting:read"):
            return context.get_accounting_summary()
        return {"error": "permission denied"}

plugin = MyPlugin()
```

Base classes: `HeliosPlugin` (lifecycle hooks), `ToolPlugin` (commands),
`DataPlugin` (data sources), `UIPlugin` (views).

## Lifecycle

`install` → `enable` → `disable` → `uninstall`. Each transition is recorded in the
plugin audit log. Install/enable a plugin through the API:

```
POST /plugins/install            # body: the manifest object
POST /plugins/{plugin_id}/enable
POST /plugins/{plugin_id}/disable
DELETE /plugins/{plugin_id}
```

See `example_tool/` for a complete working example.
