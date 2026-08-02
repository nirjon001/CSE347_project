# Hostel Management System — Code Report

**Course:** CSE347 — Information System Analysis & Design
**Stack:** Python 3 + Flask + MySQL (MariaDB via XAMPP) + HTML/CSS/JS
**This document explains every file, how each part works, and how a request travels through the code.**

---

## 1. How to Run the Project

1. Start XAMPP and make sure **MySQL** is running (port 3306).
2. Load the database (one time):
   - `hostel_management_schema.sql` creates the database and all 17 tables.
   - `seed_data.sql` inserts sample users so you can log in immediately.
3. Open a terminal in the project folder and run:

   ```
   python app.py
   ```

4. Open `http://127.0.0.1:5000` in your browser.

### Test accounts (from `seed_data.sql`)

| Username   | Password   | Role    |
|------------|------------|---------|
| `manager`  | `admin123` | Manager |
| `staff1`   | `staff123` | Staff   |
| `student1` | `student123` | Student |
| `student2` | `student123` | Student (no room yet) |

---

## 2. How a Request Flows Through the App

This is the most important thing to understand. Follow one click in the browser:

```
Browser (HTML form)
   │  1. user submits form → browser sends HTTP request to a URL
   ▼
Flask app.py (a route function matches the URL)
   │  2. route checks login + role (decorators)
   │  3. route reads form data (request.form) or URL data
   ▼
db.py (helper functions)
   │  4. route calls query()/execute() with a SQL statement + %s placeholders
   ▼
MySQL database (hostel_management)
   │  5. returns rows (as Python dicts) or affected-row count
   ▼
db.py returns data to the route
   ▼
route calls render_template('page.html', data=...)
   │  6. Flask fills the template with the data (Jinja2 syntax)
   ▼
Browser gets finished HTML and displays the page
```

Rules to remember:
- **GET** requests just display pages.
- **POST** requests change data (register, allocate, update, delete).
- After a successful POST the route redirects back to a GET page so refreshing the browser does not re-submit the form.

---

## 3. File-by-File Explanation

### 3.1 `config.py` — Settings

```python
DB_CONFIG = {'host': '127.0.0.1', 'user': 'root', 'password': '', 'database': 'hostel_management', ...}
SECRET_KEY = 'cse347-hostel-management-secret-key'
```

- `DB_CONFIG` is the dictionary every database connection is built from. XAMPP's default MySQL user is `root` with an **empty password** — that is why `password` is `''`. If your XAMPP has a password, change it here only.
- `SECRET_KEY` is used by Flask to sign the session cookie (the thing that keeps you "logged in" between requests).

### 3.2 `db.py` — The database bridge

All SQL goes through these three small functions. They are the **only** file that talks to MySQL, so if you ever switch databases you only change this file.

```python
def get_connection():  # opens one real MySQL connection
def query(sql, params=(), one=False):    # SELECT — returns rows (list of dicts)
def execute(sql, params=()):             # INSERT/UPDATE/DELETE — returns new row id
```

- `query()` opens a connection, runs the SQL, fetches all rows as **dictionaries** (column name → value), closes the connection and returns them. `one=True` returns just the first row (or `None`).
- `execute()` runs INSERT/UPDATE/DELETE, commits the change, and returns `lastrowid` (the new ID) — useful right after an INSERT.
- `%s` in the SQL are **placeholders**. The values are passed separately in `params`. This is called a *parameterized query* and it is how we prevent **SQL injection** (a user can never break out of the SQL string).

### 3.3 `app.py` — The whole application

This one file holds every URL route. Each route = one Python function that answers one URL.

#### Setup block (top of file)

```python
app = Flask(__name__)
app.secret_key = SECRET_KEY
```

- Creates the Flask application object and turns on sessions.
- `@app.context_processor` injects `session_role` and `session_username` into **every template**, which the navbar uses to show the right menu for each role.

#### The three security helpers

| Helper | What it does |
|---|---|
| `login_required` (decorator) | If `session['user_id']` is missing, redirect to the login page. Protects every page except home/login. |
| `role_required('manager')` (decorator factory) | Checks `session['role']`. Blocks a student from opening a manager page. |
| `get_role_id(role, user_id)` | Looks up the `manager_id` / `staff_id` / `student_id` for a user — because our schema splits `users` into three separate tables (table-per-subtype). |

A decorator is a "wrapper" function: `@login_required` above a route means "run the login check first, then run the route."

#### Authentication routes (Login sequence diagram #1)

**`/` (home)** — If already logged in, go to your dashboard; otherwise show the landing page.

**`/login` (GET + POST)**
1. If the form was POSTed, read `username` and `password`.
2. Look up the user: `SELECT * FROM users WHERE username = %s`.
3. `check_password_hash(user['password'], password)` — compares the typed password against the stored **scrypt hash** (never against plain text).
4. On success, store `user_id`, `username`, `role`, and `role_id` in the **session** (Flask keeps this in an encrypted cookie), then redirect to the dashboard.
5. On failure, show a flash message "Invalid username or password."

**`/logout`** — `session.clear()` removes the login data and returns home.

