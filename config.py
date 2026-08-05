import os

# Local development uses XAMPP's MySQL at 127.0.0.1 with a passwordless root.
# On the deployed (web) copy these come from Render's environment variables,
# so the exact same code runs in both places.
DB_CONFIG = {
    'host':     os.environ.get('DB_HOST', '127.0.0.1'),
    'user':     os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'hostel_management'),
    'port':     int(os.environ.get('DB_PORT', '3306')),
    'charset':  'utf8mb4',
}

# Optional TLS for hosts that require it (e.g. Aiven's free MySQL).
# DB_SSL_CA is the path to the CA certificate file (public, safe to commit).
_ssl_ca = os.environ.get('DB_SSL_CA')
if _ssl_ca:
    DB_CONFIG['ssl_ca'] = _ssl_ca

SECRET_KEY = os.environ.get('SECRET_KEY', 'cse347-hostel-management-secret-key')
