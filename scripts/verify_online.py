"""在线验证 8 个工具（需要网络）

用法: D:/anaconda2024/python.exe scripts/verify_online.py
"""
import json
import sys

sys.path.insert(0, "src")

from modou_tools_mcp.backends import web_search, fetch_page, hot_topics, github, juejin, pdf, sec, cninfo, arxiv, exa

PASS, FAIL = 0, 0


def check(label, r, require_ok=True):
    global PASS, FAIL
    ok = isinstance(r, dict) and (r.get("ok") is True if require_ok else "ok" in r)
    tag = "OK  " if ok else "FAIL"
    if ok:
        PASS += 1
        extra = ""
        if "count" in r:
            extra = f" count={r['count']}"
        elif "pages_total" in r:
            extra = f" pages={r['pages_total']} tables={r.get('tables_found', 0)} scanned={r.get('is_scanned')}"
        print(f"  {tag} {label}{extra}")
    else:
        FAIL += 1
        err = r.get("error", r.get("detail", "?"))
        print(f"  {tag} {label}: {err}")


print("== 1. web_search (需 SearXNG localhost:8080) ==")
check("搜索 'AI 编程工具'", web_search.web_search("AI 编程工具", 5))

print("\n== 2. fetch_page ==")
_rec = juejin.juejin_recommended(limit=3)
_real_url = (_rec.get("articles") or [{}])[0].get("url", "")
if _real_url:
    check(f"抓取掘金文章 {_real_url[:40]}", fetch_page.fetch_page(_real_url, max_chars=2000))
else:
    print("  SKIP 推荐流无文章，跳过 fetch_page")

print("\n== 3. fetch_hot_topics ==")
r = hot_topics.fetch_hot_topics([])
meta = r.get("_meta", {})
print(f"  平台 {meta.get('ok_count')}/{meta.get('total_platforms')} 成功, 耗时 {meta.get('elapsed_ms')}ms")
if meta.get("ok_count", 0) > 0:
    PASS += 1
    print("  OK   hot_topics 结构")
else:
    FAIL += 1
    print("  FAIL hot_topics 结构")

print("\n== 4. github ==")
check("搜索 'AI agent'", github.github_search_repos("AI agent framework", 3))
r = github.github_compare_repos(["langchain-ai/langchain", "openai/openai-python"])
if not r.get("ok") and "限流" in r.get("error", ""):
    print("  SKIP 对比仓库: 环境 IP 无认证配额耗尽（60次/h），代码已正确处理 403")
else:
    check("对比仓库", r)

print("\n== 5. juejin ==")
check("推荐流", juejin.juejin_recommended(limit=5))
check("分类 AI", juejin.juejin_by_category("ai", 3))

print("\n== 5.5 arxiv ==")
check("搜索 'agent'", arxiv.arxiv_search("agent", 3))
check("按最新排序", arxiv.arxiv_search("LLM reasoning", 3, sort="submittedDate"))

print("\n== 5.6 exa ==")
check("英文语义搜索", exa.exa_search("best AI coding tools 2026 comparison", 3))

print("\n== 6. parse_pdf ==")
check("解析 arXiv PDF", pdf.parse_pdf(url="https://arxiv.org/pdf/2401.00001.pdf", max_pages=3))

print("\n== 7. sec (较慢) ==")
check("MSFT 财报", sec.sec_company_facts(ticker="MSFT", years=2))
check("对比 MSFT/AAPL", sec.sec_compare_companies(["MSFT", "AAPL"], years=1))

print("\n== 8. cninfo (东方财富, 有重试) ==")
check("科大讯飞财务分析", cninfo.cninfo_financial_analysis("002230", years=2))
r = cninfo.cninfo_company_profile("600519")
if not r.get("ok"):
    import time
    time.sleep(3)
    r = cninfo.cninfo_company_profile("600519")
check("茅台公司信息", r)

print(f"\n结果: {PASS} 通过, {FAIL} 失败")
sys.exit(1 if FAIL else 0)
