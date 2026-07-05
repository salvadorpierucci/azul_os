// ─── WHATSAPP ───
window.checkWhatsAppStatus = async function() {
  const url = document.getElementById("wa-url").value;
  const key = document.getElementById("wa-key").value;
  const instance = document.getElementById("wa-instance").value || "mi-whatsapp";
  if (!url) { toast("Ingresa la URL de Evolution API", "error"); return; }
  try {
    const r = await fetch(`${url}/instance/fetchInstances`, { headers: key ? { "apikey": key } : {} });
    if (r.ok) {
      const instances = await r.json();
      const myInst = instances.find(i => i.name === instance);
      if (myInst && myInst.connectionStatus === "open") {
        document.getElementById("wa-status-dot").className = "w-3 h-3 rounded-full bg-green-500";
        document.getElementById("wa-status-text").textContent = `Conectado (${myInst.name} - ${myInst.ownerJid})`;
        document.getElementById("wa-status-detail").classList.remove("hidden");
        document.getElementById("wa-status-detail").textContent = `Numero: ${myInst.ownerJid || "—"} | Estado: ${myInst.connectionStatus}`;
      } else {
        document.getElementById("wa-status-dot").className = "w-3 h-3 rounded-full bg-yellow-500";
        document.getElementById("wa-status-text").textContent = `Instancia ${instance} no conectada`;
      }
    } else { throw new Error("Error"); }
  } catch {
    document.getElementById("wa-status-dot").className = "w-3 h-3 rounded-full bg-red-500";
    document.getElementById("wa-status-text").textContent = "Error de conexion";
    document.getElementById("wa-status-detail").classList.add("hidden");
  }
};

window.configWhatsAppWebhook = async function() {
  const url = document.getElementById("wa-url").value;
  const key = document.getElementById("wa-key").value;
  const instance = document.getElementById("wa-instance").value || "mi-whatsapp";
  if (!url) { toast("Ingresa la URL de Evolution API primero", "error"); return; }
  try {
    const r = await fetch(`${url}/webhook/set/${instance}`, { method: "POST", headers: { "Content-Type": "application/json", apikey: key }, body: JSON.stringify({ webhook: { url: `${BASE_URL}/whatsapp/webhook`, enabled: true, events: ["messages.upsert"] } }) });
    if (r.ok) { toast("Webhook configurado correctamente"); } else { toast("Error configurando webhook: " + await r.text(), "error"); }
  } catch { toast("No se pudo conectar con Evolution API", "error"); }
};

async function loadWhatsAppConfig() {
  try {
    const res = await fetch(`${BASE_URL}/whatsapp/admin/config`);
    const config = await res.json();
    const active = document.getElementById("wa-bot-active");
    active.checked = config.bot_activo === "true";
    document.getElementById("wa-bot-status-label").textContent = active.checked ? "Bot activo" : "Bot pausado";
    document.getElementById("wa-saludo-texto").value = config.saludo_texto || "¡Hola! Soy el asistente de Azul Alquileres";
    document.getElementById("wa-menu-texto").value = config.menu_texto || "Comandos disponibles:...";
    document.getElementById("wa-recordatorio-hs").value = config.recordatorio_hs || "48";
    document.getElementById("cmd-stock").checked = config.comando_stock === "true";
    document.getElementById("cmd-disponible").checked = config.comando_disponible === "true";
    document.getElementById("cmd-eventos").checked = config.comando_eventos === "true";
    document.getElementById("cmd-presupuesto").checked = config.comando_presupuesto === "true";
  } catch { /* silent fail on first load */ }
}

window.toggleBotActive = async function() {
  const active = document.getElementById("wa-bot-active");
  const label = document.getElementById("wa-bot-status-label"); label.textContent = active.checked ? "Bot activo" : "Bot pausado";
  try { await fetch(`${BASE_URL}/whatsapp/admin/config`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ clave: "bot_activo", valor: active.checked ? "true" : "false" }) }); toast(active.checked ? "Bot activado" : "Bot pausado"); }
  catch { toast("Error guardando configuracion", "error"); }
};

window.saveBotMessages = async function() {
  const saludo = document.getElementById("wa-saludo-texto").value;
  const menu = document.getElementById("wa-menu-texto").value;
  try {
    await fetch(`${BASE_URL}/whatsapp/admin/config`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ clave: "saludo_texto", valor: saludo }) });
    await fetch(`${BASE_URL}/whatsapp/admin/config`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ clave: "menu_texto", valor: menu }) });
    toast("Mensajes guardados");
  } catch { toast("Error guardando mensajes", "error"); }
};

window.toggleComando = async function(clave) {
  const el = document.getElementById(clave === "comando_stock" ? "cmd-stock" : clave === "comando_disponible" ? "cmd-disponible" : clave === "comando_eventos" ? "cmd-eventos" : "cmd-presupuesto");
  const valor = el.checked ? "true" : "false";
  try { await fetch(`${BASE_URL}/whatsapp/admin/config`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ clave, valor }) }); }
  catch { toast("Error actualizando comando", "error"); }
};

window.saveRecordatorio = async function() {
  const hs = document.getElementById("wa-recordatorio-hs").value;
  try { await fetch(`${BASE_URL}/whatsapp/admin/config`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ clave: "recordatorio_hs", valor: String(hs) }) }); toast(`Recordatorio configurado a ${hs} horas`); }
  catch { toast("Error guardando recordatorio", "error"); }
};

window.sendTestMessage = async function() {
  const numero = document.getElementById("wa-test-numero").value;
  const texto = document.getElementById("wa-test-texto").value;
  if (!numero || !texto) { toast("Completa numero y mensaje", "error"); return; }
  try {
    const res = await fetch(`${BASE_URL}/whatsapp/enviar/${encodeURIComponent(numero)}?texto=${encodeURIComponent(texto)}`);
    const data = await res.json();
    const detail = document.getElementById("wa-test-result"); detail.classList.remove("hidden");
    if (data.ok) { detail.textContent = "✅ Mensaje enviado"; detail.className = "mt-2 text-xs text-green-600"; }
    else { detail.textContent = "❌ " + (data.error || "Error al enviar"); detail.className = "mt-2 text-xs text-red-500"; }
  } catch {
    document.getElementById("wa-test-result").classList.remove("hidden");
    document.getElementById("wa-test-result").textContent = "❌ Error de conexion con el servidor";
    document.getElementById("wa-test-result").className = "mt-2 text-xs text-red-500";
  }
};

// Load config on navigate to whatsapp page
const _origNavigate = window.navigate;
window.navigate = function(page, data) {
  if (typeof _origNavigate === "function") _origNavigate(page, data);
  if (page === "whatsapp") setTimeout(loadWhatsAppConfig, 100);
};
