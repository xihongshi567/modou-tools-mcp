"""美股上市公司财报 — SEC EDGAR API（data.sec.gov），免费无速率限制，国内可用但较慢"""
from __future__ import annotations

import json
from typing import Any

import requests

UA = {"User-Agent": "modou-tools-mcp/0.1 (material-collector; contact@modou.local)"}
TIMEOUT = 30

# XBRL tag 映射（us-gaap）
_TAGS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax",
                "RevenueFromContractWithCustomerIncludingAssessedTax",
                "SalesRevenueNet", "Revenues"],
    "net_income": ["NetIncomeLoss"],
    "gross_profit": ["GrossProfit"],
    "rd_expense": ["ResearchAndDevelopmentExpense"],
    "eps": ["EarningsPerShareBasic"],
}


def _get(url: str) -> dict | None:
    r = requests.get(url, headers=UA, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _lookup_cik(ticker: str) -> str | None:
    """ticker → CIK（10 位补零），来自 SEC 公开映射文件"""
    try:
        data = _get("https://www.sec.gov/files/company_tickers.json")
        for entry in data.values():
            if entry["ticker"].upper() == ticker.upper():
                return str(entry["cik_str"]).zfill(10)
    except Exception:
        pass
    return None


def _annual_series(data: dict, tag: str) -> dict[str, float]:
    """从 companyfacts 提取最近财年数值序列 {年份: 值}"""
    units = data.get("facts", {}).get("us-gaap", {}).get(tag, {}).get("units", {})
    series: dict[str, float] = {}
    for unit, entries in units.items():
        if unit != "USD":
            continue
        for e in entries:
            # 只取年度 10-K 数据（fp=FY），忽略季度
            if e.get("form") != "10-K" or e.get("fp") != "FY":
                continue
            end = e.get("end", "")
            if len(end) != 10 or not end.startswith("12-31"):
                continue
            year = end[:4]
            val = e.get("val")
            if isinstance(val, (int, float)) and year not in series:
                series[year] = float(val)
    return dict(sorted(series.items()))


def _facts_for(ticker: str, cik: str | None, metrics: list[str], years: int) -> dict:
    if cik is None:
        cik = _lookup_cik(ticker)
        if not cik:
            raise ValueError(
                f"未找到 ticker={ticker} 对应的 CIK，请检查拼写或用 cik 参数直接传入"
            )

    raw = _get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json")
    name = raw.get("entityName", "")
    indicators: dict[str, dict] = {}
    for m in metrics:
        series: dict[str, float] = {}
        for tag in _TAGS.get(m, []):
            series = _annual_series(raw, tag)
            if series:
                break
        indicators[m] = series

    return {
        "ticker": ticker,
        "cik": cik,
        "name": name,
        "indicators": {m: dict(list(s.items())[-years:]) for m, s in indicators.items()},
        "source_url": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
    }


def sec_company_facts(
    ticker: str = "",
    cik: str = "",
    metrics: list[str] | None = None,
    years: int = 3,
) -> dict[str, Any]:
    """查询美股公司结构化财报数据（营收/净利/毛利/研发/每股收益）"""
    metrics = metrics or ["revenue", "net_income", "gross_profit", "rd_expense", "eps"]
    if not ticker and not cik:
        return {"ok": False, "error": "缺少参数", "detail": "ticker 与 cik 至少提供其一"}
    try:
        facts = _facts_for(ticker.upper(), cik or None, metrics, years)
        return {"ok": True, "action": "company_facts", **facts}
    except requests.RequestException as e:
        return {"ok": False, "error": "SEC EDGAR 请求失败", "detail": str(e)}
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": "解析失败", "detail": str(e)}


def sec_compare_companies(
    tickers: list[str],
    metrics: list[str] | None = None,
    years: int = 1,
) -> dict[str, Any]:
    """对比多家美股公司同一财年的核心指标"""
    metrics = metrics or ["revenue", "net_income", "rd_expense"]
    result: dict[str, Any] = {"ok": True, "action": "compare_companies", "results": []}
    for t in tickers:
        try:
            facts = _facts_for(t.upper(), None, metrics, years)
            row = {"ticker": facts["ticker"], "name": facts["name"]}
            for m in metrics:
                series = facts["indicators"][m]
                row[m] = series.get(max(series.keys())) if series else None
            row["source_url"] = facts["source_url"]
            result["results"].append(row)
        except Exception as e:
            result["results"].append({"ticker": t, "ok": False, "error": str(e)})
    return result
