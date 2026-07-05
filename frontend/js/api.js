// URL base dinamica: usa el mismo host:puerto que el navegador
const API = window.location.origin + "/api";
const BASE_URL = window.location.origin;

// Si una peticion devuelve 401, redirigir al login
async function _handleResponse(r) {
  if (r.status === 401) {
    window.location.href = "/login";
    throw new Error("No autorizado");
  }
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function apiGet(path) {
  const r = await fetch(`${API}${path}`, { credentials: "same-origin" });
  return _handleResponse(r);
}

async function apiPost(path, body) {
  const r = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: "same-origin",
  });
  return _handleResponse(r);
}

async function apiPut(path, body) {
  const r = await fetch(`${API}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: "same-origin",
  });
  return _handleResponse(r);
}

async function apiDelete(path) {
  const r = await fetch(`${API}${path}`, {
    method: "DELETE",
    credentials: "same-origin",
  });
  return _handleResponse(r);
}

async function apiUpload(path, formData) {
  const r = await fetch(`${API}${path}`, {
    method: "POST",
    body: formData,
    credentials: "same-origin",
  });
  return _handleResponse(r);
}

async function apiUploadPut(path, formData) {
  const r = await fetch(`${API}${path}`, {
    method: "PUT",
    body: formData,
    credentials: "same-origin",
  });
  return _handleResponse(r);
}