from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'ibn_al_shaykh_secret_key_2024'

DB_NAME = 'store.db'

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, purchase_price REAL NOT NULL, min_selling_price REAL NOT NULL, max_selling_price REAL NOT NULL, avg_selling_price REAL NOT NULL, current_price REAL NOT NULL, quantity INTEGER NOT NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS invoices (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, item_id INTEGER, quantity_sold INTEGER, selling_price REAL, total REAL)')
        conn.execute("INSERT OR IGNORE INTO users (username, password) VALUES ('admin', 'admin123')")
        conn.commit()
    print("✅ قاعدة البيانات جاهزة!")

init_db()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password)).fetchone()
        if user:
            session['user'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='بيانات الدخول غير صحيحة')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return '''
    <html dir="rtl">
    <head><title>الرئيسية</title></head>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1>🏪 محل ابن الشيخ</h1>
        <p>مرحباً بك في نظام إدارة المحل</p>
        <div style="display: flex; gap: 10px; justify-content: center;">
            <a href="/sales" style="background: #667eea; color: white; padding: 10px 20px; text-decoration: none;">💰 المبيعات</a>
            <a href="/inventory" style="background: #667eea; color: white; padding: 10px 20px; text-decoration: none;">📦 المخازن</a>
            <a href="/add_item" style="background: #667eea; color: white; padding: 10px 20px; text-decoration: none;">➕ إضافة صنف</a>
            <a href="/logout" style="background: #dc3545; color: white; padding: 10px 20px; text-decoration: none;">🚪 خروج</a>
        </div>
    </body>
    </html>
    '''

@app.route('/sales')
def sales():
    if 'user' not in session:
        return redirect(url_for('login'))
    return "صفحة المبيعات - قيد التطوير"

@app.route('/inventory')
def inventory():
    if 'user' not in session:
        return redirect(url_for('login'))
    return "صفحة المخازن - قيد التطوير"

@app.route('/add_item')
def add_item():
    if 'user' not in session:
        return redirect(url_for('login'))
    return "صفحة إضافة صنف - قيد التطوير"

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
