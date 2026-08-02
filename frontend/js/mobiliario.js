// ─── MOBILIARIO ───
let _mobItemsCache = [];  // cache de items para no llamar a la API en cada búsqueda

async function loadMobiliario() {
  const items = await apiGet("/mobiliario/");
  _mobItemsCache = items;
  // Consultar disponibilidad si hay fecha seleccionada
  _mobDisponibilidadMap = {};
  if (mobFechaDisponibilidad) {
    try {
      const resp = await apiGet(`/mobiliario/disponibilidad/${mobFechaDisponibilidad}`);
      // Respuesta del backend: {fecha, disponible: [{id, nombre, disponible, ...}], ...}
      const dispArr = (resp && resp.disponible) ? resp.disponible : (Array.isArray(resp) ? resp : []);
      dispArr.forEach(d => {
        const mid = d.mobiliario_id != null ? d.mobiliario_id : d.id;
        if (mid != null) _mobDisponibilidadMap[mid] = d.disponible != null ? d.disponible : d.stock_disponible;
      });
    } catch (e) {
      console.error("Error disponibilidad mobiliario:", e);
    }
  }
  const cats = [...new Set(items.map(i => i.categoria))].sort();
  const filterDiv = document.getElementById("mobiliario-filtros");
  filterDiv.innerHTML = `<button onclick="setMobFilter('')" class="px-3 py-1 rounded-full text-xs ${mobFilter==='' ? 'bg-navy text-ivory' : 'bg-ivory-dark text-charcoal/60 hover:bg-ivory-dark'} transition">Todos</button>` +
    cats.map(c => `<button onclick="setMobFilter('${c}')" class="px-3 py-1 rounded-full text-xs ${mobFilter===c ? 'bg-navy text-ivory' : 'bg-ivory-dark text-charcoal/60 hover:bg-ivory-dark'} transition">${c}</button>`).join("");

  // Sincronizar valor del input de fecha con el estado (por si se navega entre páginas)
  const fechaInput = document.getElementById("mobiliario-fecha");
  if (fechaInput && fechaInput.value !== mobFechaDisponibilidad) {
    fechaInput.value = mobFechaDisponibilidad;
  }

  _renderMobiliarioGrid();
}

window.setMobFilter = function(f) { mobFilter = f; _renderMobiliarioGrid(); };

window.setMobSearchQuery = function(q) {
  mobSearchQuery = q || "";
  // Usar cache: filtrar en cliente sin llamar a la API
  clearTimeout(window._mobSearchTimer);
  window._mobSearchTimer = setTimeout(() => _renderMobiliarioGrid(), 150);
};

