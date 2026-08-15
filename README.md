<div align="center">

# 🏨 HOSTEL MANAGEMENT SYSTEM

### *CSE347 — Information System Analysis & Design*

### 🔥 **Role-based · Geo-fenced · Analytics-driven** 🔥

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![MySQL](https://img.shields.io/badge/MySQL%2FMariaDB-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://www.mysql.com)
[![Render](https://img.shields.io/badge/Host-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://render.com)
[![Chart.js](https://img.shields.io/badge/Charts-Chart.js-FF6384?style=for-the-badge&logo=chartdotjs&logoColor=white)](https://www.chartjs.org)
![Security](https://img.shields.io/badge/Security-%E2%9C%93%20Parameterized-2ea44f?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-%E2%9C%93%20LIVE-00C853?style=for-the-badge)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

## 🌐 **LIVE DEMO**

### [🚀 https://hostel-management-368b.onrender.com/ 🚀](https://hostel-management-368b.onrender.com/)

**Sign in with any demo account below 👇**

</div>

---

## ✨ Feature Showcase

<table>
<tr>
<td width="50%">

### 👑 Manager
- 📋 Register / delete students, allocate rooms
- 🏠 Add hostels (🗺️ map-pin GPS) & rooms with custom beds
- 💰 **Generate multiple invoices at once** (rent / electricity / food / water / other)
- 🧾 Expandable per-student bill list + **Print statements**
- 📈 Dashboard analytics — today's donut + 14-day trend charts
- 🔍 Per-person attendance View/Edit with own charts
- 📣 Send notices · 🚫 Record/resolve violations · 🍲 Update mess menu
- 🗂️ Approve mess-off · 📬 Track all parcels & visitors

</td>
<td width="50%">

### 🧑‍🎓 Student & 🛡️ Staff
- 🛏️ View profile, room & hostel info
- 📝 Submit complaints & track status
- 🧾 View invoices (paid/unpaid totals, **Print**)
- 📬 One-click **parcel self-collection** with full audit trail
- 🚶 Record **in/out** attendance
- 📍 **Geo-fenced attendance** — mark Present only inside hostel GPS radius
- 📊 Personal stats + donut/trend charts
- 🛡️ Staff: register visitors, receive parcels, mark student returns

</td>
</tr>
</table>

### 🌟 Highlights

| | Feature | Why it's cool |
|---|---|---|
| 🚨 | **Geo-fenced attendance** | Browser GPS + Leaflet/OpenStreetMap — zero paid API keys, live position + accuracy ring + inside/outside check |
| 🤖 | **Auto absent-day backfill** | Background job fills missing `Absent` days automatically — history is always complete |
| 🎨 | **AJAX actions** | Invoice/status/attendance/parcel actions update in place — **no page reloads** |
| 📱 | **Fully responsive** | Mobile slide-in sidebar, fluid charts, unified map sizes |
| 🔔 | **Smart notifications** | Unread bell badge + filter chips (All / Unread / by category) |
| ♀️ | **Gender-separated hostels** | DB-level trigger refuses opposite-gender allocations |
| 🔒 | **Security-first** | scrypt hashing, parameterized SQL, role-guarded routes, strict SQL mode |

---

## 🛠️ Tech Stack

<div align="center">

| Layer | Technology |
|:---:|:---:|
| 🧠 **Backend** | **Python 3** + **Flask** (Jinja2 server-rendered) |
| 🗄️ **Database** | **MySQL / MariaDB** — 18 tables + 3 triggers |
| 🎨 **Frontend** | HTML · CSS · vanilla JS · **Chart.js** |
| ☁️ **Deployment** | **Render** (web) + **Aiven** (free MySQL over TLS) |

</div>

---

## 🚀 Getting Started

### 📋 1. Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| 🐍 **Python** | 3.10+ (tested on 3.14) | Includes `pip` |
| 🗄️ **XAMPP** (or any MySQL/MariaDB) | MariaDB 10.4+ | XAMPP = MySQL + phpMyAdmin, easiest on Windows |
| 🔧 **Git** *(optional)* | any | Only needed to clone |

### 🟢 2. Start MySQL

Open **XAMPP Control Panel** → press **Start** next to **MySQL** → wait for green. It must listen on port **3306**.

### 🗃️ 3. Load the database

<details>
<summary><b>Option A — phpMyAdmin (easiest) 👈</b></summary>

1. Open `http://localhost/phpmyadmin`
2. **Import** → select `hostel_management_schema.sql` → **Go** (creates DB + 18 tables)
3. Import `seed_data.sql` the same way (demo accounts & records)

> **Already on an old version?** Run `migrations.sql` — it upgrades in place, is idempotent (safe to re-run), and never wipes data.

</details>

<details>
<summary><b>Option B — command line</b></summary>

```bash
"C:\xampp\mysql\bin\mysql.exe" -u root < hostel_management_schema.sql
"C:\xampp\mysql\bin\mysql.exe" -u root < seed_data.sql
```

</details>

### 📦 4. Install dependencies

```bash
pip install -r requirements.txt
```

Installs **Flask**, **mysql-connector-python**, and **gunicorn** (the deployed web server).

### ⚙️ 5. Database settings *(only if your MySQL has a password)*

`config.py` reads env vars and falls back to XAMPP defaults (`root` / no password / port 3306), so usually **nothing to change**. Passworded root? Set `DB_PASSWORD` in your environment or edit the default:

```python
import os
DB_CONFIG = {
    'host':     os.environ.get('DB_HOST', '127.0.0.1'),
    'user':     os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),   # set this for a passworded root
    'database': os.environ.get('DB_NAME', 'hostel_management'),
    'port':     int(os.environ.get('DB_PORT', '3306')),
    'charset':  'utf8mb4',
}
```

### ▶️ 6. Run it

```bash
python app.py
```

Open **http://127.0.0.1:5000** 🎉 and log in with any demo account.

### ✅ 7. Verify

- 👑 Manager dashboard → student/room/complaint counts + attendance analytics
- ➕ **Register Student** → 🛏️ **Allocate Room**
- 🏠 **Add Hostel** (gender + coords) → ➕ **Add Room** → allocate (opposite-gender refused)
- 🚫 **Violations → Record** (with notify) · 🍲 **Mess Off → Approve/Reject**
- 🔔 Click the bell — unread count reflects your notices
- 🧑🎓 Log in as **student1** → complaints, invoices, parcels (**Collect**), geo-fenced **Attendance**
- 🛡️ Log in as **staff1** → register a visitor, receive a parcel, mark a student returned

---

## 👥 Demo Accounts

<div align="center">

| 👤 Username | 🔑 Password | 🎭 Role |
|:---:|:---:|:---:|
| `manager` | `admin123` | 👑 **Manager** — Ayesha Rahman |
| `staff1` | `staff123` | 🛡️ Staff — Karim Mia (Caretaker) |
| `staff2` | `staff123` | 🛡️ Staff — Rashida Begum (Cook) |
| `staff3` | `staff123` | 🛡️ Staff — Hanif Uddin (Guard) |
| `student1` | `student123` | 🧑🎓 Student — Jakir Hossain (room 101) |
| `student2` | `student123` | 🧑🎓 Student — Moin Uddin (room 101) |
| `student3` | `student123` | 🧑🎓 Student — Abdullah Al Mamun (room 101) |
| `student4` | `student123` | 🧑🎓 Student — Iftekhar Alam (room 101) |
| `student5` | `student123` | 🧑🎓 Student — Rakib Uddin (room 102) |
| `student6` … `student50` | `student123` | 🧑🎓 50 students · 2.5 months of attendance |

</div>

---

## 🌐 Live Website & Deployment

The **same code** runs locally *and* on the free web copy:

> 🟢 **https://hostel-management-368b.onrender.com/** — Render web service + Aiven free MySQL (TLS)

`GET /healthz` returns `ok` for uptime monitors (UptimeRobot). The full guide — architecture, Aiven + Render setup, the `scripts\.web-db.env` credentials file, and `sync_web_db.bat push/pull` — lives in **[`DEPLOYMENT.md`](DEPLOYMENT.md)**.

---

## 🐛 Troubleshooting

### 💻 Local development

| 🚨 Problem | ✅ Fix |
|---|---|
| `mysql: command not found` | Not on PATH (normal for XAMPP) → use phpMyAdmin or the full path `C:\xampp\mysql\bin\mysql.exe` |
| `Access denied for user 'root'` | Root has a password → set it in `config.py` (step 5) |
| Port 3306 won't start | Another MySQL is using it → stop it, or change the port in XAMPP **and** `config.py` |
| `No module named 'flask'` | Run `pip install -r requirements.txt`; for multiple Pythons use `py -m pip install -r requirements.txt` |
| `Address already in use` | Another `python app.py` is running or port 5000 is busy |
| Login always fails | `seed_data.sql` not imported → re-run it |
| `hostel_management` not found | Schema not imported → re-run `hostel_management_schema.sql` |
| Attendance says "outside the area" | GPS is beyond the hostel's `radius_m` from its `lat`/`lng`; on a deployed server geolocation needs HTTPS |
| `init_web_db.bat` privileges error | Host restricts `CREATE DATABASE`/`CREATE TRIGGER` → keep `DB_STRIP_USING=1`, use a trigger-friendly host (Aiven) |

### ☁️ Live website

| 🚨 Symptom | 🤔 Reality | ✅ Fix |
|---|---|---|
| First click after idle takes 30–60 s | Render free instance **slept** | Not an error — wait. UptimeRobot or a billing method keeps it warm |
| Crash loop (`WORKER TIMEOUT` repeating) | Worker hung on a dead DB socket | **Already fixed** — background backfill thread + 15 s socket timeouts (`db.py`) + `--timeout 60` |
| `/healthz` → **500** | Render Environment tab missing `DB_*` vars | Fill with real Aiven values → **Manual Deploy → Deploy latest commit** |
| Data looks old/empty on the web | Web DB not synced | Run `scripts\sync_web_db.bat push` after local changes |
| DB stops responding after idle | Aiven free MySQL **powers off** | Wake it in the Aiven console (~1 min) |

---

## 📂 Project Structure

```
CSE347_project/
│
├── 🧠 app.py                        # Flask app — all routes for the 3 roles + auto-absent backfill thread
├── ⚙️ config.py                     # DB settings from env vars (falls back to local XAMPP defaults)
├── 🗄️ db.py                         # Parameterized query/execute helpers + safe socket timeouts
├── 📦 requirements.txt              # Python deps (Flask, mysql-connector-python, gunicorn)
├── ☁️ render.yaml                   # Render Blueprint — free web deploy (gunicorn app:app)
│
├── 🗃️ hostel_management_schema.sql  # Fresh schema: 18 tables + 3 triggers (no data)
├── 🔁 migrations.sql                # Idempotent upgrade for older databases (safe to re-run)
├── 🌱 seed_data.sql                 # Demo data — 50 students, 2.5 months of attendance, etc.
│
├── 🖼️ templates/                    # Jinja2 pages
│   ├── base.html                    #   shared layout (role sidebar, bell, mobile hamburger)
│   ├── auth/                        #   login, change password
│   ├── manager/                     #   manager dashboards & forms
│   ├── student/                     #   student pages
│   └── staff/                       #   staff pages
│
├── 🎨 static/                       # Frontend assets
│   ├── css/style.css                #   single stylesheet (responsive, print styles)
│   └── js/main.js                   #   AJAX actions, confirm dialogs, toggles
│
├── 🛠️ scripts/                      # Development & deploy helpers
│   ├── generate_seed.py             #   regenerates seed_data.sql deterministically
│   ├── web_db.py                    #   Python CLI: init / drop / push / pull the web DB
│   ├── init_web_db.bat              #   one-time import of schema + seed into the web DB
│   ├── sync_web_db.bat              #   push / pull data between local and web DBs
│   ├── .web-db.env.example          #   credentials template (copy to .web-db.env)
│   └── .web-db.env                  #   ⚠️ REAL credentials — git-ignored, never committed
│
├── 🔐 certs/
│   └── aiven-ca.pem                 # Public TLS CA cert for the Aiven web DB (committed)
│
├── 📊 svg/
│   └── class_diagram.svg            # UML class diagram (18 classes, attributes + methods)
│
├── 📖 README.md                     # ⭐ You are here
├── ☁️ DEPLOYMENT.md                 # Full web-deployment guide (Render + Aiven + sync)
├── 📄 report.md                     # Code walkthrough — request flow, routes, class mapping, security
├── 📄 Requirements Definition.pdf   # Functional & non-functional requirements (course deliverable)
├── 📄 Requirements Definition v2.docx   # Renewed requirements (current v4 system)
├── 📄 Feasibility-Analysis-v2.docx  # Renewed feasibility (Taka costs + PERT schedule)
├── 📝 AGENTS .md                    # Project memory / changelog for developers
└── 📜 LICENSE                       # MIT license
```

---

## 📚 Documentation

| 📄 Doc | 📖 What it covers |
|---|---|
| [☁️ `DEPLOYMENT.md`](DEPLOYMENT.md) | Full free-web deployment — Render + Aiven + data sync + deploy troubleshooting |
| [📄 `report.md`](report.md) | Request flow, every route, class-diagram mapping, security measures |
| [📊 `svg/class_diagram.svg`](svg/class_diagram.svg) | UML class diagram — 18 classes, attributes & methods |
| [📄 `Requirements Definition.pdf`](Requirements%20Definition.pdf) | Functional & non-functional requirements (course deliverable) |
| [📄 `Requirements Definition v2.docx`](Requirements%20Definition%20v2.docx) | Renewed requirements matching the current v4 system |
| [📄 `Feasibility-Analysis-v2.docx`](Feasibility-Analysis-v2.docx) | Renewed feasibility — Taka cost breakdown + PERT schedule |
| [📜 `LICENSE`](LICENSE) | MIT license — free to use, copy, modify |

---

<div align="center">

## 🙏 Thank You for Exploring!

**Made with 💚 for CSE347 — Information System Analysis & Design**

[⬆️ Back to top](#-hostel-management-system)

</div>
