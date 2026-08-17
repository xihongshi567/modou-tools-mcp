"""Exa 英文语义搜索 — 通过 Exa 免费 MCP 端点（streamable HTTP），免 key 国内直连

端点: https://mcp.exa.ai/mcp (streamable HTTP + SSE 响应)
工具: web_search_exa / web_fetch_exa
"""
from __future__ import annotations

import json
from typing import Any

import requests

BASE = "https://mcp.exa.ai/mcp"
TIMEOUT = 30
_HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}

_session: requests.Session | None = None
_session_id: str | None = None
_MAX_RESULTS = 10


def _sse_last(text: str) -> dict:
    """解析 SSE 响应，返回最后一个 data 的 JSON"""
    payload = None
    for block in text.split("\n\n"):
        for line in block.split("\n"):
            if line.startswith("data: "):
                payload = json.loads(line[6:])
    if payload is None:
        raise ValueError("SSE 响应中无 data")
    return payload


def _ensure_session() -> tuple[requests.Session, str]:
    """懒初始化 MCP 会话（模块级缓存，失败重建）"""
    global _session, _session_id
    if _session is not None and _session_id:
        return _session, _session_id

    s = requests.Session()
    r = s.post(
        BASE,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "modou-tools", "version": "0.1"},
            },
        },
        headers=_HEADERS,
        timeout=20,
    )
    r.raise_for_status()
    sess_id = r.headers.get("mcp-session-id")
    if not sess_id:
        raise ValueError("Exa 未返回 session id")
    _sse_last(r.text)  # 确认 initialize 成功

    h2 = {**_HEADERS, "mcp-session-id": sess_id}
    s.post(BASE, json={"jsonrpc": "2.0", "method": "notifications/initialized"}, headers=h2, timeout=20)
    _session, _session_id = s, sess_id
    return s, sess_id


def _call(tool: str, arguments: dict) -> dict:
    s, sess_id = _ensure_session()
    h2 = {**_HEADERS, "mcp-session-id": sess_id}
    r = s.post(
        BASE,
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
        },
        headers=h2,
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return _sse_last(r.text)


def exa_search(query: str, num_results: int = 10) -> dict[str, Any]:
    """Exa 语义搜索（英文为主），适合海外技术趋势、行业报告、论文。

    用描述性语句搜索效果更好，如 "blog post comparing React and Vue performance"
    """
    try:
        res = _call("web_search_exa", {"query": query, "numResults": min(num_results, _MAX_RESULTS)})
        content = res.get("result", {}).get("content", [])
        text = ""
        for c in content:
            if c.get("type") == "text":
                text += c.get("text", "")
        if not text:
            is_error = res.get("result", {}).get("isError")
            if is_error:
                return {"ok": False, "error": "Exa 搜索失败", "detail": text[:200] or "无错误详情"}
        return {
            "ok": True,
            "query": query,
            "count": len(text.split("Title:")) - 1 if "Title:" in text else 0,
            "markdown": text,
            "_note": "结果为 Markdown 报告，含 Title/URL/Published/Highlights",
        }
    except requests.RequestException as e:
        # 会话可能失效，重建后重试一次
        global _session, _session_id
        _session, _session_id = None, None
        try:
            res = _call("web_search_exa", {"query": query, "numResults": min(num_results, _MAX_RESULTS)})
            content = res.get("result", {}).get("content", [])
            text = "".join(c.get("text", "") for c in content if c.get("type") == "text")
            return {"ok": True, "query": query, "count": len(text.split("Title:")) - 1, "markdown": text}
        except Exception as e2:
            return {"ok": False, "error": "Exa 请求失败", "detail": str(e2)[:200]}
    except Exception as e:
        return {"ok": False, "error": "Exa 请求失败", "detail": str(e)[:200]}
