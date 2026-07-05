// ─── Navegacion ───
let currentPage = "dashboard";
let _dataCache = {};  // cache de datos por pagina para no re-fetchear

function navigate(page, data) {
  currentPage = page;
  document.querySelectorAll(".page-section").forEach(el => el.classList.add("hidden"));
  const target = document.getElementById(`page-${page}`);
  if (target) target.classList.remove("hidden");
  document.querySelectorAll(".nav-link").forEach(el => el.classList.remove("active"));
  document.querySelector(`.nav-link[data-page="${page}"]`)?.classList.add("active");
  loadPageData(page, data);
  if (window.innerWidth < 1024) toggleMobileSidebar(false);
}

function toggleMobileSidebar(forceOpen) {
  const sb = document.getElementById("sidebar");
  const isOpen = !sb.classList.contains("-translate-x-full");
  if (forceOpen === true || (!isOpen && forceOpen !== false)) {
    sb.classList.remove("-translate-x-full");
  } else {
    sb.classList.add("-translate-x-full");
  }
}

// ─── Search bars ───
let eventoSearch = "";
let clienteSearch = "";
let pptoSearch = "";
let pptoEstadoFilter = "";

// ─── Load data per page ───
async function loadPageData(page, data) {
  try {
    switch (page) {
      case "dashboard": await loadDashboard(); break;
      case "calendario": await loadCalendario(); break;
      case "eventos": await loadEventos(); break;
      case "mobiliario": await loadMobiliario(); break;
      case "clientes": await loadClientes(); break;
      case "presupuestos": await loadPresupuestos(); break;
      case "finanzas": await loadFinanzas(); break;
      case "cliente-perfil": await loadClientePerfil(data); break;
    }
  } catch (e) {
    console.error(e);
  }
}

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
      return `<div class="flex items-center gap-3 py-2 border-b border-ivory-dark last:border-0 cursor-pointer hover:bg-ivory-dark/50 rounded px-1" onclick="navigate('eventos')">
        <span class="w-2 h-2 rounded-full ${color} flex-shrink-0"></span>
        <span class="font-medium">${e.titulo}</span>
        <span class="text-charcoal/40 ml-auto">${fecha}</span>
      </div>`;
    }).join("");
}

// ─── CALENDARIO ───
let calYear, calMonth;

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

// ─── EVENTOS ───
async function loadEventos() {
  const eventos = await apiGet("/eventos/");
  const cont = document.getElementById("eventos-list");
  
  // actualizar search bar si no existe
  const searchEl = document.getElementById("evento-search");
  if (searchEl) {
    eventoSearch = searchEl.value.trim().toLowerCase();
  }

  // filtrar
  const filtered = eventoSearch
    ? eventos.filter(e => e.titulo.toLowerCase().includes(eventoSearch) || (e.lugar||"").toLowerCase().includes(eventoSearch))
    : eventos;

  if (filtered.length === 0) {
    cont.innerHTML = `<div class="text-center py-12 text-charcoal/40">
      <span class="material-symbols-outlined text-5xl mb-2 block">event_busy</span>
      <p>${eventoSearch ? 'Sin resultados para "' + eventoSearch + '"' : 'No hay eventos'}</p>
    </div>`;
    return;
  }
  cont.innerHTML = filtered.sort((a,b) => new Date(a.fecha) - new Date(b.fecha)).map(e => {
    const badge = e.estado === "confirmado" ? "bg-primary text-on-primary" :
                  e.estado === "reserva" ? "bg-yellow-400 text-charcoal" :
                  e.estado === "cancelado" ? "bg-red-100 text-red-700" :
                  "bg-green-100 text-green-700";
    const pagoBadge = e.estado_pago === "pagado" ? "bg-green-100 text-green-700" :
                      e.estado_pago === "seña" ? "bg-yellow-100 text-yellow-700" :
                      e.estado_pago === "parcial" ? "bg-orange-100 text-orange-700" :
                      "bg-gray-100 text-gray-600";
    const fecha = new Date(e.fecha).toLocaleDateString("es-AR", { day:"2-digit", month:"short", year:"numeric" });
    return `<div class="bg-white rounded-lg shadow-sm border border-ivory-dark hover:shadow-md transition-shadow">
      <div class="p-4 flex items-center justify-between cursor-pointer" onclick="verEvento(${e.id})">
        <div class="flex-1 min-w-0">
          <p class="font-medium truncate">${e.titulo}</p>
          <p class="text-sm text-charcoal/60">${fecha} ${e.lugar ? '— ' + e.lugar : ''}</p>
          <p class="text-sm text-navy font-display mt-1">$${e.monto_total?.toLocaleString("es-AR") || 0}</p>
        </div>
        <div class="flex items-center gap-2 flex-shrink-0 ml-3">
          <span class="text-xs px-2 py-1 rounded ${pagoBadge}">${e.estado_pago}</span>
          <span class="text-xs px-2 py-1 rounded ${badge}">${e.estado}</span>
          <div class="flex gap-1 ml-2" onclick="event.stopPropagation()">
            <button onclick="editarEventoModal(${e.id})" class="p-1.5 hover:bg-ivory-dark rounded-lg transition" title="Editar">
              <span class="material-symbols-outlined text-base text-charcoal/50 hover:text-primary">edit</span>
            </button>
            <button onclick="confirmarEliminarEvento(${e.id},'${e.titulo.replace(/'/g,"\\'")}')" class="p-1.5 hover:bg-red-50 rounded-lg transition" title="Eliminar">
              <span class="material-symbols-outlined text-base text-charcoal/50 hover:text-red-500">delete</span>
            </button>
          </div>
        </div>
      </div>
    </div>`;
  }).join("");
}

window.onEventoSearch = function(val) {
  eventoSearch = val.trim().toLowerCase();
  loadEventos();
};

// ─── Ver detalle de evento ───
window.verEvento = async function(id) {
  const ev = await apiGet(`/eventos/${id}`);
  const fecha = new Date(ev.fecha).toLocaleDateString("es-AR", { day:"2-digit", month:"long", year:"numeric" });
  const hora = new Date(ev.fecha).toLocaleTimeString("es-AR", { hour:"2-digit", minute:"2-digit" });
  const badge = ev.estado === "confirmado" ? "bg-primary text-on-primary" :
                ev.estado === "reserva" ? "bg-yellow-400 text-charcoal" :
                ev.estado === "cancelado" ? "bg-red-100 text-red-700" :
                "bg-green-100 text-green-700";
  const pagoBadge = ev.estado_pago === "pagado" ? "bg-green-100 text-green-700" :
                    ev.estado_pago === "seña" ? "bg-yellow-100 text-yellow-700" :
                    ev.estado_pago === "parcial" ? "bg-orange-100 text-orange-700" :
                    "bg-gray-100 text-gray-600";

  let itemsHtml = "";
  if (ev.items && ev.items.length > 0) {
    itemsHtml = `
      <div class="mt-4 border-t border-ivory-dark pt-4">
        <h4 class="font-medium mb-2 text-sm uppercase text-charcoal/50 tracking-wider">Mobiliario</h4>
        <div class="space-y-1">
          ${ev.items.map(i => `
            <div class="flex justify-between text-sm py-1 border-b border-ivory-dark/50 last:border-0">
              <div class="flex-1">
                <span class="text-charcoal/40 text-xs">(${i.categoria})</span> ${i.nombre}
              </div>
              <div class="text-right">
                <span class="text-charcoal/50">${i.cantidad}x $${i.precio_unitario?.toLocaleString("es-AR")}</span>
                <span class="font-medium ml-2">$${i.subtotal?.toLocaleString("es-AR")}</span>
              </div>
            </div>
          `).join("")}
        </div>
        <div class="mt-2 pt-2 border-t border-ivory-dark text-sm space-y-1">
          <div class="flex justify-between"><span class="text-charcoal/50">Subtotal mobiliario</span><span>$${ev.items.reduce((s,i)=>s+i.subtotal,0).toLocaleString("es-AR")}</span></div>
          <div class="flex justify-between"><span class="text-charcoal/50">Traslado</span><span>$${ev.costo_traslado?.toLocaleString("es-AR") || 0}</span></div>
          <div class="flex justify-between"><span class="text-charcoal/50">Mano de obra</span><span>$${ev.costo_mano_obra?.toLocaleString("es-AR") || 0}</span></div>
          <div class="flex justify-between font-display text-lg border-t border-ivory-dark pt-1"><span>Total</span><span class="text-navy">$${ev.monto_total?.toLocaleString("es-AR") || 0}</span></div>
          ${ev.monto_senia > 0 ? `<div class="flex justify-between text-sm"><span class="text-charcoal/50">Seña</span><span class="text-green-600">$${ev.monto_senia?.toLocaleString("es-AR")}</span></div>` : ''}
        </div>
      </div>`;
  }
  
  showModal(`
    <h3 class="font-display text-xl mb-4">${ev.titulo}</h3>
    <div class="space-y-2 text-sm">
      <div class="flex justify-between"><span class="text-charcoal/50">Cliente</span><span class="font-medium">${ev.cliente_nombre}</span></div>
      <div class="flex justify-between"><span class="text-charcoal/50">Fecha</span><span>${fecha} — ${hora}hs</span></div>
      ${ev.lugar ? `<div class="flex justify-between"><span class="text-charcoal/50">Lugar</span><span>${ev.lugar}</span></div>` : ''}
      <div class="flex justify-between items-center"><span class="text-charcoal/50">Estado</span><span class="text-xs px-2 py-1 rounded ${badge}">${ev.estado}</span></div>
      <div class="flex justify-between items-center"><span class="text-charcoal/50">Pago</span><span class="text-xs px-2 py-1 rounded ${pagoBadge}">${ev.estado_pago}</span></div>
      ${ev.notas ? `<div class="mt-2"><span class="text-charcoal/50 block mb-1">Notas</span><p class="bg-ivory-dark/50 p-2 rounded text-sm">${ev.notas}</p></div>` : ''}
    </div>
    ${itemsHtml}
    <div class="mt-4 flex gap-2">
      <button onclick="closeModal();editarEventoModal(${ev.id})" class="flex-1 bg-primary text-on-primary px-4 py-2 rounded-lg hover:opacity-90 transition text-sm flex items-center justify-center gap-1">
        <span class="material-symbols-outlined text-base">edit</span> Editar
      </button>
      <button onclick="closeModal();confirmarEliminarEvento(${ev.id},'${ev.titulo.replace(/'/g,"\\'")}')" class="bg-red-50 text-red-600 px-4 py-2 rounded-lg hover:bg-red-100 transition text-sm flex items-center justify-center gap-1">
        <span class="material-symbols-outlined text-base">delete</span> Eliminar
      </button>
    </div>
  `);
};

