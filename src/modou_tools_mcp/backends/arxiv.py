"""arXiv 论文检索 — export.arxiv.org 公开 API，免费免登录，国内直连"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import requests

API = "https://export.arxiv.org/api/query"
TIMEOUT = 20

_NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def _parse_feed(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    out = []
    for e in root.findall("a:entry", _NS):
        authors = [
            a.find("a:name", _NS).text or ""
            for a in e.findall("a:author", _NS)
        ]
        summary = (e.findtext("a:summary", "", _NS) or "").strip().replace("\n", " ")
        out.append({
            "title": (e.findtext("a:title", "", _NS) or "").strip().replace("\n", " "),
            "authors": authors[:10],
            "summary": summary[:500],
            "published": (e.findtext("a:published", "", _NS) or "")[:10],
            "updated": (e.findtext("a:updated", "", _NS) or "")[:10],
            "primary_category": e.findtext("arxiv:primary_category", "", _NS),
            "url": e.findtext("a:id", "", _NS) or "",
            "pdf_url": (e.findtext("a:id", "", _NS) or "").replace("/abs/", "/pdf/"),
        })
    return out


def arxiv_search(
    query: str,
    limit: int = 10,
    sort: str = "relevance",
) -> dict[str, Any]:
    """搜索 arXiv 论文（标题/摘要/作者全字段匹配）。

    Args:
        query: 搜索词，支持 arXiv 高级语法如 'cat:cs.AI AND all:agent'，也支持纯关键词
        limit: 返回数量，默认 10，最大 50
        sort: 排序，relevance=相关度（默认）/ submittedDate=最新提交
    """
    try:
        r = requests.get(
            API,
            params={
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": min(limit, 50),
                "sortBy": sort if sort in ("relevance", "submittedDate") else "relevance",
                "sortOrder": "descending",
            },
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        papers = _parse_feed(r.text)
        return {
            "ok": True,
            "query": query,
            "count": len(papers),
            "sort": sort,
            "papers": papers,
            "_note": "摘要已截断至 500 字符，全文通过 fetch_page(pdf_url) 或 arxiv.org 页面获取",
        }
    except requests.RequestException as e:
        return {"ok": False, "error": "arXiv API 请求失败", "detail": str(e)}
    except ET.ParseError as e:
        return {"ok": False, "error": "arXiv 响应解析失败", "detail": str(e)}
    except Exception as e:
        return {"ok": False, "error": "解析失败", "detail": str(e)[:200]}
