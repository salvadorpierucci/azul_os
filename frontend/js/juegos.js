// ─── JUEGOS / COMBOS (integrado en Mobiliario) ───
let _juegosCache = [];

async function loadJuegos() {
  try {
    const juegos = await apiGet("/juegos/");
    _juegosCache = juegos || [];
    _renderJuegosGrid();
  } catch (e) {
    console.error("Error cargando juegos:", e);
    _juegosCache = [];
    _renderJuegosGrid();
  }
}

function _renderJuegosGrid() {
  const grid = document.getElementById("juegos-grid");
  if (!grid) return;
  if (_juegosCache.length === 0) {
    grid.innerHTML = `<div class="text-charcoal/40 text-sm col-span-full text-center py-4">No hay juegos creados. Usá "Agregar → Juego / Combo" para crear uno.</div>`;
    return;
  }
  grid.innerHTML = _juegosCache.map(j => {
    const itemsHtml = (j.items || []).map(it => 
      `<span class="text-xs bg-ivory-dark/50 rounded px-1.5 py-0.5">${it.cantidad}x ${it.mobiliario_nombre || '?'}</span>`
    ).join(" ");
    const total = j.precio_alquiler || 0;
    return `<div class="card-juego bg-white rounded-lg shadow-sm border border-ivory-dark overflow-hidden hover:shadow-md transition-shadow group">
      <div class="p-4 cursor-pointer" onclick="editJuego(${j.id})">
        <div class="flex items-start justify-between mb-2">
          <p class="font-medium text-sm truncate flex-1">${j.nombre}</p>
          <div class="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1 flex-shrink-0 ml-2">
            <button onclick="event.stopPropagation();editJuego(${j.id})" class="text-charcoal/40 hover:text-primary transition" title="Editar"><span class="material-symbols-outlined text-sm">edit</span></button>
            <button onclick="event.stopPropagation();confirmarEliminarJuego(${j.id},'${(j.nombre||'').replace(/'/g,"\\'")}')" class="text-charcoal/40 hover:text-red-500 transition" title="Eliminar"><span class="material-symbols-outlined text-sm">delete</span></button>
          </div>
        </div>
        <div class="flex flex-wrap gap-1 mb-2">${itemsHtml}</div>
        <div class="flex justify-between items-center mt-2 pt-2 border-t border-ivory-dark/50">
          <span class="text-xs text-charcoal/50">${(j.items||[]).length} items</span>
          <span class="font-display text-navy">$${total.toLocaleString("es-AR")}</span>
        </div>
      </div>
    </div>`;
  }).join("");
}

// ─── Modal crear/editar juego ───
let _juegoModalItems = [];  // [{ mobiliario_id, cantidad }]
let _juegoModalEditingId = null;
let _juegoModalMobiliario = [];
let _juegoPrecioSugerido = 0;

window.openJuegoModal = async function(editId) {
  _juegoModalEditingId = editId || null;
  _juegoModalItems = [];
  
  // Cargar lista de mobiliario para el dropdown
  _juegoModalMobiliario = await apiGet("/mobiliario/");
  
  let editData = null;
  if (editId) {
    editData = _juegosCache.find(j => j.id === editId);
    if (editData && editData.items) {
      _juegoModalItems = editData.items.map(it => ({ mobiliario_id: it.mobiliario_id, cantidad: it.cantidad }));
    }
  }
  
  if (_juegoModalItems.length === 0) {
    _juegoModalItems.push({ mobiliario_id: null, cantidad: 1 });
  }
  
  _renderJuegoModal(editData);
};

