# AGENTS.md — Hostel Management System (CSE347: Information System Analysis & Design)

> This file is project memory. Read it fully at the start of every new chat about this project.
> Update it at the end of every conversation — see "How to update this file" at the bottom.

---

## 1. Project Snapshot

- **Course**: CSE347 – Information System Analysis and Design
- **Student**: 3rd year, 3rd semester
- **Project**: Hostel Management System
- **Known skill level**: comfortable with HTML, CSS, Python, MySQL. Less experienced with JS/jQuery (assumed — confirm/correct if wrong).
- **Planned stack**: HTML, CSS, JavaScript, jQuery (frontend) · Python (backend — Flask recommended, not yet confirmed) · MySQL (database)
- **Course emphasis**: this is an analysis & design course, so requirements docs, UML diagrams, and DB design carry real weight — not just working code.

---

## 2. Current Status

**Stage: Phase 0 complete + working Flask application built (Phase 4 milestone 1-6). A full MySQL database + complete Flask app is running with all three roles (Manager, Student, Staff). Backend confirmed as Flask with server-rendered Jinja templates (no REST API). Frontend currently uses only one tiny jQuery-free JS file (confirm dialogs). Next up: Phase 1 (use case diagram) and/or drawing the 3 required sequence diagrams, plus styling polish / report screenshots.**

Deliverables produced so far (in `/mnt/user-data/outputs/`):
- `class_diagram.svg` — corrected UML class diagram, 17 classes, generalization from `User`, all relationships/multiplicities per Section 6 decisions
- `hostel_management_schema.sql` — normalized MySQL schema derived directly from the class diagram (users + role subtype tables, all feature tables, FK constraints, a CHECK constraint on violations, indexes)

Application code produced (in project repo):
- `config.py`, `db.py` — DB config + parameterized query/execute helpers (SQL injection safe)
- `app.py` — full Flask app: auth (login/logout/sessions/change-password), all Manager/Student/Staff routes
- `seed_data.sql` — demo data, 4 accounts (manager/admin123, staff1/staff123, student1 & student2/student123)
- `templates/` — base.html + auth/manager/student/staff page families (Jinja2, role-based navbar)
- `static/css/style.css`, `static/js/main.js` — one stylesheet + confirm-dialog script only
- `report.md` — full code walkthrough (request flow, every route, class-method mapping table)
- DB loaded into XAMPP MariaDB (10.4.32, port 3306, root no password): `hostel_management` DB + all 17 tables + seed data. All routes tested via Flask test client (40+ checks pass) and live server boots with HTTP 200.

Uploaded so far:
- `Class_diagram.pdf` (text-based, one class diagram)
- `Requirements_Definition.pdf` (functional + non-functional requirements, 12 functional categories)
- 6 sequence diagram images: Register New Student (mislabeled — actually Visitors), Room Allocation, Complaint, Invoice, Visitors, Parcel

---

## 3. Known Issues Log (from initial review)

### Class Diagram — DESIGN DECIDED, not yet drawn/generated
- [x] Inheritance: `User` is superclass (login, changePassword). `Manager`, `Student`, `Staff` extend it via generalization.
- [x] Caretaker/cook/watchman/guard = values of `Staff.designation`, NOT separate classes.
- [x] `MessMenu` — own class.
- [x] `MessOff`, `Feedback`, `StudentInOut`, `Violation` — kept as lightweight classes (1→0..* from Student; Violation also links to Staff), but implemented in CODE as sub-features inside the Student (and Staff) module rather than standalone big modules.
- [x] Relationships added: `Complaint↔Room`, `Visitor↔Student`, `Parcel↔Student`, `Invoice↔Student`
- [x] `Attendance` split into `StudentAttendance` and `StaffAttendance` (two classes, decided over single generic class)
- [x] Capacity: `Hostel.totalRooms: int` added; `Room.totalBeds: int` added (alongside existing `availableBeds`)
- [x] `Manager.deleteStudent(studentId: int): bool` added
- [x] Typo fixed (multiplicities are consistent `0..*` throughout the generated diagram)
- [x] **Generated**: `class_diagram.svg` delivered — 17 classes total: User, Manager, Student, Staff, Hostel, Room, Complaint, Invoice, StudentAttendance, StaffAttendance, Visitor, Parcel, MessMenu, MessOff, Feedback, StudentInOut, Violation
- [x] **MySQL schema generated**: `hostel_management_schema.sql` — table-per-subtype inheritance (users + managers/students/staff), all FKs in place, Violation has a CHECK constraint enforcing exactly one of student_id/staff_id
- [x] **Role-access gap found & fixed**: original diagram had the data relationships (attendance/violation/visitor tables linked correctly) but no methods on `Manager`/`Staff` to actually access them. Added to `Manager`: `recordStudentAttendance()`, `recordStaffAttendance()`, `viewAttendance()`, `recordViolation()`, `viewViolation()`, `viewVisitorLogs()`. Added to `Staff`: `registerVisitor()`.
- [x] **Visitor contradiction resolved**: requirements doc (9.1) said Manager registers visitors, but the uploaded sequence diagram showed Staff registering them with Manager only viewing logs. Went with the sequence diagram's version (Staff registers, Manager oversees) since it's the more realistic front-desk workflow. Diagram and schema (`visitors.registered_by_staff` FK) both updated to match. **Requirements doc text itself (9.1) still says "Manager" — should be corrected to "Staff" before final submission if the written requirements doc is graded separately.**
- [x] User confirmed: keep ONE detailed 17-class diagram (not split into subsystem diagrams), accepting density as a tradeoff

