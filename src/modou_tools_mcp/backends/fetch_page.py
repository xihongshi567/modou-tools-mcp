"""网页内容提取工具 — 智能去噪 + Markdown 输出，供素材收集员 Agent function calling 使用

依赖: trafilatura (pip install trafilatura)

Function calling 定义:
{
  "name": "fetch_page",
  "description": "抓取指定网页正文，自动去广告/导航/侧边栏，输出干净 Markdown。
                  保留标题层级、链接、列表等结构，对 LLM 友好。",
  "parameters": {
    "type": "object",
    "properties": {
      "url": {
        "type": "string",
        "description": "要抓取的网页 URL"
      },
      "include_links": {
        "type": "boolean",
        "description": "是否保留链接，默认 true"
      },
      "max_chars": {
        "type": "integer",
        "description": "最大返回字符数，默认 8000。超长自动截断并标注"
      }
    },
    "required": ["url"]
  }
}
"""
from __future__ import annotations

import json
import re
import textwrap
from typing import Any

import requests
import trafilatura

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
}

# 需要先"敲门"拿 Cookie 才能访问的站点
_TRICKY_HOSTS = {
    "zhihu.com": "https://www.zhihu.com/hot",
    "weibo.com": "https://weibo.com/",
    "douyin.com": "https://www.douyin.com/",
}


def _create_session(url: str) -> requests.Session:
    """创建带浏览器指纹的 Session，对需要 Cookie 种子的站点先敲门"""
    sess = requests.Session()
    sess.headers.update(BROWSER_HEADERS)

    # 自动生成 Referer
    from urllib.parse import urlparse
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    sess.headers["Referer"] = origin + "/"

    # 对需要 Cookie 的站点先敲门
    host = parsed.netloc.lower()
    for host_key, knock_url in _TRICKY_HOSTS.items():
        if host_key in host:
            try:
                sess.get(knock_url, timeout=10)
            except Exception:
                pass
            break

    return sess


def fetch_page(
    url: str,
    include_links: bool = True,
    max_chars: int = 8000,
) -> dict[str, Any]:
    """抓取网页正文，输出干净 Markdown。

    Args:
        url: 网页 URL
        include_links: 是否保留链接
        max_chars: 最大字符数，超长截断并标注剩余量

    Returns:
        {
          "ok": true/false,
          "url": "原始 URL",
          "title": "页面标题",
          "author": "作者（如有）",
          "date": "发布日期（如有）",
          "markdown": "正文 Markdown",
          "chars_total": 原文总字符数,
          "chars_returned": 实际返回字符数,
          "truncated": true/false,
          "error": "错误信息（仅失败时）"
        }
    """
    result = {
        "ok": False,
        "url": url,
        "title": "",
        "author": "",
        "date": "",
        "markdown": "",
        "chars_total": 0,
        "chars_returned": 0,
        "truncated": False,
    }

    try:
        # 1. 抓取 HTML（带 Session + 敲门逻辑）
        sess = _create_session(url)
        r = sess.get(url, timeout=15)
        r.raise_for_status()

        # 2. 用原始字节给 trafilatura 解析（避免 requests 猜错中文编码）
        html_bytes = r.content

        # 3. trafilatura 提取元数据
        metadata = trafilatura.extract_metadata(
            html_bytes,
            default_url=url,
        )
        if metadata:
            result["title"] = metadata.title or ""
            result["author"] = metadata.author or ""
            result["date"] = str(metadata.date) if metadata.date else ""

        # 4. trafilatura 智能提取正文 → Markdown
        md = trafilatura.extract(
            html_bytes,
            output_format="markdown",
            include_links=include_links,
            include_images=False,
            include_tables=True,
            favor_precision=True,  # 宁可少取不取错
        )

        if not md:
            result["error"] = "trafilatura 未能从页面提取到正文内容"
            return result

        # 4. 处理超长
        md = md.strip()
        result["chars_total"] = len(md)

        if len(md) > max_chars:
            md = md[:max_chars]
            # 在最近的段落边界截断
            last_break = max(md.rfind("\n\n"), md.rfind("\n"))
            if last_break > max_chars * 0.7:
                md = md[:last_break]
            result["truncated"] = True
            remaining = result["chars_total"] - len(md)
            md += f"\n\n> ⚠️ 内容已截断，还有约 {remaining:,} 字符。用 start_index={len(md)} 继续读取。"

        result["ok"] = True
        result["markdown"] = md
        result["chars_returned"] = len(md)

    except requests.RequestException as e:
        result["error"] = f"HTTP 请求失败: {e}"
    except Exception as e:
        result["error"] = f"解析失败: {e}"

    return result


def fetch_page_text(url: str, max_chars: int = 8000) -> str:
    """快捷版：直接返回 Markdown 字符串，适合注入 LLM 上下文"""
    r = fetch_page(url, max_chars=max_chars)
    if not r["ok"]:
        return f"[fetch_page 失败] {r['error']}"

    header = f"## {r['title'] or '无标题'}"
    if r["author"] or r["date"]:
        meta = " · ".join(filter(None, [r["author"], r["date"]]))
        header += f"\n*{meta}*"
    return f"{header}\n{r['markdown']}"


# CLI 测试入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print("用法:")
        print("  python fetch_page.py <URL>              # 抓取页面，Markdown 输出")
        print("  python fetch_page.py <URL> --json       # JSON 格式输出")
        print("  python fetch_page.py --tool-def         # 输出 function calling 定义")
        sys.exit(0)

    if sys.argv[1] == "--tool-def":
        print(json.dumps(build_tool_definition(), ensure_ascii=False, indent=2))
        sys.exit(0)

    url = sys.argv[1]
    output_json = "--json" in sys.argv

    r = fetch_page(url)

    if output_json:
        safe = {k: v for k, v in r.items() if k != "markdown"}
        safe["markdown_preview"] = r["markdown"][:500]
        print(json.dumps(safe, ensure_ascii=False, indent=2))
    else:
        if r["ok"]:
            print(r["markdown"])
        else:
            print(f"❌ {r['error']}")
