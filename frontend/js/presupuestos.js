// ─── PRESUPUESTOS ───

// Helper: formatea fecha sin timezone issues.
// Acepta "2026-07-03", "2026-07-03 00:00:00.000000", "2026-07-03T00:00:00" etc.
// Siempre extrae YYYY-MM-DD del string y formatea local (es-AR).
const _MESES_CORTOS = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"];
const _MESES_LARGOS = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"];
function _fmtFecha(fechaStr, largo = false) {
  if (!fechaStr) return "—";
  const m = String(fechaStr).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return fechaStr;
  const dd = m[3], mm = parseInt(m[2], 10) - 1, yyyy = m[1];
  const meses = largo ? _MESES_LARGOS : _MESES_CORTOS;
  return `${dd} ${meses[mm]} ${yyyy}`;
}

// Devuelve YYYY-MM-DD en hora local (no UTC) para usar como fallback en inputs.
function _hoyLocal() {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

async function loadPresupuestos() {
  presupuestosList = await apiGet("/presupuestos/");
  _presupuestosList = presupuestosList || [];
  const searchEl = document.getElementById("ppto-search");
  if (searchEl) pptoSearch = searchEl.value.trim().toLowerCase();
  _updatePptoEstadoFilterButtons();
  renderPresupuestosList();
}

function _updatePptoEstadoFilterButtons() {
  document.querySelectorAll("#ppto-estado-filtros button").forEach(btn => {
    const e = btn.getAttribute("data-estado");
    if (e === pptoEstadoFilter) btn.className = "px-3 py-1 rounded-full text-xs font-medium transition bg-navy text-ivory";
    else btn.className = "px-3 py-1 rounded-full text-xs font-medium transition bg-ivory-dark text-charcoal/60 hover:bg-ivory-dark";
  });
}

window.filterPptoEstado = function(estado) { pptoEstadoFilter = estado; _updatePptoEstadoFilterButtons(); renderPresupuestosList(); };
window.onPptoSearch = function(val) { pptoSearch = val.trim().toLowerCase(); renderPresupuestosList(); };

function renderPresupuestosList() {
  let filtered = _presupuestosList;
  if (pptoEstadoFilter) filtered = filtered.filter(p => p.estado === pptoEstadoFilter);
  if (pptoSearch) filtered = filtered.filter(p => (p.nombre || "").toLowerCase().includes(pptoSearch) || (p.cliente_nombre || "").toLowerCase().includes(pptoSearch) || (p.tipo_evento || "").toLowerCase().includes(pptoSearch));
  const cont = document.getElementById("presupuestos-list");
  if (!cont) return;
  if (filtered.length === 0) {
    cont.innerHTML = `<div class="text-center py-12 text-charcoal/40"><span class="material-symbols-outlined text-5xl mb-2 block">receipt_long</span><p>${pptoSearch || pptoEstadoFilter ? 'Sin resultados' : 'No hay presupuestos'}</p></div>`;
    return;
  }
  cont.innerHTML = filtered.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0)).map(p => {
    const fecha = _fmtFecha(p.fecha_evento);
    const created = p.created_at ? new Date(p.created_at).toLocaleDateString("es-AR", { day:"2-digit", month:"short" }) : "";
    const badge = _pptoEstadoBadge(p.estado);
    const displayNombre = p.nombre || `${p.cliente_nombre || "Presupuesto"} · ${p.tipo_evento || ""}`;
    return `<div class="bg-white rounded-lg shadow-sm border border-ivory-dark hover:shadow-md transition-shadow">
      <div class="p-4 flex items-center justify-between cursor-pointer" onclick="verPresupuestoDetalle(${p.id})">
        <div class="flex-1 min-w-0">
          <p class="font-medium truncate">${displayNombre}</p>
          <div class="flex items-center gap-3 text-sm text-charcoal/60 mt-1"><span class="flex items-center gap-1"><span class="material-symbols-outlined text-xs">calendar_today</span>${fecha}</span>${p.cliente_nombre ? `<span class="text-xs text-charcoal/40">${p.cliente_nombre}</span>` : ''}${created ? `<span class="text-xs text-charcoal/30">· ${created}</span>` : ''}</div>
        </div>
        <div class="flex items-center gap-2 flex-shrink-0 ml-3"><span class="font-display text-navy">$${p.total?.toLocaleString("es-AR") || 0}</span><span class="text-xs px-2 py-1 rounded ${badge}">${p.estado || "borrador"}</span></div>
      </div>
    </div>`;
  }).join("");
}

