:: ════════════════════════════════════════════════════════════════════════
:: INSTALADOR AZUL OS — Windows 10/11
:: ════════════════════════════════════════════════════════════════════════
:: Doble-click este archivo. Instala TODO automaticamente:
::
::   ✓ Python 3.12 (si no esta)
::   ✓ Entorno virtual + dependencias
::   ✓ Base de datos SQLite (conserva datos si ya existe)
::   ✓ Backup automatico diario con copia segura en caliente
::   ✓ Autenticacion (password + token)
::   ✓ Accesos directos en Escritorio y Menu Inicio
::
:: Al terminar, Azul OS esta 100% funcional en http://localhost:8000
:: ════════════════════════════════════════════════════════════════════════

@echo off
setlocal enabledelayedexpansion
title Azul OS — Instalador

cd /d "%~dp0"
set "INSTALL_DIR=%~dp0"
set "INSTALL_DIR=%INSTALL_DIR:~0,-1%"

echo.
echo   ╔══════════════════════════════════════════════════════════╗
echo   ║                                                          ║
echo   ║        AZUL OS — INSTALADOR WINDOWS                     ║
echo   ║        Sistema de Gestion para Azul Livings             ║
echo   ║                                                          ║
echo   ║  Instala: Python 3.12 · venv · dependencias · DB        ║
echo   ║           backup automatico · auth · accesos directos   ║
echo   ║                                                          ║
echo   ╚══════════════════════════════════════════════════════════╝
echo.
echo   Presiona cualquier tecla para comenzar...
pause >nul

:: ────────────────────────────────────────────────────────────
:: PASO 1/7 — Python 3.12
:: ────────────────────────────────────────────────────────────
echo.
echo   [1/7] Verificando Python...

where python >nul 2>nul
if %errorlevel% equ 0 (
    for /f "tokens=2" %%v in ('python -c "import sys; print(sys.version_info.minor)" 2^>nul') do set "pyver=%%v"
    for /f "tokens=1" %%v in ('python -c "import sys; print(sys.version_info.major)" 2^>nul') do set "pymajor=%%v"
    echo         Python !pymajor!.!pyver! encontrado.
    if !pymajor! LSS 3 goto :install_python
    if !pymajor! equ 3 if !pyver! LSS 10 goto :install_python
    goto :python_ok
)

:install_python
echo         Instalando Python 3.12 automaticamente...
where winget >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo         winget no disponible. Abriendo descarga manual...
    echo         https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe
    echo         Importante: MARCA "Add Python to PATH" durante la instalacion.
    start https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe
    echo.
    echo         Despues de instalar Python, ejecuta este instalador de nuevo.
    pause
    exit /b 1
)

echo         Descargando Python 3.12 via winget...
winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements 2>&1
if %errorlevel% neq 0 (
    echo         winget fallo. Abriendo descarga manual...
    start https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe
    pause
    exit /b 1
)

echo         Python instalado. Refrescando PATH...
call :refresh_env
timeout /t 3 /nobreak >nul

:python_ok
echo         Python OK.

:: ────────────────────────────────────────────────────────────
:: PASO 2/7 — Entorno virtual + dependencias
:: ────────────────────────────────────────────────────────────
echo.
echo   [2/7] Creando entorno virtual e instalando dependencias...

if exist "venv\" (
    echo         venv ya existe. Saltando...
) else (
    python -m venv venv 2>&1
    if %errorlevel% neq 0 (
        echo         ERROR al crear venv. Revisa que Python este en PATH.
        pause
        exit /b 1
    )
    echo         venv creado.
)

call venv\Scripts\activate.bat
python -m pip install --upgrade pip -q 2>&1
echo         Instalando FastAPI + SQLAlchemy + ReportLab + Pillow...
pip install -r backend\requirements.txt -q 2>&1
echo         Instalando herramientas adicionales...
pip install alembic pytest openpyxl -q 2>&1
echo         Dependencias instaladas.

:: ────────────────────────────────────────────────────────────
:: PASO 3/7 — Archivo .env
:: ────────────────────────────────────────────────────────────
echo.
echo   [3/7] Configurando .env...

if exist "backend\.env" (
    echo         .env ya existe. Saltando...
    goto :env_ok
)

:: Generar token aleatorio
python -c "import secrets; print(secrets.token_hex(32))" > "%TEMP%\azul_token.txt" 2>nul
set /p AZUL_TOKEN=<"%TEMP%\azul_token.txt"
del "%TEMP%\azul_token.txt" 2>nul

