// ─── FINANZAS ───
function _initFinanzasSelectors() {
  const now = new Date();
  if (!finanzasAnio) finanzasAnio = now.getFullYear();
  if (!finanzasMes) finanzasMes = now.getMonth() + 1;
  const anioSel = document.getElementById("finanzas-anio");
  const mesSel = document.getElementById("finanzas-mes");
  if (!anioSel || !mesSel) return;
  const curYear = now.getFullYear();
  anioSel.innerHTML = "";
  for (let y = curYear - 5; y <= curYear + 1; y++) { anioSel.innerHTML += `<option value="${y}" ${y === finanzasAnio ? 'selected' : ''}>${y}</option>`; }
  mesSel.innerHTML = "";
  MONTHS_ES.forEach((m, i) => { const val = i + 1; mesSel.innerHTML += `<option value="${val}" ${val === finanzasMes ? 'selected' : ''}>${m}</option>`; });
  finanzasAnio = parseInt(anioSel.value); finanzasMes = parseInt(mesSel.value);
}

function _updateTipoFilterButtons() {
  document.querySelectorAll("#finanzas-tipo-filtros button").forEach(btn => {
    const t = btn.getAttribute("data-tipo");
    if (t === finanzasTipoFilter) btn.className = "px-3 py-1 rounded-full text-xs font-medium transition bg-navy text-ivory";
    else btn.className = "px-3 py-1 rounded-full text-xs font-medium transition bg-ivory-dark text-charcoal/60 hover:bg-ivory-dark";
  });
}

function filterFinanzasTipo(tipo) { finanzasTipoFilter = tipo; _updateTipoFilterButtons(); _renderFinanzasList(); }
window.filterFinanzasTipo = filterFinanzasTipo;

async function loadFinanzas() {
  _initFinanzasSelectors(); _updateTipoFilterButtons();
  const anioSel = document.getElementById("finanzas-anio");
  const mesSel = document.getElementById("finanzas-mes");
  finanzasAnio = parseInt(anioSel.value); finanzasMes = parseInt(mesSel.value);
  const [resumen, registros, eventos] = await Promise.all([apiGet(`/finanzas/resumen/mensual?anio=${finanzasAnio}&mes=${finanzasMes}`), apiGet("/finanzas/"), apiGet("/eventos/")]);
  _finanzasEventos = {}; eventos.forEach(e => { _finanzasEventos[e.id] = e.titulo; });
  _finanzasRegistros = registros.filter(r => { const d = new Date(r.fecha); return d.getFullYear() === finanzasAnio && (d.getMonth() + 1) === finanzasMes; });
  document.getElementById("finanzas-summary").innerHTML = `
    <div class="bg-white rounded-lg shadow-sm p-5 border border-ivory-dark text-center"><p class="text-xs uppercase tracking-wider text-charcoal/40 mb-1">Ingresos</p><p class="text-2xl font-display text-navy">$${resumen.ingresos?.toLocaleString("es-AR") || 0}</p></div>
    <div class="bg-white rounded-lg shadow-sm p-5 border border-ivory-dark text-center"><p class="text-xs uppercase tracking-wider text-charcoal/40 mb-1">Egresos</p><p class="text-2xl font-display text-red-500">$${resumen.egresos?.toLocaleString("es-AR") || 0}</p></div>
    <div class="bg-white rounded-lg shadow-sm p-5 border border-ivory-dark text-center"><p class="text-xs uppercase tracking-wider text-charcoal/40 mb-1">Balance</p><p class="text-2xl font-display ${resumen.balance >= 0 ? 'text-green-600' : 'text-red-500'}">$${resumen.balance?.toLocaleString("es-AR") || 0}</p></div>`;
  _renderFinanzasList();
}

