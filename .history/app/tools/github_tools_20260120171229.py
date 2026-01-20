from typing import Any, Dict, Optional

from app.tools.tool_base import ToolDefinition


def real_get_pull_request(
    params: Dict[str, Any],
    api_hub: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Real tool: fetch pull request details using GitHub API.
    Requires GitHub token to be set in GITHUB_TOKEN environment variable.
    """
    repo_full = params.get("repo")
    number = params.get("number")

    if not repo_full or "/" not in repo_full:
        return {
            "success": False,
            "error": "Invalid repo format. Expected 'owner/repo'",
        }

    owner, repo = repo_full.split("/", 1)

    # Get GitHub client from external API hub
    if not api_hub:
        return {
            "success": False,
            "error": "API hub not available",
        }

    github_client = api_hub.clients.get("github")

    if not github_client:
        return {
            "success": False,
            "error": "GitHub client not initialized",
        }

    result = github_client.get_pull_request(owner, repo, number)

    if result["success"]:
        data = result["data"]
        return {
            "success": True,
            "data": {
                "id": data.get("id"),
                "number": data.get("number"),
                "title": data.get("title"),
                "state": data.get("state"),
                "author": data.get("user", {}).get("login"),
                "url": data.get("html_url"),
                "body": data.get("body"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "head": {
                    "ref": data.get("head", {}).get("ref"),
                    "sha": data.get("head", {}).get("sha"),
                },
                "base": {
                    "ref": data.get("base", {}).get("ref"),
                    "sha": data.get("base", {}).get("sha"),
                },
            },
        }
    else:
        return {
            "success": False,
            "error": result.get("error", "Unknown error"),
        }


def real_list_pull_requests(
    params: Dict[str, Any],
    api_hub: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Real tool: list pull requests for a repository.
    Returns a list of PRs sorted by creation date (newest first).
    """
    repo_full = params.get("repo")
    state = params.get("state", "open")  # open, closed, all

    if not repo_full or "/" not in repo_full:
        return {
            "success": False,
            "error": "Invalid repo format. Expected 'owner/repo'",
        }

    owner, repo = repo_full.split("/", 1)

    # Get GitHub client from external API hub
    if not api_hub:
        return {
            "success": False,
            "error": "API hub not available",
        }

    github_client = api_hub.clients.get("github")

    if not github_client:
        return {
            "success": False,
            "error": "GitHub client not initialized",
        }

    result = github_client.list_pull_requests(owner, repo, state)

    if result["success"]:
        data = result["data"]
        # Return simplified list
        pr_list = []
        for pr in data[:10]:  # Limit to 10 most recent
            pr_list.append({
                "number": pr.get("number"),
                "title": pr.get("title"),
                "state": pr.get("state"),
                "author": pr.get("user", {}).get("login"),
                "url": pr.get("html_url"),
                "created_at": pr.get("created_at"),
            })
        return {
            "success": True,
            "data": pr_list,
            "total": len(data),
        }
    else:
        return {
            "success": False,
            "error": result.get("error", "Unknown error"),
        }


GET_PULL_REQUEST_TOOL = ToolDefinition(
    name="get_pull_request",
    description="获取指定 PR 的详细信息（需要 repo 和 number）",
    parameters_schema={
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "仓库名，格式 'owner/repo'"},
            "number": {"type": "integer", "description": "PR 编号"},
        },
        "required": ["repo", "number"],
    },
    handler=real_get_pull_request,
)


LIST_PULL_REQUESTS_TOOL = ToolDefinition(
    name="list_pull_requests",
    description="列出仓库的 PR 列表（默认返回最新的 10 个 open PR）",
    parameters_schema={
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "仓库名，格式 'owner/repo'"},
            "state": {"type": "string", "description": "PR 状态: open/closed/all", "enum": ["open", "closed", "all"]},
        },
        "required": ["repo"],
    },
    handler=real_list_pull_requests,
)


