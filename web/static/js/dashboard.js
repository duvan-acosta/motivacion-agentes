/* Panel admin — alineado con API FastAPI existente */

const AGENT_LABELS = {
  director: "Director",
  content_creator: "Creador de contenido",
  visual_designer: "Diseñador visual",
  video_producer: "Productor de video",
  publisher: "Publicador",
};

let charts = {};
let allPackages = [];

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || err.message || "Error de servidor");
  }
  return res.json();
}

function toast(msg, type = "info") {
  const container = document.getElementById("toast-container");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

function badge(status) {
  const map = {
    ready: "badge-ready", pending: "badge-pending", published: "badge-published",
    manual: "badge-manual", failed: "badge-failed", idle: "badge-idle",
    running: "badge-running", error: "badge-error", ok: "badge-ok",
    missing: "badge-missing", stub: "badge-stub", unknown: "badge-idle",
    stopped: "badge-missing", optional: "badge-stub",
  };
  return `<span class="badge ${map[status] || "badge-idle"}">${status}</span>`;
}

function formatTime(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("es-ES", {
      day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
    });
  } catch { return iso; }
}

function navTo(sectionId) {
  document.querySelectorAll(".nav-item").forEach((n) =>
    n.classList.toggle("active", n.dataset.section === sectionId));
  document.querySelectorAll(".section").forEach((s) =>
    s.classList.toggle("active", s.id === sectionId));
  loadSection(sectionId);
}

async function loadSection(id) {
  try {
    switch (id) {
      case "inicio": await loadDashboard(); break;
      case "agentes": await loadAgents(); break;
      case "servicios": await loadServices(); break;
      case "material": await loadMaterial(); break;
      case "estadisticas": await loadAnalytics(); break;
      case "configuracion": await loadConfig(); break;
    }
  } catch (e) {
    toast("Error al cargar datos: " + e.message, "error");
  }
}

async function loadDashboard() {
  const data = await api("/api/dashboard/summary");
  const c = data.counts;
  document.getElementById("stat-total").textContent = c.total;
  document.getElementById("stat-ready").textContent = c.ready;
  document.getElementById("stat-pending").textContent = c.pending;
  document.getElementById("stat-published").textContent = c.published;
  document.getElementById("stat-manual").textContent = c.manual;

  const feed = document.getElementById("activity-feed");
  if (!data.recent_activity?.length) {
    feed.innerHTML = '<li><span class="activity-time">—</span><span>Sin actividad reciente</span></li>';
  } else {
    feed.innerHTML = data.recent_activity.map((a) =>
      `<li><span class="activity-time">${formatTime(a.timestamp)}</span><span>${a.message}</span></li>`
    ).join("");
  }

  const statuses = data.agents?.status || {};
  document.getElementById("agent-indicators").innerHTML = Object.entries(AGENT_LABELS)
    .map(([id, label]) =>
      `<div class="agent-card"><h4>${label} ${badge(statuses[id] || "idle")}</h4></div>`
    ).join("");
}

async function loadAgents() {
  const data = await api("/api/agents");
  document.getElementById("demo-toggle").checked = data.demo_mode;
  document.getElementById("btn-generate").disabled = data.generation_running;
  document.getElementById("btn-workflow").disabled = data.generation_running;

  document.getElementById("agents-grid").innerHTML = data.agents.map((a) => `
    <div class="agent-card">
      <h4>${a.label} ${badge(a.status)}</h4>
      <p>${a.description}</p>
      <div class="rag-tags">${(a.rag || []).map((f) => `<span class="rag-tag">${f}</span>`).join("") || '<span class="rag-tag">sin RAG</span>'}</div>
      <div class="agent-meta">
        ${a.last_run ? `<span>Última ejecución: ${formatTime(a.last_run.timestamp)}</span><span>Tema: ${a.last_run.theme || "—"}</span>` : "<span>Sin ejecuciones recientes</span>"}
      </div>
    </div>
  `).join("");

  const lr = data.last_run;
  document.getElementById("tasks-list").innerHTML = lr
    ? `<div class="service-row"><span class="name">Última tarea ${badge(lr.success ? "ready" : lr.success === false ? "failed" : "running")}</span><span class="detail">${formatTime(lr.timestamp)} — ${lr.message || ""}</span></div>`
    : '<p style="color:var(--text-muted);font-size:0.85rem">Sin tareas recientes</p>';
}

