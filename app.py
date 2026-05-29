from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g
from datetime import datetime
import sqlite3
import os
import shutil
import urllib.parse as urlparse

app = Flask(__name__)
app.secret_key = 'ibn_al_shaykh_secret_key_2024'

DB_NAME = 'store.db'

# ============================================================
# إعدادات قاعدة البيانات (تدعم SQLite و PostgreSQL)
# ============================================================

def get_db():
    """إرجاع اتصال بقاعدة البيانات (SQLite محلياً أو PostgreSQL على Render)"""
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
                g.db_cursor = g.db.cursor(cursor_factory=RealDictCursor)
            except ImportError:
                print("⚠️ psycopg2 غير مثبت، يرجى تشغيل: pip install psycopg2-binary")
                raise
        return g.db
    else:
        # استخدام SQLite محلياً
        if 'db' not in g:
            g.db = sqlite3.connect(DB_NAME)
            g.db.row_factory = sqlite3.Row
        return g.db

def get_cursor():
    """إرجاع مؤشر cursor مناسب لنوع قاعدة البيانات"""
    DATABASE_URL = os.environ.get('DATABASE_URL')
    db = get_db()
    
    if DATABASE_URL:
        return g.db_cursor
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
            if DATABASE_URL:
                result = cursor.fetchone()
                if result:
                    result = dict(result)
            else:
                result = cursor.fetchone()
            db.commit()
            return result
        elif fetch_all:
            if DATABASE_URL:
                results = cursor.fetchall()
                results = [dict(row) for row in results]
            else:
                results = cursor.fetchall()
            db.commit()
            return results
        else:
            db.commit()
            return cursor
    except Exception as e:
        db.rollback()
        print(f"⚠️ خطأ في الاستعلام: {e}")
        raise e

def init_db():
    """تهيئة قاعدة البيانات (جداول ومستخدم افتراضي)"""
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if DATABASE_URL:
        # PostgreSQL - إنشاء الجداول
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
                total REAL,
                FOREIGN KEY (item_id) REFERENCES items (id)
            )''',
            
            '''CREATE TABLE IF NOT EXISTS backups_log (
                id SERIAL PRIMARY KEY,
                backup_date TEXT NOT NULL,
                backup_type TEXT NOT NULL,
                file_path TEXT NOT NULL
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
            
            """INSERT INTO permissions (role, can_sales, can_add_items, can_edit_items, can_delete_items, can_inventory, can_shortages, can_reports, can_sales_list, can_returns, can_manage_users, can_view_logs) 
               VALUES ('مدير', 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1) 
               ON CONFLICT (role) DO NOTHING""",
            
            """INSERT INTO permissions (role, can_sales, can_add_items, can_edit_items, can_delete_items, can_inventory, can_shortages, can_reports, can_sales_list, can_returns, can_manage_users, can_view_logs) 
               VALUES ('موظف', 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0) 
               ON CONFLICT (role) DO NOTHING""",
            
            """INSERT INTO permissions (role, can_sales, can_add_items, can_edit_items, can_delete_items, can_inventory, can_shortages, can_reports, can_sales_list, can_returns, can_manage_users, can_view_logs) 
               VALUES ('مراقب', 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0) 
               ON CONFLICT (role) DO NOTHING""",
            
            "INSERT INTO users (username, password, role, created_at) SELECT 'admin', 'admin123', 'مدير', '2024-01-01' WHERE NOT EXISTS (SELECT 1 FROM users WHERE username='admin')"
        ]
        
        for query in queries:
            try:
                execute_query(query)
            except Exception as e:
                print(f"⚠️ خطأ في إنشاء الجدول: {e}")
    else:
        # SQLite - إنشاء الجداول
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    full_name TEXT,
                    role TEXT DEFAULT 'موظف',
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT
                )
            ''')
            
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
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS backups_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    backup_date TEXT NOT NULL,
                    backup_type TEXT NOT NULL,
                    file_path TEXT NOT NULL
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS purchase_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_name TEXT NOT NULL,
                    required_quantity INTEGER NOT NULL,
                    priority TEXT DEFAULT 'متوسط',
                    status TEXT DEFAULT 'مطلوب',
                    date_requested TEXT NOT NULL,
                    notes TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS returns_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sale_id INTEGER,
                    item_name TEXT,
                    return_quantity INTEGER,
                    return_amount REAL,
                    reason TEXT,
                    return_date TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    action TEXT NOT NULL,
                    details TEXT,
                    ip_address TEXT,
                    log_date TEXT NOT NULL
                )
            ''')
            
            conn.execute("INSERT OR IGNORE INTO permissions (role, can_sales, can_add_items, can_edit_items, can_delete_items, can_inventory, can_shortages, can_reports, can_sales_list, can_returns, can_manage_users, can_view_logs) VALUES ('مدير', 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1)")
            conn.execute("INSERT OR IGNORE INTO permissions (role, can_sales, can_add_items, can_edit_items, can_delete_items, can_inventory, can_shortages, can_reports, can_sales_list, can_returns, can_manage_users, can_view_logs) VALUES ('موظف', 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0)")
            conn.execute("INSERT OR IGNORE INTO permissions (role, can_sales, can_add_items, can_edit_items, can_delete_items, can_inventory, can_shortages, can_reports, can_sales_list, can_returns, can_manage_users, can_view_logs) VALUES ('مراقب', 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0)")
            
            conn.execute("INSERT OR IGNORE INTO users (username, password, role, created_at) VALUES ('admin', 'admin123', 'مدير', '2024-01-01')")
            conn.commit()
    
    print("✅ قاعدة البيانات جاهزة!")

