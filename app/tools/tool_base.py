from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Protocol


class ToolHandler(Protocol):
    """
    Handler protocol for tools. Must return a structured dict result.
    Can optionally accept api_hub for accessing external APIs.
    """

    def __call__(self, params: Dict[str, Any], api_hub: Optional[Any] = None) -> Dict[str, Any]:
        ...


class ToolExecutionError(Exception):
    """Raised when a tool fails to execute."""


@dataclass
class ToolDefinition:
    """
    Base definition for a tool.
    - name: unique identifier used by the agent to request the tool
    - description: human-readable purpose
    - parameters_schema: JSON-schema-like dict to validate inputs (lightweight)
    - handler: callable that executes the tool and returns a structured dict
    """

    name: str
    description: str
    parameters_schema: Dict[str, Any]
    handler: ToolHandler

    def run(self, params: Dict[str, Any], api_hub: Optional[Any] = None) -> Dict[str, Any]:
        return self.handler(params, api_hub)