async function loadServices() {
  const data = await api("/api/services/health");

  document.getElementById("services-list").innerHTML = data.services.map((s) => `
    <div class="service-row">
      <div>
        <div class="name">${s.name} ${badge(s.status)}</div>
        <div class="detail">${s.description}</div>
        <div class="key-list">${s.label || ""}: ${s.configured ? (s.masked_key || "configurada") : "— no configurada"}</div>
      </div>
    </div>
  `).join("");

  const sched = data.scheduler;
  document.getElementById("scheduler-info").innerHTML = `
    <div class="service-row">
      <div>
        <div class="name">Scheduler ${badge(sched.status)}</div>
        <div class="detail">Generación diaria a las ${sched.schedule} (${sched.timezone})</div>
        <div class="detail">Próxima ejecución: ${formatTime(sched.next_run)}</div>
      </div>
    </div>`;

  document.getElementById("docker-services").innerHTML = (data.docker || []).map((s) =>
    `<div class="service-row"><span class="name">${s.name}</span>${badge(s.status)}<span class="detail">${s.role || ""}</span></div>`
  ).join("");
}

async function loadMaterial() {
  const data = await api("/api/content/packages?limit=100");
  allPackages = data.packages;

  const dateFilter = document.getElementById("filter-date").value;
  const statusFilter = document.getElementById("filter-status").value;

  const dates = [...new Set(allPackages.map((p) => p.date))].sort().reverse();
  const dateSelect = document.getElementById("filter-date");
  const cur = dateSelect.value;
  dateSelect.innerHTML = '<option value="">Todas las fechas</option>' +
    dates.map((d) => `<option value="${d}" ${d === cur ? "selected" : ""}>${d}</option>`).join("");

  let filtered = allPackages;
  if (dateFilter) filtered = filtered.filter((p) => p.date === dateFilter);
  if (statusFilter) filtered = filtered.filter((p) => p.status === statusFilter);

  const tbody = document.getElementById("packages-tbody");
  if (!filtered.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted)">Sin paquetes</td></tr>';
    return;
  }

  tbody.innerHTML = filtered.map((p) => {
    const img = p.thumbnail
      ? `<img class="package-preview" src="/api/content/media/${p.thumbnail}" alt="preview">`
      : '<div class="package-preview"></div>';
    return `<tr>
      <td>${img}</td>
      <td><strong>${p.name}</strong><br><small style="color:var(--text-muted)">${p.date}</small></td>
      <td>${p.theme}</td>
      <td>${badge(p.status)}</td>
      <td>${formatTime(p.generated_at)}</td>
      <td>
        <button class="btn btn-sm btn-secondary" onclick="viewPackage('${p.id}')">Ver</button>
        <button class="btn btn-sm btn-primary" onclick="publishPackage('${p.id}')" ${p.status === "published" ? "disabled" : ""}>Publicar</button>
        <a class="btn btn-sm btn-secondary" href="/api/content/packages/${encodeURIComponent(p.id)}/download">Descargar</a>
      </td>
    </tr>`;
  }).join("");
}

async function viewPackage(id) {
  const p = await api("/api/content/packages/" + encodeURIComponent(id));
  document.getElementById("modal-title").textContent = p.name || id;
  const imgEl = document.getElementById("modal-preview");
  if (p.images?.length) {
    imgEl.src = "/api/content/media/" + p.images[0].path;
    imgEl.style.display = "block";
  } else {
    imgEl.style.display = "none";
  }

  document.getElementById("modal-body").innerHTML = `
    <p style="margin-bottom:0.75rem">${badge(p.status)} · Tema: <strong>${p.theme}</strong></p>
    <p style="font-style:italic;margin-bottom:1rem;color:var(--accent-mist)">"${p.message}"</p>
    <h4 style="margin-bottom:0.5rem;font-size:0.85rem;color:var(--text-muted)">Captions</h4>
    ${Object.entries(p.captions || {}).map(([k, v]) => `<div class="caption-block"><strong>${k}</strong>${v}</div>`).join("")}
    ${p.hashtags ? `<div class="caption-block"><strong>hashtags</strong>${p.hashtags}</div>` : ""}
    <h4 style="margin:1rem 0 0.5rem;font-size:0.85rem;color:var(--text-muted)">Ruta</h4>
    <code style="font-size:0.75rem;color:var(--text-muted)">${p.path}</code>
    <h4 style="margin:1rem 0 0.5rem;font-size:0.85rem;color:var(--text-muted)">Manifest</h4>
    <pre style="background:var(--bg-deep);padding:0.75rem;border-radius:8px;font-size:0.7rem;overflow:auto;max-height:200px">${JSON.stringify(p.manifest, null, 2)}</pre>
  `;
  document.getElementById("modal-overlay").classList.add("active");
  document.getElementById("modal-publish-btn").onclick = () => publishPackage(id);
}

