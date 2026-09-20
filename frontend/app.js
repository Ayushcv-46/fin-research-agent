const form = document.getElementById("report-form");
const submitButton = form.querySelector("button[type='submit']");
const progressDiv = document.getElementById("progress");
const reportDiv = document.getElementById("report-output");

function escapeHtml(value) {
  if (typeof value !== "string") return value;
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function renderReport(data) {
  const safeTicker = escapeHtml(data.ticker);
  const safeQuestion = escapeHtml(data.question);
  const safeReport = escapeHtml(data.final_report) || "No report generated.";
  
  const judgeContent = data.judge_score
    ? `
      <div class="bg-gray-50 p-3 rounded text-sm space-y-1">
        <div><span class="font-semibold">Overall:</span> ${data.judge_score.overall ?? "N/A"}/10</div>
        <div><span class="font-semibold">Grounding:</span> ${data.judge_score.grounding ?? "N/A"}/10 | <span class="font-semibold">Completeness:</span> ${data.judge_score.completeness ?? "N/A"}/10 | <span class="font-semibold">Clarity:</span> ${data.judge_score.clarity ?? "N/A"}/10</div>
        <div><span class="font-semibold">Flagged Issues:</span> ${data.judge_score.flagged_issues && data.judge_score.flagged_issues.length ? data.judge_score.flagged_issues.map(escapeHtml).join(", ") : "None"}</div>
      </div>
    `
    : `<div class="bg-yellow-50 text-yellow-800 p-3 rounded text-sm font-medium">Judge unavailable</div>`;

  reportDiv.innerHTML = `
    <div class="bg-white p-6 rounded shadow space-y-4">
      <div class="border-b pb-3">
        <h2 class="text-xl font-bold text-gray-900">${safeTicker} Research Report</h2>
        <p class="text-sm text-gray-500">${safeQuestion}</p>
      </div>

      <div class="prose max-w-none text-sm text-gray-800 whitespace-pre-wrap font-sans">
        ${safeReport}
      </div>

      <div class="pt-4 border-t">
        <h3 class="text-sm font-bold text-gray-700 uppercase tracking-wide mb-2">Quality & Transparency Panel</h3>
        ${judgeContent}
      </div>
    </div>
  `;
}

form.addEventListener("submit", function (event) {
  event.preventDefault();

  const ticker = document.getElementById("ticker").value.trim().toUpperCase();
  const question = document.getElementById("question").value.trim();
  const judgeMode = document.getElementById("judge_mode").value;

  if (!ticker) {
    alert("Please enter a valid ticker.");
    return;
  }

  // Disable button while running
  submitButton.disabled = true;
  submitButton.classList.add("opacity-50", "cursor-not-allowed");

  // Clear previous outputs
  progressDiv.innerHTML = "";
  reportDiv.innerHTML = "";

  const url = `http://localhost:8000/report/stream?ticker=${encodeURIComponent(ticker)}&question=${encodeURIComponent(question)}&judge_mode=${encodeURIComponent(judgeMode)}`;
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
    renderReport(data);
    eventSource.close();
    submitButton.disabled = false;
    submitButton.classList.remove("opacity-50", "cursor-not-allowed");
  });

  eventSource.addEventListener("error", function (event) {
    let message = "Could not reach server or an error occurred during research.";
    try {
      if (event.data) {
        const parsed = JSON.parse(event.data);
        if (parsed.message) message = parsed.message;
      }
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