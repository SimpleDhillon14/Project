/* =========================================================================
   Chemical Reaction Kinetics Analyzer — Frontend Application Logic
   Talks to the Flask backend defined in js/config.js (API_CONFIG.BASE_URL)
   ========================================================================= */

const API = API_CONFIG.BASE_URL.replace(/\/$/, "");

const METHOD_INFO = {
  integral: {
    label: "Integral Method",
    equation: "-r_A = -dC_A/dt = k·C_A^n",
    text: "Assumes an order n, integrates the rate law, linearizes it, and tests a sweep of candidate orders (0 to 3, then a fine sweep around the best) to find the order that gives the best physically meaningful linear fit.",
    columns: ["time", "concentration"],
  },
  differential: {
    label: "Differential Method",
    equation: "ln(-r_A) = ln(k) + n·ln(C_A)",
    text: "Numerically differentiates C_A vs t to obtain -dC_A/dt at each point, then fits ln(-r_A) vs ln(C_A) — the slope is a continuous (possibly fractional) reaction order n, and the intercept gives ln(k). A guess-and-test comparison table is also shown.",
    columns: ["time", "concentration"],
  },
  autocatalytic: {
    label: "Autocatalytic Reaction",
    equation: "A + B → 2B,   -r_A = k·C_A·C_B",
    text: "The product B accelerates its own formation. Since C_A + C_B is conserved, ln(C_B/C_A) is linear in time with slope k·C_T, giving the rate constant k.",
    columns: ["time", "concentration_a", "concentration_b"],
  },
  reversible: {
    label: "Reversible Reaction",
    equation: "A ⇌ B,   -r_A = kf·C_A - kr·C_B",
    text: "Starting from pure A, ln[(C_A - C_Ae)/(C_A0 - C_Ae)] is linear in time with slope -(kf + kr). Combined with the equilibrium constant K = kf/kr = (C_A0 - C_Ae)/C_Ae, both kf and kr are solved individually.",
    columns: ["time", "concentration"],
  },
  irreversible: {
    label: "Irreversible Reaction",
    equation: "-r_A = k·C_A^n",
    text: "Analyzes irreversible concentration-time data using either the Integral Method (test every order transparently) or the Differential Method (continuous fractional order from log-log regression). Choose the mode below.",
    columns: ["time", "concentration"],
  },
};

const state = {
  method: "integral",
  rows: makeEmptyRows(6),
  lastResult: null,
};

function makeEmptyRows(n) {
  const rows = [];
  for (let i = 0; i < n; i++) rows.push({ t: "", c: "", cb: "" });
  return rows;
}

/* ---------------------------- DOM references ---------------------------- */
const methodSelect = document.getElementById("method-select");
const methodDescription = document.getElementById("method-description");
const tableHead = document.getElementById("data-table-head");
const tableBody = document.getElementById("data-table-body");
const addRowBtn = document.getElementById("add-row-btn");
const clearRowsBtn = document.getElementById("clear-rows-btn");
const csvInput = document.getElementById("csv-input");
const csvStatus = document.getElementById("csv-status");
const analyzeBtn = document.getElementById("analyze-btn");
const loadingEl = document.getElementById("loading");
const errorBox = document.getElementById("error-box");
const resultsEl = document.getElementById("results");
const irreversibleModeWrapper = document.getElementById("irreversible-mode-wrapper");
const reversibleExtra = document.getElementById("reversible-extra");

/* ------------------------------- Tabs ------------------------------- */
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
  });
});

/* --------------------------- Method selection --------------------------- */
methodSelect.addEventListener("change", () => {
  state.method = methodSelect.value;
  updateMethodUI();
});

function updateMethodUI() {
  const info = METHOD_INFO[state.method];
  methodDescription.innerHTML =
    `<strong>Assumed reaction / rate law:</strong> <span class="equation">${info.equation}</span><br>${info.text}`;

  irreversibleModeWrapper.classList.toggle("hidden", state.method !== "irreversible");
  reversibleExtra.classList.toggle("hidden", state.method !== "reversible");

  clearError();
  resultsEl.classList.add("hidden");
  resultsEl.innerHTML = "";
  renderTable();
}

