from datetime import date, datetime
from functools import wraps

from flask import (
    Flask, flash, redirect, render_template, request, session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from config import SECRET_KEY
from db import execute, get_connection, query

app = Flask(__name__)
app.secret_key = SECRET_KEY


@app.context_processor
def inject_session_user():
    return {
        'session_role': session.get('role'),
        'session_username': session.get('username'),
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
    return render_template(
        'manager/dashboard.html', stats=stats,
        recent_complaints=recent_complaints, recent_violations=recent_violations,
    )


@app.route('/manager/students')
@login_required
@role_required('manager')
def manager_students():
    students = query(
        'SELECT s.student_id, s.name, s.email, s.phone, s.gender, u.username, r.room_no '
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
            execute(
                'INSERT INTO students (user_id, name, email, phone, address, gender) '
                'VALUES (%s, %s, %s, %s, %s, %s)',
                (user_id, name, email, phone, address, gender),
            )
            flash(f'Student "{name}" registered successfully.', 'success')
            return redirect(url_for('manager_students'))
    return render_template('manager/register_student.html')


@app.route('/manager/students/delete/<int:student_id>', methods=['POST'])
@login_required
@role_required('manager')
def delete_student(student_id):
    conn = get_connection()
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
        'SELECT r.room_id, r.room_no, r.total_beds, r.available_beds, h.hostel_name, '
        '(SELECT COUNT(*) FROM students s WHERE s.room_id = r.room_id) AS occupants '
        'FROM rooms r JOIN hostels h ON r.hostel_id = h.hostel_id ORDER BY r.room_id'
    )
    hostels = query('SELECT hostel_id, hostel_name, location, total_rooms FROM hostels ORDER BY hostel_id')
    return render_template('manager/rooms.html', rooms=rooms, hostels=hostels)


@app.route('/manager/hostels/add', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def add_hostel():
    if request.method == 'POST':
        hostel_name = request.form.get('hostel_name', '').strip()
        location = request.form.get('location', '').strip()
        if not hostel_name:
            flash('Hostel name is required.', 'danger')
        else:
            execute(
                'INSERT INTO hostels (hostel_name, location, total_rooms) VALUES (%s, %s, 0)',
                (hostel_name, location),
            )
            flash(f'Hostel "{hostel_name}" added.', 'success')
            return redirect(url_for('manager_rooms'))
    return render_template('manager/add_hostel.html')


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
    hostels = query('SELECT hostel_id, hostel_name FROM hostels ORDER BY hostel_id')
    return render_template('manager/add_room.html', hostels=hostels)


@app.route('/manager/rooms/allocate', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def allocate_room():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        room_id = request.form.get('room_id')
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute('SELECT available_beds FROM rooms WHERE room_id = %s FOR UPDATE', (room_id,))
            room = cur.fetchone()
            if not room or room['available_beds'] <= 0:
                flash('No beds available in that room.', 'danger')
            else:
                cur.execute('UPDATE rooms SET available_beds = available_beds - 1 WHERE room_id = %s', (room_id,))
                cur.execute('UPDATE students SET room_id = %s WHERE student_id = %s', (room_id, student_id))
                conn.commit()
                flash('Room allocated successfully.', 'success')
        except Exception:
            conn.rollback()
            flash('Allocation failed. Please try again.', 'danger')
        finally:
            cur.close()
            conn.close()
        return redirect(url_for('allocate_room'))
    unallocated = query('SELECT student_id, name FROM students WHERE room_id IS NULL ORDER BY student_id')
    free_rooms = query('SELECT room_id, room_no, available_beds FROM rooms WHERE available_beds > 0 ORDER BY room_id')
    return render_template('manager/allocate_room.html', students=unallocated, rooms=free_rooms)


@app.route('/manager/complaints', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def manager_complaints():
    if request.method == 'POST':
        complaint_id = request.form.get('complaint_id')
        status = request.form.get('status')
        execute('UPDATE complaints SET status = %s WHERE complaint_id = %s', (status, complaint_id))
        flash('Complaint status updated.', 'success')
        return redirect(url_for('manager_complaints'))
    complaints = query(
        'SELECT c.*, s.name AS student_name, r.room_no '
        'FROM complaints c JOIN students s ON c.student_id = s.student_id '
        'LEFT JOIN rooms r ON c.room_id = r.room_id ORDER BY c.date DESC, c.complaint_id DESC'
    )
    return render_template('manager/complaints.html', complaints=complaints)


@app.route('/manager/invoices', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def manager_invoices():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        amount = request.form.get('amount')
        due_date = request.form.get('due_date')
        execute(
            'INSERT INTO invoices (student_id, amount, due_date, payment_status) VALUES (%s, %s, %s, %s)',
            (student_id, amount, due_date, 'Unpaid'),
        )
        flash('Invoice generated.', 'success')
        return redirect(url_for('manager_invoices'))
    invoices = query(
        'SELECT i.*, s.name AS student_name FROM invoices i '
        'JOIN students s ON i.student_id = s.student_id ORDER BY i.invoice_id DESC'
    )
    students = query('SELECT student_id, name FROM students ORDER BY student_id')
    return render_template('manager/invoices.html', invoices=invoices, students=students)


@app.route('/manager/invoices/toggle/<int:invoice_id>', methods=['POST'])
@login_required
@role_required('manager')
def toggle_invoice(invoice_id):
    invoice = query('SELECT payment_status FROM invoices WHERE invoice_id = %s', (invoice_id,), one=True)
    new_status = 'Paid' if invoice['payment_status'] != 'Paid' else 'Unpaid'
    execute('UPDATE invoices SET payment_status = %s WHERE invoice_id = %s', (new_status, invoice_id))
    flash(f'Invoice marked {new_status}.', 'success')
    return redirect(url_for('manager_invoices'))


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
        else:
            staff_id = request.form.get('staff_id')
            execute(
                'INSERT INTO staff_attendance (staff_id, date, status) VALUES (%s, %s, %s) '
                'ON DUPLICATE KEY UPDATE status = %s',
                (staff_id, att_date, status, status),
            )
        flash('Attendance recorded.', 'success')
        return redirect(url_for('manager_attendance'))
    students = query('SELECT student_id, name FROM students ORDER BY student_id')
    staff_members = query('SELECT staff_id, name FROM staff ORDER BY staff_id')
    student_attendance = query(
        'SELECT a.*, s.name FROM student_attendance a JOIN students s ON a.student_id = s.student_id '
        'ORDER BY a.date DESC, a.attendance_id DESC LIMIT 15'
    )
    staff_attendance = query(
        'SELECT a.*, st.name FROM staff_attendance a JOIN staff st ON a.staff_id = st.staff_id '
        'ORDER BY a.date DESC, a.attendance_id DESC LIMIT 15'
    )
    return render_template(
        'manager/attendance.html', students=students, staff_members=staff_members,
        student_attendance=student_attendance, staff_attendance=staff_attendance,
    )


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
        target = request.form.get('target')
        target_id = request.form.get('target_id')
        description = request.form.get('description', '').strip()
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
        flash('Violation recorded.', 'success')
        return redirect(url_for('manager_violations'))
    violations = query(
        'SELECT v.*, s.name AS student_name, st.name AS staff_name FROM violations v '
        'LEFT JOIN students s ON v.student_id = s.student_id '
        'LEFT JOIN staff st ON v.staff_id = st.staff_id '
        'ORDER BY v.date DESC, v.violation_id DESC'
    )
    students = query('SELECT student_id, name FROM students ORDER BY student_id')
    staff_members = query('SELECT staff_id, name FROM staff ORDER BY staff_id')
    return render_template('manager/violations.html', violations=violations, students=students, staff_members=staff_members)


@app.route('/manager/violations/resolve/<int:violation_id>', methods=['POST'])
@login_required
@role_required('manager')
def resolve_violation(violation_id):
    execute(
        'UPDATE violations SET status = %s, resolved_at = %s WHERE violation_id = %s',
        ('Resolved', date.today().isoformat(), violation_id),
    )
    flash('Violation marked as resolved.', 'success')
    return redirect(url_for('manager_violations'))


@app.route('/manager/feedback')
@login_required
@role_required('manager')
def manager_feedback():
    feedbacks = query(
        'SELECT f.*, s.name AS student_name FROM feedback f '
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
        execute('UPDATE mess_off_requests SET status = %s WHERE mess_off_id = %s', (status, request_id))
        flash(f'Mess off request {status.lower()}.', 'success')
        return redirect(url_for('manager_mess_off'))
    requests = query(
        'SELECT r.*, s.name AS student_name FROM mess_off_requests r '
        'JOIN students s ON r.student_id = s.student_id '
        'ORDER BY r.mess_off_id DESC'
    )
    return render_template('manager/mess_off.html', requests=requests)


@app.route('/manager/parcels')
@login_required
@role_required('manager')
def manager_parcels():
    parcels = query(
        'SELECT p.*, s.name AS student_name, r.name AS received_by, c.name AS collected_by '
        'FROM parcels p JOIN students s ON p.student_id = s.student_id '
        'LEFT JOIN staff r ON p.received_by_staff = r.staff_id '
        'LEFT JOIN staff c ON p.collected_by_staff = c.staff_id '
        'ORDER BY p.received_date DESC, p.parcel_id DESC'
    )
    return render_template('manager/parcels.html', parcels=parcels)


@app.route('/manager/visitors')
@login_required
@role_required('manager')
def manager_visitors():
    visitors = query(
        'SELECT v.*, s.name AS student_name, st.name AS registered_by '
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
            execute(
                'INSERT INTO staff (user_id, name, designation, salary) VALUES (%s, %s, %s, %s)',
                (user_id, name, designation, salary),
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
    conn = get_connection()
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
        execute(
            'UPDATE students SET email = %s, phone = %s, address = %s, gender = %s '
            'WHERE student_id = %s',
            (
                request.form.get('email', '').strip(),
                request.form.get('phone', '').strip(),
                request.form.get('address', '').strip(),
                request.form.get('gender', ''),
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
            execute(
                'INSERT INTO complaints (student_id, room_id, description, status, date) '
                'VALUES (%s, %s, %s, %s, %s)',
                (session['role_id'], session.get('room_id'), description, 'Pending', date.today().isoformat()),
            )
            flash('Complaint submitted.', 'success')
        return redirect(url_for('student_complaints'))
    complaints = query(
        'SELECT * FROM complaints WHERE student_id = %s ORDER BY date DESC, complaint_id DESC',
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
    return render_template('student/invoices.html', invoices=invoices)


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
            flash('Mess off request submitted.', 'success')
        return redirect(url_for('student_mess_off'))
    requests = query(
        'SELECT * FROM mess_off_requests WHERE student_id = %s ORDER BY mess_off_id DESC',
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
            execute(
                'INSERT INTO student_in_out (student_id, out_date, reason, status) VALUES (%s, %s, %s, %s)',
                (session['role_id'], out_date, reason, 'Out'),
            )
            flash('Leave request recorded.', 'success')
        return redirect(url_for('student_in_out'))
    records = query(
        'SELECT * FROM student_in_out WHERE student_id = %s ORDER BY out_date DESC',
        (session['role_id'],),
    )
    return render_template('student/in_out.html', records=records)


@app.route('/student/parcels')
@login_required
@role_required('student')
def student_parcels():
    parcels = query(
        'SELECT p.*, r.name AS received_by, c.name AS collected_by '
        'FROM parcels p '
        'LEFT JOIN staff r ON p.received_by_staff = r.staff_id '
        'LEFT JOIN staff c ON p.collected_by_staff = c.staff_id '
        'WHERE p.student_id = %s ORDER BY p.received_date DESC, p.parcel_id DESC',
        (session['role_id'],),
    )
    return render_template('student/parcels.html', parcels=parcels)


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
            flash('Visitor registered.', 'success')
        return redirect(url_for('staff_visitors'))
    students = query('SELECT student_id, name FROM students ORDER BY student_id')
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
        action = request.form.get('action')
        if action == 'receive':
            student_id = request.form.get('student_id')
            received_date = request.form.get('received_date')
            if student_id and received_date:
                execute(
                    'INSERT INTO parcels (student_id, received_by_staff, status, received_date) '
                    'VALUES (%s, %s, %s, %s)',
                    (student_id, session['role_id'], 'Arrived', received_date),
                )
                flash('Parcel received and registered.', 'success')
        elif action == 'collect':
            parcel_id = request.form.get('parcel_id')
            execute(
                "UPDATE parcels SET status = 'Collected', collected_at = %s, collected_by_staff = %s "
                'WHERE parcel_id = %s',
                (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), session['role_id'], parcel_id),
            )
            flash('Parcel marked as collected.', 'success')
        return redirect(url_for('staff_parcels'))
    students = query('SELECT student_id, name FROM students ORDER BY student_id')
    parcels = query(
        'SELECT p.*, s.name AS student_name, r.name AS received_by, c.name AS collected_by '
        'FROM parcels p JOIN students s ON p.student_id = s.student_id '
        'LEFT JOIN staff r ON p.received_by_staff = r.staff_id '
        'LEFT JOIN staff c ON p.collected_by_staff = c.staff_id '
        'ORDER BY p.received_date DESC, p.parcel_id DESC'
    )
    return render_template('staff/parcels.html', students=students, parcels=parcels)


@app.route('/staff/in-out', methods=['GET', 'POST'])
@login_required
@role_required('staff')
def staff_in_out():
    if request.method == 'POST':
        record_id = request.form.get('record_id')
        execute(
            "UPDATE student_in_out SET in_date = %s, status = %s WHERE record_id = %s AND status = 'Out'",
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Returned', record_id),
        )
        flash('Student marked as returned.', 'success')
        return redirect(url_for('staff_in_out'))
    out_records = query(
        'SELECT io.*, s.name AS student_name FROM student_in_out io '
        'JOIN students s ON io.student_id = s.student_id '
        "WHERE io.status = 'Out' ORDER BY io.out_date DESC"
    )
    history = query(
        'SELECT io.*, s.name AS student_name FROM student_in_out io '
        'JOIN students s ON io.student_id = s.student_id '
        "WHERE io.status = 'Returned' ORDER BY io.in_date DESC, io.record_id DESC LIMIT 20"
    )
    return render_template('staff/in_out.html', out_records=out_records, history=history)


@app.route('/staff/attendance', methods=['GET', 'POST'])
@login_required
@role_required('staff')
def staff_attendance():
    if request.method == 'POST':
        status = request.form.get('status')
        execute(
            'INSERT INTO staff_attendance (staff_id, date, status) VALUES (%s, %s, %s) '
            'ON DUPLICATE KEY UPDATE status = %s',
            (session['role_id'], date.today().isoformat(), status, status),
        )
        flash('Attendance recorded for today.', 'success')
        return redirect(url_for('staff_attendance'))
    records = query(
        'SELECT * FROM staff_attendance WHERE staff_id = %s ORDER BY date DESC',
        (session['role_id'],),
    )
    return render_template('staff/attendance.html', records=records)


if __name__ == '__main__':
    app.run(debug=True)
