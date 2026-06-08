/* Panel admin — Mental Equilibrio */

const SECTION_TITLES = {
  inicio: "Inicio",
  agentes: "Agentes",
  servicios: "Servicios",
  material: "Material generado",
  estadisticas: "Estadísticas y tendencias",
};

const AGENT_LABELS = {
  director: "Director",
  content_creator: "Creador",
  visual_designer: "Visual",
  video_producer: "Video",
  publisher: "Publicador",
};

let charts = {};
let refreshTimer = null;

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

function toast(msg, kind = "info") {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.className = `toast show ${kind}`;
  setTimeout(() => el.classList.remove("show"), 3500);
}

function badge(status) {
  const cls = `badge badge-${status || "unknown"}`;
  return `<span class="${cls}">${status || "unknown"}</span>`;
}

function agentDot(status) {
  return `<span class="agent-dot agent-${status || "idle"}"></span>`;
}

function navigate(section) {
  document.querySelectorAll(".nav-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.section === section);
  });
  document.querySelectorAll(".section").forEach((el) => {
    el.classList.toggle("active", el.id === `section-${section}`);
  });
  document.getElementById("page-title").textContent = SECTION_TITLES[section] || section;
  document.getElementById("sidebar").classList.remove("open");
  document.getElementById("mobile-overlay").classList.remove("open");

  if (section === "estadisticas") loadAnalytics();
  if (section === "material") loadPackages();
  if (section === "servicios") loadServices();
  if (section === "agentes") loadAgents();
}

async function loadDashboard() {
  const data = await api("/api/dashboard/summary");
  const c = data.counts;
  document.getElementById("stat-total").textContent = c.total;
  document.getElementById("stat-ready").textContent = c.ready;
  document.getElementById("stat-pending").textContent = c.pending;
  document.getElementById("stat-published").textContent = c.published;
  document.getElementById("stat-manual").textContent = c.manual;
  document.getElementById("stat-failed").textContent = c.failed;

  const grid = document.getElementById("agent-status-grid");
  const statuses = data.agents?.status || {};
  grid.innerHTML = Object.entries(AGENT_LABELS)
    .map(
      ([id, label]) =>
        `<div class="flex items-center gap-2 p-2 rounded-lg bg-[var(--bg-elevated)]">${agentDot(
          statuses[id] || "idle"
        )}<span class="text-sm">${label}</span></div>`
    )
    .join("");

  const feed = document.getElementById("activity-feed");
  if (!data.recent_activity?.length) {
    feed.innerHTML = '<p class="text-sm text-[var(--text-muted)]">Sin actividad reciente.</p>';
  } else {
    feed.innerHTML = data.recent_activity
      .map(
        (a) =>
          `<div class="activity-item"><p class="text-sm">${a.message}</p><p class="text-xs text-[var(--text-muted)] mt-1">${formatDate(
            a.timestamp
          )}</p></div>`
      )
      .join("");
  }

  updateDemoBadge(data.demo_mode);
}

async function loadAgents() {
  const data = await api("/api/agents");
  updateDemoToggle(data.demo_mode);
  document.getElementById("btn-generate").disabled = data.generation_running;
  document.getElementById("btn-workflow").disabled = data.generation_running;

  const list = document.getElementById("agents-list");
  list.innerHTML = data.agents
    .map(
      (a) => `
    <div class="card">
      <div class="flex items-start gap-3 mb-2">
        ${agentDot(a.status)}
        <div>
          <h3 class="font-semibold">${a.label}</h3>
          <p class="text-xs text-[var(--text-muted)]">${a.name}</p>
        </div>
      </div>
      <p class="text-sm text-[var(--text-muted)] mb-3">${a.description}</p>
      ${
        a.rag?.length
          ? `<p class="text-xs"><span class="text-[var(--text-muted)]">RAG:</span> ${a.rag.join(
              ", "
            )}</p>`
          : "<p class='text-xs text-[var(--text-muted)]'>Sin RAG directo</p>"
      }
    </div>`
    )
    .join("");

  const lastRun = document.getElementById("last-run-card");
  if (data.last_run) {
    lastRun.classList.remove("hidden");
    document.getElementById("last-run-content").innerHTML = `
      <p class="text-sm"><strong>Tema:</strong> ${data.last_run.theme || "—"}</p>
      <p class="text-sm"><strong>Estado:</strong> ${
        data.last_run.success === true
          ? "✓ Éxito"
          : data.last_run.success === false
          ? "✗ Error"
          : "En curso"
      }</p>
      <p class="text-sm text-[var(--text-muted)]">${formatDate(data.last_run.timestamp)}</p>
      ${data.last_run.message ? `<p class="text-sm mt-2">${data.last_run.message}</p>` : ""}
    `;
  }
}