/* ------------------------------ Data table ------------------------------ */
function renderTable() {
  const info = METHOD_INFO[state.method];
  const cols = info.columns;

  const headerLabels = {
    time: "Time",
    concentration: "Concentration (C_A)",
    concentration_a: "Concentration A",
    concentration_b: "Concentration B",
  };

  tableHead.innerHTML =
    "<tr>" + cols.map((c) => `<th>${headerLabels[c]}</th>`).join("") + "<th>Action</th></tr>";

  tableBody.innerHTML = "";
  state.rows.forEach((row, idx) => {
    const tr = document.createElement("tr");
    cols.forEach((col) => {
      const td = document.createElement("td");
      const input = document.createElement("input");
      input.type = "text";
      input.placeholder = "0";
      input.value = colValue(row, col);
      input.addEventListener("input", (e) => setColValue(row, col, e.target.value));
      td.appendChild(input);
      tr.appendChild(td);
    });
    const actionTd = document.createElement("td");
    const delBtn = document.createElement("button");
    delBtn.className = "btn danger-outline small";
    delBtn.textContent = "Remove";
    delBtn.addEventListener("click", () => {
      state.rows.splice(idx, 1);
      renderTable();
    });
    actionTd.appendChild(delBtn);
    tr.appendChild(actionTd);
    tableBody.appendChild(tr);
  });
}

function colValue(row, col) {
  if (col === "time") return row.t;
  if (col === "concentration" || col === "concentration_a") return col === "concentration" ? row.c : row.c;
  if (col === "concentration_b") return row.cb;
  return "";
}
function setColValue(row, col, value) {
  if (col === "time") row.t = value;
  else if (col === "concentration" || col === "concentration_a") row.c = value;
  else if (col === "concentration_b") row.cb = value;
}

addRowBtn.addEventListener("click", () => {
  state.rows.push({ t: "", c: "", cb: "" });
  renderTable();
});
clearRowsBtn.addEventListener("click", () => {
  state.rows = makeEmptyRows(6);
  renderTable();
});

/* ------------------------------ CSV upload ------------------------------ */
csvInput.addEventListener("change", () => {
  const file = csvInput.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const parsed = parseCSV(reader.result);
      applyCSVData(parsed);
      csvStatus.textContent = `Loaded ${parsed.rows.length} rows from ${file.name}.`;
      csvStatus.style.color = "var(--accent)";
    } catch (e) {
      csvStatus.textContent = "Error: " + e.message;
      csvStatus.style.color = "var(--danger)";
    }
  };
  reader.readAsText(file);
});

function parseCSV(text) {
  const lines = text.split(/\r?\n/).map((l) => l.trim()).filter((l) => l.length > 0);
  if (lines.length < 2) throw new Error("CSV must contain a header row and at least one data row.");
  const headers = lines[0].split(",").map((h) => h.trim().toLowerCase());
  const rows = lines.slice(1).map((line) => line.split(",").map((v) => v.trim()));
  return { headers, rows };
}

function applyCSVData(parsed) {
  const { headers, rows } = parsed;
  const info = METHOD_INFO[state.method];

  const colIndex = {};
  if (state.method === "autocatalytic") {
    colIndex.time = findHeader(headers, ["time", "t"]);
    colIndex.concentration_a = findHeader(headers, ["concentrationa", "concentration_a", "ca", "concentrationof a"]);
    colIndex.concentration_b = findHeader(headers, ["concentrationb", "concentration_b", "cb"]);
    if (colIndex.time === -1 || colIndex.concentration_a === -1 || colIndex.concentration_b === -1) {
      throw new Error("CSV must contain Time, ConcentrationA and ConcentrationB columns.");
    }
    state.rows = rows.map((r) => ({
      t: r[colIndex.time] ?? "",
      c: r[colIndex.concentration_a] ?? "",
      cb: r[colIndex.concentration_b] ?? "",
    }));
  } else {
    colIndex.time = findHeader(headers, ["time", "t"]);
    colIndex.concentration = findHeader(headers, ["concentration", "c", "ca", "concentration_a"]);
    if (colIndex.time === -1 || colIndex.concentration === -1) {
      throw new Error("CSV must contain Time and Concentration columns.");
    }
    state.rows = rows.map((r) => ({
      t: r[colIndex.time] ?? "",
      c: r[colIndex.concentration] ?? "",
      cb: "",
    }));
  }
  renderTable();
  document.querySelector('.tab-btn[data-tab="manual"]').click();
}

function findHeader(headers, candidates) {
  for (const c of candidates) {
    const idx = headers.findIndex((h) => h.replace(/\s+/g, "") === c);
    if (idx !== -1) return idx;
  }
  return -1;
}

