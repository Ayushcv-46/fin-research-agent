const form = document.getElementById("report-form");
const submitBtn = document.getElementById("submit-btn");
const progressDiv = document.getElementById("progress");
const reportDiv = document.getElementById("report-output");
const historyList = document.getElementById("history-list");
const companySearch = document.getElementById("company-search");
const companyResults = document.getElementById("company-results");
const selectedCompany = document.getElementById("selected-company");
const API_BASE = window.location.port === "5500" ? "http://localhost:8000" : "";
let selectedCompanyData = null;
let searchTimer = null;

function escapeHtml(value) {
  if (typeof value !== "string") return value ?? "";
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

function relativeTime(iso) {
  if (!iso) return "";
  const seconds = Math.floor((Date.now() - new Date(iso)) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

async function fetchHistory() {
  try {
    const response = await fetch(`${API_BASE}/reports`);
    if (!response.ok) throw new Error("History unavailable");
    const reports = await response.json();
    if (!reports.length) { historyList.innerHTML = `<p class="sidebar-empty">No reports yet.</p>`; return; }
    historyList.innerHTML = reports.map(report => `
      <div class="history-item" data-id="${report.id}" tabindex="0" role="button">
        <div class="history-ticker">${escapeHtml(report.company_name || report.ticker)} <small>${escapeHtml(report.ticker)}</small></div>
        <div class="history-question">${escapeHtml(report.question)}</div>
        <div class="history-time">${relativeTime(report.timestamp)}</div>
      </div>`).join("");
    historyList.querySelectorAll(".history-item").forEach(item => {
      item.addEventListener("click", () => loadReport(item.dataset.id));
      item.addEventListener("keydown", event => { if (event.key === "Enter") loadReport(item.dataset.id); });
    });
  } catch {
    historyList.innerHTML = `<p class="sidebar-error">Could not load saved reports.</p>`;
  }
}

async function loadReport(id) {
  try {
    const response = await fetch(`${API_BASE}/reports/${id}`);
    if (!response.ok) throw new Error();
    const data = await response.json();
    data.judge_score = null; // Historical DB does not persist detailed quality metadata.
    progressDiv.innerHTML = "";
    renderReport(data);
  } catch { alert("Could not load this report."); }
}

function renderReport(data) {
  const report = data.final_report || "No report was generated.";
  const rendered = typeof marked !== "undefined" && marked.parse
    ? marked.parse(report)
    : `<pre>${escapeHtml(report)}</pre>`;
  const quality = data.judge_score ? `<details class="quality-details"><summary>Automated report quality checks (not an investment rating)</summary><p>Grounding ${data.judge_score.grounding ?? "—"}/10 · Evidence coverage ${data.judge_score.completeness ?? "—"}/10 · Clarity ${data.judge_score.clarity ?? "—"}/10. These fallible model checks do not assess whether an investment is suitable.</p></details>` : "";
  const warnings = (data.data_warnings || []).map(item => `<li>${escapeHtml(item)}</li>`).join("");
  reportDiv.innerHTML = `
    <div class="card report-card">
      <div class="report-header">
        <div class="report-ticker">${escapeHtml(data.company_name || data.ticker || "Company")}</div>
        <div class="report-question">${escapeHtml(data.question || "")}</div>
      </div>
      ${data.langsmith_tracing ? `<div class="trace-meta">LangSmith tracing is on for this run.${data.langsmith_trace_url ? ` <a href="${escapeHtml(data.langsmith_trace_url)}" target="_blank" rel="noopener noreferrer">Open trace</a>` : " Check the configured LangSmith project for the run."}</div>` : ""}
      <div class="report-meta">Ticker: ${escapeHtml(data.ticker || "—")} · Latest annual report filed ${escapeHtml(data.filing_metadata?.filing_date || "date unavailable")}</div>
      <div class="report-divider"></div>
      <div class="report-body"><div class="prose">${rendered}</div>${warnings ? `<div class="data-warning"><strong>Data availability</strong><ul>${warnings}</ul></div>` : ""}</div>
      ${quality}
    </div>`;
  reportDiv.scrollIntoView({ behavior: "smooth", block: "start" });
}

const stageLabels = {
  data: "Getting company filing and market information",
  retriever: "Finding relevant evidence in the annual report",
  confidence_check: "Checking whether the evidence answers your question",
  retry_retrieval: "Looking for additional evidence",
  analyst: "Preparing a plain-language explanation",
  judge: "Checking report quality",
  report: "Preparing your company summary",
};

form.addEventListener("submit", event => {
  event.preventDefault();
  if (!selectedCompanyData) { alert("Search for a company and select one of the suggestions."); companySearch.focus(); return; }
  const question = document.getElementById("question").value.trim();
  if (!question) { alert("Choose a question or type what you would like to know."); return; }
  submitBtn.disabled = true;
  submitBtn.classList.add("loading");
  progressDiv.innerHTML = "";
  reportDiv.innerHTML = "";
  const searchMode = document.getElementById("search-mode").value;
  const retrievalMode = document.getElementById("retrieval-mode").value;
  const langsmithTracing = document.getElementById("langsmith-tracing").checked;
  const params = new URLSearchParams({ ticker: selectedCompanyData.ticker, company_name: selectedCompanyData.name,
    question, judge_mode: "api", search_mode: searchMode, retrieval_mode: retrievalMode,
    langsmith_tracing: String(langsmithTracing) });
  const source = new EventSource(`${API_BASE}/report/stream?${params}`);
  source.addEventListener("stage", event => {
    const detail = JSON.parse(event.data);
    const row = document.createElement("div");
    row.className = "pipeline-step";
    row.textContent = stageLabels[detail.stage] || detail.message || detail.stage;
    progressDiv.appendChild(row);
  });
  source.addEventListener("complete", event => {
    renderReport(JSON.parse(event.data));
    fetchHistory();
    source.close();
    submitBtn.disabled = false;
    submitBtn.classList.remove("loading");
  });
  source.addEventListener("error", event => {
    if (event.data) {
      let message = "Something went wrong while preparing the company summary.";
      try { message = JSON.parse(event.data).message || message; } catch {}
      const row = document.createElement("div"); row.className = "error-step"; row.textContent = message; progressDiv.appendChild(row);
    }
    source.close();
    submitBtn.disabled = false;
    submitBtn.classList.remove("loading");
  });
});

companySearch.addEventListener("input", () => {
  selectedCompanyData = null;
  selectedCompany.textContent = "";
  const query = companySearch.value.trim();
  clearTimeout(searchTimer);
  if (query.length < 2) { companyResults.style.display = "none"; return; }
  searchTimer = setTimeout(async () => {
    try {
      const response = await fetch(`${API_BASE}/companies/search?q=${encodeURIComponent(query)}`);
      if (!response.ok) throw new Error();
      const matches = await response.json();
      companyResults.innerHTML = matches.map((company, index) => `<div class="company-option" role="option" data-index="${index}">${escapeHtml(company.name)}<small>${escapeHtml(company.ticker)}</small></div>`).join("") || `<div class="company-option">No matching companies found</div>`;
      companyResults.style.display = "block";
      companyResults.setAttribute("aria-expanded", "true");
      companyResults.querySelectorAll("[data-index]").forEach(option => option.addEventListener("click", () => {
        selectedCompanyData = matches[Number(option.dataset.index)];
        companySearch.value = selectedCompanyData.name;
        selectedCompany.textContent = `Selected: ${selectedCompanyData.name} (${selectedCompanyData.ticker})`;
        companyResults.style.display = "none";
        companyResults.setAttribute("aria-expanded", "false");
      }));
    } catch {
      companyResults.innerHTML = `<div class="company-option">Company search is temporarily unavailable.</div>`;
      companyResults.style.display = "block";
    }
  }, 250);
});

document.addEventListener("click", event => { if (!event.target.closest(".company-search")) companyResults.style.display = "none"; });

document.querySelectorAll(".question-choice").forEach(button => button.addEventListener("click", () => {
  document.querySelectorAll(".question-choice").forEach(choice => choice.classList.remove("active"));
  button.classList.add("active");
  const input = document.getElementById("question");
  if (button.dataset.question) input.value = button.dataset.question;
  else { input.value = ""; input.placeholder = "Type your question in plain language"; input.focus(); }
}));

fetchHistory();
