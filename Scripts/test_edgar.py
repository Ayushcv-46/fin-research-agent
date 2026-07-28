import requests

headers = {"User-Agent": "Ayush C V ayush4sringeri@gmail.com"}

# Step A: look up Apple's CIK using EDGAR's ticker-to-CIK mapping file
mapping = requests.get(
    "https://www.sec.gov/files/company_tickers.json", headers=headers
).json()

apple_cik = None
for entry in mapping.values():
    if entry["ticker"] == "AAPL":
        apple_cik = str(entry["cik_str"]).zfill(10)  # EDGAR wants 10-digit, zero-padded
        break

print("Apple CIK:", apple_cik)

# Step B: fetch Apple's filing history using that CIK
filings = requests.get(
    f"https://data.sec.gov/submissions/CIK{apple_cik}.json", headers=headers
).json()

print("Company name:", filings["name"])
print("Most recent form filed:", filings["filings"]["recent"]["form"][0])