// ─── Crear evento ───
window.openEventoModal = async function() {
  const clientes = await apiGet("/clientes/");
  showModal(`
    <h3 class="font-display text-xl mb-4">Nuevo Evento</h3>
    <form onsubmit="crearEvento(event)">
      <div class="space-y-3">
        <div><label class="block text-sm mb-1 font-medium">Cliente</label>
          <select name="cliente_id" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none">
            <option value="">Seleccionar...</option>
            ${clientes.map(c => `<option value="${c.id}">${c.nombre}</option>`).join("")}
          </select></div>
        <div><label class="block text-sm mb-1 font-medium">Titulo</label>
          <input name="titulo" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" placeholder="Boda de Maria"/></div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="block text-sm mb-1 font-medium">Fecha</label>
            <input name="fecha" type="datetime-local" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
          <div><label class="block text-sm mb-1 font-medium">Lugar</label>
            <input name="lugar" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="block text-sm mb-1 font-medium">Traslado ($)</label>
            <input name="costo_traslado" type="number" value="0" step="0.01" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
          <div><label class="block text-sm mb-1 font-medium">Mano de obra ($)</label>
            <input name="costo_mano_obra" type="number" value="0" step="0.01" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="block text-sm mb-1 font-medium">Estado</label>
            <select name="estado" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none">
              <option value="reserva">Reserva</option><option value="confirmado">Confirmado</option>
            </select></div>
          <div><label class="block text-sm mb-1 font-medium">Pago</label>
            <select name="estado_pago" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none">
              <option value="pendiente">Pendiente</option><option value="seña">Con seña</option><option value="pagado">Pagado</option>
            </select></div>
        </div>
        <div><label class="block text-sm mb-1 font-medium">Notas</label>
          <textarea name="notas" rows="2" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"></textarea></div>
      </div>
      <button type="submit" class="mt-4 bg-primary text-on-primary px-4 py-2 rounded-lg hover:opacity-90 transition w-full font-medium">Crear Evento</button>
    </form>
  `);
};

window.crearEvento = async function(ev) {
  ev.preventDefault();
  const fd = new FormData(ev.target);
  const data = Object.fromEntries(fd.entries());
  data.cliente_id = parseInt(data.cliente_id);
  data.costo_traslado = parseFloat(data.costo_traslado) || 0;
  data.costo_mano_obra = parseFloat(data.costo_mano_obra) || 0;
  if (!data.estado_pago) data.estado_pago = "pendiente";
  await apiPost("/eventos/", data);
  closeModal();
  loadEventos();
  toast("Evento creado");
};

// ─── Editar evento ───
window.editarEventoModal = async function(id) {
  const ev = await apiGet(`/eventos/${id}`);
  const clientes = await apiGet("/clientes/");
  const fechaLocal = new Date(ev.fecha).toISOString().slice(0,16);
  showModal(`
    <h3 class="font-display text-xl mb-4">Editar Evento</h3>
    <form onsubmit="guardarEvento(event, ${id})">
      <div class="space-y-3">
        <div><label class="block text-sm mb-1 font-medium">Cliente</label>
          <select name="cliente_id" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none">
            ${clientes.map(c => `<option value="${c.id}" ${c.id === ev.cliente_id ? 'selected' : ''}>${c.nombre}</option>`).join("")}
          </select></div>
        <div><label class="block text-sm mb-1 font-medium">Titulo</label>
          <input name="titulo" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${ev.titulo}"/></div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="block text-sm mb-1 font-medium">Fecha</label>
            <input name="fecha" type="datetime-local" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${fechaLocal}"/></div>
          <div><label class="block text-sm mb-1 font-medium">Lugar</label>
            <input name="lugar" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${ev.lugar || ''}"/></div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="block text-sm mb-1 font-medium">Traslado ($)</label>
            <input name="costo_traslado" type="number" step="0.01" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${ev.costo_traslado || 0}"/></div>
          <div><label class="block text-sm mb-1 font-medium">Mano de obra ($)</label>
            <input name="costo_mano_obra" type="number" step="0.01" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${ev.costo_mano_obra || 0}"/></div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="block text-sm mb-1 font-medium">Estado</label>
            <select name="estado" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none">
              <option value="reserva" ${ev.estado==='reserva'?'selected':''}>Reserva</option>
              <option value="confirmado" ${ev.estado==='confirmado'?'selected':''}>Confirmado</option>
              <option value="completado" ${ev.estado==='completado'?'selected':''}>Completado</option>
              <option value="cancelado" ${ev.estado==='cancelado'?'selected':''}>Cancelado</option>
            </select></div>
          <div><label class="block text-sm mb-1 font-medium">Pago</label>
            <select name="estado_pago" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none">
              <option value="pendiente" ${ev.estado_pago==='pendiente'?'selected':''}>Pendiente</option>
              <option value="seña" ${ev.estado_pago==='seña'?'selected':''}>Con seña</option>
              <option value="parcial" ${ev.estado_pago==='parcial'?'selected':''}>Parcial</option>
              <option value="pagado" ${ev.estado_pago==='pagado'?'selected':''}>Pagado</option>
            </select></div>
        </div>
        <div><label class="block text-sm mb-1 font-medium">Seña ($)</label>
          <input name="monto_senia" type="number" step="0.01" value="${ev.monto_senia || 0}" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
        <div><label class="block text-sm mb-1 font-medium">Notas</label>
          <textarea name="notas" rows="2" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none">${ev.notas || ''}</textarea></div>
      </div>
      <button type="submit" class="mt-4 bg-primary text-on-primary px-4 py-2 rounded-lg hover:opacity-90 transition w-full font-medium">Guardar Cambios</button>
    </form>
  `);
};

window.guardarEvento = async function(ev, id) {
  ev.preventDefault();
  const fd = new FormData(ev.target);
  const data = {};
  for (const [key, val] of fd.entries()) {
    if (key === "cliente_id") data[key] = parseInt(val);
    else if (["costo_traslado","costo_mano_obra","monto_senia"].includes(key)) data[key] = parseFloat(val) || 0;
    else data[key] = val;
  }
  await apiPut(`/eventos/${id}`, data);
  closeModal();
  loadEventos();
  toast("Evento actualizado");
};

// ─── Eliminar evento ───
window.confirmarEliminarEvento = function(id, titulo) {
  showModal(`
    <h3 class="font-display text-xl mb-4 text-red-600">Eliminar Evento</h3>
    <p class="text-sm mb-4">¿Estas seguro de eliminar <strong>${titulo}</strong>? Esta accion no se puede deshacer.</p>
    <div class="flex gap-2">
      <button onclick="closeModal()" class="flex-1 bg-ivory-dark text-charcoal px-4 py-2 rounded-lg hover:bg-ivory transition font-medium">Cancelar</button>
      <button onclick="eliminarEvento(${id})" class="flex-1 bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600 transition font-medium">Eliminar</button>
    </div>
  `);
};

window.eliminarEvento = async function(id) {
  await apiDelete(`/eventos/${id}`);
  closeModal();
  loadEventos();
  toast("Evento eliminado");
};

// ─── MOBILIARIO ───
let mobFilter = "";

async function loadMobiliario() {
  const items = await apiGet("/mobiliario/");
  const cats = [...new Set(items.map(i => i.categoria))].sort();
  const filterDiv = document.getElementById("mobiliario-filtros");
  filterDiv.innerHTML = `<button onclick="setMobFilter('')" class="px-3 py-1 rounded-full text-xs ${mobFilter==='' ? 'bg-navy text-ivory' : 'bg-ivory-dark text-charcoal/60 hover:bg-ivory-dark'} transition">Todos</button>` +
    cats.map(c => `<button onclick="setMobFilter('${c}')" class="px-3 py-1 rounded-full text-xs ${mobFilter===c ? 'bg-navy text-ivory' : 'bg-ivory-dark text-charcoal/60 hover:bg-ivory-dark'} transition">${c}</button>`).join("");
  
  const filtered = mobFilter ? items.filter(i => i.categoria === mobFilter) : items;
  const grid = document.getElementById("mobiliario-grid");
  grid.innerHTML = filtered.map(m => {
    const fotoUrl = m.foto_path ? `/uploads/mobiliario/${m.foto_path}` : "";
    const stockClass = m.stock_disponible <= 0 ? 'text-red-600 font-bold' : m.stock_disponible <= 1 ? 'text-red-500' : 'text-green-600';
    return `
    <div class="card-mob bg-white rounded-lg shadow-sm border border-ivory-dark overflow-hidden hover:shadow-md transition-shadow group">
      <div class="h-32 bg-ivory-dark flex items-center justify-center overflow-hidden relative cursor-pointer" onclick="editMobiliario(${m.id})">
        ${fotoUrl ? `<img src="${fotoUrl}" class="w-full h-full object-cover"/>` : '<span class="material-symbols-outlined text-4xl text-charcoal/20">chair</span>'}
        <div class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
          <button onclick="event.stopPropagation();editMobiliario(${m.id})" class="bg-white/90 backdrop-blur-sm p-1 rounded shadow-sm hover:bg-primary hover:text-on-primary transition" title="Editar">
            <span class="material-symbols-outlined text-sm">edit</span>
          </button>
          <button onclick="event.stopPropagation();confirmarEliminarMobiliario(${m.id},'${m.nombre.replace(/'/g,"\\'")}')" class="bg-white/90 backdrop-blur-sm p-1 rounded shadow-sm hover:bg-red-500 hover:text-white transition" title="Eliminar">
            <span class="material-symbols-outlined text-sm">delete</span>
          </button>
        </div>
      </div>
      <div class="p-3 cursor-pointer" onclick="editMobiliario(${m.id})">
        <p class="font-medium text-sm truncate">${m.nombre}</p>
        <p class="text-xs text-charcoal/50">${m.categoria}</p>
        <div class="flex justify-between mt-2 items-center">
          <span class="text-sm font-display text-navy">$${m.precio_alquiler?.toLocaleString("es-AR")}</span>
          <span class="text-xs ${stockClass}">Stock: ${m.stock_disponible}/${m.stock_total}</span>
        </div>
      </div>
    </div>`;
  }).join("");
}

window.setMobFilter = function(f) { mobFilter = f; loadMobiliario(); };

window.openMobiliarioModal = function(editItem) {
  const isEdit = !!editItem;
  showModal(`
    <h3 class="font-display text-xl mb-4">${isEdit ? 'Editar' : 'Agregar'} Mobiliario</h3>
    <form id="mob-form" onsubmit="crearMobiliario(event, ${isEdit ? editItem.id : 'null'})">
      <div class="space-y-3">
        <div><label class="block text-sm mb-1 font-medium">Nombre</label>
          <input name="nombre" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${isEdit ? editItem.nombre : ''}"/></div>
        <div><label class="block text-sm mb-1 font-medium">Categoria</label>
          <input name="categoria" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" placeholder="silla, sillon, mesa..." value="${isEdit ? editItem.categoria : ''}"/></div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="block text-sm mb-1 font-medium">Precio Alquiler</label>
            <input name="precio_alquiler" type="number" step="0.01" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${isEdit ? editItem.precio_alquiler : ''}"/></div>
          <div><label class="block text-sm mb-1 font-medium">Stock Total</label>
            <input name="stock_total" type="number" required value="${isEdit ? editItem.stock_total : '1'}" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
        </div>
        <div><label class="block text-sm mb-1 font-medium">Foto</label>
          <input name="foto" type="file" accept="image/*" class="w-full border border-ivory-dark rounded-lg p-2 text-sm"/>
          ${isEdit && editItem.foto_path ? `<p class="text-xs text-charcoal/40 mt-1">Foto actual: ${editItem.foto_path}</p>` : ''}
        </div>
        <div><label class="block text-sm mb-1 font-medium">Descripcion</label>
          <textarea name="descripcion" rows="2" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none">${isEdit ? (editItem.descripcion || '') : ''}</textarea></div>
      </div>
      <button type="submit" class="mt-4 bg-primary text-on-primary px-4 py-2 rounded-lg hover:opacity-90 transition w-full font-medium">${isEdit ? 'Actualizar' : 'Guardar'}</button>
    </form>
  `);
};

