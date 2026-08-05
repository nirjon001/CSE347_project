@echo off
REM =====================================================================
REM  init_web_db.bat -- one-time import of schema + seed data into the
REM  FREE web database (Aiven MySQL 8 over TLS).
REM
REM  Reads scripts\.web-db.env (copy from .web-db.env.example first).
REM  Delegates to scripts\web_db.py, which uses mysql-connector-python
REM  (the app's own driver) because XAMPP's MariaDB client cannot talk
REM  to MySQL 8 hosts that use caching_sha2_password.
REM =====================================================================
setlocal
cd /d "%~dp0"
python web_db.py init %*
exit /b %errorlevel%
