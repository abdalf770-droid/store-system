import sqlite3
from datetime import datetime

DB_NAME = 'instance/store.db'

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        # جدول المستخدمين
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        # جدول الأصناف
        conn.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                purchase_price REAL NOT NULL,
                min_selling_price REAL NOT NULL,
                max_selling_price REAL NOT NULL,
                avg_selling_price REAL NOT NULL,
                current_price REAL NOT NULL,
                quantity INTEGER NOT NULL
            )
        ''')
        # جدول الفواتير اليومية
        conn.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                item_id INTEGER,
                quantity_sold INTEGER,
                selling_price REAL,
                total REAL,
                FOREIGN KEY (item_id) REFERENCES items (id)
            )
        ''')
        # جدول النسخ الاحتياطية (تسجيل فقط)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS backups_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_date TEXT NOT NULL,
                backup_type TEXT NOT NULL,
                file_path TEXT NOT NULL
            )
        ''')
        # إضافة مستخدم افتراضي
        conn.execute("INSERT OR IGNORE INTO users (username, password) VALUES ('admin', 'admin123')")