/* ------------------------------- Analyze -------------------------------- */
analyzeBtn.addEventListener("click", runAnalysis);

function clearError() {
  errorBox.classList.add("hidden");
  errorBox.textContent = "";
}
function showError(msg) {
  errorBox.textContent = msg;
  errorBox.classList.remove("hidden");
}

async function runAnalysis() {
  clearError();
  resultsEl.classList.add("hidden");
  resultsEl.innerHTML = "";

  const method = state.method;
  const payload = buildPayload(method);
  if (payload.error) {
    showError(payload.error);
    return;
  }

  loadingEl.classList.remove("hidden");
  analyzeBtn.disabled = true;

  try {
    const endpoint = `${API}/api/analyze/${method}`;
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload.body),
    });
    const data = await res.json();
    if (!res.ok) {
      showError(data.error || "Analysis failed.");
      return;
    }
    state.lastResult = { method, data };
    renderResults(method, data);
  } catch (e) {
    showError(
      "Could not reach the backend API. Check that API_CONFIG.BASE_URL in js/config.js " +
      "points to your running backend, and that the backend is deployed/awake. (" + e.message + ")"
    );
  } finally {
    loadingEl.classList.add("hidden");
    analyzeBtn.disabled = false;
  }
}

function buildPayload(method) {
  if (method === "autocatalytic") {
    const t = [], ca = [], cb = [];
    for (const row of state.rows) {
      if (row.t === "" && row.c === "" && row.cb === "") continue;
      t.push(row.t);
      ca.push(row.c);
      cb.push(row.cb);
    }
    if (t.length < 3) return { error: "Please enter at least three complete rows of data." };
    return { body: { time: numArr(t), concentration_a: numArr(ca), concentration_b: numArr(cb) } };
  }

  const t = [], c = [];
  for (const row of state.rows) {
    if (row.t === "" && row.c === "") continue;
    t.push(row.t);
    c.push(row.c);
  }
  if (t.length < 3) return { error: "Please enter at least three complete rows of data." };

  const body = { time: numArr(t), concentration: numArr(c) };

  if (method === "irreversible") {
    body.mode = document.getElementById("irreversible-mode").value;
  }
  if (method === "reversible") {
    const ca0 = document.getElementById("rev-ca0").value;
    const cae = document.getElementById("rev-cae").value;
    if (ca0 !== "") body.C_A0 = parseFloat(ca0);
    if (cae !== "") body.C_Ae = parseFloat(cae);
  }

  return { body };
}

function numArr(arr) {
  return arr.map((v) => (v === "" ? null : parseFloat(v)));
}

/* ------------------------------- Rendering ------------------------------- */
function el(tag, className, html) {
  const e = document.createElement("div");
  e.className = className || "";
  if (html !== undefined) e.innerHTML = html;
  e.tagNameOverride = tag;
  return e;
}

function section(title) {
  const wrap = document.createElement("div");
  wrap.className = "result-section";
  const h3 = document.createElement("h3");
  h3.textContent = title;
  wrap.appendChild(h3);
  return wrap;
}

function fmt(n, digits = 5) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  if (typeof n !== "number") return String(n);
  return n.toPrecision(digits).replace(/\.?0+$/, (m) => (m.includes(".") ? "" : m));
}

let plotCounter = 0;
function nextPlotId() {
  plotCounter += 1;
  return "plot-" + plotCounter;
}

function renderResults(method, data) {
  resultsEl.classList.remove("hidden");
  resultsEl.innerHTML = "";

  // 1. Input data
  const s1 = section("1. Input Data");
  s1.appendChild(buildOriginalDataTable(method, data));
  resultsEl.appendChild(s1);

  // 2 & 3: Method + original equation
  const s2 = section("2 & 3. Selected Method & Kinetic Equation");
  const info = METHOD_INFO[method];
  const box = document.createElement("div");
  box.className = "method-description";
  box.innerHTML = `<strong>${info.label}</strong><br><span class="equation">${info.equation}</span>`;
  s2.appendChild(box);
  resultsEl.appendChild(s2);

  if (method === "integral" || (method === "irreversible" && data.analysis_mode !== "differential")) {
    renderIntegralStyleResults(data);
  } else if (method === "differential" || (method === "irreversible" && data.analysis_mode === "differential")) {
    renderDifferentialResults(data);
  } else if (method === "autocatalytic") {
    renderSingleTransformResult(data, "Autocatalytic Reaction Analysis");
  } else if (method === "reversible") {
    renderReversibleResults(data);
  }

  // Prediction calculator (only when we have n, k, C0)
  const n = data.reaction_order;
  const k = data.rate_constant;
  const c0 = data.initial_concentration ?? data.C_A0;
  if (typeof n === "number" && typeof k === "number" && typeof c0 === "number") {
    resultsEl.appendChild(buildPredictionCalculator(n, k, c0));
  }

  resultsEl.scrollIntoView({ behavior: "smooth", block: "start" });
}