function _renderJuegoModal(editData) {
  const ed = editData || {};
  const titulo = _juegoModalEditingId ? `Editar Juego #${_juegoModalEditingId}` : "Nuevo Juego / Combo";
  showModal(`<h3 class="font-display text-xl mb-4">${titulo}</h3>
    <form onsubmit="guardarJuego(event)" class="space-y-3">
      <div><label class="block text-sm mb-1 font-medium">Nombre del juego</label>
        <input id="juego-nombre" required value="${ed.nombre || ''}" placeholder="Ej: Combo Caña" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/>
      </div>
      <div><label class="block text-sm mb-1 font-medium">Descripcion</label>
        <textarea id="juego-desc" rows="2" placeholder="Opcional" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none">${ed.descripcion || ''}</textarea>
      </div>
      <div>
        <h4 class="font-medium text-sm mb-2 text-charcoal/70">Items del combo</h4>
        <div id="juego-items" class="space-y-2"></div>
        <button type="button" onclick="_addJuegoItem()" class="mt-2 text-xs text-primary hover:underline flex items-center gap-1"><span class="material-symbols-outlined text-sm">add</span> Agregar item</button>
      </div>
      <div id="juego-precio-total" class="border-t border-ivory-dark pt-2 mt-2 text-sm"></div>
      <div><label class="block text-sm mb-1 font-medium">Precio del combo</label>
        <div class="flex gap-2 items-center">
          <input id="juego-precio" type="number" min="0" step="1000" value="${ed.precio_alquiler ?? 0}" class="w-32 border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" placeholder="Precio final"/>
          <button type="button" id="juego-precio-suggest-btn" onclick="_syncPrecioSugerido()" class="text-xs text-primary hover:underline">Usar sugerido</button>
        </div>
        <p id="juego-precio-sugerido-txt" class="text-xs text-charcoal/40 mt-1"></p>
      </div>
      <button type="submit" class="w-full bg-primary text-on-primary px-4 py-2 rounded-lg hover:opacity-90 transition font-medium">${_juegoModalEditingId ? 'Actualizar' : 'Crear'} Juego</button>
    </form>`);
  _renderJuegoItems();
}

function _renderJuegoItems() {
  const cont = document.getElementById("juego-items");
  if (!cont) return;
  cont.innerHTML = _juegoModalItems.map((item, i) => {
    const sel = _juegoModalMobiliario.find(m => m.id === item.mobiliario_id);
    const selLabel = sel ? `${sel.nombre} – $${sel.precio_alquiler?.toLocaleString("es-AR")}` : "";
    return `<div class="flex gap-2 items-center">
      <div class="relative flex-1">
        <input type="text" value="${selLabel}" placeholder="Buscar mobiliario..." autocomplete="off" oninput="_juegoItemSearch(this, ${i})" class="w-full border border-ivory-dark rounded-lg p-2 text-sm focus:border-primary outline-none" />
        <div class="absolute z-50 left-0 right-0 mt-1 bg-white border border-ivory-dark rounded-lg shadow-lg max-h-48 overflow-y-auto hidden" data-juego-dd="1"></div>
      </div>
      <input type="number" value="${item.cantidad}" min="1" onchange="_juegoModalItems[${i}].cantidad=parseInt(this.value)||1;_renderJuegoItems()" class="w-20 border border-ivory-dark rounded-lg p-2 text-sm focus:border-primary outline-none" placeholder="Cant"/>
      ${_juegoModalItems.length > 1 ? `<button type="button" onclick="_removeJuegoItem(${i})" class="text-red-400 hover:text-red-600 transition"><span class="material-symbols-outlined text-sm">close</span></button>` : ''}
    </div>`;
  }).join("");
  _updateJuegoPrecioTotal();
}

function _updateJuegoPrecioTotal() {
  const el = document.getElementById("juego-precio-total");
  if (!el) return;
  let total = 0;
  _juegoModalItems.forEach(item => {
    const mob = _juegoModalMobiliario.find(m => m.id === item.mobiliario_id);
    if (mob) total += (mob.precio_alquiler || 0) * (item.cantidad || 1);
  });
  el.innerHTML = `<div class="flex justify-between"><span class="text-charcoal/50">Items válidos: ${_juegoModalItems.filter(i => i.mobiliario_id).length}</span><span class="text-charcoal/50">Suma de items: $${total.toLocaleString("es-AR")}</span></div>`;
  _juegoPrecioSugerido = total;
  const sugTxt = document.getElementById("juego-precio-sugerido-txt");
  if (sugTxt) sugTxt.textContent = `Sugerido (suma de items): $${total.toLocaleString("es-AR")}`;
}

