@echo off
:: ════════════════════════════════════════════════════════════
:: AZUL OS — BACKUP DE BASE DE DATOS (Windows)
:: ════════════════════════════════════════════════════════════
:: Llama al script Python cross-platform.
:: Ejecutado por Programador de Tareas todos los dias a las 03:00.
:: Tambien se ejecuta al iniciar Azul OS.
:: ════════════════════════════════════════════════════════════

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."

cd /d "%PROJECT_DIR%"

:: Ejecutar backup via Python (usa sqlite3 .backup — copia segura en caliente)
call venv\Scripts\activate.bat >nul 2>&1
python "%SCRIPT_DIR%backup_db.py"

if %errorlevel% equ 0 (
    exit /b 0
) else (
    echo [%date% %time%] ERROR: Backup fallido con codigo %errorlevel%
    exit /b %errorlevel%
)