function buildOriginalDataTable(method, data) {
  const wrap = document.createElement("div");
  wrap.className = "comparison-table-wrapper";
  const table = document.createElement("table");
  if (method === "autocatalytic") {
    const rows = data.original_data || [];
    table.innerHTML =
      "<tr><th>Time</th><th>C_A</th><th>C_B</th></tr>" +
      rows.map((r) => `<tr><td>${fmt(r.time)}</td><td>${fmt(r.concentration_a)}</td><td>${fmt(r.concentration_b)}</td></tr>`).join("");
  } else {
    const rows = data.original_data || [];
    table.innerHTML =
      "<tr><th>Time</th><th>Concentration (C_A)</th></tr>" +
      rows.map((r) => `<tr><td>${fmt(r.time)}</td><td>${fmt(r.concentration)}</td></tr>`).join("");
  }
  wrap.appendChild(table);
  return wrap;
}

/* ----------------------- Integral / Irreversible (integral mode) ----------------------- */
function renderIntegralStyleResults(data) {
  // 4. Reaction order testing
  const s4 = section("4. Reaction Order Testing Process (Coarse Sweep)");
  s4.appendChild(buildOrderGrid(data.coarse_results, data.final_best));
  resultsEl.appendChild(s4);

  const s4b = section("Fractional Order Refinement (Fine Sweep Around Best Order)");
  s4b.appendChild(buildOrderGrid(data.refine_results, data.final_best));
  resultsEl.appendChild(s4b);

  // 5. Comparison table
  const s5 = section("5. Order Comparison Table");
  s5.appendChild(buildComparisonTable([...data.coarse_results, ...data.refine_results]));
  resultsEl.appendChild(s5);

  // 6. Graphical analysis for the final best order
  const s6 = section("6. Graphical Analysis — Final Selected Order");
  const best = data.final_best;
  const plotId = nextPlotId();
  const div = document.createElement("div");
  div.className = "graph-container";
  div.id = plotId;
  s6.appendChild(div);
  resultsEl.appendChild(s6);
  setTimeout(() => plotRegression(plotId, best.transformed_x, best.transformed_y, best.slope, best.intercept, best.x_label, best.y_label, `Order n = ${fmt(best.order,4)} — R² = ${fmt(best.r_squared,4)}`), 0);

  if (data.nearest_integer_note) {
    const note = document.createElement("div");
    note.className = "note-box";
    note.textContent = data.nearest_integer_note;
    resultsEl.appendChild(note);
  }

  // 7-9 final results
  resultsEl.appendChild(buildFinalResultsSection(data));
}

function buildOrderGrid(results, best) {
  const grid = document.createElement("div");
  grid.className = "order-grid";
  results.forEach((r) => {
    const isBest = best && r.order === best.order && r.slope === best.slope;
    const card = document.createElement("div");
    card.className = "order-card " + (isBest ? "best" : "rejected");

    const errorLine = r.error ? `<div class="reason-list">Error: ${r.error}</div>` : "";
    const reasons = (r.reasons || []).map((x) => `<li>${x}</li>`).join("");

    card.innerHTML = `
      <h4>Order n = ${fmt(r.order, 4)}</h4>
      <div class="eq">${r.equation || ""}</div>
      ${r.error ? errorLine : `
      <table>
        <tr><td><strong>Slope</strong></td><td>${fmt(r.slope)}</td></tr>
        <tr><td><strong>Intercept</strong></td><td>${fmt(r.intercept)}</td></tr>
        <tr><td><strong>R²</strong></td><td>${fmt(r.r_squared, 5)}</td></tr>
        <tr><td><strong>k</strong></td><td>${fmt(r.k)}</td></tr>
        <tr><td><strong>C_A0</strong></td><td>${fmt(r.c0)}</td></tr>
      </table>
      <span class="badge ${isBest ? "accept" : "reject"}">${isBest ? "✅ Best candidate" : "❌ " + (r.decision || "Rejected")}</span>
      ${reasons ? `<ul class="reason-list">${reasons}</ul>` : ""}
      <button class="btn secondary small view-graph-btn">View Graph</button>
      `}
    `;

    if (!r.error) {
      const graphDiv = document.createElement("div");
      graphDiv.className = "graph-container hidden";
      const gid = nextPlotId();
      graphDiv.id = gid;
      card.appendChild(graphDiv);
      const btn = card.querySelector(".view-graph-btn");
      btn.addEventListener("click", () => {
        graphDiv.classList.toggle("hidden");
        if (!graphDiv.classList.contains("hidden") && !graphDiv.dataset.plotted) {
          plotRegression(gid, r.transformed_x, r.transformed_y, r.slope, r.intercept, r.x_label, r.y_label, `n = ${fmt(r.order,4)}`);
          graphDiv.dataset.plotted = "1";
        }
      });
    }

    grid.appendChild(card);
  });
  return grid;
}

