// ─── CALENDARIO ───
async function loadCalendario() {
  const now = new Date();
  calYear = calYear || now.getFullYear();
  calMonth = calMonth || now.getMonth();
  renderCalendar();
}

function changeMonth(delta) {
  calMonth += delta;
  if (calMonth > 11) { calMonth = 0; calYear++; }
  if (calMonth < 0) { calMonth = 11; calYear--; }
  renderCalendar();
}

async function renderCalendar() {
  const eventos = await apiGet("/eventos/");
  const meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
  document.getElementById("calendar-month").textContent = `${meses[calMonth]} ${calYear}`;

  const firstDay = new Date(calYear, calMonth, 1).getDay();
  const daysInMonth = new Date(calYear, calMonth + 1, 0).getDate();
  const today = new Date();

  const evMap = {};
  eventos.forEach(e => {
    const d = new Date(e.fecha);
    if (d.getFullYear() === calYear && d.getMonth() === calMonth) {
      const key = d.getDate();
      if (!evMap[key]) evMap[key] = [];
      evMap[key].push(e);
    }
  });

  const grid = document.getElementById("calendar-grid");
  const dayNames = ["Dom","Lun","Mar","Mie","Jue","Vie","Sab"];
  let html = dayNames.map(d => `<div class="text-center text-xs text-charcoal/40 font-medium py-2">${d}</div>`).join("");

  for (let i = 0; i < firstDay; i++) html += '<div></div>';
  for (let d = 1; d <= daysInMonth; d++) {
    const isToday = d === today.getDate() && calMonth === today.getMonth() && calYear === today.getFullYear();
    const evs = evMap[d] || [];
    const hasEvent = evs.length > 0;
    const dotColor = evs.some(e => e.estado === "confirmado") ? "bg-primary" : evs.some(e => e.estado === "reserva") ? "bg-yellow-400" : "";
    html += `<div class="cal-day p-1 rounded ${isToday ? 'today' : ''} ${hasEvent ? 'has-event' : ''}" ${hasEvent ? `onclick="showDayEvents(${d})"` : ''}>
      <div class="text-xs mb-1 ${isToday ? 'text-primary font-bold' : 'text-charcoal/60'}">${d}</div>
      ${hasEvent ? `<div class="w-2 h-2 rounded-full ${dotColor} mx-auto"></div>` : ''}
      ${evs.length > 1 ? `<div class="text-[10px] text-charcoal/40 text-center">+${evs.length}</div>` : ''}
    </div>`;
  }
  grid.innerHTML = html;
}

window.showDayEvents = async function(day) {
  const eventos = await apiGet("/eventos/");
  const dayEvents = eventos.filter(e => {
    const d = new Date(e.fecha);
    return d.getDate() === day && d.getMonth() === calMonth && d.getFullYear() === calYear;
  });
  if (dayEvents.length === 0) return;
  showModal(`
    <h3 class="font-display text-xl mb-4">Eventos del ${day}/${calMonth+1}/${calYear}</h3>
    <div class="space-y-3">
      ${dayEvents.map(e => `
        <div class="p-3 rounded-lg border border-ivory-dark cursor-pointer hover:bg-ivory-dark/50" onclick="closeModal();verEvento(${e.id})">
          <p class="font-medium">${e.titulo}</p>
          <p class="text-sm text-charcoal/60">Estado: ${e.estado} | Pago: ${e.estado_pago}</p>
          <p class="text-sm text-charcoal/60">Total: $${e.monto_total?.toLocaleString("es-AR") || 0}</p>
        </div>
      `).join("")}
    </div>
  `);
};
