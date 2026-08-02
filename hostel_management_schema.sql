-- =====================================================================
-- Hostel Management System — MySQL Schema
-- CSE347: Information System Analysis & Design
-- Derived directly from the corrected UML class diagram.
-- =====================================================================

CREATE DATABASE IF NOT EXISTS hostel_management;
USE hostel_management;

-- ---------------------------------------------------------------------
-- 1. USERS  (base table — mirrors the User superclass)
-- ---------------------------------------------------------------------
CREATE TABLE users (
    user_id     INT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(50)  NOT NULL UNIQUE,
    password    VARCHAR(255) NOT NULL,        -- store a hash, never plain text
    role        ENUM('student', 'manager', 'staff') NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 2. ROLE TABLES (each links back to users — table-per-subtype)
-- ---------------------------------------------------------------------
CREATE TABLE managers (
    manager_id   INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT NOT NULL UNIQUE,
    name         VARCHAR(100) NOT NULL,
    designation  VARCHAR(50)  NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE staff (
    staff_id     INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT NOT NULL UNIQUE,
    name         VARCHAR(100) NOT NULL,
    designation  VARCHAR(50)  NOT NULL,   -- e.g. Caretaker, Cook, Watchman, Guard
    salary       DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE hostels (
    hostel_id    INT AUTO_INCREMENT PRIMARY KEY,
    hostel_name  VARCHAR(100) NOT NULL,
    location     VARCHAR(150),
    total_rooms  INT NOT NULL DEFAULT 0
) ENGINE=InnoDB;

CREATE TABLE rooms (
    room_id         INT AUTO_INCREMENT PRIMARY KEY,
    hostel_id       INT NOT NULL,
    room_no         VARCHAR(20) NOT NULL,
    total_beds      INT NOT NULL,
    available_beds  INT NOT NULL,
    FOREIGN KEY (hostel_id) REFERENCES hostels(hostel_id) ON DELETE CASCADE,
    UNIQUE KEY uq_room_per_hostel (hostel_id, room_no)
) ENGINE=InnoDB;

CREATE TABLE students (
    student_id   INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT NOT NULL UNIQUE,
    name         VARCHAR(100) NOT NULL,
    email        VARCHAR(100) UNIQUE,
    phone        VARCHAR(20),
    address      VARCHAR(255),
    gender       VARCHAR(15),
    room_id      INT NULL,                  -- nullable: student may not be allocated yet
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 3. STUDENT-LINKED FEATURE TABLES
-- ---------------------------------------------------------------------
CREATE TABLE complaints (
    complaint_id  INT AUTO_INCREMENT PRIMARY KEY,
    student_id    INT NOT NULL,
    room_id       INT NULL,
    description   TEXT NOT NULL,
    status        ENUM('Pending', 'In Progress', 'Resolved') DEFAULT 'Pending',
    date          DATE NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE invoices (
    invoice_id      INT AUTO_INCREMENT PRIMARY KEY,
    student_id      INT NOT NULL,
    amount          DECIMAL(10,2) NOT NULL,
    due_date        DATE NOT NULL,
    payment_status  ENUM('Unpaid', 'Paid', 'Overdue') DEFAULT 'Unpaid',
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE student_attendance (
    attendance_id  INT AUTO_INCREMENT PRIMARY KEY,
    student_id     INT NOT NULL,
    date           DATE NOT NULL,
    status         ENUM('Present', 'Absent', 'Leave') NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    UNIQUE KEY uq_student_date (student_id, date)
) ENGINE=InnoDB;

CREATE TABLE visitors (
    visitor_id           INT AUTO_INCREMENT PRIMARY KEY,
    student_id           INT NOT NULL,          -- who they're visiting
    registered_by_staff  INT NULL,              -- staff who processed the registration
    visitor_name         VARCHAR(100) NOT NULL,
    visit_date            DATE NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (registered_by_staff) REFERENCES staff(staff_id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE parcels (
    parcel_id      INT AUTO_INCREMENT PRIMARY KEY,
    student_id     INT NOT NULL,
    status         ENUM('Arrived', 'Collected') DEFAULT 'Arrived',
    received_date  DATE NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE mess_off_requests (
    mess_off_id  INT AUTO_INCREMENT PRIMARY KEY,
    student_id   INT NOT NULL,
    start_date   DATE NOT NULL,
    end_date     DATE NOT NULL,
    status       ENUM('Pending', 'Approved', 'Rejected') DEFAULT 'Pending',
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE feedback (
    feedback_id  INT AUTO_INCREMENT PRIMARY KEY,
    student_id   INT NOT NULL,
    description  TEXT NOT NULL,
    date         DATE NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE student_in_out (
    record_id   INT AUTO_INCREMENT PRIMARY KEY,
    student_id  INT NOT NULL,
    out_date    DATETIME NOT NULL,
    in_date     DATETIME NULL,
    reason      VARCHAR(255),
    status      ENUM('Out', 'Returned') DEFAULT 'Out',
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 4. STAFF-LINKED FEATURE TABLES
-- ---------------------------------------------------------------------
CREATE TABLE staff_attendance (
    attendance_id  INT AUTO_INCREMENT PRIMARY KEY,
    staff_id       INT NOT NULL,
    date           DATE NOT NULL,
    status         ENUM('Present', 'Absent', 'Leave') NOT NULL,
    FOREIGN KEY (staff_id) REFERENCES staff(staff_id) ON DELETE CASCADE,
    UNIQUE KEY uq_staff_date (staff_id, date)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 5. VIOLATIONS  (can belong to a student OR a staff member, not both)
-- ---------------------------------------------------------------------
CREATE TABLE violations (
    violation_id  INT AUTO_INCREMENT PRIMARY KEY,
    student_id    INT NULL,
    staff_id      INT NULL,
    description   TEXT NOT NULL,
    date          DATE NOT NULL,
    recorded_by   INT NOT NULL,           -- manager_id or staff_id who logged it
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (staff_id) REFERENCES staff(staff_id) ON DELETE CASCADE,
    CONSTRAINT chk_violation_target CHECK (
        (student_id IS NOT NULL AND staff_id IS NULL) OR
        (student_id IS NULL AND staff_id IS NOT NULL)
    )
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 6. MESS MENU  (managed by a manager, viewed by students)
-- ---------------------------------------------------------------------
CREATE TABLE mess_menu (
    menu_id           INT AUTO_INCREMENT PRIMARY KEY,
    manager_id        INT NOT NULL,
    day_of_week       ENUM('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday') NOT NULL,
    meal_type         ENUM('Breakfast','Lunch','Dinner') NOT NULL,
    items_description TEXT NOT NULL,
    FOREIGN KEY (manager_id) REFERENCES managers(manager_id) ON DELETE CASCADE,
    UNIQUE KEY uq_menu_slot (day_of_week, meal_type)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Helpful indexes for common lookups
-- ---------------------------------------------------------------------
CREATE INDEX idx_students_room       ON students(room_id);
CREATE INDEX idx_complaints_student  ON complaints(student_id);
CREATE INDEX idx_invoices_student    ON invoices(student_id);
CREATE INDEX idx_parcels_student     ON parcels(student_id);
CREATE INDEX idx_visitors_student    ON visitors(student_id);
