"""GitHub 仓库趋势 — GitHub REST API，零认证 60 次/h，可选 GITHUB_TOKEN 提升至 5000 次/h"""
from __future__ import annotations

import os
from typing import Any

import requests

BASE = "https://api.github.com"
TIMEOUT = 15


def _headers() -> dict:
    h = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "modou-tools-mcp/0.1",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _repo_summary(repo: dict) -> dict:
    return {
        "full_name": repo.get("full_name", ""),
        "stars": repo.get("stargazers_count", 0),
        "forks": repo.get("forks_count", 0),
        "open_issues": repo.get("open_issues_count", 0),
        "language": repo.get("language"),
        "description": repo.get("description") or "",
        "created_at": (repo.get("created_at") or "")[:10],
        "updated_at": (repo.get("updated_at") or "")[:10],
        "license": (repo.get("license") or {}).get("spdx_id"),
        "topics": repo.get("topics", []),
        "url": repo.get("html_url", ""),
    }


def github_search_repos(
    query: str,
    limit: int = 10,
    sort: str = "stars",
) -> dict[str, Any]:
    """搜索 GitHub 仓库，按 stars/forks/updated 排序"""
    result: dict[str, Any] = {"ok": False, "action": "search_repos", "query": query}
    try:
        r = requests.get(
            f"{BASE}/search/repositories",
            headers=_headers(),
            params={
                "q": query,
                "sort": sort if sort in ("stars", "forks", "updated") else "stars",
                "order": "desc",
                "per_page": min(limit, 50),
            },
            timeout=TIMEOUT,
        )
        if r.status_code == 403:
            return {
                "ok": False,
                "error": "GitHub API 限流",
                "detail": "无认证 60次/小时已达上限，配置 GITHUB_TOKEN 环境变量可提升至 5000次/小时",
            }
        r.raise_for_status()
        data = r.json()
        repos = [_repo_summary(x) for x in data.get("items", [])[:limit]]
        result.update(
            ok=True,
            count=len(repos),
            total_matches=data.get("total_count", 0),
            repos=repos,
        )
    except requests.RequestException as e:
        result.update(error="GitHub API 请求失败", detail=str(e))
    except Exception as e:
        result.update(error="解析失败", detail=str(e))
    return result


def github_compare_repos(repos: list[str]) -> dict[str, Any]:
    """对比多个 GitHub 仓库的当前快照数据"""
    result: dict[str, Any] = {"ok": True, "action": "compare_repos", "repos": []}
    for full_name in repos:
        try:
            r = requests.get(f"{BASE}/repos/{full_name}", headers=_headers(), timeout=TIMEOUT)
            if r.status_code == 403:
                result.update(
                    ok=False,
                    error="GitHub API 限流",
                    detail="配置 GITHUB_TOKEN 环境变量可提升至 5000次/小时",
                )
                return result
            r.raise_for_status()
            result["repos"].append(_repo_summary(r.json()))
        except requests.RequestException as e:
            result["repos"].append(
                {"full_name": full_name, "ok": False, "error": str(e)}
            )
    return result
