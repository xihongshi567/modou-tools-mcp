"""热点获取工具 — 供素材收集员 Agent function calling 使用
零认证、零费用，并发拉取知乎/B站/GitHub/HN 热榜。

Function calling 定义:
{
  "name": "fetch_hot_topics",
  "description": "获取主流平台当前热搜/热点榜单，了解技术社区焦点、找选题灵感。
                  平台: zhihu(知乎热榜), bilibili(B站热门视频), github(GitHub趋势仓库),
                  hackernews(HN 首页热帖)。
                  零认证，零费用。",
  "parameters": {
    "type": "object",
    "properties": {
      "platforms": {
        "type": "array", "items": {"type": "string"},
        "description": "要获取的平台列表。不传或传空列表则获取全部。"
      }
    },
    "required": []
  }
}
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
}

# ── 平台注册 ──────────────────────────────────────────────

_FETCHERS: dict[str, dict] = {}


def _register(name: str, cn_name: str, description: str):
    def deco(fn):
        _FETCHERS[name] = {"cn_name": cn_name, "desc": description, "fn": fn}
        return fn
    return deco


# ═══════════════════════════════════════════════════════════
# 各平台抓取器
# ═══════════════════════════════════════════════════════════

@_register("zhihu", "知乎", "知乎热榜搜索关键词 Top 20")
def _fetch_zhihu() -> list[dict]:
    sess = requests.Session()
    sess.get(
        "https://www.zhihu.com/hot",
        headers={**HEADERS, "Referer": "https://www.zhihu.com/"},
        timeout=10,
    )
    r = sess.get(
        "https://www.zhihu.com/api/v4/search/top_search/tabs/hot/items",
        headers={
            **HEADERS,
            "Accept": "application/json",
            "Referer": "https://www.zhihu.com/hot",
            "x-api-version": "3.0.40",
        },
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    items = []
    for i, entry in enumerate(data.get("data", [])[:20], 1):
        title = entry.get("query_display", "")
        if not title:
            continue
        items.append({
            "rank": i,
            "title": title,
            "hot": 0,
            "hot_text": entry.get("query_description", "") or "",
            "url": f"https://www.zhihu.com/search?q={entry.get('real_query', title)}",
        })
    return items


@_register("bilibili", "B站", "B站综合热门视频 Top 20")
def _fetch_bilibili() -> list[dict]:
    r = requests.get(
        "https://api.bilibili.com/x/web-interface/popular",
        headers={**HEADERS, "Referer": "https://www.bilibili.com/"},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    items = []
    for i, entry in enumerate(data.get("data", {}).get("list", [])[:20], 1):
        items.append({
            "rank": i,
            "title": entry.get("title", ""),
            "hot": entry.get("stat", {}).get("view", 0),
            "url": entry.get("short_link_v2", entry.get("short_link", "")),
        })
    return items


@_register("github", "GitHub", "GitHub 近7天高星新仓库 Top 20")
def _fetch_github() -> list[dict]:
    from datetime import datetime, timedelta
    week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    r = requests.get(
        "https://api.github.com/search/repositories",
        headers={**HEADERS, "Accept": "application/vnd.github+json"},
        params={
            "q": f"stars:>100 created:>{week_ago}",
            "sort": "stars",
            "order": "desc",
            "per_page": 20,
        },
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    items = []
    for i, repo in enumerate(data.get("items", [])[:20], 1):
        items.append({
            "rank": i,
            "title": repo.get("full_name", ""),
            "hot": repo.get("stargazers_count", 0),
            "url": repo.get("html_url", ""),
        })
    return items


@_register("hackernews", "HackerNews", "HN 首页热帖 Top 20")
def _fetch_hackernews() -> list[dict]:
    r = requests.get(
        "https://hn.algolia.com/api/v1/search",
        headers={**HEADERS, "Accept": "application/json"},
        params={"tags": "front_page", "hitsPerPage": 20},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    items = []
    for i, h in enumerate(data.get("hits", [])[:20], 1):
        items.append({
            "rank": i,
            "title": h.get("title", ""),
            "hot": h.get("points", 0),
            "hot_text": f"💬{h.get('num_comments', 0)}评论",
            "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID', '')}",
        })
    return items


# ═══════════════════════════════════════════════════════════
# 公开接口
# ═══════════════════════════════════════════════════════════

def available_platforms() -> list[dict]:
    """返回可用平台列表，供 Agent 决策"""
    return [
        {"id": name, "name": cfg["cn_name"], "description": cfg["desc"]}
        for name, cfg in _FETCHERS.items()
    ]


def fetch_hot_topics(platforms: list[str] | None = None) -> dict[str, Any]:
    """并发拉取指定平台的热榜数据。

    Args:
        platforms: 平台 ID 列表。None 或空列表表示获取全部。
                   可选: zhihu, bilibili, github, hackernews

    Returns:
        {
          "<platform_id>": {
            "cn_name": "中文名",
            "ok": true/false,
            "error": "错误信息（仅失败时）",
            "count": 条目数,
            "items": [
              {"rank": 1, "title": "...", "hot": 1234567, "url": "..."},
              ...
            ]
          },
          ...
        }
    """
    targets = [p for p in (platforms or []) if p in _FETCHERS]
    if not targets:
        targets = list(_FETCHERS.keys())

    results: dict[str, dict] = {}
    t0 = time.time()

    def _fetch_one(name: str) -> tuple[str, str, list[dict] | None]:
        try:
            items = _FETCHERS[name]["fn"]()
            return (name, "", items)
        except Exception as e:
            return (name, str(e), None)

    with ThreadPoolExecutor(max_workers=len(targets)) as pool:
        futures = {pool.submit(_fetch_one, t): t for t in targets}
        for fut in as_completed(futures):
            name, error, items = fut.result()
            cfg = _FETCHERS[name]
            results[name] = {
                "cn_name": cfg["cn_name"],
                "ok": error == "",
                "count": len(items) if items else 0,
                "items": items or [],
            }
            if error:
                results[name]["error"] = error

    results["_meta"] = {
        "elapsed_ms": int((time.time() - t0) * 1000),
        "total_platforms": len(targets),
        "ok_count": sum(1 for r in results.values() if r.get("ok")),
    }

    return results


def fetch_hot_topics_summary(platforms: list[str] | None = None) -> str:
    """返回热榜摘要文本，适合直接注入 LLM 对话上下文。

    格式: 每个平台一段 Markdown，含 Top 10 标题和热度。
    """
    data = fetch_hot_topics(platforms)
    lines = []
    for pid, info in data.items():
        if pid == "_meta":
            continue
        status = "✅" if info["ok"] else "❌"
        lines.append(f"## {status} {info['cn_name']} ({pid})")
        if not info["ok"]:
            lines.append(f"错误: {info.get('error', '未知')}")
            lines.append("")
            continue
        lines.append(f"共 {info['count']} 条")
        for item in info["items"][:10]:
            hot = item.get("hot_text") or (f"🔥{item['hot']}" if item.get("hot") else "")
            lines.append(f"{item['rank']:>2}. {item['title'][:60]}  {hot}")
        lines.append("")
    return "\n".join(lines)


# CLI 测试入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if "--help" in sys.argv or "-h" in sys.argv:
        print("用法:")
        print("  python hot_topics.py               # 全部平台，文本摘要")
        print("  python hot_topics.py --json        # 全部平台，JSON 输出")
        print("  python hot_topics.py zhihu bilibili  # 指定平台")
        print("  python hot_topics.py --tool-def    # 输出 function calling 定义")
        print()
        print("可用平台:", ", ".join(_FETCHERS.keys()))
        sys.exit(0)

    if "--tool-def" in sys.argv:
        print(json.dumps(build_tool_definition(), ensure_ascii=False, indent=2))
        sys.exit(0)

    targets = [a for a in sys.argv[1:] if not a.startswith("--")]
    output_json = "--json" in sys.argv

    if output_json:
        result = fetch_hot_topics(targets or None)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(fetch_hot_topics_summary(targets or None))
