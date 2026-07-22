// ─── Juegos (combos de mobiliario) ───
let _juegosList = [];

async function loadJuegos() {
  try {
    const data = await apiGet("/juegos");
    _juegosList = Array.isArray(data) ? data : [];
  } catch (e) {
    _juegosList = [];
    console.error("Error cargando juegos:", e);
  }
  renderJuegos();
}

function renderJuegos() {
  const cont = document.getElementById("page-content");
  if (!cont) return;
  const juegos = _juegosList;
  const cardsHtml = juegos.length === 0
    ? `<div class="text-center py-12 text-charcoal/40"><span class="material-symbols-outlined text-5xl">inventory_2</span><p class="mt-2">No hay juegos creados</p></div>`
    : juegos.map(j => `
      <div class="bg-white rounded-xl shadow-sm border border-ivory-dark overflow-hidden hover:shadow-md transition">
        <div class="p-4">
          <div class="flex items-start justify-between">
            <div>
              <h3 class="font-display text-lg text-navy">${j.nombre}</h3>
              <p class="text-sm text-charcoal/60 mt-1">Mobiliario: ${j.mobiliario_nombre}</p>
            </div>
            <div class="flex gap-1">
              <button onclick="editJuego(${j.id})" class="bg-ivory-dark/30 p-1.5 rounded hover:bg-primary hover:text-on-primary transition" title="Editar"><span class="material-symbols-outlined text-sm">edit</span></button>
              <button onclick="confirmarEliminarJuego(${j.id}, '${j.nombre.replace(/'/g, "\\'")}')" class="bg-ivory-dark/30 p-1.5 rounded hover:bg-red-500 hover:text-white transition" title="Eliminar"><span class="material-symbols-outlined text-sm">delete</span></button>
            </div>
          </div>
          <div class="grid grid-cols-3 gap-2 mt-3 text-sm">
            <div><span class="text-charcoal/50 block">Cantidad</span><span class="font-medium">${j.cantidad} un.</span></div>
            <div><span class="text-charcoal/50 block">Precio</span><span class="font-medium">$${(j.precio_alquiler || 0).toLocaleString("es-AR")}</span></div>
            <div><span class="text-charcoal/50 block">Stock disp.</span><span class="font-medium">${Math.floor((j.mobiliario_stock || 0) / (j.cantidad || 1))} juegos</span></div>
          </div>
          ${j.descripcion ? `<p class="text-xs text-charcoal/40 mt-2 italic">${j.descripcion}</p>` : ""}
          ${!j.activo ? `<span class="inline-block mt-2 text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">Inactivo</span>` : ""}
        </div>
      </div>`).join("");

  cont.innerHTML = `
    <div class="flex items-center justify-between mb-6">
      <h2 class="font-display text-3xl">Juegos</h2>
      <button onclick="openJuegoModal()" class="bg-primary text-on-primary px-4 py-2 rounded-lg font-medium hover:opacity-90 transition flex items-center gap-1">
        <span class="material-symbols-outlined text-base">add</span> Nuevo Juego
      </button>
    </div>
    <p class="text-sm text-charcoal/50 mb-4">Un juego agrupa N unidades de un mobiliario existente. El stock se calcula según la cantidad disponible.</p>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      ${cardsHtml}
    </div>`;
}

