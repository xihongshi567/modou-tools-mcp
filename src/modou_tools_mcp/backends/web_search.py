"""网页搜索工具 — SearXNG 聚合搜索，供素材收集员 Agent function calling 使用

前提: SearXNG Docker 运行在 localhost:8080

Function calling 定义:
{
  "name": "web_search",
  "description": "中文网页搜索，聚合百度/搜狗/Bing CN 等多个搜索引擎结果。
                  适合搜索行业报告、技术文章、新闻、用户讨论等中文内容。",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "搜索关键词，支持中文"
      },
      "num_results": {
        "type": "integer",
        "description": "返回结果数量，默认 10，最大 20"
      },
      "language": {
        "type": "string",
        "description": "搜索语言，默认 zh-CN。可选: zh-CN, en, all"
      }
    },
    "required": ["query"]
  }
}
"""
from __future__ import annotations

import json
import time
from typing import Any

import requests

SEARXNG_URL = "http://localhost:8080/search"
TIMEOUT = 15


def web_search(
    query: str,
    num_results: int = 10,
    language: str = "zh-CN",
) -> dict[str, Any]:
    """SearXNG 聚合搜索。

    Args:
        query: 搜索关键词，支持中文
        num_results: 返回结果数量，默认 10
        language: 搜索语言，默认 zh-CN

    Returns:
        {
          "ok": true/false,
          "query": "原始查询",
          "count": 返回结果数,
          "results": [
            {"title": "...", "url": "...", "snippet": "摘要", "source": "搜索引擎"},
            ...
          ],
          "error": "错误信息（仅失败时）"
        }
    """
    result = {
        "ok": False,
        "query": query,
        "count": 0,
        "results": [],
    }

    try:
        r = requests.get(
            SEARXNG_URL,
            params={
                "q": query,
                "format": "json",
                "language": language,
            },
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()

        items = data.get("results", [])[:num_results]
        result["results"] = [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": (item.get("snippet", item.get("content", "")) or "")[:300],
                "source": item.get("engine", item.get("source", "")),
            }
            for item in items
        ]
        result["ok"] = True
        result["count"] = len(result["results"])

    except requests.ConnectionError:
        result["error"] = "SearXNG 未运行，请先启动 Docker: docker start searxng"
    except requests.Timeout:
        result["error"] = f"搜索超时 ({TIMEOUT}s)"
    except Exception as e:
        result["error"] = f"搜索失败: {e}"

    return result


def web_search_text(query: str, num_results: int = 10) -> str:
    """快捷版：返回搜索结果的 Markdown 摘要，适合注入 LLM 上下文"""
    r = web_search(query, num_results)
    if not r["ok"]:
        return f"[web_search 失败] {r['error']}"

    lines = [f"## 搜索: {r['query']}", f"共 {r['count']} 条结果\n"]
    for i, item in enumerate(r["results"], 1):
        lines.append(f"{i}. **[{item['title']}]({item['url']})**")
        if item["snippet"]:
            lines.append(f"   {item['snippet']}")
        lines.append("")
    return "\n".join(lines)


# CLI 测试入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print("用法:")
        print("  python web_search.py <关键词>              # 搜索并显示摘要")
        print("  python web_search.py <关键词> --json       # JSON 输出")
        print("  python web_search.py --tool-def            # function calling 定义")
        sys.exit(0)

    if sys.argv[1] == "--tool-def":
        print(json.dumps(build_tool_definition(), ensure_ascii=False, indent=2))
        sys.exit(0)

    query = sys.argv[1]
    output_json = "--json" in sys.argv

    if output_json:
        r = web_search(query)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(web_search_text(query))