function _renderFinanzasList() {
  const filtered = finanzasTipoFilter === "todos" ? _finanzasRegistros : _finanzasRegistros.filter(r => r.tipo === finanzasTipoFilter);
  const cont = document.getElementById("finanzas-list");
  if (filtered.length === 0) { cont.innerHTML = `<div class="text-center py-8 text-charcoal/40"><span class="material-symbols-outlined text-4xl mb-2 block">receipt_long</span><p>No hay registros para ${MONTHS_ES[finanzasMes - 1]} ${finanzasAnio}</p></div>`; return; }
  cont.innerHTML = filtered.sort((a, b) => new Date(b.fecha) - new Date(a.fecha)).map(r => {
    const fechaStr = new Date(r.fecha).toLocaleDateString("es-AR", { day:"2-digit", month:"short" });
    const icon = r.tipo === "ingreso" ? "trending_up" : "trending_down";
    const tipoBadge = r.tipo === "ingreso" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700";
    const tipoLabel = r.tipo === "ingreso" ? "+" : "-";
    const eventoName = r.evento_id ? (_finanzasEventos[r.evento_id] || `Evento #${r.evento_id}`) : "";
    const conceptoEsc = r.concepto.replace(/'/g, "\\'");
    return `<div class="flex items-center justify-between py-2.5 px-1 border-b border-ivory-dark/60 last:border-0 hover:bg-ivory-dark/30 rounded transition">
      <div class="flex items-center gap-3 min-w-0 flex-1">
        <span class="material-symbols-outlined text-lg ${r.tipo === 'ingreso' ? 'text-green-600' : 'text-red-500'}">${icon}</span>
        <div class="min-w-0"><p class="font-medium truncate">${r.concepto}</p>
        <div class="flex items-center gap-2 text-xs text-charcoal/40"><span>${fechaStr}</span>${eventoName ? `<span class="flex items-center gap-0.5"><span class="material-symbols-outlined text-[12px]">link</span>${eventoName}</span>` : ''}${r.notas ? `<span class="italic truncate max-w-[120px]" title="${r.notas}">${r.notas}</span>` : ''}</div></div>
      </div>
      <div class="flex items-center gap-2 flex-shrink-0 ml-3">
        <span class="text-xs px-2 py-0.5 rounded ${tipoBadge}">${r.tipo}</span>
        <span class="font-display font-semibold ${r.tipo === 'ingreso' ? 'text-green-600' : 'text-red-500'}">${tipoLabel}$${r.monto?.toLocaleString("es-AR")}</span>
        <button onclick="confirmarEliminarFinanza(${r.id},'${conceptoEsc}')" class="p-1 hover:bg-red-50 rounded-lg transition" title="Eliminar"><span class="material-symbols-outlined text-base text-charcoal/40 hover:text-red-500">delete</span></button>
      </div>
    </div>`;
  }).join("");
}

window.openFinanzaModal = async function() {
  const presupuestos = await apiGet("/presupuestos/");
  _finanzasPresupuestos = presupuestos || [];
  const pptoOpts = _finanzasPresupuestos.map(p => `<option value="${p.id}">#${p.id} ${p.cliente_nombre || ''} – ${p.tipo_evento || ''} – $${(p.total||0).toLocaleString('es-AR')} (${p.estado})</option>`).join("");
  showModal(`<h3 class="font-display text-xl mb-4">Nuevo Registro</h3><form onsubmit="crearFinanza(event)"><div class="space-y-3">
    <div><label class="block text-sm mb-1 font-medium">Tipo</label><div class="flex gap-2">
      <label class="flex-1 cursor-pointer"><input type="radio" name="tipo" value="ingreso" checked class="hidden peer" onchange="_togglePresupuestoDropdown()"/><div class="peer-checked:bg-green-100 peer-checked:border-green-500 peer-checked:text-green-700 border border-ivory-dark rounded-lg p-2 text-center text-sm font-medium transition hover:bg-ivory-dark"><span class="material-symbols-outlined text-lg align-middle mr-1">trending_up</span>Ingreso</div></label>
      <label class="flex-1 cursor-pointer"><input type="radio" name="tipo" value="egreso" class="hidden peer" onchange="_togglePresupuestoDropdown()"/><div class="peer-checked:bg-red-100 peer-checked:border-red-500 peer-checked:text-red-700 border border-ivory-dark rounded-lg p-2 text-center text-sm font-medium transition hover:bg-ivory-dark"><span class="material-symbols-outlined text-lg align-middle mr-1">trending_down</span>Egreso</div></label>
    </div></div>
    <div id="finanza-ppto-row" class="grid grid-cols-2 gap-3">
      <div><label class="block text-sm mb-1 font-medium">Vincular Presupuesto</label><select id="finanza-ppto-id" onchange="_onPresupuestoSelect()" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"><option value="">— Sin presupuesto —</option>${pptoOpts}</select></div>
      <div><label class="block text-sm mb-1 font-medium">Monto del presupuesto</label><div id="finanza-ppto-monto" class="border border-ivory-dark rounded-lg p-2 bg-ivory-dark/30 text-sm text-charcoal/50">—</div></div>
    </div>
    <div><label class="block text-sm mb-1 font-medium">Concepto</label><input name="concepto" id="finanza-concepto" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" placeholder="Ej: Seña Boda García"/></div>
    <div class="grid grid-cols-2 gap-3">
      <div><label class="block text-sm mb-1 font-medium">Monto ($)</label><input name="monto" id="finanza-monto" type="number" step="0.01" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" placeholder="0.00"/></div>
      <div><label class="block text-sm mb-1 font-medium">Fecha</label><input name="fecha" type="date" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${new Date().toISOString().slice(0,10)}"/></div>
    </div>
    <div><label class="block text-sm mb-1 font-medium">Notas</label><textarea name="notas" rows="2" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" placeholder="Opcional..."></textarea></div>
    </div><button type="submit" class="mt-4 bg-primary text-on-primary px-4 py-2 rounded-lg hover:opacity-90 transition w-full font-medium">Guardar Registro</button></form>`);
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
  if (ppto) { montoEl.textContent = `$${(ppto.total||0).toLocaleString("es-AR")}`; conceptoEl.value = `Presupuesto #${ppto.id} – ${ppto.cliente_nombre || ''} ${ppto.tipo_evento || ''}`; montoInput.value = ppto.total || ""; }
  else { montoEl.textContent = "—"; }
};

window.crearFinanza = async function(ev) {
  ev.preventDefault();
  const fd = new FormData(ev.target);
  const tipo = fd.get("tipo"); const concepto = fd.get("concepto"); const monto = parseFloat(fd.get("monto")); const fecha = fd.get("fecha"); const notas = fd.get("notas") || "";
  const presupuestoId = parseInt(document.getElementById("finanza-ppto-id")?.value) || null;
  if (!tipo || !concepto || isNaN(monto) || monto <= 0) { toast("Completa todos los campos correctamente", "error"); return; }
  await apiPost("/finanzas/", { tipo, concepto, monto, fecha: fecha ? new Date(fecha + "T12:00:00").toISOString() : new Date().toISOString(), notas, evento_id: null, presupuesto_id: presupuestoId });
  closeModal(); loadFinanzas(); toast("Registro creado");
};

window.confirmarEliminarFinanza = function(id, concepto) {
  showModal(`<h3 class="font-display text-xl mb-4 text-red-600">Eliminar Registro</h3><p class="text-sm mb-4">¿Estás seguro de eliminar <strong>${concepto}</strong>? Esta acción no se puede deshacer.</p>
    <div class="flex gap-2"><button onclick="closeModal()" class="flex-1 bg-ivory-dark text-charcoal px-4 py-2 rounded-lg hover:bg-ivory transition font-medium">Cancelar</button>
    <button onclick="eliminarFinanza(${id})" class="flex-1 bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600 transition font-medium">Eliminar</button></div>`);
};

window.eliminarFinanza = async function(id) {
  try { await apiDelete(`/finanzas/${id}`); closeModal(); loadFinanzas(); toast("Registro eliminado"); }
  catch (e) { toast("Error: " + e.message, "error"); }
};
