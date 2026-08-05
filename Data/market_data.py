# data/market_data.py

import yfinance as yf
import time


def get_price_snapshot(ticker: str) -> dict:
    """
    Returns current price, 52-week high/low, and volume for a ticker.
    Returns a dict with None values (not a crash) if data is missing.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        return {
            "ticker": ticker,
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "volume": info.get("volume"),
            "error": None,
        }
    except Exception as e:
        return {
            "ticker": ticker,
            "current_price": None,
            "fifty_two_week_high": None,
            "fifty_two_week_low": None,
            "volume": None,
            "error": str(e),
        }


def get_fundamentals(ticker: str) -> dict:
    """
    Returns key fundamentals: P/E ratio, market cap, revenue, EPS.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        return {
            "ticker": ticker,
            "pe_ratio": info.get("trailingPE"),
            "market_cap": info.get("marketCap"),
            "revenue": info.get("totalRevenue"),
            "eps": info.get("trailingEps"),
            "error": None,
        }
    except Exception as e:
        return {
            "ticker": ticker,
            "pe_ratio": None,
            "market_cap": None,
            "revenue": None,
            "eps": None,
            "error": str(e),
        }


if __name__ == "__main__":
    # quick manual test — run: python data/market_data.py
    test_tickers = ["AAPL", "TSLA", "INFY", "ZZZFAKE123", "RELIANCE.NS"]

    for t in test_tickers:
        print(f"\n--- {t} ---")
        print("Price snapshot:", get_price_snapshot(t))
        time.sleep(1)  # small delay to avoid rate-limiting
        print("Fundamentals:", get_fundamentals(t))
        time.sleep(1)