def real_get_pull_request_files(
    params: Dict[str, Any],
    api_hub: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Real tool: get list of changed files in a PR.
    """
    repo_full = params.get("repo")
    number = params.get("number")

    if not repo_full or "/" not in repo_full:
        return {
            "success": False,
            "error": "Invalid repo format. Expected 'owner/repo'",
        }

    owner, repo = repo_full.split("/", 1)

    if not api_hub:
        return {"success": False, "error": "API hub not available"}

    github_client = api_hub.clients.get("github")
    if not github_client:
        return {"success": False, "error": "GitHub client not initialized"}

    result = github_client.get_pull_request_files(owner, repo, number)

    if result["success"]:
        files = result["data"]
        file_list = []
        for f in files:
            file_list.append({
                "filename": f.get("filename"),
                "status": f.get("status"),
                "additions": f.get("additions"),
                "deletions": f.get("deletions"),
                "changes": f.get("changes"),
                "patch": f.get("patch", "")[:500] if f.get("patch") else "",  # Truncate long patches
            })
        return {"success": True, "data": file_list, "total": len(files)}
    else:
        return {"success": False, "error": result.get("error", "Unknown error")}


GET_PULL_REQUEST_FILES_TOOL = ToolDefinition(
    name="get_pull_request_files",
    description="获取 PR 的文件变更列表（每个文件的增删改行数）",
    parameters_schema={
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "仓库名，格式 'owner/repo'"},
            "number": {"type": "integer", "description": "PR 编号"},
        },
        "required": ["repo", "number"],
    },
    handler=real_get_pull_request_files,
)


# ========== Issues ==========
def real_list_issues(
    params: Dict[str, Any],
    api_hub: Optional[Any] = None,
) -> Dict[str, Any]:
    """List issues for a repository."""
    repo_full = params.get("repo")
    state = params.get("state", "open")

    if not repo_full or "/" not in repo_full:
        return {"success": False, "error": "Invalid repo format"}

    owner, repo = repo_full.split("/", 1)

    if not api_hub:
        return {"success": False, "error": "API hub not available"}

    github_client = api_hub.clients.get("github")
    if not github_client:
        return {"success": False, "error": "GitHub client not initialized"}

    endpoint = f"/repos/{owner}/{repo}/issues"
    result = github_client._request("GET", endpoint, params={"state": state})

    if result["success"]:
        issues = []
        for issue in result["data"][:10]:
            issues.append({
                "number": issue.get("number"),
                "title": issue.get("title"),
                "state": issue.get("state"),
                "author": issue.get("user", {}).get("login"),
                "created_at": issue.get("created_at"),
                "comments": issue.get("comments"),
            })
        return {"success": True, "data": issues, "total": len(result["data"])}
    else:
        return {"success": False, "error": result.get("error")}


def real_get_issue(
    params: Dict[str, Any],
    api_hub: Optional[Any] = None,
) -> Dict[str, Any]:
    """Get a specific issue."""
    repo_full = params.get("repo")
    number = params.get("number")

    if not repo_full or "/" not in repo_full:
        return {"success": False, "error": "Invalid repo format"}

    owner, repo = repo_full.split("/", 1)

    if not api_hub:
        return {"success": False, "error": "API hub not available"}

    github_client = api_hub.clients.get("github")
    if not github_client:
        return {"success": False, "error": "GitHub client not initialized"}

    endpoint = f"/repos/{owner}/{repo}/issues/{number}"
    result = github_client._request("GET", endpoint)

    if result["success"]:
        issue = result["data"]
        return {
            "success": True,
            "data": {
                "number": issue.get("number"),
                "title": issue.get("title"),
                "state": issue.get("state"),
                "author": issue.get("user", {}).get("login"),
                "body": issue.get("body"),
                "created_at": issue.get("created_at"),
                "comments": issue.get("comments"),
                "labels": [l.get("name") for l in issue.get("labels", [])],
            },
        }
    else:
        return {"success": False, "error": result.get("error")}


# ========== Commits ==========
def real_list_commits(
    params: Dict[str, Any],
    api_hub: Optional[Any] = None,
) -> Dict[str, Any]:
    """List commits for a repository or branch."""
    repo_full = params.get("repo")
    branch = params.get("branch")

    if not repo_full or "/" not in repo_full:
        return {"success": False, "error": "Invalid repo format"}

    owner, repo = repo_full.split("/", 1)

    if not api_hub:
        return {"success": False, "error": "API hub not available"}

    github_client = api_hub.clients.get("github")
    if not github_client:
        return {"success": False, "error": "GitHub client not initialized"}

    endpoint = f"/repos/{owner}/{repo}/commits"
    params = {}
    if branch:
        params["sha"] = branch

    result = github_client._request("GET", endpoint, params=params)

    if result["success"]:
        commits = []
        for c in result["data"][:10]:
            commits.append({
                "sha": c.get("sha")[:7],
                "message": c.get("commit", {}).get("message", "").split("\n")[0],
                "author": c.get("commit", {}).get("author", {}).get("name"),
                "date": c.get("commit", {}).get("author", {}).get("date"),
            })
        return {"success": True, "data": commits, "total": len(result["data"])}
    else:
        return {"success": False, "error": result.get("error")}


# ========== File Content ==========
def real_get_file_content(
    params: Dict[str, Any],
    api_hub: Optional[Any] = None,
) -> Dict[str, Any]:
    """Get file content from repository."""
    repo_full = params.get("repo")
    path = params.get("path")
    ref = params.get("ref")

    if not repo_full or "/" not in repo_full:
        return {"success": False, "error": "Invalid repo format"}

    owner, repo = repo_full.split("/", 1)

    if not api_hub:
        return {"success": False, "error": "API hub not available"}

    github_client = api_hub.clients.get("github")
    if not github_client:
        return {"success": False, "error": "GitHub client not initialized"}

    result = github_client.get_file_content(owner, repo, path, ref)

    if result["success"]:
        content = result["data"]
        return {
            "success": True,
            "data": {
                "name": content.get("name"),
                "path": content.get("path"),
                "size": content.get("size"),
                "type": content.get("type"),
                "content": content.get("content", "")[:5000],  # Limit content size
                "encoding": content.get("encoding"),
            },
        }
    else:
        return {"success": False, "error": result.get("error")}


LIST_ISSUES_TOOL = ToolDefinition(
    name="list_issues",
    description="列出仓库的 Issues（默认返回最新的 10 个）",
    parameters_schema={
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "仓库名，格式 'owner/repo'"},
            "state": {"type": "string", "description": "状态: open/closed/all"},
        },
        "required": ["repo"],
    },
    handler=real_list_issues,
)

GET_ISSUE_TOOL = ToolDefinition(
    name="get_issue",
    description="获取指定 Issue 的详细信息",
    parameters_schema={
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "仓库名"},
            "number": {"type": "integer", "description": "Issue 编号"},
        },
        "required": ["repo", "number"],
    },
    handler=real_get_issue,
)

LIST_COMMITS_TOOL = ToolDefinition(
    name="list_commits",
    description="列出仓库的最近提交（可指定分支）",
    parameters_schema={
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "仓库名"},
            "branch": {"type": "string", "description": "分支名（可选）"},
        },
        "required": ["repo"],
    },
    handler=real_list_commits,
)

GET_FILE_CONTENT_TOOL = ToolDefinition(
    name="get_file_content",
    description="获取文件的原始内容（可用于查看代码、配置文件等）",
    parameters_schema={
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "仓库名"},
            "path": {"type": "string", "description": "文件路径，如 'src/App.tsx'"},
            "ref": {"type": "string", "description": "分支或标签（可选）"},
        },
        "required": ["repo", "path"],
    },
    handler=real_get_file_content,
)


# ========== Repo Info ==========
def real_get_repo_info(
    params: Dict[str, Any],
    api_hub: Optional[Any] = None,
) -> Dict[str, Any]:
    """获取仓库的基本信息，包括 description、topics、README 等"""
    repo_full = params.get("repo")

    if not repo_full or "/" not in repo_full:
        return {"success": False, "error": "Invalid repo format"}

    owner, repo = repo_full.split("/", 1)

    if not api_hub:
        return {"success": False, "error": "API hub not available"}

    github_client = api_hub.clients.get("github")
    if not github_client:
        return {"success": False, "error": "GitHub client not initialized"}

    # 获取仓库基本信息
    result = github_client._request("GET", f"/repos/{owner}/{repo}")

    if not result["success"]:
        return {"success": False, "error": result.get("error")}

    data = result["data"]

    # 尝试获取 README 内容
    readme_content = ""
    readme_result = github_client.get_file_content(owner, repo, "README.md")
    if readme_result["success"]:
        readme_content = readme_result["data"].get("content", "")[:3000]
    else:
        # 尝试其他可能的 README 名称
        for name in ["README.md", "README.rst", "README.txt", "readme.md", "README"]:
            readme_result = github_client.get_file_content(owner, repo, name)
            if readme_result["success"]:
                readme_content = readme_result["data"].get("content", "")[:3000]
                break

    return {
        "success": True,
        "data": {
            "name": data.get("name"),
            "full_name": data.get("full_name"),
            "description": data.get("description"),
            "topics": data.get("topics", []),
            "stars": data.get("stargazers_count"),
            "forks": data.get("forks_count"),
            "open_issues": data.get("open_issues_count"),
            "language": data.get("language"),
            "license": data.get("license", {}).get("name") if data.get("license") else None,
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "url": data.get("html_url"),
            "readme": readme_content,
        },
    }


GET_REPO_INFO_TOOL = ToolDefinition(
    name="get_repo_info",
    description="获取仓库的基本信息（description、topics、star 数等）并尝试读取 README 内容",
    parameters_schema={
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "仓库名，格式 'owner/repo'"},
        },
        "required": ["repo"],
    },
    handler=real_get_repo_info,
)

