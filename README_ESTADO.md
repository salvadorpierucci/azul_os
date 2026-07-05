# Azul OS - Estado del Sistema

**Fecha**: 2026-06-28
**Versión**: Baileys Puro (sin Evolution API)

## Arquitectura Actual

### WhatsApp Service
- **Tecnología**: Node.js + @whiskeysockets/baileys
- **Ubicación**: `/home/sathel/proyectos/whatsapp-baileys/`
- **Puerto**: 3001
- **Estado**: ✅ Funcional
- **Autenticación**: QR o Pairing Code
- **Persistencia**: `auth_info/` (sesión guardada)

### Backend Azul OS
- **Tecnología**: Python + FastAPI
- **Ubicación**: `/home/sathel/proyectos/azul-os/backend/`
- **Puerto**: 8000
- **Estado**: ✅ Funcional
- **Integración WhatsApp**: HTTP POST a `localhost:3001/send`

## Cómo Iniciar

```bash
# Script unificado
/home/sathel/proyectos/azul-os/start_all.sh
```

## Conectar WhatsApp

1. Iniciá el servicio
2. Escaneá el QR que aparece en consola
3. Listo! La sesión se guarda

## Ver Estado

```bash
curl http://localhost:3001/status
curl http://localhost:8000/whatsapp/admin/config
```

## Logs

```bash
tail -f /tmp/baileys.log
```

---

**Eliminado**: Evolution API, Docker, Redis, Postgres
**Próximo**: Escanear QR para activar