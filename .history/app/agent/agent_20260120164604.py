"""
Agent Implementation with Gemini API Integration

推理循环：
1. 用户输入 → 构建完整 Prompt → Gemini API
2. 解析 JSON 输出
3. 判断 intent：
   - tool_request: 执行工具 → 将结果加入上下文 → 再次调用 LLM
   - final: 返回最终答案
   - continue: 返回中间消息
"""

import json
import logging
from typing import Any, Dict, List, Optional

import requests

from app.api.external_clients import ExternalApiHub
from app.models.agent_output import AgentOutput
from app.models.message import Message
from app.tools.tool_registry import ToolRegistry
from app.core.config import Settings


# ============== SYSTEM PROMPT ==============
SYSTEM_PROMPT = """你是 GitHub PR 分析助手，简洁高效地完成任务。

## 核心原则
1. **禁止操作代码库**：只能读取，不能修改
2. **自动执行**：用户说"分析"就自动获取所有相关信息
3. **输出 JSON**：每次推理返回 JSON

## 分析 PR 的标准流程
当用户要求分析 PR 时，自动执行以下工具：
1. `get_pull_request` - PR 基本信息
2. `get_pull_request_files` - 文件变更
3. （可选）`list_pull_request_comments` - 评论

## 可用工具
{tool_descriptions}

## 输出格式
```json
{{
  "intent": "tool_request | final",
  "message": "简短结论",
  "tool": {{"name": "工具名", "params": {{}}}}
}}
```

## 关键规则
- 用户同意后**立即执行**工具，不需要重复确认
- 不要说"我接下来会..."，直接做
- 不要反复问"您确定吗？"
- 提供最终分析时，设置 intent="final"
"""


# ============== GEMINI API CLIENT ==============
class GeminiClient:
    """Simple Gemini API client for text generation."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp") -> None:
        self.api_key = api_key
        self.model = model
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def generate(self, prompt: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Call Gemini API and return structured result.

        Returns:
            {
                "success": bool,
                "text": str,  # Raw response text
                "parsed": dict,  # Parsed JSON (if valid)
                "error": str,  # Error message if failed
            }
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "API key not configured",
            }

        # Build content
        contents = [{"parts": [{"text": prompt}]}]
        if context:
            contents[0]["parts"][0]["text"] = f"{context}\n\n---\n\n{prompt}"

        payload = {"contents": contents}

        try:
            response = requests.post(
                self.api_url,
                params={"key": self.api_key},
                json=payload,
                timeout=60,
            )
            response.raise_for_status()

            data = response.json()
            if "candidates" in data and len(data["candidates"]) > 0:
                text = data["candidates"][0]["content"]["parts"][0].get("text", "")
                # Try to parse JSON from response
                parsed = self._extract_json(text)
                return {
                    "success": True,
                    "text": text,
                    "parsed": parsed,
                }
            else:
                return {
                    "success": False,
                    "error": "No candidates in response",
                }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"JSON parse error: {str(e)}",
            }

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from response text."""
        text = text.strip()
        # Remove markdown code fences if present
        if text.startswith("```"):
            # Find the first newline
            first_newline = text.find("\n")
            if first_newline != -1:
                text = text[first_newline + 1 :]
            # Remove closing fence
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON in the text
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    pass
            return None


