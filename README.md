# CSE347 — Hostel Management System

A web-based hostel management system built for **CSE347: Information System Analysis & Design** (3rd year, 3rd semester).

## Features

- **Role-based login** — separate dashboards for Manager, Student, and Staff (Flask sessions + hashed passwords)
- **Gender-separated hostels** — each hostel is Male or Female; room allocation (and the database) refuses to place a student in an opposite-gender hostel
- **Notification system** — a bell with an unread-count badge and a full notification page; students/staff get automatic alerts (complaint updates, new invoices, parcel arrivals, visitor arrivals, violation notices, mess-off decisions) and managers can send free-text notices
- **Geo-fenced attendance** — students and staff mark "Present" only from inside their hostel's GPS radius (browser location + Leaflet/OpenStreetMap, no paid API keys). Managers set the hostel's location by dropping a pin on a map or typing coordinates, and the map shows your live position with an accuracy estimate (how close ± the fix is) and an inside/outside check
- **Student parcel self-collection** — staff receive parcels (auto-notifying the student); students pick them up with one click, and every parcel keeps an audit trail (who received it, who collected it, when)
- **Manager**: register/delete students, allocate rooms, add/edit/delete hostels (map pin or typed coordinates; duplicate addresses are rejected) & add rooms with custom bed capacity, view each room's occupants, manage complaints & invoices (**generate several bills at once** — room rent / electricity / food / water / other — with a summary-by-type section, a per-student **expandable bill list** with totals, a **Print statement** per student showing their invoice count + total value, and per-invoice **Print** physical copies), record attendance, update the mess menu, record & resolve violations (tabbed page: record / send notice / browse all with Open-Resolved filters and per-row notify), view student feedback, approve/reject mess-off requests, view all parcels, view visitor logs, manage & delete staff
- **Student**: view profile & room, submit complaints, view invoices (total / paid / unpaid summary with View-Print for a physical copy), apply mess-off, give feedback, record in/out, check & collect parcels (who received them, when collected), mark attendance
- **Staff**: register visitors at the front desk, receive parcels (notifies the student), record student returns, record own (geo-fenced) attendance
- **Security**: scrypt password hashing, parameterized SQL (SQL-injection safe), role-guarded routes, strict SQL mode so invalid data is rejected

## Tech Stack

- **Backend**: Python 3 + Flask (server-rendered Jinja2 templates)
- **Database**: MySQL / MariaDB (schema in `hostel_management_schema.sql`)
- **Frontend**: HTML + CSS (single small JS file)

## Getting Started

### 1. Prerequisites

A teammate needs exactly these three things installed before running the project:

| Requirement | Version | Notes |
|---|---|---|
| **Python** | 3.10+ (tested on 3.14) | Includes `pip` |
| **XAMPP** (or any MySQL/MariaDB server) | MariaDB 10.4+ | XAMPP bundles MySQL + phpMyAdmin — easiest option on Windows |
| **Git** (optional) | any recent | Only needed to clone the repo |

### 2. Start MySQL

Open the **XAMPP Control Panel** and press **Start** next to **MySQL**. Wait until the row turns green. (It must listen on port **3306** — the app expects that.)

### 3. Load the database

The app needs the schema plus some demo data. There are two ways — pick one.

**Option A — phpMyAdmin (easiest):**
1. Open `http://localhost/phpmyadmin`
2. Click **Import** → **Choose File**
3. Select `hostel_management_schema.sql` → **Go** (creates the `hostel_management` database + all 18 tables)
4. Import `seed_data.sql` the same way (adds demo accounts & records)

> **Already used the old version?** Run `migrations.sql` instead of re-importing the schema — it adds the new columns/tables/foreign keys/triggers without wiping your data. It is safe to run any time (it skips anything that already exists, so re-running causes no errors).

**Option B — command line:**

If the `mysql` command is on your PATH (it is *not* by default with XAMPP — use the full path below or Option A):
```
"C:\xampp\mysql\bin\mysql.exe" -u root < hostel_management_schema.sql
"C:\xampp\mysql\bin\mysql.exe" -u root < seed_data.sql
```

### 4. Install Python dependencies

```
pip install -r requirements.txt
```

This installs **Flask**, **mysql-connector-python**, and **gunicorn** (the web server used on the deployed copy).

### 5. Check the database settings (only if your MySQL uses a password)

`config.py` reads every setting from an environment variable and falls back to XAMPP's defaults. With no variables set it behaves exactly as before — XAMPP's MySQL `root` user has an **empty password**, so nothing needs to change. If your MySQL root has a password, either set `DB_PASSWORD` in your environment or edit the default here:

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

### 6. Run the app

```
python app.py
```

You should see `Running on http://127.0.0.1:5000`. Open that URL in a browser and log in with any demo account below.

### 7. Verify it works

