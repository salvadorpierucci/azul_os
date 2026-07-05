"""Autenticación simple por bearer token + cookie de sesión.

El token se configura via env var AZUL_AUTH_TOKEN en ~/.config/azul-os/.env
Si no está seteado, la auth está deshabilitada (modo desarrollo local).

Para producción (Cloudflare Tunnel): setear AZUL_AUTH_TOKEN y AZUL_AUTH_PASSWORD.

Excepciones (rutas públicas sin auth):
  - /login, /logout (endpoints de auth)
  - /css/, /js/, /uploads/ (assets estáticos)
  - /api/debug/ (health checks)
  - /whatsapp/webhook (callbacks de Twilio)
"""
import os
import secrets
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


# Token de auth — si no está seteado, auth deshabilitada
_AUTH_TOKEN = os.environ.get("AZUL_AUTH_TOKEN", "")
# Password para obtener el token via /login
_AUTH_PASSWORD = os.environ.get("AZUL_AUTH_PASSWORD", "azul")

# Rutas que NO requieren auth
_PUBLIC_PATHS = {"/login", "/logout"}

# Prefijos de rutas públicas
_PUBLIC_PREFIXES = (
    "/css/",
    "/js/",
    "/uploads/",
    "/api/debug/",
    "/favicon",
    "/whatsapp/webhook",
)


def _is_public(path: str) -> bool:
    if path in _PUBLIC_PATHS:
        return True
    for prefix in _PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware que valida bearer token o cookie de sesión."""

    async def dispatch(self, request: Request, call_next):
        # Si no hay token configurado, auth deshabilitada
        if not _AUTH_TOKEN:
            return await call_next(request)

        path = request.url.path

        # Rutas públicas — sin auth
        if _is_public(path):
            return await call_next(request)

        # Verificar header Authorization: Bearer <token>
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if secrets.compare_digest(token, _AUTH_TOKEN):
                return await call_next(request)

        # Verificar cookie de sesión
        cookie_token = request.cookies.get("azul_session", "")
        if cookie_token and secrets.compare_digest(cookie_token, _AUTH_TOKEN):
            return await call_next(request)

        # No autenticado
        if path.startswith("/api/") or path.startswith("/whatsapp/"):
            return JSONResponse({"detail": "No autorizado"}, status_code=401)

        # Para requests de navegador (HTML), redirigir a login
        accept = request.headers.get("accept", "")
        if "text/html" in accept and "application/json" not in accept:
            return Response(
                content='<html><head><meta http-equiv="refresh" content="0;url=/login"></head></html>',
                status_code=302,
                headers={"location": "/login"},
            )
        return JSONResponse({"detail": "No autorizado"}, status_code=401)


async def login_endpoint(request: Request):
    """POST /login — body: {"password": "..."} → setea cookie + retorna token."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    password = body.get("password", "")
    if not _AUTH_TOKEN:
        return JSONResponse({"detail": "Auth no configurada"}, status_code=500)
    if not secrets.compare_digest(password, _AUTH_PASSWORD):
        return JSONResponse({"detail": "Contraseña incorrecta"}, status_code=401)
    response = JSONResponse({"token": _AUTH_TOKEN, "ok": True})
    response.set_cookie(
        key="azul_session",
        value=_AUTH_TOKEN,
        httponly=True,
        samesite="lax",
        max_age=86400 * 7,  # 7 días
    )
    return response


async def logout_endpoint():
    """POST /logout — elimina cookie."""
    response = JSONResponse({"ok": True})
    response.delete_cookie("azul_session")
    return response


def login_page():
    """Página de login HTML simple."""
    return Response(
        content="""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Azul OS — Login</title>
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Hanken+Grotesk:wght@300;400;500;600&display=swap" rel="stylesheet"/>
<script>
  tailwind.config = {
    theme: { extend: {
      colors: {
        primary: "#c5a880", "on-primary": "#ffffff",
        navy: "#3a5874", "navy-dark": "#2c4359", "navy-darker": "#1a2a3a",
        ivory: "#fdfbf7", "ivory-dark": "#f4efe6", charcoal: "#1a2a3a",
      },
      fontFamily: { display: ["Playfair Display"], body: ["Hanken Grotesk"] }
    }}
  }
</script>
</head>
<body class="bg-navy-darker min-h-screen flex items-center justify-center font-body">
  <div class="bg-ivory rounded-xl shadow-2xl p-8 w-full max-w-sm">
    <h1 class="font-display text-3xl text-navy text-center mb-2">Azul OS</h1>
    <p class="text-charcoal/50 text-center text-sm mb-6">Gestión de Eventos</p>
    <form onsubmit="doLogin(event)" class="space-y-4">
      <div>
        <label class="block text-sm mb-1 font-medium text-charcoal/70">Contraseña</label>
        <input id="password" type="password" required autofocus
          class="w-full border border-ivory-dark rounded-lg p-3 focus:border-primary outline-none"
          placeholder="••••••••"/>
      </div>
      <button type="submit"
        class="w-full bg-primary text-on-primary px-4 py-3 rounded-lg font-medium hover:opacity-90 transition">
        Ingresar
      </button>
      <p id="error" class="text-red-500 text-sm text-center hidden"></p>
    </form>
  </div>
  <script>
    async function doLogin(e) {
      e.preventDefault();
      const pw = document.getElementById('password').value;
      const errEl = document.getElementById('error');
      try {
        const r = await fetch('/login', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({password: pw})
        });
        if (r.ok) {
          window.location.href = '/';
        } else {
          const data = await r.json();
          errEl.textContent = data.detail || 'Error';
          errEl.classList.remove('hidden');
        }
      } catch(err) {
        errEl.textContent = 'Error de conexión';
        errEl.classList.remove('hidden');
      }
    }
  </script>
</body>
</html>""",
        media_type="text/html",
    )