function closeModal() {
  document.getElementById("modal-overlay").classList.remove("active");
}

async function publishPackage(id) {
  const res = await api("/api/content/packages/" + encodeURIComponent(id) + "/publish", {
    method: "POST",
    body: JSON.stringify({ platforms: null }),
  });
  toast(res.message || "Publicación iniciada", res.ok === false ? "error" : "success");
  closeModal();
  loadMaterial();
}

async function loadAnalytics() {
  const [platforms, trends] = await Promise.all([
    api("/api/analytics/platforms"),
    api("/api/analytics/trends"),
  ]);

  document.getElementById("analytics-demo-banner").style.display =
    trends.demo_mode ? "flex" : "none";

  document.getElementById("platform-metrics").innerHTML = platforms.platforms.map((p) => {
    const m = p.metrics;
    return `
    <div class="platform-metric-card">
      <h4>${p.label} ${p.connect_cta ? '<span class="badge badge-stub">demo</span>' : badge("ok")}</h4>
      <div class="metric-row"><span>Seguidores</span><span class="val">${m.followers?.toLocaleString("es-ES") || "—"}</span></div>
      <div class="metric-row"><span>Engagement</span><span class="val">${m.engagement_rate || "—"}%</span></div>
      <div class="metric-row"><span>Posts/semana</span><span class="val">${m.posts_this_week || "—"}</span></div>
      ${p.connect_cta ? '<button class="btn btn-sm btn-secondary" style="margin-top:0.5rem" onclick="toast(\'Configura las API keys en .env\',\'info\')">Conectar API</button>' : ""}
    </div>`;
  }).join("");

  renderCharts(trends);
}

function renderCharts(trends) {
  const platform = trends.platforms?.instagram || Object.values(trends.platforms || {})[0];
  if (!platform) return;

  const chartOpts = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: "#8b9cb3" } } },
    scales: {
      x: { ticks: { color: "#8b9cb3", maxTicksLimit: 10 }, grid: { color: "#2d3a4d" } },
      y: { ticks: { color: "#8b9cb3" }, grid: { color: "#2d3a4d" } },
    },
  };

  const labels = platform.dates || [];

  if (charts.followers) charts.followers.destroy();
  charts.followers = new Chart(document.getElementById("chart-followers"), {
    type: "line",
    data: {
      labels,
      datasets: [{ label: "Seguidores", data: platform.followers, borderColor: "#7d9b76", backgroundColor: "rgba(125,155,118,0.1)", fill: true, tension: 0.3 }],
    },
    options: chartOpts,
  });

  if (charts.engagement) charts.engagement.destroy();
  charts.engagement = new Chart(document.getElementById("chart-engagement"), {
    type: "line",
    data: {
      labels,
      datasets: [{ label: "Engagement %", data: platform.engagement_rate, borderColor: "#4a8f8f", backgroundColor: "rgba(74,143,143,0.1)", fill: true, tension: 0.3 }],
    },
    options: chartOpts,
  });

  if (charts.posts) charts.posts.destroy();
  charts.posts = new Chart(document.getElementById("chart-posts"), {
    type: "bar",
    data: {
      labels,
      datasets: [{ label: "Posts/semana", data: platform.posts_per_week, backgroundColor: "#c4a35a" }],
    },
    options: chartOpts,
  });

  document.getElementById("top-hashtags").innerHTML = (trends.hashtags || []).map(([tag, count]) =>
    `<div class="service-row"><span class="name">${tag}</span><span class="detail">${count} usos</span></div>`
  ).join("") || '<p style="color:var(--text-muted)">Sin datos de hashtags</p>';
}

async function triggerGenerate() {
  const theme = document.getElementById("theme-input").value.trim() || null;
  const demo = document.getElementById("demo-toggle").checked;
  const res = await api("/api/agents/generate", { method: "POST", body: JSON.stringify({ theme, demo }) });
  toast(res.message, res.ok === false ? "error" : "success");
  setTimeout(() => { loadAgents(); loadDashboard(); }, 2000);
}

