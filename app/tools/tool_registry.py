from typing import Any, Dict, List, Optional

from app.tools.tool_base import ToolDefinition, ToolExecutionError


class ToolRegistry:
    """
    Registry to manage tool definitions and execute them by name.
    """

    def __init__(self, api_hub: Optional[Any] = None) -> None:
        self._tools: Dict[str, ToolDefinition] = {}
        self.api_hub = api_hub  # External API hub for tool access

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' 已存在")
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' 未注册")
        return self._tools[name]

    def list_tools(self) -> List[ToolDefinition]:
        return list(self._tools.values())

    def execute(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        tool = self.get(name)
        try:
            result = tool.run(params, self.api_hub)
            return {
                "tool": name,
                "success": True,
                "result": result,
                "error": None,
            }
        except ToolExecutionError as exc:
            return {
                "tool": name,
                "success": False,
                "result": None,
                "error": str(exc),
            }
        except Exception as exc:
            # Wrap unexpected errors to keep a stable structure.
            return {
                "tool": name,
                "success": False,
                "result": None,
                "error": f"Unexpected error: {exc}",
            }

    def maybe_execute_from_agent(
        self, agent_output: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        If agent output requests a tool, execute it and return the response dict.
        Expected format:
        {
            "intent": "tool_request",
            "tool": {"name": "...", "params": {...}}
        }
        """
        if agent_output.get("intent") != "tool_request":
            return None
        tool_info = agent_output.get("tool") or {}
        name = tool_info.get("name")
        params = tool_info.get("params") or {}
        if not name:
            raise ValueError("agent_output.tool.name 缺失")
        return self.execute(name=name, params=params)

