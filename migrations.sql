-- =====================================================================
-- Migration — upgrades an existing hostel_management database to the
-- current schema:
--   * violation status + parcel tracking      (from the "8 fixes" build)
--   * parcels collected by the STUDENT        (collected_by_staff ->
--                                              collected_by_student)
--   * hostels: gender (boys/girls separation) + geofence coords
--   * notifications table + bell-icon system
--   * student-room gender guard trigger
--   * invoices: invoice_type (room rent / electricity / food / water / other)
--
-- SAFE TO RUN ANY TIME / ANY NUMBER OF TIMES:
--   * on the ORIGINAL schema  -> applies every step
--   * on the previous build   -> applies only the new steps
--   * on the current schema   -> does nothing, raises no errors
--
-- Run with:   mysql -u root < migrations.sql
-- (or import the file in phpMyAdmin)
--
-- Fresh installs don't need this file: hostel_management_schema.sql
-- already includes everything below.
--
-- Note: uses MariaDB "ADD COLUMN IF NOT EXISTS" / "CREATE TABLE IF NOT
-- EXISTS" syntax (XAMPP MariaDB 10.4). MariaDB has no "ADD CONSTRAINT
-- IF NOT EXISTS" / "DROP FOREIGN KEY IF EXISTS", so FKs and index drops
-- go through information_schema-guarded stored procedures.
-- =====================================================================
USE hostel_management;

-- ---------------------------------------------------------------------
-- 1) Violations: add a resolvable status
-- ---------------------------------------------------------------------
ALTER TABLE violations
    ADD COLUMN IF NOT EXISTS status      ENUM('Open', 'Resolved') NOT NULL DEFAULT 'Open' AFTER date,
    ADD COLUMN IF NOT EXISTS resolved_at DATE NULL AFTER status;

-- ---------------------------------------------------------------------
-- 2) Parcels: staff who received it + when it was collected
-- ---------------------------------------------------------------------
ALTER TABLE parcels
    ADD COLUMN IF NOT EXISTS received_by_staff INT NULL AFTER student_id,
    ADD COLUMN IF NOT EXISTS collected_at      DATETIME NULL AFTER received_date;

-- 3) Parcel received_by FK (original schema had none)
DROP PROCEDURE IF EXISTS migrate_parcel_received_fk;
DELIMITER //
CREATE PROCEDURE migrate_parcel_received_fk()
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.REFERENTIAL_CONSTRAINTS
                   WHERE CONSTRAINT_SCHEMA = DATABASE()
                     AND CONSTRAINT_NAME = 'fk_parcels_received_by') THEN
        ALTER TABLE parcels ADD CONSTRAINT fk_parcels_received_by
            FOREIGN KEY (received_by_staff) REFERENCES staff(staff_id) ON DELETE SET NULL;
    END IF;
END//
DELIMITER ;
CALL migrate_parcel_received_fk();
DROP PROCEDURE IF EXISTS migrate_parcel_received_fk;

-- 4) Parcels: collection now belongs to the STUDENT.
--    Drop the old collected_by_staff column (and whichever FK referenced
--    it — the name may be auto-generated or from an earlier migration),
--    then add collected_by_student.
DROP PROCEDURE IF EXISTS migrate_parcel_collect;
DELIMITER //
CREATE PROCEDURE migrate_parcel_collect()
BEGIN
    DECLARE done INT DEFAULT 0;
    DECLARE fk_name VARCHAR(64);
    DECLARE cur CURSOR FOR
        SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'parcels'
          AND COLUMN_NAME = 'collected_by_staff'
          AND REFERENCED_TABLE_NAME = 'staff';
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = 1;

    OPEN cur;
    drop_loop: LOOP
        FETCH cur INTO fk_name;
        IF done THEN LEAVE drop_loop; END IF;
        SET @s = CONCAT('ALTER TABLE parcels DROP FOREIGN KEY `', fk_name, '`');
        PREPARE stmt FROM @s;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END LOOP;
    CLOSE cur;

    IF EXISTS (SELECT 1 FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'parcels'
                 AND COLUMN_NAME = 'collected_by_staff') THEN
        ALTER TABLE parcels DROP COLUMN collected_by_staff;
    END IF;
