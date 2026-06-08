const API = {
  summary: () => fetch('/api/dashboard/summary').then(r => r.json()),
  agents: () => fetch('/api/agents').then(r => r.json()),
  generate: (body) => fetch('/api/agents/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(r => r.json()),
  workflow: (body) => fetch('/api/agents/workflow', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(r => r.json()),
  demoMode: (enabled) => fetch('/api/agents/demo-mode', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ enabled }) }).then(r => r.json()),
  health: () => fetch('/api/services/health').then(r => r.json()),
  packages: (params) => fetch('/api/content/packages?' + new URLSearchParams(params)).then(r => r.json()),
  package: (id) => fetch('/api/content/packages/' + encodeURIComponent(id)).then(r => r.json()),
  publish: (id, platforms) => fetch('/api/content/packages/' + encodeURIComponent(id) + '/publish', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ platforms }) }).then(r => r.json()),
  analyticsPlatforms: () => fetch('/api/analytics/platforms').then(r => r.json()),
  analyticsTrends: (platform) => fetch('/api/analytics/trends?' + new URLSearchParams(platform ? { platform } : {})).then(r => r.json()),
};

let charts = {};
let refreshInterval = null;

function toast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = 'toast ' + type;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

function badge(status) {
  const map = { ready: 'badge-ready', pending: 'badge-pending', published: 'badge-published', manual: 'badge-manual', failed: 'badge-failed', idle: 'badge-idle', running: 'badge-running', error: 'badge-error', ok: 'badge-ok', missing: 'badge-missing', stub: 'badge-stub', optional: 'badge-stub' };
  return `<span class="badge ${map[status] || 'badge-idle'}">${status}</span>`;
}

function formatTime(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleString('es-ES', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  } catch { return iso; }
}

function navTo(sectionId) {
  document.querySelectorAll('.nav-item').forEach(n => n.classList.toggle('active', n.dataset.section === sectionId));
  document.querySelectorAll('.section').forEach(s => s.classList.toggle('active', s.id === sectionId));
  loadSection(sectionId);
}

async function loadSection(id) {
  try {
    switch (id) {
      case 'inicio': await loadDashboard(); break;
      case 'agentes': await loadAgents(); break;
      case 'servicios': await loadServices(); break;
      case 'material': await loadMaterial(); break;
      case 'estadisticas': await loadAnalytics(); break;
    }
  } catch (e) {
    toast('Error al cargar datos: ' + e.message, 'error');
  }
}

async function loadDashboard() {
  const data = await API.summary();
  const p = data.packages;
  document.getElementById('stat-total').textContent = p.total;
  document.getElementById('stat-ready').textContent = p.ready;
  document.getElementById('stat-pending').textContent = p.pending;
  document.getElementById('stat-published').textContent = p.published;
  document.getElementById('stat-manual').textContent = p.manual;

  const feed = document.getElementById('activity-feed');
  if (!data.recent_activity.length) {
    feed.innerHTML = '<li><span class="activity-time">—</span><span>Sin actividad reciente</span></li>';
  } else {
    feed.innerHTML = data.recent_activity.map(a =>
      `<li><span class="activity-time">${formatTime(a.timestamp)}</span><span>${a.message}</span></li>`
    ).join('');
  }

  const agentsEl = document.getElementById('agent-indicators');
  agentsEl.innerHTML = data.agent_status.map(a =>
    `<div class="agent-card"><h4>${a.label} ${badge(a.status)}</h4><div class="agent-meta"><span>Tema: ${a.theme || '—'}</span></div></div>`
  ).join('');
}

async function loadAgents() {
  const data = await API.agents();
  document.getElementById('demo-toggle').checked = data.demo_mode;

  const grid = document.getElementById('agents-grid');
  grid.innerHTML = data.agents.map(a => `
    <div class="agent-card">
      <h4>${a.label} ${badge(a.status)}</h4>
      <p>${a.description}</p>
      <div class="rag-tags">${a.rag_collections.map(c => `<span class="rag-tag">${c}</span>`).join('') || '<span class="rag-tag">sin RAG</span>'}</div>
      <div class="agent-meta">
        <span>Última ejecución: ${formatTime(a.last_run)}</span>
        <span>Tema: ${a.theme || '—'}</span>
        ${a.last_error ? `<span style="color:var(--error)">Error: ${a.last_error}</span>` : ''}
      </div>
    </div>
  `).join('');

  const tasksEl = document.getElementById('tasks-list');
  if (!data.tasks.length) {
    tasksEl.innerHTML = '<p style="color:var(--text-muted);font-size:0.85rem">Sin tareas recientes</p>';
  } else {
    tasksEl.innerHTML = data.tasks.map(t =>
      `<div class="service-row"><span class="name">${t.type} — ${badge(t.status)}</span><span class="detail">${formatTime(t.started_at)} — ${t.message}</span></div>`
    ).join('');
  }
}

