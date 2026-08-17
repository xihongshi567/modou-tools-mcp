"""验证魔搭托管版 modou-tools MCP 服务端到端可用。

用法: D:/anaconda2024/python.exe scripts/verify_modelscope_remote.py <remote_url>
"""
import json
import sys

import requests

URL = sys.argv[1] if len(sys.argv) > 1 else ""
H = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}


def post(msg, sid=None, timeout=180):
    h = dict(H)
    if sid:
        h["mcp-session-id"] = sid
    r = requests.post(URL, headers=h, json=msg, timeout=timeout)
    sid2 = r.headers.get("mcp-session-id", sid)
    data = None
    for line in r.text.splitlines():
        if line.startswith("data:"):
            data = json.loads(line[5:].strip())
    if data is None:
        try:
            data = r.json()
        except Exception:
            data = {"raw": r.text[:500], "status": r.status_code}
    return sid2, data


def main():
    print("== 1. initialize ==")
    sid, r1 = post({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                               "clientInfo": {"name": "verify-remote", "version": "1.0"}}})
    print("  ->", json.dumps(r1, ensure_ascii=False)[:180])
    if "result" not in r1:
        print("FAIL initialize"); sys.exit(1)

    post({"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)

    print("== 2. tools/list ==")
    sid, r2 = post({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, sid)
    tools = (r2.get("result") or {}).get("tools", [])
    print(f"  -> {len(tools)} 个工具")
    for t in tools:
        print("   -", t.get("name"))
    if len(tools) != 15:
        print("FAIL 工具数量 != 15"); sys.exit(1)

    print("== 3. tools/call arxiv_search(query=agent) ==")
    sid, r3 = post({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                    "params": {"name": "arxiv_search", "arguments": {"query": "agent", "limit": 3}}}, sid)
    content = json.dumps(r3, ensure_ascii=False)
    print("  ->", content[:500])
    ok = "isError" not in (r3.get("result") or {}) or (r3.get("result") or {}).get("isError") is False
    print("\n结果:", "通过" if ok else "失败")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
