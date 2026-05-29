from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g
from datetime import datetime
import sqlite3
import os
import shutil
import urllib.parse as urlparse
import traceback

app = Flask(__name__)
app.secret_key = 'ibn_al_shaykh_secret_key_2024'

DB_NAME = 'store.db'

# ============================================================
# إعدادات قاعدة البيانات (تدعم SQLite و PostgreSQL)
# ============================================================

def get_db():
    """إرجاع اتصال بقاعدة البيانات"""
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if DATABASE_URL:
        if 'db' not in g:
            try:
                import psycopg2
                from psycopg2.extras import RealDictCursor
                
                urlparse.uses_netloc.append("postgres")
                url = urlparse.urlparse(DATABASE_URL)
                
                g.db = psycopg2.connect(
                    database=url.path[1:],
                    user=url.username,
                    password=url.password,
                    host=url.hostname,
                    port=url.port,
                    sslmode='require'
                )
            except ImportError:
                print("⚠️ psycopg2 غير مثبت")
                raise
        return g.db
    else:
        if 'db' not in g:
            g.db = sqlite3.connect(DB_NAME)
            g.db.row_factory = sqlite3.Row
        return g.db

def get_cursor():
    """إرجاع مؤشر cursor مناسب لنوع قاعدة البيانات"""
    DATABASE_URL = os.environ.get('DATABASE_URL')
    db = get_db()
    
    if DATABASE_URL:
        return db.cursor()
    else:
        return db.cursor()

def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """تنفيذ استعلام مع دعم كل من SQLite و PostgreSQL"""
    DATABASE_URL = os.environ.get('DATABASE_URL')
    db = get_db()
    cursor = get_cursor()
    
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if fetch_one:
            result = cursor.fetchone()
            if DATABASE_URL and result:
                result = dict(result)
            db.commit()
            return result
        elif fetch_all:
            results = cursor.fetchall()
            if DATABASE_URL and results:
                results = [dict(row) for row in results]
            db.commit()
            return results
        else:
            db.commit()
            return cursor
    except Exception as e:
        db.rollback()
        print(f"⚠️ خطأ في الاستعلام: {e}")
        print(f"⚠️ الاستعلام: {query}")
        traceback.print_exc()
        raise e

@app.teardown_appcontext
def close_db(error=None):
    """إغلاق اتصال قاعدة البيانات بعد كل طلب"""
    if 'db' in g:
        g.db.close()

# ============================================================
# تهيئة قاعدة البيانات
# ============================================================

def # ============================================================
# تهيئة قاعدة البيانات (داخل سياق التطبيق)
# ============================================================