window.crearMobiliario = async function(ev, editId) {
  ev.preventDefault();
  const form = document.getElementById("mob-form");
  const fd = new FormData(form);
  fd.delete("descripcion");
  fd.append("descripcion", form.querySelector('[name="descripcion"]').value || "");
  
  try {
    if (editId) {
      await apiUploadPut(`/mobiliario/${editId}`, fd);
    } else {
      await apiUpload("/mobiliario/", fd);
    }
    closeModal();
    loadMobiliario();
    toast(editId ? "Mobiliario actualizado" : "Mobiliario creado");
  } catch (e) {
    alert("Error: " + e.message);
  }
};

window.editMobiliario = async function(id) {
  const items = await apiGet("/mobiliario/");
  const item = items.find(m => m.id === id);
  if (item) openMobiliarioModal(item);
};

window.confirmarEliminarMobiliario = function(id, nombre) {
  showModal(`
    <h3 class="font-display text-xl mb-4 text-red-600">Eliminar Mobiliario</h3>
    <p class="text-sm mb-4">¿Estas seguro de eliminar <strong>${nombre}</strong>? Se desactivara del catalogo.</p>
    <div class="flex gap-2">
      <button onclick="closeModal()" class="flex-1 bg-ivory-dark text-charcoal px-4 py-2 rounded-lg hover:bg-ivory transition font-medium">Cancelar</button>
      <button onclick="eliminarMobiliario(${id})" class="flex-1 bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600 transition font-medium">Eliminar</button>
    </div>
  `);
};

window.eliminarMobiliario = async function(id) {
  await apiDelete(`/mobiliario/${id}`);
  closeModal();
  loadMobiliario();
  toast("Mobiliario eliminado");
};

// ─── CLIENTES ───
async function loadClientes() {
  const clientes = await apiGet("/clientes/");
  const cont = document.getElementById("clientes-list");
  
  const searchEl = document.getElementById("cliente-search");
  if (searchEl) {
    clienteSearch = searchEl.value.trim().toLowerCase();
  }

  const filtered = clienteSearch
    ? clientes.filter(c => c.nombre.toLowerCase().includes(clienteSearch) || (c.telefono||"").includes(clienteSearch) || (c.whatsapp||"").includes(clienteSearch))
    : clientes;

  if (filtered.length === 0) {
    cont.innerHTML = `<div class="text-center py-12 text-charcoal/40">
      <span class="material-symbols-outlined text-5xl mb-2 block">person_off</span>
      <p>${clienteSearch ? 'Sin resultados para "' + clienteSearch + '"' : 'No hay clientes'}</p>
    </div>`;
    return;
  }
  cont.innerHTML = filtered.map(c => `
    <div class="bg-white rounded-lg shadow-sm border border-ivory-dark hover:shadow-md transition-shadow">
      <div class="p-4 flex items-center justify-between">
        <div class="flex-1 min-w-0 cursor-pointer" onclick="navigateToClientePerfil(${c.id})">
          <p class="font-medium truncate hover:text-primary transition">${c.nombre}</p>
          <div class="flex gap-3 text-sm text-charcoal/60 mt-1">
            ${c.whatsapp ? `<span class="flex items-center gap-1"><span class="material-symbols-outlined text-xs">chat</span>${c.whatsapp}</span>` : ''}
            ${c.telefono && c.telefono !== c.whatsapp ? `<span class="flex items-center gap-1"><span class="material-symbols-outlined text-xs">phone</span>${c.telefono}</span>` : ''}
            ${c.email ? `<span class="flex items-center gap-1"><span class="material-symbols-outlined text-xs">mail</span>${c.email}</span>` : ''}
          </div>
        </div>
        <div class="flex items-center gap-1 flex-shrink-0 ml-3">
          <button onclick="navigateToClientePerfil(${c.id})" class="p-1.5 hover:bg-ivory-dark rounded-lg transition" title="Ver perfil">
            <span class="material-symbols-outlined text-base text-charcoal/50 hover:text-primary">visibility</span>
          </button>
          <button onclick="editarClienteModal(${c.id})" class="p-1.5 hover:bg-ivory-dark rounded-lg transition" title="Editar">
            <span class="material-symbols-outlined text-base text-charcoal/50 hover:text-primary">edit</span>
          </button>
          <button onclick="confirmarEliminarCliente(${c.id},'${c.nombre.replace(/'/g,"\\'")}')​" class="p-1.5 hover:bg-red-50 rounded-lg transition" title="Eliminar">
            <span class="material-symbols-outlined text-base text-charcoal/50 hover:text-red-500">delete</span>
          </button>
        </div>
      </div>
    </div>
  `).join("");
}

window.onClienteSearch = function(val) {
  clienteSearch = val.trim().toLowerCase();
  loadClientes();
};

// ─── Crear cliente ───
window.openClienteModal = function() {
  showModal(`
    <h3 class="font-display text-xl mb-4">Nuevo Cliente</h3>
    <form onsubmit="crearCliente(event)">
      <div class="space-y-3">
        <div><label class="block text-sm mb-1 font-medium">Nombre</label>
          <input name="nombre" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="block text-sm mb-1 font-medium">Telefono / WhatsApp</label>
            <input name="whatsapp" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
          <div><label class="block text-sm mb-1 font-medium">Telefono alter.</label>
            <input name="telefono" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
        </div>
        <div><label class="block text-sm mb-1 font-medium">Email</label>
          <input name="email" type="email" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
        <div><label class="block text-sm mb-1 font-medium">Notas</label>
          <textarea name="notas" rows="2" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"></textarea></div>
      </div>
      <button type="submit" class="mt-4 bg-primary text-on-primary px-4 py-2 rounded-lg hover:opacity-90 transition w-full font-medium">Guardar</button>
    </form>
  `);
};

window.crearCliente = async function(ev) {
  ev.preventDefault();
  const fd = new FormData(ev.target);
  const data = Object.fromEntries(fd.entries());
  if (!data.telefono) data.telefono = data.whatsapp || "";
  await apiPost("/clientes/", data);
  closeModal();
  loadClientes();
  toast("Cliente creado");
};

// ─── Editar cliente ───
window.editarClienteModal = async function(id) {
  const c = await apiGet(`/clientes/${id}`);
  showModal(`
    <h3 class="font-display text-xl mb-4">Editar Cliente</h3>
    <form onsubmit="guardarCliente(event, ${id})">
      <div class="space-y-3">
        <div><label class="block text-sm mb-1 font-medium">Nombre</label>
          <input name="nombre" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${c.nombre}"/></div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="block text-sm mb-1 font-medium">Telefono / WhatsApp</label>
            <input name="whatsapp" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${c.whatsapp || ''}"/></div>
          <div><label class="block text-sm mb-1 font-medium">Telefono alter.</label>
            <input name="telefono" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${c.telefono || ''}"/></div>
        </div>
        <div><label class="block text-sm mb-1 font-medium">Email</label>
          <input name="email" type="email" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${c.email || ''}"/></div>
        <div><label class="block text-sm mb-1 font-medium">Notas</label>
          <textarea name="notas" rows="2" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none">${c.notas || ''}</textarea></div>
      </div>
      <button type="submit" class="mt-4 bg-primary text-on-primary px-4 py-2 rounded-lg hover:opacity-90 transition w-full font-medium">Guardar Cambios</button>
    </form>
  `);
};

window.guardarCliente = async function(ev, id) {
  ev.preventDefault();
  const fd = new FormData(ev.target);
  const data = Object.fromEntries(fd.entries());
  if (!data.telefono) data.telefono = data.whatsapp || "";
  await apiPut(`/clientes/${id}`, data);
  closeModal();
  loadClientes();
  toast("Cliente actualizado");
};

// ─── Eliminar cliente ───
window.confirmarEliminarCliente = function(id, nombre) {
  showModal(`
    <h3 class="font-display text-xl mb-4 text-red-600">Eliminar Cliente</h3>
    <p class="text-sm mb-4">¿Estas seguro de eliminar <strong>${nombre}</strong>?</p>
    <p class="text-xs text-charcoal/50 mb-4">Si tiene eventos asociados, debera eliminar o reasignar esos eventos primero.</p>
    <div class="flex gap-2">
      <button onclick="closeModal()" class="flex-1 bg-ivory-dark text-charcoal px-4 py-2 rounded-lg hover:bg-ivory transition font-medium">Cancelar</button>
      <button onclick="eliminarCliente(${id})" class="flex-1 bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600 transition font-medium">Eliminar</button>
    </div>
  `);
};

window.eliminarCliente = async function(id) {
  try {
    await apiDelete(`/clientes/${id}`);
    closeModal();
    loadClientes();
    toast("Cliente eliminado");
  } catch (e) {
    toast(e.message, "error");
  }
};

// ─── PRESUPUESTOS ───
let _presupuestosList = [];

async function loadPresupuestos() {
  presupuestosList = await apiGet("/presupuestos/");
  _presupuestosList = presupuestosList || [];
  const searchEl = document.getElementById("ppto-search");
  if (searchEl) pptoSearch = searchEl.value.trim().toLowerCase();
  _updatePptoEstadoFilterButtons();
  renderPresupuestosList();
}
// keep backward compat alias
let presupuestosList = [];

function _pptoEstadoBadge(estado) {
  const map = {
    borrador: "bg-gray-100 text-gray-600",
    enviado: "bg-blue-100 text-blue-700",
    confirmado: "bg-green-100 text-green-700",
    cancelado: "bg-red-100 text-red-700",
  };
  return map[estado] || "bg-gray-100 text-gray-600";
}

function _updatePptoEstadoFilterButtons() {
  document.querySelectorAll("#ppto-estado-filtros button").forEach(btn => {
    const e = btn.getAttribute("data-estado");
    if (e === pptoEstadoFilter) {
      btn.className = "px-3 py-1 rounded-full text-xs font-medium transition bg-navy text-ivory";
    } else {
      btn.className = "px-3 py-1 rounded-full text-xs font-medium transition bg-ivory-dark text-charcoal/60 hover:bg-ivory-dark";
    }
  });
}

window.filterPptoEstado = function(estado) {
  pptoEstadoFilter = estado;
  _updatePptoEstadoFilterButtons();
  renderPresupuestosList();
};

window.onPptoSearch = function(val) {
  pptoSearch = val.trim().toLowerCase();
  renderPresupuestosList();
};

