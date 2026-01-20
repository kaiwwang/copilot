from typing import Optional
import json

from logging import Logger
from app.agent.agent import Agent
from app.api.external_clients import ExternalApiHub
from app.api.github_client import GitHubClient
from app.core.config import Settings
from app.tools.tool_registry import ToolRegistry
from app.tools.github_tools import GET_PULL_REQUEST_TOOL, LIST_PULL_REQUESTS_TOOL
from app.models.agent_output import AgentOutput


class CliApp:
    """
    CLI Application for interacting with the GitHub PR Analysis Agent.

    Features:
    - Natural language input for PR analysis
    - Multi-turn conversation with memory
    - Automatic tool execution and result integration
    """

    MAX_REASONING_STEPS = 5  # Prevent infinite loops in tool execution

    def __init__(self, settings: Settings, logger: Logger) -> None:
        self.settings = settings
        self.logger = logger
        self.api_hub = ExternalApiHub()
        self._register_github_client()
        self.tool_registry = ToolRegistry(api_hub=self.api_hub)
        self._register_builtin_tools()
        self.agent = Agent(
            api_hub=self.api_hub,
            tool_registry=self.tool_registry,
            settings=settings,
            logger=logger,
        )

    def _register_github_client(self) -> None:
        """Initialize and register the GitHub client."""
        github_client = GitHubClient(token=self.settings.github_token)
        self.api_hub.register_github_client(github_client)
        self.logger.info("GitHub 客户端已注册")

    def _register_builtin_tools(self) -> None:
        """Register built-in tools."""
        self.tool_registry.register(GET_PULL_REQUEST_TOOL)
        self.tool_registry.register(LIST_PULL_REQUESTS_TOOL)
        self.logger.info(f"已注册工具: {len(self.tool_registry._tools)} 个")

    def run(self) -> None:
        """
        Main CLI loop.

        Handles user input, agent reasoning, and tool execution.
        """
        self._print_welcome()

        while True:
            try:
                user_input: Optional[str] = input("\n你: ").strip()
            except (EOFError, KeyboardInterrupt):
                self.logger.info("\n收到退出信号，对话结束")
                break

            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit"}:
                self.logger.info("收到退出指令")
                break

            # Process user input through agent reasoning loop
            response = self._process_input(user_input)
            self._print_response(response)

    def _process_input(self, user_input: str) -> AgentOutput:
        """
        Process user input through the complete reasoning + tool execution loop.

        Args:
            user_input: The user's message

        Returns:
            Final AgentOutput
        """
        context = ""
        reasoning_steps = 0

        while reasoning_steps < self.MAX_REASONING_STEPS:
            reasoning_steps += 1

            # Call agent for reasoning
            agent_output = self.agent.handle(user_input)

            # Handle tool request
            if agent_output.intent == "tool_request" and agent_output.tool:
                tool_name = agent_output.tool.get("name")
                tool_params = agent_output.tool.get("params", {})

                self.logger.info(f"执行工具: {tool_name}")

                # Execute tool
                tool_result = self.tool_registry.maybe_execute_from_agent(
                    agent_output.to_dict()
                )

                if tool_result and tool_result.get("success"):
                    result_data = tool_result.get("result", {})
                    # Print tool result to user
                    print(f"\n[工具 {tool_name} 执行结果]")
                    if result_data.get("success"):
                        data = result_data.get("data", {})
                        print(f"标题: {data.get('title')}")
                        print(f"状态: {data.get('state')}")
                        print(f"作者: {data.get('author')}")
                        print(f"URL: {data.get('url')}")
                        if data.get('body'):
                            body = data.get('body')[:200]
                            print(f"描述: {body}...")
                    else:
                        print(f"错误: {result_data.get('error')}")

                    # Format tool result as context for next reasoning
                    context = f"""## 工具执行结果
工具名称: {tool_name}
执行参数: {json.dumps(tool_params, ensure_ascii=False)}
执行结果: {json.dumps(result_data, ensure_ascii=False, indent=2)}

请基于上述工具执行结果，回答用户的问题。如果信息已经足够给出答案，请设置 intent 为 "final"。"""
                    self.logger.info(f"工具执行成功: {tool_name}")
                else:
                    error_msg = tool_result.get("error", "Unknown error") if tool_result else "Tool execution failed"
                    self.logger.error(f"工具执行失败: {error_msg}")
                    return AgentOutput(
                        intent="continue",
                        message=f"工具执行失败: {error_msg}",
                        final=False,
                    )

                # Clear user input, use context as the new input for next reasoning
                user_input = context
                continue

            # Handle final or continue response
            if agent_output.intent == "final" or agent_output.final:
                return agent_output

            # For continue intent, return the message
            return agent_output

        # Max steps reached
        self.logger.warning("达到最大推理步数")
        return AgentOutput(
            intent="continue",
            message="推理步骤过多，请尝试简化您的问题",
            final=False,
        )

    def _print_welcome(self) -> None:
        """Print welcome message."""
        print("=" * 60)
        print("  GitHub PR 分析助手")
        print("=" * 60)
        print("\n我可以帮你：")
        print("  • 查看 Pull Request 详情")
        print("  • 分析 PR 的标题、描述、文件变更")
        print("  • 列出评论和审查意见")
        print("\n示例问题：")
        print("  • 查看 facebook/react 的 PR #25000")
        print("  • 分析 openai/chatgpt-retrieval-plugin 的 PR #1")
        print("\n输入 'exit' 或 'quit' 退出对话")
        print("-" * 60)

    def _print_response(self, response: AgentOutput) -> None:
        """Print agent response in a formatted way."""
        if response.intent == "final":
            print(f"\n[分析结果]")
            print(response.message)
        elif response.message:
            print(f"\nAgent: {response.message}")
        elif response.intent == "tool_request":
            print(f"\n[等待执行工具: {response.tool.get('name')}]")