# ============== MAIN AGENT CLASS ==============
class Agent:
    """
    GitHub PR Analysis Agent with Gemini API integration.

    Reasoning loop:
    1. Build full prompt (system + context + user input)
    2. Call Gemini API
    3. Parse JSON output
    4. Check intent:
       - tool_request: execute tool → add result to context → repeat
       - final: return final answer
       - continue: return intermediate message
    """

    MAX_REASONING_STEPS = 5  # Prevent infinite loops

    def __init__(
        self,
        api_hub: ExternalApiHub,
        tool_registry: ToolRegistry | None = None,
        settings: Optional[Settings] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.api_hub = api_hub
        self.tool_registry = tool_registry
        self.settings = settings or Settings()
        self.logger = logger

        # Initialize Gemini client
        self.gemini = GeminiClient(
            api_key=self.settings.gemini_api_key,
            model=self.settings.gemini_model,
        )

        # Conversation history
        self.history: List[Message] = []

    def handle(self, user_input: str) -> AgentOutput:
        """
        Main entry point for agent reasoning.

        Args:
            user_input: The user's message

        Returns:
            AgentOutput with intent, message, tool info
        """
        # Add user message to history
        user_msg = Message(role="user", content=user_input)
        self.history.append(user_msg)

        # Truncate history if needed
        self._prune_history()

        # Start reasoning loop
        try:
            output = self._reasoning_loop()
            return output
        except Exception as e:
            self._log(f"Agent error: {str(e)}")
            return AgentOutput(
                intent="continue",
                message=f"抱歉，处理您的请求时出错: {str(e)}",
                final=False,
            )

    def _reasoning_loop(self, context: str = "") -> AgentOutput:
        """
        Single reasoning step with Gemini API.

        This method only makes ONE API call and returns the decision.
        Tool execution is handled by the caller (CLI).

        Args:
            context: Previous context (e.g., tool results)

        Returns:
            AgentOutput with intent, message, tool info
        """
        # Build prompt
        prompt = self._build_prompt(
            user_input=self.history[-1].content,
            context=context,
            tool_results=[],
        )

        # Call Gemini API
        self._log(f"Calling Gemini API...")
        result = self.gemini.generate(prompt)

        if not result["success"]:
            self._log(f"API error: {result['error']}")
            return AgentOutput(
                intent="continue",
                message=f"调用 API 失败: {result['error']}",
                final=False,
            )

        # Parse response
        parsed = result["parsed"]
        if not parsed:
            self._log(f"Failed to parse JSON: {result['text'][:200]}")
            return AgentOutput(
                intent="continue",
                message="无法解析模型返回，请重试",
                final=False,
            )

        self._log(f"Model intent: {parsed.get('intent')}")

        intent = parsed.get("intent", "continue")
        message = parsed.get("message", "")
        tool_info = parsed.get("tool")
        is_final = parsed.get("final", False)

        # Handle final or continue
        if is_final or intent == "final":
            return AgentOutput(
                intent="final",
                message=message,
                tool=tool_info,
                final=True,
            )

        # Return tool request or continue
        return AgentOutput(
            intent=intent,
            message=message,
            tool=tool_info,
            final=False,
        )

    def _build_prompt(
        self,
        user_input: str,
        context: str,
        tool_results: List[Dict[str, Any]],
    ) -> str:
        """
        Build the full prompt for Gemini API.

        Combines:
        - System prompt (with available tools)
        - Previous conversation history
        - Tool execution results (if any)
        - Current user input
        """
        # Build tool descriptions
        tool_descriptions = self._get_tool_descriptions()

        # Build conversation history
        history_text = self._format_history()

        # Build tool results
        results_text = ""
        if tool_results:
            results_text = "## 工具执行结果\n"
            for i, result in enumerate(tool_results, 1):
                results_text += f"\n### 工具 {i}: {result['tool']}\n"
                results_text += f"参数: {json.dumps(result['params'], ensure_ascii=False)}\n"
                results_text += f"结果: {json.dumps(result['result'], ensure_ascii=False, indent=2)}\n"

        # Full prompt
        prompt = f"""{SYSTEM_PROMPT.format(tool_descriptions=tool_descriptions)}

## 对话历史
{history_text}

{results_text}

## 当前用户输入
{user_input}

请分析上述信息，返回 JSON 格式的推理结果。
"""

        return prompt

    def _get_tool_descriptions(self) -> str:
        """Get descriptions of all available tools."""
        if not self.tool_registry:
            return "无工具可用"

        descriptions = []
        for name, tool in self.tool_registry._tools.items():
            desc = f"""- **名称**: {tool.name}
  **描述**: {tool.description}
  **参数**:
```json
{json.dumps(tool.parameters_schema, ensure_ascii=False, indent=2)}
```"""
            descriptions.append(desc)

        return "\n\n".join(descriptions)

    def _format_history(self) -> str:
        """Format conversation history for prompt."""
        if not self.history:
            return "（无历史记录）"

        lines = []
        for msg in self.history:
            role = {"user": "用户", "assistant": "助手"}.get(msg.role, msg.role)
            content = msg.content[:200]  # Truncate long messages
            lines.append(f"**{role}**: {content}")

        return "\n".join(lines)

    def _format_tool_result(self, tool_name: str, result: Dict[str, Any]) -> str:
        """Format tool result for context."""
        return f"""### 工具调用结果: {tool_name}
```json
{json.dumps(result, ensure_ascii=False, indent=2)}
```"""

    def _prune_history(self) -> None:
        """Truncate history to fit within limit."""
        if len(self.history) > self.settings.history_limit:
            self.history = self.history[-self.settings.history_limit :]

    def _log(self, message: str) -> None:
        """Log message if logger is available."""
        if self.logger:
            self.logger.info(f"[Agent] {message}")
        else:
            print(f"[Agent] {message}")