window.openJuegoModal = async function(editJuego) {
  const isEdit = !!editJuego;
  // Cargar mobiliario para el select
  let mobiliario = [];
  try {
    mobiliario = await apiGet("/mobiliario");
  } catch (e) { console.error(e); }
  const mobOptions = (Array.isArray(mobiliario) ? mobiliario : [])
    .filter(m => m.activo !== false)
    .map(m => `<option value="${m.id}" ${isEdit && editJuego.mobiliario_id === m.id ? "selected" : ""}>${m.nombre} (stock: ${m.stock_total})</option>`)
    .join("");

  showModal(`<h3 class="font-display text-xl mb-4">${isEdit ? 'Editar' : 'Nuevo'} Juego</h3>
    <form id="juego-form" onsubmit="crearJuego(event, ${isEdit ? editJuego.id : 'null'})">
      <div class="space-y-3">
        <div>
          <label class="block text-sm mb-1 font-medium">Nombre del juego</label>
          <input id="juego-nombre" value="${isEdit ? editJuego.nombre : ''}" placeholder="Ej: Juego Caña Bior 9p" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/>
        </div>
        <div>
          <label class="block text-sm mb-1 font-medium">Mobiliario base</label>
          <select id="juego-mobiliario" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none">
            <option value="">— Seleccionar —</option>
            ${mobOptions}
          </select>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-sm mb-1 font-medium">Cantidad de unidades</label>
            <input id="juego-cantidad" type="number" min="1" value="${isEdit ? editJuego.cantidad : 1}" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/>
          </div>
          <div>
            <label class="block text-sm mb-1 font-medium">Precio de alquiler ($)</label>
            <input id="juego-precio" type="number" min="0" step="1000" value="${isEdit ? editJuego.precio_alquiler : ''}" placeholder="0" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/>
          </div>
        </div>
        <div>
          <label class="block text-sm mb-1 font-medium">Descripción (opcional)</label>
          <textarea id="juego-descripcion" rows="2" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none">${isEdit ? (editJuego.descripcion || '') : ''}</textarea>
        </div>
        <label class="flex items-center gap-2 text-sm">
          <input id="juego-activo" type="checkbox" ${isEdit ? (editJuego.activo ? 'checked' : '') : 'checked'} class="rounded border-ivory-dark"/>
          Activo
        </label>
        <button type="submit" class="w-full bg-primary text-on-primary px-4 py-2 rounded-lg hover:opacity-90 transition font-medium flex items-center justify-center gap-1">
          <span class="material-symbols-outlined text-base">save</span> ${isEdit ? 'Guardar' : 'Crear'} Juego
        </button>
      </div>
    </form>`);
};

window.crearJuego = async function(ev, editId) {
  ev.preventDefault();
  const data = {
    nombre: document.getElementById("juego-nombre").value.trim(),
    mobiliario_id: parseInt(document.getElementById("juego-mobiliario").value),
    cantidad: parseInt(document.getElementById("juego-cantidad").value) || 1,
    precio_alquiler: parseFloat(document.getElementById("juego-precio").value) || 0,
    descripcion: document.getElementById("juego-descripcion").value.trim(),
    activo: document.getElementById("juego-activo").checked,
  };
  if (!data.nombre || !data.mobiliario_id) {
    toast("Faltan datos obligatorios", "error");
    return;
  }
  try {
    if (editId) {
      await apiPut(`/juegos/${editId}`, data);
      toast("Juego actualizado");
    } else {
      await apiPost("/juegos", data);
      toast("Juego creado");
    }
    closeModal();
    loadJuegos();
  } catch (e) {
    console.error(e);
    toast("Error al guardar juego: " + (e.message || e), "error");
  }
};

window.editJuego = async function(id) {
  const juegos = await apiGet("/juegos");
  const item = juegos.find(j => j.id === id);
  if (item) openJuegoModal(item);
};

window.confirmarEliminarJuego = function(id, nombre) {
  showModal(`<h3 class="font-display text-xl mb-4 text-red-600">Eliminar Juego</h3>
    <p class="mb-4">¿Seguro que querés eliminar "<strong>${nombre}</strong>"? Esta acción no se puede deshacer.</p>
    <div class="flex gap-2">
      <button onclick="eliminarJuego(${id})" class="flex-1 bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600 transition font-medium">Eliminar</button>
      <button onclick="closeModal()" class="flex-1 bg-ivory-dark/30 px-4 py-2 rounded-lg hover:bg-ivory-dark/50 transition">Cancelar</button>
    </div>`);
};

window.eliminarJuego = async function(id) {
  try {
    await apiDelete(`/juegos/${id}`);
    closeModal();
    loadJuegos();
    toast("Juego eliminado");
  } catch (e) {
    toast("Error al eliminar: " + (e.message || e), "error");
  }
};
