"""
GitHub API Client

Provides a unified interface for GitHub API calls.
All methods return structured dictionaries with consistent error handling.
"""

import os
import requests
from typing import Any, Dict, List, Optional


class GitHubClient:
    """
    Read-only GitHub API client.
    Token is read from environment variable GITHUB_TOKEN.
    """

    def __init__(self, token: Optional[str] = None) -> None:
        self.token = token or os.getenv("GITHUB_TOKEN", "")
        self.base_url = os.getenv("GITHUB_API_BASE", "https://api.github.com")
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AI-Agent-GitHub-Client",
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make an HTTP request to GitHub API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., "/repos/owner/repo/pulls/1")
            **kwargs: Additional arguments for requests.request

        Returns:
            Dict with keys: "success" (bool), "data" (Any), "error" (str, optional)
        """
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return {
                "success": True,
                "data": response.json(),
                "status_code": response.status_code,
            }
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Error {response.status_code}: {response.text}"
            return {
                "success": False,
                "error": error_msg,
                "status_code": response.status_code,
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Request Error: {str(e)}",
                "status_code": None,
            }

    def get_pull_request(
        self, owner: str, repo: str, pull_number: int
    ) -> Dict[str, Any]:
        """
        Get a specific pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pull_number: Pull request number

        Returns:
            Dict with pull request details
        """
        endpoint = f"/repos/{owner}/{repo}/pulls/{pull_number}"
        return self._request("GET", endpoint)

    def list_pull_request_commits(
        self, owner: str, repo: str, pull_number: int
    ) -> Dict[str, Any]:
        """
        List commits in a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pull_number: Pull request number

        Returns:
            Dict with list of commits
        """
        endpoint = f"/repos/{owner}/{repo}/pulls/{pull_number}/commits"
        return self._request("GET", endpoint)

    def get_pull_request_diff(
        self, owner: str, repo: str, pull_number: int
    ) -> Dict[str, Any]:
        """
        Get the diff of a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pull_number: Pull request number

        Returns:
            Dict with diff content
        """
        endpoint = f"/repos/{owner}/{repo}/pulls/{pull_number}"
        headers = {"Accept": "application/vnd.github.v3.diff"}
        return self._request("GET", endpoint, headers=headers)

    def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get the content of a file from the repository.

        Args:
            owner: Repository owner
            repo: Repository name
            path: File path in the repository
            ref: Git reference (branch, tag, or commit SHA)

        Returns:
            Dict with file content
        """
        endpoint = f"/repos/{owner}/{repo}/contents/{path}"
        params = {}
        if ref:
            params["ref"] = ref
        return self._request("GET", endpoint, params=params)

    def list_pull_request_comments(
        self, owner: str, repo: str, pull_number: int
    ) -> Dict[str, Any]:
        """
        List review comments on a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pull_number: Pull request number

        Returns:
            Dict with list of comments
        """
        endpoint = f"/repos/{owner}/{repo}/pulls/{pull_number}/comments"
        return self._request("GET", endpoint)

    def list_pull_request_reviews(
        self, owner: str, repo: str, pull_number: int
    ) -> Dict[str, Any]:
        """
        List reviews for a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pull_number: Pull request number

        Returns:
            Dict with list of reviews
        """
        endpoint = f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews"
        return self._request("GET", endpoint)

    def list_pull_requests(
        self, owner: str, repo: str, state: str = "open"
    ) -> Dict[str, Any]:
        """
        List pull requests for a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            state: PR state (open, closed, all)

        Returns:
            Dict with list of pull requests
        """
        endpoint = f"/repos/{owner}/{repo}/pulls"
        params = {"state": state}
        return self._request("GET", endpoint, params=params)

    def get_pull_request_files(
        self, owner: str, repo: str, pull_number: int
    ) -> Dict[str, Any]:
        """
        List changed files in a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pull_number: Pull request number

        Returns:
            Dict with list of changed files
        """
        endpoint = f"/repos/{owner}/{repo}/pulls/{pull_number}/files"
        return self._request("GET", endpoint)
