# CSE347 — Hostel Management System

A web-based hostel management system built for **CSE347: Information System Analysis & Design** (3rd year, 3rd semester).

## Features

- **Role-based login** — separate dashboards for Manager, Student, and Staff (Flask sessions + hashed passwords)
- **Manager**: register/delete students, allocate rooms, add hostels & rooms with custom bed capacity, manage complaints & invoices, record attendance, update the mess menu, record & resolve violations, view student feedback, approve/reject mess-off requests, view all parcels, view visitor logs, manage & delete staff
- **Student**: view profile & room, submit complaints, view invoices, apply mess-off, give feedback, record in/out, check parcels (who received them, when collected)
- **Staff**: register visitors at the front desk, receive & hand over parcels (with audit trail), record student returns, record own attendance
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
3. Select `hostel_management_schema.sql` → **Go** (creates the `hostel_management` database + all 17 tables)
4. Import `seed_data.sql` the same way (adds demo accounts & records)

> **Already used the old version?** Run `migrations.sql` instead of re-importing the schema — it adds the new columns/foreign keys/trigger without wiping your data. It is safe to run any time (it skips anything that already exists, so re-running causes no errors).

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

This installs **Flask** and **mysql-connector-python**.

### 5. Check the database settings (only if your MySQL uses a password)

Open `config.py`. By default XAMPP's MySQL `root` user has an **empty password**, so nothing needs to change. If your MySQL root has a password, update it here:

```python
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'YOUR_PASSWORD_HERE',   # empty by default in XAMPP
    'database': 'hostel_management',
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
- Try **Add Hostel** then **Add Room** with a custom capacity, and allocate a student into it.
- Try **Violations → Resolve**, **Mess Off → Approve/Reject**, and open **Feedback** / **Parcels** views.
- Log in as **student1** to see the student side (complaints, invoices, mess menu, parcels).
- Log in as **staff1** to register a visitor, receive/collect a parcel, and mark a student as returned.

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

## Project Structure

```
CSE347_project/
│
├── app.py                          # Flask app: all routes (auth, manager, student, staff)
├── config.py                       # DB connection + secret key settings
├── db.py                           # Parameterized query/execute helpers
├── requirements.txt                # Python dependencies
│
├── hostel_management_schema.sql    # MySQL schema (17 tables + trigger)
├── migrations.sql                  # Upgrades an old schema to the current one
├── seed_data.sql                   # Demo data + accounts
│
├── templates/                      # Jinja2 HTML pages
│   ├── base.html                   #   shared layout (navbar, flashes, footer)
│   ├── home.html                   #   landing page
│   ├── auth/                       #   login + change-password pages
│   │   ├── login.html
│   │   └── change_password.html
│   ├── manager/                    #   manager dashboard + feature pages
│   │   ├── dashboard.html
│   │   ├── students.html
│   │   ├── register_student.html
│   │   ├── rooms.html              #   shows hostels + rooms, add buttons
│   │   ├── add_hostel.html
│   │   ├── add_room.html
│   │   ├── allocate_room.html
│   │   ├── complaints.html
│   │   ├── invoices.html
│   │   ├── attendance.html
│   │   ├── mess_menu.html
│   │   ├── violations.html         #   status + resolve button
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
│   │   └── parcels.html            #   shows received_by / collected info
│   └── staff/                      #   staff dashboard + feature pages
│       ├── dashboard.html
│       ├── visitors.html
│       ├── parcels.html            #   receive + collect forms
│       ├── in_out.html             #   mark students returned
│       └── attendance.html
│
├── static/                         # Static assets
│   ├── css/
│   │   └── style.css               #   stylesheet
│   └── js/
│       └── main.js                 #   confirm-dialog helper
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