with app.app_context():
    init_db()
    """تهيئة قاعدة البيانات (جداول ومستخدم افتراضي)"""
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    try:
        if DATABASE_URL:
            # PostgreSQL
            queries = [
                '''CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    full_name TEXT,
                    role TEXT DEFAULT 'موظف',
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT
                )''',
                
                '''CREATE TABLE IF NOT EXISTS items (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    purchase_price REAL NOT NULL,
                    min_selling_price REAL NOT NULL,
                    max_selling_price REAL NOT NULL,
                    avg_selling_price REAL NOT NULL,
                    current_price REAL NOT NULL,
                    quantity INTEGER NOT NULL
                )''',
                
                '''CREATE TABLE IF NOT EXISTS invoices (
                    id SERIAL PRIMARY KEY,
                    date TEXT NOT NULL,
                    item_id INTEGER,
                    quantity_sold INTEGER,
                    selling_price REAL,
                    total REAL
                )''',
                
                '''CREATE TABLE IF NOT EXISTS purchase_orders (
                    id SERIAL PRIMARY KEY,
                    item_name TEXT NOT NULL,
                    required_quantity INTEGER NOT NULL,
                    priority TEXT DEFAULT 'متوسط',
                    status TEXT DEFAULT 'مطلوب',
                    date_requested TEXT NOT NULL,
                    notes TEXT
                )''',
                
                '''CREATE TABLE IF NOT EXISTS returns_log (
                    id SERIAL PRIMARY KEY,
                    sale_id INTEGER,
                    item_name TEXT,
                    return_quantity INTEGER,
                    return_amount REAL,
                    reason TEXT,
                    return_date TEXT
                )''',
                
                '''CREATE TABLE IF NOT EXISTS permissions (
                    id SERIAL PRIMARY KEY,
                    role TEXT UNIQUE NOT NULL,
                    can_sales INTEGER DEFAULT 0,
                    can_add_items INTEGER DEFAULT 0,
                    can_edit_items INTEGER DEFAULT 0,
                    can_delete_items INTEGER DEFAULT 0,
                    can_inventory INTEGER DEFAULT 0,
                    can_shortages INTEGER DEFAULT 0,
                    can_reports INTEGER DEFAULT 0,
                    can_sales_list INTEGER DEFAULT 0,
                    can_returns INTEGER DEFAULT 0,
                    can_manage_users INTEGER DEFAULT 0,
                    can_view_logs INTEGER DEFAULT 0
                )''',
                
                '''CREATE TABLE IF NOT EXISTS activity_logs (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER,
                    username TEXT,
                    action TEXT NOT NULL,
                    details TEXT,
                    ip_address TEXT,
                    log_date TEXT NOT NULL
                )''',
            ]
            
            for query in queries:
                try:
                    execute_query(query)
                except Exception as e:
                    print(f"⚠️ خطأ: {e}")
            
            # إضافة المستخدم الافتراضي
            execute_query("INSERT INTO users (username, password, role, created_at) SELECT 'admin', 'admin123', 'مدير', '2024-01-01' WHERE NOT EXISTS (SELECT 1 FROM users WHERE username='admin')")
            
        else:
            # SQLite
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, full_name TEXT, role TEXT DEFAULT "موظف", is_active INTEGER DEFAULT 1, created_at TEXT)')
                conn.execute('CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, purchase_price REAL NOT NULL, min_selling_price REAL NOT NULL, max_selling_price REAL NOT NULL, avg_selling_price REAL NOT NULL, current_price REAL NOT NULL, quantity INTEGER NOT NULL)')
                conn.execute('CREATE TABLE IF NOT EXISTS invoices (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, item_id INTEGER, quantity_sold INTEGER, selling_price REAL, total REAL)')
                conn.execute('CREATE TABLE IF NOT EXISTS purchase_orders (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT NOT NULL, required_quantity INTEGER NOT NULL, priority TEXT DEFAULT "متوسط", status TEXT DEFAULT "مطلوب", date_requested TEXT NOT NULL, notes TEXT)')
                conn.execute('CREATE TABLE IF NOT EXISTS returns_log (id INTEGER PRIMARY KEY AUTOINCREMENT, sale_id INTEGER, item_name TEXT, return_quantity INTEGER, return_amount REAL, reason TEXT, return_date TEXT)')
                conn.execute('CREATE TABLE IF NOT EXISTS permissions (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT UNIQUE NOT NULL, can_sales INTEGER DEFAULT 0, can_add_items INTEGER DEFAULT 0, can_edit_items INTEGER DEFAULT 0, can_delete_items INTEGER DEFAULT 0, can_inventory INTEGER DEFAULT 0, can_shortages INTEGER DEFAULT 0, can_reports INTEGER DEFAULT 0, can_sales_list INTEGER DEFAULT 0, can_returns INTEGER DEFAULT 0, can_manage_users INTEGER DEFAULT 0, can_view_logs INTEGER DEFAULT 0)')
                conn.execute('CREATE TABLE IF NOT EXISTS activity_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, action TEXT NOT NULL, details TEXT, ip_address TEXT, log_date TEXT NOT NULL)')
                conn.execute("INSERT OR IGNORE INTO users (username, password, role, created_at) VALUES ('admin', 'admin123', 'مدير', '2024-01-01')")
                conn.commit()
        
        print("✅ قاعدة البيانات جاهزة!")
    except Exception as e:
        print(f"⚠️ خطأ في تهيئة قاعدة البيانات: {e}")
        traceback.print_exc()

# تشغيل التهيئة
init_db()