@app.teardown_appcontext
def close_db(error=None):
    """إغلاق اتصال قاعدة البيانات بعد كل طلب"""
    if 'db' in g:
        if os.environ.get('DATABASE_URL'):
            if hasattr(g, 'db_cursor'):
                g.db_cursor.close()
        g.db.close()

# ============================================================
# تهيئة قاعدة البيانات عند بدء التشغيل
# ============================================================
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
    
    total_purchase = execute_query('SELECT COALESCE(SUM(purchase_price * quantity), 0) as total FROM items', fetch_one=True)['total']
    total_selling = execute_query('SELECT COALESCE(SUM(current_price * quantity), 0) as total FROM items', fetch_one=True)['total']
    today = datetime.now().strftime('%Y-%m-%d')
    today_sales = execute_query('SELECT COALESCE(SUM(total), 0) as total FROM invoices WHERE date LIKE ?', 
                               (today + '%',), fetch_one=True)['total']
    expected_profit = total_selling - total_purchase
    
    critical_items_count = execute_query('SELECT COUNT(*) as count FROM items WHERE quantity <= 1', fetch_one=True)['count']
    low_stock_count = execute_query('SELECT COUNT(*) as count FROM items WHERE quantity BETWEEN 2 AND 5', fetch_one=True)['count']
    
    return render_template('dashboard.html', 
                         total_purchase=total_purchase, 
                         total_selling=total_selling,
                         today_sales=today_sales, 
                         expected_profit=expected_profit,
                         critical_items_count=critical_items_count,
                         low_stock_count=low_stock_count)

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

@app.route('/low_stock_alert')
def low_stock_alert():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    critical_items = execute_query('SELECT * FROM items WHERE quantity <= 1 ORDER BY quantity ASC', fetch_all=True)
    low_items = execute_query('SELECT * FROM items WHERE quantity BETWEEN 2 AND 4 ORDER BY quantity ASC', fetch_all=True)
    
    return render_template('low_stock_alert.html', 
                         critical_items=critical_items, 
                         low_items=low_items)

