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

async function exportSession() {
  setStatus("Obteniendo pestaña activa...", "pending");

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.url) { setStatus("No se pudo obtener la URL", "err"); return; }

  const url = new URL(tab.url);
  const platform = detectPlatform(url.hostname);

  if (!platform) {
    setStatus(`Sitio no reconocido: ${url.hostname}\nNavega a Google, YouTube, TikTok, Instagram, X o Facebook`, "err");
    return;
  }

  setStatus(`Leyendo cookies de ${platform}...`, "pending");

  // Leer cookies — incluir subdominios
  const baseDomain = url.hostname.replace(/^(www\.|studio\.)/, "");
  let allCookies = await chrome.cookies.getAll({ domain: baseDomain });

  // Para Google/YouTube capturar también .google.com
  if (platform === "google" || platform === "youtube") {
    const extra = await chrome.cookies.getAll({ domain: ".google.com" });
    const seen = new Set(allCookies.map(c => c.name + "|" + c.domain));
    for (const c of extra) {
      if (!seen.has(c.name + "|" + c.domain)) allCookies.push(c);
    }
  }

  if (allCookies.length === 0) {
    setStatus(`Sin cookies en ${platform}. ¿Estás logueado?`, "err");
    return;
  }

  // Convertir al formato Playwright
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

  // Descargar como JSON — va directo a la carpeta de Descargas
  const json = JSON.stringify(playwrightCookies, null, 2);
  const blob = new Blob([json], { type: "application/json" });
  const blobUrl = URL.createObjectURL(blob);
  const filename = `me_session_${platform}.json`;

  try {
    await chrome.downloads.download({
      url: blobUrl,
      filename,
      saveAs: false,   // descarga automática sin diálogo
      conflictAction: "overwrite",
    });
    setStatus(`✓ Descargado: ${filename}\n(${allCookies.length} cookies)\n\nEjecuta: python import_sessions.py`, "ok");
  } catch (err) {
    setStatus(`Error al descargar: ${err.message}`, "err");
  } finally {
    URL.revokeObjectURL(blobUrl);
  }
}

document.getElementById("btn").addEventListener("click", exportSession);
