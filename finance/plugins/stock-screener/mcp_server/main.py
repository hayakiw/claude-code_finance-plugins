#!/usr/bin/env python3
"""
Financial Data MCP Server
中長期投資分析のための財務データ取得MCPサーバー（Yahoo Finance使用）

使用方法:
  pip install -r requirements.txt
  python main.py

ティッカー例:
  日本株: 7203.T（トヨタ）, 9984.T（ソフトバンクG）, 6758.T（ソニー）
  米国株: AAPL, MSFT, GOOGL
"""

import asyncio
import json
import sys
from typing import Any

try:
    import yfinance as yf
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types
except ImportError as e:
    print(f"Error: Missing dependency — {e}", file=sys.stderr)
    print("Run: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

app = Server("financial-data")


# ─────────────────────────────────────────────
# ツール定義
# ─────────────────────────────────────────────

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_stock_fundamentals",
            description=(
                "銘柄のファンダメンタルズデータを取得します。"
                "ROE・ROIC・営業利益率・自己資本比率・ネットキャッシュ・"
                "EPS成長率・PER・PBR・配当利回りなどを返します。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": (
                            "銘柄コード。"
                            "日本株は末尾に .T を付ける（例: 7203.T）、"
                            "米国株はそのまま（例: AAPL）"
                        )
                    }
                },
                "required": ["ticker"]
            }
        ),
        types.Tool(
            name="screen_stocks",
            description=(
                "複数銘柄のファンダメンタルズを一括取得してスクリーニング用データを返します。"
                "最大20銘柄まで同時処理可能です。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tickers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "銘柄コードのリスト（最大20件）",
                        "maxItems": 20
                    }
                },
                "required": ["tickers"]
            }
        ),
        types.Tool(
            name="get_price_history",
            description="銘柄の株価履歴と52週高値・安値を取得します。",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "銘柄コード"
                    },
                    "period": {
                        "type": "string",
                        "description": "取得期間: 1mo / 3mo / 6mo / 1y / 2y / 5y",
                        "default": "1y"
                    }
                },
                "required": ["ticker"]
            }
        )
    ]


# ─────────────────────────────────────────────
# ツール実行
# ─────────────────────────────────────────────

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "get_stock_fundamentals":
        return await _get_fundamentals(arguments["ticker"])
    elif name == "screen_stocks":
        return await _screen_stocks(arguments["tickers"])
    elif name == "get_price_history":
        return await _get_price_history(
            arguments["ticker"],
            arguments.get("period", "1y")
        )
    else:
        raise ValueError(f"Unknown tool: {name}")


# ─────────────────────────────────────────────
# 実装
# ─────────────────────────────────────────────

def _pct(value: Any) -> Any:
    """小数をパーセント表記に変換（Noneはそのまま）"""
    if value is None:
        return None
    return round(value * 100, 2)


def _round2(value: Any) -> Any:
    if value is None:
        return None
    return round(value, 2)


def _億円(value: Any) -> Any:
    """円→億円変換（Noneはそのまま）"""
    if value is None:
        return None
    return round(value / 1e8, 1)