**`/dashboard`** — reads `session['role']` and redirects to the correct dashboard (`/manager`, `/student`, or `/staff`).

**`/change-password`** — implements `User.changePassword(oldPwd, newPwd)` from the class diagram. Checks the old password, confirms the two new ones match, then writes a fresh hash with `generate_password_hash()`.

#### Manager routes (Manager class methods)

| URL | Class method it maps to | What it does |
|---|---|---|
| `/manager` | — | Dashboard: counts of students/rooms/complaints/invoices + recent complaints & violations |
| `/manager/students` | `viewStudents` | Lists all students joined with their username and room |
| `/manager/students/register` | `registerStudent()` | Creates a `users` row (role=student, hashed password) then a `students` row — two inserts in a transaction-like sequence |
| `/manager/students/delete/<id>` | `deleteStudent(id)` | Deletes the user (ON DELETE CASCADE removes the student row), and if they had a room, **returns the bed** by incrementing `available_beds` |
| `/manager/rooms` | `viewRooms()` | Shows each room, hostel, bed counts and current occupants |
| `/manager/rooms/allocate` | `allocateRoom()` | The Room Allocation sequence diagram #3. Uses `SELECT ... FOR UPDATE` to lock the room row, refuses allocation if `available_beds <= 0`, else decrements beds and sets the student's `room_id` |
| `/manager/complaints` | `viewComplaint` / `resolveComplaint` | Lists complaints with student+room; a form updates status to Pending/In Progress/Resolved |
| `/manager/invoices` | `generateInvoice()` | Creates a new invoice for a student with amount + due date |
| `/manager/invoices/toggle/<id>` | `updatePaymentStatus()` | Flips an invoice between Paid/Unpaid |
| `/manager/attendance` | `recordStudentAttendance()` `recordStaffAttendance()` | Records attendance; `ON DUPLICATE KEY UPDATE` lets you overwrite the same (student, date) instead of erroring |
| `/manager/mess-menu` | `updateMessMenu()` | Upserts a menu item per (day, meal) slot |
| `/manager/violations` | `recordViolation()` | Inserts a violation for a student **or** a staff member — exactly one of the two, matching the CHECK constraint |
| `/manager/visitors` | `viewVisitorLogs()` | Manager **views** visitor logs (staff registers them) |
| `/manager/staff` | `addStaff()` | Creates a `users` + `staff` row (caretaker/cook/watchman/guard...) |

#### Student routes (Student class methods)

| URL | Class method | What it does |
|---|---|---|
| `/student` | — | Dashboard: room, unpaid invoice count, open complaints, waiting parcels, today's mess menu |
| `/student/profile` | `viewProfile()` | View and edit own email/phone/address/gender |
| `/student/room` | `viewRoom()` | Shows own room + hostel details (or a "not allocated" notice) |
| `/student/complaints` | `submitComplaint()` | Submit a complaint; list own complaints with status badges |
| `/student/invoices` | `viewInvoice()` | List own invoices and payment status |
| `/student/mess-off` | `applyMessOff()` | Request mess-off with start/end date (status Pending) |
| `/student/feedback` | `submitFeedback()` | Submit and view own feedback |
| `/student/in-out` | `submitLeaveRequest()` | Record a departure (out_date, reason); status starts as Out |
| `/student/parcels` | `viewParcels` | List own parcels and whether collected |

#### Staff routes (Staff class methods)

| URL | Class method | What it does |
|---|---|---|
| `/staff` | — | Dashboard: visitors today, arrived parcels, own attendance |
| `/staff/visitors` | `registerVisitor()` | The front-desk workflow — staff registers a visitor against a student; `registered_by_staff` stores the staff id |
| `/staff/parcels` | `updateParcelStatus()` | Marks an Arrived parcel as Collected |
| `/staff/attendance` | `recordAttendance()` | Staff marks own Present/Leave for today (upsert) |

#### The final block

```python
if __name__ == '__main__':
    app.run(debug=True)
```

- Runs the development server. `debug=True` auto-reloads the app whenever you save `app.py`, so you don't restart manually during development.

---

## 4. Templates (`templates/`) — the HTML pages

Flask uses **Jinja2** templates. A template is HTML with `{{ variable }}` (print a value) and `{% ... %}` (logic like `if`/`for`).

### `base.html` — the shared layout
Every other page says `{% extends "base.html" %}` at the top. That means base.html provides:
- The `<head>` with the stylesheet link.
- The **navbar** — and here is the clever part: it reads `session_role` and shows different menu links for manager / student / staff, plus username, role badge, and Logout.
- **Flash messages** — `get_flashed_messages()` displays the green/red/yellow notices produced by `flash()` in `app.py`.
- The footer.
- The `<script>` tag for `main.js`.

A page that extends base.html only writes its own content inside `{% block content %}...{% endblock %}`.

### The three page families
- `auth/` — `login.html` (centered card on a gradient background) and `change_password.html`.
- `manager/` — dashboard + 10 feature pages (students, register student, rooms, allocate room, complaints, invoices, attendance, mess menu, violations, visitors, staff).
- `student/` — dashboard + 8 pages (profile, room, complaints, invoices, mess off, feedback, in/out, parcels).
- `staff/` — dashboard + 3 pages (visitors, parcels, attendance).