window.verPresupuestoDetalle = async function(id) {
  const p = await apiGet(`/presupuestos/${id}`);
  const fecha = _fmtFecha(p.fecha_evento, true);
  const badge = _pptoEstadoBadge(p.estado);
  let lugaresHtml = "";
  if (p.lugares && p.lugares.length > 0) {
    lugaresHtml = `<div class="mt-4 border-t border-ivory-dark pt-4"><h4 class="font-medium mb-3 text-sm uppercase text-charcoal/50 tracking-wider">Mobiliario por Lugar</h4><div class="space-y-4">`;
    p.lugares.forEach(lug => {
      const items = lug.productos || lug.items || [];
      lugaresHtml += `<div class="bg-ivory-dark/30 rounded-lg p-3"><p class="font-medium text-sm text-navy mb-2">${lug.nombre || "Sin nombre"}</p><div class="space-y-1">`;
      if (items.length > 0) {
        items.forEach(it => {
          const nombre = it.nombre || it.catalogo_key || "Mobiliario";
          const cant = it.cantidad || 1;
          const subtotal = it.subtotal || (cant * (it.precio_unitario || 0));
          lugaresHtml += `<div class="flex justify-between text-sm py-1 border-b border-ivory-dark/50 last:border-0"><span>${cant}x ${nombre}</span><span class="font-medium">$${subtotal.toLocaleString("es-AR")}</span></div>`;
        });
      } else { lugaresHtml += `<p class="text-sm text-charcoal/40">Sin items</p>`; }
      lugaresHtml += `</div></div>`;
    });
    lugaresHtml += `</div></div>`;
  }
  const mc = document.getElementById("modal-content");
  mc.classList.remove("max-w-lg"); mc.classList.add("max-w-3xl");
  showModal(`<h3 class="font-display text-xl mb-4">${p.nombre || p.cliente_nombre || "Presupuesto #" + p.id}</h3>
    <div class="space-y-2 text-sm">
      ${p.nombre ? `<div class="flex justify-between"><span class="text-charcoal/50">Presupuesto</span><span class="font-medium">${p.nombre}</span></div>` : ""}
      <div class="flex justify-between"><span class="text-charcoal/50">Cliente</span><span class="font-medium">${p.cliente_nombre || "—"}</span></div>
      <div class="flex justify-between"><span class="text-charcoal/50">Tipo de Evento</span><span>${p.tipo_evento || "—"}</span></div>
      <div class="flex justify-between"><span class="text-charcoal/50">Fecha del Evento</span><span>${fecha}</span></div>
      <div class="flex justify-between"><span class="text-charcoal/50">Invitados</span><span>${p.cantidad_invitados || "—"}</span></div>
      <div class="flex justify-between"><span class="text-charcoal/50">Localidad</span><span>${p.localidad || "—"}</span></div>
      <div class="flex justify-between items-center"><span class="text-charcoal/50">Estado</span><span class="text-xs px-2 py-1 rounded ${badge}">${p.estado || "borrador"}</span></div>
    </div>${lugaresHtml}
    <div class="mt-4 border-t border-ivory-dark pt-3 text-sm space-y-1">
      <div class="flex justify-between"><span class="text-charcoal/50">Subtotal Mobiliario</span><span>$${(p.subtotal_mobiliario || 0).toLocaleString("es-AR")}</span></div>
      <div class="flex justify-between"><span class="text-charcoal/50">Traslado${p.distancia_km ? " (" + p.distancia_km + "km)" : ""}</span><span>$${(p.costo_logistica || 0).toLocaleString("es-AR")}</span></div>
      ${(p.costo_armado || 0) > 0 ? `<div class="flex justify-between"><span class="text-charcoal/50">Armado y desarme</span><span>$${(p.costo_armado || 0).toLocaleString("es-AR")}</span></div>` : ""}
      <div class="flex justify-between font-display text-lg border-t border-ivory-dark pt-1 mt-1"><span>Total</span><span class="text-navy">$${(p.total || 0).toLocaleString("es-AR")}</span></div>
    </div>
    <div class="mt-5 flex flex-wrap gap-2">
      <button onclick="closeModal();editarPresupuestoModal(${p.id})" class="flex-1 bg-primary text-on-primary px-3 py-2 rounded-lg hover:opacity-90 transition text-sm flex items-center justify-center gap-1"><span class="material-symbols-outlined text-base">edit</span> Editar</button>
      <button onclick="confirmarEliminarPresupuesto(${p.id})" class="bg-red-50 text-red-600 px-3 py-2 rounded-lg hover:bg-red-100 transition text-sm flex items-center justify-center gap-1"><span class="material-symbols-outlined text-base">delete</span> Eliminar</button>
      <button onclick="convertirPresupuestoEvento(${p.id})" class="bg-green-50 text-green-700 px-3 py-2 rounded-lg hover:bg-green-100 transition text-sm flex items-center justify-center gap-1"><span class="material-symbols-outlined text-base">event</span> Convertir en Evento</button>
    </div>
    <div class="mt-3 flex flex-wrap gap-2 border-t border-ivory-dark pt-3">
      <span class="text-xs text-charcoal/40 self-center mr-1">Descargar:</span>
      <a href="${BASE_URL}/api/presupuestos/${p.id}/pdf/completo" target="_blank" class="px-3 py-1.5 bg-ivory-dark rounded-lg text-xs font-medium hover:bg-ivory transition flex items-center gap-1"><span class="material-symbols-outlined text-sm">description</span> Completo</a>
      <a href="${BASE_URL}/api/presupuestos/${p.id}/pdf/cliente" target="_blank" class="px-3 py-1.5 bg-ivory-dark rounded-lg text-xs font-medium hover:bg-ivory transition flex items-center gap-1"><span class="material-symbols-outlined text-sm">description</span> Cliente</a>
      <a href="${BASE_URL}/api/presupuestos/${p.id}/pdf/empleados" target="_blank" class="px-3 py-1.5 bg-ivory-dark rounded-lg text-xs font-medium hover:bg-ivory transition flex items-center gap-1"><span class="material-symbols-outlined text-sm">picture_as_pdf</span> Empleados</a>
    </div>`);
};

