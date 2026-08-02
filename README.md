# CSE347 — Hostel Management System

A web-based hostel management system built for **CSE347: Information System Analysis & Design** (3rd year, 3rd semester).

## Features

- **Role-based login** — separate dashboards for Manager, Student, and Staff (Flask sessions + hashed passwords)
- **Manager**: register/delete students, allocate rooms, manage complaints & invoices, record attendance, update the mess menu, record violations, view visitor logs, manage staff
- **Student**: view profile & room, submit complaints, view invoices, apply mess-off, give feedback, record in/out, check parcels
- **Staff**: register visitors at the front desk, mark parcels collected, record own attendance
- **Security**: scrypt password hashing, parameterized SQL (SQL-injection safe), role-guarded routes

## Tech Stack

- **Backend**: Python 3 + Flask (server-rendered Jinja2 templates)
- **Database**: MySQL / MariaDB (schema in `hostel_management_schema.sql`)
- **Frontend**: HTML + CSS (single small JS file)

## Getting Started

1. Install XAMPP (or any MySQL/MariaDB server) and start MySQL on port 3306.
2. Load the database:
   ```
   mysql -u root < hostel_management_schema.sql
   mysql -u root < seed_data.sql
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run:
   ```
   python app.py
   ```
5. Open http://127.0.0.1:5000

## Demo Accounts

| Username   | Password   | Role    |
|------------|------------|---------|
| `manager`  | `admin123` | Manager |
| `staff1`   | `staff123` | Staff   |
| `student1` | `student123` | Student |
| `student2` | `student123` | Student (no room allocated) |

## Project Structure

```
CSE347_project/
│
├── app.py                          # Flask app: all routes (auth, manager, student, staff)
├── config.py                       # DB connection + secret key settings
├── db.py                           # Parameterized query/execute helpers
├── requirements.txt                # Python dependencies
│
├── hostel_management_schema.sql    # MySQL schema (17 tables)
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
│   │   ├── rooms.html
│   │   ├── allocate_room.html
│   │   ├── complaints.html
│   │   ├── invoices.html
│   │   ├── attendance.html
│   │   ├── mess_menu.html
│   │   ├── violations.html
│   │   ├── visitors.html
│   │   └── staff.html
│   ├── student/                    #   student dashboard + feature pages
│   │   ├── dashboard.html
│   │   ├── profile.html
│   │   ├── room.html
│   │   ├── complaints.html
│   │   ├── invoices.html
│   │   ├── mess_off.html
│   │   ├── feedback.html
│   │   ├── in_out.html
│   │   └── parcels.html
│   └── staff/                      #   staff dashboard + feature pages
│       ├── dashboard.html
│       ├── visitors.html
│       ├── parcels.html
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