function buildComparisonTable(results) {
  const wrap = document.createElement("div");
  wrap.className = "comparison-table-wrapper";
  const table = document.createElement("table");
  table.innerHTML =
    "<tr><th>Order</th><th>Transformation</th><th>Slope</th><th>Intercept</th><th>k</th><th>C₀</th><th>R²</th><th>Decision</th></tr>" +
    results
      .map(
        (r) => `<tr>
          <td>${fmt(r.order, 4)}</td>
          <td>${r.y_label || "—"} vs ${r.x_label || "t"}</td>
          <td>${fmt(r.slope)}</td>
          <td>${fmt(r.intercept)}</td>
          <td>${fmt(r.k)}</td>
          <td>${fmt(r.c0)}</td>
          <td>${fmt(r.r_squared, 5)}</td>
          <td>${r.decision || (r.error ? "Error" : "—")}</td>
        </tr>`
      )
      .join("");
  wrap.appendChild(table);
  return wrap;
}

function buildFinalResultsSection(data) {
  const wrap = document.createElement("div");
  wrap.className = "result-section";
  wrap.innerHTML = `<h3>7, 8 &amp; 9. Regression Results, Final Kinetic Parameters &amp; Rate Equation</h3>`;

  const grid = document.createElement("div");
  grid.className = "param-grid";
  const best = data.final_best || {};
  const items = [
    ["Selected Order (n)", fmt(data.reaction_order, 4)],
    ["Rate Constant (k)", fmt(data.rate_constant)],
    ["Initial Conc. (C_A0)", fmt(data.initial_concentration)],
    ["R²", fmt(best.r_squared, 5)],
    ["Slope", fmt(best.slope)],
    ["Intercept", fmt(best.intercept)],
  ];
  items.forEach(([label, value]) => {
    const box = document.createElement("div");
    box.className = "param-box";
    box.innerHTML = `<div class="value">${value}</div><div class="label">${label}</div>`;
    grid.appendChild(box);
  });
  wrap.appendChild(grid);

  const eqBox = document.createElement("div");
  eqBox.className = "final-eq-box";
  eqBox.textContent = "Final Rate Equation:  " + (data.final_rate_equation || "—");
  wrap.appendChild(eqBox);

  return wrap;
}

/* ----------------------------- Differential ----------------------------- */
function renderDifferentialResults(data) {
  const s4 = section("4. Numerical Differentiation (Forward / Central / Backward)");
  s4.appendChild(buildDerivativeTable(data.derivative_table));
  resultsEl.appendChild(s4);

  const s5 = section("5 & 6. Data Transformation & Graphical Analysis");
  const plotId = nextPlotId();
  const div = document.createElement("div");
  div.className = "graph-container";
  div.id = plotId;
  s5.appendChild(div);
  resultsEl.appendChild(s5);
  setTimeout(() => plotRegression(plotId, data.transformed_x, data.transformed_y, data.slope, data.intercept, data.x_label, data.y_label, `Continuous order n = ${fmt(data.reaction_order,4)}`), 0);

  if (data.guess_and_test && data.guess_and_test.length) {
    const s5b = section("Guess-and-Test Comparison (Fixed Candidate Orders)");
    s5b.appendChild(buildOrderGrid(data.guess_and_test, data.guess_and_test_best));
    resultsEl.appendChild(s5b);
  }

  resultsEl.appendChild(buildFinalResultsSection({
    reaction_order: data.reaction_order,
    rate_constant: data.rate_constant,
    initial_concentration: data.initial_concentration,
    final_rate_equation: data.final_rate_equation,
    final_best: { r_squared: data.r_squared, slope: data.slope, intercept: data.intercept },
  }));
}