async def _get_fundamentals(ticker: str) -> list[types.TextContent]:
    """単一銘柄のファンダメンタルズを取得"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        if not info or info.get("regularMarketPrice") is None:
            return [types.TextContent(
                type="text",
                text=json.dumps(
                    {"error": f"銘柄 '{ticker}' のデータが見つかりません。ティッカーコードを確認してください。"},
                    ensure_ascii=False
                )
            )]

        # ── 収益性指標 ──────────────────────────
        roe = _pct(info.get("returnOnEquity"))
        # ROICはyfinanceに直接フィールドがないため近似値（NOPAT/投下資本）は難しく、
        # returnOnCapital または returnOnAssets で代替
        roic = _pct(info.get("returnOnCapital") or info.get("returnOnAssets"))
        operating_margin = _pct(info.get("operatingMargins"))
        gross_margin = _pct(info.get("grossMargins"))
        profit_margin = _pct(info.get("profitMargins"))

        # ── 財務健全性 ───────────────────────────
        total_assets = info.get("totalAssets")
        total_equity = info.get("totalStockholderEquity") or info.get("bookValue")
        equity_ratio = None
        if total_assets and total_equity:
            equity_ratio = round(total_equity / total_assets * 100, 2)

        total_cash = info.get("totalCash") or 0
        total_debt = info.get("totalDebt") or 0
        net_cash_億 = _億円(total_cash - total_debt)

        # 有利子負債倍率（D/E Ratio）
        de_ratio = None
        if total_equity and total_equity > 0 and total_debt:
            de_ratio = _round2(total_debt / total_equity)

        # 営業CF
        operating_cf = None
        try:
            cf = stock.cashflow
            if cf is not None and not cf.empty:
                ocf_row = cf.loc["Total Cash From Operating Activities"] if "Total Cash From Operating Activities" in cf.index else None
                if ocf_row is not None:
                    operating_cf = _億円(ocf_row.iloc[0])
        except Exception:
            pass

        # ── 成長性 ────────────────────────────────
        revenue_growth = _pct(info.get("revenueGrowth"))
        earnings_growth = _pct(info.get("earningsGrowth"))
        earnings_quarterly_growth = _pct(info.get("earningsQuarterlyGrowth"))

        # ── バリュエーション ─────────────────────
        per = _round2(info.get("trailingPE") or info.get("forwardPE"))
        forward_per = _round2(info.get("forwardPE"))
        pbr = _round2(info.get("priceToBook"))
        ev_ebitda = _round2(info.get("enterpriseToEbitda"))
        peg_ratio = _round2(info.get("pegRatio"))
        dividend_yield = _pct(info.get("dividendYield"))
        payout_ratio = _pct(info.get("payoutRatio"))

        result = {
            "ticker": ticker,
            "company_name": info.get("longName") or info.get("shortName", ticker),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "currency": info.get("currency", "N/A"),
            "current_price": info.get("regularMarketPrice"),
            "market_cap_億円": _億円(info.get("marketCap")),

            "【収益性】": {
                "ROE（%）": roe,
                "ROIC近似（%）": roic,
                "営業利益率（%）": operating_margin,
                "粗利率（%）": gross_margin,
                "純利益率（%）": profit_margin,
            },

            "【財務健全性】": {
                "自己資本比率（%）": equity_ratio,
                "ネットキャッシュ（億円）": net_cash_億,
                "有利子負債倍率（倍）": de_ratio,
                "営業CF直近期（億円）": operating_cf,
                "総負債（億円）": _億円(total_debt) if total_debt else None,
                "現預金（億円）": _億円(total_cash) if total_cash else None,
            },

            "【成長性（直近）】": {
                "売上高成長率YoY（%）": revenue_growth,
                "EPS成長率YoY（%）": earnings_growth,
                "EPS成長率（四半期）（%）": earnings_quarterly_growth,
            },

            "【バリュエーション】": {
                "PER（実績倍）": per,
                "PER（予想倍）": forward_per,
                "PBR（倍）": pbr,
                "EV/EBITDA（倍）": ev_ebitda,
                "PEGレシオ": peg_ratio,
                "配当利回り（%）": dividend_yield,
                "配当性向（%）": payout_ratio,
            },

            "【参考】": {
                "52週高値": info.get("fiftyTwoWeekHigh"),
                "52週安値": info.get("fiftyTwoWeekLow"),
                "目標株価（アナリスト中央値）": info.get("targetMedianPrice"),
            }
        }

        return [types.TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, indent=2)
        )]

    except Exception as e:
        return [types.TextContent(
            type="text",
            text=json.dumps(
                {"error": str(e), "ticker": ticker},
                ensure_ascii=False
            )
        )]


async def _screen_stocks(tickers: list[str]) -> list[types.TextContent]:
    """複数銘柄の主要指標を一括取得"""
    results = []
    for ticker in tickers[:20]:  # 最大20件
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            if not info or not info.get("regularMarketPrice"):
                results.append({"ticker": ticker, "error": "データなし"})
                continue

            roe = _pct(info.get("returnOnEquity"))
            op_margin = _pct(info.get("operatingMargins"))
            per = _round2(info.get("trailingPE") or info.get("forwardPE"))
            pbr = _round2(info.get("priceToBook"))
            revenue_growth = _pct(info.get("revenueGrowth"))
            earnings_growth = _pct(info.get("earningsGrowth"))
            div_yield = _pct(info.get("dividendYield"))

            total_assets = info.get("totalAssets")
            total_equity = info.get("totalStockholderEquity")
            equity_ratio = None
            if total_assets and total_equity:
                equity_ratio = round(total_equity / total_assets * 100, 2)

            results.append({
                "ticker": ticker,
                "company_name": info.get("longName") or info.get("shortName", ticker),
                "sector": info.get("sector", "N/A"),
                "ROE（%）": roe,
                "営業利益率（%）": op_margin,
                "自己資本比率（%）": equity_ratio,
                "売上高成長率（%）": revenue_growth,
                "EPS成長率（%）": earnings_growth,
                "PER（倍）": per,
                "PBR（倍）": pbr,
                "配当利回り（%）": div_yield,
            })
        except Exception as e:
            results.append({"ticker": ticker, "error": str(e)})

    return [types.TextContent(
        type="text",
        text=json.dumps(results, ensure_ascii=False, indent=2)
    )]


async def _get_price_history(ticker: str, period: str = "1y") -> list[types.TextContent]:
    """株価履歴を取得"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)

        if hist.empty:
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": f"株価データなし: {ticker}"}, ensure_ascii=False)
            )]

        result = {
            "ticker": ticker,
            "period": period,
            "start_date": str(hist.index[0].date()),
            "end_date": str(hist.index[-1].date()),
            "latest_close": round(float(hist["Close"].iloc[-1]), 2),
            "period_high": round(float(hist["High"].max()), 2),
            "period_low": round(float(hist["Low"].min()), 2),
            "period_return_pct": round(
                (float(hist["Close"].iloc[-1]) / float(hist["Close"].iloc[0]) - 1) * 100, 2
            ),
            "avg_volume": int(hist["Volume"].mean()),
        }

        return [types.TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, indent=2)
        )]

    except Exception as e:
        return [types.TextContent(
            type="text",
            text=json.dumps({"error": str(e), "ticker": ticker}, ensure_ascii=False)
        )]


# ─────────────────────────────────────────────
# エントリーポイント
# ─────────────────────────────────────────────

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
