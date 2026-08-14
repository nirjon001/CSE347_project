from datetime import date, datetime, timedelta
from functools import wraps
from math import asin, cos, radians, sin, sqrt
import os
import threading

from flask import (
    Flask, flash, g, jsonify, redirect, render_template, request, session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

import mysql.connector

from config import SECRET_KEY
from db import execute, get_connection, get_dedicated_connection, init_db, query

app = Flask(__name__)
app.secret_key = SECRET_KEY
init_db(app)


@app.route('/healthz')
def healthz():
    query('SELECT 1')
    return 'ok'


@app.errorhandler(500)
def internal_error(e):
    return (
        '<!doctype html><html><head><meta charset="utf-8"><title>Something went wrong</title></head>'
        '<body style="font-family:system-ui;background:#f6f7f9;display:flex;min-height:100vh;align-items:center;justify-content:center;">'
        '<div style="max-width:420px;padding:24px;background:#fff;border-radius:12px;box-shadow:0 4px 16px rgba(0,0,0,.08);">'
        '<h2 style="margin-top:0;color:#c0392b;">Something went wrong</h2>'
        '<p style="color:#555;">The server hit an error while handling your request. Please go back and try again. '
        'If it keeps happening, check the terminal where the server is running for details.</p>'
        '<p><a href="/" style="color:#1d6fb8;">Back to home</a></p></div></body></html>',
        500,
    )


@app.context_processor
def inject_session_user():
    unread = 0
    if 'user_id' in session:
        row = query(
            'SELECT COUNT(*) AS c FROM notifications WHERE user_id = %s AND is_read = 0',
            (session['user_id'],), one=True,
        )
        unread = row['c'] if row else 0
    popup_unread = 0
    if session.pop('show_unread_popup', False) and unread > 0:
        popup_unread = unread
    return {
        'session_role': session.get('role'),
        'session_username': session.get('username'),
        'unread_count': unread,
        'popup_unread': popup_unread,
    }


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper


def role_required(role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get('role') != role:
                flash('You do not have permission to view that page.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return wrapper
    return decorator


def _is_ajax():
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def get_role_id(role, user_id):
    if role == 'manager':
        row = query('SELECT manager_id FROM managers WHERE user_id = %s', (user_id,), one=True)
    elif role == 'staff':
        row = query('SELECT staff_id FROM staff WHERE user_id = %s', (user_id,), one=True)
    elif role == 'student':
        row = query('SELECT student_id FROM students WHERE user_id = %s', (user_id,), one=True)
    else:
        row = None
    return row[list(row)[0]] if row else None


def notify_user(user_id, title, message, link=None):
    execute(
        'INSERT INTO notifications (user_id, title, message, link) VALUES (%s, %s, %s, %s)',
        (user_id, title, message, link),
    )


def notify_managers(title, message, link=None):
    rows = query('SELECT user_id FROM managers')
    for row in rows:
        notify_user(row['user_id'], title, message, link)


def notify_student(student_id, title, message, link=None):
    row = query('SELECT user_id FROM students WHERE student_id = %s', (student_id,), one=True)
    if row:
        notify_user(row['user_id'], title, message, link)


def notify_staff(staff_id, title, message, link=None):
    row = query('SELECT user_id FROM staff WHERE staff_id = %s', (staff_id,), one=True)
    if row:
        notify_user(row['user_id'], title, message, link)


def notify_all_staff(title, message, link=None):
    rows = query('SELECT user_id FROM staff')
    for row in rows:
        notify_user(row['user_id'], title, message, link)


ATT_STATUS = ('Present', 'Absent', 'Leave')
ATT_COLORS = {'Present': '#27ae60', 'Absent': '#e74c3c', 'Leave': '#3498db', 'Not marked': '#95a5a6'}


def _attendance_stats(records):
    counts = {s: 0 for s in ATT_STATUS}
    for r in records:
        if r.get('status') in counts:
            counts[r['status']] += 1
    total = sum(counts.values())
    rate = round(counts['Present'] / total * 100, 1) if total else 0.0
    return counts, total, rate


def _donut_payload(labels, values):
    return {'labels': labels, 'data': values}


def _attendance_trend(records, days=14, end=None):
    if end is None:
        end = date.today()
    start = end - timedelta(days=days - 1)
    by_date = {}
    for r in records:
        key = str(r['date'])
        cell = by_date.setdefault(key, {'Present': 0, 'Absent': 0, 'Leave': 0})
        if r.get('status') in cell:
            cell[r['status']] += r.get('count', 1)
    labels, present, absent, leave = [], [], [], []
    for i in range(days):
        d = start + timedelta(days=i)
        labels.append(d.strftime('%d %b'))
        cell = by_date.get(d.isoformat(), {'Present': 0, 'Absent': 0, 'Leave': 0})
        present.append(cell['Present'])
        absent.append(cell['Absent'])
        leave.append(cell['Leave'])
    return {'labels': labels, 'present': present, 'absent': absent, 'leave': leave}


def distance_m(lat1, lng1, lat2, lng2):
    radius = 6371000.0
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlmb = radians(lng2 - lng1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlmb / 2) ** 2
    return radius * 2 * asin(sqrt(a))


ABSENT_BACKFILL_DAYS = 30
_absent_backfill_last_run = None


def _attendance_floor(table, id_col, join_sql):
    """Earliest date each member should be held accountable from (their first
    attendance record, or their join day if they never marked)."""
    rows = query(
        f'SELECT m.{id_col}, '
        f'COALESCE(MIN(a.date), DATE(u.created_at)) AS floor_date '
        f'FROM {join_sql} m '
        f'JOIN users u ON m.user_id = u.user_id '
        f'LEFT JOIN {table} a ON a.{id_col} = m.{id_col} '
        f'GROUP BY m.{id_col}, u.created_at'
    )
    floors = {}
    for r in rows:
        if r['floor_date']:
            floors[r[id_col]] = r['floor_date']
    return floors


def backfill_absent_days():
    """Lazily mark Absent for any past day (within the last ABSENT_BACKFILL_DAYS
    days, but never today) that a student/staff member has no attendance row
    for. Existing Present/Leave/Absent rows are never overwritten (INSERT
    IGNORE + the UNIQUE(student/date) key). Runs at most once per day via
    @app.before_request, so a day that passes unmarked becomes Absent the next
    time the site is visited."""
    today = date.today()
    start = today - timedelta(days=ABSENT_BACKFILL_DAYS)
    dates = [start + timedelta(days=i) for i in range(ABSENT_BACKFILL_DAYS)]
    dates = [d for d in dates if d < today]
    if not dates:
        return

    student_floors = _attendance_floor(
        'student_attendance', 'student_id', 'students')
    staff_floors = _attendance_floor(
        'staff_attendance', 'staff_id', 'staff')

    for member_id, floor in student_floors.items():
        for d in dates:
            if d < floor:
                continue
            execute(
                'INSERT IGNORE INTO student_attendance (student_id, date, status) '
                'VALUES (%s, %s, %s)',
                (member_id, d, 'Absent'),
            )
    for member_id, floor in staff_floors.items():
        for d in dates:
            if d < floor:
                continue
            execute(
                'INSERT IGNORE INTO staff_attendance (staff_id, date, status) '
                'VALUES (%s, %s, %s)',
                (member_id, d, 'Absent'),
            )


@app.before_request
def _auto_backfill_absent():
    global _absent_backfill_last_run
    if request.endpoint in ('healthz', 'static'):
        return
    if os.environ.get('DB_HOST') == '':
        return
    today = date.today()
    if _absent_backfill_last_run == today:
        return
    _absent_backfill_last_run = today

    def _run_backfill():
        with app.app_context():
            g._db_conn = get_dedicated_connection()
            try:
                backfill_absent_days()
            except Exception:
                pass

    threading.Thread(target=_run_backfill, daemon=True).start()


@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = query('SELECT * FROM users WHERE username = %s', (username,), one=True)
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['role_id'] = get_role_id(user['role'], user['user_id'])
            session['show_unread_popup'] = True
            flash(f'Welcome back, {user["username"]}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('auth/login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))


@app.route('/dashboard')
@login_required
def dashboard():
    role = session.get('role')
    if role == 'manager':
        return redirect(url_for('manager_dashboard'))
    if role == 'student':
        return redirect(url_for('student_dashboard'))
    if role == 'staff':
        return redirect(url_for('staff_dashboard'))
    return redirect(url_for('home'))


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_pwd = request.form.get('old_password', '')
        new_pwd = request.form.get('new_password', '')
        confirm_pwd = request.form.get('confirm_password', '')
        user = query('SELECT * FROM users WHERE user_id = %s', (session['user_id'],), one=True)
        if not check_password_hash(user['password'], old_pwd):
            flash('Current password is incorrect.', 'danger')
        elif new_pwd != confirm_pwd:
            flash('New passwords do not match.', 'danger')
        elif len(new_pwd) < 4:
            flash('New password must be at least 4 characters.', 'danger')
        else:
            hashed = generate_password_hash(new_pwd)
            execute('UPDATE users SET password = %s WHERE user_id = %s', (hashed, session['user_id']))
            flash('Password changed successfully.', 'success')
            return redirect(url_for('dashboard'))
    return render_template('auth/change_password.html')


NOTIF_CATEGORIES = (
    ('Complaints', ('complaint',)),
    ('Mess Off', ('mess-off',)),
    ('Feedback', ('feedback',)),
    ('In / Out', ('student out', 'returned')),
    ('Parcels', ('parcel',)),
    ('Visitors', ('visitor',)),
    ('Attendance', ('attendance',)),
    ('Invoices', ('invoice',)),
    ('Violations', ('violation',)),
    ('Notices', ('notice',)),
    ('Rooms', ('room allocated',)),
)


def _notif_category(title):
    low = (title or '').lower()
    for name, keys in NOTIF_CATEGORIES:
        if any(k in low for k in keys):
            return name
    return 'Other'


@app.route('/notifications')
@login_required
def notifications():
    notifs = query(
        'SELECT * FROM notifications WHERE user_id = %s '
        'ORDER BY created_at DESC, notification_id DESC',
        (session['user_id'],),
    )
    for n in notifs:
        n['category'] = _notif_category(n['title'])
    unread = sum(1 for n in notifs if not n['is_read'])
    cat_counts = {}
    for n in notifs:
        cat_counts[n['category']] = cat_counts.get(n['category'], 0) + 1
    return render_template('notifications.html', notifications=notifs, unread=unread, cat_counts=cat_counts)


@app.route('/notifications/read/<int:notification_id>', methods=['GET', 'POST'])
@login_required
def notification_read(notification_id):
    execute(
        'UPDATE notifications SET is_read = 1 '
        'WHERE notification_id = %s AND user_id = %s',
        (notification_id, session['user_id']),
    )
    notif = query(
        'SELECT link FROM notifications WHERE notification_id = %s',
        (notification_id,), one=True,
    )
    return redirect(notif['link'] if notif and notif['link'] else url_for('notifications'))


@app.route('/notifications/read-all', methods=['POST'])
@login_required
def notifications_read_all():
    execute('UPDATE notifications SET is_read = 1 WHERE user_id = %s', (session['user_id'],))
    if _is_ajax():
        return jsonify(ok=True, message='All notifications marked as read.')
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('notifications'))


# =====================================================================
# MANAGER ROUTES
# =====================================================================

@app.route('/manager')
@login_required
@role_required('manager')
def manager_dashboard():
    stats = {
        'students': query('SELECT COUNT(*) AS c FROM students', one=True)['c'],
        'rooms': query('SELECT COUNT(*) AS c FROM rooms', one=True)['c'],
        'pending_complaints': query("SELECT COUNT(*) AS c FROM complaints WHERE status = 'Pending'", one=True)['c'],
        'unpaid_invoices': query("SELECT COUNT(*) AS c FROM invoices WHERE payment_status = 'Unpaid'", one=True)['c'],
        'open_violations': query("SELECT COUNT(*) AS c FROM violations WHERE status = 'Open'", one=True)['c'],
        'pending_mess_off': query("SELECT COUNT(*) AS c FROM mess_off_requests WHERE status = 'Pending'", one=True)['c'],
        'open_visitors': query('SELECT COUNT(*) AS c FROM visitors', one=True)['c'],
    }
    recent_complaints = query(
        'SELECT c.*, s.name AS student_name FROM complaints c '
        'JOIN students s ON c.student_id = s.student_id '
        'ORDER BY c.date DESC, c.complaint_id DESC LIMIT 5'
    )
    recent_violations = query(
        'SELECT v.*, s.name AS student_name, st.name AS staff_name FROM violations v '
        'LEFT JOIN students s ON v.student_id = s.student_id '
        'LEFT JOIN staff st ON v.staff_id = st.staff_id '
        'ORDER BY v.date DESC, v.violation_id DESC LIMIT 5'
    )
    today_str = date.today().isoformat()
    today_counts = {s: 0 for s in ATT_STATUS}
    for row in query(
        'SELECT status, COUNT(*) AS c FROM student_attendance WHERE date = %s GROUP BY status',
        (today_str,),
    ):
        today_counts[row['status']] += row['c']
    for row in query(
        'SELECT status, COUNT(*) AS c FROM staff_attendance WHERE date = %s GROUP BY status',
        (today_str,),
    ):
        today_counts[row['status']] += row['c']
    registered = stats['students'] + query('SELECT COUNT(*) AS c FROM staff', one=True)['c']
    recorded = sum(today_counts.values())
    today_donut = _donut_payload(
        ['Present', 'Absent', 'Leave', 'Not marked'],
        [today_counts['Present'], today_counts['Absent'], today_counts['Leave'], max(registered - recorded, 0)],
    )
    trend_start = (date.today() - timedelta(days=13)).isoformat()
    trend_records = query(
        'SELECT date, status, COUNT(*) AS count FROM student_attendance WHERE date >= %s GROUP BY date, status',
        (trend_start,),
    )
    trend_records += query(
        'SELECT date, status, COUNT(*) AS count FROM staff_attendance WHERE date >= %s GROUP BY date, status',
        (trend_start,),
    )
    trend14 = _attendance_trend(trend_records, days=14)
    return render_template(
        'manager/dashboard.html', stats=stats,
        recent_complaints=recent_complaints, recent_violations=recent_violations,
        today_donut=today_donut, trend14=trend14,
    )


@app.route('/manager/students')
@login_required
@role_required('manager')
def manager_students():
    students = query(
        'SELECT s.student_id, s.student_no, s.name, s.email, s.phone, s.gender, u.username, r.room_no '
        'FROM students s JOIN users u ON s.user_id = u.user_id '
        'LEFT JOIN rooms r ON s.room_id = r.room_id ORDER BY s.student_id'
    )
    return render_template('manager/students.html', students=students)


@app.route('/manager/students/register', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def register_student():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        gender = request.form.get('gender', '')
        if not (username and password and name):
            flash('Username, password and name are required.', 'danger')
        elif query('SELECT user_id FROM users WHERE username = %s', (username,), one=True):
            flash('That username is already taken.', 'danger')
        else:
            user_id = execute(
                'INSERT INTO users (username, password, role) VALUES (%s, %s, %s)',
                (username, generate_password_hash(password), 'student'),
            )
            next_no = query(
                "SELECT AUTO_INCREMENT AS n FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'students'",
                one=True,
            )['n']
            execute(
                'INSERT INTO students (student_no, user_id, name, email, phone, address, gender) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s)',
                (f'STU-{next_no:04d}', user_id, name, email, phone, address, gender),
            )
            flash(f'Student "{name}" registered successfully.', 'success')
            return redirect(url_for('manager_students'))
    return render_template('manager/register_student.html')


@app.route('/manager/students/delete/<int:student_id>', methods=['POST'])
@login_required
@role_required('manager')
def delete_student(student_id):
    conn = get_dedicated_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute('SELECT user_id, room_id FROM students WHERE student_id = %s', (student_id,))
        student = cur.fetchone()
        if not student:
            flash('Student not found.', 'danger')
            return redirect(url_for('manager_students'))
        cur.execute('DELETE FROM users WHERE user_id = %s', (student['user_id'],))
        # MariaDB does not fire the bed-freed trigger on cascaded deletes,
        # so free the bed explicitly here.
        if student['room_id']:
            cur.execute(
                'UPDATE rooms SET available_beds = available_beds + 1 WHERE room_id = %s',
                (student['room_id'],),
            )
        conn.commit()
        flash('Student deleted successfully.', 'success')
    except Exception:
        conn.rollback()
        flash('Could not delete student.', 'danger')
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('manager_students'))


@app.route('/manager/rooms')
@login_required
@role_required('manager')
def manager_rooms():
    rooms = query(
        'SELECT r.room_id, r.room_no, r.total_beds, r.available_beds, h.hostel_name, h.gender, '
        '(SELECT COUNT(*) FROM students s WHERE s.room_id = r.room_id) AS occupants '
        'FROM rooms r JOIN hostels h ON r.hostel_id = h.hostel_id ORDER BY r.room_id'
    )
    room_students = {}
    for row in query(
        'SELECT s.room_id, s.student_id, s.student_no, s.name, s.email, s.phone '
        'FROM students s WHERE s.room_id IS NOT NULL ORDER BY s.name'
    ):
        room_students.setdefault(row['room_id'], []).append(row)
    for r in rooms:
        r['students'] = room_students.get(r['room_id'], [])
    hostels = query(
        'SELECT h.hostel_id, h.hostel_name, h.location, h.gender, h.lat, h.lng, h.radius_m, '
        '(SELECT COUNT(*) FROM rooms r WHERE r.hostel_id = h.hostel_id) AS total_rooms '
        'FROM hostels h ORDER BY h.hostel_id'
    )
    return render_template('manager/rooms.html', rooms=rooms, hostels=hostels)


def _hostel_form():
    hostel_name = request.form.get('hostel_name', '').strip()[:150]
    location = request.form.get('location', '').strip()[:255]
    gender = request.form.get('gender', '')
    lat = request.form.get('lat', '').strip()
    lng = request.form.get('lng', '').strip()
    radius_m = request.form.get('radius_m', '').strip() or '50'
    try:
        radius_m = int(radius_m)
        radius_m = max(10, min(radius_m, 2000))
        lat_f = float(lat) if lat else None
        lng_f = float(lng) if lng else None
    except ValueError:
        return None, 'Coordinates must be numbers.'
    if not hostel_name:
        return None, 'Hostel name is required.'
    if gender not in ('Male', 'Female'):
        return None, 'Hostel gender is required.'
    return {
        'hostel_name': hostel_name,
        'location': location,
        'gender': gender,
        'lat': lat_f,
        'lng': lng_f,
        'radius_m': radius_m,
    }, None


def _hostel_allocated(hostel_id):
    row = query(
        'SELECT COUNT(*) AS c FROM students s JOIN rooms r ON s.room_id = r.room_id '
        'WHERE r.hostel_id = %s',
        (hostel_id,), one=True,
    )
    return row['c'] if row else 0


def _hostel_same_address(location, exclude_id=None):
    if not location:
        return None
    sql = 'SELECT hostel_id, hostel_name FROM hostels WHERE location = %s'
    params = [location]
    if exclude_id is not None:
        sql += ' AND hostel_id != %s'
        params.append(exclude_id)
    return query(sql, tuple(params), one=True)


@app.route('/manager/hostels/add', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def add_hostel():
    if request.method == 'POST':
        data, err = _hostel_form()
        dup = _hostel_same_address(data['location']) if data else None
        if err:
            flash(err, 'danger')
        elif dup:
            flash(f'Another hostel already uses this address: "{dup["hostel_name"]}". Use a different address.', 'danger')
        else:
            try:
                execute(
                    'INSERT INTO hostels (hostel_name, location, gender, total_rooms, lat, lng, radius_m) '
                    'VALUES (%s, %s, %s, 0, %s, %s, %s)',
                    (data['hostel_name'], data['location'], data['gender'], data['lat'], data['lng'], data['radius_m']),
                )
            except mysql.connector.Error as e:
                flash(f'Could not add the hostel: {e}', 'danger')
            else:
                flash(f'Hostel "{data["hostel_name"]}" added.', 'success')
                return redirect(url_for('manager_rooms'))
    return render_template('manager/add_hostel.html')


@app.route('/manager/hostels/edit/<int:hostel_id>', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def edit_hostel(hostel_id):
    hostel = query('SELECT * FROM hostels WHERE hostel_id = %s', (hostel_id,), one=True)
    if not hostel:
        flash('Hostel not found.', 'danger')
        return redirect(url_for('manager_rooms'))
    if request.method == 'POST':
        data, err = _hostel_form()
        dup = _hostel_same_address(data['location'], exclude_id=hostel_id) if data else None
        if err:
            flash(err, 'danger')
        elif dup:
            flash(f'Another hostel already uses this address: "{dup["hostel_name"]}". Use a different address.', 'danger')
        elif data['gender'] != hostel['gender'] and _hostel_allocated(hostel_id):
            flash('Cannot change the hostel gender while students are allocated to it. Move them first.', 'danger')
        else:
            try:
                execute(
                    'UPDATE hostels SET hostel_name=%s, location=%s, gender=%s, lat=%s, lng=%s, radius_m=%s '
                    'WHERE hostel_id=%s',
                    (data['hostel_name'], data['location'], data['gender'], data['lat'], data['lng'],
                     data['radius_m'], hostel_id),
                )
            except mysql.connector.Error as e:
                flash(f'Could not save the hostel: {e}', 'danger')
            else:
                flash(f'Hostel "{data["hostel_name"]}" updated.', 'success')
                return redirect(url_for('manager_rooms'))
        if data:
            hostel = {**hostel, **data}
    return render_template('manager/add_hostel.html', hostel=hostel)


@app.route('/manager/hostels/delete/<int:hostel_id>', methods=['POST'])
@login_required
@role_required('manager')
def delete_hostel(hostel_id):
    hostel = query('SELECT * FROM hostels WHERE hostel_id = %s', (hostel_id,), one=True)
    if not hostel:
        flash('Hostel not found.', 'danger')
        return redirect(url_for('manager_rooms'))
    allocated = _hostel_allocated(hostel_id)
    if allocated:
        flash(
            f'Cannot delete "{hostel["hostel_name"]}": {allocated} student(s) are still allocated to it. '
            'Move or delete them first.',
            'danger',
        )
        return redirect(url_for('manager_rooms'))
    execute('DELETE FROM hostels WHERE hostel_id = %s', (hostel_id,))
    flash(f'Hostel "{hostel["hostel_name"]}" deleted (its rooms were removed too).', 'success')
    return redirect(url_for('manager_rooms'))


@app.route('/manager/rooms/add', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def add_room():
    if request.method == 'POST':
        hostel_id = request.form.get('hostel_id')
        room_no = request.form.get('room_no', '').strip()
        total_beds = request.form.get('total_beds', '0')
        try:
            total_beds = int(total_beds)
        except ValueError:
            total_beds = 0
        if not (hostel_id and room_no):
            flash('Hostel and room number are required.', 'danger')
        elif total_beds < 1:
            flash('Capacity must be at least 1.', 'danger')
        elif query('SELECT room_id FROM rooms WHERE hostel_id = %s AND room_no = %s', (hostel_id, room_no), one=True):
            flash('That room number already exists in this hostel.', 'danger')
        else:
            execute(
                'INSERT INTO rooms (hostel_id, room_no, total_beds, available_beds) VALUES (%s, %s, %s, %s)',
                (hostel_id, room_no, total_beds, total_beds),
            )
            execute('UPDATE hostels SET total_rooms = total_rooms + 1 WHERE hostel_id = %s', (hostel_id,))
            flash(f'Room {room_no} added with {total_beds} beds.', 'success')
            return redirect(url_for('manager_rooms'))
    hostels = query('SELECT hostel_id, hostel_name, gender FROM hostels ORDER BY hostel_id')
    return render_template('manager/add_room.html', hostels=hostels)


@app.route('/manager/rooms/allocate', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def allocate_room():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        room_id = request.form.get('room_id')
        student = query('SELECT gender FROM students WHERE student_id = %s', (student_id,), one=True)
        room = query(
            'SELECT h.gender AS hostel_gender, h.hostel_name, r.room_no FROM rooms r '
            'JOIN hostels h ON r.hostel_id = h.hostel_id WHERE r.room_id = %s',
            (room_id,), one=True,
        )
        if not student or not room:
            flash('Invalid student or room selected.', 'danger')
            return redirect(url_for('allocate_room'))
        if student['gender'] != room['hostel_gender']:
            flash(
                f'Gender mismatch: a {student["gender"]} student cannot be placed in the '
                f'{room["hostel_name"]} ({room["hostel_gender"]}) hostel.',
                'danger',
            )
            return redirect(url_for('allocate_room'))
        conn = get_dedicated_connection()
        allocated = False
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute('SELECT available_beds FROM rooms WHERE room_id = %s FOR UPDATE', (room_id,))
            room_row = cur.fetchone()
            if not room_row or room_row['available_beds'] <= 0:
                flash('No beds available in that room.', 'danger')
            else:
                cur.execute('UPDATE rooms SET available_beds = available_beds - 1 WHERE room_id = %s', (room_id,))
                cur.execute('UPDATE students SET room_id = %s WHERE student_id = %s', (room_id, student_id))
                conn.commit()
                allocated = True
                flash('Room allocated successfully.', 'success')
        except Exception:
            conn.rollback()
            flash('Allocation failed. Please try again.', 'danger')
        finally:
            cur.close()
            conn.close()
        if allocated:
            notify_student(
                student_id, 'Room allocated',
                f'You have been allocated {room["room_no"]} in the {room["hostel_name"]} hostel.',
                '/student/room',
            )
        return redirect(url_for('allocate_room'))
    unallocated = query('SELECT student_id, student_no, name, gender FROM students WHERE room_id IS NULL ORDER BY student_id')
    free_rooms = query(
        'SELECT r.room_id, r.room_no, r.available_beds, h.gender '
        'FROM rooms r JOIN hostels h ON r.hostel_id = h.hostel_id '
        'WHERE r.available_beds > 0 ORDER BY r.room_id'
    )
    return render_template('manager/allocate_room.html', students=unallocated, rooms=free_rooms)


@app.route('/manager/complaints', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def manager_complaints():
    if request.method == 'POST':
        complaint_id = request.form.get('complaint_id')
        status = request.form.get('status')
        complaint = query(
            'SELECT student_id FROM complaints WHERE complaint_id = %s',
            (complaint_id,), one=True,
        )
        execute('UPDATE complaints SET status = %s WHERE complaint_id = %s', (status, complaint_id))
        if complaint:
            notify_student(
                complaint['student_id'],
                'Complaint update',
                f'Your complaint status is now "{status}".',
                '/student/complaints',
            )
        if _is_ajax():
            return jsonify(ok=True, message='Complaint status updated.', status=status)
        flash('Complaint status updated.', 'success')
        return redirect(url_for('manager_complaints'))
    complaints = query(
        'SELECT c.*, s.student_no, s.name AS student_name, r.room_no, h.hostel_name '
        'FROM complaints c JOIN students s ON c.student_id = s.student_id '
        'LEFT JOIN rooms r ON COALESCE(c.room_id, s.room_id) = r.room_id '
        'LEFT JOIN hostels h ON r.hostel_id = h.hostel_id '
        'ORDER BY c.date DESC, c.complaint_id DESC'
    )
    return render_template('manager/complaints.html', complaints=complaints)


INVOICE_TYPES = ('Room Rent', 'Electricity', 'Food', 'Water', 'Other')


def _invoice_amount_field(invoice_type):
    return 'amount_' + invoice_type.lower().replace(' ', '_')


def _invoice_notification_message(created, due_date):
    total = round(sum(a for _, a in created), 2)
    parts = ', '.join(f'{t} ${a:,.2f}' for t, a in created)
    return f'New invoices issued: {parts} (total ${total:,.2f}). Due date: {due_date}.'


def _invoice_receipt_data(invoice_id):
    return query(
        'SELECT i.*, s.name AS student_name, s.student_no, r.room_no, h.hostel_name, h.location '
        'FROM invoices i '
        'JOIN students s ON i.student_id = s.student_id '
        'LEFT JOIN rooms r ON s.room_id = r.room_id '
        'LEFT JOIN hostels h ON r.hostel_id = h.hostel_id '
        'WHERE i.invoice_id = %s',
        (invoice_id,), one=True,
    )


def _student_invoice_statement(student_id):
    student = query(
        'SELECT s.student_id, s.student_no, s.name AS student_name, r.room_no, h.hostel_name, h.location '
        'FROM students s '
        'LEFT JOIN rooms r ON s.room_id = r.room_id '
        'LEFT JOIN hostels h ON r.hostel_id = h.hostel_id '
        'WHERE s.student_id = %s',
        (student_id,), one=True,
    )
    if not student:
        return None, None, None
    invoices = query(
        'SELECT * FROM invoices WHERE student_id = %s ORDER BY invoice_id',
        (student_id,),
    )
    totals = query(
        'SELECT COUNT(*) AS count, '
        'COALESCE(SUM(amount), 0) AS total, '
        'COALESCE(SUM(CASE WHEN payment_status = "Paid" THEN amount ELSE 0 END), 0) AS paid, '
        'COALESCE(SUM(CASE WHEN payment_status <> "Paid" THEN amount ELSE 0 END), 0) AS unpaid '
        'FROM invoices WHERE student_id = %s',
        (student_id,), one=True,
    )
    return student, invoices, totals


@app.route('/manager/invoices', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def manager_invoices():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        due_date = request.form.get('due_date')
        created = []
        bad_types = []
        for t in INVOICE_TYPES:
            raw = request.form.get(_invoice_amount_field(t), '').strip()
            if not raw:
                continue
            try:
                amount = round(float(raw), 2)
            except ValueError:
                bad_types.append(t)
                continue
            if amount <= 0:
                bad_types.append(t)
                continue
            execute(
                'INSERT INTO invoices (student_id, invoice_type, amount, due_date, payment_status) '
                'VALUES (%s, %s, %s, %s, %s)',
                (student_id, t, amount, due_date, 'Unpaid'),
            )
            created.append((t, amount))
        if not created:
            if bad_types:
                flash('No invoices generated — the amount entered for '
                      f'{", ".join(bad_types)} was not a valid number.', 'danger')
            else:
                flash('Enter at least one invoice amount.', 'danger')
        else:
            notify_student(
                student_id,
                'New invoices',
                _invoice_notification_message(created, due_date),
                '/student/invoices',
            )
            flash(f'{len(created)} invoice(s) generated for the student.', 'success')
        return redirect(url_for('manager_invoices'))
    invoices = query(
        'SELECT i.*, s.name AS student_name FROM invoices i '
        'JOIN students s ON i.student_id = s.student_id ORDER BY i.invoice_id DESC'
    )
    students = query('SELECT student_id, student_no, name FROM students ORDER BY student_id')
    student_summary = query(
        'SELECT s.student_id, s.student_no, s.name AS student_name, '
        'MIN(i.invoice_id) AS first_invoice_id, '
        'COUNT(*) AS count, SUM(i.amount) AS total, '
        'GROUP_CONCAT(i.invoice_type ORDER BY i.invoice_id SEPARATOR ", ") AS types '
        'FROM invoices i JOIN students s ON i.student_id = s.student_id '
        'GROUP BY s.student_id, s.student_no, s.name ORDER BY first_invoice_id'
    )
    summary = query(
        'SELECT invoice_type, COUNT(*) AS count, SUM(amount) AS total '
        'FROM invoices GROUP BY invoice_type ORDER BY invoice_type'
    )
    grand = query('SELECT COUNT(*) AS count, SUM(amount) AS total FROM invoices', one=True)
    return render_template(
        'manager/invoices.html', invoices=invoices, students=students,
        student_summary=student_summary, summary=summary, grand=grand,
        invoice_types=INVOICE_TYPES,
    )


@app.route('/manager/invoices/toggle/<int:invoice_id>', methods=['POST'])
@login_required
@role_required('manager')
def toggle_invoice(invoice_id):
    invoice = query('SELECT payment_status FROM invoices WHERE invoice_id = %s', (invoice_id,), one=True)
    new_status = 'Paid' if invoice['payment_status'] != 'Paid' else 'Unpaid'
    execute('UPDATE invoices SET payment_status = %s WHERE invoice_id = %s', (new_status, invoice_id))
    if _is_ajax():
        return jsonify(ok=True, message=f'Invoice marked {new_status}.', status=new_status)
    flash(f'Invoice marked {new_status}.', 'success')
    return redirect(url_for('manager_invoices'))


@app.route('/manager/invoices/print/<int:invoice_id>')
@login_required
@role_required('manager')
def manager_invoice_print(invoice_id):
    invoice = _invoice_receipt_data(invoice_id)
    if not invoice:
        flash('Invoice not found.', 'danger')
        return redirect(url_for('manager_invoices'))
    return render_template('invoice_print.html', invoice=invoice)


@app.route('/manager/invoices/print-student/<int:student_id>')
@login_required
@role_required('manager')
def manager_invoice_statement_print(student_id):
    student, invoices, totals = _student_invoice_statement(student_id)
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('manager_invoices'))
    return render_template(
        'invoice_statement_print.html', student=student, invoices=invoices, totals=totals,
        today=date.today(),
    )


@app.route('/manager/attendance', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def manager_attendance():
    if request.method == 'POST':
        kind = request.form.get('kind')
        att_date = request.form.get('date')
        status = request.form.get('status')
        if kind == 'student':
            student_id = request.form.get('student_id')
            execute(
                'INSERT INTO student_attendance (student_id, date, status) VALUES (%s, %s, %s) '
                'ON DUPLICATE KEY UPDATE status = %s',
                (student_id, att_date, status, status),
            )
            notify_student(
                student_id, 'Attendance',
                f'Your attendance was marked as {status} for {att_date}.',
                '/student/attendance',
            )
        else:
            staff_id = request.form.get('student_id')
            execute(
                'INSERT INTO staff_attendance (staff_id, date, status) VALUES (%s, %s, %s) '
                'ON DUPLICATE KEY UPDATE status = %s',
                (staff_id, att_date, status, status),
            )
            notify_staff(
                staff_id, 'Attendance',
                f'Your attendance was marked as {status} for {att_date}.',
                '/staff/attendance',
            )
        flash('Attendance recorded.', 'success')
        return redirect(url_for('manager_attendance'))
    students = query('SELECT student_id, student_no, name FROM students ORDER BY student_id')
    staff_members = query('SELECT staff_id, staff_no, name FROM staff ORDER BY staff_id')
    student_attendance = query(
        'SELECT a.*, s.student_no, s.name FROM student_attendance a JOIN students s ON a.student_id = s.student_id '
        'ORDER BY a.date DESC, a.attendance_id DESC LIMIT 15'
    )
    staff_attendance = query(
        'SELECT a.*, st.staff_no, st.name FROM staff_attendance a JOIN staff st ON a.staff_id = st.staff_id '
        'ORDER BY a.date DESC, a.attendance_id DESC LIMIT 15'
    )

    person_type = request.args.get('person_type')
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    person = None
    person_records = []
    person_stats = None
    person_donut = None
    person_trend = None

    person_id = request.args.get('person_id')
    try:
        person_id = int(person_id) if person_id else None
    except (TypeError, ValueError):
        person_id = None

    if person_type in ('student', 'staff') and person_id:
        where = []
        params = []
        if from_date:
            where.append('date >= %s')
            params.append(from_date)
        if to_date:
            where.append('date <= %s')
            params.append(to_date)
        if person_type == 'student':
            where.append('student_id = %s')
            params.append(person_id)
        else:
            where.append('staff_id = %s')
            params.append(person_id)
        where_sql = (' WHERE ' + ' AND '.join(where)) if where else ''
        if person_type == 'student':
            person = query(
                'SELECT student_id, student_no, name FROM students WHERE student_id = %s',
                (person_id,), one=True,
            )
            person_records = query(
                'SELECT * FROM student_attendance' + where_sql + ' ORDER BY date DESC, attendance_id DESC',
                tuple(params),
            )
        else:
            person = query(
                'SELECT staff_id, staff_no, name FROM staff WHERE staff_id = %s',
                (person_id,), one=True,
            )
            person_records = query(
                'SELECT * FROM staff_attendance' + where_sql + ' ORDER BY date DESC, attendance_id DESC',
                tuple(params),
            )
        counts, total, rate = _attendance_stats(person_records)
        person_stats = {
            'present': counts['Present'], 'absent': counts['Absent'],
            'leave': counts['Leave'], 'rate': rate,
        }
        person_donut = _donut_payload(
            ['Present', 'Absent', 'Leave'],
            [counts['Present'], counts['Absent'], counts['Leave']],
        )
        try:
            end = date.fromisoformat(to_date) if to_date else date.today()
            if from_date and to_date:
                days = (end - date.fromisoformat(from_date)).days + 1
                days = max(days, 1)
            else:
                days = 30
            person_trend = _attendance_trend(person_records, days=days, end=end)
        except ValueError:
            person_trend = _attendance_trend(person_records, days=30, end=date.today())

    return render_template(
        'manager/attendance.html', students=students, staff_members=staff_members,
        student_attendance=student_attendance, staff_attendance=staff_attendance,
        person_type=person_type, person=person, person_records=person_records,
        person_stats=person_stats, person_donut=person_donut, person_trend=person_trend,
        from_date=from_date, to_date=to_date,
    )


@app.route('/manager/attendance/update', methods=['POST'])
@login_required
@role_required('manager')
def manager_attendance_update():
    person_type = request.form.get('person_type')
    person_id = request.form.get('person_id')
    att_date = request.form.get('att_date')
    status = request.form.get('status')
    from_date = request.form.get('from_date', '')
    to_date = request.form.get('to_date', '')
    try:
        person_id = int(person_id) if person_id else None
    except (TypeError, ValueError):
        person_id = None
    if person_type not in ('student', 'staff') or not person_id or not att_date:
        if _is_ajax():
            return jsonify(ok=False, message='Invalid attendance update request.')
        flash('Invalid attendance update request.', 'danger')
    elif status not in ATT_STATUS:
        if _is_ajax():
            return jsonify(ok=False, message='Invalid status.')
        flash('Invalid status.', 'danger')
    else:
        if person_type == 'student':
            execute(
                'INSERT INTO student_attendance (student_id, date, status) VALUES (%s, %s, %s) '
                'ON DUPLICATE KEY UPDATE status = %s',
                (person_id, att_date, status, status),
            )
            notify_student(
                person_id, 'Attendance',
                f'Your attendance for {att_date} was updated to {status}.',
                '/student/attendance',
            )
        else:
            execute(
                'INSERT INTO staff_attendance (staff_id, date, status) VALUES (%s, %s, %s) '
                'ON DUPLICATE KEY UPDATE status = %s',
                (person_id, att_date, status, status),
            )
            notify_staff(
                person_id, 'Attendance',
                f'Your attendance for {att_date} was updated to {status}.',
                '/staff/attendance',
            )
        if _is_ajax():
            return jsonify(ok=True, message='Attendance updated.', status=status)
        flash('Attendance updated.', 'success')
    return redirect(url_for(
        'manager_attendance', person_type=person_type, person_id=person_id,
        from_date=from_date or None, to_date=to_date or None,
    ))


@app.route('/manager/mess-menu', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def manager_mess_menu():
    if request.method == 'POST':
        day = request.form.get('day_of_week')
        meal = request.form.get('meal_type')
        items = request.form.get('items_description', '').strip()
        if items:
            execute(
                'INSERT INTO mess_menu (manager_id, day_of_week, meal_type, items_description) '
                'VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE items_description = %s',
                (session['role_id'], day, meal, items, items),
            )
            flash('Mess menu updated.', 'success')
        return redirect(url_for('manager_mess_menu'))
    menu = query('SELECT * FROM mess_menu ORDER BY FIELD(day_of_week, %s, %s, %s, %s, %s, %s, %s), FIELD(meal_type, %s, %s, %s)',
                 ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday', 'Breakfast', 'Lunch', 'Dinner'))
    return render_template('manager/mess_menu.html', menu=menu)


@app.route('/manager/violations', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def manager_violations():
    if request.method == 'POST':
        action = request.form.get('action', 'record')
        if action == 'notice':
            recipient_type = request.form.get('recipient_type')
            recipient_id = request.form.get('recipient_id')
            message = request.form.get('message', '').strip()
            if message and recipient_id:
                if recipient_type == 'student':
                    notify_student(recipient_id, 'Notice from the hostel', message)
                else:
                    notify_staff(recipient_id, 'Notice from the hostel', message)
                flash('Notification sent.', 'success')
            else:
                flash('Recipient and message are required.', 'danger')
        elif action == 'row_notify':
            violation_id = request.form.get('violation_id')
            message = request.form.get('message', '').strip()
            row = query(
                'SELECT student_id, staff_id FROM violations WHERE violation_id = %s',
                (violation_id,), one=True,
            ) if violation_id else None
            if not row:
                flash('Violation not found.', 'danger')
            elif not message:
                flash('Message is required.', 'danger')
            else:
                if row['student_id']:
                    notify_student(row['student_id'], 'Violation', message)
                elif row['staff_id']:
                    notify_staff(row['staff_id'], 'Violation', message)
                flash('Notification sent to the violator.', 'success')
        else:
            target = request.form.get('target')
            target_id = request.form.get('target_id')
            description = request.form.get('description', '').strip()
            notify = request.form.get('notify') == 'on'
            custom_message = request.form.get('notify_message', '').strip()
            if target == 'student':
                execute(
                    'INSERT INTO violations (student_id, staff_id, description, date, recorded_by) '
                    'VALUES (%s, NULL, %s, %s, %s)',
                    (target_id, description, date.today().isoformat(), session['role_id']),
                )
            else:
                execute(
                    'INSERT INTO violations (student_id, staff_id, description, date, recorded_by) '
                    'VALUES (NULL, %s, %s, %s, %s)',
                    (target_id, description, date.today().isoformat(), session['role_id']),
                )
            if notify:
                message = custom_message or f'You received a violation: {description[:150]}'
                if target == 'student':
                    notify_student(target_id, 'Violation', message)
                else:
                    notify_staff(target_id, 'Violation', message)
            flash('Violation recorded.', 'success')
        return redirect(url_for('manager_violations'))
    violations = query(
        'SELECT v.*, s.student_no, s.name AS student_name, st.staff_no, st.name AS staff_name FROM violations v '
        'LEFT JOIN students s ON v.student_id = s.student_id '
        'LEFT JOIN staff st ON v.staff_id = st.staff_id '
        'ORDER BY v.date DESC, v.violation_id DESC'
    )
    students = query('SELECT student_id, student_no, name FROM students ORDER BY student_id')
    staff_members = query('SELECT staff_id, staff_no, name FROM staff ORDER BY staff_id')
    return render_template('manager/violations.html', violations=violations, students=students, staff_members=staff_members)


@app.route('/manager/notify', methods=['POST'])
@login_required
@role_required('manager')
def manager_notify():
    recipient_type = request.form.get('recipient_type')
    recipient_id = request.form.get('recipient_id')
    message = request.form.get('message', '').strip()
    if message and recipient_id:
        if recipient_type == 'student':
            notify_student(recipient_id, 'Notice from the hostel', message)
        else:
            notify_staff(recipient_id, 'Notice from the hostel', message)
        flash('Notification sent.', 'success')
    else:
        flash('Recipient and message are required.', 'danger')
    return redirect(url_for('manager_violations'))


@app.route('/manager/violations/resolve/<int:violation_id>', methods=['POST'])
@login_required
@role_required('manager')
def resolve_violation(violation_id):
    violation = query(
        'SELECT student_id, staff_id FROM violations WHERE violation_id = %s',
        (violation_id,), one=True,
    )
    execute(
        'UPDATE violations SET status = %s, resolved_at = %s WHERE violation_id = %s',
        ('Resolved', date.today().isoformat(), violation_id),
    )
    if violation:
        if violation['student_id']:
            notify_student(
                violation['student_id'], 'Violation',
                'Your violation was marked as resolved.',
            )
        elif violation['staff_id']:
            notify_staff(
                violation['staff_id'], 'Violation',
                'Your violation was marked as resolved.',
            )
    if _is_ajax():
        return jsonify(ok=True, message='Violation marked as resolved.', status='Resolved')
    flash('Violation marked as resolved.', 'success')
    return redirect(url_for('manager_violations'))


@app.route('/manager/feedback')
@login_required
@role_required('manager')
def manager_feedback():
    feedbacks = query(
        'SELECT f.*, s.student_no, s.name AS student_name FROM feedback f '
        'JOIN students s ON f.student_id = s.student_id '
        'ORDER BY f.date DESC, f.feedback_id DESC'
    )
    return render_template('manager/feedback.html', feedbacks=feedbacks)


@app.route('/manager/mess-off', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def manager_mess_off():
    if request.method == 'POST':
        request_id = request.form.get('request_id')
        status = request.form.get('status')
        mess_off = query(
            'SELECT student_id FROM mess_off_requests WHERE mess_off_id = %s',
            (request_id,), one=True,
        )
        execute('UPDATE mess_off_requests SET status = %s WHERE mess_off_id = %s', (status, request_id))
        if mess_off:
            notify_student(
                mess_off['student_id'], 'Mess-off request',
                f'Your mess-off request was {status.lower()}.',
                '/student/mess-off',
            )
        if _is_ajax():
            return jsonify(ok=True, message=f'Mess off request {status.lower()}.', status=status)
        flash(f'Mess off request {status.lower()}.', 'success')
        return redirect(url_for('manager_mess_off'))
    requests = query(
        'SELECT r.*, s.student_no, s.name AS student_name FROM mess_off_requests r '
        'JOIN students s ON r.student_id = s.student_id '
        'ORDER BY r.start_date DESC, r.mess_off_id DESC'
    )
    return render_template('manager/mess_off.html', requests=requests)


@app.route('/manager/parcels')
@login_required
@role_required('manager')
def manager_parcels():
    parcels = query(
        'SELECT p.*, s.student_no, s.name AS student_name, r.name AS received_by, c.name AS collected_by '
        'FROM parcels p JOIN students s ON p.student_id = s.student_id '
        'LEFT JOIN staff r ON p.received_by_staff = r.staff_id '
        'LEFT JOIN students c ON p.collected_by_student = c.student_id '
        'ORDER BY p.received_date DESC, p.parcel_id DESC'
    )
    return render_template('manager/parcels.html', parcels=parcels)


@app.route('/manager/visitors')
@login_required
@role_required('manager')
def manager_visitors():
    visitors = query(
        'SELECT v.*, s.student_no, s.name AS student_name, st.staff_no, st.name AS registered_by '
        'FROM visitors v JOIN students s ON v.student_id = s.student_id '
        'LEFT JOIN staff st ON v.registered_by_staff = st.staff_id '
        'ORDER BY v.visit_date DESC, v.visitor_id DESC'
    )
    return render_template('manager/visitors.html', visitors=visitors)


@app.route('/manager/staff', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def manager_staff():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        name = request.form.get('name', '').strip()
        designation = request.form.get('designation', '').strip()
        salary = request.form.get('salary', '0')
        if not (username and password and name and designation):
            flash('All fields are required.', 'danger')
        elif query('SELECT user_id FROM users WHERE username = %s', (username,), one=True):
            flash('That username is already taken.', 'danger')
        else:
            user_id = execute(
                'INSERT INTO users (username, password, role) VALUES (%s, %s, %s)',
                (username, generate_password_hash(password), 'staff'),
            )
            next_no = query(
                "SELECT AUTO_INCREMENT AS n FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'staff'",
                one=True,
            )['n']
            execute(
                'INSERT INTO staff (staff_no, user_id, name, designation, salary) '
                'VALUES (%s, %s, %s, %s, %s)',
                (f'STF-{next_no:04d}', user_id, name, designation, salary),
            )
            flash(f'Staff "{name}" added.', 'success')
            return redirect(url_for('manager_staff'))
    staff_members = query('SELECT st.*, u.username FROM staff st JOIN users u ON st.user_id = u.user_id ORDER BY st.staff_id')
    return render_template('manager/staff.html', staff_members=staff_members)


@app.route('/manager/staff/delete/<int:staff_id>', methods=['POST'])
@login_required
@role_required('manager')
def delete_staff(staff_id):
    if staff_id == session.get('role_id'):
        flash('You cannot delete yourself.', 'danger')
        return redirect(url_for('manager_staff'))
    conn = get_dedicated_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute('SELECT user_id FROM staff WHERE staff_id = %s', (staff_id,))
        staff = cur.fetchone()
        if not staff:
            flash('Staff not found.', 'danger')
            return redirect(url_for('manager_staff'))
        cur.execute('DELETE FROM users WHERE user_id = %s', (staff['user_id'],))
        conn.commit()
        flash('Staff deleted successfully.', 'success')
    except Exception:
        conn.rollback()
        flash('Could not delete staff.', 'danger')
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('manager_staff'))


# =====================================================================
# STUDENT ROUTES
# =====================================================================

@app.route('/student')
@login_required
@role_required('student')
def student_dashboard():
    student = query(
        'SELECT s.*, r.room_no, r.total_beds, h.hostel_name FROM students s '
        'LEFT JOIN rooms r ON s.room_id = r.room_id '
        'LEFT JOIN hostels h ON r.hostel_id = h.hostel_id '
        'WHERE s.student_id = %s', (session['role_id'],), one=True,
    )
    unpaid = query(
        'SELECT COUNT(*) AS c FROM invoices WHERE student_id = %s AND payment_status <> %s',
        (session['role_id'], 'Paid'), one=True,
    )['c']
    pending_complaints = query(
        "SELECT COUNT(*) AS c FROM complaints WHERE student_id = %s AND status <> 'Resolved'",
        (session['role_id'],), one=True,
    )['c']
    parcels = query(
        "SELECT COUNT(*) AS c FROM parcels WHERE student_id = %s AND status = 'Arrived'",
        (session['role_id'],), one=True,
    )['c']
    today = date.today().strftime('%A')
    menu = query('SELECT * FROM mess_menu WHERE day_of_week = %s', (today,))
    return render_template(
        'student/dashboard.html', student=student, unpaid=unpaid,
        pending_complaints=pending_complaints, parcels=parcels, menu=menu, today=today,
    )


@app.route('/student/profile', methods=['GET', 'POST'])
@login_required
@role_required('student')
def student_profile():
    student = query('SELECT * FROM students WHERE student_id = %s', (session['role_id'],), one=True)
    if request.method == 'POST':
        new_gender = request.form.get('gender', '')
        if student['gender'] != new_gender and student['room_id']:
            room_hostel = query(
                'SELECT h.gender FROM rooms r JOIN hostels h ON r.hostel_id = h.hostel_id '
                'WHERE r.room_id = %s',
                (student['room_id'],), one=True,
            )
            if room_hostel and room_hostel['gender'] != new_gender:
                flash(
                    f'Cannot change gender to {new_gender} while allocated to the '
                    f'{room_hostel["gender"]} hostel.',
                    'danger',
                )
                return redirect(url_for('student_profile'))
        execute(
            'UPDATE students SET email = %s, phone = %s, address = %s, gender = %s '
            'WHERE student_id = %s',
            (
                request.form.get('email', '').strip(),
                request.form.get('phone', '').strip(),
                request.form.get('address', '').strip(),
                new_gender,
                session['role_id'],
            ),
        )
        flash('Profile updated.', 'success')
        return redirect(url_for('student_profile'))
    return render_template('student/profile.html', student=student)


@app.route('/student/room')
@login_required
@role_required('student')
def student_room():
    student = query(
        'SELECT s.name, r.room_no, r.total_beds, r.available_beds, h.hostel_name, h.location '
        'FROM students s LEFT JOIN rooms r ON s.room_id = r.room_id '
        'LEFT JOIN hostels h ON r.hostel_id = h.hostel_id WHERE s.student_id = %s',
        (session['role_id'],), one=True,
    )
    return render_template('student/room.html', student=student)


@app.route('/student/complaints', methods=['GET', 'POST'])
@login_required
@role_required('student')
def student_complaints():
    if request.method == 'POST':
        description = request.form.get('description', '').strip()
        if description:
            student = query(
                'SELECT name, room_id FROM students WHERE student_id = %s',
                (session['role_id'],), one=True,
            )
            execute(
                'INSERT INTO complaints (student_id, room_id, description, status, date) '
                'VALUES (%s, %s, %s, %s, %s)',
                (session['role_id'], student['room_id'], description, 'Pending', date.today().isoformat()),
            )
            notify_managers(
                'New complaint',
                f"{student['name']} submitted a complaint: {description[:100]}",
                '/manager/complaints',
            )
            flash('Complaint submitted.', 'success')
        return redirect(url_for('student_complaints'))
    complaints = query(
        'SELECT c.*, r.room_no, h.hostel_name '
        'FROM complaints c '
        'JOIN students s ON c.student_id = s.student_id '
        'LEFT JOIN rooms r ON COALESCE(c.room_id, s.room_id) = r.room_id '
        'LEFT JOIN hostels h ON r.hostel_id = h.hostel_id '
        'WHERE c.student_id = %s ORDER BY c.date DESC, c.complaint_id DESC',
        (session['role_id'],),
    )
    return render_template('student/complaints.html', complaints=complaints)


@app.route('/student/invoices')
@login_required
@role_required('student')
def student_invoices():
    invoices = query(
        'SELECT * FROM invoices WHERE student_id = %s ORDER BY invoice_id DESC',
        (session['role_id'],),
    )
    total = query(
        'SELECT COUNT(*) AS count, SUM(amount) AS total, '
        'SUM(CASE WHEN payment_status = "Paid" THEN amount ELSE 0 END) AS paid, '
        'SUM(CASE WHEN payment_status <> "Paid" THEN amount ELSE 0 END) AS unpaid '
        'FROM invoices WHERE student_id = %s',
        (session['role_id'],), one=True,
    )
    return render_template('student/invoices.html', invoices=invoices, total=total)


@app.route('/student/invoices/print/<int:invoice_id>')
@login_required
@role_required('student')
def student_invoice_print(invoice_id):
    invoice = _invoice_receipt_data(invoice_id)
    if not invoice or invoice['student_id'] != session['role_id']:
        flash('Invoice not found.', 'danger')
        return redirect(url_for('student_invoices'))
    return render_template('invoice_print.html', invoice=invoice)


@app.route('/student/mess-off', methods=['GET', 'POST'])
@login_required
@role_required('student')
def student_mess_off():
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        if start_date and end_date:
            execute(
                'INSERT INTO mess_off_requests (student_id, start_date, end_date, status) '
                'VALUES (%s, %s, %s, %s)',
                (session['role_id'], start_date, end_date, 'Pending'),
            )
            student = query(
                'SELECT name FROM students WHERE student_id = %s',
                (session['role_id'],), one=True,
            )
            notify_managers(
                'Mess-off request',
                f"{student['name']} requested mess-off from {start_date} to {end_date}.",
                '/manager/mess-off',
            )
            flash('Mess off request submitted.', 'success')
        return redirect(url_for('student_mess_off'))
    requests = query(
        'SELECT * FROM mess_off_requests WHERE student_id = %s ORDER BY start_date DESC, mess_off_id DESC',
        (session['role_id'],),
    )
    return render_template('student/mess_off.html', requests=requests)


@app.route('/student/feedback', methods=['GET', 'POST'])
@login_required
@role_required('student')
def student_feedback():
    if request.method == 'POST':
        description = request.form.get('description', '').strip()
        if description:
            execute(
                'INSERT INTO feedback (student_id, description, date) VALUES (%s, %s, %s)',
                (session['role_id'], description, date.today().isoformat()),
            )
            student = query(
                'SELECT name FROM students WHERE student_id = %s',
                (session['role_id'],), one=True,
            )
            notify_managers(
                'New feedback',
                f"{student['name']} submitted feedback: {description[:100]}",
                '/manager/feedback',
            )
            flash('Feedback submitted. Thank you!', 'success')
        return redirect(url_for('student_feedback'))
    feedbacks = query(
        'SELECT * FROM feedback WHERE student_id = %s ORDER BY date DESC, feedback_id DESC',
        (session['role_id'],),
    )
    return render_template('student/feedback.html', feedbacks=feedbacks)


@app.route('/student/in-out', methods=['GET', 'POST'])
@login_required
@role_required('student')
def student_in_out():
    if request.method == 'POST':
        out_date = request.form.get('out_date')
        reason = request.form.get('reason', '').strip()
        if out_date:
            student = query(
                'SELECT name, student_no FROM students WHERE student_id = %s',
                (session['role_id'],), one=True,
            )
            execute(
                'INSERT INTO student_in_out (student_id, out_date, reason, status) VALUES (%s, %s, %s, %s)',
                (session['role_id'], out_date, reason, 'Out'),
            )
            who = f'{student["name"]} ({student["student_no"]})' if student else f'Student #{session["role_id"]}'
            notify_all_staff(
                'Student out',
                f'{who} has left the hostel. Please mark them returned when they come back.',
                '/staff/in-out',
            )
            notify_managers('Student out', f'{who} has left the hostel.')
            flash('Leave request recorded.', 'success')
        return redirect(url_for('student_in_out'))
    records = query(
        'SELECT * FROM student_in_out WHERE student_id = %s ORDER BY out_date DESC',
        (session['role_id'],),
    )
    return render_template('student/in_out.html', records=records)


@app.route('/student/parcels', methods=['GET', 'POST'])
@login_required
@role_required('student')
def student_parcels():
    if request.method == 'POST':
        if request.form.get('action') == 'collect':
            parcel_id = request.form.get('parcel_id')
            parcel = query(
                'SELECT received_by_staff FROM parcels WHERE parcel_id = %s AND student_id = %s',
                (parcel_id, session['role_id']), one=True,
            )
            if parcel:
                execute(
                    "UPDATE parcels SET status = 'Collected', collected_at = %s, "
                    'collected_by_student = %s WHERE parcel_id = %s AND status = %s',
                    (
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        session['role_id'],
                        parcel_id,
                        'Arrived',
                    ),
                )
                student = query(
                    'SELECT name FROM students WHERE student_id = %s',
                    (session['role_id'],), one=True,
                )
                notify_staff(
                    parcel['received_by_staff'], 'Parcel collected',
                    f"{student['name']} collected their parcel.",
                    '/staff/parcels',
                )
                notify_managers(
                    'Parcel collected',
                    f"{student['name']} collected their parcel.",
                    '/manager/parcels',
                )
                if _is_ajax():
                    return jsonify(ok=True, message='Parcel collected. Enjoy!', status='Collected')
                flash('Parcel collected. Enjoy!', 'success')
        return redirect(url_for('student_parcels'))
    parcels = query(
        'SELECT p.*, r.name AS received_by, c.name AS collected_by '
        'FROM parcels p '
        'LEFT JOIN staff r ON p.received_by_staff = r.staff_id '
        'LEFT JOIN students c ON p.collected_by_student = c.student_id '
        'WHERE p.student_id = %s ORDER BY p.received_date DESC, p.parcel_id DESC',
        (session['role_id'],),
    )
    return render_template('student/parcels.html', parcels=parcels)


@app.route('/student/attendance', methods=['GET', 'POST'])
@login_required
@role_required('student')
def student_attendance():
    today_str = date.today().isoformat()
    if request.method == 'POST':
        status = request.form.get('status')
        lat = request.form.get('lat')
        lng = request.form.get('lng')
        student = query(
            'SELECT s.student_id, r.hostel_id FROM students s '
            'LEFT JOIN rooms r ON s.room_id = r.room_id WHERE s.student_id = %s',
            (session['role_id'],), one=True,
        )
        if status == 'Leave':
            execute(
                'INSERT INTO student_attendance (student_id, date, status) VALUES (%s, %s, %s) '
                'ON DUPLICATE KEY UPDATE status = %s',
                (session['role_id'], today_str, 'Leave', 'Leave'),
            )
            flash('Attendance recorded for today.', 'success')
        elif status == 'Present' and lat and lng and student and student['hostel_id']:
            try:
                lat_f, lng_f = float(lat), float(lng)
            except ValueError:
                lat_f = None
            if lat_f is not None:
                hostel = query(
                    'SELECT hostel_name, lat, lng, radius_m FROM hostels WHERE hostel_id = %s',
                    (student['hostel_id'],), one=True,
                )
                if not hostel or hostel['lat'] is None or hostel['lng'] is None:
                    flash('Location is not configured for your hostel. Please contact the manager.', 'danger')
                else:
                    dist = distance_m(lat_f, lng_f, float(hostel['lat']), float(hostel['lng']))
                    if dist <= float(hostel['radius_m']):
                        execute(
                            'INSERT INTO student_attendance (student_id, date, status) VALUES (%s, %s, %s) '
                            'ON DUPLICATE KEY UPDATE status = %s',
                            (session['role_id'], today_str, 'Present', 'Present'),
                        )
                        flash(
                            f'Attendance granted. You are {dist / 1000:.2f} km from '
                            f'{hostel["hostel_name"]}.',
                            'success',
                        )
                    else:
                        flash(
                            f'You are {dist / 1000:.2f} km from {hostel["hostel_name"]}. '
                            f'Attendance NOT granted (outside the {hostel["radius_m"]} m area).',
                            'danger',
                        )
            else:
                flash('Could not read your location. Please allow location access.', 'danger')
        else:
            flash('You need an allocated room and your location to mark Present.', 'danger')
        return redirect(url_for('student_attendance'))
    records = query(
        'SELECT * FROM student_attendance WHERE student_id = %s ORDER BY date DESC',
        (session['role_id'],),
    )
    student = query(
        'SELECT s.name, r.hostel_id, h.hostel_name, h.lat, h.lng, h.radius_m '
        'FROM students s LEFT JOIN rooms r ON s.room_id = r.room_id '
        'LEFT JOIN hostels h ON r.hostel_id = h.hostel_id WHERE s.student_id = %s',
        (session['role_id'],), one=True,
    )
    today_record = query(
        'SELECT * FROM student_attendance WHERE student_id = %s AND date = %s',
        (session['role_id'], today_str), one=True,
    )
    counts, total, rate = _attendance_stats(records)
    my_stats = {
        'present': counts['Present'], 'absent': counts['Absent'],
        'leave': counts['Leave'], 'rate': rate,
    }
    my_donut = _donut_payload(
        ['Present', 'Absent', 'Leave'],
        [counts['Present'], counts['Absent'], counts['Leave']],
    )
    my_trend = _attendance_trend(records, days=30, end=date.today())
    return render_template(
        'student/attendance.html', records=records, student=student, today_record=today_record,
        my_stats=my_stats, my_donut=my_donut, my_trend=my_trend,
    )


# =====================================================================
# STAFF ROUTES
# =====================================================================

@app.route('/staff')
@login_required
@role_required('staff')
def staff_dashboard():
    today_str = date.today().isoformat()
    stats = {
        'visitors_today': query(
            'SELECT COUNT(*) AS c FROM visitors WHERE visit_date = %s', (today_str,), one=True,
        )['c'],
        'parcels_arrived': query(
            "SELECT COUNT(*) AS c FROM parcels WHERE status = 'Arrived'", one=True,
        )['c'],
        'attendance_today': query(
            'SELECT COUNT(*) AS c FROM staff_attendance WHERE staff_id = %s AND date = %s',
            (session['role_id'], today_str), one=True,
        )['c'],
    }
    recent_visitors = query(
        'SELECT v.*, s.name AS student_name FROM visitors v '
        'JOIN students s ON v.student_id = s.student_id '
        'ORDER BY v.visit_date DESC, v.visitor_id DESC LIMIT 5'
    )
    return render_template('staff/dashboard.html', stats=stats, recent_visitors=recent_visitors)


@app.route('/staff/visitors', methods=['GET', 'POST'])
@login_required
@role_required('staff')
def staff_visitors():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        visitor_name = request.form.get('visitor_name', '').strip()
        visit_date = request.form.get('visit_date')
        if visitor_name:
            execute(
                'INSERT INTO visitors (student_id, registered_by_staff, visitor_name, visit_date) '
                'VALUES (%s, %s, %s, %s)',
                (student_id, session['role_id'], visitor_name, visit_date),
            )
            notify_student(
                student_id, 'Visitor arrived',
                f'{visitor_name} came to see you on {visit_date}.',
                '/student/in-out',
            )
            flash('Visitor registered.', 'success')
        return redirect(url_for('staff_visitors'))
    students = query('SELECT student_id, student_no, name FROM students ORDER BY student_id')
    visitors = query(
        'SELECT v.*, s.name AS student_name FROM visitors v '
        'JOIN students s ON v.student_id = s.student_id ORDER BY v.visit_date DESC, v.visitor_id DESC'
    )
    return render_template('staff/visitors.html', students=students, visitors=visitors)


@app.route('/staff/parcels', methods=['GET', 'POST'])
@login_required
@role_required('staff')
def staff_parcels():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        received_date = request.form.get('received_date')
        if student_id and received_date:
            execute(
                'INSERT INTO parcels (student_id, received_by_staff, status, received_date) '
                'VALUES (%s, %s, %s, %s)',
                (student_id, session['role_id'], 'Arrived', received_date),
            )
            notify_student(
                student_id, 'Parcel arrived',
                'A parcel has arrived for you. Please collect it at the front desk.',
                '/student/parcels',
            )
            flash('Parcel received and registered.', 'success')
        return redirect(url_for('staff_parcels'))
    students = query('SELECT student_id, student_no, name FROM students ORDER BY student_id')
    parcels = query(
        'SELECT p.*, s.student_no, s.name AS student_name, r.name AS received_by, c.name AS collected_by '
        'FROM parcels p JOIN students s ON p.student_id = s.student_id '
        'LEFT JOIN staff r ON p.received_by_staff = r.staff_id '
        'LEFT JOIN students c ON p.collected_by_student = c.student_id '
        'ORDER BY p.received_date DESC, p.parcel_id DESC'
    )
    return render_template('staff/parcels.html', students=students, parcels=parcels)


@app.route('/staff/in-out', methods=['GET', 'POST'])
@login_required
@role_required('staff')
def staff_in_out():
    if request.method == 'POST':
        record_id = request.form.get('record_id')
        record = query(
            'SELECT student_id FROM student_in_out WHERE record_id = %s',
            (record_id,), one=True,
        )
        execute(
            "UPDATE student_in_out SET in_date = %s, status = %s WHERE record_id = %s AND status = 'Out'",
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Returned', record_id),
        )
        if record:
            notify_student(
                record['student_id'], 'Returned',
                'You have been marked as returned to the hostel.',
                '/student/in-out',
            )
        if _is_ajax():
            return jsonify(ok=True, message='Student marked as returned.', status='Returned')
        flash('Student marked as returned.', 'success')
        return redirect(url_for('staff_in_out'))
    out_records = query(
        'SELECT io.*, s.student_no, s.name AS student_name FROM student_in_out io '
        'JOIN students s ON io.student_id = s.student_id '
        "WHERE io.status = 'Out' ORDER BY io.out_date DESC"
    )
    history = query(
        'SELECT io.*, s.student_no, s.name AS student_name FROM student_in_out io '
        'JOIN students s ON io.student_id = s.student_id '
        "WHERE io.status = 'Returned' ORDER BY io.in_date DESC, io.record_id DESC LIMIT 20"
    )
    return render_template('staff/in_out.html', out_records=out_records, history=history)


@app.route('/staff/attendance', methods=['GET', 'POST'])
@login_required
@role_required('staff')
def staff_attendance():
    today_str = date.today().isoformat()
    if request.method == 'POST':
        status = request.form.get('status')
        lat = request.form.get('lat')
        lng = request.form.get('lng')
        hostel_id = request.form.get('hostel_id')
        if status == 'Leave':
            execute(
                'INSERT INTO staff_attendance (staff_id, date, status) VALUES (%s, %s, %s) '
                'ON DUPLICATE KEY UPDATE status = %s',
                (session['role_id'], today_str, 'Leave', 'Leave'),
            )
            flash('Attendance recorded for today.', 'success')
        elif status == 'Present' and lat and lng and hostel_id:
            try:
                lat_f, lng_f = float(lat), float(lng)
            except ValueError:
                lat_f = None
            if lat_f is not None:
                hostel = query(
                    'SELECT hostel_name, lat, lng, radius_m FROM hostels WHERE hostel_id = %s',
                    (hostel_id,), one=True,
                )
                if not hostel or hostel['lat'] is None or hostel['lng'] is None:
                    flash('Location is not configured for that hostel. Please contact the manager.', 'danger')
                else:
                    dist = distance_m(lat_f, lng_f, float(hostel['lat']), float(hostel['lng']))
                    if dist <= float(hostel['radius_m']):
                        execute(
                            'INSERT INTO staff_attendance (staff_id, date, status) VALUES (%s, %s, %s) '
                            'ON DUPLICATE KEY UPDATE status = %s',
                            (session['role_id'], today_str, 'Present', 'Present'),
                        )
                        flash(
                            f'Attendance granted. You are {dist / 1000:.2f} km from '
                            f'{hostel["hostel_name"]}.',
                            'success',
                        )
                    else:
                        flash(
                            f'You are {dist / 1000:.2f} km from {hostel["hostel_name"]}. '
                            f'Attendance NOT granted (outside the {hostel["radius_m"]} m area).',
                            'danger',
                        )
            else:
                flash('Could not read your location. Please allow location access.', 'danger')
        else:
            flash('Location is required to mark Present.', 'danger')
        return redirect(url_for('staff_attendance'))
    records = query(
        'SELECT * FROM staff_attendance WHERE staff_id = %s ORDER BY date DESC',
        (session['role_id'],),
    )
    hostels = query('SELECT hostel_id, hostel_name, lat, lng, radius_m FROM hostels ORDER BY hostel_id')
    today_record = query(
        'SELECT * FROM staff_attendance WHERE staff_id = %s AND date = %s',
        (session['role_id'], today_str), one=True,
    )
    counts, total, rate = _attendance_stats(records)
    my_stats = {
        'present': counts['Present'], 'absent': counts['Absent'],
        'leave': counts['Leave'], 'rate': rate,
    }
    my_donut = _donut_payload(
        ['Present', 'Absent', 'Leave'],
        [counts['Present'], counts['Absent'], counts['Leave']],
    )
    my_trend = _attendance_trend(records, days=30, end=date.today())
    return render_template(
        'staff/attendance.html', records=records, hostels=hostels, today_record=today_record,
        my_stats=my_stats, my_donut=my_donut, my_trend=my_trend,
    )


if __name__ == '__main__':
    app.run(debug=True)
