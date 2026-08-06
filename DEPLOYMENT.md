# Deploy to the Web (free)

The **same code** runs locally *and* as a free web copy. The database settings are read from environment variables, so only *where MySQL lives* changes — not the code.

> **Live site**: https://hostel-management-368b.onrender.com/

## Architecture

- **Local copy** — XAMPP MySQL at `127.0.0.1` (unchanged).
- **Web copy** — hosted on **Render** (free web service) backed by a **free external MySQL**. Recommended host: **Aiven free MySQL** (current MySQL 8, always-free, 1 GB, no credit card, remote access over TLS). Other free MySQL hosts tend to be unusable for this project — freesqldatabase.com runs ancient MySQL 5.5 (the schema's triggers/`CURRENT_TIMESTAMP` defaults can't import) and db4free.net's domain has been hijacked.
- **Data sync** — `scripts\init_web_db.bat` imports the schema + seed once; `scripts\sync_web_db.bat` copies data either way on demand. Both delegate to `scripts\web_db.py`, which uses **mysql-connector-python** (already a project dependency) because XAMPP's MariaDB client can't authenticate to MySQL 8 hosts (they use the `caching_sha2_password` plugin).

## One-time setup

1. **Create the web database on Aiven** (aiven.io):
   - Sign up (GitHub/Google account works, **no credit card**), then **Create a service** → **MySQL** → the **free** plan → pick a region → create.
   - Open the service, click **Create database** and name it **`hostel_management`**.
   - Copy the connection details: **host**, **port**, **user**, **password**. Also download the **CA certificate** (Service settings → CA Certificate) and save it as **`certs\aiven-ca.pem`** inside this project folder.
2. **Fill in the credentials** — copy `scripts\.web-db.env.example` → `scripts\.web-db.env` and edit it (the real file is git-ignored): set `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME=hostel_management`, `DB_SSL_CA=certs\aiven-ca.pem`, and keep `DB_STRIP_USING=1` (imports into your Aiven database without needing `CREATE DATABASE`).
3. **Import schema + seed once** (uses `mysql-connector-python` from `pip install -r requirements.txt`; it creates `hostel_management` on Aiven and imports the 18 tables + 3 triggers + seed data):
   ```
   scripts\init_web_db.bat
   ```
4. **Deploy to Render** — push this repo to GitHub, then on render.com choose **New → Blueprint** and select the repo. `render.yaml` configures the free web service automatically (`gunicorn app:app`). In the service's **Environment** tab set `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_PORT` (Aiven's port isn't 3306 — use the real one) and `SECRET_KEY` (Render generates one by default). The site goes live at `https://hostel-management-368b.onrender.com`.

> **TLS note**: Aiven requires encrypted connections. The app and scripts pick this up from `DB_SSL_CA` (the CA certificate is public, so it's committed with the repo). If you use a different host that doesn't need TLS, leave `DB_SSL_CA` blank.

## Sync data between local and web

```
scripts\sync_web_db.bat push   # local -> web (upload your data)
scripts\sync_web_db.bat pull   # web   -> local (download the web data)
```

`push` dumps your local XAMPP DB and imports it into the web DB; `pull` is the reverse. Both read `scripts\.web-db.env`.

> **Free-tier notes**: Render's free web service sleeps when idle and expires after ~30 days unless you add a billing method. Aiven's free MySQL powers itself off after a period of inactivity — wake it from the Aiven console before a demo (takes a minute). The web DB uses the same schema + 3 triggers as local. The web app exposes a `GET /healthz` health-check endpoint (returns `ok`) for uptime monitors such as UptimeRobot.