copy /y backend\.env.example backend\.env >nul 2>&1

:: Append auth + CORS + Twilio placeholder
echo. >> backend\.env
echo # --- AUTENTICACION (generada automaticamente) --- >> backend\.env
echo AZUL_AUTH_TOKEN=%AZUL_TOKEN% >> backend\.env
echo AZUL_AUTH_PASSWORD=azul >> backend\.env
echo. >> backend\.env
echo # --- CORS (vacio = solo localhost) --- >> backend\.env
echo AZUL_CORS_ORIGINS= >> backend\.env
echo. >> backend\.env
echo # --- TWILIO WHATSAPP (completar manualmente) --- >> backend\.env
echo # Conseguir cuenta gratuita en https://www.twilio.com/console >> backend\.env

echo         .env creado con autenticacion.
echo.
echo         ══════════════════════════════════════════════════
echo         IMPORTANTE — GUARDA ESTA INFORMACION:
echo           TOKEN:  %AZUL_TOKEN%
echo           PASSWORD: azul
echo         ══════════════════════════════════════════════════
echo.

:env_ok

:: ────────────────────────────────────────────────────────────
:: PASO 4/7 — Base de datos
:: ────────────────────────────────────────────────────────────
echo.
echo   [4/7] Verificando base de datos...

if not exist "data\" mkdir "data"

if exist "data\azul_os.db" (
    :: Verificar integridad de DB existente
    echo         DB encontrada. Verificando integridad...
    python -c "import sqlite3; c=sqlite3.connect(r'data\azul_os.db'); r=c.execute('PRAGMA integrity_check').fetchone()[0]; c.close(); print(r); exit(0 if r=='ok' else 1)" 2>&1
    if %errorlevel% neq 0 (
        echo         ADVERTENCIA: DB existente no pasa verificación — inicializando nueva...
        python -c "from app.database import init_db; init_db(); print('DB inicializada')" 2>&1
    ) else (
        echo         DB OK — conservando datos existentes.
    )
) else (
    echo         DB no encontrada — inicializando...
    cd backend
    python -c "from app.database import init_db; init_db(); print('DB inicializada con datos seed')" 2>&1
    cd ..
    echo         DB creada con datos iniciales.
)

:: ────────────────────────────────────────────────────────────
:: PASO 5/7 — Backup automatico
:: ────────────────────────────────────────────────────────────
echo.
echo   [5/7] Configurando backup automatico...

:: Crear estructura de backups
if not exist "backups\daily" mkdir "backups\daily" 2>nul
if not exist "backups\weekly" mkdir "backups\weekly" 2>nul
if not exist "backups\monthly" mkdir "backups\monthly" 2>nul

:: Hacer primer backup ahora mismo
echo         Haciendo primer backup ahora...
call venv\Scripts\activate.bat >nul 2>&1
python scripts\backup_db.py 2>&1

:: Registrar tarea programada diaria a las 03:00
set "BACKUP_CMD=cmd /c cd /d \"%INSTALL_DIR%\" ^&^& call venv\Scripts\activate.bat ^>nul ^&^& python scripts\backup_db.py"

schtasks /create /tn "Azul OS Backup Diario" /tr "%BACKUP_CMD%" /sc daily /st 03:00 /f /rl limited 2>&1
if %errorlevel% equ 0 (
    echo         Tarea programada: Backup diario a las 03:00 AM.
) else (
    echo         ADVERTENCIA: No se pudo crear tarea programada ^(sin permisos^).
    echo         El backup igual se ejecuta cada vez que inicias Azul OS.
)

:: ────────────────────────────────────────────────────────────
:: PASO 6/7 — Launcher (iniciar.bat)
:: ────────────────────────────────────────────────────────────
echo.
echo   [6/7] Creando launcher...

set "LAUNCHER=%INSTALL_DIR%\Iniciar Azul OS.bat"

