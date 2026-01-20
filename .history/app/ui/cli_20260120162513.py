from typing import Optional

from logging import Logger
from app.agent.agent import Agent
from app.api.external_clients import ExternalApiHub
from app.api.github_client import GitHubClient
from app.core.config import Settings
from app.tools.tool_registry import ToolRegistry
from app.tools.github_tools import GET_PULL_REQUEST_TOOL
from app.models.agent_output import AgentOutput


class CliApp:
    """
    Simple REPL-style CLI for interacting with the agent.
    """

    def __init__(self, settings: Settings, logger: Logger) -> None:
        self.settings = settings
        self.logger = logger
        self.api_hub = ExternalApiHub()
        self._register_github_client()
        self.tool_registry = ToolRegistry(api_hub=self.api_hub)
        self._register_builtin_tools()
        self.agent = Agent(api_hub=self.api_hub, tool_registry=self.tool_registry)

    def _register_github_client(self) -> None:
        """Initialize and register the GitHub client."""
        github_client = GitHubClient(token=self.settings.github_token)
        self.api_hub.register_github_client(github_client)
        self.logger.info("GitHub 客户端已注册")

    def run(self) -> None:
        self.logger.info(f"启动 {self.settings.app_name} (输入 'exit' 退出)")
        while True:
            try:
                user_input: Optional[str] = input("你: ").strip()
            except (EOFError, KeyboardInterrupt):
                self.logger.info("退出对话")
                break

            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit"}:
                self.logger.info("收到退出指令")
                break

            agent_output = self.agent.handle(user_input)
            self._handle_agent_output(agent_output)

    def _register_builtin_tools(self) -> None:
        # Register demo tools here. Extend with real implementations later.
        self.tool_registry.register(GET_PULL_REQUEST_TOOL)

    def _handle_agent_output(self, agent_output: AgentOutput) -> None:
        # agent_output is AgentOutput instance
        data = agent_output.to_dict()
        if agent_output.intent == "tool_request":
            tool_resp = self.tool_registry.maybe_execute_from_agent(data)
            print(f"[tool_result] {tool_resp}")
            return

        if agent_output.intent == "final":
            print(f"[final] {agent_output.message}")
            return

        # default continue/chat
        print(f"Agent: {agent_output.message}")