function buildDerivativeTable(rows) {
  const wrap = document.createElement("div");
  wrap.className = "comparison-table-wrapper";
  const table = document.createElement("table");
  table.innerHTML =
    "<tr><th>Time</th><th>Concentration</th><th>dC/dt</th><th>-dC/dt (rate)</th></tr>" +
    (rows || [])
      .map((r) => `<tr><td>${fmt(r.time)}</td><td>${fmt(r.concentration)}</td><td>${fmt(r.dC_dt)}</td><td>${fmt(r.neg_dC_dt)}</td></tr>`)
      .join("");
  wrap.appendChild(table);
  return wrap;
}

/* --------------------- Autocatalytic (single transform) --------------------- */
function renderSingleTransformResult(data, title) {
  const s = section(title);
  if (data.assumption_note) {
    const note = document.createElement("div");
    note.className = "note-box";
    note.textContent = data.assumption_note;
    s.appendChild(note);
  }
  const plotId = nextPlotId();
  const div = document.createElement("div");
  div.className = "graph-container";
  div.id = plotId;
  s.appendChild(div);
  resultsEl.appendChild(s);
  setTimeout(() => plotRegression(plotId, data.transformed_x, data.transformed_y, data.slope, data.intercept, data.x_label, data.y_label, `R² = ${fmt(data.r_squared,4)}`), 0);

  const grid = document.createElement("div");
  grid.className = "param-grid";
  const items = [
    ["Slope", fmt(data.slope)],
    ["Intercept", fmt(data.intercept)],
    ["R²", fmt(data.r_squared, 5)],
    ["Rate Constant (k)", fmt(data.rate_constant)],
    ["Total Conc. (C_T)", fmt(data.total_concentration)],
  ];
  items.forEach(([label, value]) => {
    const box = document.createElement("div");
    box.className = "param-box";
    box.innerHTML = `<div class="value">${value}</div><div class="label">${label}</div>`;
    grid.appendChild(box);
  });
  resultsEl.appendChild(grid);

  const eqBox = document.createElement("div");
  eqBox.className = "final-eq-box";
  eqBox.textContent = "Final Rate Equation:  " + (data.final_rate_equation || "—");
  resultsEl.appendChild(eqBox);
}

/* ------------------------------- Reversible ------------------------------- */
function renderReversibleResults(data) {
  const s = section("Reversible Reaction Analysis");
  const plotId = nextPlotId();
  const div = document.createElement("div");
  div.className = "graph-container";
  div.id = plotId;
  s.appendChild(div);
  resultsEl.appendChild(s);
  setTimeout(() => plotRegression(plotId, data.transformed_x, data.transformed_y, data.slope, data.intercept, data.x_label, data.y_label, `R² = ${fmt(data.r_squared,4)}`), 0);

  const grid = document.createElement("div");
  grid.className = "param-grid";
  const items = [
    ["Slope", fmt(data.slope)],
    ["Intercept", fmt(data.intercept)],
    ["R²", fmt(data.r_squared, 5)],
    ["Forward k (kf)", fmt(data.forward_rate_constant)],
    ["Reverse k (kr)", fmt(data.reverse_rate_constant)],
    ["Equilibrium K", fmt(data.equilibrium_constant)],
    ["C_A0", fmt(data.C_A0)],
    ["C_Ae", fmt(data.C_Ae)],
  ];
  items.forEach(([label, value]) => {
    const box = document.createElement("div");
    box.className = "param-box";
    box.innerHTML = `<div class="value">${value}</div><div class="label">${label}</div>`;
    grid.appendChild(box);
  });
  resultsEl.appendChild(grid);

  const eqBox = document.createElement("div");
  eqBox.className = "final-eq-box";
  eqBox.textContent = "Final Rate Equation:  " + (data.final_rate_equation || "—");
  resultsEl.appendChild(eqBox);
}

