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

function downloadJson(filename, data) {
  const json = JSON.stringify(data, null, 2);
  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function exportSession() {
  setStatus("Obteniendo pestaña activa...", "pending");

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.url) { setStatus("No se pudo obtener la URL", "err"); return; }

  const url = new URL(tab.url);
  const platform = detectPlatform(url.hostname);

  if (!platform) {
    setStatus(`Sitio no reconocido:\n${url.hostname}\n\nNavega a: google.com, youtube.com,\ntiktok.com, instagram.com, x.com\no facebook.com`, "err");
    return;
  }

  setStatus(`Leyendo cookies de ${platform}...`, "pending");

  const baseDomain = url.hostname.replace(/^(www\.|studio\.)/, "");
  let allCookies = await chrome.cookies.getAll({ domain: baseDomain });

  // Para Google/YouTube incluir también .google.com
  if (platform === "google" || platform === "youtube") {
    const extra = await chrome.cookies.getAll({ domain: ".google.com" });
    const seen = new Set(allCookies.map(c => c.name + "|" + c.domain));
    for (const c of extra) {
      if (!seen.has(c.name + "|" + c.domain)) allCookies.push(c);
    }
  }

  if (allCookies.length === 0) {
    setStatus(`Sin cookies en ${platform}.\n¿Estás logueado en esta pestaña?`, "err");
    return;
  }

  // Formato Playwright
  const playwrightCookies = allCookies.map(c => ({
    name:     c.name,
    value:    c.value,
    domain:   c.domain,
    path:     c.path,
    expires:  c.expirationDate ?? -1,
    httpOnly: c.httpOnly,
    secure:   c.secure,
    sameSite: c.sameSite === "no_restriction" ? "None"
             : c.sameSite === "lax"           ? "Lax"
             : c.sameSite === "strict"         ? "Strict"
             : "Lax",
  }));

  try {
    downloadJson(`me_session_${platform}.json`, playwrightCookies);
    setStatus(`✓ Descargado: me_session_${platform}.json\n(${allCookies.length} cookies)\n\nLuego ejecuta:\npython import_sessions.py`, "ok");
  } catch (err) {
    setStatus(`Error: ${err.message}`, "err");
  }
}

document.getElementById("btn").addEventListener("click", exportSession);
