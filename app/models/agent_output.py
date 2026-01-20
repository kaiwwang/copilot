import json
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class AgentOutput:
    """
    Structured output from the Agent to the main program.
    intent: "tool_request" | "continue" | "final"
    - tool_request: expect tool {"name": str, "params": dict}
    - continue: intermediate assistant message
    - final: final answer to present to user
    """

    intent: str
    message: Optional[str] = None
    tool: Optional[Dict[str, Any]] = None
    final: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent,
            "message": self.message,
            "tool": self.tool,
            "final": self.final,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AgentOutput":
        return AgentOutput(
            intent=data.get("intent", ""),
            message=data.get("message"),
            tool=data.get("tool"),
            final=bool(data.get("final", False)),
        )

    @staticmethod
    def from_json(payload: str) -> "AgentOutput":
        return AgentOutput.from_dict(json.loads(payload))