// Re-renderiza solo el grid usando el cache (sin llamar a la API)
function _renderMobiliarioGrid() {
  if (!_mobItemsCache || _mobItemsCache.length === 0) return;
  const items = _mobItemsCache;
  const filtered = mobFilter ? items.filter(i => i.categoria === mobFilter) : items;
  const searched = mobSearchQuery
    ? filtered.filter(i => (i.nombre || "").toLowerCase().includes(mobSearchQuery.toLowerCase()) || (i.categoria || "").toLowerCase().includes(mobSearchQuery.toLowerCase()))
    : filtered;
  // Ordenar alfabéticamente
  const sorted = [...searched].sort((a, b) => (a.nombre || "").toLowerCase().localeCompare((b.nombre || "").toLowerCase()));
  const grid = document.getElementById("mobiliario-grid");
  if (!grid) return;
  grid.innerHTML = sorted.map((m, idx) => {
    const fotoUrl = m.foto_path ? `/uploads/mobiliario/${m.foto_path}` : "";
    const stockDisp = mobFechaDisponibilidad
      ? (typeof _mobDisponibilidadMap[m.id] === "number" ? _mobDisponibilidadMap[m.id] : m.stock_disponible)
      : m.stock_disponible;
    const stockClass = stockDisp <= 0 ? 'text-red-600 font-bold' : stockDisp <= 1 ? 'text-red-500' : 'text-green-600';
    const stockLabel = mobFechaDisponibilidad
      ? `Disp: ${stockDisp}/${m.stock_total}`
      : `Stock: ${m.stock_disponible}/${m.stock_total}`;
    return `<div class="card-mob bg-white rounded-lg shadow-sm border border-ivory-dark overflow-hidden hover:shadow-md transition-shadow group" draggable="true" data-mob-id="${m.id}" data-mob-idx="${idx}" ondragstart="_mobDragStart(event, ${m.id})" ondragover="_mobDragOver(event)" ondrop="_mobDrop(event, ${m.id})">
      <div class="h-32 bg-ivory-dark flex items-center justify-center overflow-hidden relative cursor-pointer" onclick="editMobiliario(${m.id})">
        ${fotoUrl ? `<img src="${fotoUrl}" class="w-full h-full object-cover"/>` : '<span class="material-symbols-outlined text-4xl text-charcoal/20">chair</span>'}
        <div class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
          <button onclick="event.stopPropagation();editMobiliario(${m.id})" class="bg-white/90 backdrop-blur-sm p-1 rounded shadow-sm hover:bg-primary hover:text-on-primary transition" title="Editar"><span class="material-symbols-outlined text-sm">edit</span></button>
          <button onclick="event.stopPropagation();confirmarEliminarMobiliario(${m.id},'${m.nombre.replace(/'/g,"\\'")}')" class="bg-white/90 backdrop-blur-sm p-1 rounded shadow-sm hover:bg-red-500 hover:text-white transition" title="Eliminar"><span class="material-symbols-outlined text-sm">delete</span></button>
        </div>
      </div>
      <div class="p-3 cursor-pointer flex items-start gap-2" onclick="editMobiliario(${m.id})">
        <span class="material-symbols-outlined text-xs text-charcoal/30 mt-0.5 cursor-grab active:cursor-grabbing flex-shrink-0" title="Arrastrar para reordenar">drag_indicator</span>
        <div class="flex-1 min-w-0">
          <p class="font-medium text-sm truncate">${m.nombre}</p>
          <p class="text-xs text-charcoal/50">${m.categoria}</p>
          ${m.descripcion ? `<p class="text-xs text-charcoal/40 mt-1 line-clamp-2">${m.descripcion}</p>` : ''}
          <div class="flex justify-between mt-2 items-center">
            <span class="text-sm font-display text-navy">$${m.precio_alquiler?.toLocaleString("es-AR")}</span>
            <span class="text-xs ${stockClass}">${stockLabel}</span>
          </div>
        </div>
      </div>
    </div>`;
  }).join("");
}

// ─── DRAG & DROP para reordenar mobiliario ───
let _mobDragId = null;

window._mobDragStart = function(ev, mobId) {
  _mobDragId = mobId;
  ev.dataTransfer.effectAllowed = "move";
  ev.dataTransfer.setData("text/plain", String(mobId));
  // Añadir clase visual
  ev.target.closest('.card-mob')?.classList.add('opacity-50');
};

window._mobDragOver = function(ev) {
  ev.preventDefault();
  ev.dataTransfer.dropEffect = "move";
};

window._mobDrop = async function(ev, targetMobId) {
  ev.preventDefault();
  if (_mobDragId == null || _mobDragId === targetMobId) { _mobDragId = null; _renderMobiliarioGrid(); return; }

  // Reordenar en el cache local
  const srcIdx = _mobItemsCache.findIndex(m => m.id === _mobDragId);
  const dstIdx = _mobItemsCache.findIndex(m => m.id === targetMobId);
  if (srcIdx === -1 || dstIdx === -1) { _mobDragId = null; return; }

  const [moved] = _mobItemsCache.splice(srcIdx, 1);
  _mobItemsCache.splice(dstIdx, 0, moved);
  _mobDragId = null;

  // Enviar el nuevo orden al backend
  try {
    const orden = _mobItemsCache.map(m => m.id);
    await apiPut("/mobiliario/reordenar/", { orden });
  } catch (e) {
    console.error("Error al reordenar mobiliario:", e);
    // Recargar desde el backend para restaurar orden correcto
    const items = await apiGet("/mobiliario/");
    _mobItemsCache = items;
  }
  _renderMobiliarioGrid();
  toast("Mobiliario reordenado");
};

