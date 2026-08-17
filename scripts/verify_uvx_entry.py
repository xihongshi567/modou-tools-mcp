"""验证 uvx 从 wheel 安装后能正常启动并完成 MCP 握手。

用法: uv run python scripts/verify_uvx_entry.py dist/modou_tools_mcp-0.1.0-py3-none-any.whl
"""
import json
import subprocess
import sys

wheel = sys.argv[1]
proc = subprocess.Popen(
    ["uvx", "--from", wheel, "modou-tools-mcp"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)


def send(msg):
    proc.stdin.write((json.dumps(msg) + "\n").encode())
    proc.stdin.flush()


def recv():
    line = proc.stdout.readline()
    return json.loads(line) if line else None


send(
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "entry-verify", "version": "0.1.0"},
        },
    }
)
r1 = recv()
print("initialize:", json.dumps(r1, ensure_ascii=False)[:200])

send({"jsonrpc": "2.0", "method": "notifications/initialized"})
send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
r2 = recv()
if r2 and "result" in r2:
    tools = r2["result"].get("tools", [])
    print(f"tools/list: {len(tools)} tools")
    for t in tools:
        print("  -", t["name"])
else:
    print("tools/list FAIL:", json.dumps(r2, ensure_ascii=False)[:500])

proc.kill()
