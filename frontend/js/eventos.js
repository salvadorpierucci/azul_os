// ─── EVENTOS ───

// Helpers de fecha sin timezone issues (extrae YYYY-MM-DD[-HH:MM] del string directamente)
const _EVT_MESES_CORTOS = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"];
const _EVT_MESES_LARGOS = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"];
function _evtFmtFecha(fechaStr, largo = false) {
  if (!fechaStr) return "—";
  const m = String(fechaStr).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return fechaStr;
  const dd = m[3], mm = parseInt(m[2], 10) - 1, yyyy = m[1];
  const meses = largo ? _EVT_MESES_LARGOS : _EVT_MESES_CORTOS;
  return `${dd} ${meses[mm]} ${yyyy}`;
}
function _evtFmtHora(fechaStr) {
  if (!fechaStr) return "";
  const m = String(fechaStr).match(/(\d{2}):(\d{2})/);
  if (!m) return "";
  return `${m[1]}:${m[2]}`;
}
// Para <input type="datetime-local">: extrae YYYY-MM-DDTHH:MM del string sin mezclar timezones
function _evtFechaLocalInput(fechaStr) {
  if (!fechaStr) return "";
  const m = String(fechaStr).match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/);
  if (m) return `${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}`;
  const dm = String(fechaStr).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (dm) return `${dm[1]}-${dm[2]}-${dm[3]}T00:00`;
  return "";
}