window.setMobFechaDisponibilidad = function(fecha) {
  mobFechaDisponibilidad = fecha || "";
  loadMobiliario();
};

window.openMobiliarioModal = function(editItem) {
  const isEdit = !!editItem;
  showModal(`<h3 class="font-display text-xl mb-4">${isEdit ? 'Editar' : 'Agregar'} Mobiliario</h3>
    <form id="mob-form" onsubmit="crearMobiliario(event, ${isEdit ? editItem.id : 'null'})">
      <div class="space-y-3">
        <div><label class="block text-sm mb-1 font-medium">Nombre</label><input name="nombre" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${isEdit ? editItem.nombre : ''}"/></div>
        <div><label class="block text-sm mb-1 font-medium">Categoria</label><input name="categoria" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" placeholder="silla, sillon, mesa..." value="${isEdit ? editItem.categoria : ''}"/></div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="block text-sm mb-1 font-medium">Precio Alquiler</label><input name="precio_alquiler" type="number" step="0.01" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${isEdit ? editItem.precio_alquiler : ''}"/></div>
          <div><label class="block text-sm mb-1 font-medium">Stock Total</label><input name="stock_total" type="number" required value="${isEdit ? editItem.stock_total : '1'}" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
        </div>
        <div><label class="block text-sm mb-1 font-medium">Foto</label><input name="foto" type="file" accept="image/*" class="w-full border border-ivory-dark rounded-lg p-2 text-sm"/>${isEdit && editItem.foto_path ? `<p class="text-xs text-charcoal/40 mt-1">Foto actual: ${editItem.foto_path}</p>` : ''}</div>
        <div><label class="block text-sm mb-1 font-medium">Descripcion</label><textarea name="descripcion" rows="2" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none">${isEdit ? (editItem.descripcion || '') : ''}</textarea></div>
      </div>
      <button type="submit" class="mt-4 bg-primary text-on-primary px-4 py-2 rounded-lg hover:opacity-90 transition w-full font-medium">${isEdit ? 'Actualizar' : 'Guardar'}</button>
    </form>`);
};

window.crearMobiliario = async function(ev, editId) {
  ev.preventDefault();
  const form = document.getElementById("mob-form");
  const fd = new FormData(form);
  fd.delete("descripcion");
  fd.append("descripcion", form.querySelector('[name="descripcion"]').value || "");
  try {
    if (editId) { await apiUploadPut(`/mobiliario/${editId}`, fd); }
    else { await apiUpload("/mobiliario/", fd); }
    closeModal(); loadMobiliario(); toast(editId ? "Mobiliario actualizado" : "Mobiliario creado");
  } catch (e) { alert("Error: " + e.message); }
};

window.editMobiliario = async function(id) {
  const items = await apiGet("/mobiliario/");
  const item = items.find(m => m.id === id);
  if (item) openMobiliarioModal(item);
};

window.confirmarEliminarMobiliario = function(id, nombre) {
  showModal(`<h3 class="font-display text-xl mb-4 text-red-600">Eliminar Mobiliario</h3>
    <p class="text-sm mb-4">¿Estas seguro de eliminar <strong>${nombre}</strong>? Se desactivara del catalogo.</p>
    <div class="flex gap-2">
      <button onclick="closeModal()" class="flex-1 bg-ivory-dark text-charcoal px-4 py-2 rounded-lg hover:bg-ivory transition font-medium">Cancelar</button>
      <button onclick="eliminarMobiliario(${id})" class="flex-1 bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600 transition font-medium">Eliminar</button>
    </div>`);
};

window.eliminarMobiliario = async function(id) {
  await apiDelete(`/mobiliario/${id}`); closeModal(); loadMobiliario(); toast("Mobiliario eliminado");
};