### Sequence Diagrams
- [x] Scope decided: teacher only requires **2–3** sequence diagrams for lab task (not full module coverage), and wants matching function implementations in code
- [x] Chosen 3: **Login/Authentication** (new), **Register Student** (replaces mislabeled duplicate), **Room Allocation** (already exists, has good `alt` branching — keep as-is)
- [x] **Code implementations now exist for all 3**: `/login` (sessions + role redirect), `/manager/students/register`, `/manager/rooms/allocate` (bed-availability check with `FOR UPDATE`) — mapped 1:1 in report.md §8
- [ ] Login and Register Student diagrams still need to be drawn (don't exist yet) — code functions are ready, so diagrams can mirror them
- [ ] Existing extra diagrams (Complaint, Invoice, Visitor, Parcel) can stay as bonus material in the report but aren't required for the lab grade — low priority
- Note: Invoice diagram's ambiguous initiator (Manager vs Student) not a concern anymore since Invoice isn't one of the 3 required diagrams — only revisit if it's kept in the report

### Requirements Document
- [ ] Sections 8 (Mess), 10 (Feedback), 11 (Student In/Out) have no class-diagram representation at all yet
- [ ] Caretaker appears once (4.2), nowhere else — inconsistent
- [ ] 2.3 (delete student) and 7.4 (staff leaving records) have no matching class methods

**None of the above are fixed yet — this is the immediate next task.**

---

## 4. Project Plan (phases)

- [x] **Phase 0**: Fix requirements/class diagram/sequence diagram inconsistencies (current phase)
- [ ] **Phase 1**: Formal system analysis — finalize actors, add a use case diagram (currently missing entirely)
- [ ] **Phase 2**: System design — corrected class diagram, complete sequence diagram set, ER diagram, normalized MySQL schema, architecture diagram
- [ ] **Phase 3**: UI wireframes for Student dashboard and Manager dashboard
- [ ] **Phase 4**: Implementation — **Milestones 1-6 DONE (skeleton, auth, register student, room allocation, student module, manager module, staff module)**. Milestone 7 (polish) pending.
- [ ] **Phase 5**: Testing against requirements (traceability)
- [ ] **Phase 6**: Final documentation/report (SRS, design doc, ERD, report) — `report.md` drafted, needs final formatting

---

## 5. Open Questions / Decisions Needed

- ~~Confirm backend framework~~ — **RESOLVED: Flask confirmed** (was already installed; Django rejected — lighter for course project). Rendered with Jinja server-side templates, no REST API, to keep JS minimal for beginner skill level.
- Is a working prototype required for grading, or is the deliverable primarily documentation + diagrams? (A full working prototype now exists regardless — this question is about how much polish/effort to put into Phase 4 Milestone 7.)
- Any required diagram types from the course syllabus not yet covered here (e.g., DFDs, activity diagrams, ER diagram in a specific notation)?
- Whichever sequence diagrams are finalized must match real backend function names 1:1 — teacher wants the diagrammed functions actually implemented. (All 3 required flows now have matching code — see report.md §8.)

---

## 6. Decisions Made So Far

- **Caretaker**: not a separate class — it's a `designation` value on `Staff` (along with cook, watchman, guard, etc.)
- **Inheritance**: `User` → `Manager`, `Student`, `Staff` (generalization)
- **MessOff / Feedback / StudentInOut / Violation**: kept as small classes for correct 1-to-many data modeling, but implemented as features bundled inside the Student/Staff module in code rather than standalone large modules
- **Attendance**: split into `StudentAttendance` and `StaffAttendance` rather than one generic class
- **Hostel/Room capacity**: `Hostel.totalRooms`, `Room.totalBeds` added
- **Sequence diagrams for lab**: only 3 required — Login, Register Student, Room Allocation. Others (Complaint, Invoice, Visitor, Parcel) optional bonus content, not required for grading.
- **Backend**: Flask (Django rejected — lighter for a course project, and Flask was already installed on the machine)
- **Frontend style**: server-rendered Jinja templates (NOT a REST API + AJAX/jQuery). Rationale: student is a beginner with JS and comfortable with Python/HTML; server-side rendering needs almost no JS. jQuery deferred until needed.
- **Auth model**: Flask sessions + werkzeug scrypt password hashing; `login_required` + `role_required` decorators; `get_role_id()` resolves the subtype id (manager_id/staff_id/student_id) at login and stores it in the session.
- **DB access**: single `db.py` with `query()`/`execute()` parameterized helpers (SQL-injection-safe `%s` placeholders); one connection per call (fine for a course project).
- **Stored passwords**: `seed_data.sql` uses pre-generated werkzeug scrypt hashes so demo accounts work immediately.

---

## 7. Conventions (filled in as of first build)

- **File/folder structure**: `app.py` (all routes, one file — beginner-friendly), `config.py` (settings), `db.py` (DB helpers), `templates/<role>/<page>.html`, `static/css/style.css`, `static/js/main.js`, `report.md`, `seed_data.sql`
- **DB table naming**: snake_case plural (`students`, `student_attendance`); FKs named `<entity>_id`; ENUMs for status fields
- **Routes**: `/manager/...`, `/student/...`, `/staff/...` prefixes; POST for mutations, GET for views; redirect-after-POST to avoid re-submit
- **Python**: snake_case functions, no code comments (all explanation lives in `report.md`), parameterized SQL via `db.query`/`db.execute` with `%s`
- **Templates**: all extend `base.html`; role-based navbar driven by `session_role`; status shown with `.badge` classes
- **Secrets**: demo `SECRET_KEY` in `config.py` (course project); passwords always werkzeug-scrypt hashed

---

## 8. How to Update This File

At the end of each conversation on this project, update:
1. **Section 2 (Current Status)** — what phase we're in, what was just finished
2. **Section 3 (Known Issues Log)** — check off fixed items, add newly found ones
3. **Section 4 (Project Plan)** — check off completed phases/steps
4. **Section 5 (Open Questions)** — remove answered ones, add new ones
5. **Section 6 (Decisions Made)** — append any new decision with a one-line reason
6. Add a dated entry to the changelog below

> **User policy (2026-08-02):** update this file after EVERY build milestone, every code change, and every major chat — this file is the persistent memory for the project. Do not wait until the end of a "phase".

### Changelog
- **2026-08-02**: Initial file created. Reviewed uploaded class diagram, requirements doc, and 6 sequence diagrams. Logged all flaws found. Proposed 6-phase project plan. No design/code work started yet.
- **2026-08-02 (cont.)**: User resolved most Phase 0 design decisions — inheritance structure, Caretaker-as-designation, mess/feedback/violation classes kept but treated as code-level features, attendance split, hostel/room capacity fields, manager delete method. Scoped sequence diagrams down to 3 required ones (Login, Register Student, Room Allocation) per teacher's lab requirement.
- **2026-08-02 (cont.)**: Generated corrected class diagram (`class_diagram.svg`, built programmatically via Python for accurate layout, visually QA'd before delivery) and full MySQL schema (`hostel_management_schema.sql`, syntax-checked with sqlparse) reflecting all Section 6 decisions. Both delivered to user. Phase 0 is now complete. Still no application code (Flask/HTML/JS) written.
- **2026-08-02 (cont.)**: User caught a real gap — Manager (the admin/superuser role) had no methods to view student/staff attendance, violations, or visitor logs, even though the data relationships existed. Also flagged a genuine contradiction between the requirements doc (Manager registers visitors) and the uploaded sequence diagram (Staff registers visitors). Resolved: added oversight methods to Manager, added `registerVisitor()` to Staff, went with the sequence diagram's staff-registers version, updated both the diagram and schema (`visitors.registered_by_staff`) to match. User chose to keep one single detailed 17-class diagram rather than splitting into subsystem diagrams. Flagged that requirements doc section 9.1 wording still needs a manual text correction if that document is separately graded.
- **2026-08-02 (cont.)**: BUILT THE WORKING APPLICATION. Environment verified: Python 3.14.5, Flask 3.1.3, mysql-connector-python 8.3.0 preinstalled; user installed XAMPP (C:\xampp, MariaDB 10.4.32 on port 3306, root with no password). Loaded schema + created `seed_data.sql` (4 accounts, hashes pre-generated). Built `config.py`, `db.py`, `app.py` (all auth + Manager/Student/Staff routes), 20 Jinja templates + `base.html`, `style.css`, minimal `main.js`. Decision made: **Flask + server-rendered Jinja, no REST API** (beginner-friendly). All 17 classes from the diagram now have working code (mapping table in report.md §8). Tested with Flask test client — 40+ assertions pass (login for each role, register/allocate/attendance/violation/invoice/visitor flows, wrong-password rejection, role-guard blocking) and live server returns HTTP 200. DB reset to clean seed afterwards. User requested this update of AGENTS.md after every build/change/major chat — policy noted in Section 8. Next major remaining task: draw the 3 required sequence diagrams (code exists to mirror) and/or use case diagram.
- **2026-08-02 (cont.)**: Pushed project to GitHub via HTTPS (user chose HTTPS over original SSH commands; repo already existed at github.com/nirjon001/CSE347_project, public). Added README.md + .gitignore, git init, first commit `d05daa6`, branch `main` tracking `origin/main`. Installed GitHub CLI (winget, gh 2.97.0) but auth left to user (Credential Manager pop-up used for HTTPS push). Later the same day: reformed README "Project Structure" from a flat list into a proper directory-tree diagram per user request, and expanded the "Getting Started" section into a full teammate-run guide (prerequisites table, XAMPP + phpMyAdmin + command-line DB import options, config.py password note, run steps, verification checklist, troubleshooting table).
- **2026-08-03**: COMPLETED THE 8-FIX FEATURE PACK (all work below is UNCOMMITTED; user ordered no commit/push until he approves). Fixed: (1) Manager Feedback page added — student feedback was invisible to management; (2) Manager can resolve violations (`/manager/violations/resolve/<id>` sets `status=Resolved` + `resolved_at`, new `violations.status` ENUM + column); (3) Manager can delete staff (`/manager/staff/delete/<id>`; "cannot delete yourself" guard; cascades staff_attendance, SET NULLs visitors/parcels staff refs); (4) custom room capacity — new Add Hostel + Add Room forms (`/manager/hostels/add`, `/manager/rooms/add`, any total_beds >= 1, dup + zero-capacity guards, hostel `total_rooms` auto-increment); (5) Manager Parcels view (`/manager/parcels`) with received_by/collected_by staff names; (6) Mess-off approval assigned to Manager (`/manager/mess-off` approves/rejects pending requests; dashboard now shows pending count); (7) Staff records student returns (`/staff/in-out`, sets `in_date` + `Returned`); (8) Parcels now track who received (`received_by_staff`) and who/when collected (`collected_at`, `collected_by_staff`) — Staff receive/collect actions, Student page shows the trail, old DBs upgraded via new `migrations.sql`. Schema hardening: strict SQL mode (`STRICT_TRANS_TABLES`) set in `db.py` and schema so ENUM/CHECK reject bad values (MariaDB is non-strict by default — caught by tests), and trigger `trg_student_delete_bed` frees a bed on direct `students` deletes (MariaDB does NOT fire triggers on cascaded deletes, so app's `delete_student` also increments `available_beds` explicitly — both paths keep occupied+available=total). Expanded `seed_data.sql` to 9 users / 3 staff / 5 students / 2 hostels / 6 rooms / 4 complaints / 6 invoices / 4 visitors / 5 parcels / 4 violations / 4 mess-off / 4 feedback / 5 in-out / 6 menu. TESTING: Layer 1 SQL integrity suite — 44/44 pass (tables, seed counts, bed invariant, ENUM rejection, CHECK, UNIQUE, FK, cascade + SET NULL on user/staff/manager deletes, trigger, seed-intact after rollback). Layer 2 Flask end-to-end suite — 81/81 pass (all new flows + regressions: add hostel/room, custom-capacity allocate, resolve violation, approve/reject mess-off, feedback visible to manager, delete staff + self-guard, receive/collect parcel with audit trail, mark student returned, role guards). DB reset to clean seed afterwards. Docs updated: report.md (route tables, template families, §6 schema/trigger/MariaDB note, class-diagram mapping), README.md (features, verify steps, accounts, structure tree), this changelog. NEXT: awaiting user approval to commit + push; then remaining diagrams (3 sequence diagrams + use case) per project plan.
- **2026-08-03 (cont.)**: User reported a bug — manager Hostel table showed "-" for Location. Cause: `manager_rooms` route's `hostels` query selected `hostel_id, hostel_name, total_rooms` but omitted `location` (template already rendered `{{ h.location or '-' }}`). Fixed: added `location` to the query. Verified via test client (both "North Campus" and "South Campus" now render). Also: user's attempt to run `migrations.sql` on his already-updated DB failed with "Duplicate column 'status'" — expected, because his DB had been rebuilt from the updated schema during testing (it was already current; explained file-vs-live-database distinction). Rewrote `migrations.sql` to be fully IDEMPOTENT so it can never error again: `ADD COLUMN IF NOT EXISTS` for the 5 columns (MariaDB 10.4 supports it), an `information_schema`-guarded stored procedure for the 2 FK constraints (MariaDB has NO `ADD CONSTRAINT IF NOT EXISTS` — verified empirically: syntax error 1064), and the existing `DROP TRIGGER IF EXISTS`. Tested against a scratch `migration_test` DB mirroring the OLD schema: first run upgrades cleanly, second run is a no-op with zero errors, FK/trigger/columns all present afterwards; real DB verified intact (9 users / 5 students / 5 parcels) after an accidental no-op run during the test. Scratch DB dropped. Docs updated (README/report.md now say "safe to run any time").
- **2026-08-03 (cont.)**: REDESIGNED AUTH PAGES (user: login "sizing issue" + "too plain"). Root causes found: (1) `.auth-wrap` gradient was rendered INSIDE `.container {max-width:1100px}` so the gradient only covered a centered strip — sides showed gray (the "odd" look); (2) `.auth-wrap{min-height:100vh}` + footer + flex-column body = page taller than viewport, scrollbar, footer below fold; (3) duplicate flash rendering — base.html flashes AND login.html flashes (Flask serves only the first, so errors appeared above the gradient, not in the card); (4) card only said "Log In" — no system identity. Fixes (all verified with test client): `base.html` added `{% block body_class %}` on `<body>` + wrapped top flashes in `{% block flashes %}` so auth pages can suppress them; `login.html` now `auth-page` body class, redesigned card with `.auth-logo` monogram "HM", title "Hostel Management System", subtitle, in-card flashes, full-width button, and muted demo-account hint (manager/admin123 etc.); new `show/hide password` toggle — `.password-wrap` + `.toggle-password` button with inline SVG eye/eye-slash icons (no libraries), applied to login AND all 3 fields in change_password.html; `main.js` got a small handler toggling input type + swapping icons; `style.css` full-bleed auth layout (`body.auth-page .container{max-width:none;padding:0;display:flex}`, `.auth-wrap{min-height:calc(100vh - 44px)}`), new logo/toggle/demo styles, `.hero` reworked to full-viewport centered; `home.html` matches (logo + name + tagline + Log In). Verified: `/` & `/login` HTTP 200, auth-page class, 1 toggle btn + 2 svg per password field (3 on change-password), demo hint present, failed login shows ONE flash inside the card. DB untouched.
- **2026-08-03 (cont.)**: NAVBAR USER + FOOTER POLISH (user: `manager (manager)` plain text + footer too plain). Navbar now: `.nav-user` flex row with a circular `.nav-avatar` (30px gradient circle, first letter of username uppercased, e.g. "M"), `.nav-username` (white semibold), and a `.nav-role` pill color-coded per role (gold=manager, blue=staff, green=student). Footer (both `base.html` and `home.html`): `© 2026 Hostel Management System (HMS). All rights reserved.` (user chose "rights only", dropped the CSE347 course line). Verified via test client: avatar letter + role badge correct for manager/staff/student, old `(role)` text gone, rights footer on `/` and authed pages, server HTTP 200. No app.py/DB changes.