echo @echo off > "%LAUNCHER%"
echo title Azul OS — Servidor >> "%LAUNCHER%"
echo :: Iniciar Azul OS en http://localhost:8000 >> "%LAUNCHER%"
echo. >> "%LAUNCHER%"
echo cd /d "%INSTALL_DIR%" >> "%LAUNCHER%"
echo. >> "%LAUNCHER%"
echo :: Activar venv >> "%LAUNCHER%"
echo call venv\Scripts\activate.bat >> "%LAUNCHER%"
echo. >> "%LAUNCHER%"
echo :: Backup de seguridad al iniciar >> "%LAUNCHER%"
echo echo Haciendo backup de seguridad... >> "%LAUNCHER%"
echo python scripts\backup_db.py 2^>nul >> "%LAUNCHER%"
echo echo. >> "%LAUNCHER%"
echo. >> "%LAUNCHER%"
echo echo ╔════════════════════════════════════════════════════╗ >> "%LAUNCHER%"
echo echo ║          AZUL OS — INICIANDO SERVIDOR              ║ >> "%LAUNCHER%"
echo echo ║  Abri http://localhost:8000 en tu navegador        ║ >> "%LAUNCHER%"
echo echo ║  Password: azul                                    ║ >> "%LAUNCHER%"
echo echo ╚════════════════════════════════════════════════════╝ >> "%LAUNCHER%"
echo echo. >> "%LAUNCHER%"
echo. >> "%LAUNCHER%"
echo :: Abrir navegador automaticamente >> "%LAUNCHER%"
echo start http://localhost:8000 >> "%LAUNCHER%"
echo. >> "%LAUNCHER%"
echo :: Iniciar servidor >> "%LAUNCHER%"
echo cd backend >> "%LAUNCHER%"
echo python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 >> "%LAUNCHER%"
echo. >> "%LAUNCHER%"
echo :: Si crashea, mostrar el error en vez de cerrarse >> "%LAUNCHER%"
echo echo. >> "%LAUNCHER%"
echo echo El servidor se detuvo. >> "%LAUNCHER%"
echo pause >> "%LAUNCHER%"

:: ────────────────────────────────────────────────────────────
:: PASO 7/7 — Accesos directos
:: ────────────────────────────────────────────────────────────
echo.
echo   [7/7] Creando accesos directos...

powershell -ExecutionPolicy Bypass -Command ^
  "$WshShell = New-Object -ComObject WScript.Shell; "^
  "$Desktop = [Environment]::GetFolderPath('Desktop'); "^
  "$StartMenu = [Environment]::GetFolderPath('StartMenu'); "^
  "$Programs = Join-Path $StartMenu 'Programs\Azul OS'; "^
  "New-Item -ItemType Directory -Force -Path $Programs | Out-Null; "^
  ""^
  "Write-Host '        Creando acceso en Escritorio...'; "^
  "$Shortcut = $WshShell.CreateShortcut(Join-Path $Desktop 'Azul OS.lnk'); "^
  "$Shortcut.TargetPath = '%LAUNCHER%'; "^
  "$Shortcut.WorkingDirectory = '%INSTALL_DIR%'; "^
  "$Shortcut.IconLocation = 'shell32.dll,14'; "^
  "$Shortcut.Save(); "^
  ""^
  "Write-Host '        Creando acceso en Menu Inicio...'; "^
  "$Shortcut2 = $WshShell.CreateShortcut(Join-Path $Programs 'Azul OS.lnk'); "^
  "$Shortcut2.TargetPath = '%LAUNCHER%'; "^
  "$Shortcut2.WorkingDirectory = '%INSTALL_DIR%'; "^
  "$Shortcut2.IconLocation = 'shell32.dll,14'; "^
  "$Shortcut2.Save(); "^
  ""^
  "Write-Host '        Listo.'"

:: ────────────────────────────────────────────────────────────
:: FINAL
:: ────────────────────────────────────────────────────────────

echo.
echo   ╔══════════════════════════════════════════════════════════╗
echo   ║                                                          ║
echo   ║       INSTALACION COMPLETADA CON EXITO                   ║
echo   ║                                                          ║
echo   ╚══════════════════════════════════════════════════════════╝
echo.
echo   Azul OS esta listo para usar.
echo.
echo   PARA INICIAR:
echo     - Doble-click en "Azul OS" en el Escritorio
echo     - Abri http://localhost:8000 en tu navegador
echo     - Password: azul
echo.
echo   BACKUPS:
echo     - Automatico: todos los dias a las 03:00 AM
echo     - Tambien se hace backup al iniciar Azul OS
echo     - Guardados en carpeta backups\ (7 diarios + 4 semanales + 3 mensuales)
echo     - Para restaurar: doble-click en scripts\restore_db.bat
echo.
echo   WHATSAPP:
echo     - Edita backend\.env con tus credenciales de Twilio
echo     - Reinicia Azul OS para activar el bot
echo.
echo   Para detener el servidor: cerra la ventana negra.
echo.
echo   Presiona cualquier tecla para cerrar...
pause >nul
exit /b 0

:: ─── Helper: refrescar variables de entorno ───
:refresh_env
    for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "syspath=%%b"
    set "PATH=%syspath%;%PATH%"
    goto :eof