async function loadServices() {
  const data = await API.health();

  document.getElementById('services-list').innerHTML = data.services.map(s => `
    <div class="service-row">
      <div>
        <div class="name">${s.name} ${badge(s.status)}</div>
        <div class="detail">${s.message}</div>
        <div class="key-list">${Object.entries(s.keys).map(([k, v]) => `${k}: ${v.configured ? v.masked : '— no configurada'}`).join(' · ')}</div>
      </div>
    </div>
  `).join('');

  const sched = data.scheduler;
  document.getElementById('scheduler-info').innerHTML = `
    <div class="service-row">
      <div><div class="name">Scheduler ${badge(sched.status)}</div>
      <div class="detail">Generación diaria a las ${sched.schedule} (${sched.timezone})</div>
      <div class="detail">Próxima ejecución: ${formatTime(sched.next_run)}</div>
      <div class="detail">${sched.note}</div></div>
    </div>`;

  document.getElementById('docker-services').innerHTML = data.docker_services.map(s =>
    `<div class="service-row"><span class="name">${s.name}</span>${badge(s.status)}</div>`
  ).join('');
}

async function loadMaterial() {
  const dateFilter = document.getElementById('filter-date').value;
  const statusFilter = document.getElementById('filter-status').value;
  const params = {};
  if (dateFilter) params.date = dateFilter;
  if (statusFilter) params.status = statusFilter;

  const data = await API.packages(params);
  const dateSelect = document.getElementById('filter-date');
  const currentDate = dateSelect.value;
  dateSelect.innerHTML = '<option value="">Todas las fechas</option>' +
    data.dates.map(d => `<option value="${d}" ${d === currentDate ? 'selected' : ''}>${d}</option>`).join('');

  const tbody = document.getElementById('packages-tbody');
  if (!data.packages.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted)">Sin paquetes generados</td></tr>';
    return;
  }

  tbody.innerHTML = data.packages.map(p => {
    const img = p.preview_image
      ? `<img class="package-preview" src="/api/content/media/${encodeURIComponent(p.id)}/${p.preview_image}" alt="preview">`
      : '<div class="package-preview"></div>';
    return `<tr>
      <td>${img}</td>
      <td><strong>${p.package_id}</strong><br><small style="color:var(--text-muted)">${p.date}</small></td>
      <td>${p.theme}</td>
      <td>${badge(p.status)}</td>
      <td>${formatTime(p.generated_at)}</td>
      <td>
        <button class="btn btn-sm btn-secondary" onclick="viewPackage('${p.id}')">Ver</button>
        <button class="btn btn-sm btn-primary" onclick="publishPackage('${p.id}')" ${p.status === 'published' ? 'disabled' : ''}>Publicar</button>
        <a class="btn btn-sm btn-secondary" href="/api/content/packages/${encodeURIComponent(p.id)}/download">Descargar</a>
      </td>
    </tr>`;
  }).join('');
}

async function viewPackage(id) {
  try {
    const p = await API.package(id);
    document.getElementById('modal-title').textContent = p.package_id || p.id;
    const imgEl = document.getElementById('modal-preview');
    if (p.preview_image) {
      imgEl.src = `/api/content/media/${encodeURIComponent(p.id)}/${p.preview_image}`;
      imgEl.style.display = 'block';
    } else {
      imgEl.style.display = 'none';
    }

    document.getElementById('modal-body').innerHTML = `
      <p style="margin-bottom:0.75rem">${badge(p.status)} · Tema: <strong>${p.theme}</strong></p>
      <p style="font-style:italic;margin-bottom:1rem;color:var(--accent-mist)">"${p.message}"</p>
      <h4 style="margin-bottom:0.5rem;font-size:0.85rem;color:var(--text-muted)">Captions y textos</h4>
      ${Object.entries(p.captions).map(([k, v]) => `<div class="caption-block"><strong>${k}</strong>${v}</div>`).join('')}
      <h4 style="margin:1rem 0 0.5rem;font-size:0.85rem;color:var(--text-muted)">Ruta</h4>
      <code style="font-size:0.75rem;color:var(--text-muted)">${p.path}</code>
      <h4 style="margin:1rem 0 0.5rem;font-size:0.85rem;color:var(--text-muted)">Manifest</h4>
      <pre style="background:var(--bg-deep);padding:0.75rem;border-radius:8px;font-size:0.7rem;overflow:auto;max-height:200px">${JSON.stringify(p.manifest, null, 2)}</pre>
    `;
    document.getElementById('modal-overlay').classList.add('active');
    document.getElementById('modal-publish-btn').onclick = () => publishPackage(id);
  } catch (e) {
    toast('Error al cargar paquete', 'error');
  }
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('active');
}

async function publishPackage(id) {
  try {
    const res = await API.publish(id, null);
    toast(res.message, 'success');
    closeModal();
    loadMaterial();
  } catch (e) {
    toast('Error al publicar', 'error');
  }
}

