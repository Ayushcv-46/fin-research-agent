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
    resp = requests.get(url, headers=HEADERS, timeout=30)
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


def get_latest_10k_record(cik: str) -> dict:
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    print(f"[get_latest_10k] Fetching submissions for CIK {cik} from {url}")
    resp = requests.get(url, headers=HEADERS, timeout=30)
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
            filing_resp = requests.get(doc_url, headers=HEADERS, timeout=30)
            print(f"[get_latest_10k] Status code: {filing_resp.status_code}")
            filing_resp.raise_for_status()
            print(f"[get_latest_10k] Successfully fetched filing text ({len(filing_resp.text)} chars)")
            filing_dates = recent.get("filingDate", [])
            report_dates = recent.get("reportDate", [])
            return {
                "html": filing_resp.text,
                "accession_number": accessions[i],
                "filing_date": filing_dates[i] if i < len(filing_dates) else None,
                "report_date": report_dates[i] if i < len(report_dates) else None,
                "form": form,
                "url": doc_url,
            }

    print("[get_latest_10k] No 10-K found in recent filings")
    raise ValueError("No 10-K found in recent filings")


def get_latest_10k(cik: str) -> str:
    """Return the latest 10-K HTML for compatibility with existing callers."""
    return get_latest_10k_record(cik)["html"]


def clean_filing_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    # Preserve financial statement data by flattening tables to readable rows.
    for table in soup.find_all("table"):
        rows = []
        for row in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
            if any(cells):
                rows.append(" | ".join(cells))
        table.replace_with(soup.new_string("\n" + "\n".join(rows) + "\n"))

    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("http"):
            continue
        lines.append(line)

    return "\n".join(lines)
