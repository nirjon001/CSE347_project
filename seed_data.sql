-- =====================================================================
-- Seed data for the Hostel Management System (expanded demo set)
-- Logins:
--   manager  / admin123   (Manager)
--   staff1   / staff123   (Staff  — Caretaker)
--   staff2   / staff123   (Staff  — Cook)
--   staff3   / staff123   (Staff  — Guard)
--   student1 / student123 (Student — Rafi, allocated)
--   student2 / student123 (Student — Sadia, not allocated)
--   student3 / student123 (Student — Tanvir, allocated)
--   student4 / student123 (Student — Nusrat, allocated)
--   student5 / student123 (Student — Mehedi, not allocated)
-- =====================================================================
-- DATA ONLY. Requires hostel_management_schema.sql to be imported first.
-- Do not run twice without dropping the database (fixed IDs -> duplicate errors).
-- =====================================================================
USE hostel_management;

-- USERS (passwords are scrypt hashes generated with werkzeug)
INSERT INTO users (user_id, username, password, role) VALUES
(1, 'manager',  'scrypt:32768:8:1$ItNtyupaUcH625hR$ec8438bf1d1dfa39c537087dbcc24ea6aa9c973e75cb1ec129ddc35a0e435822da3c837a8dca62cb58e06faa7added134f14fdcfd770664b449d3884bcd32c5c', 'manager'),
(2, 'staff1',   'scrypt:32768:8:1$ueps82YvEwUsZejm$c78857c37c492e6d397829e38db021ad62216d0b100661db99e719fd32043f2c005e49c54d4643da12817f6ef97e1aec7e713560a45f2e647651b1690ed46a2b', 'staff'),
(3, 'staff2',   'scrypt:32768:8:1$ueps82YvEwUsZejm$c78857c37c492e6d397829e38db021ad62216d0b100661db99e719fd32043f2c005e49c54d4643da12817f6ef97e1aec7e713560a45f2e647651b1690ed46a2b', 'staff'),
(4, 'staff3',   'scrypt:32768:8:1$ueps82YvEwUsZejm$c78857c37c492e6d397829e38db021ad62216d0b100661db99e719fd32043f2c005e49c54d4643da12817f6ef97e1aec7e713560a45f2e647651b1690ed46a2b', 'staff'),
(5, 'student1', 'scrypt:32768:8:1$dHF9S6ravzQbODud$7723829848ee0605439e56da915d58d7b7a367f308a99f8b387afc960c1d110ad19b88aa851ec4bc55c7ed7b8eda9633df35a8b19e5130284ca844a31980db9d', 'student'),
(6, 'student2', 'scrypt:32768:8:1$dHF9S6ravzQbODud$7723829848ee0605439e56da915d58d7b7a367f308a99f8b387afc960c1d110ad19b88aa851ec4bc55c7ed7b8eda9633df35a8b19e5130284ca844a31980db9d', 'student'),
(7, 'student3', 'scrypt:32768:8:1$dHF9S6ravzQbODud$7723829848ee0605439e56da915d58d7b7a367f308a99f8b387afc960c1d110ad19b88aa851ec4bc55c7ed7b8eda9633df35a8b19e5130284ca844a31980db9d', 'student'),
(8, 'student4', 'scrypt:32768:8:1$dHF9S6ravzQbODud$7723829848ee0605439e56da915d58d7b7a367f308a99f8b387afc960c1d110ad19b88aa851ec4bc55c7ed7b8eda9633df35a8b19e5130284ca844a31980db9d', 'student'),
(9, 'student5', 'scrypt:32768:8:1$dHF9S6ravzQbODud$7723829848ee0605439e56da915d58d7b7a367f308a99f8b387afc960c1d110ad19b88aa851ec4bc55c7ed7b8eda9633df35a8b19e5130284ca844a31980db9d', 'student');

-- MANAGERS
INSERT INTO managers (manager_id, user_id, name, designation) VALUES
(1, 1, 'Ayesha Rahman', 'Chief Manager');

