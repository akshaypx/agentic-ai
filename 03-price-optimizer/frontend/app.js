const form = document.getElementById("search-form");
const queryInput = document.getElementById("query");
const imageUrlInput = document.getElementById("image-url");
const runStatus = document.getElementById("run-status");
const stepsEl = document.getElementById("steps");
const resultsBody = document.getElementById("results-body");
const tableFilter = document.getElementById("table-filter");
const recommendationEl = document.getElementById("recommendation");
const avgPriceEl = document.getElementById("avg-price");
const minPriceEl = document.getElementById("min-price");
const maxPriceEl = document.getElementById("max-price");
const totalRankedEl = document.getElementById("total-ranked");

let rankedProducts = [];

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  resetView();
  runStatus.textContent = "Running";

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: queryInput.value.trim(),
        image_url: imageUrlInput.value.trim() || null,
      }),
    });

    if (!response.ok || !response.body) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.trim()) {
          continue;
        }
        const eventPayload = JSON.parse(line);
        handleEvent(eventPayload);
      }
    }
  } catch (error) {
    appendStep({
      stage: "frontend",
      status: "error",
      message: error.message || "Failed to start workflow.",
      details: {},
    });
    runStatus.textContent = "Error";
  }
});

tableFilter.addEventListener("input", () => renderTable());

function handleEvent(eventPayload) {
  const { type, data } = eventPayload;

  if (type === "workflow_started") {
    appendStep({
      stage: "workflow",
      status: "started",
      message: `Started workflow for "${data.query}".`,
      details: {},
    });
    return;
  }

  if (type === "step") {
    appendStep(data);
    return;
  }

  if (type === "workflow_completed") {
    rankedProducts = data.ranked_products || [];
    renderRecommendation(data.recommendation);
    renderStats(data.stats, rankedProducts.length);
    renderTable();
    runStatus.textContent = "Completed";
    return;
  }

  if (type === "error") {
    appendStep({
      stage: "workflow",
      status: "error",
      message: data.message,
      details: {},
    });
    runStatus.textContent = "Error";
  }
}

function appendStep(step) {
  if (!stepsEl.querySelector(".step")) {
    stepsEl.innerHTML = "";
  }

  const div = document.createElement("div");
  div.className = `step ${step.status}`;

  const details = Object.entries(step.details || {})
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .slice(0, 3)
    .map(([key, value]) => `${key}: ${value}`)
    .join(" · ");

  div.innerHTML = `
    <strong>${humanize(step.stage)} · ${humanize(step.status)}</strong>
    <div>${step.message}</div>
    <small>${details}</small>
  `;

  stepsEl.prepend(div);
}

function renderRecommendation(recommendation) {
  if (!recommendation) {
    recommendationEl.className = "recommendation empty";
    recommendationEl.textContent = "No recommendation returned.";
    return;
  }

  recommendationEl.className = "recommendation";
  recommendationEl.innerHTML = `
    <h3>${recommendation.recommended_product_title || "Recommendation ready"}</h3>
    <div class="price">${formatCurrency(recommendation.recommended_price)}</div>
    <p>${recommendation.reasoning || ""}</p>
    <small>${recommendation.summary || ""}</small>
  `;
}

function renderStats(stats, totalRanked) {
  avgPriceEl.textContent = formatCurrency(stats?.avg_price);
  minPriceEl.textContent = formatCurrency(stats?.min_price);
  maxPriceEl.textContent = formatCurrency(stats?.max_price);
  totalRankedEl.textContent = String(totalRanked);
}

function renderTable() {
  const filter = tableFilter.value.trim().toLowerCase();
  const filtered = rankedProducts.filter((item) => {
    const haystack = [
      item.title,
      item.source,
      item.source_type,
      ...(item.reasons || []),
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(filter);
  });

  if (!filtered.length) {
    resultsBody.innerHTML = `<tr><td colspan="8" class="empty-row">No products match the current filter.</td></tr>`;
    return;
  }

  resultsBody.innerHTML = filtered
    .sort((a, b) => (b.confidence || 0) - (a.confidence || 0))
    .map((item) => `
      <tr>
        <td>${item.rank}</td>
        <td class="product-cell">
          ${item.link ? `<a href="${item.link}" target="_blank" rel="noreferrer">${item.title}</a>` : item.title}
        </td>
        <td>${item.source || "-"}</td>
        <td>${humanize(item.source_type)}</td>
        <td>${item.price || formatCurrency(item.extracted_price)}</td>
        <td><span class="score-badge">${formatScore(item.confidence)}</span></td>
        <td><span class="score-badge">${formatScore(item.weightage)}</span></td>
        <td>${(item.reasons || []).join(", ")}</td>
      </tr>
    `)
    .join("");
}

function resetView() {
  rankedProducts = [];
  stepsEl.innerHTML = "";
  resultsBody.innerHTML = `<tr><td colspan="8" class="empty-row">No results yet.</td></tr>`;
  recommendationEl.className = "recommendation empty";
  recommendationEl.textContent = "Run a query to generate the final recommendation.";
  renderStats({}, 0);
}

function humanize(value) {
  return String(value || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function formatCurrency(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "-";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(Number(value));
}

function formatScore(value) {
  if (value === null || value === undefined) {
    return "-";
  }
  return Number(value).toFixed(2);
}