END//
DELIMITER ;
CALL migrate_parcel_collect();
DROP PROCEDURE IF EXISTS migrate_parcel_collect;

ALTER TABLE parcels
    ADD COLUMN IF NOT EXISTS collected_by_student INT NULL AFTER collected_at;

DROP PROCEDURE IF EXISTS migrate_parcel_collect_fk;
DELIMITER //
CREATE PROCEDURE migrate_parcel_collect_fk()
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.REFERENTIAL_CONSTRAINTS
                   WHERE CONSTRAINT_SCHEMA = DATABASE()
                     AND CONSTRAINT_NAME = 'fk_parcels_collected_by_student') THEN
        ALTER TABLE parcels ADD CONSTRAINT fk_parcels_collected_by_student
            FOREIGN KEY (collected_by_student) REFERENCES students(student_id) ON DELETE SET NULL;
    END IF;
END//
DELIMITER ;
CALL migrate_parcel_collect_fk();
DROP PROCEDURE IF EXISTS migrate_parcel_collect_fk;

-- ---------------------------------------------------------------------
-- 5) Hostels: gender (single-gender buildings) + geofence for attendance
--    Gender is added nullable, backfilled by a name heuristic, then made
--    NOT NULL so it stays safe on any re-run.
-- ---------------------------------------------------------------------
ALTER TABLE hostels
    ADD COLUMN IF NOT EXISTS gender   ENUM('Male', 'Female') NULL AFTER location,
    ADD COLUMN IF NOT EXISTS lat      DECIMAL(10,7) NULL AFTER total_rooms,
    ADD COLUMN IF NOT EXISTS lng      DECIMAL(10,7) NULL AFTER lat,
    ADD COLUMN IF NOT EXISTS radius_m INT NOT NULL DEFAULT 50 AFTER lng;

UPDATE hostels
SET gender = IF(
    LOWER(hostel_name) LIKE '%girls%' OR LOWER(hostel_name) LIKE '%ladies%'
    OR LOWER(hostel_name) LIKE '%female%', 'Female', 'Male')
WHERE gender IS NULL;

ALTER TABLE hostels MODIFY gender ENUM('Male', 'Female') NOT NULL;

-- Wider text columns so long reverse-geocoded addresses can't overflow
-- under STRICT_TRANS_TABLES (MODIFY is idempotent - safe to re-run).
ALTER TABLE hostels MODIFY hostel_name VARCHAR(150) NOT NULL;
ALTER TABLE hostels MODIFY location     VARCHAR(255) NULL;

-- ---------------------------------------------------------------------
-- 6) Notifications (bell icon) table + index
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    notification_id  INT AUTO_INCREMENT PRIMARY KEY,
    user_id          INT NOT NULL,
    title            VARCHAR(150) NOT NULL,
    message          TEXT NOT NULL,
    link             VARCHAR(255) NULL,
    is_read          TINYINT(1) NOT NULL DEFAULT 0,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

DROP PROCEDURE IF EXISTS migrate_notifications_index;
DELIMITER //
CREATE PROCEDURE migrate_notifications_index()
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.STATISTICS
                   WHERE TABLE_SCHEMA = DATABASE()
                     AND TABLE_NAME = 'notifications'
                     AND INDEX_NAME = 'idx_notifications_user') THEN
        CREATE INDEX idx_notifications_user ON notifications(user_id, is_read);
    END IF;
END//
DELIMITER ;
CALL migrate_notifications_index();
DROP PROCEDURE IF EXISTS migrate_notifications_index;

-- ---------------------------------------------------------------------
-- 7) Triggers (idempotent: drop + recreate)
-- ---------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_student_delete_bed;
DELIMITER //
CREATE TRIGGER trg_student_delete_bed
AFTER DELETE ON students
FOR EACH ROW
BEGIN
    IF OLD.room_id IS NOT NULL THEN
        UPDATE rooms SET available_beds = available_beds + 1
        WHERE room_id = OLD.room_id;
    END IF;
END//
DELIMITER ;