async function loadAnalytics() {
  const [platforms, trends] = await Promise.all([API.analyticsPlatforms(), API.analyticsTrends()]);

  const hasDemo = platforms.platforms.some(p => p.demo);
  document.getElementById('analytics-demo-banner').style.display = hasDemo ? 'flex' : 'none';

  document.getElementById('platform-metrics').innerHTML = platforms.platforms.map(p => `
    <div class="platform-metric-card">
      <h4>${p.platform} ${p.demo ? '<span class="badge badge-stub">demo</span>' : badge('ok')}</h4>
      <div class="metric-row"><span>Seguidores</span><span class="val">${p.followers.toLocaleString('es-ES')}</span></div>
      <div class="metric-row"><span>Cambio 7d</span><span class="val">+${p.followers_change_7d}</span></div>
      <div class="metric-row"><span>Engagement</span><span class="val">${p.engagement_rate}%</span></div>
      <div class="metric-row"><span>Posts/semana</span><span class="val">${p.posts_this_week}</span></div>
      ${p.demo ? '<button class="btn btn-sm btn-secondary" style="margin-top:0.5rem" onclick="toast(\'Configura las API keys en .env\',\'info\')">Conectar API</button>' : ''}
    </div>
  `).join('');

  renderCharts(trends.platforms[0] || trends.platforms);
}

function renderCharts(platformData) {
  const data = Array.isArray(platformData) ? platformData[0] : platformData;
  if (!data) return;

  const chartOpts = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: '#8b9cb3' } } },
    scales: {
      x: { ticks: { color: '#8b9cb3', maxTicksLimit: 10 }, grid: { color: '#2d3a4d' } },
      y: { ticks: { color: '#8b9cb3' }, grid: { color: '#2d3a4d' } },
    },
  };

  if (charts.followers) charts.followers.destroy();
  charts.followers = new Chart(document.getElementById('chart-followers'), {
    type: 'line',
    data: {
      labels: data.labels,
      datasets: [{ label: 'Seguidores', data: data.datasets.followers, borderColor: '#7d9b76', backgroundColor: 'rgba(125,155,118,0.1)', fill: true, tension: 0.3 }],
    },
    options: chartOpts,
  });

  if (charts.engagement) charts.engagement.destroy();
  charts.engagement = new Chart(document.getElementById('chart-engagement'), {
    type: 'line',
    data: {
      labels: data.labels,
      datasets: [{ label: 'Engagement %', data: data.datasets.engagement_rate, borderColor: '#4a8f8f', backgroundColor: 'rgba(74,143,143,0.1)', fill: true, tension: 0.3 }],
    },
    options: chartOpts,
  });

  if (charts.posts) charts.posts.destroy();
  charts.posts = new Chart(document.getElementById('chart-posts'), {
    type: 'bar',
    data: {
      labels: data.labels,
      datasets: [{ label: 'Posts/día', data: data.datasets.posts_per_day, backgroundColor: '#c4a35a' }],
    },
    options: chartOpts,
  });

  const hashtags = data.top_hashtags || [];
  document.getElementById('top-hashtags').innerHTML = hashtags.map(h =>
    `<div class="service-row"><span class="name">${h.tag}</span><span class="detail">${h.count} usos</span></div>`
  ).join('');
}

async function triggerGenerate() {
  const theme = document.getElementById('theme-input').value || null;
  const demo = document.getElementById('demo-toggle').checked;
  try {
    const res = await API.generate({ theme, demo });
    toast(res.message, 'success');
    setTimeout(() => { loadAgents(); loadDashboard(); }, 2000);
  } catch (e) {
    toast('Error al iniciar generación', 'error');
  }
}

async function triggerWorkflow() {
  const theme = document.getElementById('theme-input').value || null;
  const demo = document.getElementById('demo-toggle').checked;
  try {
    const res = await API.workflow({ theme, demo });
    toast(res.message, 'success');
    setTimeout(() => { loadAgents(); loadDashboard(); }, 2000);
  } catch (e) {
    toast('Error al iniciar workflow', 'error');
  }
}

async function toggleDemoMode() {
  const enabled = document.getElementById('demo-toggle').checked;
  try {
    await API.demoMode(enabled);
    toast(`Modo ${enabled ? 'demo' : 'producción'} activado`, 'info');
  } catch (e) {
    toast('Error al cambiar modo', 'error');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => navTo(item.dataset.section));
  });

  document.getElementById('btn-generate').addEventListener('click', triggerGenerate);
  document.getElementById('btn-workflow').addEventListener('click', triggerWorkflow);
  document.getElementById('demo-toggle').addEventListener('change', toggleDemoMode);
  document.getElementById('filter-date').addEventListener('change', loadMaterial);
  document.getElementById('filter-status').addEventListener('change', loadMaterial);
  document.getElementById('modal-close').addEventListener('click', closeModal);
  document.getElementById('modal-overlay').addEventListener('click', (e) => {
    if (e.target.id === 'modal-overlay') closeModal();
  });

  navTo('inicio');
  refreshInterval = setInterval(() => {
    const active = document.querySelector('.section.active');
    if (active) loadSection(active.id);
  }, 30000);
});
