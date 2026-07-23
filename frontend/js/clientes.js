// ─── CLIENTES ───
async function loadClientes() {
  const clientes = await apiGet("/clientes/");
  const cont = document.getElementById("clientes-list");
  const searchEl = document.getElementById("cliente-search");
  if (searchEl) clienteSearch = searchEl.value.trim().toLowerCase();
  const filtered = clienteSearch
    ? clientes.filter(c => c.nombre.toLowerCase().includes(clienteSearch) || (c.telefono||"").includes(clienteSearch) || (c.whatsapp||"").includes(clienteSearch))
    : clientes;
  if (filtered.length === 0) {
    cont.innerHTML = `<div class="text-center py-12 text-charcoal/40"><span class="material-symbols-outlined text-5xl mb-2 block">person_off</span><p>${clienteSearch ? 'Sin resultados para "' + clienteSearch + '"' : 'No hay clientes'}</p></div>`;
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
          <button onclick="navigateToClientePerfil(${c.id})" class="p-1.5 hover:bg-ivory-dark rounded-lg transition" title="Ver perfil"><span class="material-symbols-outlined text-base text-charcoal/50 hover:text-primary">visibility</span></button>
          <button onclick="editarClienteModal(${c.id})" class="p-1.5 hover:bg-ivory-dark rounded-lg transition" title="Editar"><span class="material-symbols-outlined text-base text-charcoal/50 hover:text-primary">edit</span></button>
          <button onclick="confirmarEliminarCliente(${c.id},'${c.nombre.replace(/'/g,"\\'")}')" class="p-1.5 hover:bg-red-50 rounded-lg transition" title="Eliminar"><span class="material-symbols-outlined text-base text-charcoal/50 hover:text-red-500">delete</span></button>
        </div>
      </div>
    </div>`).join("");
}

window.onClienteSearch = function(val) { clienteSearch = val.trim().toLowerCase(); loadClientes(); };

window.openClienteModal = function() {
  showModal(`<h3 class="font-display text-xl mb-4">Nuevo Cliente</h3>
    <form onsubmit="crearCliente(event)">
      <div class="space-y-3">
        <div><label class="block text-sm mb-1 font-medium">Nombre</label><input name="nombre" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="block text-sm mb-1 font-medium">Telefono / WhatsApp</label><input name="whatsapp" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
          <div><label class="block text-sm mb-1 font-medium">Telefono alter.</label><input name="telefono" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
        </div>
        <div><label class="block text-sm mb-1 font-medium">Email</label><input name="email" type="email" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"/></div>
        <div><label class="block text-sm mb-1 font-medium">Notas</label><textarea name="notas" rows="2" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none"></textarea></div>
      </div>
      <button type="submit" class="mt-4 bg-primary text-on-primary px-4 py-2 rounded-lg hover:opacity-90 transition w-full font-medium">Guardar</button>
    </form>`);
};

window.crearCliente = async function(ev) {
  ev.preventDefault();
  const fd = new FormData(ev.target);
  const data = Object.fromEntries(fd.entries());
  if (!data.telefono) data.telefono = data.whatsapp || "";
  await apiPost("/clientes/", data); closeModal(); loadClientes(); toast("Cliente creado");
};

window.editarClienteModal = async function(id) {
  const c = await apiGet(`/clientes/${id}`);
  showModal(`<h3 class="font-display text-xl mb-4">Editar Cliente</h3>
    <form onsubmit="guardarCliente(event, ${id})">
      <div class="space-y-3">
        <div><label class="block text-sm mb-1 font-medium">Nombre</label><input name="nombre" required class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${c.nombre}"/></div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="block text-sm mb-1 font-medium">Telefono / WhatsApp</label><input name="whatsapp" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${c.whatsapp || ''}"/></div>
          <div><label class="block text-sm mb-1 font-medium">Telefono alter.</label><input name="telefono" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${c.telefono || ''}"/></div>
        </div>
        <div><label class="block text-sm mb-1 font-medium">Email</label><input name="email" type="email" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none" value="${c.email || ''}"/></div>
        <div><label class="block text-sm mb-1 font-medium">Notas</label><textarea name="notas" rows="2" class="w-full border border-ivory-dark rounded-lg p-2 focus:border-primary outline-none">${c.notas || ''}</textarea></div>
      </div>
      <button type="submit" class="mt-4 bg-primary text-on-primary px-4 py-2 rounded-lg hover:opacity-90 transition w-full font-medium">Guardar Cambios</button>
    </form>`);
};

window.guardarCliente = async function(ev, id) {
  ev.preventDefault();
  const fd = new FormData(ev.target);
  const data = Object.fromEntries(fd.entries());
  if (!data.telefono) data.telefono = data.whatsapp || "";
  await apiPut(`/clientes/${id}`, data); closeModal(); loadClientes(); toast("Cliente actualizado");
};

window.confirmarEliminarCliente = function(id, nombre) {
  showModal(`<h3 class="font-display text-xl mb-4 text-red-600">Eliminar Cliente</h3>
    <p class="text-sm mb-4">¿Estas seguro de eliminar <strong>${nombre}</strong>?</p>
    <p class="text-xs text-charcoal/50 mb-4">Si tiene eventos asociados, debera eliminar o reasignar esos eventos primero.</p>
    <div class="flex gap-2">
      <button onclick="closeModal()" class="flex-1 bg-ivory-dark text-charcoal px-4 py-2 rounded-lg hover:bg-ivory transition font-medium">Cancelar</button>
      <button onclick="eliminarCliente(${id})" class="flex-1 bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600 transition font-medium">Eliminar</button>
    </div>`);
};

window.eliminarCliente = async function(id) {
  try { await apiDelete(`/clientes/${id}`); closeModal(); loadClientes(); toast("Cliente eliminado"); }
  catch (e) { toast(e.message, "error"); }
};

// ─── CLIENTE PERFIL ───
window.navigateToClientePerfil = function(id) { navigate("cliente-perfil", id); };
window.goBackToClientes = function() { navigate("clientes"); };

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

function _pptoEstadoBadge(estado) {
  const map = { borrador: "bg-gray-100 text-gray-600", enviado: "bg-blue-100 text-blue-700", confirmado: "bg-green-100 text-green-700", cancelado: "bg-red-100 text-red-700" };
  return map[estado] || "bg-gray-100 text-gray-600";
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
      tabContent = `<div class="text-center py-8 text-charcoal/40"><span class="material-symbols-outlined text-4xl mb-2 block">event_busy</span><p>No hay eventos</p></div>`;
    } else {
      tabContent = c.eventos.map(e => {
        const badge = e.estado === "confirmado" ? "bg-primary text-on-primary" : e.estado === "reserva" ? "bg-yellow-400 text-charcoal" : e.estado === "cancelado" ? "bg-red-100 text-red-700" : "bg-green-100 text-green-700";
        const fecha = e.fecha ? (() => { const m = String(e.fecha).match(/^(\d{4})-(\d{2})-(\d{2})/); const ms=["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"]; return m ? `${m[3]} ${ms[parseInt(m[2],10)-1]} ${m[1]}` : "—"; })() : "—";
        const title = e.titulo || `Evento #${e.id}`;
        return `<div class="flex items-center justify-between py-3 px-1 border-b border-ivory-dark/60 last:border-0 hover:bg-ivory-dark/30 rounded transition">
          <div class="min-w-0 flex-1"><p class="font-medium truncate">${title}</p><p class="text-xs text-charcoal/50">${fecha}</p></div>
          <div class="flex items-center gap-2 flex-shrink-0 ml-3"><span class="font-display text-sm text-navy">$${(e.monto_total || 0).toLocaleString("es-AR")}</span><span class="text-xs px-2 py-1 rounded ${badge}">${e.estado}</span></div>
        </div>`;
      }).join("");
    }
  } else {
    if (!c.presupuestos || c.presupuestos.length === 0) {
      tabContent = `<div class="text-center py-8 text-charcoal/40"><span class="material-symbols-outlined text-4xl mb-2 block">receipt_long</span><p>No hay presupuestos</p></div>`;
    } else {
      tabContent = c.presupuestos.map(p => {
        const badge = _pptoEstadoBadge(p.estado);
        const fecha = p.fecha_evento ? (() => { const m = String(p.fecha_evento).match(/^(\d{4})-(\d{2})-(\d{2})/); const ms=["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"]; return m ? `${m[3]} ${ms[parseInt(m[2],10)-1]} ${m[1]}` : "—"; })() : "—";
        return `<div class="flex items-center justify-between py-3 px-1 border-b border-ivory-dark/60 last:border-0 hover:bg-ivory-dark/30 rounded transition cursor-pointer" onclick="navigate('presupuestos');verPresupuestoDetalle(${p.id})">
          <div class="min-w-0 flex-1"><p class="font-medium truncate">${p.tipo_evento || "Presupuesto"}</p><p class="text-xs text-charcoal/50">${fecha}</p></div>
          <div class="flex items-center gap-2 flex-shrink-0 ml-3"><span class="font-display text-sm text-navy">$${(p.total || 0).toLocaleString("es-AR")}</span><span class="text-xs px-2 py-1 rounded ${badge}">${p.estado || "borrador"}</span></div>
        </div>`;
      }).join("");
    }
  }
  cont.innerHTML = `<div class="bg-white rounded-lg shadow-sm p-5 border border-ivory-dark mb-6">
    <div class="flex items-start gap-4">
      <div class="w-14 h-14 rounded-full bg-navy/10 flex items-center justify-center flex-shrink-0"><span class="material-symbols-outlined text-3xl text-navy">person</span></div>
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
  <div class="grid grid-cols-2 gap-4 mb-6">
    <div class="bg-white rounded-lg shadow-sm p-4 border border-ivory-dark text-center"><p class="text-xs uppercase tracking-wider text-charcoal/40 mb-1">Total Eventos</p><p class="text-2xl font-display text-navy">${c.total_eventos || 0}</p></div>
    <div class="bg-white rounded-lg shadow-sm p-4 border border-ivory-dark text-center"><p class="text-xs uppercase tracking-wider text-charcoal/40 mb-1">Total Gastado</p><p class="text-2xl font-display text-primary">$${(c.total_gastado || 0).toLocaleString("es-AR")}</p></div>
  </div>
  <div class="bg-white rounded-lg shadow-sm p-5 border border-ivory-dark">
    <div class="flex gap-2 mb-4">
      <button onclick="_switchClientePerfilTab('eventos')" class="px-4 py-1.5 rounded-full text-sm font-medium transition ${tabEventosClass}">Eventos</button>
      <button onclick="_switchClientePerfilTab('presupuestos')" class="px-4 py-1.5 rounded-full text-sm font-medium transition ${tabPptoClass}">Presupuestos</button>
    </div>
    <div>${tabContent}</div>
  </div>`;
}

window._switchClientePerfilTab = function(tab) { _clientePerfilTab = tab; renderClientePerfil(); };
