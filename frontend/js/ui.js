// ─── MODAL + TOAST + INIT ───
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
