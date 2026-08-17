"""modou-tools-mcp: 素材收集员 8 个采集工具沉淀为 MCP server

用法:
  modou-tools-mcp                 # stdio 模式启动（Claude Code / MCP 客户端默认）
  python -m modou_tools_mcp.server

Claude Code 挂载:
  claude mcp add modou-tools -- python "D:/okok/modou-tools-mcp/src/modou_tools_mcp/server.py"
"""
from __future__ import annotations

import warnings

warnings.filterwarnings("ignore")  # 第三方库 warning 会污染 MCP stdio 协议流

from fastmcp import FastMCP

from modou_tools_mcp.backends import arxiv, cninfo, exa, fetch_page, github, hot_topics, juejin, pdf, sec, web_search

mcp = FastMCP("modou-tools")


# ── 发现 ─────────────────────────────────────────────────────

@mcp.tool()
def web_search(query: str, num_results: int = 10, language: str = "zh-CN") -> dict:
    """中文网页搜索，聚合百度/搜狗/Bing CN 等引擎（依赖本地 SearXNG localhost:8080）。

    Args:
        query: 搜索关键词，支持中文
        num_results: 返回结果数量，默认 10
        language: 搜索语言，默认 zh-CN，可选 en / all
    """
    return web_search.web_search(query, num_results, language)


@mcp.tool()
def fetch_hot_topics(platforms: list[str] | None = None) -> dict:
    """获取主流平台当前热搜榜单（zhihu 知乎 / bilibili B站 / github GitHub 趋势 / hackernews HN）。

    Args:
        platforms: 平台列表，不传则获取全部
    """
    return hot_topics.fetch_hot_topics(platforms)


@mcp.tool()
def juejin_recommended(sort: str = "hot", limit: int = 10, cursor: str = "0") -> dict:
    """掘金技术社区推荐流文章发现。

    Args:
        sort: hot=热门（默认） / new=最新
        limit: 返回数量，默认 10，最大 20
        cursor: 分页游标，首次不传
    """
    return juejin.juejin_recommended(sort, limit, cursor)


@mcp.tool()
def juejin_by_category(category: str, limit: int = 10) -> dict:
    """按分类浏览掘金文章（ai / frontend / backend / android / ios / freebie / article）。

    Args:
        category: 分类名
        limit: 返回数量，默认 10，最大 20
    """
    return juejin.juejin_by_category(category, limit)


@mcp.tool()
def github_search_repos(query: str, limit: int = 10, sort: str = "stars") -> dict:
    """搜索 GitHub 仓库趋势，把技术趋势翻译成数字（stars/forks/活跃度）。

    Args:
        query: 搜索关键词，如 "AI agent framework"
        limit: 返回数量，默认 10
        sort: 排序，stars（默认）/ forks / updated
    """
    return github.github_search_repos(query, limit, sort)


@mcp.tool()
def github_compare_repos(repos: list[str]) -> dict:
    """对比多个 GitHub 仓库的当前快照数据。

    Args:
        repos: 仓库全名列表，如 ["langchain-ai/langchain", "openai/openai-python"]
    """
    return github.github_compare_repos(repos)


@mcp.tool()
def arxiv_search(query: str, limit: int = 10, sort: str = "relevance") -> dict:
    """搜索 arXiv 论文（标题/摘要/作者全字段匹配），研究者获取最新学术动态。

    Args:
        query: 搜索词，支持 arXiv 高级语法如 'cat:cs.AI AND all:agent'
        limit: 返回数量，默认 10，最大 50
        sort: 排序，relevance=相关度（默认）/ submittedDate=最新提交
    """
    return arxiv.arxiv_search(query, limit, sort)


@mcp.tool()
def exa_search(query: str, num_results: int = 10) -> dict:
    """Exa 英文语义搜索，适合海外技术趋势、行业报告、论文。

    Args:
        query: 用描述性语句搜索效果更好，如 "blog post comparing React and Vue performance"
        num_results: 返回数量，默认 10
    """
    return exa.exa_search(query, num_results)


# ── 数据 ─────────────────────────────────────────────────────

@mcp.tool()
def sec_company_facts(ticker: str = "", cik: str = "", metrics: list[str] | None = None, years: int = 3) -> dict:
    """查询美股公司财报（SEC EDGAR），拿营收/净利/研发支出等结构化数据。

    Args:
        ticker: 美股代码，如 AAPL（与 cik 二选一）
        cik: CIK 代码，高级参数
        metrics: 关注指标，可选 revenue / net_income / gross_profit / rd_expense / eps
        years: 返回最近 N 财年，默认 3
    """
    return sec.sec_company_facts(ticker, cik, metrics, years)


@mcp.tool()
def sec_compare_companies(tickers: list[str], metrics: list[str] | None = None, years: int = 1) -> dict:
    """对比多家美股公司同一财年的核心指标。

    Args:
        tickers: 美股代码列表，如 ["MSFT", "AAPL"]
        metrics: 关注指标，默认 revenue / net_income / rd_expense
        years: 财年数，默认 1
    """
    return sec.sec_compare_companies(tickers, metrics, years)


@mcp.tool()
def cninfo_company_profile(code: str, market: str = "ashare") -> dict:
    """查询 A股公司基本信息（东方财富公开接口）。

    Args:
        code: 股票代码，A股 6 位，如 600519
        market: 市场，ashare（默认）
    """
    return cninfo.cninfo_company_profile(code, market)


@mcp.tool()
def cninfo_financial_analysis(code: str, years: int = 3) -> dict:
    """查询 A股公司财务分析指标（ROE/净利率/营收增速/毛利率/研发占比）。

    Args:
        code: 股票代码，A股 6 位，如 002230
        years: 返回最近 N 年，默认 3
    """
    return cninfo.cninfo_financial_analysis(code, years)


@mcp.tool()
def cninfo_compare_companies(codes: list[str], years: int = 1) -> dict:
    """对比多家 A股公司最新财年核心指标。

    Args:
        codes: 股票代码列表，如 ["002230", "000063"]
        years: 财年数，默认 1
    """
    return cninfo.cninfo_compare_companies(codes, years)


# ── 提取 ─────────────────────────────────────────────────────

@mcp.tool()
def fetch_page(url: str, include_links: bool = True, max_chars: int = 8000) -> dict:
    """抓取网页正文，自动去广告/导航/侧边栏，输出干净 Markdown（trafilatura）。

    Args:
        url: 目标网页 URL
        include_links: 是否保留 Markdown 链接，默认 true
        max_chars: 最大返回字符数，默认 8000，超长截断并标注
    """
    return fetch_page.fetch_page(url, include_links, max_chars)


@mcp.tool()
def parse_pdf(url: str = "", file_path: str = "", max_pages: int = 30, extract_tables: bool = True) -> dict:
    """解析 PDF 报告为 Markdown（保留表格），本地文件或在线 URL 均可。

    Args:
        url: 在线 PDF 的 URL（与 file_path 二选一）
        file_path: 本地 PDF 路径（与 url 二选一）
        max_pages: 最大解析页数，默认 30
        extract_tables: 是否提取表格，默认 true
    """
    return pdf.parse_pdf(url, file_path, max_pages, extract_tables)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