async function loadEventos() {
  const eventos = await apiGet("/eventos/");
  const cont = document.getElementById("eventos-list");
  const searchEl = document.getElementById("evento-search");
  if (searchEl) eventoSearch = searchEl.value.trim().toLowerCase();
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
                  e.estado === "cancelado" ? "bg-red-100 text-red-700" : "bg-green-100 text-green-700";
    const pagoBadge = e.estado_pago === "pagado" ? "bg-green-100 text-green-700" :
                      e.estado_pago === "seña" ? "bg-yellow-100 text-yellow-700" :
                      e.estado_pago === "parcial" ? "bg-orange-100 text-orange-700" : "bg-gray-100 text-gray-600";
    const fecha = _evtFmtFecha(e.fecha);
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

window.onEventoSearch = function(val) { eventoSearch = val.trim().toLowerCase(); loadEventos(); };

window.verEvento = async function(id) {
  const ev = await apiGet(`/eventos/${id}`);
  const fecha = _evtFmtFecha(ev.fecha, true);
  const hora = _evtFmtHora(ev.fecha);
  const badge = ev.estado === "confirmado" ? "bg-primary text-on-primary" :
                ev.estado === "reserva" ? "bg-yellow-400 text-charcoal" :
                ev.estado === "cancelado" ? "bg-red-100 text-red-700" : "bg-green-100 text-green-700";
  const pagoBadge = ev.estado_pago === "pagado" ? "bg-green-100 text-green-700" :
                    ev.estado_pago === "seña" ? "bg-yellow-100 text-yellow-700" :
                    ev.estado_pago === "parcial" ? "bg-orange-100 text-orange-700" : "bg-gray-100 text-gray-600";
  let itemsHtml = "";
  if (ev.items && ev.items.length > 0) {
    itemsHtml = `<div class="mt-4 border-t border-ivory-dark pt-4">
      <h4 class="font-medium mb-2 text-sm uppercase text-charcoal/50 tracking-wider">Mobiliario</h4>
      <div class="space-y-1">
        ${ev.items.map(i => `<div class="flex justify-between text-sm py-1 border-b border-ivory-dark/50 last:border-0">
          <div class="flex-1"><span class="text-charcoal/40 text-xs">(${i.categoria})</span> ${i.nombre}</div>
          <div class="text-right">
            <span class="text-charcoal/50">${i.cantidad}x $${i.precio_unitario?.toLocaleString("es-AR")}</span>
            <span class="font-medium ml-2">$${i.subtotal?.toLocaleString("es-AR")}</span>
          </div>
        </div>`).join("")}
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
  showModal(`<h3 class="font-display text-xl mb-4">${ev.titulo}</h3>
    <div class="space-y-2 text-sm">
      <div class="flex justify-between"><span class="text-charcoal/50">Cliente</span><span class="font-medium">${ev.cliente_nombre}</span></div>
      <div class="flex justify-between"><span class="text-charcoal/50">Fecha</span><span>${fecha} — ${hora}hs</span></div>
      ${ev.lugar ? `<div class="flex justify-between"><span class="text-charcoal/50">Lugar</span><span>${ev.lugar}</span></div>` : ''}
      <div class="flex justify-between items-center"><span class="text-charcoal/50">Estado</span><span class="text-xs px-2 py-1 rounded ${badge}">${ev.estado}</span></div>
      <div class="flex justify-between items-center"><span class="text-charcoal/50">Pago</span><span class="text-xs px-2 py-1 rounded ${pagoBadge}">${ev.estado_pago}</span></div>
      ${ev.notas ? `<div class="mt-2"><span class="text-charcoal/50 block mb-1">Notas</span><p class="bg-ivory-dark/50 p-2 rounded text-sm">${ev.notas}</p></div>` : ''}
    </div>${itemsHtml}
    <div class="mt-4 flex gap-2">
      <button onclick="closeModal();editarEventoModal(${ev.id})" class="flex-1 bg-primary text-on-primary px-4 py-2 rounded-lg hover:opacity-90 transition text-sm flex items-center justify-center gap-1"><span class="material-symbols-outlined text-base">edit</span> Editar</button>
      <button onclick="closeModal();confirmarEliminarEvento(${ev.id},'${ev.titulo.replace(/'/g,"\\'")}')" class="bg-red-50 text-red-600 px-4 py-2 rounded-lg hover:bg-red-100 transition text-sm flex items-center justify-center gap-1"><span class="material-symbols-outlined text-base">delete</span> Eliminar</button>
    </div>`);
};

window.openEventoModal = async function() {
  const clientes = await apiGet("/clientes/");
  showModal(`<h3 class="font-display text-xl mb-4">Nuevo Evento</h3>
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
          <div><label class="block text-sm mb-1 font-medium">Fecha</label><input name="fecha" type="datetime-local" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
          <div><label class="block text-sm mb-1 font-medium">Lugar</label><input name="lugar" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="block text-sm mb-1 font-medium">Traslado ($)</label><input name="costo_traslado" type="number" value="0" step="0.01" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
          <div><label class="block text-sm mb-1 font-medium">Mano de obra ($)</label><input name="costo_mano_obra" type="number" value="0" step="0.01" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="block text-sm mb-1 font-medium">Estado</label><select name="estado" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"><option value="reserva">Reserva</option><option value="confirmado">Confirmado</option></select></div>
          <div><label class="block text-sm mb-1 font-medium">Pago</label><select name="estado_pago" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"><option value="pendiente">Pendiente</option><option value="seña">Con seña</option><option value="pagado">Pagado</option></select></div>
        </div>
        <div><label class="block text-sm mb-1 font-medium">Notas</label><textarea name="notas" rows="2" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"></textarea></div>
      </div>
      <button type="submit" class="mt-4 bg-primary text-on-primary px-4 py-2 rounded-lg hover:opacity-90 transition w-full font-medium">Crear Evento</button>
    </form>`);
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
  closeModal(); loadEventos(); toast("Evento creado");
};

window.editarEventoModal = async function(id) {
  const ev = await apiGet(`/eventos/${id}`);
  const clientes = await apiGet("/clientes/");
  const fechaLocal = _evtFechaLocalInput(ev.fecha);
  showModal(`<h3 class="font-display text-xl mb-4">Editar Evento</h3>
    <form onsubmit="guardarEvento(event, ${id})">
      <div class="space-y-3">
        <div><label class="block text-sm mb-1 font-medium">Cliente</label>
          <select name="cliente_id" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none">
            ${clientes.map(c => `<option value="${c.id}" ${c.id === ev.cliente_id ? 'selected' : ''}>${c.nombre}</option>`).join("")}
          </select></div>
        <div><label class="block text-sm mb-1 font-medium">Titulo</label><input name="titulo" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${ev.titulo}"/></div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="block text-sm mb-1 font-medium">Fecha</label><input name="fecha" type="datetime-local" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${fechaLocal}"/></div>
          <div><label class="block text-sm mb-1 font-medium">Lugar</label><input name="lugar" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${ev.lugar || ''}"/></div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="block text-sm mb-1 font-medium">Traslado ($)</label><input name="costo_traslado" type="number" step="0.01" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${ev.costo_traslado || 0}"/></div>
          <div><label class="block text-sm mb-1 font-medium">Mano de obra ($)</label><input name="costo_mano_obra" type="number" step="0.01" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${ev.costo_mano_obra || 0}"/></div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="block text-sm mb-1 font-medium">Estado</label><select name="estado" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none">
            <option value="reserva" ${ev.estado==='reserva'?'selected':''}>Reserva</option><option value="confirmado" ${ev.estado==='confirmado'?'selected':''}>Confirmado</option><option value="completado" ${ev.estado==='completado'?'selected':''}>Completado</option><option value="cancelado" ${ev.estado==='cancelado'?'selected':''}>Cancelado</option></select></div>
          <div><label class="block text-sm mb-1 font-medium">Pago</label><select name="estado_pago" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none">
            <option value="pendiente" ${ev.estado_pago==='pendiente'?'selected':''}>Pendiente</option><option value="seña" ${ev.estado_pago==='seña'?'selected':''}>Con seña</option><option value="parcial" ${ev.estado_pago==='parcial'?'selected':''}>Parcial</option><option value="pagado" ${ev.estado_pago==='pagado'?'selected':''}>Pagado</option></select></div>
        </div>
        <div><label class="block text-sm mb-1 font-medium">Seña ($)</label><input name="monto_senia" type="number" step="0.01" value="${ev.monto_senia || 0}" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
        <div><label class="block text-sm mb-1 font-medium">Notas</label><textarea name="notas" rows="2" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none">${ev.notas || ''}</textarea></div>
      </div>
      <button type="submit" class="mt-4 bg-primary text-on-primary px-4 py-2 rounded-lg hover:opacity-90 transition w-full font-medium">Guardar Cambios</button>
    </form>`);
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
  await apiPut(`/eventos/${id}`, data); closeModal(); loadEventos(); toast("Evento actualizado");
};

window.confirmarEliminarEvento = function(id, titulo) {
  showModal(`<h3 class="font-display text-xl mb-4 text-red-600">Eliminar Evento</h3>
    <p class="text-sm mb-4">¿Estas seguro de eliminar <strong>${titulo}</strong>? Esta accion no se puede deshacer.</p>
    <div class="flex gap-2">
      <button onclick="closeModal()" class="flex-1 bg-ivory-dark text-charcoal px-4 py-2 rounded-lg hover:bg-ivory transition font-medium">Cancelar</button>
      <button onclick="eliminarEvento(${id})" class="flex-1 bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600 transition font-medium">Eliminar</button>
    </div>`);
};

window.eliminarEvento = async function(id) {
  await apiDelete(`/eventos/${id}`); closeModal(); loadEventos(); toast("Evento eliminado");
};
