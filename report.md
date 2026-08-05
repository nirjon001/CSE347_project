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
| `manager`  | `admin123` | Manager (Ayesha Rahman) |
| `staff1`   | `staff123` | Staff — Caretaker (Karim Mia) |
| `staff2`   | `staff123` | Staff — Cook (Rashida Begum) |
| `staff3`   | `staff123` | Staff — Guard (Hanif Uddin) |
| `student1` | `student123` | Student — Rafi (room 101) |
| `student2` | `student123` | Student — Sadia (no room) |
| `student3` | `student123` | Student — Tanvir (room 201) |
| `student4` | `student123` | Student — Nusrat (room 301) |
| `student5` | `student123` | Student — Mehedi (no room) |

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
- `@app.context_processor` injects `session_role`, `session_username`, and the notification **`unread_count`** into **every template**, which the left sidebar uses to show the right menu for each role and the notification bell badge.

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

#### The notification system

Every role gets an in-app notification feed. The bell icon in the sidebar footer shows an unread-count badge (via `unread_count` from the context processor).

| Helper / route | What it does |
|---|---|
| `notify_user(user_id, ...)` | Inserts one `notifications` row for a user |
| `notify_managers(...)` | Sends the same notification to **every** manager (used for new complaints, mess-off requests, feedback, parcel collections) |
| `notify_student(id, ...)` / `notify_staff(id, ...)` | Sends to one student/staff member via their `user_id` |
| `/notifications` | Lists the logged-in user's notifications, newest first; unread ones are highlighted |
| `/notifications/read/<id>` | Clicking a notification marks it read and follows its `link` |
| `/notifications/read-all` | Marks everything read |

Automatic triggers: complaint status change → student; new invoice → student; mess-off decision → student; violation recorded (with the notify checkbox) → student or staff (custom text optional); violation resolved → target; staff receives a parcel → student; staff registers a visitor → student; student collects a parcel → receiving staff + all managers. The manager can also send a **manual free-text notice** to any student or staff member — either from the **Send Notice** tab or per violation row (see `/manager/violations` below).

#### Manager routes (Manager class methods)