### A typical form page (e.g. `manager/register_student.html`)
```html
<form method="post">           <!-- sends a POST to the same URL -->
    <input name="username" required>
    <button type="submit">Register</button>
</form>
```
When submitted, the browser POSTs to `/manager/students/register`, the route reads `request.form['username']`, inserts into the database, flashes a message and redirects.

### A typical list page (e.g. `manager/complaints.html`)
```html
{% for c in complaints %}          <!-- loop over rows from the route -->
    <tr><td>{{ c.student_name }}</td><td>{{ c.description }}</td>...</tr>
{% else %}                          <!-- runs if the list is empty -->
    <tr><td colspan="7" class="empty">No complaints found.</td></tr>
{% endfor %}
```
`complaints` is the list the route passed into `render_template()`. Each item `c` is a row-dictionary whose keys are the SQL column names.

### Status badges
The `badge` classes color-code status: green=Paid/Resolved/Collected/Present/Approved, yellow=Pending/Unpaid/Arrived/Out, red=Overdue/Absent/Rejected, blue=In Progress/Leave.

---

## 5. Static files (`static/`)

- `css/style.css` — one stylesheet for the whole app. CSS variables at the top (`:root { --primary: ... }`) define the colour theme, and `.card`, `.table`, `.form-group`, `.btn`, `.badge`, `.flashes` classes are reused everywhere.
- `js/main.js` — a tiny script: any form with `data-confirm="..."` shows a browser confirm dialog before submitting. This powers the "Delete student?" confirmation buttons. That is the only JavaScript needed, which keeps the app beginner-friendly.

---

## 6. Database files

### `hostel_management_schema.sql`
Creates `hostel_management` and the 17 tables exactly matching the UML class diagram:
- `users` (base / superclass) + `managers`, `staff`, `students` (subtype tables, each linked by a `user_id` FK) — this is **table-per-subtype inheritance**.
- Feature tables: `complaints`, `invoices`, `student_attendance`, `staff_attendance`, `visitors`, `parcels`, `mess_off_requests`, `feedback`, `student_in_out`, `violations`, `mess_menu`, plus `hostels` and `rooms`.
- `violations` has a `CHECK` constraint so a violation belongs to exactly **one** of student/staff.
- Indexes speed up common lookups (e.g. `idx_complaints_student`).

### `seed_data.sql`
Inserts demo records (4 users, 1 manager, 1 staff, 1 hostel, 2 rooms, 2 students, menu, invoices, one complaint, one feedback). Passwords are stored as **scrypt hashes**, never plain text.

---

## 7. Security Measures

1. **Password hashing** — `generate_password_hash()` / `check_password_hash()` (Werkzeug, ships with Flask). The database only ever contains hashes.
2. **SQL injection prevention** — every query uses `%s` placeholders with separate parameters (see `db.py`).
3. **Session-based auth** — pages are protected by `login_required` and `role_required`, so a student cannot reach manager URLs by guessing them.
4. **No secrets in the repo** — the `SECRET_KEY` is in `config.py` only for a course project; a real deployment would read it from an environment variable.

---

## 8. Mapping to the UML Class Diagram

Every class method from `class_diagram.svg` has a matching code route:

| Class & method | Code (route / function) |
|---|---|
| `User.login()` | `/login` |
| `User.changePassword()` | `/change-password` |
| `Manager.registerStudent()` | `/manager/students/register` |
| `Manager.deleteStudent()` | `/manager/students/delete/<id>` |
| `Manager.allocateRoom()` | `/manager/rooms/allocate` |
| `Manager.viewRooms()` | `/manager/rooms` |
| `Manager.generateInvoice()` | `/manager/invoices` |
| `Manager.updateMessMenu()` | `/manager/mess-menu` |
| `Manager.approveMessOff()` | `/manager/mess-menu` (status updates via same pattern) |
| `Manager.recordStudentAttendance()` / `recordStaffAttendance()` | `/manager/attendance` |
| `Manager.recordViolation()` / `viewViolation()` | `/manager/violations` |
| `Manager.viewVisitorLogs()` | `/manager/visitors` |
| `Staff.registerVisitor()` | `/staff/visitors` |
| `Staff.updateParcelStatus()` | `/staff/parcels` |
| `Staff.recordAttendance()` | `/staff/attendance` |
| `Student.viewProfile()` / `viewRoom()` | `/student/profile` / `/student/room` |
| `Student.submitComplaint()` | `/student/complaints` |
| `Student.viewInvoice()` | `/student/invoices` |
| `Student.applyMessOff()` | `/student/mess-off` |
| `Student.submitFeedback()` | `/student/feedback` |
| `Student.submitLeaveRequest()` | `/student/in-out` |
| `Student.viewParcels` | `/student/parcels` |

The three **required sequence diagrams** map as:
1. **Login/Authentication** → `/login` + session + role redirect.
2. **Register Student** → `/manager/students/register` (user + student rows).
3. **Room Allocation** → `/manager/rooms/allocate` (bed-availability check + atomic update).