function renderPresupuestosList() {
  let filtered = _presupuestosList;
  if (pptoEstadoFilter) {
    filtered = filtered.filter(p => p.estado === pptoEstadoFilter);
  }
  if (pptoSearch) {
    filtered = filtered.filter(p =>
      (p.cliente_nombre || "").toLowerCase().includes(pptoSearch) ||
      (p.tipo_evento || "").toLowerCase().includes(pptoSearch)
    );
  }
  const cont = document.getElementById("presupuestos-list");
  if (!cont) return;
  if (filtered.length === 0) {
    cont.innerHTML = `<div class="text-center py-12 text-charcoal/40">
      <span class="material-symbols-outlined text-5xl mb-2 block">receipt_long</span>
      <p>${pptoSearch || pptoEstadoFilter ? 'Sin resultados' : 'No hay presupuestos'}</p>
    </div>`;
    return;
  }
  cont.innerHTML = filtered.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0)).map(p => {
    const fecha = p.fecha_evento ? new Date(p.fecha_evento).toLocaleDateString("es-AR", { day: "2-digit", month: "short", year: "numeric" }) : "—";
    const created = p.created_at ? new Date(p.created_at).toLocaleDateString("es-AR", { day: "2-digit", month: "short" }) : "";
    const badge = _pptoEstadoBadge(p.estado);
    return `<div class="bg-white rounded-lg shadow-sm border border-ivory-dark hover:shadow-md transition-shadow">
      <div class="p-4 flex items-center justify-between cursor-pointer" onclick="verPresupuestoDetalle(${p.id})">
        <div class="flex-1 min-w-0">
          <p class="font-medium truncate">${p.cliente_nombre || "—"} <span class="text-charcoal/40 font-normal">· ${p.tipo_evento || ""}</span></p>
          <div class="flex items-center gap-3 text-sm text-charcoal/60 mt-1">
            <span class="flex items-center gap-1"><span class="material-symbols-outlined text-xs">calendar_today</span>${fecha}</span>
            ${created ? `<span class="text-xs text-charcoal/30">Creado ${created}</span>` : ''}
          </div>
        </div>
        <div class="flex items-center gap-2 flex-shrink-0 ml-3">
          <span class="font-display text-navy">$${p.total?.toLocaleString("es-AR") || 0}</span>
          <span class="text-xs px-2 py-1 rounded ${badge}">${p.estado || "borrador"}</span>
        </div>
      </div>
    </div>`;
  }).join("");
}

// ─── Ver detalle de presupuesto ───
window.verPresupuestoDetalle = async function(id) {
  const p = await apiGet(`/presupuestos/${id}`);
  const fecha = p.fecha_evento ? new Date(p.fecha_evento).toLocaleDateString("es-AR", { day: "2-digit", month: "long", year: "numeric" }) : "—";
  const badge = _pptoEstadoBadge(p.estado);

  // Build lugares/items HTML
  let lugaresHtml = "";
  if (p.lugares && p.lugares.length > 0) {
    lugaresHtml = `<div class="mt-4 border-t border-ivory-dark pt-4">
      <h4 class="font-medium mb-3 text-sm uppercase text-charcoal/50 tracking-wider">Mobiliario por Lugar</h4>
      <div class="space-y-4">`;
    p.lugares.forEach(lug => {
      lugaresHtml += `<div class="bg-ivory-dark/30 rounded-lg p-3">
        <p class="font-medium text-sm text-navy mb-2">${lug.nombre || "Sin nombre"}</p>
        <div class="space-y-1">`;
      if (lug.items && lug.items.length > 0) {
        lug.items.forEach(it => {
          lugaresHtml += `<div class="flex justify-between text-sm py-1 border-b border-ivory-dark/50 last:border-0">
            <span>${it.cantidad}x ${it.nombre || "Mobiliario"}</span>
            <span class="font-medium">$${(it.subtotal || 0).toLocaleString("es-AR")}</span>
          </div>`;
        });
      } else {
        lugaresHtml += `<p class="text-sm text-charcoal/40">Sin items</p>`;
      }
      lugaresHtml += `</div></div>`;
    });
    lugaresHtml += `</div></div>`;
  }

  const mc = document.getElementById("modal-content");
  mc.classList.remove("max-w-lg");
  mc.classList.add("max-w-3xl");

  showModal(`
    <h3 class="font-display text-xl mb-4">Presupuesto #${p.id}</h3>
    <div class="space-y-2 text-sm">
      <div class="flex justify-between"><span class="text-charcoal/50">Cliente</span><span class="font-medium">${p.cliente_nombre || "—"}</span></div>
      <div class="flex justify-between"><span class="text-charcoal/50">Tipo de Evento</span><span>${p.tipo_evento || "—"}</span></div>
      <div class="flex justify-between"><span class="text-charcoal/50">Fecha del Evento</span><span>${fecha}</span></div>
      <div class="flex justify-between"><span class="text-charcoal/50">Invitados</span><span>${p.cantidad_invitados || "—"}</span></div>
      <div class="flex justify-between"><span class="text-charcoal/50">Localidad</span><span>${p.localidad || "—"}</span></div>
      <div class="flex justify-between items-center"><span class="text-charcoal/50">Estado</span><span class="text-xs px-2 py-1 rounded ${badge}">${p.estado || "borrador"}</span></div>
    </div>
    ${lugaresHtml}
    <div class="mt-4 border-t border-ivory-dark pt-3 text-sm space-y-1">
      <div class="flex justify-between"><span class="text-charcoal/50">Subtotal Mobiliario</span><span>$${(p.subtotal_mobiliario || 0).toLocaleString("es-AR")}</span></div>
      <div class="flex justify-between"><span class="text-charcoal/50">Logística (${p.logistica_tipo || "—"}${p.distancia_km ? " · " + p.distancia_km + "km" : ""})</span><span>$${(p.costo_logistica || 0).toLocaleString("es-AR")}</span></div>
      ${p.acarreo_adicional ? '<div class="flex justify-between"><span class="text-charcoal/50">Acarreo adicional</span><span>Sí</span></div>' : ''}
      ${p.solo_ambientacion ? '<div class="flex justify-between"><span class="text-charcoal/50">Solo ambientación</span><span>Sí</span></div>' : ''}
      <div class="flex justify-between font-display text-lg border-t border-ivory-dark pt-1 mt-1"><span>Total</span><span class="text-navy">$${(p.total || 0).toLocaleString("es-AR")}</span></div>
    </div>
    <div class="mt-5 flex flex-wrap gap-2">
      <button onclick="closeModal();editarPresupuestoModal(${p.id})" class="flex-1 bg-primary text-on-primary px-3 py-2 rounded-lg hover:opacity-90 transition text-sm flex items-center justify-center gap-1">
        <span class="material-symbols-outlined text-base">edit</span> Editar
      </button>
      <button onclick="confirmarEliminarPresupuesto(${p.id})" class="bg-red-50 text-red-600 px-3 py-2 rounded-lg hover:bg-red-100 transition text-sm flex items-center justify-center gap-1">
        <span class="material-symbols-outlined text-base">delete</span> Eliminar
      </button>
      <button onclick="convertirPresupuestoEvento(${p.id})" class="bg-green-50 text-green-700 px-3 py-2 rounded-lg hover:bg-green-100 transition text-sm flex items-center justify-center gap-1">
        <span class="material-symbols-outlined text-base">event</span> Convertir en Evento
      </button>
    </div>
    <div class="mt-3 flex flex-wrap gap-2 border-t border-ivory-dark pt-3">
      <span class="text-xs text-charcoal/40 self-center mr-1">PDF:</span>
      <a href="${BASE_URL}/api/presupuestos/${p.id}/pdf/completo" target="_blank" class="px-3 py-1.5 bg-ivory-dark rounded-lg text-xs font-medium hover:bg-ivory transition flex items-center gap-1">
        <span class="material-symbols-outlined text-sm">picture_as_pdf</span> Completo
      </a>
      <a href="${BASE_URL}/api/presupuestos/${p.id}/pdf/cliente" target="_blank" class="px-3 py-1.5 bg-ivory-dark rounded-lg text-xs font-medium hover:bg-ivory transition flex items-center gap-1">
        <span class="material-symbols-outlined text-sm">picture_as_pdf</span> Cliente
      </a>
      <a href="${BASE_URL}/api/presupuestos/${p.id}/pdf/empleados" target="_blank" class="px-3 py-1.5 bg-ivory-dark rounded-lg text-xs font-medium hover:bg-ivory transition flex items-center gap-1">
        <span class="material-symbols-outlined text-sm">picture_as_pdf</span> Empleados
      </a>
    </div>
  `);
};

// ─── Eliminar presupuesto ───
window.confirmarEliminarPresupuesto = function(id) {
  showModal(`
    <h3 class="font-display text-xl mb-4 text-red-600">Eliminar Presupuesto</h3>
    <p class="text-sm mb-4">¿Estás seguro de eliminar este presupuesto? Esta acción no se puede deshacer.</p>
    <div class="flex gap-2">
      <button onclick="closeModal()" class="flex-1 bg-ivory-dark text-charcoal px-4 py-2 rounded-lg hover:bg-ivory transition font-medium">Cancelar</button>
      <button onclick="eliminarPresupuesto(${id})" class="flex-1 bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600 transition font-medium">Eliminar</button>
    </div>
  `);
};

window.eliminarPresupuesto = async function(id) {
  await apiDelete(`/presupuestos/${id}`);
  closeModal();
  loadPresupuestos();
  toast("Presupuesto eliminado");
};

// ─── Convertir presupuesto en evento ───
window.convertirPresupuestoEvento = async function(id) {
  try {
    const res = await apiPost(`/presupuestos/${id}/convertir-evento/`, {});
    toast("Evento creado desde presupuesto");
    closeModal();
    navigate("eventos");
  } catch (e) {
    toast("Error: " + e.message, "error");
  }
};

// ─── Nuevo Presupuesto Modal ───
let _nuevoPptoLugares = [{ nombre: "", productos: [{ mobiliario_id: null, cantidad: 1 }] }];
let _nuevoPptoClientes = [];
let _nuevoPptoMobiliario = [];
let _nuevoPptoEditingId = null;  // null=nuevo, id=editando

window.openNuevoPresupuestoModal = async function() {
  const [clientes, mobiliario] = await Promise.all([
    apiGet("/clientes/"),
    apiGet("/mobiliario/")
  ]);
  _nuevoPptoClientes = clientes;
  _nuevoPptoMobiliario = mobiliario;
  _nuevoPptoLugares = [{ nombre: "", productos: [{ mobiliario_id: null, cantidad: 1 }] }];
  _nuevoPptoEditingId = null;
  _renderPptoModal();
};

