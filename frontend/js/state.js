// ─── Estado compartido + Navegación ───
let currentPage = "dashboard";
let _dataCache = {};
let eventoSearch = "";
let clienteSearch = "";
let pptoSearch = "";
let pptoEstadoFilter = "";
let mobFilter = "";
let mobFechaDisponibilidad = "";  // YYYY-MM-DD; vacío = stock total
let _mobDisponibilidadMap = {};   // { mobiliario_id: stock_disponible_para_fecha }
let calYear, calMonth;
let _clientePerfilData = null;
let _clientePerfilTab = "eventos";
let finanzasAnio, finanzasMes, finanzasTipoFilter = "todos";
let _finanzasRegistros = [];
let _finanzasEventos = {};
let _presupuestosList = [];
let presupuestosList = [];
let _nuevoPptoLugares = [];
let _nuevoPptoClientes = [];
let _nuevoPptoMobiliario = [];
let _nuevoPptoEditingId = null;
let _finanzasPresupuestos = [];

const MONTHS_ES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];

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