DROP TRIGGER IF EXISTS trg_student_room_gender;
DELIMITER //
CREATE TRIGGER trg_student_room_gender
BEFORE INSERT ON students
FOR EACH ROW
BEGIN
    IF NEW.room_id IS NOT NULL THEN
        IF EXISTS (
            SELECT 1
            FROM rooms r JOIN hostels h ON r.hostel_id = h.hostel_id
            WHERE r.room_id = NEW.room_id AND h.gender <> NEW.gender
        ) THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Room hostel gender does not match the student gender';
        END IF;
    END IF;
END//
DELIMITER ;

DROP TRIGGER IF EXISTS trg_student_room_gender_upd;
DELIMITER //
CREATE TRIGGER trg_student_room_gender_upd
BEFORE UPDATE ON students
FOR EACH ROW
BEGIN
    IF NEW.room_id IS NOT NULL THEN
        IF EXISTS (
            SELECT 1
            FROM rooms r JOIN hostels h ON r.hostel_id = h.hostel_id
            WHERE r.room_id = NEW.room_id AND h.gender <> NEW.gender
        ) THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Room hostel gender does not match the student gender';
        END IF;
    END IF;
END//
DELIMITER ;

-- ---------------------------------------------------------------------
-- 8) Invoices: invoice type (room rent / electricity / food / water / other)
-- ---------------------------------------------------------------------
ALTER TABLE invoices
    ADD COLUMN IF NOT EXISTS invoice_type ENUM('Room Rent', 'Electricity', 'Food', 'Water', 'Other')
        NOT NULL DEFAULT 'Room Rent' AFTER student_id;

-- ---------------------------------------------------------------------
-- 9) Re-sync each hostel's room count with the real number of rooms
--    (idempotent: safe to run any time)
-- ---------------------------------------------------------------------
UPDATE hostels h
SET h.total_rooms = (SELECT COUNT(*) FROM rooms r WHERE r.hostel_id = h.hostel_id);

-- ---------------------------------------------------------------------
-- 10) Human-friendly unique IDs: students.student_no + staff.staff_no
--     (e.g. STU-0001 / STF-0001). Added nullable, backfilled from the
--     primary key, then made NOT NULL + unique. Idempotent on MariaDB
--     ("ADD COLUMN IF NOT EXISTS"). The web copy is MySQL 8 and uses
--     `python scripts/web_db.py migrate` (information_schema-guarded).
-- ---------------------------------------------------------------------
ALTER TABLE students ADD COLUMN IF NOT EXISTS student_no VARCHAR(20) NULL AFTER student_id;
ALTER TABLE staff    ADD COLUMN IF NOT EXISTS staff_no    VARCHAR(20) NULL AFTER staff_id;

UPDATE students SET student_no = CONCAT('STU-', LPAD(student_id, 4, '0'))
WHERE student_no IS NULL OR student_no = '';
UPDATE staff SET staff_no = CONCAT('STF-', LPAD(staff_id, 4, '0'))
WHERE staff_no IS NULL OR staff_no = '';

ALTER TABLE students MODIFY student_no VARCHAR(20) NOT NULL;
ALTER TABLE staff    MODIFY staff_no    VARCHAR(20) NOT NULL;

DROP PROCEDURE IF EXISTS migrate_student_no_unique;
DELIMITER //
CREATE PROCEDURE migrate_student_no_unique()
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.STATISTICS
                   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'students'
                     AND INDEX_NAME = 'uq_students_student_no') THEN
        ALTER TABLE students ADD UNIQUE KEY uq_students_student_no (student_no);
    END IF;
END//
DELIMITER ;
CALL migrate_student_no_unique();
DROP PROCEDURE IF EXISTS migrate_student_no_unique;

DROP PROCEDURE IF EXISTS migrate_staff_no_unique;
DELIMITER //
CREATE PROCEDURE migrate_staff_no_unique()
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.STATISTICS
                   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'staff'
                     AND INDEX_NAME = 'uq_staff_staff_no') THEN
        ALTER TABLE staff ADD UNIQUE KEY uq_staff_staff_no (staff_no);
    END IF;
END//
DELIMITER ;
CALL migrate_staff_no_unique();
DROP PROCEDURE IF EXISTS migrate_staff_no_unique;