// ─── Cálculo 100% local (no backend) ───
function _calcularPptoLocal() {
  const dist = parseFloat(document.getElementById("nppto-distancia")?.value) || 0;
  const acarreo = document.getElementById("nppto-acarreo")?.checked || false;
  const mobById = {};
  _nuevoPptoMobiliario.forEach(m => { mobById[m.id] = m; });

  let subtotalMob = 0;
  _nuevoPptoLugares.forEach(lug => {
    lug.productos.forEach(p => {
      const mob = mobById[p.mobiliario_id];
      if (mob) subtotalMob += mob.precio_alquiler * (p.cantidad || 1);
    });
  });

  let costoLog = 0;
  if (dist > 0) {
    costoLog = dist * 14000;
    if (acarreo) costoLog += 3500;
  }

  const total = subtotalMob + costoLog;
  return { subtotalMob, costoLog, total };
}

function _actualizarTotalesPpto() {
  const calc = _calcularPptoLocal();
  const el = document.getElementById("nppto-totales");
  if (el) {
    el.innerHTML = `
      <div class="flex justify-between text-sm"><span class="text-charcoal/50">Subtotal Mobiliario</span><span>$${calc.subtotalMob.toLocaleString("es-AR")}</span></div>
      <div class="flex justify-between text-sm"><span class="text-charcoal/50">Costo Logística</span><span>$${calc.costoLog.toLocaleString("es-AR")}</span></div>
      <div class="flex justify-between font-display text-lg border-t border-ivory-dark pt-1 mt-1"><span>Total</span><span class="text-navy">$${calc.total.toLocaleString("es-AR")}</span></div>`;
  }
  // Also update logística cost label
  const dist = parseFloat(document.getElementById("nppto-distancia")?.value) || 0;
  const acarreo = document.getElementById("nppto-acarreo")?.checked || false;
  let logCost = dist > 0 ? dist * 14000 : 0;
  if (acarreo && dist > 0) logCost += 3500;
  const logLabel = document.getElementById("nppto-logistica-cost");
  if (logLabel) logLabel.textContent = logCost.toLocaleString("es-AR");
}

// ─── Render solo la sección lugares (no TODO el modal) ───
function _renderPptoLugaresOnly() {
  const cont = document.getElementById("nppto-lugares");
  if (!cont) return;
  const mobOpts = _nuevoPptoMobiliario.map(m => `<option value="${m.id}">${m.nombre} – $${m.precio_alquiler?.toLocaleString("es-AR")}</option>`).join("");

  let html = "";
  _nuevoPptoLugares.forEach((lug, li) => {
    html += `<div class="border border-ivory-dark rounded-lg p-3 bg-ivory-dark/20">
      <div class="flex items-center gap-2 mb-2">
        <input value="${lug.nombre}" placeholder="Nombre del lugar" onchange="_nuevoPptoLugares[${li}].nombre=this.value" class="flex-1 border border-ivory-dark rounded-lg p-2 text-sm focus:border-primary outline-none"/>
        ${_nuevoPptoLugares.length > 1 ? `<button type="button" onclick="_removeLugar(${li})" class="text-red-400 hover:text-red-600 transition"><span class="material-symbols-outlined text-lg">close</span></button>` : ''}
      </div>
      <div class="space-y-2">`;
    lug.productos.forEach((prod, pi) => {
      html += `<div class="flex gap-2 items-center">
        <select onchange="_nuevoPptoLugares[${li}].productos[${pi}].mobiliario_id=parseInt(this.value)||null;_actualizarTotalesPpto()" class="flex-1 border border-ivory-dark rounded-lg p-2 text-sm focus:border-primary outline-none">
          <option value="">Seleccionar mobiliario...</option>
          ${_nuevoPptoMobiliario.map(m => `<option value="${m.id}" ${prod.mobiliario_id === m.id ? 'selected' : ''}>${m.nombre} – $${m.precio_alquiler?.toLocaleString("es-AR")}</option>`).join("")}
        </select>
        <input type="number" value="${prod.cantidad}" min="1" onchange="_nuevoPptoLugares[${li}].productos[${pi}].cantidad=parseInt(this.value)||1;_actualizarTotalesPpto()" class="w-20 border border-ivory-dark rounded-lg p-2 text-sm focus:border-primary outline-none" placeholder="Cant"/>
        ${lug.productos.length > 1 ? `<button type="button" onclick="_removeLugarProducto(${li},${pi})" class="text-red-400 hover:text-red-600 transition"><span class="material-symbols-outlined text-sm">close</span></button>` : ''}
      </div>`;
    });
    html += `</div>
      <button type="button" onclick="_addLugarProducto(${li})" class="mt-2 text-xs text-primary hover:underline flex items-center gap-1">
        <span class="material-symbols-outlined text-sm">add</span> Agregar item
      </button>
    </div>`;
  });
  cont.innerHTML = html;
  _actualizarTotalesPpto();
}

// ─── Render completo del modal (solo al abrir, NO al agregar/quitar items) ───
function _renderPptoModal(editData) {
  const mc = document.getElementById("modal-content");
  mc.classList.remove("max-w-lg");
  mc.classList.add("max-w-3xl");

  const p = editData || {};
  const clientesOpts = _nuevoPptoClientes.map(c => `<option value="${c.id}" ${p.cliente_id && c.id === p.cliente_id ? 'selected' : ''}>${c.nombre}</option>`).join("");
  const fechaVal = p.fecha_evento ? (() => { try { return new Date(p.fecha_evento).toISOString().slice(0,10); } catch { return ""; } })() : "";
  const titulo = _nuevoPptoEditingId ? `Editar Presupuesto #${_nuevoPptoEditingId}` : "Nuevo Presupuesto";
  const submitLabel = _nuevoPptoEditingId ? "Guardar Cambios" : "Guardar Presupuesto";
  const submitAction = _nuevoPptoEditingId ? `guardarEditarPresupuesto(event, ${_nuevoPptoEditingId})` : `guardarNuevoPresupuesto(event)`;

  // Build initial lugares HTML
  let lugaresHtml = "";

  showModal(`
    <h3 class="font-display text-xl mb-4">${titulo}</h3>
    <form onsubmit="${submitAction}">
      <div class="space-y-3">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-sm mb-1 font-medium">Cliente existente</label>
            <select id="nppto-cliente-id" onchange="document.getElementById('nppto-cliente-nombre').value=''" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none">
              <option value="">— Nuevo cliente —</option>
              ${clientesOpts}
            </select>
          </div>
          <div>
            <label class="block text-sm mb-1 font-medium">Nombre del cliente (nuevo)</label>
            <input id="nppto-cliente-nombre" value="${p.cliente_nombre || ''}" placeholder="Nombre si es cliente nuevo" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" onchange="document.getElementById('nppto-cliente-id').value=''"/>
          </div>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div>
            <label class="block text-sm mb-1 font-medium">Fecha Evento</label>
            <input id="nppto-fecha" type="date" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${fechaVal}"/>
          </div>
          <div>
            <label class="block text-sm mb-1 font-medium">Tipo Evento</label>
            <input id="nppto-tipo" value="${p.tipo_evento || ''}" placeholder="Boda, Cumple..." class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/>
          </div>
          <div>
            <label class="block text-sm mb-1 font-medium">Invitados</label>
            <input id="nppto-invitados" type="number" min="0" value="${p.cantidad_invitados || ''}" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/>
          </div>
          <div>
            <label class="block text-sm mb-1 font-medium">Localidad</label>
            <input id="nppto-localidad" value="${p.localidad || ''}" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/>
          </div>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div>
            <label class="block text-sm mb-1 font-medium">Distancia (km)</label>
            <input id="nppto-distancia" type="number" min="0" step="0.1" value="${p.distancia_km || 0}" oninput="_actualizarTotalesPpto()" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/>
          </div>
          <div>
            <label class="block text-sm mb-1 font-medium">Logística tipo</label>
            <select id="nppto-logistica-tipo" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none">
              <option value="Traslado Simple" ${p.logistica_tipo==='Traslado Simple'||p.logistica_tipo==='traslado_simple'?'selected':''}>Traslado Simple</option>
              <option value="Ida y Vuelta" ${p.logistica_tipo==='Ida y Vuelta'||p.logistica_tipo==='ida_vuelta'?'selected':''}>Ida y Vuelta</option>
              <option value="Multiple" ${p.logistica_tipo==='Multiple'||p.logistica_tipo==='multiple'?'selected':''}>Multiple</option>
            </select>
          </div>
          <div class="flex items-end gap-2">
            <label class="flex items-center gap-2 cursor-pointer p-2">
              <input id="nppto-acarreo" type="checkbox" ${p.acarreo_adicional?'checked':''} class="w-4 h-4 accent-primary" onchange="_actualizarTotalesPpto()"/>
              <span class="text-sm">Acarreo adicional</span>
            </label>
          </div>
          <div class="flex items-end gap-2">
            <label class="flex items-center gap-2 cursor-pointer p-2">
              <input id="nppto-ambientacion" type="checkbox" ${p.solo_ambientacion?'checked':''} class="w-4 h-4 accent-primary"/>
              <span class="text-sm">Solo ambientación</span>
            </label>
          </div>
        </div>
        <div class="text-xs text-charcoal/40">Costo logística: $<span id="nppto-logistica-cost">0</span> (a $14.000/km + $3.500 acarreo)</div>

        <!-- Lugares -->
        <div>
          <h4 class="font-medium text-sm mb-2 text-charcoal/70">Lugares y Mobiliario</h4>
          <div id="nppto-lugares" class="space-y-3">${lugaresHtml}</div>
          <button type="button" onclick="_addLugar()" class="mt-2 text-sm text-primary hover:underline flex items-center gap-1">
            <span class="material-symbols-outlined text-sm">add</span> Agregar lugar
          </button>
        </div>

        <!-- Totales en vivo -->
        <div id="nppto-totales" class="mt-4 border-t border-ivory-dark pt-3 text-sm space-y-1"></div>

        ${_nuevoPptoEditingId ? `<div class="mt-2">
          <label class="block text-sm mb-1 font-medium">Estado</label>
          <select id="nppto-estado" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none">
            <option value="borrador" ${p.estado==='borrador'?'selected':''}>Borrador</option>
            <option value="enviado" ${p.estado==='enviado'?'selected':''}>Enviado</option>
            <option value="confirmado" ${p.estado==='confirmado'?'selected':''}>Confirmado</option>
            <option value="cancelado" ${p.estado==='cancelado'?'selected':''}>Cancelado</option>
          </select>
        </div>` : ''}

        <button type="submit" class="w-full bg-primary text-on-primary px-4 py-2 rounded-lg hover:opacity-90 transition font-medium flex items-center justify-center gap-1">
          <span class="material-symbols-outlined text-base">save</span> ${submitLabel}
        </button>
      </div>
    </form>
  `);

  // Render lugares AFTER modal is in DOM
  _renderPptoLugaresOnly();
}

// ─── Lugar/producto management ───
window._addLugar = function() {
  _nuevoPptoLugares.push({ nombre: "", productos: [{ mobiliario_id: null, cantidad: 1 }] });
  _renderPptoLugaresOnly();  // solo re-renderiza la sección lugares
};
window._removeLugar = function(li) {
  _nuevoPptoLugares.splice(li, 1);
  _renderPptoLugaresOnly();
};
window._addLugarProducto = function(li) {
  _nuevoPptoLugares[li].productos.push({ mobiliario_id: null, cantidad: 1 });
  _renderPptoLugaresOnly();
};
window._removeLugarProducto = function(li, pi) {
  _nuevoPptoLugares[li].productos.splice(pi, 1);
  _renderPptoLugaresOnly();
};
window._actualizarTotalesPpto = _actualizarTotalesPpto;

