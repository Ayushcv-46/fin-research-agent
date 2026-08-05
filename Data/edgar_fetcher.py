import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Ayush REVA University Research Project ayush@ayush4sringeri.com"}


def get_cik(ticker: str) -> str:
    url = "https://www.sec.gov/files/company_tickers.json"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()

    ticker = ticker.upper()
    for entry in data.values():
        if entry["ticker"] == ticker:
            return str(entry["cik_str"]).zfill(10)

    raise ValueError(f"Ticker {ticker} not found in EDGAR mapping")


def get_latest_10k(cik: str) -> str:
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()

    recent = data["filings"]["recent"]
    forms = recent["form"]
    accessions = recent["accessionNumber"]
    docs = recent["primaryDocument"]

    for i, form in enumerate(forms):
        if form == "10-K":
            accession_no_dash = accessions[i].replace("-", "")
            cik_int = cik.lstrip("0")
            doc_url = (
                f"https://www.sec.gov/Archives/edgar/data/"
                f"{cik_int}/{accession_no_dash}/{docs[i]}"
            )
            filing_resp = requests.get(doc_url, headers=HEADERS)
            filing_resp.raise_for_status()
            return filing_resp.text

    raise ValueError("No 10-K found in recent filings")


def clean_filing_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "table"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Drop XBRL/metadata junk: URLs, tag refs, or lines with no spaces
        # (real sentences always contain spaces; XBRL refs don't)
        if line.startswith("http") or " " not in line:
            continue
        lines.append(line)

    return "\n".join(lines)