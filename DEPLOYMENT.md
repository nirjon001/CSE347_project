# 🌐 Deploy to the Web (free)

The **same code** runs locally *and* as a free web copy. The database settings are read from environment variables, so only *where MySQL lives* changes — not the code.

> **Live site**: [https://hostel-management-368b.onrender.com/](https://hostel-management-368b.onrender.com/) — a free Render web service backed by a free Aiven MySQL database.

---

## 🏗️ Architecture

```
┌───────────────────┐          ┌──────────────────────────────────────────┐
│  LOCAL (your PC)  │          │  WEB (free hosting)                      │
│                   │          │                                          │
│  Flask app        │          │  Render web service  ── TLS ── Aiven     │
│  └─ config.py     │          │  (gunicorn app:app)   ────────  MySQL 8  │
│       │           │          │        │                     (1 GB free) │
│       ▼           │          │        └─ DB_HOST / DB_* env vars ──┘    │
│  XAMPP MariaDB    │          │                                          │
│  (127.0.0.1:3306) │          │  Data sync via scripts\sync_web_db.bat   │
└─────────┬─────────┘          └──────────────────────────────────────────┘
          │                                                               |
          └── push/pull ──────────────────────────────────────────────────┘
```

- **Local copy** — XAMPP MySQL at `127.0.0.1` (unchanged).
- **Web copy** — hosted on **Render** (free web service) backed by a **free external MySQL**. Recommended host: **Aiven free MySQL** (current MySQL 8, always-free, 1 GB, no credit card, remote access over TLS). Other free MySQL hosts tend to be unusable for this project — freesqldatabase.com runs ancient MySQL 5.5 (the schema's triggers / `CURRENT_TIMESTAMP` defaults can't import) and db4free.net's domain has been hijacked. **Do not use either.**
- **Data sync** — `scripts\init_web_db.bat` imports the schema + seed once; `scripts\sync_web_db.bat` copies data either way on demand. Both delegate to `scripts\web_db.py`, which uses **mysql-connector-python** (already a project dependency) because XAMPP's MariaDB client can't authenticate to MySQL 8 hosts (they use the `caching_sha2_password` plugin).

---

## 🔧 One-time setup

### 1. Create the web database on Aiven (aiven.io)

1. Sign up (GitHub/Google account works, **no credit card**), then **Create a service** → **MySQL** → the **free** plan → pick a region → create.
2. Open the service, click **Create database** and name it **`hostel_management`**.
3. Copy the connection details: **host**, **port**, **user**, **password**.
4. Download the **CA certificate** (Service settings → CA Certificate) and save it as **`certs\aiven-ca.pem`** inside this project folder. This file is public and committed to the repo.

> **TLS note**: Aiven requires encrypted connections. The app and scripts pick this up from `DB_SSL_CA` (the path is relative to the repo root). If you ever use a host that doesn't need TLS, leave `DB_SSL_CA` blank.

### 2. Fill in the credentials

Copy `scripts\.web-db.env.example` → `scripts\.web-db.env` and edit it (the real file is **git-ignored**, so the password never reaches the repo):

```
DB_HOST=mysql-XXXXXXXXXXXXXXXX.g.aivencloud.com   # your Aiven host
DB_PORT=27896                                     # Aiven's port (NOT 3306)
DB_USER=avnadmin
DB_PASSWORD=YourPasswordHere
DB_NAME=hostel_management
DB_SSL_CA=certs/aiven-ca.pem
DB_STRIP_USING=1                                  # import without CREATE DATABASE
```

### 3. Import schema + seed once

Uses `mysql-connector-python` (already in `requirements.txt`). It creates the `hostel_management` database on Aiven and imports the **18 tables + 3 triggers + seed data**:

```
scripts\init_web_db.bat
```

### 4. Deploy to Render

1. Push this repo to GitHub (auto-deploys on push to `main` via `render.yaml`).
2. On render.com choose **New → Blueprint** and select the repo. `render.yaml` configures the free web service automatically (`gunicorn app:app --timeout 60`).
3. In the service's **Environment** tab, set the variables (these are the values Render uses to reach your Aiven DB):

| Variable        | Value |
|-----------------|-------|
| `DB_HOST`       | your Aiven host, e.g. `mysql-382080f8-XXXX.g.aivencloud.com` |
| `DB_PORT`       | your Aiven port, e.g. `27896` (**not** 3306) |
| `DB_USER`       | `avnadmin` |
| `DB_PASSWORD`   | your Aiven password |
| `DB_NAME`       | `hostel_management` |
| `DB_SSL_CA`     | `certs/aiven-ca.pem` |
| `SECRET_KEY`    | Render generates one by default (set your own if you prefer) |

4. Click **Manual Deploy → Deploy latest commit**. The site goes live at `https://hostel-management-368b.onrender.com`.

---

## 🔄 Sync data between local and web

```
scripts\sync_web_db.bat push   # local -> web (upload your data)
scripts\sync_web_db.bat pull   # web   -> local (download the web data)
```

`push` dumps your local XAMPP DB and imports it into the web DB; `pull` is the reverse. Both read `scripts\.web-db.env`.

---

## 🩺 Deploy troubleshooting

| Symptom | What's really happening | Fix |
|---|---|---|
| `/healthz` returns **500** but the site works locally | Render's Environment tab is missing or has empty `DB_*` variables | Fill the Environment tab with your real Aiven values (step 4) and **Manual Deploy → Deploy latest commit**. |
| Crash loop in Render logs: `WORKER TIMEOUT` repeats | A worker thread hung on a **dead DB socket** (Aiven free DB drops idle connections; `recv` blocks forever) | **Already fixed** — the app sets 15-second socket timeouts in `db.py` and runs the auto-absent backfill in a background thread, and `render.yaml` uses `--timeout 60`. If it ever returns, open **Render → Logs** and check the traceback. |
| First load after idle is very slow (30–60 s) | Render's free instance **slept** | Not an error — wait for the cold start. Add UptimeRobot (ping `/healthz`) or add a billing method to keep it warm. |
| The database stops responding after a long idle | Aiven's free MySQL **powers itself off** when inactive | Wake it from the Aiven console before a demo (takes about a minute). |
| Data on the web looks old/empty | The web DB wasn't synced | Run `scripts\sync_web_db.bat push` after significant local changes. |
| `init_web_db.bat` fails with a privileges error | The host restricts `CREATE DATABASE` or `CREATE TRIGGER` | Keep `DB_STRIP_USING=1` and use a host that allows triggers (Aiven does). |
| Browser blocks geolocation on the deployed site | Geolocation requires HTTPS; free Render services already serve HTTPS, but the browser may need the URL to be exactly `https://…` (no `http://`) | Always open the site via the `https://` link. `localhost` always works for local testing. |

---

## 🧾 Free-tier notes

- Render's free web service **sleeps** when idle and **expires after ~30 days** unless you add a billing method.
- Aiven's free MySQL **powers itself off** after a period of inactivity — wake it from the Aiven console (takes a minute).
- The web DB uses the **same schema + 3 triggers** as local (verified via `web_db.py`'s trigger-aware SQL importer).
- The app exposes `GET /healthz` (returns `ok`) for uptime monitors such as UptimeRobot.