async function loadServices() {
  const data = await api("/api/services/health");
  const sched = data.scheduler;
  document.getElementById("scheduler-info").innerHTML = `
    <p><strong>Estado:</strong> ${sched.status === "running" ? "🟢 En ejecución" : "⚪ Detenido"}</p>
    <p><strong>Horario:</strong> ${sched.schedule} (${sched.timezone})</p>
    <p><strong>Próxima ejecución:</strong> ${formatDate(sched.next_run)}</p>
  `;

  document.getElementById("services-grid").innerHTML = data.services
    .map(
      (s) => `
    <div class="card">
      <div class="flex justify-between items-start mb-2">
        <h3 class="font-semibold">${s.name}</h3>
        <span class="badge ${s.configured ? "badge-ready" : "badge-pending"}">${
        s.configured ? "Configurado" : "Falta API"
      }</span>
      </div>
      <p class="text-sm text-[var(--text-muted)] mb-2">${s.description}</p>
      ${
        s.masked_key
          ? `<p class="text-xs font-mono">${s.masked_key}</p>`
          : '<p class="text-xs text-[var(--text-muted)]">Sin clave configurada</p>'
      }
    </div>`
    )
    .join("");

  document.getElementById("docker-services").innerHTML = (data.docker || [])
    .map(
      (d) =>
        `<div class="flex justify-between py-2 border-b border-[var(--border)] last:border-0">
          <span>${d.name} <span class="text-xs text-[var(--text-muted)]">— ${d.role}</span></span>
          <span class="badge ${d.status === "running" ? "badge-ready" : "badge-unknown"}">${
          d.status
        }</span>
        </div>`
    )
    .join("");
}

async function loadPackages() {
  const data = await api("/api/content/packages?limit=50");
  const list = document.getElementById("packages-list");
  if (!data.packages?.length) {
    list.innerHTML =
      '<div class="card text-center text-[var(--text-muted)]">No hay paquetes generados. Usa Agentes → Generar contenido.</div>';
    return;
  }

  list.innerHTML = data.packages
    .map(
      (p) => `
    <div class="card flex flex-wrap items-center gap-4">
      ${
        p.thumbnail
          ? `<img src="/api/content/media/${p.thumbnail}" alt="" class="pkg-thumb">`
          : '<div class="pkg-thumb flex items-center justify-center text-2xl">📦</div>'
      }
      <div class="flex-1 min-w-[200px]">
        <p class="font-semibold">${p.name}</p>
        <p class="text-sm text-[var(--text-muted)]">${p.date} · Tema: ${p.theme}</p>
      </div>
      ${badge(p.status)}
      <div class="flex gap-2">
        <button class="btn btn-secondary btn-view" data-id="${p.id}">Ver detalle</button>
        <a href="/api/content/packages/${encodeURIComponent(p.id)}/download" class="btn btn-secondary">Descargar</a>
        <button class="btn btn-primary btn-publish" data-id="${p.id}">Publicar</button>
      </div>
    </div>`
    )
    .join("");

  list.querySelectorAll(".btn-view").forEach((btn) => {
    btn.addEventListener("click", () => showPackageDetail(btn.dataset.id));
  });
  list.querySelectorAll(".btn-publish").forEach((btn) => {
    btn.addEventListener("click", () => publishPackage(btn.dataset.id));
  });
}