- Log in as **manager** — you should see the Manager dashboard with student/room/complaint counts.
- Try **Register Student** → then **Allocate Room** to that student.
- Try **Add Hostel** (with gender + location coords) then **Add Room** with a custom capacity, and allocate a student into it (opposite-gender rooms are hidden/refused).
- Try **Violations → Record** with the notify checkbox, **Mess Off → Approve/Reject**, and open **Feedback** / **Parcels** views.
- Click the **bell (Notifications)** in the sidebar — the unread count should reflect the notices above.
- Log in as **student1** to see the student side (complaints, invoices, mess menu, parcels with a **Collect** button, geo-fenced **Attendance**).
- Log in as **staff1** to register a visitor, receive a parcel, and mark a student as returned.

## Demo Accounts

| Username   | Password   | Role    |
|------------|------------|---------|
| `manager`  | `admin123` | Manager (Ayesha Rahman) |
| `staff1`   | `staff123` | Staff — Caretaker (Karim Mia) |
| `staff2`   | `staff123` | Staff — Cook (Rashida Begum) |
| `staff3`   | `staff123` | Staff — Guard (Hanif Uddin) |
| `student1` | `student123` | Student — Rafi (room 101) |
| `student2` | `student123` | Student — Sadia (no room) |
| `student3` | `student123` | Student — Tanvir (room 201) |
| `student4` | `student123` | Student — Nusrat (room 301) |
| `student5` | `student123` | Student — Mehedi (no room) |

## Deploy to the Web (free)

The **same code** runs locally *and* as a free web copy. The database settings are read from environment variables, so only *where MySQL lives* changes — not the code.

### Architecture

- **Local copy** — XAMPP MySQL at `127.0.0.1` (unchanged).
- **Web copy** — hosted on **Render** (free web service) backed by a **free external MySQL**. Recommended host: **Aiven free MySQL** (current MySQL 8, always-free, 1 GB, no credit card, remote access over TLS). Other free MySQL hosts tend to be unusable for this project — freesqldatabase.com runs ancient MySQL 5.5 (the schema's triggers/`CURRENT_TIMESTAMP` defaults can't import) and db4free.net's domain has been hijacked.
- **Data sync** — `scripts\init_web_db.bat` imports the schema + seed once; `scripts\sync_web_db.bat` copies data either way on demand. Both delegate to `scripts\web_db.py`, which uses **mysql-connector-python** (already a project dependency) because XAMPP's MariaDB client can't authenticate to MySQL 8 hosts (they use the `caching_sha2_password` plugin).

### One-time setup

1. **Create the web database on Aiven** (aiven.io):
   - Sign up (GitHub/Google account works, **no credit card**), then **Create a service** → **MySQL** → the **free** plan → pick a region → create.
   - Open the service, click **Create database** and name it **`hostel_management`**.
   - Copy the connection details: **host**, **port**, **user**, **password**. Also download the **CA certificate** (Service settings → CA Certificate) and save it as **`certs\aiven-ca.pem`** inside this project folder.
