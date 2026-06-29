import sqlite3
import os

DB_NAME = "compliance.db"

def init_db():
    """Initializes the database schema and seeds sample data."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matters (
            matter_id TEXT PRIMARY KEY,
            matter_name TEXT NOT NULL,
            folder_path TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS access_control (
            email TEXT,
            matter_id TEXT,
            access_level TEXT NOT NULL,
            PRIMARY KEY (email, matter_id),
            FOREIGN KEY(email) REFERENCES users(email),
            FOREIGN KEY(matter_id) REFERENCES matters(matter_id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            operator_email TEXT NOT NULL,
            target_email TEXT NOT NULL,
            matter_id TEXT NOT NULL,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            details TEXT
        )
    """)
    
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO users VALUES (?, ?, ?)", [
            ("associate1@firm.com", "Alice Smith", "Associate"),
            ("partner1@firm.com", "Bob Jones", "Partner"),
            ("intern1@firm.com", "Charlie Brown", "Intern")
        ])
        cursor.executemany("INSERT INTO matters VALUES (?, ?, ?)", [
            ("CASE101", "TechCorp NDA", "vault/Case_101_NDA_TechCorp"),
            ("CASE102", "FinBank Merger", "vault/Case_102_Merger_FinBank")
        ])
        
        os.makedirs("vault/Case_101_NDA_TechCorp", exist_ok=True)
        os.makedirs("vault/Case_102_Merger_FinBank", exist_ok=True)
        
    conn.commit()
    conn.close()

def log_action(cursor, operator, target, matter_id, action, status, details=""):
    """Writes an immutable log entry using the caller's open database transaction cursor."""
    cursor.execute("""
        INSERT INTO audit_logs (operator_email, target_email, matter_id, action, status, details)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (operator, target, matter_id, action, status, details))

if __name__ == "__main__":
    init_db()
    print("Database initialized and mock data seeded successfully.")