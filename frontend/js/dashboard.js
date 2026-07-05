// ─── DASHBOARD ───
async function loadDashboard() {
  const eventos = await apiGet("/eventos/");
  const finanzas = await apiGet("/finanzas/resumen/mensual");
  const mobiliario = await apiGet("/mobiliario/");

  const ahora = new Date();
  const proximos = eventos.filter(e => new Date(e.fecha) >= ahora && e.estado !== "cancelado").slice(0, 10);
  const reservas = eventos.filter(e => e.estado === "reserva").length;
  const alertas = mobiliario.filter(m => m.stock_disponible <= 1).length;

  document.getElementById("kpi-proximos").textContent = proximos.length;
  document.getElementById("kpi-reservas").textContent = reservas;
  document.getElementById("kpi-ingresos").textContent = `$${finanzas.ingresos?.toLocaleString("es-AR") || 0}`;
  document.getElementById("kpi-alertas").textContent = alertas;

  const cont = document.getElementById("dashboard-eventos");
  cont.innerHTML = proximos.length === 0
    ? '<p class="text-charcoal/40">No hay eventos proximos</p>'
    : proximos.map(e => {
      const color = e.estado === "confirmado" ? "bg-primary" : "bg-yellow-400";
      const fecha = new Date(e.fecha).toLocaleDateString("es-AR", { day:"2-digit", month:"short" });
      return \`<div class="flex items-center gap-3 py-2 border-b border-ivory-dark last:border-0 cursor-pointer hover:bg-ivory-dark/50 rounded px-1" onclick="navigate('eventos')">
        <span class="w-2 h-2 rounded-full ${color} flex-shrink-0"></span>
        <span class="font-medium">\${e.titulo}</span>
        <span class="text-charcoal/40 ml-auto">\${fecha}</span>
      </div>\`;
    }).join("");
}