// ─── Guardar nuevo presupuesto ───
window.guardarNuevoPresupuesto = async function(ev) {
  ev.preventDefault();
  const clienteId = parseInt(document.getElementById("nppto-cliente-id")?.value) || null;
  const clienteNombre = document.getElementById("nppto-cliente-nombre")?.value || "";
  if (!clienteId && !clienteNombre) { toast("Indica un cliente existente o escribe el nombre", "error"); return; }

  // Validate at least one product
  const hasProducts = _nuevoPptoLugares.some(l => l.productos.some(p => p.mobiliario_id));
  if (!hasProducts) { toast("Agrega al menos un item de mobiliario", "error"); return; }

  const lugares = _nuevoPptoLugares.map(lug => ({
    nombre: lug.nombre || "Lugar",
    productos: lug.productos.filter(p => p.mobiliario_id).map(p => ({ mobiliario_id: p.mobiliario_id, catalogo_key: (_nuevoPptoMobiliario.find(m => m.id === p.mobiliario_id)?.nombre || ""), cantidad: p.cantidad }))
  }));

  const calc = _calcularPptoLocal();

  const saveData = {
    cliente_id: clienteId,
    cliente_nombre: clienteNombre || (_nuevoPptoClientes.find(c => c.id === clienteId)?.nombre || ""),
    fecha_evento: document.getElementById("nppto-fecha")?.value || new Date().toISOString().slice(0, 10),
    tipo_evento: document.getElementById("nppto-tipo")?.value || "",
    cantidad_invitados: parseInt(document.getElementById("nppto-invitados")?.value) || null,
    localidad: document.getElementById("nppto-localidad")?.value || "",
    distancia_km: parseFloat(document.getElementById("nppto-distancia")?.value) || null,
    logistica_tipo: document.getElementById("nppto-logistica-tipo")?.value || "Traslado Simple",
    acarreo_adicional: document.getElementById("nppto-acarreo")?.checked || false,
    solo_ambientacion: document.getElementById("nppto-ambientacion")?.checked || false,
    lugares,
    subtotal_mobiliario: calc.subtotalMob,
    costo_logistica: calc.costoLog,
    total: calc.total,
    whatsapp_text: "",
    estado: "borrador",
  };

  try {
    await apiPost("/presupuestos/", saveData);
    closeModal();
    loadPresupuestos();
    toast("Presupuesto guardado");
  } catch (e) {
    toast("Error: " + e.message, "error");
  }
};

// ─── Editar presupuesto modal ───
window.editarPresupuestoModal = async function(id) {
  const p = await apiGet(`/presupuestos/${id}`);
  const [clientes, mobiliario] = await Promise.all([
    apiGet("/clientes/"),
    apiGet("/mobiliario/")
  ]);
  _nuevoPptoClientes = clientes;
  _nuevoPptoMobiliario = mobiliario;
  _nuevoPptoEditingId = id;

  // Build lugares from existing data — usar "productos" en vez de "items"
  if (p.lugares && p.lugares.length > 0) {
    _nuevoPptoLugares = p.lugares.map(lug => ({
      nombre: lug.nombre || "",
      productos: (lug.productos || lug.items || []).map(it => ({ mobiliario_id: it.mobiliario_id || it.id || null, cantidad: it.cantidad || 1 }))
    }));
  } else {
    _nuevoPptoLugares = [{ nombre: "", productos: [{ mobiliario_id: null, cantidad: 1 }] }];
  }

  _renderPptoModal(p);
};

window.guardarEditarPresupuesto = async function(ev, id) {
  ev.preventDefault();
  const clienteId = parseInt(document.getElementById("nppto-cliente-id")?.value) || null;
  const clienteNombre = document.getElementById("nppto-cliente-nombre")?.value || "";
  if (!clienteId && !clienteNombre) { toast("Indica un cliente", "error"); return; }

  const lugares = _nuevoPptoLugares.map(lug => ({
    nombre: lug.nombre || "Lugar",
    productos: lug.productos.filter(p => p.mobiliario_id).map(p => ({ mobiliario_id: p.mobiliario_id, catalogo_key: (_nuevoPptoMobiliario.find(m => m.id === p.mobiliario_id)?.nombre || ""), cantidad: p.cantidad }))
  }));

  const calc = _calcularPptoLocal();

  const saveData = {
    cliente_id: clienteId,
    cliente_nombre: clienteNombre || (_nuevoPptoClientes.find(c => c.id === clienteId)?.nombre || ""),
    fecha_evento: document.getElementById("nppto-fecha")?.value || new Date().toISOString().slice(0, 10),
    tipo_evento: document.getElementById("nppto-tipo")?.value || "",
    cantidad_invitados: parseInt(document.getElementById("nppto-invitados")?.value) || null,
    localidad: document.getElementById("nppto-localidad")?.value || "",
    distancia_km: parseFloat(document.getElementById("nppto-distancia")?.value) || null,
    logistica_tipo: document.getElementById("nppto-logistica-tipo")?.value || "Traslado Simple",
    acarreo_adicional: document.getElementById("nppto-acarreo")?.checked || false,
    solo_ambientacion: document.getElementById("nppto-ambientacion")?.checked || false,
    lugares,
    subtotal_mobiliario: calc.subtotalMob,
    costo_logistica: calc.costoLog,
    total: calc.total,
    whatsapp_text: "",
    estado: document.getElementById("nppto-estado")?.value || "borrador",
  };

  try {
    await apiPut(`/presupuestos/${id}`, saveData);
    closeModal();
    loadPresupuestos();
    toast("Presupuesto actualizado");
  } catch (e) {
    toast("Error: " + e.message, "error");
  }
};

// ─── CLIENTE PERFIL ───
let _clientePerfilData = null;
let _clientePerfilTab = "eventos";

window.navigateToClientePerfil = function(id) {
  navigate("cliente-perfil", id);
};

window.goBackToClientes = function() {
  navigate("clientes");
};

async function loadClientePerfil(clienteId) {
  if (!clienteId) return;
  try {
    _clientePerfilData = await apiGet(`/clientes/${clienteId}/perfil`);
    _clientePerfilTab = "eventos";
    renderClientePerfil();
  } catch (e) {
    document.getElementById("cliente-perfil-content").innerHTML = `<p class="text-red-500">Error cargando perfil: ${e.message}</p>`;
  }
}

function renderClientePerfil() {
  const c = _clientePerfilData;
  if (!c) return;
  const cont = document.getElementById("cliente-perfil-content");
  if (!cont) return;

  const tabEventosClass = _clientePerfilTab === "eventos" ? "bg-navy text-ivory" : "bg-ivory-dark text-charcoal/60 hover:bg-ivory-dark";
  const tabPptoClass = _clientePerfilTab === "presupuestos" ? "bg-navy text-ivory" : "bg-ivory-dark text-charcoal/60 hover:bg-ivory-dark";

  let tabContent = "";
  if (_clientePerfilTab === "eventos") {
    if (!c.eventos || c.eventos.length === 0) {
      tabContent = `<div class="text-center py-8 text-charcoal/40">
        <span class="material-symbols-outlined text-4xl mb-2 block">event_busy</span>
        <p>No hay eventos</p>
      </div>`;
    } else {
      tabContent = c.eventos.map(e => {
        const badge = e.estado === "confirmado" ? "bg-primary text-on-primary" :
                      e.estado === "reserva" ? "bg-yellow-400 text-charcoal" :
                      e.estado === "cancelado" ? "bg-red-100 text-red-700" :
                      "bg-green-100 text-green-700";
        const fecha = e.fecha ? new Date(e.fecha).toLocaleDateString("es-AR", { day: "2-digit", month: "short", year: "numeric" }) : "—";
        const title = e.titulo || `Evento #${e.id}`;
        return `<div class="flex items-center justify-between py-3 px-1 border-b border-ivory-dark/60 last:border-0 hover:bg-ivory-dark/30 rounded transition">
          <div class="min-w-0 flex-1">
            <p class="font-medium truncate">${title}</p>
            <p class="text-xs text-charcoal/50">${fecha}</p>
          </div>
          <div class="flex items-center gap-2 flex-shrink-0 ml-3">
            <span class="font-display text-sm text-navy">$${(e.monto_total || 0).toLocaleString("es-AR")}</span>
            <span class="text-xs px-2 py-1 rounded ${badge}">${e.estado}</span>
          </div>
        </div>`;
      }).join("");
    }
  } else {
    if (!c.presupuestos || c.presupuestos.length === 0) {
      tabContent = `<div class="text-center py-8 text-charcoal/40">
        <span class="material-symbols-outlined text-4xl mb-2 block">receipt_long</span>
        <p>No hay presupuestos</p>
      </div>`;
    } else {
      tabContent = c.presupuestos.map(p => {
        const badge = _pptoEstadoBadge(p.estado);
        const fecha = p.fecha_evento ? new Date(p.fecha_evento).toLocaleDateString("es-AR", { day: "2-digit", month: "short", year: "numeric" }) : "—";
        return `<div class="flex items-center justify-between py-3 px-1 border-b border-ivory-dark/60 last:border-0 hover:bg-ivory-dark/30 rounded transition cursor-pointer" onclick="navigate('presupuestos');verPresupuestoDetalle(${p.id})">
          <div class="min-w-0 flex-1">
            <p class="font-medium truncate">${p.tipo_evento || "Presupuesto"}</p>
            <p class="text-xs text-charcoal/50">${fecha}</p>
          </div>
          <div class="flex items-center gap-2 flex-shrink-0 ml-3">
            <span class="font-display text-sm text-navy">$${(p.total || 0).toLocaleString("es-AR")}</span>
            <span class="text-xs px-2 py-1 rounded ${badge}">${p.estado || "borrador"}</span>
          </div>
        </div>`;
      }).join("");
    }
  }

  cont.innerHTML = `
    <!-- Client info card -->
    <div class="bg-white rounded-lg shadow-sm p-5 border border-ivory-dark mb-6">
      <div class="flex items-start gap-4">
        <div class="w-14 h-14 rounded-full bg-navy/10 flex items-center justify-center flex-shrink-0">
          <span class="material-symbols-outlined text-3xl text-navy">person</span>
        </div>
        <div class="flex-1 min-w-0">
          <h2 class="font-display text-2xl">${c.nombre}</h2>
          <div class="flex flex-wrap gap-3 mt-2 text-sm text-charcoal/60">
            ${c.whatsapp ? `<span class="flex items-center gap-1"><span class="material-symbols-outlined text-xs">chat</span>${c.whatsapp}</span>` : ''}
            ${c.telefono && c.telefono !== c.whatsapp ? `<span class="flex items-center gap-1"><span class="material-symbols-outlined text-xs">phone</span>${c.telefono}</span>` : ''}
            ${c.email ? `<span class="flex items-center gap-1"><span class="material-symbols-outlined text-xs">mail</span>${c.email}</span>` : ''}
          </div>
          ${c.notas ? `<p class="text-sm text-charcoal/50 mt-2 bg-ivory-dark/50 p-2 rounded">${c.notas}</p>` : ''}
        </div>
      </div>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-2 gap-4 mb-6">
      <div class="bg-white rounded-lg shadow-sm p-4 border border-ivory-dark text-center">
        <p class="text-xs uppercase tracking-wider text-charcoal/40 mb-1">Total Eventos</p>
        <p class="text-2xl font-display text-navy">${c.total_eventos || 0}</p>
      </div>
      <div class="bg-white rounded-lg shadow-sm p-4 border border-ivory-dark text-center">
        <p class="text-xs uppercase tracking-wider text-charcoal/40 mb-1">Total Gastado</p>
        <p class="text-2xl font-display text-primary">$${(c.total_gastado || 0).toLocaleString("es-AR")}</p>
      </div>
    </div>

    <!-- Tabs -->
    <div class="bg-white rounded-lg shadow-sm p-5 border border-ivory-dark">
      <div class="flex gap-2 mb-4">
        <button onclick="_switchClientePerfilTab('eventos')" class="px-4 py-1.5 rounded-full text-sm font-medium transition ${tabEventosClass}">Eventos</button>
        <button onclick="_switchClientePerfilTab('presupuestos')" class="px-4 py-1.5 rounded-full text-sm font-medium transition ${tabPptoClass}">Presupuestos</button>
      </div>
      <div>${tabContent}</div>
    </div>
  `;
}