@app.route('/dashboard_stats')
def dashboard_stats():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    today = datetime.now().strftime('%Y-%m-%d')
    today_sales_count = execute_query('SELECT COUNT(*) as count FROM invoices WHERE date LIKE ?', 
                                      (today + '%',), fetch_one=True)['count']
    today_items_sold = execute_query('SELECT COALESCE(SUM(quantity_sold), 0) as total FROM invoices WHERE date LIKE ?',
                                     (today + '%',), fetch_one=True)['total']
    today_revenue = execute_query('SELECT COALESCE(SUM(total), 0) as total FROM invoices WHERE date LIKE ?',
                                  (today + '%',), fetch_one=True)['total']
    
    weekly_activity = execute_query('''
        SELECT DATE(date) as day, COUNT(*) as invoices, SUM(total) as revenue
        FROM invoices 
        WHERE date >= DATE('now', '-7 days')
        GROUP BY DATE(date)
        ORDER BY day DESC
    ''', fetch_all=True)
    
    top_items = execute_query('''
        SELECT 
            items.name,
            SUM(invoices.quantity_sold) as total_sold,
            COUNT(invoices.id) as times_sold,
            SUM(invoices.total) as revenue,
            items.current_price,
            items.quantity as current_stock
        FROM invoices 
        LEFT JOIN items ON invoices.item_id = items.id 
        GROUP BY items.id
        ORDER BY total_sold DESC
        LIMIT 10
    ''', fetch_all=True)
    
    stock_ranking = execute_query('''
        SELECT 
            name,
            quantity,
            current_price,
            purchase_price,
            CASE 
                WHEN quantity = 0 THEN 'نفد بالكامل'
                WHEN quantity <= 2 THEN 'حرج جداً'
                WHEN quantity <= 5 THEN 'منخفض'
                WHEN quantity <= 10 THEN 'جيد'
                ELSE 'ممتاز'
            END as stock_status
        FROM items 
        ORDER BY quantity ASC
    ''', fetch_all=True)
    
    total_items = execute_query('SELECT COUNT(*) as count FROM items', fetch_one=True)['count']
    out_of_stock = execute_query('SELECT COUNT(*) as count FROM items WHERE quantity = 0', fetch_one=True)['count']
    low_stock = execute_query('SELECT COUNT(*) as count FROM items WHERE quantity BETWEEN 1 AND 5', fetch_one=True)['count']
    
    return render_template('dashboard_stats.html',
                         today_sales_count=today_sales_count,
                         today_items_sold=today_items_sold,
                         today_revenue=today_revenue,
                         weekly_activity=weekly_activity,
                         top_items=top_items,
                         stock_ranking=stock_ranking,
                         total_items=total_items,
                         out_of_stock=out_of_stock,
                         low_stock=low_stock)

