"""掘金技术社区文章发现 — api.juejin.cn 公开 JSON API，免费无需登录，国内直连"""
from __future__ import annotations

from typing import Any

import requests

BASE = "https://api.juejin.cn"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
}
TIMEOUT = 15

# 分类 cate_id 映射
_CATEGORIES = {
    "ai": "6809637771511070727",
    "frontend": "6809637767543259144",
    "backend": "6809637773939712014",
    "android": "6809635626879541261",
    "ios": "6809635626661445639",
    "freebie": "6809635064312209422",
    "article": "6809635064312209422",
}


def _post(path: str, body: dict) -> dict:
    r = requests.post(f"{BASE}{path}", json=body, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    if data.get("err_no") != 0:
        raise ValueError(f"掘金 API 错误: {data.get('err_msg', 'unknown')}")
    return data


def _normalize(items: list) -> list[dict]:
    out = []
    for item in items:
        # 接口结构: article_info 直接返回 或 item_info.article_info 嵌套
        info = item.get("article_info") or item.get("item_info", {}).get("article_info") or {}
        if not info.get("article_id"):
            continue
        author = info.get("author_user_info", {})
        out.append({
            "article_id": info.get("article_id", ""),
            "title": info.get("title", ""),
            "brief": (info.get("brief_content") or "")[:200],
            "author": author.get("user_name", ""),
            "category": info.get("category_name", ""),
            "tags": [t.get("tag_name", "") for t in info.get("tags", [])],
            "views": info.get("view_count", 0),
            "digg": info.get("digg_count", 0),
            "url": f"https://juejin.cn/post/{info.get('article_id', '')}",
        })
    return out


def juejin_recommended(sort: str = "hot", limit: int = 10, cursor: str = "0") -> dict[str, Any]:
    """掘金推荐流文章发现（hot=热门 / new=最新）"""
    data = _post(
        "/recommend_api/v1/article/recommend_all_feed",
        {
            "id_type": 2,
            "client_type": 2608,
            "sort_type": 200 if sort == "hot" else 300,
            "cursor": cursor,
            "limit": min(limit, 20),
        },
    )
    items = data.get("data", [])
    return {
        "ok": True,
        "action": "recommended",
        "sort": sort,
        "count": len(items),
        "cursor": data.get("cursor", cursor),
        "has_more": data.get("has_more", False),
        "articles": _normalize(items),
        "_note": "每篇文章全文通过 fetch_page(url) 获取",
    }


def juejin_by_category(category: str, limit: int = 10) -> dict[str, Any]:
    """按分类浏览掘金文章（ai/frontend/backend/android/ios/freebie/article）"""
    cate_id = _CATEGORIES.get(category)
    if not cate_id:
        return {
            "ok": False,
            "error": f"分类不存在: {category}",
            "detail": "可用分类: ai, frontend, backend, android, ios, freebie, article",
        }
    data = _post(
        "/recommend_api/v1/article/recommend_all_feed",
        {
            "id_type": 2,
            "client_type": 2608,
            "sort_type": 200,
            "cursor": "0",
            "limit": min(limit, 20),
            "cate_id": cate_id,
        },
    )
    items = data.get("data", [])
    return {
        "ok": True,
        "action": "by_category",
        "category": category,
        "count": len(items),
        "articles": _normalize(items),
        "_note": "每篇文章全文通过 fetch_page(url) 获取",
    }