window._switchClientePerfilTab = function(tab) {
  _clientePerfilTab = tab;
  renderClientePerfil();
};

// ─── FINANZAS ───
let finanzasAnio, finanzasMes, finanzasTipoFilter = "todos";
let _finanzasRegistros = [];  // cache for client-side tipo filtering
let _finanzasEventos = {};    // evento_id -> titulo lookup

const MONTHS_ES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];

function _initFinanzasSelectors() {
  const now = new Date();
  if (!finanzasAnio) finanzasAnio = now.getFullYear();
  if (!finanzasMes) finanzasMes = now.getMonth() + 1; // 1-indexed

  const anioSel = document.getElementById("finanzas-anio");
  const mesSel = document.getElementById("finanzas-mes");
  if (!anioSel || !mesSel) return;

  // Year selector: current year ± 5
  const curYear = now.getFullYear();
  anioSel.innerHTML = "";
  for (let y = curYear - 5; y <= curYear + 1; y++) {
    anioSel.innerHTML += `<option value="${y}" ${y === finanzasAnio ? 'selected' : ''}>${y}</option>`;
  }

  // Month selector
  mesSel.innerHTML = "";
  MONTHS_ES.forEach((m, i) => {
    const val = i + 1;
    mesSel.innerHTML += `<option value="${val}" ${val === finanzasMes ? 'selected' : ''}>${m}</option>`;
  });

  // Read current values from selects (in case user changed them)
  finanzasAnio = parseInt(anioSel.value);
  finanzasMes = parseInt(mesSel.value);
}

function _updateTipoFilterButtons() {
  document.querySelectorAll("#finanzas-tipo-filtros button").forEach(btn => {
    const t = btn.getAttribute("data-tipo");
    if (t === finanzasTipoFilter) {
      btn.className = "px-3 py-1 rounded-full text-xs font-medium transition bg-navy text-ivory";
    } else {
      btn.className = "px-3 py-1 rounded-full text-xs font-medium transition bg-ivory-dark text-charcoal/60 hover:bg-ivory-dark";
    }
  });
}

function filterFinanzasTipo(tipo) {
  finanzasTipoFilter = tipo;
  _updateTipoFilterButtons();
  _renderFinanzasList();
}
window.filterFinanzasTipo = filterFinanzasTipo;

async function loadFinanzas() {
  _initFinanzasSelectors();
  _updateTipoFilterButtons();

  const anioSel = document.getElementById("finanzas-anio");
  const mesSel = document.getElementById("finanzas-mes");
  finanzasAnio = parseInt(anioSel.value);
  finanzasMes = parseInt(mesSel.value);

  // Fetch resumen + all registros + eventos (for evento name lookup) in parallel
  const [resumen, registros, eventos] = await Promise.all([
    apiGet(`/finanzas/resumen/mensual?anio=${finanzasAnio}&mes=${finanzasMes}`),
    apiGet("/finanzas/"),
    apiGet("/eventos/"),
  ]);

  // Build evento name lookup
  _finanzasEventos = {};
  eventos.forEach(e => { _finanzasEventos[e.id] = e.titulo; });

  // Filter registros to selected month
  _finanzasRegistros = registros.filter(r => {
    const d = new Date(r.fecha);
    return d.getFullYear() === finanzasAnio && (d.getMonth() + 1) === finanzasMes;
  });

  // Summary cards
  document.getElementById("finanzas-summary").innerHTML = `
    <div class="bg-white rounded-lg shadow-sm p-5 border border-ivory-dark text-center">
      <p class="text-xs uppercase tracking-wider text-charcoal/40 mb-1">Ingresos</p>
      <p class="text-2xl font-display text-navy">$${resumen.ingresos?.toLocaleString("es-AR") || 0}</p>
    </div>
    <div class="bg-white rounded-lg shadow-sm p-5 border border-ivory-dark text-center">
      <p class="text-xs uppercase tracking-wider text-charcoal/40 mb-1">Egresos</p>
      <p class="text-2xl font-display text-red-500">$${resumen.egresos?.toLocaleString("es-AR") || 0}</p>
    </div>
    <div class="bg-white rounded-lg shadow-sm p-5 border border-ivory-dark text-center">
      <p class="text-xs uppercase tracking-wider text-charcoal/40 mb-1">Balance</p>
      <p class="text-2xl font-display ${resumen.balance >= 0 ? 'text-green-600' : 'text-red-500'}">$${resumen.balance?.toLocaleString("es-AR") || 0}</p>
    </div>
  `;

  _renderFinanzasList();
}