async function showPackageDetail(id) {
  const pkg = await api(`/api/content/packages/${encodeURIComponent(id)}`);
  document.getElementById("modal-title").textContent = pkg.name || id;
  const imgs = (pkg.images || [])
    .map(
      (i) =>
        `<img src="/api/content/media/${i.path}" alt="${i.label}" class="rounded-lg max-h-40 border border-[var(--border)]">`
    )
    .join("");
  const caps = Object.entries(pkg.captions || {})
    .map(([pl, txt]) => {
      const preview = txt.length > 200 ? txt.slice(0, 200) + "…" : txt;
      return `<p class="text-sm"><strong>${pl}:</strong> ${escapeHtml(preview)}</p>`;
    })
    .join("");

  document.getElementById("modal-body").innerHTML = `
    <div class="mb-4">${badge(pkg.status)}</div>
    <p class="text-sm mb-3"><strong>Mensaje:</strong> ${escapeHtml(pkg.message || "—")}</p>
    <p class="text-sm mb-3"><strong>Hashtags:</strong> ${escapeHtml(pkg.hashtags || "—")}</p>
    <p class="text-sm mb-3"><strong>Ruta:</strong> <code class="text-xs">${escapeHtml(pkg.path)}</code></p>
    <div class="flex flex-wrap gap-2 mb-4">${imgs}</div>
    ${caps}
    <details class="mt-4"><summary class="cursor-pointer text-sm text-[var(--accent)]">manifest.json</summary>
      <pre class="text-xs mt-2 overflow-auto p-2 bg-[var(--bg-elevated)] rounded">${escapeHtml(
        JSON.stringify(pkg.manifest, null, 2)
      )}</pre>
    </details>
    <div class="flex gap-2 mt-4">
      <button class="btn btn-primary" id="modal-publish">Publicar paquete</button>
      <a href="/api/content/packages/${encodeURIComponent(id)}/download" class="btn btn-secondary">Descargar ZIP</a>
    </div>
  `;
  document.getElementById("package-modal").classList.add("open");
  document.getElementById("modal-publish").addEventListener("click", () => {
    publishPackage(id);
    document.getElementById("package-modal").classList.remove("open");
  });
}

async function publishPackage(id) {
  try {
    const res = await api(`/api/content/packages/${encodeURIComponent(id)}/publish`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    toast(res.message || "Publicación iniciada", "success");
  } catch (e) {
    toast(e.message, "error");
  }
}

async function loadAnalytics() {
  const [platforms, trends] = await Promise.all([
    api("/api/analytics/platforms"),
    api("/api/analytics/trends"),
  ]);

  const banner = document.getElementById("analytics-demo-banner");
  banner.classList.toggle("hidden", !trends.demo_mode);

  document.getElementById("platform-metrics").innerHTML = platforms.platforms
    .map(
      (p) => `
    <div class="card">
      <div class="flex justify-between mb-2">
        <h3 class="font-semibold">${p.label}</h3>
        ${
          p.connect_cta
            ? '<span class="badge badge-pending">Conectar API</span>'
            : '<span class="badge badge-ready">Conectado</span>'
        }
      </div>
      <p class="text-2xl font-bold">${p.metrics.followers?.toLocaleString("es")} <span class="text-sm font-normal text-[var(--text-muted)]">seguidores</span></p>
      <p class="text-sm text-[var(--text-muted)]">Engagement: ${p.metrics.engagement_rate}%</p>
      <p class="text-sm text-[var(--text-muted)]">Posts/semana: ${p.metrics.posts_this_week}</p>
    </div>`
    )
    .join("");

  const hashtags = document.getElementById("top-hashtags");
  hashtags.innerHTML = (trends.hashtags || [])
    .map(([tag, count]) => `<span class="badge badge-ready">${tag} (${count})</span>`)
    .join("");

  renderCharts(trends);
}

function renderCharts(trends) {
  const colors = {
    instagram: "#E1306C",
    tiktok: "#69C9D0",
    facebook: "#4267B2",
    youtube: "#FF0000",
    x: "#1DA1F2",
  };

  const platforms = Object.keys(trends.platforms || {});
  const labels = platforms.length ? trends.platforms[platforms[0]].dates : [];

  destroyCharts();

  const commonOpts = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: "#8fa896" } } },
    scales: {
      x: { ticks: { color: "#8fa896", maxTicksLimit: 8 }, grid: { color: "#2a3d34" } },
      y: { ticks: { color: "#8fa896" }, grid: { color: "#2a3d34" } },
    },
  };

  charts.followers = new Chart(document.getElementById("chart-followers"), {
    type: "line",
    data: {
      labels,
      datasets: platforms.map((p) => ({
        label: p,
        data: trends.platforms[p].followers,
        borderColor: colors[p] || "#5a9a6e",
        tension: 0.3,
        fill: false,
      })),
    },
    options: commonOpts,
  });

  charts.engagement = new Chart(document.getElementById("chart-engagement"), {
    type: "line",
    data: {
      labels,
      datasets: platforms.map((p) => ({
        label: p,
        data: trends.platforms[p].engagement_rate,
        borderColor: colors[p] || "#5a9a6e",
        tension: 0.3,
      })),
    },
    options: commonOpts,
  });

  charts.posts = new Chart(document.getElementById("chart-posts"), {
    type: "bar",
    data: {
      labels,
      datasets: platforms.map((p) => ({
        label: p,
        data: trends.platforms[p].posts_per_week,
        backgroundColor: (colors[p] || "#5a9a6e") + "88",
      })),
    },
    options: commonOpts,
  });
}

