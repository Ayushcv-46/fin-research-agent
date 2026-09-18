const form = document.getElementById("report-form");
const progressDiv = document.getElementById("progress");
const reportDiv = document.getElementById("report-output");

form.addEventListener("submit", function (event) {
  event.preventDefault();

  const ticker = document.getElementById("ticker").value;
  const question = document.getElementById("question").value;
  const judgeMode = document.getElementById("judge_mode").value;

  // clear anything from a previous run
  progressDiv.innerHTML = "";
  reportDiv.innerHTML = "";

  const url = `http://localhost:8000/report/stream?ticker=${encodeURIComponent(ticker)}&question=${encodeURIComponent(question)}&judge_mode=${encodeURIComponent(judgeMode)}`;
  const eventSource = new EventSource(url);

  eventSource.addEventListener("stage", function (event) {
    const data = JSON.parse(event.data);
    const line = document.createElement("div");
    line.className = "text-sm text-gray-700 bg-white px-3 py-2 rounded shadow-sm";
    line.textContent = `${data.stage}: ${data.message}`;
    progressDiv.appendChild(line);
  });

  eventSource.addEventListener("complete", function (event) {
    const data = JSON.parse(event.data);
    reportDiv.innerHTML = `
      <div class="bg-white p-4 rounded shadow">
        <h2 class="font-bold mb-2">Report ready</h2>
        <pre class="text-xs whitespace-pre-wrap">${JSON.stringify(data, null, 2)}</pre>
      </div>
    `;
    eventSource.close(); // stop listening, the run is done
  });

  eventSource.addEventListener("error", function (event) {
    const line = document.createElement("div");
    line.className = "text-sm text-red-700 bg-red-50 px-3 py-2 rounded";
    line.textContent = "Something went wrong during the run.";
    progressDiv.appendChild(line);
    eventSource.close();
  });
});