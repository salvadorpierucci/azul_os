# WhatsApp迁移 - Evolution AP→Baileys

## Fecha: 2026-06-28

## Cambios Realizados

### 1. Nuevo Servicio WhatsApp Baileys
- **Ubicación**: `/home/sathel/proyectos/whatsapp-baileys/`
- **Puerto**: 3001
- **Dependencias**: Node.js + @whiskeysockets/baileys
- **Estado**: ✅ Corriendo

### 2. Backend Azul OS Actualizado
- **Archivo**: `/home/sathel/proyectos/azul-os/backend/app/routers/whatsapp.py`
- **Cambio**: Ahora usa `WHATSAPP_SERVICE_URL=http://localhost:3001` en vez de Evolution API
- **Endpoint**: `/send` del servicio Baileys reemplaza a `/message/sendText/{instance}`

### 3. Script de Inicio Unificado
- **Archivo**: `/home/sathel/proyectos/azul-os/start_all.sh`
- **Funcionalidad**: Inicia WhatsApp Baileys + Backend FastAPI automáticamente

## Cómo Usar

### Iniciar el Sistema

```bash
# Opción 1: Script unificado (recomendado)
/home/sathel/proyectos/azul-os/start_all.sh

# Opción 2: Por separado
# Terminal 1: WhatsApp
cd /home/sathel/proyectos/whatsapp-baileys
node server.js

# Terminal 2: Backend
cd /home/sathel/proyectos/azul-os/backend
../venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Conectar WhatsApp (Primera Vez)

1. Iniciá el servicio WhatsApp Baileys
2. Verás un QR en la consola
3. Escanealo con tu WhatsApp:
   - Android: Menú → Dispositivos vinculados → Vincular dispositivo
   - iPhone: Configuración → Dispositivos vinculados → Vincular dispositivo
4. La sesión se guarda en `auth_info/` - no necesitás re-escanear cada vez

### Ver Estado

```bash
# WhatsApp service
curl http://localhost:3001/status
# {"status":"connected","connected":true}

# Backend
curl http://localhost:8000/whatsapp/admin/config
# {"bot_activo":"true",...}
```

### Enviar Mensaje Test

```bash
# Desde la línea de comandos
curl -X POST http://localhost:3001/send \
  -H "Content-Type: application/json" \
  -d '{"number":"5492323346385","text":"Hola desde Baileys!"}'

# Desde Azul OS (webhook automático configurado)
curl "http://localhost:8000/whatsapp/enviar/5492323346385?texto=Test"
```

## Comandos Útiles

```bash
# Ver logs de WhatsApp
tail -f /tmp/baileys.log

# Reiniciar conexión (nuevo QR)
curl -X POST http://localhost:3001/reconnect

# Ver procesos
pgrep -fa "node.*server.js"  # WhatsApp
pgrep -fa "uvicorn"           # Backend
```

## Ventajas vs Evolution API

| Característica | Evolution API | Baileys Puro |
|---------------|---------------|--------------|
| **Docker** | ✅ Requerido | ❌ No |
| **Puertos** | 8080 + DB + Redis | 3001 |
| **Memoria** | ~500MB | ~50MB |
| **Inicio** | 30-60s | 5-10s |
| **Estabilidad** | ❌ Keep-alive errors | ✅ Conexión directa |
| **QR** | Cada 24hs |Persistente |
| **Mantenimiento** | Alto | Bajo |

## Problemas Comunes

### "No conectado a WhatsApp"
- Escaneá el QR nuevamente
- Verificá: `curl http://localhost:3001/status`
- Si dice `"connected":false`, necesitás re-escanear

### QR no aparece
1. Matá el proceso: `pkill -f 'node.*server.js'`
2. Opcional: borrá `auth_info/` para nueva sesión
3. Reiniciá: `node server.js`

### Mensajes no llegan
- Verificá estado: `curl http://localhost:3001/status`
- Si está `connected`, revisá logs: `tail -f /tmp/baileys.log`
- Verificá que el número tenga formato: `5492323346385` (sin +)

## Próximos Pasos

1. **Escaneá el QR** para conectar tu WhatsApp
2. **Probá los comandos**:
   - Enviá "hola" a tu número
   - Deberías recibir el menú de comandos
3. **Configurá webhook** si必要 (ya está configurado por defecto)

## Archivos Clave

```
/home/sathel/proyectos/
├── whatsapp-baileys/
│   ├── server.js           # Servicio principal
│   ├── .env                # Config (puerto, webhook)
│   ├── package.json        # Dependencias
│   ├── start.sh            # Script de inicio
│   ├── README.md           # Documentación
│   └── auth_info/          # Sesión de WhatsApp (auto-generado)
│
└── azul-os/
    ├── backend/
    │   └── app/routers/
    │       └── whatsapp.py  # Integra con Baileys
    └── start_all.sh         # Script unificado
```

## Notas

- **Puerto 3000**: Ocupado por另一个 service (`whatsapp-bridge.js`). No lo toques.
- **Puerto 3001**: WhatsApp Baileys (nuevo)
- **Puerto 8000**: Backend Azul OS

## Soporte

Si algo falla:
1. Revisá logs: `tail -f /tmp/baileys.log`
2. Verificá estado: `curl http://localhost:3001/status`
3. Reconnect: `curl -X POST http://localhost:3001/reconnect`
4. Busca "Connection Failure" en los logs - indica problems de red

---

**Estado Actual**: ✅ Sistema migrado y funcional. Solo falta escanear QR para activar WhatsApp.