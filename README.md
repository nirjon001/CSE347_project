# 🏨 CSE347 — Hostel Management System

> A full-featured, role-based **Hostel Management System** built for **CSE347: Information System Analysis & Design** (3rd year, 3rd semester).

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)
![MySQL](https://img.shields.io/badge/Database-MySQL%2FMariaDB-4479A1?logo=mysql&logoColor=white)
![Render](https://img.shields.io/badge/Host-Render-46E3B7?logo=render&logoColor=white)
![Security](https://img.shields.io/badge/Security-Parameterized%20Queries-2ea44f)
![Status](https://img.shields.io/badge/Status-LIVE-success)

> **🟢 Live demo:** [https://hostel-management-368b.onrender.com/](https://hostel-management-368b.onrender.com/) — log in with the demo accounts below.

---

## ✨ Features

- **Role-based login** — separate dashboards for Manager, Student, and Staff (Flask sessions + hashed passwords)
- **Gender-separated hostels** — each hostel is Male or Female; room allocation (and the database) refuses to place a student in an opposite-gender hostel
- **Notification system** — a bell with an unread-count badge and a full notification page with **filter chips** (All / Unread / by category: Complaints, Mess Off, Parcels, Visitors, Attendance, Invoices, Violations, Notices, ...) so a busy admin inbox stays manageable; students/staff get automatic alerts (complaint updates, new invoices, parcel arrivals, visitor arrivals, violation notices, mess-off decisions) and managers can send free-text notices
- **Geo-fenced attendance** — students and staff mark "Present" only from inside their hostel's GPS radius (browser location + Leaflet/OpenStreetMap, no paid API keys). Managers set the hostel's location by dropping a pin on a map or typing coordinates, and the map shows your live position with an accuracy estimate (how close ± the fix is) and an inside/outside check
- **Student parcel self-collection** — staff receive parcels (auto-notifying the student); students pick them up with one click, and every parcel keeps an audit trail (who received it, who collected it, when)
- **Manager — rooms & people**: register/delete students, allocate rooms, add/edit/delete hostels (map pin or typed coordinates; duplicate addresses are rejected) & add rooms with custom bed capacity, view each room's occupants (each room row **expands** to list its students — name, student no, email, phone — like the invoice list), Hostels/Rooms come as two **pill-tab views**, manage & delete staff
- **Manager — day-to-day**: manage complaints & invoices (**generate several bills at once** — room rent / electricity / food / water / other — with a summary-by-type section, a per-student **expandable bill list** with totals, a **Print statement** per student and per-invoice **Print** copies), record attendance with a **dashboard analytics section** (today's status donut + last-14-day trend) and a **per-person View/Edit** table (select a student or staff member to browse their history and change any day's status inline, with their own donut + trend charts), update the mess menu, record & resolve violations (tabbed page: record / send notice / browse all with Open-Resolved filters and per-row notify), view student feedback, approve/reject mess-off requests, view all parcels, view visitor logs
- **Student**: view profile & room, submit complaints, view invoices (total / paid / unpaid summary with View-Print for a physical copy), apply mess-off, give feedback, record in/out, check & collect parcels (who received them, when collected), mark **(geo-fenced) attendance with personal stats + donut/trend charts**
- **Staff**: register visitors at the front desk, receive parcels (notifies the student), record student returns, record own (geo-fenced) attendance **with personal stats + charts**
- **Security**: scrypt password hashing, parameterized SQL (SQL-injection safe), role-guarded routes, strict SQL mode so invalid data is rejected

## 🛠️ Tech Stack

- **Backend**: Python 3 + Flask (server-rendered Jinja2 templates)
- **Database**: MySQL / MariaDB (schema in `hostel_management_schema.sql`)
- **Frontend**: HTML + CSS (single small JS file) + Chart.js (via CDN) for attendance/trend charts

## 🚀 Getting Started

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

## 👥 Demo Accounts

| Username   | Password   | Role    |
|------------|------------|---------|
| `manager`  | `admin123` | Manager (Ayesha Rahman) |
| `staff1`   | `staff123` | Staff — Caretaker (Karim Mia) |
| `staff2`   | `staff123` | Staff — Cook (Rashida Begum) |
| `staff3`   | `staff123` | Staff — Guard (Hanif Uddin) |
| `student1` | `student123` | Student — Jakir Hossain (room 101) |
| `student2` | `student123` | Student — Moin Uddin (room 101) |
| `student3` | `student123` | Student — Abdullah Al Mamun (room 101) |
| `student4` | `student123` | Student — Iftekhar Alam (room 101) |
| `student5` | `student123` | Student — Rakib Uddin (room 102) |
| `student6` … `student50` | `student123` | 50 students total, 2.5 months of daily attendance records & rich demo data |

## 🌐 Live Website

The project runs online at **https://hostel-management-368b.onrender.com/** (free Render web service + Aiven free MySQL). It serves the same code as the local copy.

## ☁️ Deploy to the Web (free)

The **same code** runs locally *and* as a free web copy. The full guide — architecture, one-time Aiven + Render setup, TLS note, and the `sync_web_db.bat push/pull` data-sync commands — lives in **[`DEPLOYMENT.md`](DEPLOYMENT.md)**.

## 🐛 Troubleshooting

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

## 📂 Project Structure

```
CSE347_project/
├── app.py, config.py, db.py       # Flask app (all routes), env-driven config, DB helpers
├── requirements.txt, render.yaml  # Python deps, Render Blueprint (gunicorn app:app)
├── hostel_management_schema.sql   # Fresh schema (18 tables + 3 triggers)
├── migrations.sql                 # Idempotent upgrade for older databases
├── seed_data.sql                  # Demo accounts & records (50 students, 2.5 months of data)
├── scripts/generate_seed.py       # Regenerates seed_data.sql (names/rooms/attendance/records)
├── templates/                     # Jinja2 pages (auth/, manager/, student/, staff/ + base)
├── static/                        # css/style.css, js/main.js
├── scripts/                       # Web-deploy helpers (init_web_db.bat, sync_web_db.bat)
├── certs/                         # TLS CA cert (aiven-ca.pem) for the web DB
├── DEPLOYMENT.md                  # Full web-deployment guide
├── report.md                      # Code walkthrough (see Documentation below)
├── class_diagram (1).svg          # UML class diagram (17 classes)
└── Requirements Definition.pdf    # Functional & non-functional requirements
```

## 📚 Documentation

- `DEPLOYMENT.md` — full guide for running the free web copy (Render + Aiven).
- `report.md` — explains the request flow, every route, the class-diagram mapping, and security measures.
- `class_diagram (1).svg` — UML class diagram (17 classes).
- `Requirements Definition.pdf` — functional & non-functional requirements.
