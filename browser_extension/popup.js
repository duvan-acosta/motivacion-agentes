// Mapeo de dominio → nombre de plataforma
const PLATFORM_MAP = {
  "google.com":    "google",
  "youtube.com":   "youtube",
  "tiktok.com":    "tiktok",
  "instagram.com": "instagram",
  "x.com":         "twitter",
  "twitter.com":   "twitter",
  "facebook.com":  "facebook",
};

function detectPlatform(hostname) {
  for (const [domain, name] of Object.entries(PLATFORM_MAP)) {
    if (hostname.endsWith(domain)) return name;
  }
  return null;
}

function setStatus(msg, type = "pending") {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.className = type;
}

function showInfo(platform, cookieCount) {
  document.getElementById("info").innerHTML = `
    <div class="platform">
      <span class="name">${platform}</span>
      <span class="val">${cookieCount} cookies</span>
    </div>
  `;
}

async function exportSession() {
  setStatus("Obteniendo pestaña activa...", "pending");

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.url) {
    setStatus("No se pudo obtener la URL de la pestaña", "err");
    return;
  }

  const url = new URL(tab.url);
  const platform = detectPlatform(url.hostname);

  if (!platform) {
    setStatus(`Sitio no reconocido: ${url.hostname}\nNavega a Google, YouTube, TikTok, Instagram, X o Facebook`, "err");
    return;
  }

  setStatus(`Leyendo cookies de ${platform}...`, "pending");

  // Obtener todas las cookies del dominio actual
  const cookies = await chrome.cookies.getAll({ domain: url.hostname.replace(/^www\./, "") });

  // Para Google también capturar subdominios
  let allCookies = [...cookies];
  if (platform === "google" || platform === "youtube") {
    const extra = await chrome.cookies.getAll({ domain: ".google.com" });
    const seen = new Set(allCookies.map(c => c.name + "|" + c.domain));
    for (const c of extra) {
      if (!seen.has(c.name + "|" + c.domain)) allCookies.push(c);
    }
  }

  if (allCookies.length === 0) {
    setStatus(`Sin cookies en ${platform} — ¿estás logueado?`, "err");
    return;
  }

  setStatus(`Enviando ${allCookies.length} cookies al servidor local...`, "pending");

  // Convertir cookies al formato que espera Playwright (sameSite como string)
  const playwrightCookies = allCookies.map(c => ({
    name:     c.name,
    value:    c.value,
    domain:   c.domain,
    path:     c.path,
    expires:  c.expirationDate || -1,
    httpOnly: c.httpOnly,
    secure:   c.secure,
    sameSite: c.sameSite === "no_restriction" ? "None"
             : c.sameSite === "lax"           ? "Lax"
             : c.sameSite === "strict"         ? "Strict"
             : "Lax",
  }));

  try {
    const resp = await fetch("http://localhost:7788/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ platform, cookies: playwrightCookies }),
    });

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const result = await resp.json();

    setStatus(`✓ ${result.message}`, "ok");
    showInfo(platform, allCookies.length);
  } catch (err) {
    setStatus(
      `Error al enviar: ${err.message}\n\nAsegúrate de que el servidor local está corriendo:\n  python collect_cookies.py`,
      "err"
    );
  }
}

document.getElementById("btn").addEventListener("click", exportSession);