/* -------------------------------- Plotly -------------------------------- */
function plotRegression(divId, x, y, slope, intercept, xLabel, yLabel, title) {
  if (!x || !y || x.length === 0) return;
  const container = document.getElementById(divId);
  if (typeof Plotly === "undefined") {
    if (container) {
      container.innerHTML =
        '<div class="note-box">Graph library (Plotly) could not be loaded from the CDN — check your internet connection. ' +
        "Numeric slope/intercept/R\u00b2 values above are still valid.</div>";
    }
    return;
  }
  try {
    plotRegressionInner(divId, x, y, slope, intercept, xLabel, yLabel, title);
  } catch (e) {
    if (container) container.innerHTML = '<div class="note-box">Could not render graph: ' + e.message + "</div>";
  }
}

function plotRegressionInner(divId, x, y, slope, intercept, xLabel, yLabel, title) {
  const xMin = Math.min(...x);
  const xMax = Math.max(...x);
  const lineX = [xMin, xMax];
  const lineY = lineX.map((xv) => slope * xv + intercept);

  const traceScatter = {
    x, y,
    mode: "markers",
    type: "scatter",
    name: "Experimental data",
    marker: { color: "#1e5f8c", size: 9 },
  };
  const traceLine = {
    x: lineX, y: lineY,
    mode: "lines",
    type: "scatter",
    name: `Best fit: y = ${fmt(slope,4)}x + ${fmt(intercept,4)}`,
    line: { color: "#2f9e73", width: 2 },
  };

  const layout = {
    title: title || "",
    xaxis: { title: xLabel || "x" },
    yaxis: { title: yLabel || "y" },
    margin: { t: 40, l: 60, r: 20, b: 50 },
    height: 360,
    legend: { orientation: "h", y: -0.25 },
  };

  Plotly.newPlot(divId, [traceScatter, traceLine], layout, { responsive: true, displaylogo: false });
}

/* --------------------------- Prediction calculator --------------------------- */
function buildPredictionCalculator(n, k, c0) {
  const wrap = document.createElement("div");
  wrap.className = "result-section";
  wrap.innerHTML = `<h3>Prediction Calculator (using n = ${fmt(n,4)}, k = ${fmt(k)}, C_A0 = ${fmt(c0)})</h3>`;

  const grid = document.createElement("div");
  grid.className = "predict-grid";

  grid.appendChild(buildPredictBox("Predict Concentration", "Enter time (t)", "t", async (val) => {
    const res = await callPredict({ type: "concentration", t: parseFloat(val), n, k, C_A0: c0 });
    return res.error ? { error: res.error } : { text: `C_A = ${fmt(res.C_A)}` };
  }));

  grid.appendChild(buildPredictBox("Predict Time", "Enter concentration (C_A)", "C_A", async (val) => {
    const res = await callPredict({ type: "time", C_A: parseFloat(val), n, k, C_A0: c0 });
    return res.error ? { error: res.error } : { text: `t = ${fmt(res.t)}` };
  }));

  grid.appendChild(buildPredictBox("Predict Rate", "Enter concentration (C_A)", "C_A", async (val) => {
    const res = await callPredict({ type: "rate", C_A: parseFloat(val), n, k, C_A0: c0 });
    return res.error ? { error: res.error } : { text: `-r_A = ${fmt(res.rate)}` };
  }));

  wrap.appendChild(grid);
  return wrap;
}

function buildPredictBox(title, placeholder, fieldLabel, onCalculate) {
  const box = document.createElement("div");
  box.className = "predict-box";
  box.innerHTML = `
    <h4>${title}</h4>
    <label>${fieldLabel}</label>
    <input type="number" step="any" class="predict-input" placeholder="${placeholder}" />
    <button class="btn primary small" style="margin-top:10px;">Calculate</button>
    <div class="result-line"></div>
    <div class="predict-error"></div>
  `;
  const input = box.querySelector(".predict-input");
  const btn = box.querySelector("button");
  const resultLine = box.querySelector(".result-line");
  const errLine = box.querySelector(".predict-error");

  btn.addEventListener("click", async () => {
    resultLine.textContent = "";
    errLine.textContent = "";
    if (input.value === "") {
      errLine.textContent = "Please enter a value.";
      return;
    }
    btn.disabled = true;
    try {
      const out = await onCalculate(input.value);
      if (out.error) errLine.textContent = out.error;
      else resultLine.textContent = out.text;
    } catch (e) {
      errLine.textContent = "Request failed: " + e.message;
    } finally {
      btn.disabled = false;
    }
  });

  return box;
}

async function callPredict(payload) {
  const res = await fetch(`${API}/api/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}

/* -------------------------------- Init -------------------------------- */
updateMethodUI();