window.confirmarEliminarPresupuesto = function(id) {
  showModal(`<h3 class="font-display text-xl mb-4 text-red-600">Eliminar Presupuesto</h3><p class="text-sm mb-4">¿Estás seguro de eliminar este presupuesto? Esta acción no se puede deshacer.</p>
    <div class="flex gap-2"><button onclick="closeModal()" class="flex-1 bg-ivory-dark text-charcoal px-4 py-2 rounded-lg hover:bg-ivory transition font-medium">Cancelar</button>
    <button onclick="eliminarPresupuesto(${id})" class="flex-1 bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600 transition font-medium">Eliminar</button></div>`);
};

window.eliminarPresupuesto = async function(id) {
  await apiDelete(`/presupuestos/${id}`); closeModal(); loadPresupuestos(); toast("Presupuesto eliminado");
};

window.convertirPresupuestoEvento = async function(id) {
  try { await apiPost(`/presupuestos/${id}/convertir-evento/`, {}); toast("Evento creado desde presupuesto"); closeModal(); navigate("eventos"); }
  catch (e) { toast("Error: " + e.message, "error"); }
};

window.openNuevoPresupuestoModal = async function() {
  const [clientes, mobiliario, juegos, kmData] = await Promise.all([apiGet("/clientes/"), apiGet("/mobiliario/"), apiGet("/juegos/").catch(() => []), apiGet("/presupuestos/logistica/precio-por-km")]);
  _nuevoPptoClientes = clientes; _nuevoPptoMobiliario = mobiliario; _nuevoPptoJuegos = (juegos || []);
  _pptoPrecioKm = kmData?.precio_por_km || 7000;
  _nuevoPptoLugares = [{ nombre: "", productos: [{ tipo: "mob", id: null, cantidad: 1, label: "" }] }];
  _nuevoPptoEditingId = null; _renderPptoModal();
};

// ─── AJUSTE AUTOMÁTICO DE PRECIOS 3% MENSUAL ───
// Calcula meses de diferencia entre hoy y la fecha del evento.
// Regla: mes del evento menos mes actual (diciembre=11, julio=6 => 5 meses).
// Si la fecha es futura, suma 3% por cada mes de diferencia.
// Redondeo "lindo": >10000 → múltiplo de 500, >1000 → múltiplo de 100, >100 → múltiplo de 50.
function calcularPrecioAjustado(precioBase, fechaEvento) {
  if (!precioBase || precioBase <= 0) return 0;
  if (!fechaEvento) return _redondearPrecio(precioBase);
  let meses = 0;
  try {
    const fecha = new Date(fechaEvento + "T00:00:00");
    if (isNaN(fecha.getTime())) return _redondearPrecio(precioBase);
    const ahora = new Date();
    meses = (fecha.getFullYear() - ahora.getFullYear()) * 12 + (fecha.getMonth() - ahora.getMonth());
  } catch (e) { meses = 0; }
  if (isNaN(meses) || meses < 0) meses = 0;
  let precio = precioBase * (1 + 0.03 * meses);
  return _redondearPrecio(precio);
}