2. **Fill in the credentials** — copy `scripts\.web-db.env.example` → `scripts\.web-db.env` and edit it (the real file is git-ignored): set `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME=hostel_management`, `DB_SSL_CA=certs\aiven-ca.pem`, and keep `DB_STRIP_USING=1` (imports into your Aiven database without needing `CREATE DATABASE`).
3. **Import schema + seed once** (uses `mysql-connector-python` from step 4's `pip install`; it creates `hostel_management` on Aiven and imports the 18 tables + 3 triggers + seed data):
   ```
   scripts\init_web_db.bat
   ```
4. **Deploy to Render** — push this repo to GitHub, then on render.com choose **New → Blueprint** and select the repo. `render.yaml` configures the free web service automatically (`gunicorn app:app`). In the service's **Environment** tab set `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_PORT` (Aiven's port isn't 3306 — use the real one) and `SECRET_KEY` (Render generates one by default). The site goes live at `https://hostel-management.onrender.com`.

> **TLS note**: Aiven requires encrypted connections. The app and scripts pick this up from `DB_SSL_CA` (the CA certificate is public, so it's committed with the repo). If you use a different host that doesn't need TLS, leave `DB_SSL_CA` blank.

### Sync data between local and web

```
scripts\sync_web_db.bat push   # local -> web (upload your data)
scripts\sync_web_db.bat pull   # web   -> local (download the web data)
```

`push` dumps your local XAMPP DB and imports it into the web DB; `pull` is the reverse. Both read `scripts\.web-db.env`.

> **Free-tier notes**: Render's free web service sleeps when idle and expires after ~30 days unless you add a billing method. Aiven's free MySQL powers itself off after a period of inactivity — wake it from the Aiven console before a demo (takes a minute). The web DB uses the same schema + 3 triggers as local.

## Troubleshooting

| Problem | Fix |
|---|---|
| `mysql: command not found` | MySQL isn't on PATH (normal for XAMPP). Use phpMyAdmin (Option A) or the full path `C:\xampp\mysql\bin\mysql.exe`. |
| `Access denied for user 'root'` | Your MySQL root has a password. Put it in `config.py` (step 5). |
| Port 3306 won't start in XAMPP | Something else is using the port (e.g. another MySQL). In XAMPP, stop the other service, or change the port in XAMPP → Config and in `config.py`. |
| `ModuleNotFoundError: No module named 'flask'` | Run `pip install -r requirements.txt` (step 4). If you have multiple Python versions, use `py -m pip install -r requirements.txt`. |
| `Address already in use` when running the app | Another `python app.py` is already running, or port 5000 is busy. Stop it, or run `python app.py` on another port. |
| Pages load but login always fails | The seed data wasn't imported. Re-run `seed_data.sql` (step 3). |
| Database `hostel_management` not found | The schema wasn't imported. Re-run `hostel_management_schema.sql` (step 3). |
| Attendance says "outside the area" | The browser's GPS is farther than the hostel's `radius_m` from its `lat`/`lng`. On a deployed server the browser may block geolocation unless the site is HTTPS — `localhost` always works. |
| `scripts\init_web_db.bat` fails with a privileges error | The free host restricts `CREATE DATABASE` or `CREATE TRIGGER`. Keep `DB_STRIP_USING=1` and use a host that allows triggers (Aiven does). |

## Project Structure

```
CSE347_project/
│
├── app.py                          # Flask app: all routes (auth, manager, student, staff)
├── config.py                       # DB connection + secret key (env-var driven, XAMPP defaults)
├── db.py                           # Parameterized query/execute helpers
├── requirements.txt                # Python dependencies
├── render.yaml                     # Render Blueprint (free web service, gunicorn app:app)
│
├── scripts/                        # Web-deploy helpers (read scripts\.web-db.env)
│   ├── web_db.py                   #   Python CLI: init (import schema+seed), drop, push, pull
│   ├── init_web_db.bat             #   wrapper -> web_db.py init
│   ├── sync_web_db.bat             #   wrapper -> web_db.py push / pull
│   └── .web-db.env.example         #   credentials template (real file is git-ignored)
│
├── certs/                          # TLS CA certificate for the web DB (public, e.g. Aiven)
│   └── aiven-ca.pem                #   referenced by DB_SSL_CA
│
├── hostel_management_schema.sql    # MySQL schema (18 tables + 3 triggers)
├── migrations.sql                  # Upgrades an old schema to the current one (idempotent)
├── seed_data.sql                   # Demo data + accounts
│
├── templates/                      # Jinja2 HTML pages
│   ├── base.html                   #   shared layout (sidebar + bell badge, flashes, footer)
│   ├── home.html                   #   landing page
│   ├── notifications.html          #   per-user notification feed
│   ├── invoice_print.html          #   printable single-invoice receipt
│   ├── invoice_statement_print.html #   printable per-student statement (count + total)
│   ├── auth/                       #   login + change-password pages
│   │   ├── login.html
│   │   └── change_password.html
│   ├── manager/                    #   manager dashboard + feature pages
│   │   ├── dashboard.html
│   │   ├── students.html
│   │   ├── register_student.html
│   │   ├── rooms.html              #   hostel list (edit/delete) + rooms, add buttons
│   │   ├── add_hostel.html         #   add OR edit hostel: map pin or typed coords
│   │   ├── add_room.html
│   │   ├── allocate_room.html      #   gender-filtered dropdowns
│   │   ├── complaints.html
│   │   ├── invoices.html           #   per-type grid + expandable grouped bill list
│   │   ├── attendance.html
│   │   ├── mess_menu.html
│   │   ├── violations.html         #   tabs: record / send notice / browse + resolve + row notify
│   │   ├── feedback.html
│   │   ├── mess_off.html           #   approve / reject
│   │   ├── parcels.html
│   │   ├── visitors.html
│   │   └── staff.html              #   + delete buttons
│   ├── student/                    #   student dashboard + feature pages
│   │   ├── dashboard.html
│   │   ├── profile.html
│   │   ├── room.html
│   │   ├── complaints.html
│   │   ├── invoices.html
│   │   ├── mess_off.html
│   │   ├── feedback.html
│   │   ├── in_out.html
│   │   ├── parcels.html            #   shows received_by + Collect button
│   │   └── attendance.html         #   geo-fenced + Leaflet map (your location + inside/outside badge)
│   └── staff/                      #   staff dashboard + feature pages
│       ├── dashboard.html
│       ├── visitors.html
│       ├── parcels.html            #   receive form
│       ├── in_out.html             #   mark students returned
│       └── attendance.html         #   geo-fenced + Leaflet map (hostel picker + your location)
│
├── static/                         # Static assets
│   ├── css/
│   │   └── style.css               #   stylesheet
│   └── js/
│       └── main.js                 #   confirm dialogs + gender-filtered room dropdown
│
├── report.md                       # Full code walkthrough (how every part works)
├── class_diagram (1).svg           # UML class diagram (17 classes)
├── Requirements Definition.pdf     # Functional & non-functional requirements
└── AGENTS .md                      # Project memory / handoff notes
```

## Documentation

- `report.md` — explains the request flow, every route, the class-diagram mapping, and security measures.
- `class_diagram (1).svg` — UML class diagram (17 classes).
- `Requirements Definition.pdf` — functional & non-functional requirements.
