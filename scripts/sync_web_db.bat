@echo off
REM =====================================================================
REM  sync_web_db.bat -- copy data between the LOCAL XAMPP database and the
REM  FREE web database (Aiven MySQL 8 over TLS).
REM
REM  Usage:
REM    sync_web_db.bat push   -> local -> web  (upload your local data)
REM    sync_web_db.bat pull   -> web   -> local (download the web data)
REM
REM  Reads scripts\.web-db.env (copy from .web-db.env.example first).
REM  Delegates to scripts\web_db.py. The web side uses mysql-connector-python
REM  (XAMPP's MariaDB client cannot do caching_sha2_password auth).
REM =====================================================================
setlocal
cd /d "%~dp0"
set "MODE=%~1"
if /i "%MODE%"=="push" goto :run
if /i "%MODE%"=="pull" goto :run
echo Usage: sync_web_db.bat push ^| pull
exit /b 1
:run
python web_db.py %MODE%
exit /b %errorlevel%