function _redondearPrecio(precio) {
  let multiplo;
  if (precio > 10000) multiplo = 500;
  else if (precio > 1000) multiplo = 100;
  else if (precio > 100) multiplo = 50;
  else return Math.round(precio);
  return Math.round(precio / multiplo) * multiplo;
}

// Retorna la fecha del evento seleccionada en el modal de presupuesto
function _pptoFechaEvento() {
  const v = document.getElementById("nppto-fecha")?.value;
  return v || "";
}

function _calcularPptoLocal() {
  const dist = parseFloat(document.getElementById("nppto-distancia")?.value) || 0;
  const mobById = {}; _nuevoPptoMobiliario.forEach(m => { mobById[m.id] = m; });
  const juegoById = {}; (_nuevoPptoJuegos || []).forEach(j => { juegoById[j.id] = j; });
  const fecha = _pptoFechaEvento();
  let subtotalMob = 0;
  _nuevoPptoLugares.forEach(lug => {
    lug.productos.forEach(p => {
      if (p.juego_id) {
        const jg = juegoById[p.juego_id];
        if (jg) subtotalMob += (jg.precio_alquiler || 0) * (p.cantidad || 1);
      } else if (p.mobiliario_id) {
        const mob = mobById[p.mobiliario_id];
        if (mob) {
          const precioAjustado = calcularPrecioAjustado(mob.precio_alquiler, fecha);
          subtotalMob += precioAjustado * (p.cantidad || 1);
        }
      }
    });
  });
  let costoLog = 0;
  if (dist > 0) { costoLog = dist * (_pptoPrecioKm || 7000); }
  const costoArmado = parseFloat(document.getElementById("nppto-armado")?.value) || 0;
  return { subtotalMob, costoLog, costoArmado, total: subtotalMob + costoLog + costoArmado };
}

function _actualizarTotalesPpto() {
  const calc = _calcularPptoLocal();
  const el = document.getElementById("nppto-totales");
  if (el) { el.innerHTML = `<div class="flex justify-between text-sm"><span class="text-charcoal/50">Subtotal Mobiliario</span><span>$${calc.subtotalMob.toLocaleString("es-AR")}</span></div><div class="flex justify-between text-sm"><span class="text-charcoal/50">Traslado</span><span>$${calc.costoLog.toLocaleString("es-AR")}</span></div><div class="flex justify-between text-sm"><span class="text-charcoal/50">Armado y desarme</span><span>$${calc.costoArmado.toLocaleString("es-AR")}</span></div><div class="flex justify-between font-display text-lg border-t border-ivory-dark pt-1 mt-1"><span>Total</span><span class="text-navy">$${calc.total.toLocaleString("es-AR")}</span></div>`; }
  const dist = parseFloat(document.getElementById("nppto-distancia")?.value) || 0;
  let logCost = dist > 0 ? dist * (_pptoPrecioKm || 7000) : 0;
  const logLabel = document.getElementById("nppto-logistica-cost");
  if (logLabel) logLabel.textContent = logCost.toLocaleString("es-AR");
  const kmLabel = document.getElementById("nppto-km-rate");
  if (kmLabel) kmLabel.textContent = (_pptoPrecioKm || 7000).toLocaleString("es-AR");
}