# ============================================================
# المسارات (Routes)
# ============================================================

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = execute_query('SELECT * FROM users WHERE username=? AND password=?', 
                            (username, password), fetch_one=True)
        if user:
            session['user'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='بيانات الدخول غير صحيحة')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    try:
        # حساب الإجماليات
        total_purchase = execute_query('SELECT COALESCE(SUM(purchase_price * quantity), 0) as total FROM items', fetch_one=True)
        total_selling = execute_query('SELECT COALESCE(SUM(current_price * quantity), 0) as total FROM items', fetch_one=True)
        
        total_purchase_val = total_purchase['total'] if total_purchase else 0
        total_selling_val = total_selling['total'] if total_selling else 0
        
        today = datetime.now().strftime('%Y-%m-%d')
        today_sales = execute_query('SELECT COALESCE(SUM(total), 0) as total FROM invoices WHERE date LIKE ?', 
                                   (today + '%',), fetch_one=True)
        today_sales_val = today_sales['total'] if today_sales else 0
        
        expected_profit = total_selling_val - total_purchase_val
        
        # إحصائيات التنبيهات
        critical_count = execute_query('SELECT COUNT(*) as count FROM items WHERE quantity <= 1', fetch_one=True)
        low_count = execute_query('SELECT COUNT(*) as count FROM items WHERE quantity BETWEEN 2 AND 5', fetch_one=True)
        
        critical_items_count = critical_count['count'] if critical_count else 0
        low_stock_count = low_count['count'] if low_count else 0
        
        return render_template('dashboard.html', 
                             total_purchase=total_purchase_val, 
                             total_selling=total_selling_val,
                             today_sales=today_sales_val, 
                             expected_profit=expected_profit,
                             critical_items_count=critical_items_count,
                             low_stock_count=low_stock_count)
    except Exception as e:
        print(f"⚠️ خطأ في dashboard: {e}")
        traceback.print_exc()
        return "حدث خطأ في النظام، يرجى المحاولة لاحقاً", 500

@app.route('/sales', methods=['GET', 'POST'])
def sales():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    items = execute_query('SELECT id, name, current_price, quantity FROM items WHERE quantity > 0', fetch_all=True)
    
    if request.method == 'POST':
        item_id = request.form['item_id']
        qty = int(request.form['quantity'])
        custom_price = float(request.form.get('custom_price', 0))
        
        item = execute_query('SELECT * FROM items WHERE id=?', (item_id,), fetch_one=True)
        if item and qty <= item['quantity']:
            price = custom_price if custom_price > 0 else item['current_price']
            total = price * qty
            
            execute_query('INSERT INTO invoices (date, item_id, quantity_sold, selling_price, total) VALUES (?,?,?,?,?)',
                       (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), item_id, qty, price, total))
            execute_query('UPDATE items SET quantity = quantity - ? WHERE id=?', (qty, item_id))
            return redirect(url_for('sales'))
    
    return render_template('sales.html', items=items)

@app.route('/inventory')
def inventory():
    if 'user' not in session:
        return redirect(url_for('login'))
    items = execute_query('SELECT * FROM items', fetch_all=True)
    return render_template('inventory.html', items=items)

@app.route('/shortages', methods=['GET', 'POST'])
def shortages():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        item_name = request.form['item_name']
        required_quantity = int(request.form['required_quantity'])
        priority = request.form['priority']
        notes = request.form.get('notes', '')
        
        execute_query('INSERT INTO purchase_orders (item_name, required_quantity, priority, status, date_requested, notes) VALUES (?,?,?,?,?,?)',
                   (item_name, required_quantity, priority, 'مطلوب', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), notes))
        return redirect(url_for('shortages'))
    
    orders = execute_query('SELECT * FROM purchase_orders ORDER BY date_requested DESC', fetch_all=True)
    low_stock_items = execute_query('SELECT * FROM items WHERE quantity < 5', fetch_all=True)
    
    return render_template('shortages.html', orders=orders, low_stock_items=low_stock_items)

@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if 'user' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        data = request.form
        execute_query('INSERT INTO items (name, purchase_price, min_selling_price, max_selling_price, avg_selling_price, current_price, quantity) VALUES (?,?,?,?,?,?,?)',
                   (data['name'], float(data['purchase_price']), float(data['min_price']),
                    float(data['max_price']), float(data['avg_price']), float(data['current_price']), int(data['quantity'])))
        return redirect(url_for('inventory'))
    return render_template('add_item.html')

@app.route('/search', methods=['GET', 'POST'])
def search():
    if 'user' not in session:
        return redirect(url_for('login'))
    result = []
    if request.method == 'POST':
        keyword = request.form['keyword']
        result = execute_query('SELECT * FROM items WHERE name LIKE ?', (f'%{keyword}%',), fetch_all=True)
    return render_template('search.html', result=result)

@app.route('/reports')
def reports():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    daily_sales = execute_query('SELECT date(date) as date, SUM(total) as daily_total FROM invoices GROUP BY date(date) ORDER BY date DESC LIMIT 30', fetch_all=True)
    monthly_total = execute_query('SELECT COALESCE(SUM(total), 0) as total FROM invoices', fetch_one=True)
    monthly_total_val = monthly_total['total'] if monthly_total else 0
    
    return render_template('reports.html', daily_sales=daily_sales, monthly_total=monthly_total_val)

