const form = document.getElementById("report-form");
const submitButton = form.querySelector("button[type='submit']");
const progressDiv = document.getElementById("progress");
const reportDiv = document.getElementById("report-output");
const historyList = document.getElementById("history-list");
let currentReportData = null;

// Use relative API path if served from FastAPI directly (e.g. port 8000 / Docker), or fallback to port 8000 if served via Live Server (port 5500)
const API_BASE = window.location.port === "5500" ? "http://localhost:8000" : "";

function escapeHtml(value) {
  if (typeof value !== "string") return value;
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

async function fetchHistory() {
  try {
    const res = await fetch(`${API_BASE}/reports`);
    if (!res.ok) throw new Error("Failed to fetch history");
    const reports = await res.json();
    renderHistory(reports);
  } catch (err) {
    console.error("fetchHistory error:", err);
    historyList.innerHTML = `<p class="text-sm text-red-500">Failed to load history</p>`;
  }
}

function renderHistory(reports) {
  historyList.innerHTML = "";
  if (!reports || reports.length === 0) {
    historyList.innerHTML = `<p class="text-sm text-gray-500">No recent reports.</p>`;
    return;
  }
  
  reports.forEach(r => {
    const div = document.createElement("div");
    div.className = "bg-white p-3 rounded shadow-sm border border-gray-200 cursor-pointer hover:bg-gray-50 transition-colors";
    div.innerHTML = `
      <div class="font-bold text-gray-800">${escapeHtml(r.ticker)}</div>
      <div class="text-xs text-gray-500 truncate">${escapeHtml(r.question)}</div>
      <div class="text-xs text-gray-400 mt-1">Score: ${r.overall ?? "N/A"}/10</div>
    `;
    div.addEventListener("click", () => loadReport(r.id));
    historyList.appendChild(div);
  });
}

async function loadReport(id) {
  try {
    const res = await fetch(`${API_BASE}/reports/${id}`);
    if (!res.ok) throw new Error("Failed to load report");
    const data = await res.json();
    
    data.judge_score = {
      grounding: data.grounding,
      completeness: data.completeness,
      clarity: data.clarity,
      overall: data.overall,
      flagged_issues: []
    };
    
    renderReport(data);
  } catch (err) {
    console.error("loadReport error:", err);
    alert("Could not load report.");
  }
}

function reRunJudge(ticker, question, otherMode) {
  document.getElementById("ticker").value = ticker;
  document.getElementById("question").value = question;
  document.getElementById("judge_mode").value = otherMode;
  form.dispatchEvent(new Event("submit"));
}
window.reRunJudge = reRunJudge;

function renderReport(data) {
  currentReportData = data;
  const safeTicker = escapeHtml(data.ticker);
  const safeQuestion = escapeHtml(data.question);
  
  const rawReport = data.final_report || "No report generated.";
  const reportHtml = (typeof marked !== "undefined" && marked.parse) 
    ? marked.parse(rawReport) 
    : `<pre class="whitespace-pre-wrap">${escapeHtml(rawReport)}</pre>`;
  
  const currentMode = data.judge_mode || document.getElementById("judge_mode").value;
  const otherMode = currentMode === "api" ? "finetuned" : "api";
  
  const judgeScore = data.judge_score;
  const flagged = judgeScore?.flagged_issues?.length ? judgeScore.flagged_issues.map(escapeHtml).join(", ") : "None";

  const judgeContent = judgeScore && judgeScore.overall !== -1
    ? `
      <details class="bg-gray-50 p-4 rounded border mt-4 cursor-pointer group" open>
        <summary class="font-bold text-gray-800 list-none flex justify-between items-center cursor-pointer">
          <span>Judge Transparency Panel (${escapeHtml(currentMode)} mode)</span>
          <span class="text-blue-600 group-open:hidden text-sm">Expand</span>
          <span class="text-blue-600 hidden group-open:block text-sm">Collapse</span>
        </summary>
        <div class="mt-3 text-sm space-y-2 border-t pt-3 border-gray-200">
          <div class="grid grid-cols-2 gap-4">
            <div><span class="font-semibold text-gray-600">Overall Score:</span> <span class="font-bold text-lg text-gray-900">${judgeScore.overall}/10</span></div>
            <div>
              <span class="font-semibold text-gray-600">Sub-scores:</span><br/>
              Grounding: ${judgeScore.grounding}/10<br/>
              Completeness: ${judgeScore.completeness}/10<br/>
              Clarity: ${judgeScore.clarity}/10
            </div>
          </div>
          <div><span class="font-semibold text-red-600">Flagged Issues:</span> ${flagged}</div>
          <div class="mt-4 text-right">
            <button id="rerun-judge-btn" type="button" class="text-xs bg-blue-100 hover:bg-blue-200 text-blue-800 font-medium px-3 py-1.5 rounded transition">
              Re-run with ${otherMode} judge
            </button>
          </div>
        </div>
      </details>
    `
    : `<div class="bg-yellow-50 text-yellow-800 p-3 rounded text-sm font-medium mt-4">Judge unavailable</div>`;

  reportDiv.innerHTML = `
    <div class="bg-white p-6 rounded shadow space-y-4">
      <div class="border-b pb-3">
        <h2 class="text-2xl font-bold text-gray-900">${safeTicker} Research Report</h2>
        <p class="text-sm text-gray-500">${safeQuestion}</p>
      </div>

      <div class="prose max-w-none text-sm text-gray-800 font-sans">
        ${reportHtml}
      </div>

      ${judgeContent}
    </div>
  `;

  const rerunBtn = document.getElementById("rerun-judge-btn");
  if (rerunBtn) {
    rerunBtn.addEventListener("click", () => {
      reRunJudge(data.ticker, data.question, otherMode);
    });
  }
}

form.addEventListener("submit", function (event) {
  event.preventDefault();

  const tickerInput = document.getElementById("ticker");
  const questionInput = document.getElementById("question");
  const judgeModeInput = document.getElementById("judge_mode");

  const ticker = (tickerInput.value.trim() || tickerInput.placeholder).toUpperCase();
  const question = questionInput.value.trim() || questionInput.placeholder;
  const judgeMode = judgeModeInput.value;

  if (!ticker) {
    alert("Please enter a valid ticker.");
    return;
  }

  // Update inputs if placeholder was used
  tickerInput.value = ticker;
  questionInput.value = question;

  // Disable button while running
  submitButton.disabled = true;
  submitButton.classList.add("opacity-50", "cursor-not-allowed");

  // Clear previous outputs
  progressDiv.innerHTML = "";
  reportDiv.innerHTML = "";

  const url = `${API_BASE}/report/stream?ticker=${encodeURIComponent(ticker)}&question=${encodeURIComponent(question)}&judge_mode=${encodeURIComponent(judgeMode)}`;
  const eventSource = new EventSource(url);

  eventSource.addEventListener("stage", function (event) {
    const data = JSON.parse(event.data);
    const line = document.createElement("div");
    line.className = "text-sm text-gray-700 bg-white px-3 py-2 rounded shadow-sm border-l-4 border-blue-500";
    line.textContent = `${data.stage.toUpperCase()}: ${data.message}`;
    progressDiv.appendChild(line);
  });

  eventSource.addEventListener("complete", function (event) {
    const data = JSON.parse(event.data);
    data.judge_mode = judgeMode;
    renderReport(data);
    fetchHistory();
    eventSource.close();
    submitButton.disabled = false;
    submitButton.classList.remove("opacity-50", "cursor-not-allowed");
  });

  eventSource.addEventListener("error", function (event) {
    if (!event.data) {
      console.error(event);
      return;
    }

    let message = "Could not reach server or an error occurred during research.";
    try {
      const parsed = JSON.parse(event.data);
      if (parsed.message) message = parsed.message;
    } catch (e) {
      // fallback
    }

    const line = document.createElement("div");
    line.className = "text-sm text-red-700 bg-red-50 px-3 py-2 rounded border border-red-200";
    line.textContent = message;
    progressDiv.appendChild(line);

    eventSource.close();
    submitButton.disabled = false;
    submitButton.classList.remove("opacity-50", "cursor-not-allowed");
  });
});

// Load history on initial page load
fetchHistory();