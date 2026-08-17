"""PDF 报告解析 — PyMuPDF，本地/在线 PDF → Markdown + 表格，扫描版返回警告"""
from __future__ import annotations

import os
import tempfile
from typing import Any

import requests


def _download(url: str) -> str:
    """下载 PDF 到临时文件，返回路径"""
    r = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
        },
        timeout=30,
    )
    r.raise_for_status()
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.write(r.content)
    tmp.close()
    return tmp.name


def parse_pdf(
    url: str = "",
    file_path: str = "",
    max_pages: int = 30,
    extract_tables: bool = True,
) -> dict[str, Any]:
    """解析 PDF 报告为 Markdown（保留表格），本地文件或在线 URL 均可"""
    try:
        import pymupdf as fitz  # 新模块名，避免 fitz deprecation warning 污染 MCP stdio
    except ImportError:
        try:
            import fitz
        except ImportError:
            return {"ok": False, "error": "pymupdf 未安装", "detail": "pip install pymupdf"}

    if not url and not file_path:
        return {"ok": False, "error": "缺少参数", "detail": "url 与 file_path 至少提供其一"}

    tmp_path = None
    try:
        if url:
            try:
                tmp_path = _download(url)
                doc = fitz.open(tmp_path)
            except requests.RequestException as e:
                return {"ok": False, "error": "PDF 下载失败", "detail": str(e)}
        else:
            if not os.path.exists(file_path):
                return {"ok": False, "error": "PDF 文件不存在", "detail": file_path}
            doc = fitz.open(file_path)

        pages_total = doc.page_count
        pages_to_read = min(pages_total, max_pages)
        parts: list[str] = []
        tables_found = 0
        total_text = 0

        for i in range(pages_to_read):
            page = doc[i]
            text = page.get_text()
            total_text += len(text)
            if text.strip():
                parts.append(text.strip())
            if extract_tables:
                try:
                    tabs = page.find_tables()
                    if tabs:
                        tables_found += len(tabs.tables)
                        for t in tabs.tables:
                            rows = t.extract()
                            if rows:
                                md = "\n".join(
                                    "| " + " | ".join(str(c or "").replace("|", "\\|") for c in row) + " |"
                                    for row in rows
                                )
                                parts.append(md)
                except Exception:
                    pass

        doc.close()
        if tmp_path:
            os.unlink(tmp_path)

        markdown = "\n\n".join(parts).strip()
        is_scanned = total_text < 50 and pages_total > 0
        result: dict[str, Any] = {
            "ok": True,
            "title": os.path.basename(file_path) if file_path else url,
            "pages_total": pages_total,
            "pages_returned": pages_to_read,
            "has_tables": tables_found > 0,
            "tables_found": tables_found,
            "is_scanned": is_scanned,
            "truncated": pages_to_read < pages_total,
            "markdown": markdown,
        }
        if is_scanned:
            result["scanned_note"] = "此 PDF 为扫描图片，文字提取为空。"
        if pages_to_read < pages_total:
            result["truncated_note"] = f"仅返回前 {pages_to_read} 页，剩余 {pages_total - pages_to_read} 页未提取。"
        return result
    except Exception as e:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        return {"ok": False, "error": "PDF 解析失败", "detail": str(e)[:200]}