function _renderPptoLugaresOnly() {
  const cont = document.getElementById("nppto-lugares");
  if (!cont) return;
  let html = "";
  _nuevoPptoLugares.forEach((lug, li) => {
    html += `<div class="border border-ivory-dark rounded-lg p-3 bg-ivory-dark/20"><div class="flex items-center gap-2 mb-2">
      <input value="${lug.nombre}" placeholder="Nombre del lugar" onchange="_nuevoPptoLugares[${li}].nombre=this.value" class="flex-1 border border-ivory-dark rounded-lg p-2 text-sm focus:border-primary outline-none"/>
      ${_nuevoPptoLugares.length > 1 ? `<button type="button" onclick="_removeLugar(${li})" class="text-red-400 hover:text-red-600 transition"><span class="material-symbols-outlined text-lg">close</span></button>` : ''}</div><div class="space-y-2">`;
    lug.productos.forEach((prod, pi) => {
      const esJuego = !!prod.juego_id;
      const selMob = esJuego ? null : _nuevoPptoMobiliario.find(m => m.id === prod.mobiliario_id);
      const selJuego = esJuego ? (_nuevoPptoJuegos || []).find(j => j.id === prod.juego_id) : null;
      const selLabel = esJuego 
        ? (selJuego ? `${selJuego.nombre} – $${(selJuego.precio_alquiler||0).toLocaleString("es-AR")}` : "Juego")
        : (selMob ? `${selMob.nombre} – $${selMob.precio_alquiler?.toLocaleString("es-AR")}` : "");
      const iconTag = esJuego ? '<span class="material-symbols-outlined text-xs text-charcoal/40 mr-1">inventory_2</span>' : '';
      html += `<div class="flex gap-2 items-center">
        <div class="relative flex-1">
          <input type="text" value="${selLabel}" placeholder="Buscar mobiliario o juego..." autocomplete="off" oninput="_pptoMobSearch(this, ${li}, ${pi})" class="w-full border border-ivory-dark rounded-lg p-2 text-sm focus:border-primary outline-none pl-8" />
          <span class="material-symbols-outlined text-xs text-charcoal/30 absolute left-2 top-1/2 -translate-y-1/2 pointer-events-none">${esJuego ? 'inventory_2' : 'chair'}</span>
          <div class="absolute z-50 left-0 right-0 mt-1 bg-white border border-ivory-dark rounded-lg shadow-lg max-h-48 overflow-y-auto hidden" data-ppto-dropdown="1"></div>
        </div>
        <input type="number" value="${prod.cantidad}" min="1" onchange="_nuevoPptoLugares[${li}].productos[${pi}].cantidad=parseInt(this.value)||1;_actualizarTotalesPpto()" class="w-20 border border-ivory-dark rounded-lg p-2 text-sm focus:border-primary outline-none" placeholder="Cant"/>
        ${lug.productos.length > 1 ? `<button type="button" onclick="_removeLugarProducto(${li},${pi})" class="text-red-400 hover:text-red-600 transition"><span class="material-symbols-outlined text-sm">close</span></button>` : ''}
      </div>`;
    });
    html += `</div><button type="button" onclick="_addLugarProducto(${li})" class="mt-2 text-xs text-primary hover:underline flex items-center gap-1"><span class="material-symbols-outlined text-sm">add</span> Agregar item</button></div>`;
  });
  cont.innerHTML = html; _actualizarTotalesPpto();
}

// Búsqueda en vivo de mobiliario Y juegos dentro del modal de presupuesto
window._pptoMobSearch = function(inputEl, li, pi) {
  const dd = inputEl.parentElement.querySelector('[data-ppto-dropdown]');
  if (!dd) return;
  // limpiar selección previa al escribir
  _nuevoPptoLugares[li].productos[pi].mobiliario_id = null;
  _nuevoPptoLugares[li].productos[pi].juego_id = null;
  const q = inputEl.value.trim().toLowerCase();
  if (!q) { dd.classList.add("hidden"); dd.innerHTML = ""; return; }
  const fecha = _pptoFechaEvento();
  // Buscar mobiliario
  const filtradosMob = _nuevoPptoMobiliario.filter(m => (m.nombre || "").toLowerCase().includes(q)).slice(0, 15);
  // Buscar juegos
  const filtradosJuegos = (_nuevoPptoJuegos || []).filter(j => (j.nombre || "").toLowerCase().includes(q)).slice(0, 5);
  if (filtradosMob.length === 0 && filtradosJuegos.length === 0) {
    dd.classList.remove("hidden");
    dd.innerHTML = `<div class="p-2 text-sm text-charcoal/40">Sin resultados</div>`;
    return;
  }
  dd.classList.remove("hidden");
  let html = "";
  if (filtradosMob.length > 0) {
    html += filtradosMob.map(m => {
      const precioAjs = calcularPrecioAjustado(m.precio_alquiler, fecha);
      const precioTxt = precioAjs !== m.precio_alquiler ? `$${precioAjs.toLocaleString("es-AR")}` : `$${m.precio_alquiler?.toLocaleString("es-AR")}`;
      return `<div class="p-2 text-sm cursor-pointer hover:bg-ivory-dark border-b border-ivory-dark/50 last:border-0" onclick="_pptoMobSelect(${li}, ${pi}, ${m.id})"><span class="material-symbols-outlined text-xs text-charcoal/40 align-middle mr-1">chair</span><span class="font-medium">${m.nombre}</span> <span class="text-charcoal/50">— ${precioTxt}</span></div>`;
    }).join("");
  }
  if (filtradosJuegos.length > 0) {
    html += `<div class="px-2 py-1 text-xs text-charcoal/40 bg-ivory-dark/30 font-medium">JUEGOS / COMBOS</div>`;
    html += filtradosJuegos.map(j => {
      const itemsDesc = (j.items || []).map(it => `${it.cantidad}x ${it.mobiliario_nombre||''}`).join(", ");
      return `<div class="p-2 text-sm cursor-pointer hover:bg-ivory-dark border-b border-ivory-dark/50 last:border-0" onclick="_pptoJuegoSelect(${li}, ${pi}, ${j.id})"><span class="material-symbols-outlined text-xs text-charcoal/40 align-middle mr-1">inventory_2</span><span class="font-medium">${j.nombre}</span> <span class="text-charcoal/50">— $${(j.precio_alquiler||0).toLocaleString("es-AR")}</span> <span class="text-xs text-charcoal/40 block ml-5">${itemsDesc}</span></div>`;
    }).join("");
  }
  dd.innerHTML = html;
};