function destroyCharts() {
  Object.values(charts).forEach((c) => c?.destroy());
  charts = {};
}

function updateDemoBadge(demo) {
  const badge = document.getElementById("demo-badge");
  badge.textContent = demo ? "Modo Demo" : "Producción";
  badge.className = demo ? "badge badge-pending" : "badge badge-ready";
}

function updateDemoToggle(demo) {
  const toggle = document.getElementById("demo-toggle");
  toggle.classList.toggle("on", demo);
  toggle.setAttribute("aria-checked", demo);
  document.getElementById("demo-label").textContent = demo ? "Activado" : "Desactivado";
}

function formatDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("es-ES");
  } catch {
    return iso;
  }
}

function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

async function refreshAll() {
  try {
    await loadDashboard();
    const active = document.querySelector(".nav-item.active")?.dataset.section;
    if (active === "agentes") await loadAgents();
    if (active === "servicios") await loadServices();
    if (active === "material") await loadPackages();
    if (active === "estadisticas") await loadAnalytics();
  } catch (e) {
    toast("Error al cargar datos: " + e.message, "error");
  }
}

document.querySelectorAll(".nav-item").forEach((el) => {
  el.addEventListener("click", () => navigate(el.dataset.section));
});

document.getElementById("refresh-btn").addEventListener("click", refreshAll);

document.getElementById("menu-btn")?.addEventListener("click", () => {
  document.getElementById("sidebar").classList.add("open");
  document.getElementById("mobile-overlay").classList.add("open");
});

document.getElementById("mobile-overlay").addEventListener("click", () => {
  document.getElementById("sidebar").classList.remove("open");
  document.getElementById("mobile-overlay").classList.remove("open");
});

document.getElementById("modal-close").addEventListener("click", () => {
  document.getElementById("package-modal").classList.remove("open");
});

document.getElementById("demo-toggle").addEventListener("click", async () => {
  const on = document.getElementById("demo-toggle").classList.contains("on");
  try {
    await api("/api/agents/demo-mode", {
      method: "POST",
      body: JSON.stringify({ enabled: !on }),
    });
    updateDemoToggle(!on);
    updateDemoBadge(!on);
    toast(!on ? "Modo demo activado" : "Modo producción activado");
  } catch (e) {
    toast(e.message, "error");
  }
});

async function triggerGenerate(workflow = false) {
  const theme = document.getElementById("theme-input").value.trim() || null;
  const endpoint = workflow ? "/api/agents/workflow" : "/api/agents/generate";
  try {
    const res = await api(endpoint, {
      method: "POST",
      body: JSON.stringify({ theme }),
    });
    if (!res.ok) {
      toast(res.message, "warning");
      return;
    }
    toast(res.message, "success");
    setTimeout(refreshAll, 2000);
  } catch (e) {
    toast(e.message, "error");
  }
}

document.getElementById("btn-generate").addEventListener("click", () => triggerGenerate(false));
document.getElementById("btn-workflow").addEventListener("click", () => triggerGenerate(true));

refreshAll();
refreshTimer = setInterval(refreshAll, 30000);