-- STAFF (designation values, per class diagram decision)
INSERT INTO staff (staff_id, user_id, name, designation, salary) VALUES
(1, 2, 'Karim Mia',     'Caretaker', 15000.00),
(2, 3, 'Rashida Begum', 'Cook',      12000.00),
(3, 4, 'Hanif Uddin',   'Guard',     10000.00);

-- HOSTELS & ROOMS (varied capacities)
INSERT INTO hostels (hostel_id, hostel_name, location, gender, total_rooms, lat, lng, radius_m) VALUES
(1, 'Main Hostel',  'North Campus', 'Male',   4, 23.8100000, 90.4125000, 50),
(2, 'Girls Hostel', 'South Campus', 'Female', 2, 23.8140000, 90.4160000, 50);

INSERT INTO rooms (room_id, hostel_id, room_no, total_beds, available_beds) VALUES
(101, 1, '101', 4, 3),
(102, 1, '102', 2, 2),
(201, 1, '201', 2, 1),
(202, 1, '202', 2, 2),
(301, 2, '301', 3, 2),
(302, 2, '302', 6, 6);

-- STUDENTS
INSERT INTO students (student_id, user_id, name, email, phone, address, gender, room_id) VALUES
(1, 5, 'Rafi Ahmed',    'rafi@example.com',    '01700000001', 'Dhaka',     'Male',   101),
(2, 6, 'Sadia Islam',   'sadia@example.com',   '01700000002', 'Chattogram','Female', NULL),
(3, 7, 'Tanvir Hasan',  'tanvir@example.com',  '01700000003', 'Sylhet',    'Male',   201),
(4, 8, 'Nusrat Jahan',  'nusrat@example.com',  '01700000004', 'Rajshahi',  'Female', 301),
(5, 9, 'Mehedi Karim',  'mehedi@example.com',  '01700000005', 'Khulna',    'Male',   NULL);

-- MESS MENU (several days/meals)
INSERT INTO mess_menu (menu_id, manager_id, day_of_week, meal_type, items_description) VALUES
(1,  1, 'Saturday', 'Breakfast', 'Paratha, Dal, Egg, Tea'),
(2,  1, 'Saturday', 'Lunch',     'Rice, Chicken Curry, Salad'),
(3,  1, 'Saturday', 'Dinner',    'Rice, Fish Fry, Vegetable'),
(4,  1, 'Sunday',   'Breakfast', 'Khichuri, Pickle, Tea'),
(5,  1, 'Sunday',   'Lunch',     'Rice, Beef Bhuna, Salad'),
(6,  1, 'Sunday',   'Dinner',    'Rice, Vegetable Curry, Egg');

-- INVOICES (mix of statuses)
INSERT INTO invoices (invoice_id, student_id, amount, due_date, payment_status) VALUES
(1, 1, 4500.00, '2026-09-01', 'Unpaid'),
(2, 2, 4500.00, '2026-09-01', 'Paid'),
(3, 3, 4800.00, '2026-09-05', 'Unpaid'),
(4, 4, 4200.00, '2026-08-15', 'Overdue'),
(5, 1, 5000.00, '2026-07-01', 'Paid'),
(6, 5, 4500.00, '2026-09-01', 'Unpaid');

-- COMPLAINTS
INSERT INTO complaints (complaint_id, student_id, room_id, description, status, date) VALUES
(1, 1, 101, 'The bathroom tap is leaking since yesterday.',        'Pending',     '2026-08-02'),
(2, 3, 201, 'The window lock is broken, room cannot be secured.',  'In Progress', '2026-08-01'),
(3, 4, 301, 'Water heater is not working in the shared bath.',     'Pending',     '2026-07-30'),
(4, 1, 101, 'Ceiling fan making a loud noise.',                    'Resolved',    '2026-07-25');