window._pptoMobSelect = function(li, pi, mobId) {
  _nuevoPptoLugares[li].productos[pi] = { mobiliario_id: mobId, cantidad: _nuevoPptoLugares[li].productos[pi].cantidad || 1 };
  _renderPptoLugaresOnly();
};

window._pptoJuegoSelect = function(li, pi, juegoId) {
  _nuevoPptoLugares[li].productos[pi] = { juego_id: juegoId, cantidad: 1 };
  _renderPptoLugaresOnly();
};

function _renderPptoModal(editData) {
  const mc = document.getElementById("modal-content");
  mc.classList.remove("max-w-lg"); mc.classList.add("max-w-3xl");
  const p = editData || {};
  const clientesOpts = _nuevoPptoClientes.map(c => `<option value="${c.id}" ${p.cliente_id && c.id === p.cliente_id ? 'selected' : ''}>${c.nombre}</option>`).join("");
  const fechaVal = p.fecha_evento ? (() => { try { return p.fecha_evento.slice(0, 10); } catch { return ""; } })() : "";
  const titulo = _nuevoPptoEditingId ? `Editar Presupuesto #${_nuevoPptoEditingId}` : "Nuevo Presupuesto";
  const submitLabel = _nuevoPptoEditingId ? "Guardar Cambios" : "Guardar Presupuesto";
  const submitAction = _nuevoPptoEditingId ? `guardarEditarPresupuesto(event, ${_nuevoPptoEditingId})` : `guardarNuevoPresupuesto(event)`;
  let lugaresHtml = "";
  showModal(`<h3 class="font-display text-xl mb-4">${titulo}</h3><form onsubmit="${submitAction}"><div class="space-y-3">
    <div><label class="block text-sm mb-1 font-medium">Nombre del presupuesto</label><input id="nppto-nombre" value="${p.nombre || ''}" placeholder="Ej: Test Bug Fix,Editar Presupuesto #1..." class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <div><label class="block text-sm mb-1 font-medium">Cliente existente</label><select id="nppto-cliente-id" onchange="document.getElementById('nppto-cliente-nombre').value=''" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"><option value="">— Nuevo cliente —</option>${clientesOpts}</select></div>
      <div><label class="block text-sm mb-1 font-medium">Nombre del cliente (nuevo)</label><input id="nppto-cliente-nombre" value="${p.cliente_nombre || ''}" placeholder="Nombre si es cliente nuevo" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" onchange="document.getElementById('nppto-cliente-id').value=''"/></div>
    </div>
    <div class="grid grid-cols-2 sm:grid-cols-5 gap-3">
      <div><label class="block text-sm mb-1 font-medium">Fecha Evento</label><input id="nppto-fecha" type="date" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${fechaVal}" onchange="_actualizarTotalesPpto()"/></div>
      <div><label class="block text-sm mb-1 font-medium">Tipo Evento</label><input id="nppto-tipo" value="${p.tipo_evento || ''}" placeholder="Boda, Cumple..." class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
      <div><label class="block text-sm mb-1 font-medium">Invitados</label><input id="nppto-invitados" type="number" min="0" value="${p.cantidad_invitados || ''}" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
      <div><label class="block text-sm mb-1 font-medium">Localidad</label><input id="nppto-localidad" value="${p.localidad || ''}" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
      <div><label class="block text-sm mb-1 font-medium">Distancia (km)</label><input id="nppto-distancia" type="number" min="0" step="0.1" value="${p.distancia_km || 0}" oninput="_actualizarTotalesPpto()" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
      <div><label class="block text-sm mb-1 font-medium">Precio $/km</label><input id="nppto-precio-km" type="number" min="0" step="100" value="${_pptoPrecioKm || 7000}" placeholder="7000" oninput="_pptoPrecioKm=parseFloat(this.value)||7000;_actualizarTotalesPpto()" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
    </div>
    <div class="text-xs text-charcoal/40">Traslado: $<span id="nppto-logistica-cost">0</span> (a $<span id="nppto-km-rate">7.000</span>/km)</div>
    <div class="mt-2"><label class="block text-sm mb-1 font-medium">Armado y desarme ($)</label><input id="nppto-armado" type="number" min="0" step="1000" value="${p.costo_armado || 0}" oninput="_actualizarTotalesPpto()" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" placeholder="0"/></div>
    <div><h4 class="font-medium text-sm mb-2 text-charcoal/70">Lugares y Mobiliario</h4><div id="nppto-lugares" class="space-y-3">${lugaresHtml}</div>
    <button type="button" onclick="_addLugar()" class="mt-2 text-sm text-primary hover:underline flex items-center gap-1"><span class="material-symbols-outlined text-sm">add</span> Agregar lugar</button></div>
    <div id="nppto-totales" class="mt-4 border-t border-ivory-dark pt-3 text-sm space-y-1"></div>
    ${_nuevoPptoEditingId ? `<div class="mt-2"><label class="block text-sm mb-1 font-medium">Estado</label><select id="nppto-estado" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"><option value="borrador" ${p.estado==='borrador'?'selected':''}>Borrador</option><option value="enviado" ${p.estado==='enviado'?'selected':''}>Enviado</option><option value="confirmado" ${p.estado==='confirmado'?'selected':''}>Confirmado</option><option value="cancelado" ${p.estado==='cancelado'?'selected':''}>Cancelado</option></select></div>` : ''}
    <button type="submit" class="w-full bg-primary text-on-primary px-4 py-2 rounded-lg hover:opacity-90 transition font-medium flex items-center justify-center gap-1"><span class="material-symbols-outlined text-base">save</span> ${submitLabel}</button>
  </div></form>`);
  _renderPptoLugaresOnly();
}

window._addLugar = function() { _nuevoPptoLugares.push({ nombre: "", productos: [{ mobiliario_id: null, cantidad: 1 }] }); _renderPptoLugaresOnly(); };
window._removeLugar = function(li) { _nuevoPptoLugares.splice(li, 1); _renderPptoLugaresOnly(); };
window._addLugarProducto = function(li) { _nuevoPptoLugares[li].productos.push({ mobiliario_id: null, cantidad: 1 }); _renderPptoLugaresOnly(); };
window._removeLugarProducto = function(li, pi) { _nuevoPptoLugares[li].productos.splice(pi, 1); _renderPptoLugaresOnly(); };
window._actualizarTotalesPpto = _actualizarTotalesPpto;

window.guardarNuevoPresupuesto = async function(ev) {
  ev.preventDefault();
  const clienteId = parseInt(document.getElementById("nppto-cliente-id")?.value) || null;
  const clienteNombre = document.getElementById("nppto-cliente-nombre")?.value || "";
  if (!clienteId && !clienteNombre) { toast("Indica un cliente existente o escribe el nombre", "error"); return; }
  const hasProducts = _nuevoPptoLugares.some(l => l.productos.some(p => p.mobiliario_id || p.juego_id));
  if (!hasProducts) { toast("Agrega al menos un item de mobiliario", "error"); return; }
  const esClienteNuevo = !clienteId && !!clienteNombre;
  const lugares = _nuevoPptoLugares.map(lug => ({
    nombre: lug.nombre || "Lugar",
    productos: lug.productos.filter(p => p.mobiliario_id || p.juego_id).map(p => {
      if (p.juego_id) {
        const jg = (_nuevoPptoJuegos || []).find(j => j.id === p.juego_id);
        return { juego_id: p.juego_id, catalogo_key: jg ? jg.nombre : "Juego", cantidad: p.cantidad };
      }
      return { mobiliario_id: p.mobiliario_id, catalogo_key: (_nuevoPptoMobiliario.find(m => m.id === p.mobiliario_id)?.nombre || ""), cantidad: p.cantidad };
    })
  }));
  const calc = _calcularPptoLocal();
  const saveData = {
    nombre: document.getElementById("nppto-nombre")?.value || "",
    cliente_id: clienteId,
    cliente_nombre: clienteNombre || (_nuevoPptoClientes.find(c => c.id === clienteId)?.nombre || ""),
    fecha_evento: document.getElementById("nppto-fecha")?.value || _hoyLocal(),
    tipo_evento: document.getElementById("nppto-tipo")?.value || "",
    cantidad_invitados: parseInt(document.getElementById("nppto-invitados")?.value) || null,
    localidad: document.getElementById("nppto-localidad")?.value || "",
    distancia_km: parseFloat(document.getElementById("nppto-distancia")?.value) || null,
    lugares,
    subtotal_mobiliario: calc.subtotalMob,
    costo_logistica: calc.costoLog,
    costo_armado: calc.costoArmado,
    total: calc.total,
    whatsapp_text: "",
    estado: "borrador"
  };
  try {
    const resp = await apiPost("/presupuestos/", saveData);
    closeModal(); loadPresupuestos();
    let msg = "Presupuesto guardado";
    if (esClienteNuevo && resp && resp.cliente_id) {
      msg = `Presupuesto guardado. Cliente nuevo creado #${resp.cliente_id}: ${clienteNombre}`;
    }
    toast(msg);
  }
  catch (e) { toast("Error: " + e.message, "error"); }
};

