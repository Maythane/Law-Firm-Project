-- ฐานข้อมูลที่สร้างไว้ก่อนหน้านี้ (volume เดิม) รันไฟล์นี้ครั้งเดียว — schema.sql ทำงานเฉพาะตอน volume ว่าง
-- docker compose exec -T db mysql lawfirm-db < migrations/001_lawyer_cases.sql
ALTER TABLE case_assignments
    MODIFY status ENUM('pending', 'accepted', 'declined', 'withdrawn') NOT NULL DEFAULT 'pending',
    ADD COLUMN withdraw_requested_at DATETIME,
    ADD COLUMN withdraw_reason_code VARCHAR(20),
    ADD COLUMN withdraw_note VARCHAR(255),
    ADD COLUMN withdraw_reject_reason VARCHAR(255);

CREATE TABLE IF NOT EXISTS case_notes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    case_id INT NOT NULL,
    author_id INT NOT NULL,
    text TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases(id),
    FOREIGN KEY (author_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS case_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    case_id INT NOT NULL,
    actor_id INT NOT NULL,
    kind VARCHAR(30) NOT NULL,
    detail VARCHAR(500) NOT NULL,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases(id),
    FOREIGN KEY (actor_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