-- FEEDBACK
INSERT INTO feedback (feedback_id, student_id, description, date) VALUES
(1, 1, 'Food quality has been good this week.',                 '2026-08-02'),
(2, 3, 'Dinner portions feel a little small.',                  '2026-07-31'),
(3, 4, 'Washroom cleanliness needs more attention.',            '2026-07-28'),
(4, 2, 'WiFi speed is great, thank you.',                       '2026-07-25');

-- MESS OFF REQUESTS (for manager approval)
INSERT INTO mess_off_requests (mess_off_id, student_id, start_date, end_date, status) VALUES
(1, 1, '2026-08-10', '2026-08-14', 'Pending'),
(2, 3, '2026-08-05', '2026-08-08', 'Approved'),
(3, 4, '2026-07-20', '2026-07-24', 'Rejected'),
(4, 2, '2026-08-15', '2026-08-20', 'Pending');

-- STUDENT ATTENDANCE
INSERT INTO student_attendance (attendance_id, student_id, date, status) VALUES
(1, 1, '2026-08-02', 'Present'),
(2, 2, '2026-08-02', 'Absent'),
(3, 3, '2026-08-02', 'Present'),
(4, 4, '2026-08-02', 'Leave'),
(5, 1, '2026-08-01', 'Present');

-- STAFF ATTENDANCE
INSERT INTO staff_attendance (attendance_id, staff_id, date, status) VALUES
(1, 1, '2026-08-02', 'Present'),
(2, 2, '2026-08-02', 'Present'),
(3, 3, '2026-08-02', 'Absent'),
(4, 1, '2026-08-01', 'Present');

-- VISITORS (registered by staff at the front desk)
INSERT INTO visitors (visitor_id, student_id, registered_by_staff, visitor_name, visit_date) VALUES
(1, 1, 1, 'Ali Khan',     '2026-08-01'),
(2, 3, 1, 'Rahim Uddin',  '2026-07-30'),
(3, 2, 3, 'Fatema Akter', '2026-07-28'),
(4, 1, 2, 'Kamal Hossain','2026-07-25');

-- PARCELS (who received it + the student who collected it)
INSERT INTO parcels (parcel_id, student_id, received_by_staff, status, received_date, collected_at, collected_by_student) VALUES
(1, 1, 1, 'Arrived',   '2026-07-30', NULL, NULL),
(2, 3, 1, 'Collected', '2026-07-28', '2026-07-29 10:30:00', 3),
(3, 2, 2, 'Arrived',   '2026-08-01', NULL, NULL),
(4, 4, 3, 'Collected', '2026-07-26', '2026-07-27 18:00:00', 4),
(5, 5, 1, 'Arrived',   '2026-08-02', NULL, NULL);

-- VIOLATIONS (Open + Resolved)
INSERT INTO violations (violation_id, student_id, staff_id, description, date, status, resolved_at, recorded_by) VALUES
(1, 1, NULL, 'Late night noise in the corridor.',            '2026-07-20', 'Resolved', '2026-07-22', 1),
(2, NULL, 3, 'Left duty early without permission.',          '2026-07-21', 'Resolved', '2026-07-23', 1),
(3, 3, NULL, 'Unauthorized visitor after visiting hours.',   '2026-08-01', 'Open',     NULL,          1),
(4, 5, NULL, 'Smoking inside the room.',                     '2026-08-02', 'Open',     NULL,          2);

-- STUDENT IN / OUT (some currently Out, awaiting staff to record return)
INSERT INTO student_in_out (record_id, student_id, out_date, in_date, reason, status) VALUES
(1, 1, '2026-08-01 09:00:00', '2026-08-01 20:30:00', 'Home visit',         'Returned'),
(2, 2, '2026-08-02 08:00:00', NULL,                  'Market trip',        'Out'),
(3, 3, '2026-07-29 14:00:00', '2026-07-31 10:00:00', 'Family function',    'Returned'),
(4, 4, '2026-08-02 10:00:00', NULL,                  'Doctor appointment', 'Out'),
(5, 5, '2026-08-01 16:00:00', '2026-08-01 21:00:00', 'Tuition class',      'Returned');
