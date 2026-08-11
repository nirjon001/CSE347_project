import os

# ---------------------------------------------------------------------------
# SHARED CONNECTION SETTINGS (the same code runs in both places)
#
#   LOCAL (XAMPP, development):
#       No env vars set -> defaults below connect to the passwordless root
#       account of the local XAMPP MySQL/MariaDB at 127.0.0.1:3306.
#
#   WEB (Render + Aiven, deployed copy):
#       Render injects the real values via environment variables (DB_HOST,
#       DB_USER, DB_PASSWORD, DB_NAME, DB_PORT, DB_SSL_CA) so the defaults
#       below are overridden. DB_SSL_CA is the only web-only setting.
# ---------------------------------------------------------------------------
DB_CONFIG = {
    'host':     os.environ.get('DB_HOST', '127.0.0.1'),      # WEB: Aiven host | LOCAL: XAMPP
    'user':     os.environ.get('DB_USER', 'root'),            # WEB: avnadmin   | LOCAL: root
    'password': os.environ.get('DB_PASSWORD', ''),            # WEB: Aiven pwd  | LOCAL: empty
    'database': os.environ.get('DB_NAME', 'hostel_management'),
    'port':     int(os.environ.get('DB_PORT', '3306')),       # WEB: 27896      | LOCAL: 3306
    'charset':  'utf8mb4',
}

# ---- WEB ONLY: optional TLS (Aiven requires it) ---------------------------
# DB_SSL_CA is the path to the CA certificate (certs/aiven-ca.pem, public).
# Locally this env var is never set, so no TLS is used against XAMPP.
_ssl_ca = os.environ.get('DB_SSL_CA')
if _ssl_ca:
    DB_CONFIG['ssl_ca'] = _ssl_ca

# WEB: Render generates SECRET_KEY | LOCAL: falls back to the hardcoded default.
SECRET_KEY = os.environ.get('SECRET_KEY', 'cse347-hostel-management-secret-key')