function _renderFinanzasList() {
  const filtered = finanzasTipoFilter === "todos"
    ? _finanzasRegistros
    : _finanzasRegistros.filter(r => r.tipo === finanzasTipoFilter);

  const cont = document.getElementById("finanzas-list");
  if (filtered.length === 0) {
    cont.innerHTML = `<div class="text-center py-8 text-charcoal/40">
      <span class="material-symbols-outlined text-4xl mb-2 block">receipt_long</span>
      <p>No hay registros para ${MONTHS_ES[finanzasMes - 1]} ${finanzasAnio}</p>
    </div>`;
    return;
  }

  cont.innerHTML = filtered.sort((a, b) => new Date(b.fecha) - new Date(a.fecha)).map(r => {
    const fechaStr = new Date(r.fecha).toLocaleDateString("es-AR", { day: "2-digit", month: "short" });
    const icon = r.tipo === "ingreso" ? "trending_up" : "trending_down";
    const tipoBadge = r.tipo === "ingreso"
      ? "bg-green-100 text-green-700"
      : "bg-red-100 text-red-700";
    const tipoLabel = r.tipo === "ingreso" ? "+" : "-";
    const eventoName = r.evento_id ? (_finanzasEventos[r.evento_id] || `Evento #${r.evento_id}`) : "";
    const conceptoEsc = r.concepto.replace(/'/g, "\\'");

    return `<div class="flex items-center justify-between py-2.5 px-1 border-b border-ivory-dark/60 last:border-0 hover:bg-ivory-dark/30 rounded transition">
      <div class="flex items-center gap-3 min-w-0 flex-1">
        <span class="material-symbols-outlined text-lg ${r.tipo === 'ingreso' ? 'text-green-600' : 'text-red-500'}">${icon}</span>
        <div class="min-w-0">
          <p class="font-medium truncate">${r.concepto}</p>
          <div class="flex items-center gap-2 text-xs text-charcoal/40">
            <span>${fechaStr}</span>
            ${eventoName ? `<span class="flex items-center gap-0.5"><span class="material-symbols-outlined text-[12px]">link</span>${eventoName}</span>` : ''}
            ${r.notas ? `<span class="italic truncate max-w-[120px]" title="${r.notas}">${r.notas}</span>` : ''}
          </div>
        </div>
      </div>
      <div class="flex items-center gap-2 flex-shrink-0 ml-3">
        <span class="text-xs px-2 py-0.5 rounded ${tipoBadge}">${r.tipo}</span>
        <span class="font-display font-semibold ${r.tipo === 'ingreso' ? 'text-green-600' : 'text-red-500'}">${tipoLabel}$${r.monto?.toLocaleString("es-AR")}</span>
        <button onclick="confirmarEliminarFinanza(${r.id},'${conceptoEsc}')" class="p-1 hover:bg-red-50 rounded-lg transition" title="Eliminar">
          <span class="material-symbols-outlined text-base text-charcoal/40 hover:text-red-500">delete</span>
        </button>
      </div>
    </div>`;
  }).join("");
}

// ─── Crear registro financiero ───
let _finanzasPresupuestos = [];

window.openFinanzaModal = async function() {
  // Cargar presupuestos para el dropdown
  const presupuestos = await apiGet("/presupuestos/");
  _finanzasPresupuestos = presupuestos || [];

  const pptoOpts = _finanzasPresupuestos.map(p =>
    `<option value="${p.id}">#${p.id} ${p.cliente_nombre || ''} – ${p.tipo_evento || ''} – $${(p.total||0).toLocaleString('es-AR')} (${p.estado})</option>`
  ).join("");

  showModal(`
    <h3 class="font-display text-xl mb-4">Nuevo Registro</h3>
    <form onsubmit="crearFinanza(event)">
      <div class="space-y-3">
        <div>
          <label class="block text-sm mb-1 font-medium">Tipo</label>
          <div class="flex gap-2">
            <label class="flex-1 cursor-pointer">
              <input type="radio" name="tipo" value="ingreso" checked class="hidden peer" onchange="_togglePresupuestoDropdown()"/>
              <div class="peer-checked:bg-green-100 peer-checked:border-green-500 peer-checked:text-green-700 border border-ivory-dark rounded-lg p-2 text-center text-sm font-medium transition hover:bg-ivory-dark">
                <span class="material-symbols-outlined text-lg align-middle mr-1">trending_up</span>Ingreso
              </div>
            </label>
            <label class="flex-1 cursor-pointer">
              <input type="radio" name="tipo" value="egreso" class="hidden peer" onchange="_togglePresupuestoDropdown()"/>
              <div class="peer-checked:bg-red-100 peer-checked:border-red-500 peer-checked:text-red-700 border border-ivory-dark rounded-lg p-2 text-center text-sm font-medium transition hover:bg-ivory-dark">
                <span class="material-symbols-outlined text-lg align-middle mr-1">trending_down</span>Egreso
              </div>
            </label>
          </div>
        </div>
        <div id="finanza-ppto-row" class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-sm mb-1 font-medium">Vincular Presupuesto</label>
            <select id="finanza-ppto-id" onchange="_onPresupuestoSelect()" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none">
              <option value="">— Sin presupuesto —</option>
              ${pptoOpts}
            </select>
          </div>
          <div>
            <label class="block text-sm mb-1 font-medium">Monto del presupuesto</label>
            <div id="finanza-ppto-monto" class="border border-ivory-dark rounded-lg p-2 bg-ivory-dark/30 text-sm text-charcoal/50">—</div>
          </div>
        </div>
        <div>
          <label class="block text-sm mb-1 font-medium">Concepto</label>
          <input name="concepto" id="finanza-concepto" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" placeholder="Ej: Seña Boda García"/>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-sm mb-1 font-medium">Monto ($)</label>
            <input name="monto" id="finanza-monto" type="number" step="0.01" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" placeholder="0.00"/>
          </div>
          <div>
            <label class="block text-sm mb-1 font-medium">Fecha</label>
            <input name="fecha" type="date" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${new Date().toISOString().slice(0,10)}"/>
          </div>
        </div>
        <div>
          <label class="block text-sm mb-1 font-medium">Notas</label>
          <textarea name="notas" rows="2" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" placeholder="Opcional..."></textarea>
        </div>
      </div>
      <button type="submit" class="mt-4 bg-primary text-on-primary px-4 py-2 rounded-lg hover:opacity-90 transition w-full font-medium">Guardar Registro</button>
    </form>
  `);
};

window._togglePresupuestoDropdown = function() {
  const tipo = document.querySelector('input[name="tipo"]:checked')?.value;
  const row = document.getElementById("finanza-ppto-row");
  if (row) row.style.display = tipo === "ingreso" ? "" : "none";
};

window._onPresupuestoSelect = function() {
  const sel = document.getElementById("finanza-ppto-id");
  const montoEl = document.getElementById("finanza-ppto-monto");
  const conceptoEl = document.getElementById("finanza-concepto");
  const montoInput = document.getElementById("finanza-monto");
  const pptoId = parseInt(sel?.value) || null;
  const ppto = _finanzasPresupuestos.find(p => p.id === pptoId);
  if (ppto) {
    montoEl.textContent = `$${(ppto.total||0).toLocaleString("es-AR")}`;
    conceptoEl.value = `Presupuesto #${ppto.id} – ${ppto.cliente_nombre || ''} ${ppto.tipo_evento || ''}`;
    montoInput.value = ppto.total || "";
  } else {
    montoEl.textContent = "—";
  }
};

window.crearFinanza = async function(ev) {
  ev.preventDefault();
  const fd = new FormData(ev.target);
  const tipo = fd.get("tipo");
  const concepto = fd.get("concepto");
  const monto = parseFloat(fd.get("monto"));
  const fecha = fd.get("fecha");
  const notas = fd.get("notas") || "";
  const presupuestoId = parseInt(document.getElementById("finanza-ppto-id")?.value) || null;

  if (!tipo || !concepto || isNaN(monto) || monto <= 0) {
    toast("Completa todos los campos correctamente", "error");
    return;
  }

  await apiPost("/finanzas/", {
    tipo,
    concepto,
    monto,
    fecha: fecha ? new Date(fecha + "T12:00:00").toISOString() : new Date().toISOString(),
    notas,
    evento_id: null,
    presupuesto_id: presupuestoId,
  });

  closeModal();
  loadFinanzas();
  toast("Registro creado");
};

// ─── Eliminar registro financiero ───
window.confirmarEliminarFinanza = function(id, concepto) {
  showModal(`
    <h3 class="font-display text-xl mb-4 text-red-600">Eliminar Registro</h3>
    <p class="text-sm mb-4">¿Estás seguro de eliminar <strong>${concepto}</strong>? Esta acción no se puede deshacer.</p>
    <div class="flex gap-2">
      <button onclick="closeModal()" class="flex-1 bg-ivory-dark text-charcoal px-4 py-2 rounded-lg hover:bg-ivory transition font-medium">Cancelar</button>
      <button onclick="eliminarFinanza(${id})" class="flex-1 bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600 transition font-medium">Eliminar</button>
    </div>
  `);
};

window.eliminarFinanza = async function(id) {
  try {
    await apiDelete(`/finanzas/${id}`);
    closeModal();
    loadFinanzas();
    toast("Registro eliminado");
  } catch (e) {
    toast("Error: " + e.message, "error");
  }
};

// ─── WHATSAPP ───
window.checkWhatsAppStatus = async function() {
  const url = document.getElementById("wa-url").value;
  const key = document.getElementById("wa-key").value;
  const instance = document.getElementById("wa-instance").value || "mi-whatsapp";
  if (!url) { toast("Ingresa la URL de Evolution API", "error"); return; }
  try {
    const r = await fetch(`${url}/instance/fetchInstances`, {
      headers: key ? { "apikey": key } : {}
    });
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
    } else {
      throw new Error("Error");
    }
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
    const r = await fetch(`${url}/webhook/set/${instance}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", apikey: key },
      body: JSON.stringify({
        webhook: { url: "${BASE_URL}/whatsapp/webhook", enabled: true, events: ["messages.upsert"] }
      })
    });
    if (r.ok) { toast("Webhook configurado correctamente"); }
    else { toast("Error configurando webhook: " + await r.text(), "error"); }
  } catch { toast("No se pudo conectar con Evolution API", "error"); }
};

// ─── CONFIGURACION BOT ───

// Cargar config desde el backend
async function loadWhatsAppConfig() {
  try {
    const res = await fetch("${BASE_URL}/whatsapp/admin/config");
    const config = await res.json();

    // Bot activo
    const active = document.getElementById("wa-bot-active");
    active.checked = config.bot_activo === "true";
    document.getElementById("wa-bot-status-label").textContent = active.checked ? "Bot activo" : "Bot pausado";

    // Mensajes
    document.getElementById("wa-saludo-texto").value = config.saludo_texto || "¡Hola! Soy el asistente de Azul Alquileres 🪑";
    document.getElementById("wa-menu-texto").value = config.menu_texto || "Comandos disponibles:...";

    // Recordatorios
    document.getElementById("wa-recordatorio-hs").value = config.recordatorio_hs || "48";

    // Comandos
    document.getElementById("cmd-stock").checked = config.comando_stock === "true";
    document.getElementById("cmd-disponible").checked = config.comando_disponible === "true";
    document.getElementById("cmd-eventos").checked = config.comando_eventos === "true";
    document.getElementById("cmd-presupuesto").checked = config.comando_presupuesto === "true";
  } catch { /* silent fail on first load */ }
}

window.toggleBotActive = async function() {
  const active = document.getElementById("wa-bot-active");
  const label = document.getElementById("wa-bot-status-label");
  label.textContent = active.checked ? "Bot activo" : "Bot pausado";
  try {
    await fetch("${BASE_URL}/whatsapp/admin/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ clave: "bot_activo", valor: active.checked ? "true" : "false" })
    });
    toast(active.checked ? "Bot activado" : "Bot pausado");
  } catch { toast("Error guardando configuracion", "error"); }
};

window.saveBotMessages = async function() {
  const saludo = document.getElementById("wa-saludo-texto").value;
  const menu = document.getElementById("wa-menu-texto").value;
  try {
    await fetch("${BASE_URL}/whatsapp/admin/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ clave: "saludo_texto", valor: saludo })
    });
    await fetch("${BASE_URL}/whatsapp/admin/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ clave: "menu_texto", valor: menu })
    });
    toast("Mensajes guardados");
  } catch { toast("Error guardando mensajes", "error"); }
};

window.toggleComando = async function(clave) {
  const el = document.getElementById(clave === "comando_stock" ? "cmd-stock"
    : clave === "comando_disponible" ? "cmd-disponible"
    : clave === "comando_eventos" ? "cmd-eventos" : "cmd-presupuesto");
  const valor = el.checked ? "true" : "false";
  try {
    await fetch("${BASE_URL}/whatsapp/admin/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ clave, valor })
    });
  } catch { toast("Error actualizando comando", "error"); }
};

window.saveRecordatorio = async function() {
  const hs = document.getElementById("wa-recordatorio-hs").value;
  try {
    await fetch("${BASE_URL}/whatsapp/admin/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ clave: "recordatorio_hs", valor: String(hs) })
    });
    toast(`Recordatorio configurado a ${hs} horas`);
  } catch { toast("Error guardando recordatorio", "error"); }
};

window.sendTestMessage = async function() {
  const numero = document.getElementById("wa-test-numero").value;
  const texto = document.getElementById("wa-test-texto").value;
  if (!numero || !texto) { toast("Completa numero y mensaje", "error"); return; }
  try {
    const res = await fetch(`${BASE_URL}/whatsapp/enviar/${encodeURIComponent(numero)}?texto=${encodeURIComponent(texto)}`);
    const data = await res.json();
    const detail = document.getElementById("wa-test-result");
    detail.classList.remove("hidden");
    if (data.ok) {
      detail.textContent = "✅ Mensaje enviado";
      detail.className = "mt-2 text-xs text-green-600";
    } else {
      detail.textContent = "❌ " + (data.error || "Error al enviar");
      detail.className = "mt-2 text-xs text-red-500";
    }
  } catch {
    document.getElementById("wa-test-result").classList.remove("hidden");
    document.getElementById("wa-test-result").textContent = "❌ Error de conexion con el servidor";
    document.getElementById("wa-test-result").className = "mt-2 text-xs text-red-500";
  }
};

// Cargar config al navegar a la pagina
const _origNavigate = window.navigate;
window.navigate = function(page, data) {
  if (typeof _origNavigate === "function") _origNavigate(page, data);
  if (page === "whatsapp") setTimeout(loadWhatsAppConfig, 100);
};

// ─── MODAL ───
function showModal(html) {
  document.getElementById("modal-content").innerHTML = html;
  document.getElementById("modal-overlay").classList.remove("hidden");
}

function closeModal() {
  document.getElementById("modal-overlay").classList.add("hidden");
  const mc = document.getElementById("modal-content");
  mc.classList.remove("max-w-3xl");
  mc.classList.add("max-w-lg");
}

window.closeModal = closeModal;

// ─── TOAST ───
function toast(msg, type="ok") {
  const existing = document.getElementById("toast-msg");
  if (existing) existing.remove();
  const t = document.createElement("div");
  t.id = "toast-msg";
  t.className = `fixed bottom-6 right-6 px-5 py-3 rounded-lg shadow-lg text-sm font-medium z-[100] transition-all transform translate-y-0 opacity-100 ${type === "error" ? "bg-red-500 text-white" : "bg-navy-darker text-ivory"}`;
  t.innerHTML = `<span class="material-symbols-outlined text-sm align-middle mr-1">${type === "error" ? "error" : "check_circle"}</span> ${msg}`;
  document.body.appendChild(t);
  setTimeout(() => { t.style.opacity = "0"; t.style.transform = "translateY(10px)"; setTimeout(() => t.remove(), 400); }, 2500);
}
window.toast = toast;

// ─── INIT ───
navigate("dashboard");
