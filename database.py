import mysql.connector

# DIRECT DB CONFIG
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "property_db"
}

db = mysql.connector.connect(**DB_CONFIG)
cursor = db.cursor()

# ==============================
# NEW / MISSING TABLES
# ==============================

TABLE_QUERIES = [

    # STAFF USERS
    """
    CREATE TABLE IF NOT EXISTS staff_users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) UNIQUE,
        password VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,

    # PROPERTY IMAGES (NORMALIZED)
    """
    CREATE TABLE IF NOT EXISTS property_images (
        id INT AUTO_INCREMENT PRIMARY KEY,
        property_id INT,
        image_path TEXT,
        uploaded_by ENUM('admin','staff'),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    )
    """,

    # COLLABORATION PAYMENTS (TRACK MONTHLY / DUE / PAID)
    """
    CREATE TABLE IF NOT EXISTS collaboration_payments (
        id INT AUTO_INCREMENT PRIMARY KEY,
        collaboration_id INT,
        due_date DATE,
        amount DECIMAL(12,2),
        paid_amount DECIMAL(12,2),
        status ENUM('pending','paid','overdue'),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (collaboration_id) REFERENCES collaborations(id) ON DELETE CASCADE
    )
    """,

    # EMAIL ALERT LOGS
    """
    CREATE TABLE IF NOT EXISTS email_alerts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        reference_type ENUM('collaboration','property'),
        reference_id INT,
        email VARCHAR(255),
        message TEXT,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,

    # STAFF PROPERTY MAPPING (WHO ADDED WHAT)
    """
    CREATE TABLE IF NOT EXISTS staff_properties (
        id INT AUTO_INCREMENT PRIMARY KEY,
        staff_username VARCHAR(50),
        property_id INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    )
    """
]

for query in TABLE_QUERIES:
    cursor.execute(query)

db.commit()

# ==============================
# SHOW UPDATED STRUCTURE
# ==============================

print("\n========== UPDATED DATABASE STRUCTURE ==========\n")

cursor.execute("SHOW TABLES")
tables = cursor.fetchall()

for (table_name,) in tables:
    print(f"\n--- TABLE: {table_name} ---")
    cursor.execute(f"DESCRIBE {table_name}")
    for c in cursor.fetchall():
        print(
            f"Column: {c[0]:<25} "
            f"Type: {c[1]:<20} "
            f"Null: {c[2]:<5} "
            f"Key: {c[3]}"
        )

cursor.close()
db.close()