window._syncPrecioSugerido = function() {
  const inp = document.getElementById("juego-precio");
  if (inp) inp.value = _juegoPrecioSugerido;
};

window._juegoItemSearch = function(inputEl, i) {
  const dd = inputEl.parentElement.querySelector('[data-juego-dd]');
  if (!dd) return;
  _juegoModalItems[i].mobiliario_id = null;
  const q = inputEl.value.trim().toLowerCase();
  if (!q) { dd.classList.add("hidden"); dd.innerHTML = ""; return; }
  const filtrados = _juegoModalMobiliario.filter(m => (m.nombre || "").toLowerCase().includes(q)).slice(0, 20);
  if (filtrados.length === 0) {
    dd.classList.remove("hidden");
    dd.innerHTML = `<div class="p-2 text-sm text-charcoal/40">Sin resultados</div>`;
    return;
  }
  dd.classList.remove("hidden");
  dd.innerHTML = filtrados.map(m => 
    `<div class="p-2 text-sm cursor-pointer hover:bg-ivory-dark border-b border-ivory-dark/50 last:border-0" onclick="_juegoItemSelect(${i}, ${m.id})"><span class="font-medium">${m.nombre}</span> <span class="text-charcoal/50">— $${m.precio_alquiler?.toLocaleString("es-AR")}</span></div>`
  ).join("");
};

window._juegoItemSelect = function(i, mobId) {
  _juegoModalItems[i].mobiliario_id = mobId;
  _renderJuegoItems();
};

window._addJuegoItem = function() {
  _juegoModalItems.push({ mobiliario_id: null, cantidad: 1 });
  _renderJuegoItems();
};

window._removeJuegoItem = function(i) {
  _juegoModalItems.splice(i, 1);
  _renderJuegoItems();
};

window.guardarJuego = async function(ev) {
  ev.preventDefault();
  const nombre = document.getElementById("juego-nombre").value.trim();
  const descripcion = document.getElementById("juego-desc").value.trim();
  const items = _juegoModalItems.filter(i => i.mobiliario_id);
  if (items.length === 0) { toast("Agrega al menos un item", "error"); return; }
  
  const data = { nombre, descripcion, precio_alquiler: parseFloat(document.getElementById("juego-precio").value) || 0, items: items.map(i => ({ mobiliario_id: i.mobiliario_id, cantidad: i.cantidad })) };
  
  try {
    if (_juegoModalEditingId) {
      await apiPut(`/juegos/${_juegoModalEditingId}`, data);
      toast("Juego actualizado");
    } else {
      await apiPost("/juegos/", data);
      toast("Juego creado");
    }
    closeModal();
    loadJuegos();
  } catch (e) {
    toast("Error: " + e.message, "error");
  }
};

window.editJuego = function(id) {
  openJuegoModal(id);
};

window.confirmarEliminarJuego = function(id, nombre) {
  showModal(`<h3 class="font-display text-xl mb-4 text-red-600">Eliminar Juego</h3>
    <p class="text-sm mb-4">¿Estás seguro de eliminar <strong>${nombre}</strong>?</p>
    <div class="flex gap-2">
      <button onclick="closeModal()" class="flex-1 bg-ivory-dark text-charcoal px-4 py-2 rounded-lg hover:bg-ivory transition font-medium">Cancelar</button>
      <button onclick="eliminarJuego(${id})" class="flex-1 bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600 transition font-medium">Eliminar</button>
    </div>`);
};

window.eliminarJuego = async function(id) {
  try {
    await apiDelete(`/juegos/${id}`);
    closeModal();
    loadJuegos();
    toast("Juego eliminado");
  } catch (e) {
    toast("Error: " + e.message, "error");
  }
};