window.editarPresupuestoModal = async function(id) {
  const p = await apiGet(`/presupuestos/${id}`);
  const [clientes, mobiliario, juegos, kmData] = await Promise.all([apiGet("/clientes/"), apiGet("/mobiliario/"), apiGet("/juegos/").catch(() => []), apiGet("/presupuestos/logistica/precio-por-km")]);
  _nuevoPptoClientes = clientes; _nuevoPptoMobiliario = mobiliario; _nuevoPptoJuegos = (juegos || []); _nuevoPptoEditingId = id;
  // Calcular el precio/km que tenía este presupuesto al guardarse,
  // en vez de pisarlo con la configuración global (que pudo cambiar).
  const precioKmGuardado = (p.distancia_km && p.costo_logistica)
    ? p.costo_logistica / p.distancia_km
    : null;
  _pptoPrecioKm = precioKmGuardado || kmData?.precio_por_km || 7000;
  if (p.lugares && p.lugares.length > 0) {
    _nuevoPptoLugares = p.lugares.map(lug => ({
      nombre: lug.nombre || "",
      productos: (lug.productos || lug.items || []).map(it => {
        if (it.juego_id) {
          const jg = _nuevoPptoJuegos.find(j => j.id === it.juego_id);
          return { juego_id: it.juego_id, cantidad: it.cantidad || 1 };
        }
        if (it.mobiliario_id || it.id) {
          const mid = it.mobiliario_id || it.id;
          return { mobiliario_id: mid, cantidad: it.cantidad || 1 };
        }
        return { mobiliario_id: null, cantidad: it.cantidad || 1 };
      })
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
    productos: lug.productos.filter(p => p.mobiliario_id || p.juego_id).map(p => {
      if (p.juego_id) {
        const jg = (_nuevoPptoJuegos || []).find(j => j.id === p.juego_id);
        return { juego_id: p.juego_id, catalogo_key: jg ? jg.nombre : "Juego", cantidad: p.cantidad };
      }
      return { mobiliario_id: p.mobiliario_id, catalogo_key: (_nuevoPptoMobiliario.find(m => m.id === p.mobiliario_id)?.nombre || ""), cantidad: p.cantidad };
    })
  }));
  const calc = _calcularPptoLocal();
  const saveData = {
    nombre: document.getElementById("nppto-nombre")?.value || "",
    cliente_id: clienteId,
    cliente_nombre: clienteNombre || (_nuevoPptoClientes.find(c => c.id === clienteId)?.nombre || ""),
    fecha_evento: document.getElementById("nppto-fecha")?.value || _hoyLocal(),
    tipo_evento: document.getElementById("nppto-tipo")?.value || "",
    cantidad_invitados: parseInt(document.getElementById("nppto-invitados")?.value) || null,
    localidad: document.getElementById("nppto-localidad")?.value || "",
    distancia_km: parseFloat(document.getElementById("nppto-distancia")?.value) || null,
    lugares,
    subtotal_mobiliario: calc.subtotalMob,
    costo_logistica: calc.costoLog,
    costo_armado: calc.costoArmado,
    total: calc.total,
    whatsapp_text: "",
    estado: document.getElementById("nppto-estado")?.value || "borrador"
  };
  try { await apiPut(`/presupuestos/${id}`, saveData); closeModal(); loadPresupuestos(); toast("Presupuesto actualizado"); }
  catch (e) { toast("Error: " + e.message, "error"); }
};
