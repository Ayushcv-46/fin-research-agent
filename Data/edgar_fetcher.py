import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Ayush REVA University Research Project ayush@ayush4sringeri.com"}


TICKER_OVERRIDES = {
    "XOM": "0000034088"
}


def get_cik(ticker: str) -> str:
    ticker = ticker.upper()
    if ticker in TICKER_OVERRIDES:
        cik = TICKER_OVERRIDES[ticker]
        print(f"[get_cik] Found CIK for {ticker} in overrides: {cik}")
        return cik

    url = "https://www.sec.gov/files/company_tickers.json"
    print(f"[get_cik] Fetching CIK mapping from {url}")
    resp = requests.get(url, headers=HEADERS)
    print(f"[get_cik] Status code: {resp.status_code}")
    resp.raise_for_status()
    data = resp.json()

    print(f"[get_cik] Looking up ticker: {ticker}")
    for entry in data.values():
        if entry["ticker"] == ticker:
            cik = str(entry["cik_str"]).zfill(10)
            print(f"[get_cik] Found CIK for {ticker}: {cik}")
            return cik

    print(f"[get_cik] Ticker {ticker} not found in EDGAR mapping")
    raise ValueError(f"Ticker {ticker} not found in EDGAR mapping")


def get_latest_10k(cik: str) -> str:
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    print(f"[get_latest_10k] Fetching submissions for CIK {cik} from {url}")
    resp = requests.get(url, headers=HEADERS)
    print(f"[get_latest_10k] Status code: {resp.status_code}")
    resp.raise_for_status()
    data = resp.json()

    recent = data["filings"]["recent"]
    forms = recent["form"]
    accessions = recent["accessionNumber"]
    docs = recent["primaryDocument"]
    print(f"[get_latest_10k] Found {len(forms)} recent filings in metadata")

    for i, form in enumerate(forms):
        if form == "10-K":
            accession_no_dash = accessions[i].replace("-", "")
            cik_int = cik.lstrip("0")
            doc_url = (
                f"https://www.sec.gov/Archives/edgar/data/"
                f"{cik_int}/{accession_no_dash}/{docs[i]}"
            )
            print(f"[get_latest_10k] Found 10-K at index {i}. Accession: {accessions[i]}, Document: {docs[i]}")
            print(f"[get_latest_10k] Fetching filing content from {doc_url}")
            filing_resp = requests.get(doc_url, headers=HEADERS)
            print(f"[get_latest_10k] Status code: {filing_resp.status_code}")
            filing_resp.raise_for_status()
            print(f"[get_latest_10k] Successfully fetched filing text ({len(filing_resp.text)} chars)")
            return filing_resp.text

    print("[get_latest_10k] No 10-K found in recent filings")
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