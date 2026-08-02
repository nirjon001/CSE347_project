-- =====================================================================
-- Seed data for the Hostel Management System
-- Logins:
--   manager  / admin123
--   staff1   / staff123
--   student1 / student123
--   student2 / student123
-- =====================================================================
USE hostel_management;

-- USERS (passwords are scrypt hashes generated with werkzeug)
INSERT INTO users (user_id, username, password, role) VALUES
(1, 'manager',  'scrypt:32768:8:1$ItNtyupaUcH625hR$ec8438bf1d1dfa39c537087dbcc24ea6aa9c973e75cb1ec129ddc35a0e435822da3c837a8dca62cb58e06faa7added134f14fdcfd770664b449d3884bcd32c5c', 'manager'),
(2, 'staff1',   'scrypt:32768:8:1$ueps82YvEwUsZejm$c78857c37c492e6d397829e38db021ad62216d0b100661db99e719fd32043f2c005e49c54d4643da12817f6ef97e1aec7e713560a45f2e647651b1690ed46a2b', 'staff'),
(3, 'student1', 'scrypt:32768:8:1$dHF9S6ravzQbODud$7723829848ee0605439e56da915d58d7b7a367f308a99f8b387afc960c1d110ad19b88aa851ec4bc55c7ed7b8eda9633df35a8b19e5130284ca844a31980db9d', 'student'),
(4, 'student2', 'scrypt:32768:8:1$dHF9S6ravzQbODud$7723829848ee0605439e56da915d58d7b7a367f308a99f8b387afc960c1d110ad19b88aa851ec4bc55c7ed7b8eda9633df35a8b19e5130284ca844a31980db9d', 'student');

-- MANAGERS
INSERT INTO managers (manager_id, user_id, name, designation) VALUES
(1, 1, 'Ayesha Rahman', 'Chief Manager');

-- STAFF
INSERT INTO staff (staff_id, user_id, name, designation, salary) VALUES
(1, 2, 'Karim Mia', 'Caretaker', 15000.00);

-- HOSTELS & ROOMS
INSERT INTO hostels (hostel_id, hostel_name, location, total_rooms) VALUES
(1, 'Main Hostel', 'North Campus', 2);

INSERT INTO rooms (room_id, hostel_id, room_no, total_beds, available_beds) VALUES
(101, 1, '101', 2, 1),
(102, 1, '102', 2, 2);

-- STUDENTS
INSERT INTO students (student_id, user_id, name, email, phone, address, gender, room_id) VALUES
(1, 3, 'Rafi Ahmed', 'rafi@example.com', '01700000001', 'Dhaka', 'Male', 101),
(2, 4, 'Sadia Islam', 'sadia@example.com', '01700000002', 'Chattogram', 'Female', NULL);

-- MESS MENU (a few sample entries)
INSERT INTO mess_menu (menu_id, manager_id, day_of_week, meal_type, items_description) VALUES
(1, 1, 'Saturday', 'Breakfast', 'Paratha, Dal, Egg, Tea'),
(2, 1, 'Saturday', 'Lunch', 'Rice, Chicken Curry, Salad'),
(3, 1, 'Saturday', 'Dinner', 'Rice, Fish Fry, Vegetable');

-- INVOICES
INSERT INTO invoices (invoice_id, student_id, amount, due_date, payment_status) VALUES
(1, 1, 4500.00, '2026-09-01', 'Unpaid'),
(2, 2, 4500.00, '2026-09-01', 'Paid');

-- COMPLAINTS (one open example)
INSERT INTO complaints (complaint_id, student_id, room_id, description, status, date) VALUES
(1, 1, 101, 'The bathroom tap is leaking since yesterday.', 'Pending', '2026-08-02');

-- FEEDBACK (one example)
INSERT INTO feedback (feedback_id, student_id, description, date) VALUES
(1, 1, 'Food quality has been good this week.', '2026-08-02');