async function triggerWorkflow() {
  const theme = document.getElementById("theme-input").value.trim() || null;
  const demo = document.getElementById("demo-toggle").checked;
  const res = await api("/api/agents/workflow", { method: "POST", body: JSON.stringify({ theme, demo }) });
  toast(res.message, res.ok === false ? "error" : "success");
  setTimeout(() => { loadAgents(); loadDashboard(); }, 2000);
}

async function toggleDemoMode() {
  const enabled = document.getElementById("demo-toggle").checked;
  await api("/api/agents/demo-mode", { method: "POST", body: JSON.stringify({ enabled }) });
  toast(`Modo ${enabled ? "demo" : "producción"} activado`, "info");
}

let configData = null;

async function loadConfig() {
  configData = await api("/api/config");
  const pathEl = document.getElementById("env-path");
  if (pathEl) pathEl.textContent = configData.env_path || ".env";

  document.getElementById("config-groups").innerHTML = configData.groups.map((group) => `
    <div class="panel config-group">
      <h3>${group.label}</h3>
      <div class="config-fields">
        ${group.fields.map((f) => renderConfigField(f)).join("")}
      </div>
    </div>
  `).join("");
}

function renderConfigField(field) {
  const id = `cfg-${field.key}`;
  if (field.type === "select") {
    return `
      <label class="config-field" for="${id}">
        <span>${field.label}</span>
        <select id="${id}" data-key="${field.key}">
          ${(field.options || []).map((o) =>
            `<option value="${o}" ${field.value === o ? "selected" : ""}>${o}</option>`
          ).join("")}
        </select>
      </label>`;
  }
  if (field.type === "secret") {
    const hint = field.configured ? `<small class="config-hint">Actual: ${field.masked}</small>` : "";
    return `
      <label class="config-field" for="${id}">
        <span>${field.label} ${field.configured ? '<span class="badge badge-ok">configurada</span>' : '<span class="badge badge-missing">vacía</span>'}</span>
        <input type="password" id="${id}" data-key="${field.key}" placeholder="${field.configured ? "Dejar vacío para mantener" : "Ingresar clave"}" autocomplete="off">
        ${hint}
      </label>`;
  }
  return `
    <label class="config-field" for="${id}">
      <span>${field.label}</span>
      <input type="${field.type === "number" ? "number" : "text"}" id="${id}" data-key="${field.key}" value="${field.value || ""}">
    </label>`;
}

async function saveConfig() {
  const values = {};
  document.querySelectorAll("#config-groups [data-key]").forEach((el) => {
    const key = el.dataset.key;
    const val = el.value.trim();
    if (val) values[key] = val;
  });
  const res = await api("/api/config", { method: "POST", body: JSON.stringify({ values }) });
  toast(res.message, res.ok ? "success" : "error");
  if (res.ok) {
    await loadConfig();
    loadServices();
  }
}

function toggleMobileMenu(open) {
  document.getElementById("sidebar").classList.toggle("open", open);
  document.getElementById("mobile-overlay").classList.toggle("open", open);
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.addEventListener("click", () => {
      navTo(item.dataset.section);
      toggleMobileMenu(false);
    });
  });
  document.getElementById("mobile-menu-btn").addEventListener("click", () => {
    const sidebar = document.getElementById("sidebar");
    toggleMobileMenu(!sidebar.classList.contains("open"));
  });
  document.getElementById("mobile-overlay").addEventListener("click", () => toggleMobileMenu(false));
  document.getElementById("btn-save-config").addEventListener("click", saveConfig);
  document.getElementById("btn-reload-config").addEventListener("click", loadConfig);
  document.getElementById("btn-generate").addEventListener("click", triggerGenerate);
  document.getElementById("btn-workflow").addEventListener("click", triggerWorkflow);
  document.getElementById("demo-toggle").addEventListener("change", toggleDemoMode);
  document.getElementById("filter-date").addEventListener("change", loadMaterial);
  document.getElementById("filter-status").addEventListener("change", loadMaterial);
  document.getElementById("modal-close").addEventListener("click", closeModal);
  document.getElementById("modal-overlay").addEventListener("click", (e) => {
    if (e.target.id === "modal-overlay") closeModal();
  });

  navTo("inicio");
  setInterval(() => {
    const active = document.querySelector(".section.active");
    if (active) loadSection(active.id);
  }, 30000);
});
