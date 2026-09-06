-- BL-18: schema สำหรับ MariaDB 10.4 (XAMPP) — utf8mb4_unicode_ci ตามที่ตัดสินไว้ (ห้าม utf8mb4_0900_ai_ci)
-- ดูขอบเขตงานเต็มที่ backlog.md#bl-18 และผัง ER เต็มที่ uml.md หัวข้อ 3

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    role ENUM('admin', 'manager', 'lawyer') NOT NULL,
    name VARCHAR(120) NOT NULL,
    citizen_id VARCHAR(20) NOT NULL,
    phone VARCHAR(20),
    username VARCHAR(50) NOT NULL,
    password_hash VARCHAR(255) NOT NULL DEFAULT '',
    license_no VARCHAR(50), -- เฉพาะ lawyer
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    UNIQUE KEY idx_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS clients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    citizen_id VARCHAR(20) NOT NULL,
    phone VARCHAR(20),
    company VARCHAR(150) -- ชื่อบริษัท ถ้าเป็นนิติบุคคล
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS cases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    black_case_no VARCHAR(20),
    red_case_no VARCHAR(20),
    client_id INT NOT NULL,
    client_role VARCHAR(50) NOT NULL,
    opposing_party VARCHAR(255) NOT NULL,
    court_name VARCHAR(255) NOT NULL,
    status ENUM('open', 'filed', 'trial', 'judged', 'final', 'closed', 'cancelled')
        NOT NULL DEFAULT 'open',
    opened_date DATE NOT NULL,
    filed_date DATE, -- ว่างได้ถ้ายังไม่ฟ้อง
    FOREIGN KEY (client_id) REFERENCES clients(id),
    UNIQUE KEY idx_black (black_case_no),
    UNIQUE KEY idx_red (red_case_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS case_assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    case_id INT NOT NULL,
    lawyer_id INT NOT NULL,
    assigned_by INT NOT NULL,
    assigned_at DATETIME NOT NULL,
    status ENUM('pending', 'accepted', 'declined') NOT NULL DEFAULT 'pending',
    responded_at DATETIME, -- ว่างได้
    decline_reason VARCHAR(255), -- บังคับเมื่อปฏิเสธ
    is_lead TINYINT(1) NOT NULL DEFAULT 0,
    FOREIGN KEY (case_id) REFERENCES cases(id),
    FOREIGN KEY (lawyer_id) REFERENCES users(id),
    FOREIGN KEY (assigned_by) REFERENCES users(id),
    UNIQUE KEY idx_assign (case_id, lawyer_id, status) -- บังคับ BR-17 ที่ระดับฐานข้อมูล
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS appointments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    case_id INT NOT NULL,
    lawyer_id INT NOT NULL,
    kind ENUM('hearing', 'meeting', 'deadline') NOT NULL,
    starts_at DATETIME NOT NULL,
    ends_at DATETIME NOT NULL,
    location VARCHAR(255),
    court_name VARCHAR(255), -- เฉพาะนัดศาล
    room_no VARCHAR(50), -- เฉพาะนัดศาล
    triggered_by_event VARCHAR(255), -- เฉพาะกำหนดยื่นเอกสาร
    is_done TINYINT(1) NOT NULL DEFAULT 0,
    is_cancelled TINYINT(1) NOT NULL DEFAULT 0,
    cancel_reason VARCHAR(255),
    cancelled_at DATETIME,
    FOREIGN KEY (case_id) REFERENCES cases(id),
    FOREIGN KEY (lawyer_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_sched ON appointments(lawyer_id, starts_at);

CREATE TABLE IF NOT EXISTS appointment_changes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    appointment_id INT NOT NULL,
    old_starts_at DATETIME NOT NULL,
    new_starts_at DATETIME NOT NULL,
    reason VARCHAR(255),
    changed_at DATETIME NOT NULL,
    FOREIGN KEY (appointment_id) REFERENCES appointments(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