| URL | Class method it maps to | What it does |
|---|---|---|
| `/manager` | — | Dashboard: counts of students/rooms/complaints/invoices + open violations + pending mess-off requests + recent complaints & violations |
| `/manager/students` | `viewStudents` | Lists all students joined with their username and room |
| `/manager/students/register` | `registerStudent()` | Creates a `users` row (role=student, hashed password) then a `students` row — two inserts in a transaction-like sequence |
| `/manager/students/delete/<id>` | `deleteStudent(id)` | Deletes the user (ON DELETE CASCADE removes the student row), and if they had a room, **returns the bed** by incrementing `available_beds` (see trigger note in §6) |
| `/manager/rooms` | `viewRooms()` | Shows each hostel (with its gender), each room, bed counts and current occupants — the **Occupants column now lists the actual student names** inside each room (not just a count) |
| `/manager/hostels/add` | — | Add a **new hostel** (name + location + **gender** + lat/lng/radius for the attendance geo-fence). A Leaflet map offers **both options**: drop/pin the location on the map (click/drag/"Locate me", with optional free OpenStreetMap reverse-geocoding that auto-fills the address) or type the coordinates manually; `total_rooms` starts at 0. Saving is rejected with a friendly flash if **another hostel already uses the same address** (`_hostel_same_address()`), so two buildings can't share one location |
| `/manager/hostels/edit/<id>` | `editHostel()` | Edit every field from the add form (name, location, gender, coords, radius) with the same map. Changing the **gender is blocked** while students are allocated to that hostel. The duplicate-address check also applies but **excludes the hostel being edited**, so keeping your own address still saves |
| `/manager/hostels/delete/<id>` | `deleteHostel()` | Delete a hostel (rooms cascade). **Blocked** while any student is still allocated; the hostel list page shows the Edit/Delete buttons |
| `/manager/rooms/add` | — | Add a room with a **custom bed capacity** (any number ≥ 1) to any hostel; rejects duplicates and zero capacity |
| `/manager/rooms/allocate` | `allocateRoom()` | The Room Allocation sequence diagram #3. Uses `SELECT ... FOR UPDATE` to lock the room row, refuses allocation if `available_beds <= 0` **or if the student's gender doesn't match the hostel's gender**, else decrements beds and sets the student's `room_id`. The DB trigger below is the backstop |
| `/manager/complaints` | `viewComplaint` / `resolveComplaint` | Lists complaints with student+room; a form updates status to Pending/In Progress/Resolved — **and notifies the student** of the new status |
| `/manager/invoices` | `generateInvoice()` | Creates a new invoice for a student with an **invoice type** (Room Rent / Electricity / Food / Water / Other) + amount + due date — **and notifies the student**. The page shows a **Summary by Type** section (count + sum per type, grand total) over all invoices, plus **Print** and **Download PDF** buttons per row |
| `/manager/invoices/toggle/<id>` | `updatePaymentStatus()` | Flips an invoice between Paid/Unpaid |
| `/manager/invoices/print/<id>` | — | Opens a printable receipt (hostel name, invoice no, student, type, amount, due date, status) — press **Print / Save as PDF** |
| `/manager/invoices/pdf/<id>` | — | Downloads the same receipt as a **PDF file** (generated with `fpdf2`; falls back to Print with a message if the library isn't installed) |
| `/manager/attendance` | `recordStudentAttendance()` `recordStaffAttendance()` | Records attendance; `ON DUPLICATE KEY UPDATE` lets you overwrite the same (student, date) instead of erroring |
| `/manager/mess-menu` | `updateMessMenu()` | Upserts a menu item per (day, meal) slot |
| `/manager/violations` | `recordViolation()` / `resolveViolation()` | The page is organised into **three tabs**: **Record Violation** (student or staff target, description, optional notify checkbox + custom message), **Send Notice** (free-text manual notice to any student or staff member), and **All Violations** (open/resolved filter chips + per-row **Notify** expand and **Resolve** for open rows). The POST handler dispatches on a hidden `action` field — `record`, `notice`, or `row_notify` — which keeps every workflow on this single URL |
| `/manager/violations/resolve/<id>` | `resolveViolation(id)` | Marks a violation **Resolved**, stores `resolved_at`, and **notifies the violator** |
| `/manager/notify` | — | Backward-compatible alias of the **Send Notice** tab — sends free-text notifications to any student or staff member |
| `/manager/feedback` | — | Manager **views** all student feedback (with student names) |
| `/manager/mess-off` | `approveMessOff()` | Manager **approves or rejects** pending mess-off requests (the pending count on the dashboard drops) |
| `/manager/parcels` | — | Manager **views** all parcels with who received them and who/when collected them |
| `/manager/visitors` | `viewVisitorLogs()` | Manager **views** visitor logs (staff registers them) |
| `/manager/staff` | `addStaff()` | Creates a `users` + `staff` row (caretaker/cook/watchman/guard...) |
| `/manager/staff/delete/<id>` | — | Deletes a staff member (cascades their attendance; visitor/parcel "received by" references become NULL). You cannot delete yourself |

#### Student routes (Student class methods)

| URL | Class method | What it does |
|---|---|---|
| `/student` | — | Dashboard: room, unpaid invoice count, open complaints, waiting parcels, today's mess menu |
| `/student/profile` | `viewProfile()` | View and edit own email/phone/address/gender |
| `/student/room` | `viewRoom()` | Shows own room + hostel details (or a "not allocated" notice) |
| `/student/complaints` | `submitComplaint()` | Submit a complaint; list own complaints with status badges |
| `/student/invoices` | `viewInvoice()` | List own invoices with type and payment status, plus **total / paid / unpaid summary cards**; each row has a **View/Print** and **PDF** button (student routes only allow access to their own invoices) |
| `/student/invoices/print/<id>` | — | Printable receipt for the student's own invoice (Ctrl+P → physical copy) |
| `/student/invoices/pdf/<id>` | — | PDF download of the student's own invoice |
| `/student/mess-off` | `applyMessOff()` | Request mess-off with start/end date (status Pending) |
| `/student/feedback` | `submitFeedback()` | Submit and view own feedback |
| `/student/in-out` | `submitLeaveRequest()` | Record a departure (out_date, reason); status starts as Out |
| `/student/parcels` | `viewParcels` | List own parcels, the staff member who received it, and the collected date; **students collect their own parcels** — the Collect button sets `collected_by_student` + `collected_at` and notifies the receiving staff and managers |
| `/student/attendance` | `recordAttendance()` | **Geo-fenced attendance** — the browser fetches the student's GPS position and a free Leaflet/OSM map shows their hostel's radius circle plus their own (draggable) location marker with an inside/outside badge; the captured fix uses `enableHighAccuracy` + `maximumAge: 0` and shows a **±accuracy estimate** (with a dashed accuracy circle) so coarse desktop (IP/WiFi-based) fixes are visibly unreliable; `Present` is only recorded if the haversine distance to the hostel is within `radius_m` (Leave needs no location) |

#### Staff routes (Staff class methods)

| URL | Class method | What it does |
|---|---|---|
| `/staff` | — | Dashboard: visitors today, arrived parcels, own attendance |
| `/staff/visitors` | `registerVisitor()` | The front-desk workflow — staff registers a visitor against a student; `registered_by_staff` stores the staff id |
| `/staff/parcels` | `updateParcelStatus()` | **Receive** a new parcel (records which staff member took it in, **notifies the student**); staff no longer mark parcels collected — students do that themselves |
| `/staff/in-out` | — | Records a student's **return** — for any record currently `Out`, sets the `in_date` and status to Returned |
| `/staff/attendance` | `recordAttendance()` | **Geo-fenced attendance** — staff pick their workplace hostel, the browser fetches their GPS position, and a Leaflet/OSM map shows the selected hostel's radius circle plus their own location marker with an inside/outside badge and the **±accuracy** of the fix; `Present` is only recorded inside that hostel's `radius_m` circle (haversine); Leave needs no location |

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
- The **left sidebar** — when logged in, base.html renders a fixed 230px sidebar (`<aside class="sidebar">`) with the `HostelMS` brand on top, a scrolling menu in the middle, and a footer at the bottom. A `{% macro icon(name) %}` emits small inline SVG icons (Feather-style, no icon library) next to every link. It reads `session_role` and shows different menu links for manager / student / staff, plus a user chip (initial avatar + username + colour-coded role badge), a **Notifications link with an unread-count bell badge**, Change Password, and Logout. The body gets a `has-sidebar` class so the content area (`margin-left: 250px`) clears the fixed sidebar.
- **Flash messages** — `get_flashed_messages()` displays the green/red/yellow notices produced by `flash()` in `app.py`.
- The footer (`© 2026 Hostel Management System (HMS). All rights reserved.`).
- The `<script>` tag for `main.js`.

A page that extends base.html only writes its own content inside `{% block content %}...{% endblock %}`.

### The three page families
- `auth/` — `login.html` (full-screen gradient with a centred, branded card: `HM` monogram logo, system title, demo-account hint, and a **show/hide password** eye toggle) and `change_password.html` (same password toggle on all three fields).
- `manager/` — dashboard + 16 feature pages (students, register student, rooms, add hostel, add room, allocate room, complaints, invoices, attendance, mess menu, violations, visitors, staff, feedback, mess off, parcels).
- `student/` — dashboard + 8 pages (profile, room, complaints, invoices, mess off, feedback, in/out, parcels).
- `staff/` — dashboard + 4 pages (visitors, parcels, in/out, attendance).

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
The `badge` classes color-code status: green=Paid/Resolved/Collected/Present/Approved, yellow=Pending/Unpaid/Arrived/Out, red=Overdue/Absent/Rejected, blue=In Progress/Leave. A red `.notif-badge` on the sidebar bell shows the unread-notification count.

---

## 5. Static files (`static/`)

- `css/style.css` — one stylesheet for the whole app. CSS variables at the top (`:root { --primary: ... }`) define the colour theme, and `.card`, `.table`, `.form-group`, `.btn`, `.badge`, `.flashes` classes are reused everywhere. Added for the new features: `.notif-*` (notification feed + bell badge), `.map-canvas` (Leaflet container), `.check-label`, and `.tabs`/`.tab-btn`/`.tab-panel`/`.chip`/`.row-notify` (violations tabs + filter chips + inline notify).
- `js/main.js` — forms with `data-confirm="..."` show a browser confirm dialog before submitting (the "Delete student?" buttons). New: the **gender filter** — on the allocate page it hides rooms whose hostel gender doesn't match the selected student.

---

## 6. Database files

### `hostel_management_schema.sql`
Creates `hostel_management` and the 18 tables exactly matching the UML class diagram:
- `users` (base / superclass) + `managers`, `staff`, `students` (subtype tables, each linked by a `user_id` FK) — this is **table-per-subtype inheritance**.
- Feature tables: `complaints`, `invoices`, `student_attendance`, `staff_attendance`, `visitors`, `parcels`, `mess_off_requests`, `feedback`, `student_in_out`, `violations`, `mess_menu`, `notifications`, plus `hostels` and `rooms`.
- `violations` has a `CHECK` constraint so a violation belongs to exactly **one** of student/staff, plus a `status` ENUM (`Open`/`Resolved`) and `resolved_at`.
- `hostels` carries a `gender` ENUM (`Male`/`Female` — one gender per building), plus `lat`/`lng`/`radius_m` for the attendance geo-fence.
- `parcels` tracks `received_by_staff` (SET NULL on staff delete) and `collected_at` + `collected_by_student` (the student collects their own parcel).
- `notifications` stores the per-user feed: `user_id` FK, `title`, `message`, optional `link`, `is_read` (default 0), `created_at`.
- Indexes speed up common lookups (e.g. `idx_complaints_student`, `idx_notifications_user`).
- The script sets **strict SQL mode** (`STRICT_TRANS_TABLES`) so ENUM/CHECK columns reject bad data instead of silently storing an empty string — the app's `db.py` does the same on every connection.
- **Triggers**: `trg_student_delete_bed` frees a bed when a `students` row is deleted directly, and `trg_student_room_gender` / `trg_student_room_gender_upd` reject inserting **or** moving a student into a room of the opposite-gender hostel (the app checks this in code first; the trigger is the database-level backstop).

> MariaDB note: triggers do **not** fire on cascaded deletes, so when the app deletes a student through the `users` row it increments `available_beds` explicitly in code; the trigger covers direct `students`-row deletions. Both paths keep the invariant *occupied + available = total*.

### `migrations.sql`
For anyone who already loaded the **old** schema: run it once to upgrade without losing data. It is **idempotent** — columns use `ADD COLUMN IF NOT EXISTS`, foreign-key and index changes are wrapped in `information_schema`-guarded stored procedures (MariaDB has no `ADD CONSTRAINT IF NOT EXISTS`), triggers use `DROP TRIGGER IF EXISTS`, and the hostel-gender backfill runs only on a freshly added NULL column — so it is safe to run any number of times, even on an already-updated database (it simply does nothing).

### `seed_data.sql`
Inserts demo records (9 users, 1 manager, 3 staff, 2 hostels — Main Hostel (Male) and Girls Hostel (Female) with Dhaka-area GPS coords and a 50 m attendance radius — 5 students, menu, invoices, complaints, feedback, parcels, violations, mess-off and in/out records). Passwords are stored as **scrypt hashes**, never plain text.

---

## 7. Security Measures

1. **Password hashing** — `generate_password_hash()` / `check_password_hash()` (Werkzeug, ships with Flask). The database only ever contains hashes.
2. **SQL injection prevention** — every query uses `%s` placeholders with separate parameters (see `db.py`).
3. **Session-based auth** — pages are protected by `login_required` and `role_required`, so a student cannot reach manager URLs by guessing them.
4. **No secrets in the repo** — the `SECRET_KEY` is in `config.py` only for a course project; a real deployment would read it from an environment variable.
5. **Data ownership** — notification reads/queries always filter by `session['user_id']`, so one user can never see or mark-read another's notifications; parcel collection only works for the parcel's own student.
6. **Geo-fenced attendance** — the location check (haversine vs the hostel's `lat`/`lng`/`radius_m`) happens on the **server** with coordinates the browser sends; the Leaflet map is only a visual aid. The browser requests a fresh fix (`enableHighAccuracy`, `maximumAge: 0`) and the UI shows the **reported ±accuracy** — important because desktop browsers fall back to IP/WiFi triangulation (no GPS), which can be off by hundreds of metres. Note: browsers require HTTPS (or `localhost`) for the Geolocation API in production.
7. **Save hardening on hostel forms** — `location`/`hostel_name` are truncated to the column widths in `_hostel_form()`, the insert/update is wrapped in `try/except mysql.connector.Error` (the error is flashed instead of crashing), and a global `@app.errorhandler(500)` returns a friendly page — so a bad value (e.g., a very long reverse-geocoded address) can never drop the dev server's connection. This matters because `db.py` forces `STRICT_TRANS_TABLES`, so an over-length `VARCHAR` would otherwise raise an unhandled error 1406.
8. **Invoice print/PDF ownership** — the student print/PDF routes (`/student/invoices/print/<id>`, `/student/invoices/pdf/<id>`) verify the invoice belongs to the logged-in student before rendering or downloading; manager routes are role-guarded. The PDF generator is wrapped in `try/except ImportError`, so the app never crashes if `fpdf2` is missing — it falls back to the printable page with a message.

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
| `Manager.approveMessOff()` | `/manager/mess-off` |
| `Manager.recordStudentAttendance()` / `recordStaffAttendance()` | `/manager/attendance` |
| `Manager.recordViolation()` / `viewViolation()` / `resolveViolation()` | `/manager/violations` / `/manager/violations/resolve/<id>` |
| `Manager.viewVisitorLogs()` | `/manager/visitors` |
| `Staff.registerVisitor()` | `/staff/visitors` |
| `Staff.updateParcelStatus()` | `/staff/parcels` (receive; collection is student-driven) |
| `Staff.recordAttendance()` | `/staff/attendance` (geo-fenced) |
| `Student.viewProfile()` / `viewRoom()` | `/student/profile` / `/student/room` |
| `Student.submitComplaint()` | `/student/complaints` |
| `Student.viewInvoice()` | `/student/invoices` |
| `Student.applyMessOff()` | `/student/mess-off` |
| `Student.submitFeedback()` | `/student/feedback` |
| `Student.submitLeaveRequest()` | `/student/in-out` |
| `Student.viewParcels` | `/student/parcels` (self-collection) |
| `Student.recordAttendance()` | `/student/attendance` (geo-fenced) |

The three **required sequence diagrams** map as:
1. **Login/Authentication** → `/login` + session + role redirect.
2. **Register Student** → `/manager/students/register` (user + student rows).
3. **Room Allocation** → `/manager/rooms/allocate` (bed-availability check + atomic update).
