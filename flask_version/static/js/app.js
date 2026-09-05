/* ==========================================================================
   Innovation Portfolio Dashboard — frontend application
   Vanilla JS SPA. All data comes from the Flask API; nothing here is
   hard-coded to specific projects/brands/categories.
   ========================================================================== */

(function () {
  "use strict";

  // ------------------------------------------------------------------ state
  const state = {
    filters: { category: [], brand: [], project: [], status: [], year: [] },
    search: "",
    view: "dashboard",
    data: null,
    catColor: {},
    home: { sortKey: "yr", sortDir: "desc", page: 1, pageSize: 7 },
    proj: { sortKey: "project", sortDir: "asc", page: 1, pageSize: 10 },
  };

  const STATUS_CLASS = {
    "On Track": "ontrack",
    "Landed": "landed",
    "Delayed": "delayed",
    "Kick-off": "kickoff",
    "TBD": "tbd",
  };

  const FILTER_DEFS = [
    { key: "category", param: "category", el: "filterCategory", label: "Category" },
    { key: "brand", param: "brand", el: "filterBrand", label: "Brand" },
    { key: "project", param: "project", el: "filterProject", label: "Project" },
    { key: "status", param: "status", el: "filterStatus", label: "Status" },
    { key: "year", param: "year", el: "filterYear", label: "Year" },
  ];

  const charts = {}; // Chart.js instances keyed by canvas id

  // ------------------------------------------------------------------ utils
  function escapeHtml(s) {
    if (s === null || s === undefined) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function naSpan(val, cls) {
    if (val === null || val === undefined || val === "") {
      return `<span class="na-text">N/A</span>`;
    }
    return `<span${cls ? ` class="${cls}"` : ""}>${escapeHtml(val)}</span>`;
  }

  function badgeHtml(status) {
    const cls = STATUS_CLASS[status] || "tbd";
    return `<span class="badge badge-${cls}"><span class="dot"></span>${escapeHtml(status)}</span>`;
  }

  function qs(id) { return document.getElementById(id); }

  function animateNumber(el, to) {
    const from = Number(el.dataset.val || 0);
    const dur = 500;
    const t0 = performance.now();
    function step(t) {
      const p = Math.min(1, (t - t0) / dur);
      const eased = 1 - Math.pow(1 - p, 3);
      const val = Math.round(from + (to - from) * eased);
      el.textContent = val;
      if (p < 1) requestAnimationFrame(step);
      else el.dataset.val = to;
    }
    requestAnimationFrame(step);
  }

  let toastTimer = null;
  function toast(msg) {
    const el = qs("toast");
    el.innerHTML = `<span class="tdot"></span>${escapeHtml(msg)}`;
    el.classList.add("is-visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove("is-visible"), 2800);
  }

  // ------------------------------------------------------------------ fetch
  function buildQuery() {
    const p = new URLSearchParams();
    FILTER_DEFS.forEach((f) => {
      state.filters[f.key].forEach((v) => p.append(f.param, v));
    });
    if (state.search) p.append("q", state.search);
    return p.toString();
  }

  function fetchDashboard() {
    const q = buildQuery();
    return fetch(`/api/dashboard${q ? "?" + q : ""}`)
      .then((r) => r.json())
      .then((data) => {
        state.data = data;
        state.catColor = {};
        (data.charts.by_category || []).forEach((c) => (state.catColor[c.label] = c.color));
        renderAll();
      });
  }

  function fetchRisks() {
    const q = buildQuery();
    return fetch(`/api/risks${q ? "?" + q : ""}`).then((r) => r.json());
  }

  // ------------------------------------------------------------------ init
  function init() {
    bindNav();
    bindFilterShell();
    bindSearch();
    bindClear();
    bindRefresh();
    bindDrawer();
    fetchDashboard();
  }

  function bindNav() {
    document.querySelectorAll(".nav-item").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".nav-item").forEach((b) => b.classList.remove("is-active"));
        btn.classList.add("is-active");
        const view = btn.dataset.view;
        state.view = view;
        document.querySelectorAll(".view").forEach((v) => (v.hidden = true));
        qs(`view-${view}`).hidden = false;
        renderView(view);
      });
    });
  }

  function bindSearch() {
    let t = null;
    qs("searchInput").addEventListener("input", (e) => {
      clearTimeout(t);
      const val = e.target.value;
      t = setTimeout(() => {
        state.search = val;
        state.home.page = 1;
        state.proj.page = 1;
        fetchDashboard();
      }, 260);
    });
  }

  function bindClear() {
    qs("clearFiltersBtn").addEventListener("click", () => {
      FILTER_DEFS.forEach((f) => (state.filters[f.key] = []));
      state.search = "";
      qs("searchInput").value = "";
      state.home.page = 1;
      state.proj.page = 1;
      fetchDashboard();
    });
  }

  function bindRefresh() {
    const btn = qs("refreshBtn");
    btn.addEventListener("click", () => {
      btn.classList.add("is-spinning");
      btn.disabled = true;
      fetch("/api/refresh", { method: "POST" })
        .then((r) => r.json())
        .then(() => fetchDashboard())
        .then(() => toast("Data successfully refreshed."))
        .catch(() => toast("Refresh failed — check the Excel file path."))
        .finally(() => {
          btn.classList.remove("is-spinning");
          btn.disabled = false;
        });
    });
  }

  // ------------------------------------------------------------- filter ui
  function bindFilterShell() {
    document.addEventListener("click", (e) => {
      document.querySelectorAll(".ms-select.is-open").forEach((sel) => {
        if (!sel.contains(e.target)) sel.classList.remove("is-open");
      });
    });
  }

  function renderFilters() {
    const opts = state.data.filters;
    const optMap = {
      category: opts.categories,
      brand: opts.brands,
      project: opts.projects,
      status: opts.statuses,
      year: opts.years,
    };

    FILTER_DEFS.forEach((f) => {
      const container = qs(f.el);
      const wasOpen = container.classList.contains("is-open");
      const available = optMap[f.key] || [];
      // prune selections no longer valid
      state.filters[f.key] = state.filters[f.key].filter((v) => available.includes(v));

      const selected = state.filters[f.key];
      const labelText = selected.length === 0 ? `All ${f.label}s` : selected.length === 1 ? selected[0] : `${selected.length} selected`;

      container.innerHTML = `
        <div class="ms-trigger">
          <span class="ms-label">${escapeHtml(labelText)}</span>
          ${selected.length ? `<span class="ms-badge">${selected.length}</span>` : ""}
          <svg class="chev" viewBox="0 0 20 20"><path d="M5 8l5 5 5-5" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
        <div class="ms-panel">
          ${available.length === 0 ? `<div class="ms-empty">No options</div>` : available.map((opt) => `
            <label class="ms-option">
              <input type="checkbox" value="${escapeHtml(opt)}" ${selected.includes(opt) ? "checked" : ""} />
              <span>${escapeHtml(opt)}</span>
            </label>
          `).join("")}
        </div>
      `;
      if (wasOpen) container.classList.add("is-open");

      container.querySelector(".ms-trigger").addEventListener("click", (e) => {
        e.stopPropagation();
        const isOpen = container.classList.contains("is-open");
        document.querySelectorAll(".ms-select.is-open").forEach((s) => s.classList.remove("is-open"));
        if (!isOpen) container.classList.add("is-open");
      });

      container.querySelectorAll(".ms-option input").forEach((cb) => {
        cb.addEventListener("change", () => {
          const val = cb.value;
          const arr = state.filters[f.key];
          const idx = arr.indexOf(val);
          if (cb.checked && idx === -1) arr.push(val);
          if (!cb.checked && idx !== -1) arr.splice(idx, 1);
          state.home.page = 1;
          state.proj.page = 1;
          fetchDashboard();
        });
      });
    });
  }

  // ------------------------------------------------------------------ KPIs
  const KPI_DEFS = [
    { key: "total_projects", label: "Total Projects", accent: "var(--teal-600)", foot: "In current view" },
    { key: "on_track", label: "On Track", accent: "var(--st-ontrack)", foot: "Progressing to plan" },
    { key: "delayed", label: "Delayed", accent: "var(--st-delayed)", foot: "Needs attention" },
    { key: "landed", label: "Landed / Completed", accent: "var(--st-landed)", foot: "Shipped to market" },
    { key: "at_risk", label: "Projects at Risk", accent: "var(--amber-600)", foot: "Flagged risk notes" },
    { key: "categories", label: "Categories", accent: "#8452C2", foot: "Active categories" },
    { key: "brands", label: "Brands", accent: "#1A8FA6", foot: "Active brands" },
  ];

  function renderKPIs() {
    const grid = qs("kpiGrid");
    if (!grid.dataset.built) {
      grid.innerHTML = KPI_DEFS.map((k) => `
        <div class="kpi-card" style="--accent:${k.accent}">
          <div class="kpi-label">${k.label}</div>
          <div class="kpi-value" id="kpi-${k.key}" data-val="0">0</div>
          <div class="kpi-foot">${k.foot}</div>
        </div>
      `).join("");
      grid.dataset.built = "1";
    }
    const kpis = state.data.kpis;
    KPI_DEFS.forEach((k) => animateNumber(qs(`kpi-${k.key}`), kpis[k.key] || 0));
  }

  // --------------------------------------------------------------- charts
  function destroyChart(id) {
    if (charts[id]) { charts[id].destroy(); delete charts[id]; }
  }

  function baseFont() {
    return "13px 'Segoe UI', system-ui, sans-serif";
  }

  function doughnut(canvasId, items) {
    const el = qs(canvasId);
    if (!el) return;
    destroyChart(canvasId);
    if (!items.length) return;
    charts[canvasId] = new Chart(el, {
      type: "doughnut",
      data: {
        labels: items.map((i) => i.label),
        datasets: [{
          data: items.map((i) => i.value),
          backgroundColor: items.map((i) => i.color),
          borderColor: "#ffffff",
          borderWidth: 2,
          hoverOffset: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "62%",
        plugins: {
          legend: { position: "bottom", labels: { boxWidth: 10, boxHeight: 10, usePointStyle: true, pointStyle: "circle", padding: 14, font: { size: 12 } } },
          tooltip: { callbacks: { label: (ctx) => ` ${ctx.label}: ${ctx.parsed}` } },
        },
      },
    });
  }

  function barH(canvasId, items, color) {
    const el = qs(canvasId);
    if (!el) return;
    destroyChart(canvasId);
    if (!items.length) return;
    charts[canvasId] = new Chart(el, {
      type: "bar",
      data: {
        labels: items.map((i) => i.label),
        datasets: [{
          data: items.map((i) => i.value),
          backgroundColor: items.map((i) => i.color || color),
          borderRadius: 6,
          maxBarThickness: 26,
        }],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: (ctx) => ` ${ctx.parsed.x} projects` } } },
        scales: {
          x: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: "#eeece4" } },
          y: { grid: { display: false } },
        },
      },
    });
  }

  function renderChartsDashboard() {
    const c = state.data.charts;
    doughnut("chartCategoryHome", c.by_category);
    doughnut("chartStatusHome", c.by_status);
  }

  function renderChartsPortfolio() {
    const c = state.data.charts;
    doughnut("chartCategory", c.by_category);
    barH("chartBrand", c.by_brand, "#0f6e5d");
    doughnut("chartStatus", c.by_status);
    barH("chartProgress", c.progress, "#0f6e5d");
  }

  // ---------------------------------------------------------------- table
  const COLUMNS = [
    { key: "category", label: "Category", sortable: true },
    { key: "brand", label: "Brand", sortable: true },
    { key: "project", label: "Project", sortable: true },
    { key: "site", label: "Site", sortable: true },
    { key: "status", label: "Status", sortable: true },
    { key: "trial_status", label: "Trial Status", sortable: true },
    { key: "yr", label: "Yr", sortable: true },
    { key: "gm", label: "GM", sortable: true },
  ];

  function sortRows(rows, key, dir) {
    const mult = dir === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => {
      let av = a[key], bv = b[key];
      if (av === null || av === undefined) av = "";
      if (bv === null || bv === undefined) bv = "";
      if (typeof av === "number" && typeof bv === "number") return (av - bv) * mult;
      return String(av).localeCompare(String(bv), undefined, { numeric: true }) * mult;
    });
  }

  function renderTable(containerId, rows, tstate, countElId) {
    const container = qs(containerId);
    if (countElId) qs(countElId).textContent = `${rows.length} project${rows.length === 1 ? "" : "s"}`;

    if (!rows.length) {
      container.innerHTML = `<div class="table-empty">No projects match the current filters.</div>`;
      return;
    }

    const sorted = sortRows(rows, tstate.sortKey, tstate.sortDir);
    const totalPages = Math.max(1, Math.ceil(sorted.length / tstate.pageSize));
    tstate.page = Math.min(tstate.page, totalPages);
    const start = (tstate.page - 1) * tstate.pageSize;
    const pageRows = sorted.slice(start, start + tstate.pageSize);

    const thead = `
      <thead><tr>
        ${COLUMNS.map((c) => {
          const active = tstate.sortKey === c.key;
          const arrow = active ? (tstate.sortDir === "asc" ? "▲" : "▼") : "";
          return `<th data-key="${c.key}">${c.label}${arrow ? `<span class="sort-arrow">${arrow}</span>` : ""}</th>`;
        }).join("")}
      </tr></thead>`;

    const tbody = `<tbody>${pageRows.map((r) => `
      <tr data-id="${r.id}">
        <td><span class="cat-chip"><span class="cat-dot" style="background:${state.catColor[r.category] || "#8a93a0"}"></span>${escapeHtml(r.category)}</span></td>
        <td>${escapeHtml(r.brand)}</td>
        <td class="cell-project">${escapeHtml(r.project)}</td>
        <td class="${r.site ? "" : "cell-muted"}">${r.site ? escapeHtml(r.site) : "N/A"}</td>
        <td>${badgeHtml(r.status)}</td>
        <td class="${r.trial_status ? "" : "cell-muted"}">${r.trial_status ? escapeHtml(r.trial_status) : "N/A"}</td>
        <td class="${r.yr ? "" : "cell-muted"}">${r.yr ? escapeHtml(r.yr) : "N/A"}</td>
        <td class="${(r.gm !== null && r.gm !== undefined) ? "" : "cell-muted"}">${(r.gm !== null && r.gm !== undefined) ? escapeHtml(r.gm) : "N/A"}</td>
      </tr>`).join("")}</tbody>`;

    const pagination = `
      <div class="pagination">
        <span>Showing ${start + 1}\u2013${Math.min(start + tstate.pageSize, sorted.length)} of ${sorted.length}</span>
        <div class="pg-btns">
          <button data-pg="prev" ${tstate.page <= 1 ? "disabled" : ""}>Prev</button>
          <button data-pg="next" ${tstate.page >= totalPages ? "disabled" : ""}>Next</button>
        </div>
      </div>`;

    container.innerHTML = `<table class="dtable">${thead}${tbody}</table>${pagination}`;

    container.querySelectorAll("thead th").forEach((th) => {
      th.addEventListener("click", () => {
        const key = th.dataset.key;
        if (tstate.sortKey === key) tstate.sortDir = tstate.sortDir === "asc" ? "desc" : "asc";
        else { tstate.sortKey = key; tstate.sortDir = "asc"; }
        renderTable(containerId, rows, tstate, countElId);
      });
    });

    container.querySelectorAll("tbody tr").forEach((tr) => {
      tr.addEventListener("click", () => openDrawer(Number(tr.dataset.id)));
    });

    const prevBtn = container.querySelector('[data-pg="prev"]');
    const nextBtn = container.querySelector('[data-pg="next"]');
    if (prevBtn) prevBtn.addEventListener("click", () => { tstate.page -= 1; renderTable(containerId, rows, tstate, countElId); });
    if (nextBtn) nextBtn.addEventListener("click", () => { tstate.page += 1; renderTable(containerId, rows, tstate, countElId); });
  }

  // ---------------------------------------------------------------- risks
  function renderRisks() {
    fetchRisks().then((data) => {
      qs("riskCount").textContent = `${data.count} flagged`;
      const list = qs("riskList");
      if (!data.risks.length) {
        list.innerHTML = `<div class="table-empty">No risks flagged for the current filters.</div>`;
        return;
      }
      list.innerHTML = data.risks.map((r) => `
        <div class="risk-item" data-id="${r.id}">
          <div class="risk-flag">
            <svg viewBox="0 0 20 20"><path d="M10 2.6 18 16.4H2Z" fill="none" stroke="currentColor"/><path d="M10 8.3v3.6" stroke-linecap="round"/><circle cx="10" cy="14" r="0.9" fill="currentColor" stroke="none"/></svg>
          </div>
          <div>
            <div class="risk-title">
              <strong>${escapeHtml(r.project)}</strong>
              ${badgeHtml(r.status)}
              <span class="risk-meta">${escapeHtml(r.category)} \u00b7 ${escapeHtml(r.brand)}</span>
            </div>
            <div class="risk-text">${escapeHtml(r.risks)}</div>
            ${r.updates ? `<div class="risk-update">Latest update: ${escapeHtml(r.updates)}</div>` : ""}
          </div>
        </div>
      `).join("");
      list.querySelectorAll(".risk-item").forEach((it) => it.addEventListener("click", () => openDrawer(Number(it.dataset.id))));
    });
  }

  // ---------------------------------------------------------- status view
  function renderStatusOverview() {
    const order = ["On Track", "Kick-off", "Delayed", "Landed", "TBD"];
    const kpis = state.data.kpis;
    const meta = state.data.status_meta;
    const total = kpis.total_projects || 1;
    const map = { "On Track": kpis.on_track, "Kick-off": kpis.kick_off, "Delayed": kpis.delayed, "Landed": kpis.landed, "TBD": kpis.tbd };

    qs("statusCards").innerHTML = order.map((s) => {
      const val = map[s] || 0;
      const pct = Math.round((val / total) * 100);
      const m = meta[s];
      return `
        <div class="status-card">
          <div class="sc-top">
            <span>${badgeHtml(s)}</span>
            <span class="sc-value" style="color:${m.color}">${val}</span>
          </div>
          <div class="status-bar-track"><div class="status-bar-fill" style="width:${pct}%;background:${m.color}"></div></div>
          <div class="kpi-foot">${pct}% of portfolio</div>
        </div>`;
    }).join("");

    const rows = state.data.table;
    const groups = qs("statusGroups");
    groups.innerHTML = order.map((s) => {
      const rs = rows.filter((r) => r.status === s);
      if (!rs.length) return "";
      return `
        <div class="status-group">
          <div class="status-group-head">${badgeHtml(s)}<span class="panel-count">${rs.length} project${rs.length === 1 ? "" : "s"}</span></div>
          <div class="status-group-rows">
            <table class="dtable">
              <tbody>
                ${rs.map((r) => `
                  <tr data-id="${r.id}">
                    <td><span class="cat-chip"><span class="cat-dot" style="background:${state.catColor[r.category] || "#8a93a0"}"></span>${escapeHtml(r.category)}</span></td>
                    <td>${escapeHtml(r.brand)}</td>
                    <td class="cell-project">${escapeHtml(r.project)}</td>
                    <td class="${r.site ? "" : "cell-muted"}">${r.site ? escapeHtml(r.site) : "N/A"}</td>
                  </tr>`).join("")}
              </tbody>
            </table>
          </div>
        </div>`;
    }).join("");

    groups.querySelectorAll("tbody tr").forEach((tr) => tr.addEventListener("click", () => openDrawer(Number(tr.dataset.id))));
  }

  // -------------------------------------------------------------- drawer
  function bindDrawer() {
    qs("drawerOverlay").addEventListener("click", closeDrawer);
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });
  }

  function closeDrawer() {
    qs("drawer").classList.remove("is-open");
    qs("drawerOverlay").classList.remove("is-open");
  }

  function openDrawer(id) {
    fetch(`/api/project/${id}`)
      .then((r) => r.json())
      .then((p) => {
        qs("drawerContent").innerHTML = drawerHtml(p);
        qs("drawer").querySelector(".drawer-close")?.addEventListener("click", closeDrawer);
        qs("drawer").classList.add("is-open");
        qs("drawerOverlay").classList.add("is-open");
      });
  }

  function drawerHtml(p) {
    const imageBlock = p.image_url
      ? `<div class="drawer-image"><img src="${p.image_url}" alt="${escapeHtml(p.project)}" /></div>`
      : `<div class="drawer-image"><div class="ph"><svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="15" rx="2"/><circle cx="8.5" cy="9.5" r="1.5"/><path d="M21 16l-5.5-5.5L9 17"/></svg><span>No project image yet</span></div></div>`;

    const cards = p.cards.filter((c) => c.value !== null && c.value !== undefined && c.value !== "");
    const infoCards = cards.length
      ? `<div class="info-grid">${cards.map((c) => `
          <div class="info-card">
            <div class="ic-label">${escapeHtml(c.label)}</div>
            <div class="ic-value">${escapeHtml(c.value)}</div>
          </div>`).join("")}</div>`
      : `<p class="na">No additional field data recorded for this project.</p>`;

    return `
      <div class="drawer-hero">
        <button class="drawer-close" aria-label="Close">
          <svg viewBox="0 0 20 20"><path d="M5 5l10 10M15 5L5 15" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
        </button>
        <div class="drawer-eyebrow">${escapeHtml(p.category)} \u00b7 ${escapeHtml(p.brand)}</div>
        <h2 class="drawer-title">${escapeHtml(p.project)}</h2>
        <div class="drawer-meta">
          ${badgeHtml(p.status)}
          ${p.site ? `<span class="drawer-chip">Site: ${escapeHtml(p.site)}</span>` : ""}
        </div>
      </div>

      ${imageBlock}

      <div class="drawer-section">
        <h4>Scope</h4>
        <p class="${p.scope ? "" : "na"}">${p.scope ? escapeHtml(p.scope) : "N/A"}</p>
      </div>

      <div class="drawer-section">
        <h4>Description</h4>
        <p class="${p.description ? "" : "na"}">${p.description ? escapeHtml(p.description) : "N/A"}</p>
      </div>

      <div class="drawer-section">
        <h4>Project Details</h4>
        ${infoCards}
      </div>

      <div class="drawer-section">
        <h4>Risks</h4>
        ${p.risks ? `<div class="drawer-risk-box">${escapeHtml(p.risks)}</div>` : `<p class="na">No risks currently flagged.</p>`}
      </div>

      <div class="drawer-section">
        <h4>Updates</h4>
        ${p.updates ? `<div class="drawer-update-box">${escapeHtml(p.updates)}</div>` : `<p class="na">No updates recorded.</p>`}
      </div>
    `;
  }

  // ---------------------------------------------------------------- views
  function renderView(view) {
    if (!state.data) return;
    if (view === "dashboard") {
      renderChartsDashboard();
      renderTable("homeTableWrap", state.data.table, state.home, "homeTableCount");
    } else if (view === "projects") {
      renderTable("projectsTableWrap", state.data.table, state.proj, "projectsTableCount");
    } else if (view === "portfolio") {
      renderChartsPortfolio();
    } else if (view === "risks") {
      renderRisks();
    } else if (view === "status") {
      renderStatusOverview();
    }
  }

  function renderAll() {
    const d = state.data;
    qs("lastUpdated").textContent = d.last_updated || "\u2014";

    const pill = qs("sourcePill");
    if (d.source_missing) {
      pill.classList.add("is-missing");
      qs("sourceLabel").textContent = "Excel file not found";
    } else {
      pill.classList.remove("is-missing");
      qs("sourceLabel").textContent = "Excel connected";
    }

    renderFilters();
    renderKPIs();
    renderView(state.view);
  }

  document.addEventListener("DOMContentLoaded", init);
})();
