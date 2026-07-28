import yfinance as yf

t = yf.Ticker("TSLA")
print("Current price:", t.info.get("currentPrice"))
print(t.financials.head())