if __name__ == "__main__":
    t = yf.Ticker("TSLA")
    print("Current price:", t.info.get("currentPrice"))
    print(t.financials.head())