const form        = document.getElementById("report-form");
const submitBtn   = document.getElementById("submit-btn");
const progressDiv = document.getElementById("progress");
const reportDiv   = document.getElementById("report-output");
const historyList = document.getElementById("history-list");
let currentReportData = null;

// API base: empty string when served from FastAPI/Docker (port 8000), explicit when using Live Server (port 5500)
const API_BASE = window.location.port === "5500" ? "http://localhost:8000" : "";

// ---- Judge mode helper ----
function getJudgeMode() {
  const checked = document.querySelector('input[name="judge_mode"]:checked');
  return checked ? checked.value : "api";
}

// ---- Utility ----
function escapeHtml(value) {
  if (typeof value !== "string") return value;
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function relativeTime(iso) {
  if (!iso) return "";
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000);
  if (diff < 60)  return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function scoreClass(v) {
  if (v == null || v === -1) return "score-na";
  if (v >= 8)  return "score-hi";
  if (v >= 5)  return "score-mid";
  return "score-lo";
}

function scoreLabel(v) {
  if (v == null || v === -1) return "N/A";
  return `${v}/10`;
}

// ---- History ----
async function fetchHistory() {
  try {
    const res = await fetch(`${API_BASE}/reports`);
    if (!res.ok) throw new Error();
    renderHistory(await res.json());
  } catch {
    historyList.innerHTML = `<p class="sidebar-error">Failed to load history.</p>`;
  }
}

function renderHistory(reports) {
  if (!reports || reports.length === 0) {
    historyList.innerHTML = `<p class="sidebar-empty">No reports yet.</p>`;
    return;
  }
  historyList.innerHTML = reports.map(r => `
    <div class="history-item" data-id="${r.id}" tabindex="0" role="button">
      <div class="history-item-top">
        <span class="history-ticker">${escapeHtml(r.ticker)}</span>
        <span class="history-score ${scoreClass(r.overall)}">${scoreLabel(r.overall)}</span>
      </div>
      <div class="history-question">${escapeHtml(r.question)}</div>
      <div class="history-time">${relativeTime(r.timestamp)}</div>
    </div>
  `).join("");

  historyList.querySelectorAll(".history-item").forEach(el => {
    el.addEventListener("click",  () => loadReport(el.dataset.id));
    el.addEventListener("keydown", e => { if (e.key === "Enter") loadReport(el.dataset.id); });
  });
}

// ---- Load saved report ----
async function loadReport(id) {
  try {
    const res = await fetch(`${API_BASE}/reports/${id}`);
    if (!res.ok) throw new Error();
    const data = await res.json();
    data.judge_score = {
      grounding:    data.grounding,
      completeness: data.completeness,
      clarity:      data.clarity,
      overall:      data.overall,
      flagged_issues: []
    };
    progressDiv.innerHTML = "";
    renderReport(data);
  } catch {
    alert("Could not load report.");
  }
}

// ---- Re-run with alternate judge ----
function reRunJudge(ticker, question, mode) {
  document.getElementById("ticker").value   = ticker;
  document.getElementById("question").value = question;
  const radio = document.querySelector(`input[name="judge_mode"][value="${mode}"]`);
  if (radio) radio.checked = true;
  form.dispatchEvent(new Event("submit"));
}
window.reRunJudge = reRunJudge;

// ---- Render score bar ----
function scoreBar(label, value) {
  const pct  = value != null && value !== -1 ? (value / 10) * 100 : 0;
  const cls  = value >= 8 ? "high" : value >= 5 ? "mid" : "low";
  const text = value != null && value !== -1 ? `${value}/10` : "—";
  return `
    <div class="score-bar-row">
      <span class="score-bar-label">${label}</span>
      <div class="score-bar-track">
        <div class="score-bar-fill ${cls}" style="width:${pct}%"></div>
      </div>
      <span class="score-bar-value">${text}</span>
    </div>`;
}

// ---- Render full report ----
function renderReport(data) {
  currentReportData = data;
  const safeTicker   = escapeHtml(data.ticker   || "—");
  const safeQuestion = escapeHtml(data.question || "");
  const currentMode  = data.judge_mode || getJudgeMode();
  const otherMode    = currentMode === "api" ? "finetuned" : "api";

  const rawReport  = data.final_report || "No report generated.";
  const reportHtml = (typeof marked !== "undefined" && marked.parse)
    ? marked.parse(rawReport)
    : `<pre style="white-space:pre-wrap">${escapeHtml(rawReport)}</pre>`;

  // Metric cards
  const price   = data.price_data?.current_price    ?? null;
  const hi52    = data.price_data?.fifty_two_week_high ?? null;
  const lo52    = data.price_data?.fifty_two_week_low  ?? null;
  const pe      = data.fundamentals?.pe_ratio         ?? null;
  const mktcap  = data.fundamentals?.market_cap        ?? null;

  const fmt = v => v != null ? v : "—";
  const fmtPrice = v => v != null ? `$${Number(v).toLocaleString()}` : "—";

  const metricsHtml = `
    <div class="metric-grid">
      <div class="metric-cell">
        <div class="metric-label">Price</div>
        <div class="metric-value">${fmtPrice(price)}</div>
      </div>
      <div class="metric-cell">
        <div class="metric-label">52W High</div>
        <div class="metric-value">${fmtPrice(hi52)}</div>
      </div>
      <div class="metric-cell">
        <div class="metric-label">52W Low</div>
        <div class="metric-value">${fmtPrice(lo52)}</div>
      </div>
      <div class="metric-cell">
        <div class="metric-label">P/E Ratio</div>
        <div class="metric-value">${fmt(pe)}</div>
        <div class="metric-sub">${mktcap ? `Cap: ${mktcap}` : ""}</div>
      </div>
    </div>`;

  // Judge panel
  const judgeScore = data.judge_score;
  const hasScores  = judgeScore && judgeScore.overall != null && judgeScore.overall !== -1;

  const judgeHtml = hasScores ? `
    <div class="judge-section">
      <div class="judge-title">Quality Assessment — ${escapeHtml(currentMode)} judge</div>
      <div class="overall-score">
        <span class="overall-score-num">${judgeScore.overall}</span>
        <span class="overall-score-denom">/10</span>
        <span class="overall-score-label">Overall Score</span>
      </div>
      ${scoreBar("Grounding",    judgeScore.grounding)}
      ${scoreBar("Completeness", judgeScore.completeness)}
      ${scoreBar("Clarity",      judgeScore.clarity)}
      <button id="rerun-judge-btn" class="btn-rerun" type="button">
        Re-run with ${otherMode} judge
      </button>
    </div>` :
    `<div class="judge-section"><div class="judge-unavailable">Judge evaluation unavailable for this report.</div></div>`;

  reportDiv.innerHTML = `
    <div class="card report-card">
      <div class="report-header">
        <div class="report-ticker">${safeTicker}</div>
        <div class="report-question">${safeQuestion}</div>
      </div>
      ${metricsHtml}
      <div class="report-divider"></div>
      <div class="report-body">
        <div class="prose">${reportHtml}</div>
      </div>
      ${judgeHtml}
    </div>`;

  const rerunBtn = document.getElementById("rerun-judge-btn");
  if (rerunBtn) rerunBtn.addEventListener("click", () => reRunJudge(data.ticker, data.question, otherMode));

  reportDiv.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ---- Pipeline stage label map ----
const STAGE_LABELS = {
  data:             "Fetching SEC filing & market data",
  retriever:        "Searching vector store for relevant chunks",
  confidence_check: "Evaluating retrieval confidence",
  retry_retrieval:  "Retrying retrieval with refined query",
  analyst:          "Synthesizing financial analysis",
  judge:            "Running judge evaluation",
  report:           "Formatting final report",
};

// ---- Form submit ----
form.addEventListener("submit", function (e) {
  e.preventDefault();

  const tickerInput    = document.getElementById("ticker");
  const questionInput  = document.getElementById("question");

  const ticker   = (tickerInput.value.trim()   || tickerInput.placeholder).toUpperCase();
  const question = (questionInput.value.trim()  || questionInput.placeholder);
  const judgeMode = getJudgeMode();

  if (!ticker) { alert("Please enter a valid ticker symbol."); return; }

  tickerInput.value  = ticker;
  questionInput.value = question;

  // UI: loading state
  submitBtn.disabled = true;
  submitBtn.classList.add("loading");
  progressDiv.innerHTML = "";
  reportDiv.innerHTML   = "";

  const url = `${API_BASE}/report/stream?ticker=${encodeURIComponent(ticker)}&question=${encodeURIComponent(question)}&judge_mode=${encodeURIComponent(judgeMode)}`;
  const eventSource = new EventSource(url);

  eventSource.addEventListener("stage", function (event) {
    const d     = JSON.parse(event.data);
    const label = STAGE_LABELS[d.stage] || d.message || d.stage;
    const step  = document.createElement("div");
    step.className = "pipeline-step";
    step.innerHTML = `
      <div class="pipeline-step-icon">
        <svg fill="none" viewBox="0 0 10 10" stroke="#2563eb" stroke-width="1.8">
          <polyline points="1,6 4,9 9,2"/>
        </svg>
      </div>
      <span class="pipeline-step-label">${escapeHtml(label)}</span>`;
    progressDiv.appendChild(step);
  });

  eventSource.addEventListener("complete", function (event) {
    const d = JSON.parse(event.data);
    d.judge_mode = judgeMode;
    renderReport(d);
    fetchHistory();
    eventSource.close();
    submitBtn.disabled = false;
    submitBtn.classList.remove("loading");
  });

  eventSource.addEventListener("error", function (event) {
    if (!event.data) { console.error(event); return; }
    let message = "An error occurred during analysis. Please try again.";
    try { const p = JSON.parse(event.data); if (p.message) message = p.message; } catch {}
    const errDiv = document.createElement("div");
    errDiv.className = "error-step";
    errDiv.textContent = message;
    progressDiv.appendChild(errDiv);
    eventSource.close();
    submitBtn.disabled = false;
    submitBtn.classList.remove("loading");
  });
});

// ---- Init ----
fetchHistory();