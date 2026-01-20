from typing import Any, Dict

from app.api.github_client import GitHubClient


class ExternalApiHub:
    """
    Single entry point for all external platform APIs (GitHub/Jira/etc).
    Replace stub methods with real authenticated calls when wiring APIs.
    """

    def __init__(self) -> None:
        self.clients: Dict[str, Any] = {}

    def register(self, name: str, client: Any) -> None:
        self.clients[name] = client

    def call(self, name: str, *args: Any, **kwargs: Any) -> Any:
        if name not in self.clients:
            raise ValueError(f"client '{name}' is not registered")
        # TODO: add common error handling, retries, and logging
        return self.clients[name](*args, **kwargs)

    def register_github_client(self, github_client: GitHubClient) -> None:
        """Register GitHub client for external API access."""
        self.register("github", github_client)