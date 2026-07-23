// ─── DASHBOARD ───

const _DASH_MESES_CORTOS = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"];
function _dashFecha(fechaStr) {
  if (!fechaStr) return "—";
  const m = String(fechaStr).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return fechaStr;
  return `${m[3]} ${_DASH_MESES_CORTOS[parseInt(m[2],10)-1]}`;
}

async function loadDashboard() {
  // Cargar cada endpoint independientemente con try/catch
  let eventos = [];
  let finanzas = { ingresos: 0 };
  let mobiliario = [];

  try { eventos = await apiGet("/eventos/") || []; } catch (e) { console.error("Dashboard: error eventos", e); }
  try { finanzas = await apiGet("/finanzas/resumen/mensual") || { ingresos: 0 }; } catch (e) { console.error("Dashboard: error finanzas", e); }
  try { mobiliario = await apiGet("/mobiliario/") || []; } catch (e) { console.error("Dashboard: error mobiliario", e); }

  const ahora = new Date();
  const proximos = eventos.filter(e => new Date(e.fecha) >= ahora && e.estado !== "cancelado").slice(0, 10);
  const reservas = eventos.filter(e => e.estado === "reserva").length;
  const alertas = mobiliario.filter(m => m.stock_disponible <= 1).length;

  const elProx = document.getElementById("kpi-proximos");
  if (elProx) elProx.textContent = proximos.length;
  const elRes = document.getElementById("kpi-reservas");
  if (elRes) elRes.textContent = reservas;
  const elIng = document.getElementById("kpi-ingresos");
  if (elIng) elIng.textContent = `$${finanzas.ingresos?.toLocaleString("es-AR") || 0}`;
  const elAlertas = document.getElementById("kpi-alertas");
  if (elAlertas) elAlertas.textContent = alertas;

  const cont = document.getElementById("dashboard-eventos");
  if (!cont) return;
  cont.innerHTML = proximos.length === 0
    ? '<p class="text-charcoal/40">No hay eventos proximos</p>'
    : proximos.map(e => {
      const color = e.estado === "confirmado" ? "bg-primary" : "bg-yellow-400";
      const fecha = _dashFecha(e.fecha);
      return `<div class="flex items-center gap-3 py-2 border-b border-ivory-dark last:border-0 cursor-pointer hover:bg-ivory-dark/50 rounded px-1" onclick="navigate('eventos')">
        <span class="w-2 h-2 rounded-full ${color} flex-shrink-0"></span>
        <span class="font-medium">${e.titulo || "Evento"}</span>
        <span class="text-charcoal/40 ml-auto">${fecha}</span>
      </div>`;
    }).join("");
}