@app.route('/shortages', methods=['GET', 'POST'])
def shortages():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        item_name = request.form['item_name']
        required_quantity = int(request.form['required_quantity'])
        priority = request.form['priority']
        notes = request.form.get('notes', '')
        
        execute_query('''INSERT INTO purchase_orders (item_name, required_quantity, priority, status, date_requested, notes) 
                       VALUES (?, ?, ?, ?, ?, ?)''',
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
        execute_query('''INSERT INTO items (name, purchase_price, min_selling_price, max_selling_price, avg_selling_price, current_price, quantity) 
                       VALUES (?,?,?,?,?,?,?)''',
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
    
    if os.environ.get('DATABASE_URL'):
        daily_sales = execute_query('''SELECT DATE(date) as date, SUM(total) as daily_total FROM invoices 
                                      WHERE EXTRACT(YEAR_MONTH FROM date) = EXTRACT(YEAR_MONTH FROM NOW())
                                      GROUP BY DATE(date) ORDER BY date DESC''', fetch_all=True)
        monthly_total = execute_query('SELECT COALESCE(SUM(total), 0) as total FROM invoices WHERE EXTRACT(YEAR_MONTH FROM date) = EXTRACT(YEAR_MONTH FROM NOW())', 
                                     fetch_one=True)['total']
    else:
        daily_sales = execute_query('''SELECT date(date) as date, SUM(total) as daily_total FROM invoices 
                                      WHERE strftime("%Y-%m", date) = strftime("%Y-%m", "now") 
                                      GROUP BY date(date) ORDER BY date DESC''', fetch_all=True)
        monthly_total = execute_query('SELECT COALESCE(SUM(total), 0) as total FROM invoices WHERE strftime("%Y-%m", date) = strftime("%Y-%m", "now")', 
                                     fetch_one=True)['total']
    
    return render_template('reports.html', daily_sales=daily_sales, monthly_total=monthly_total)

@app.route('/backup')
def backup():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if os.environ.get('DATABASE_URL'):
        return jsonify({'message': '⚠️ النسخ الاحتياطي متاح فقط في النسخة المحلية (SQLite)'})
    
    backup_dir = 'backups'
    os.makedirs(backup_dir, exist_ok=True)
    backup_file = f"{backup_dir}/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy(DB_NAME, backup_file)
    execute_query('INSERT INTO backups_log (backup_date, backup_type, file_path) VALUES (?,?,?)',
               (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'manual', backup_file))
    return jsonify({'message': f'تم إنشاء النسخة الاحتياطية: {backup_file}'})

@app.route('/get_items_json')
def get_items_json():
    items = execute_query('SELECT id, name, current_price, quantity FROM items WHERE quantity > 0', fetch_all=True)
    return jsonify(items)

@app.route('/update_item/<int:item_id>', methods=['POST'])
def update_item(item_id):
    data = request.json
    if data.get('price'):
        execute_query('UPDATE items SET current_price = ? WHERE id = ?', (float(data['price']), item_id))
    if data.get('quantity'):
        execute_query('UPDATE items SET quantity = ? WHERE id = ?', (int(data['quantity']), item_id))
    return jsonify({'status': 'ok'})

@app.route('/update_order_status/<int:order_id>')
def update_order_status(order_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    execute_query('UPDATE purchase_orders SET status = "تم الشراء" WHERE id = ?', (order_id,))
    return redirect(url_for('shortages'))

@app.route('/delete_order/<int:order_id>')
def delete_order(order_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    execute_query('DELETE FROM purchase_orders WHERE id = ?', (order_id,))
    return redirect(url_for('shortages'))

@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    item = execute_query('SELECT * FROM items WHERE id = ?', (item_id,), fetch_one=True)
    
    if request.method == 'POST':
        data = request.form
        execute_query('''UPDATE items SET 
                     name = ?,
                     purchase_price = ?,
                     min_selling_price = ?,
                     max_selling_price = ?,
                     avg_selling_price = ?,
                     current_price = ?,
                     quantity = ?
                     WHERE id = ?''',
                   (data['name'], float(data['purchase_price']), float(data['min_price']),
                    float(data['max_price']), float(data['avg_price']), float(data['current_price']),
                    int(data['quantity']), item_id))
        return redirect(url_for('inventory'))
    
    return render_template('edit_item.html', item=item)

@app.route('/sales_list')
def sales_list():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    sales = execute_query('''
        SELECT 
            invoices.*, 
            items.name as item_name,
            items.purchase_price,
            (invoices.quantity_sold * items.purchase_price) as total_cost,
            (invoices.total - (invoices.quantity_sold * items.purchase_price)) as profit,
            CASE 
                WHEN (invoices.quantity_sold * items.purchase_price) > 0 
                THEN ((invoices.total - (invoices.quantity_sold * items.purchase_price)) * 100.0 / (invoices.quantity_sold * items.purchase_price))
                ELSE 0 
            END as profit_percent
        FROM invoices 
        LEFT JOIN items ON invoices.item_id = items.id 
        ORDER BY invoices.date DESC
    ''', fetch_all=True)
    
    return render_template('sales_list.html', sales=sales)

@app.route('/edit_sale/<int:sale_id>', methods=['GET', 'POST'])
def edit_sale(sale_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        new_quantity = int(request.form['quantity'])
        new_price = float(request.form['price'])
        sale = execute_query('SELECT * FROM invoices WHERE id = ?', (sale_id,), fetch_one=True)
        
        if sale:
            old_quantity = sale['quantity_sold']
            new_total = new_price * new_quantity
            
            execute_query('UPDATE items SET quantity = quantity + ? WHERE id = ?', (old_quantity, sale['item_id']))
            execute_query('UPDATE items SET quantity = quantity - ? WHERE id = ?', (new_quantity, sale['item_id']))
            execute_query('UPDATE invoices SET quantity_sold = ?, selling_price = ?, total = ? WHERE id = ?',
                       (new_quantity, new_price, new_total, sale_id))
        
        return redirect(url_for('sales_list'))
    
    sale = execute_query('''
        SELECT invoices.*, items.name as item_name, items.current_price, items.quantity as available_qty
        FROM invoices 
        LEFT JOIN items ON invoices.item_id = items.id 
        WHERE invoices.id = ?
    ''', (sale_id,), fetch_one=True)
    
    return render_template('edit_sale.html', sale=sale)

@app.route('/delete_sale/<int:sale_id>')
def delete_sale(sale_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    sale = execute_query('SELECT * FROM invoices WHERE id = ?', (sale_id,), fetch_one=True)
    
    if sale:
        execute_query('UPDATE items SET quantity = quantity + ? WHERE id = ?', (sale['quantity_sold'], sale['item_id']))
        execute_query('DELETE FROM invoices WHERE id = ?', (sale_id,))
    
    return redirect(url_for('sales_list'))

@app.route('/return_sale/<int:sale_id>', methods=['GET', 'POST'])
def return_sale(sale_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    sale = execute_query('''
        SELECT invoices.*, items.name as item_name 
        FROM invoices 
        LEFT JOIN items ON invoices.item_id = items.id 
        WHERE invoices.id = ?
    ''', (sale_id,), fetch_one=True)
    
    if request.method == 'POST':
        return_quantity = int(request.form['return_quantity'])
        reason = request.form['reason']
        
        if return_quantity <= sale['quantity_sold']:
            execute_query('UPDATE items SET quantity = quantity + ? WHERE id = ?', (return_quantity, sale['item_id']))
            
            return_amount = return_quantity * sale['selling_price']
            execute_query('''
                INSERT INTO returns_log (sale_id, item_name, return_quantity, return_amount, reason, return_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (sale_id, sale['item_name'], return_quantity, return_amount, reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            new_quantity = sale['quantity_sold'] - return_quantity
            if new_quantity > 0:
                new_total = new_quantity * sale['selling_price']
                execute_query('UPDATE invoices SET quantity_sold = ?, total = ? WHERE id = ?', (new_quantity, new_total, sale_id))
            else:
                execute_query('DELETE FROM invoices WHERE id = ?', (sale_id,))
            
            return redirect(url_for('sales_list'))
    
    return render_template('return_sale.html', sale=sale)

@app.route('/returns_report')
def returns_report():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    returns = execute_query('SELECT * FROM returns_log ORDER BY return_date DESC', fetch_all=True)
    total_returns = execute_query('SELECT COALESCE(SUM(return_amount), 0) as total FROM returns_log', fetch_one=True)['total']
    
    return render_template('returns_report.html', returns=returns, total_returns=total_returns)

@app.route('/delete_item/<int:item_id>')
def delete_item(item_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    execute_query('DELETE FROM items WHERE id = ?', (item_id,))
    return redirect(url_for('inventory'))

# ============================================================
# إدارة المستخدمين والصلاحيات
# ============================================================

@app.route('/users', methods=['GET', 'POST'])
def manage_users():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if session['user'] != 'admin':
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form.get('full_name', '')
        role = request.form['role']
        
        existing = execute_query('SELECT * FROM users WHERE username = ?', (username,), fetch_one=True)
        if existing:
            users = execute_query('SELECT * FROM users ORDER BY id', fetch_all=True)
            return render_template('users.html', error='اسم المستخدم موجود مسبقاً', users=users)
        
        execute_query('''
            INSERT INTO users (username, password, full_name, role, is_active, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
        ''', (username, password, full_name, role, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
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

@app.route('/inventory_value')
def inventory_value():
    """عرض قيمة البضاعة بثلاثة أسعار مختلفة"""
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
    
    diff_min_current = total_by_current - total_by_min
    diff_avg_current = total_by_current - total_by_avg
    diff_max_current = total_by_max - total_by_current
    
    return render_template('inventory_value.html',
                         items=items,
                         total_by_min=total_by_min,
                         total_by_avg=total_by_avg,
                         total_by_max=total_by_max,
                         total_by_current=total_by_current,
                         diff_min_current=diff_min_current,
                         diff_avg_current=diff_avg_current,
                         diff_max_current=diff_max_current)

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 تشغيل نظام إدارة محل ابن الشيخ شتيه")
    print("=" * 50)
    print("📱 افتح المتصفح على: http://127.0.0.1:5000")
    print("👤 اسم المستخدم: admin")
    print("🔑 كلمة المرور: admin123")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
