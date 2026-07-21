@echo off
:: ════════════════════════════════════════════════════════════
:: AZUL OS — RESTAURAR BACKUP (Windows)
:: ════════════════════════════════════════════════════════════
:: Uso:
::   restore_db.bat                  (lista backups)
::   restore_db.bat latest           (restaura el mas reciente)
::   restore_db.bat daily\azul_os_20260713_142244.db.gz
:: ════════════════════════════════════════════════════════════

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."
cd /d "%PROJECT_DIR%"

set "DB_PATH=data\azul_os.db"
set "BACKUP_DIR=backups"

:: ─── Sin argumentos: listar backups ───
if "%1"=="" goto :list_backups
if /i "%1"=="latest" goto :restore_latest

:: ─── Ruta especifica ───
set "BACKUP_FILE=%BACKUP_DIR%\%1"
if not exist "!BACKUP_FILE!" set "BACKUP_FILE=%1"
if not exist "!BACKUP_FILE!" (
    echo.
    echo   ERROR: Backup no encontrado: !BACKUP_FILE!
    echo.
    goto :list_backups
)
goto :do_restore

:: ─── Restaurar el mas reciente ───
:restore_latest
set "BACKUP_FILE="
for /f "delims=" %%f in ('dir /b /o-d "%BACKUP_DIR%\daily\azul_os_*.db.gz" 2^>nul') do (
    set "BACKUP_FILE=%BACKUP_DIR%\daily\%%f"
    goto :found_latest
)
for /f "delims=" %%f in ('dir /b /o-d "%BACKUP_DIR%\daily\azul_os_*.db" 2^>nul') do (
    set "BACKUP_FILE=%BACKUP_DIR%\daily\%%f"
    goto :found_latest
)
echo.
echo   ERROR: No hay backups diarios para restaurar.
echo.
goto :list_backups

:found_latest
echo.
echo   Restaurando backup mas reciente: !BACKUP_FILE!
goto :do_restore

:: ─── Listar backups ───
:list_backups
echo.
echo   ╔══════════════════════════════════════════════════════════╗
echo   ║          BACKUPS DISPONIBLES — AZUL OS                  ║
echo   ╚══════════════════════════════════════════════════════════╝
echo.

echo     DIARIOS (ultimos 7):
if exist "%BACKUP_DIR%\daily\azul_os_*.db.gz" (
    for /f "delims=" %%f in ('dir /b /o-d "%BACKUP_DIR%\daily\azul_os_*.db.gz" 2^>nul') do (
        echo       daily\%%f
    )
)
if exist "%BACKUP_DIR%\daily\azul_os_*.db" (
    for /f "delims=" %%f in ('dir /b /o-d "%BACKUP_DIR%\daily\azul_os_*.db" 2^>nul') do (
        echo       daily\%%f
    )
)
echo.
echo     SEMANALES (ultimos 4):
if exist "%BACKUP_DIR%\weekly\azul_os_*.db.gz" (
    for /f "delims=" %%f in ('dir /b /o-d "%BACKUP_DIR%\weekly\azul_os_*.db.gz" 2^>nul') do (
        echo       weekly\%%f
    )
)
echo.
echo     MENSUALES (ultimos 3):
if exist "%BACKUP_DIR%\monthly\azul_os_*.db.gz" (
    for /f "delims=" %%f in ('dir /b /o-d "%BACKUP_DIR%\monthly\azul_os_*.db.gz" 2^>nul') do (
        echo       monthly\%%f
    )
)
echo.
echo     Log: backups\backup.log
echo.
echo     Para restaurar:
echo       restore_db.bat latest
echo       restore_db.bat daily\nombre_del_backup
echo.
pause
exit /b 0

:: ─── Restaurar ───
:do_restore
echo.
echo     ⚠️  Esto va a REEMPLAZAR la base de datos actual.
echo     Se hara una copia de seguridad previa.
echo.
echo     Presiona Ctrl+C para cancelar o cualquier tecla para continuar...
pause >nul

:: Hacer backup previo de la DB actual
if exist "%DB_PATH%" (
    for /f "tokens=2 delims=," %%a in ('powershell -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "PRETS=%%a"
    echo     Respaldando DB actual como %DB_PATH%.pre-restore.!PRETS!
    copy /y "%DB_PATH%" "%DB_PATH%.pre-restore.!PRETS!" >nul 2>&1
)

:: Si es .gz, descomprimir primero
set "RESTORE_SOURCE=%BACKUP_FILE%"
echo !BACKUP_FILE! | findstr /i ".gz" >nul
if !errorlevel! equ 0 (
    echo     Descomprimiendo backup...
    set "UNZIPPED=%TEMP%\azul_os_restore.db"
    :: Usar PowerShell para descomprimir gzip
    powershell -ExecutionPolicy Bypass -Command ^
      "try { $in = [System.IO.File]::OpenRead('%BACKUP_FILE%'); $gzip = New-Object System.IO.Compression.GZipStream($in, [System.IO.Compression.CompressionMode]::Decompress); $out = [System.IO.File]::Create('%UNZIPPED%'); $gzip.CopyTo($out); $gzip.Close(); $in.Close(); $out.Close(); Write-Host '    Descomprimido OK.' } catch { Write-Host '    ERROR al descomprimir: ' $_.Exception.Message; exit 1 }"
    if !errorlevel! neq 0 (
        echo     ERROR: No se pudo descomprimir el backup.
        pause
        exit /b 1
    )
    set "RESTORE_SOURCE=%UNZIPPED%"
)

:: Verificar integridad del backup antes de restaurar
echo     Verificando integridad...
set "CHECK_RESULT="
for /f "delims=" %%r in ('powershell -ExecutionPolicy Bypass -Command ^
  "python -c \"import sqlite3; conn=sqlite3.connect('%RESTORE_SOURCE%'); r=conn.execute('PRAGMA integrity_check').fetchone()[0]; print(r); conn.close()\" 2^>^&1"') do set "CHECK_RESULT=%%r"
if not "!CHECK_RESULT!"=="ok" (
    echo     ERROR: Backup corrupto — integrity_check: !CHECK_RESULT!
    pause
    exit /b 1
)
echo     Integridad OK.

:: Restaurar
echo     Restaurando...
copy /y "!RESTORE_SOURCE!" "%DB_PATH%" >nul 2>&1
if !errorlevel! neq 0 (
    echo     ERROR: No se pudo restaurar.
    pause
    exit /b 1
)

:: Limpiar temp si descomprimimos
if defined UNZIPPED del "!UNZIPPED!" 2>nul

echo.
echo     ╔══════════════════════════════════════════════════════════╗
echo     ║          RESTAURACION COMPLETADA                        ║
echo     ╚══════════════════════════════════════════════════════════╝
echo.
echo     DB restaurada desde: %BACKUP_FILE%
echo     La DB anterior quedo en: %DB_PATH%.pre-restore.!PRETS!
echo.
echo     Para iniciar Azul OS: doble-click en "Azul OS" en el Escritorio.
echo.
pause
exit /b 0