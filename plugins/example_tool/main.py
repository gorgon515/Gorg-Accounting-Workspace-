"""Example HELIOS plugin.

In production this module is loaded by the PluginLoader with the HELIOS plugin SDK
on the import path. It demonstrates the expected plugin structure: lifecycle hooks,
a tool registration method, and permission-gated host access via the PluginContext.
"""


class ExampleToolPlugin:
    name = "example-tool"

    def on_install(self):
        print(f"[{self.name}] installed")

    def on_enable(self):
        print(f"[{self.name}] enabled")

    def on_disable(self):
        print(f"[{self.name}] disabled")

    def on_uninstall(self):
        print(f"[{self.name}] uninstalled")

    def get_tools(self):
        return [
            {
                "name": "accounting_summary",
                "description": "Get current accounting summary",
                "handler": self.get_accounting_summary,
            }
        ]

    def get_accounting_summary(self, context):
        if context.has_permission("accounting:read"):
            return context.get_accounting_summary()
        return {"error": "permission denied"}


plugin = ExampleToolPlugin()
