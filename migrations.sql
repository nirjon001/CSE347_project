-- =====================================================================
-- Migration — upgrades an existing hostel_management database that was
-- created BEFORE the "8 fixes" build (violation status + parcel tracking).
--
-- SAFE TO RUN ANY TIME / ANY NUMBER OF TIMES:
--   * on the OLD schema   -> adds the new columns, foreign keys, trigger
--   * on an already-updated database -> does nothing, raises no errors
--
-- Run with:   mysql -u root < migrations.sql
-- (or import the file in phpMyAdmin)
--
-- Fresh installs don't need this file: hostel_management_schema.sql
-- already includes everything below.
--
-- Note: uses MariaDB "ADD COLUMN IF NOT EXISTS" syntax (the project runs
-- on XAMPP MariaDB). The two foreign keys go through a tiny stored
-- procedure because MariaDB has no "ADD CONSTRAINT IF NOT EXISTS".
-- =====================================================================
USE hostel_management;

-- 1) Violations: add a resolvable status
ALTER TABLE violations
    ADD COLUMN IF NOT EXISTS status      ENUM('Open', 'Resolved') NOT NULL DEFAULT 'Open' AFTER date,
    ADD COLUMN IF NOT EXISTS resolved_at DATE NULL AFTER status;

-- 2) Parcels: track who received it and who/when it was collected
ALTER TABLE parcels
    ADD COLUMN IF NOT EXISTS received_by_staff  INT NULL AFTER student_id,
    ADD COLUMN IF NOT EXISTS collected_at       DATETIME NULL AFTER received_date,
    ADD COLUMN IF NOT EXISTS collected_by_staff INT NULL AFTER collected_at;

-- 3) Parcel foreign keys (added only if still missing)
DROP PROCEDURE IF EXISTS migrate_parcel_fks;
DELIMITER //
CREATE PROCEDURE migrate_parcel_fks()
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.REFERENTIAL_CONSTRAINTS
                   WHERE CONSTRAINT_SCHEMA = DATABASE()
                     AND CONSTRAINT_NAME = 'fk_parcels_received_by') THEN
        ALTER TABLE parcels ADD CONSTRAINT fk_parcels_received_by
            FOREIGN KEY (received_by_staff) REFERENCES staff(staff_id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.REFERENTIAL_CONSTRAINTS
                   WHERE CONSTRAINT_SCHEMA = DATABASE()
                     AND CONSTRAINT_NAME = 'fk_parcels_collected_by') THEN
        ALTER TABLE parcels ADD CONSTRAINT fk_parcels_collected_by
            FOREIGN KEY (collected_by_staff) REFERENCES staff(staff_id) ON DELETE SET NULL;
    END IF;
END//
DELIMITER ;
CALL migrate_parcel_fks();
DROP PROCEDURE IF EXISTS migrate_parcel_fks;

-- 4) Trigger: free a bed automatically when a student is deleted
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
