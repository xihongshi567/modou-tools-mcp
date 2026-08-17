"""离线冒烟测试: 验证 8 个工具的函数签名与返回结构（不依赖网络的部分）

用法: D:/anaconda2024/python.exe smoke_test.py
"""
import sys
import json

sys.path.insert(0, "src")

from modou_tools_mcp.backends import web_search, fetch_page, hot_topics, github, sec, juejin, cninfo, pdf, arxiv, exa

PASS = 0
FAIL = 0


def expect(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  OK   {label}")
    else:
        FAIL += 1
        print(f"  FAIL {label}  {detail}")


def is_ok_shape(r, name):
    return isinstance(r, dict) and "ok" in r


print("== 参数缺失检查（不依赖网络） ==")
expect("web_search 空 query", web_search.web_search("")["ok"] is False)
expect("fetch_page 空 url", fetch_page.fetch_page("")["ok"] is False)
expect("github 空 query 搜索失败或 ok 结构", is_ok_shape(github.github_search_repos(""), "github"))
expect("arxiv 空 query 返回 ok 结构", is_ok_shape(arxiv.arxiv_search(""), "arxiv"))
expect("exa 空 query 返回 ok 结构", is_ok_shape(exa.exa_search(""), "exa"))
expect("sec 缺参数", sec.sec_company_facts()["ok"] is False)
expect("juejin 非法分类", juejin.juejin_by_category("xyz")["ok"] is False)
expect("cninfo profile 返回结构", is_ok_shape(cninfo.cninfo_company_profile("000000"), "cninfo"))
expect("pdf 缺参数", pdf.parse_pdf()["ok"] is False)
expect("pdf 文件不存在", pdf.parse_pdf(file_path="D:/nope/nonexist.pdf")["ok"] is False)

print("\n== 返回结构检查 ==")
r = hot_topics.fetch_hot_topics([])
expect("hot_topics 返回 _meta", isinstance(r, dict) and "_meta" in r)
r = sec.sec_company_facts()
expect("sec 缺参数时 ok=false", r["ok"] is False and "error" in r)
r = juejin.juejin_recommended()
expect("juejin recommended ok 结构", is_ok_shape(r, "juejin"))
r = github.github_compare_repos(["a/b"])
expect("github compare ok 结构", is_ok_shape(r, "github"))

print(f"\n结果: {PASS} 通过, {FAIL} 失败")
sys.exit(1 if FAIL else 0)