@app.route('/sales_list')
def sales_list():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    sales = execute_query('SELECT invoices.*, items.name as item_name, items.purchase_price FROM invoices LEFT JOIN items ON invoices.item_id = items.id ORDER BY invoices.date DESC', fetch_all=True)
    return render_template('sales_list.html', sales=sales)

@app.route('/inventory_value')
def inventory_value():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    items = execute_query('SELECT * FROM items', fetch_all=True)
    
    total_by_min = 0
    total_by_avg = 0
    total_by_max = 0
    total_by_current = 0
    
    for item in items:
        qty = item['quantity']
        total_by_min += qty * item['min_selling_price']
        total_by_avg += qty * item['avg_selling_price']
        total_by_max += qty * item['max_selling_price']
        total_by_current += qty * item['current_price']
    
    return render_template('inventory_value.html',
                         items=items,
                         total_by_min=total_by_min,
                         total_by_avg=total_by_avg,
                         total_by_max=total_by_max,
                         total_by_current=total_by_current)

@app.route('/users', methods=['GET', 'POST'])
def manage_users():
    if 'user' not in session or session['user'] != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form.get('full_name', '')
        role = request.form['role']
        
        existing = execute_query('SELECT * FROM users WHERE username = ?', (username,), fetch_one=True)
        if existing:
            users = execute_query('SELECT * FROM users ORDER BY id', fetch_all=True)
            return render_template('users.html', error='اسم المستخدم موجود', users=users)
        
        execute_query('INSERT INTO users (username, password, full_name, role, is_active, created_at) VALUES (?,?,?,?,1,?)',
                     (username, password, full_name, role, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        return redirect(url_for('manage_users'))
    
    users = execute_query('SELECT * FROM users ORDER BY id', fetch_all=True)
    return render_template('users.html', users=users)

@app.route('/edit_user/<int:user_id>', methods=['POST'])
def edit_user(user_id):
    if 'user' not in session or session['user'] != 'admin':
        return redirect(url_for('dashboard'))
    
    role = request.form['role']
    is_active = 1 if request.form.get('is_active') else 0
    
    execute_query('UPDATE users SET role = ?, is_active = ? WHERE id = ?', (role, is_active, user_id))
    return redirect(url_for('manage_users'))

@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    if 'user' not in session or session['user'] != 'admin':
        return redirect(url_for('dashboard'))
    
    user = execute_query('SELECT username FROM users WHERE id = ?', (user_id,), fetch_one=True)
    if user and user['username'] != 'admin':
        execute_query('DELETE FROM users WHERE id = ?', (user_id,))
    
    return redirect(url_for('manage_users'))

@app.route('/activity_logs')
def activity_logs():
    if 'user' not in session or session['user'] != 'admin':
        return redirect(url_for('dashboard'))
    
    logs = execute_query('SELECT * FROM activity_logs ORDER BY log_date DESC LIMIT 200', fetch_all=True)
    return render_template('activity_logs.html', logs=logs)

@app.route('/delete_item/<int:item_id>')
def delete_item(item_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    execute_query('DELETE FROM items WHERE id = ?', (item_id,))
    return redirect(url_for('inventory'))

@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    item = execute_query('SELECT * FROM items WHERE id = ?', (item_id,), fetch_one=True)
    
    if request.method == 'POST':
        data = request.form
        execute_query('UPDATE items SET name=?, purchase_price=?, min_selling_price=?, max_selling_price=?, avg_selling_price=?, current_price=?, quantity=? WHERE id=?',
                   (data['name'], float(data['purchase_price']), float(data['min_price']),
                    float(data['max_price']), float(data['avg_price']), float(data['current_price']),
                    int(data['quantity']), item_id))
        return redirect(url_for('inventory'))
    
    return render_template('edit_item.html', item=item)

# ============================================================
# تشغيل التطبيق
# ============================================================
if __name__ == '__main__':
    print("=" * 50)
    print("🚀 تشغيل نظام إدارة محل ابن الشيخ")
    print("=" * 50)
    print("📱 افتح المتصفح على: http://127.0.0.1:5000")
    print("👤 اسم المستخدم: admin")
    print("🔑 كلمة المرور: admin123")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
