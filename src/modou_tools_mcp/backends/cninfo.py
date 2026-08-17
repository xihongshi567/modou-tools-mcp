"""A股/H股上市公司财报 — AkShare 封装东方财富公开接口，国内直连，需重试"""
from __future__ import annotations

import time
from typing import Any

import requests

TIMEOUT = 30
RETRIES = 3


def _retry(fn, *args, **kwargs):
    """东方财富接口偶发 Connection aborted，重试 3 次 + 30s 超时"""
    last_err: Exception | None = None
    for attempt in range(RETRIES):
        try:
            return fn(*args, **kwargs)
        except requests.RequestException as e:
            last_err = e
            time.sleep(1 * (attempt + 1))
    raise last_err or RuntimeError("未知错误")


def _df_rows(df) -> list[dict]:
    """DataFrame → 行 dict 列表（按日期倒序，最新在前）"""
    if df is None or df.empty:
        return []
    try:
        df = df.sort_values(by=df.columns[0], ascending=False)
    except Exception:
        pass
    return df.head(20).to_dict("records")


def cninfo_company_profile(code: str, market: str = "ashare") -> dict[str, Any]:
    """查询 A股/H股公司基本信息"""
    try:
        import akshare as ak

        if market == "hshare":
            return {"ok": False, "error": "H股公司信息接口暂未验证", "detail": "可用 market=ashare"}
        df = _retry(ak.stock_individual_info_em, symbol=code)
        if df is None or df.empty:
            return {"ok": False, "error": f"未找到代码 {code} 的公司信息"}
        kv = dict(zip(df["item"], df["value"]))
        return {
            "ok": True,
            "action": "company_profile",
            "code": code,
            "name": kv.get("股票简称", ""),
            "profile": {
                "industry": kv.get("行业", ""),
                "province": kv.get("省份", ""),
                "listing_date": kv.get("上市时间", ""),
                "total_market_cap": kv.get("总市值", ""),
                "total_shares": kv.get("总股本", ""),
            },
            "source_url": f"https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?code={code}",
        }
    except ImportError:
        return {"ok": False, "error": "akshare 未安装", "detail": "pip install akshare"}
    except Exception as e:
        return {
            "ok": False,
            "error": "东方财富接口连接失败（重试3次后仍超时）",
            "detail": str(e)[:200],
        }


def cninfo_financial_analysis(code: str, years: int = 3) -> dict[str, Any]:
    """查询 A股公司财务分析指标（ROE/净利率/营收增速/毛利率/研发占比）"""
    try:
        import akshare as ak

        df = _retry(ak.stock_financial_analysis_indicator, symbol=code)
        rows = _df_rows(df)[: max(years, 1)]
        indicators = {
            "roe": [],
            "net_profit_margin": [],
            "revenue_growth": [],
            "gross_margin": [],
            "rd_ratio": [],
        }
        periods = []
        for row in rows:
            periods.append(str(row.get("日期", ""))[:10])
            indicators["roe"].append(row.get("净资产收益率(%)"))
            indicators["net_profit_margin"].append(row.get("销售净利率(%)"))
            indicators["revenue_growth"].append(row.get("净利润增长率(%)"))
            indicators["gross_margin"].append(row.get("销售毛利率(%)"))
            indicators["rd_ratio"].append(row.get("研发费用占营业收入比例(%)"))

        name = rows[0].get("股票简称", code) if rows else code
        return {
            "ok": True,
            "action": "financial_analysis",
            "code": code,
            "name": name,
            "periods": periods,
            "indicators": indicators,
            "source_url": f"https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?code={code}",
        }
    except ImportError:
        return {"ok": False, "error": "akshare 未安装", "detail": "pip install akshare"}
    except Exception as e:
        return {
            "ok": False,
            "error": "东方财富接口连接失败（重试3次后仍超时）",
            "detail": str(e)[:200],
        }


def cninfo_compare_companies(codes: list[str], years: int = 1) -> dict[str, Any]:
    """对比多家 A股公司最新财年的核心指标"""
    result: dict[str, Any] = {"ok": True, "action": "compare_companies", "results": []}
    for code in codes:
        r = cninfo_financial_analysis(code, years=years)
        if not r["ok"]:
            result["results"].append({"code": code, "ok": False, "error": r["error"]})
            continue
        ind = r["indicators"]
        result["results"].append({
            "code": code,
            "name": r["name"],
            "period": r["periods"][0] if r["periods"] else "",
            "roe": ind["roe"][0] if ind["roe"] else None,
            "net_profit_margin": ind["net_profit_margin"][0] if ind["net_profit_margin"] else None,
            "revenue_growth": ind["revenue_growth"][0] if ind["revenue_growth"] else None,
            "gross_margin": ind["gross_margin"][0] if ind["gross_margin"] else None,
            "rd_ratio": ind["rd_ratio"][0] if ind["rd_ratio"] else None,
            "source_url": r["source_url"],
        })
    return result
