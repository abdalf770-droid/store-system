from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime
import sqlite3
import os
import shutil

app = Flask(__name__)
app.secret_key = 'ibn_al_shaykh_secret_key_2024'

DB_NAME = 'store.db'

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
        
        # جدول الفواتير
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
        
        # جدول النسخ الاحتياطية
        conn.execute('''
            CREATE TABLE IF NOT EXISTS backups_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_date TEXT NOT NULL,
                backup_type TEXT NOT NULL,
                file_path TEXT NOT NULL
            )
        ''')
        
        # جدول طلبات الشراء (النواقص)
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
        
        # إضافة مستخدم افتراضي
        conn.execute("INSERT OR IGNORE INTO users (username, password) VALUES ('admin', 'admin123')")
        
        ## تهيئة قاعدة البيانات
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

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    db = get_db()
    total_purchase = db.execute('SELECT COALESCE(SUM(purchase_price * quantity), 0) as total FROM items').fetchone()['total']
    total_selling = db.execute('SELECT COALESCE(SUM(current_price * quantity), 0) as total FROM items').fetchone()['total']
    today = datetime.now().strftime('%Y-%m-%d')
    today_sales = db.execute('SELECT COALESCE(SUM(total), 0) as total FROM invoices WHERE date LIKE ?', (today + '%',)).fetchone()['total']
    expected_profit = total_selling - total_purchase
    return render_template('dashboard.html', 
                         total_purchase=total_purchase, 
                         total_selling=total_selling,
                         today_sales=today_sales, 
                         expected_profit=expected_profit)

@app.route('/sales', methods=['GET', 'POST'])
def sales():
    if 'user' not in session:
        return redirect(url_for('login'))
    db = get_db()
    items = db.execute('SELECT id, name, current_price, quantity FROM items WHERE quantity > 0').fetchall()
    
    if request.method == 'POST':
        item_id = request.form['item_id']
        qty = int(request.form['quantity'])
        custom_price = float(request.form.get('custom_price', 0))
        
        item = db.execute('SELECT * FROM items WHERE id=?', (item_id,)).fetchone()
        if item and qty <= item['quantity']:
            price = custom_price if custom_price > 0 else item['current_price']
            total = price * qty
            
            db.execute('INSERT INTO invoices (date, item_id, quantity_sold, selling_price, total) VALUES (?,?,?,?,?)',
                       (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), item_id, qty, price, total))
            db.execute('UPDATE items SET quantity = quantity - ? WHERE id=?', (qty, item_id))
            db.commit()
            return redirect(url_for('sales'))
    
    return render_template('sales.html', items=items)

@app.route('/inventory')
def inventory():
    if 'user' not in session:
        return redirect(url_for('login'))
    db = get_db()
    items = db.execute('SELECT * FROM items').fetchall()
    return render_template('inventory.html', items=items)

@app.route('/shortages', methods=['GET', 'POST'])
def shortages():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    
    # إضافة طلب شراء جديد
    if request.method == 'POST':
        item_name = request.form['item_name']
        required_quantity = int(request.form['required_quantity'])
        priority = request.form['priority']
        notes = request.form.get('notes', '')
        
        db.execute('INSERT INTO purchase_orders (item_name, required_quantity, priority, status, date_requested, notes) VALUES (?, ?, ?, ?, ?, ?)',
                   (item_name, required_quantity, priority, 'مطلوب', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), notes))
        db.commit()
        return redirect(url_for('shortages'))
    
    # جلب جميع طلبات الشراء
    orders = db.execute('SELECT * FROM purchase_orders ORDER BY date_requested DESC').fetchall()
    
    # الأصناف منخفضة المخزون في المخزن (أقل من 5)
    low_stock_items = db.execute('SELECT * FROM items WHERE quantity < 5').fetchall()
    
    return render_template('shortages.html', orders=orders, low_stock_items=low_stock_items)

@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if 'user' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        data = request.form
        db = get_db()
        db.execute('INSERT INTO items (name, purchase_price, min_selling_price, max_selling_price, avg_selling_price, current_price, quantity) VALUES (?,?,?,?,?,?,?)',
                   (data['name'], float(data['purchase_price']), float(data['min_price']),
                    float(data['max_price']), float(data['avg_price']), float(data['current_price']), int(data['quantity'])))
        db.commit()
        return redirect(url_for('inventory'))
    return render_template('add_item.html')

@app.route('/search', methods=['GET', 'POST'])
def search():
    if 'user' not in session:
        return redirect(url_for('login'))
    result = []
    if request.method == 'POST':
        keyword = request.form['keyword']
        db = get_db()
        result = db.execute('SELECT * FROM items WHERE name LIKE ?', (f'%{keyword}%',)).fetchall()
    return render_template('search.html', result=result)

@app.route('/reports')
def reports():
    if 'user' not in session:
        return redirect(url_for('login'))
    db = get_db()
    daily_sales = db.execute('SELECT date(date) as date, SUM(total) as daily_total FROM invoices WHERE strftime("%Y-%m", date) = strftime("%Y-%m", "now") GROUP BY date(date) ORDER BY date DESC').fetchall()
    monthly_total = db.execute('SELECT COALESCE(SUM(total), 0) as total FROM invoices WHERE strftime("%Y-%m", date) = strftime("%Y-%m", "now")').fetchone()['total']
    return render_template('reports.html', daily_sales=daily_sales, monthly_total=monthly_total)

@app.route('/backup')
def backup():
    if 'user' not in session:
        return redirect(url_for('login'))
    backup_dir = 'backups'
    os.makedirs(backup_dir, exist_ok=True)
    backup_file = f"{backup_dir}/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy(DB_NAME, backup_file)
    db = get_db()
    db.execute('INSERT INTO backups_log (backup_date, backup_type, file_path) VALUES (?,?,?)',
               (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'manual', backup_file))
    db.commit()
    return jsonify({'message': f'تم إنشاء النسخة الاحتياطية: {backup_file}'})

@app.route('/get_items_json')
def get_items_json():
    db = get_db()
    items = db.execute('SELECT id, name, current_price, quantity FROM items WHERE quantity > 0').fetchall()
    return jsonify([dict(item) for item in items])

@app.route('/update_item/<int:item_id>', methods=['POST'])
def update_item(item_id):
    data = request.json
    db = get_db()
    if data.get('price'):
        db.execute('UPDATE items SET current_price = ? WHERE id = ?', (float(data['price']), item_id))
    if data.get('quantity'):
        db.execute('UPDATE items SET quantity = ? WHERE id = ?', (int(data['quantity']), item_id))
    db.commit()
    return jsonify({'status': 'ok'})

@app.route('/update_order_status/<int:order_id>')
def update_order_status(order_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    db.execute('UPDATE purchase_orders SET status = "تم الشراء" WHERE id = ?', (order_id,))
    db.commit()
    return redirect(url_for('shortages'))

@app.route('/delete_order/<int:order_id>')
def delete_order(order_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    db.execute('DELETE FROM purchase_orders WHERE id = ?', (order_id,))
    db.commit()
    return redirect(url_for('shortages'))
@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    item = db.execute('SELECT * FROM items WHERE id = ?', (item_id,)).fetchone()
    
    if request.method == 'POST':
        data = request.form
        db.execute('''UPDATE items SET 
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
        db.commit()
        return redirect(url_for('inventory'))
    
    return render_template('edit_item.html', item=item)
@app.route('/sales_list')
def sales_list():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    # جلب جميع فواتير البيع مع اسم المنتج وسعر الشراء وحساب الربح
    sales = db.execute('''
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
    ''').fetchall()
    
    return render_template('sales_list.html', sales=sales)

@app.route('/edit_sale/<int:sale_id>', methods=['GET', 'POST'])
def edit_sale(sale_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    
    if request.method == 'POST':
        new_quantity = int(request.form['quantity'])
        new_price = float(request.form['price'])
        sale = db.execute('SELECT * FROM invoices WHERE id = ?', (sale_id,)).fetchone()
        
        if sale:
            # حساب الفرق في الكمية لإعادة المخزون
            old_quantity = sale['quantity_sold']
            old_total = sale['total']
            new_total = new_price * new_quantity
            
            # تحديث المخزون: نعيد الكمية القديمة ثم نخصم الجديدة
            db.execute('UPDATE items SET quantity = quantity + ? WHERE id = ?', (old_quantity, sale['item_id']))
            db.execute('UPDATE items SET quantity = quantity - ? WHERE id = ?', (new_quantity, sale['item_id']))
            
            # تحديث الفاتورة
            db.execute('''
                UPDATE invoices SET quantity_sold = ?, selling_price = ?, total = ? 
                WHERE id = ?
            ''', (new_quantity, new_price, new_total, sale_id))
            db.commit()
        
        return redirect(url_for('sales_list'))
    
    sale = db.execute('''
        SELECT invoices.*, items.name as item_name, items.current_price, items.quantity as available_qty
        FROM invoices 
        LEFT JOIN items ON invoices.item_id = items.id 
        WHERE invoices.id = ?
    ''', (sale_id,)).fetchone()
    
    return render_template('edit_sale.html', sale=sale)

@app.route('/delete_sale/<int:sale_id>')
def delete_sale(sale_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    sale = db.execute('SELECT * FROM invoices WHERE id = ?', (sale_id,)).fetchone()
    
    if sale:
        # إعادة الكمية إلى المخزون
        db.execute('UPDATE items SET quantity = quantity + ? WHERE id = ?', (sale['quantity_sold'], sale['item_id']))
        db.execute('DELETE FROM invoices WHERE id = ?', (sale_id,))
        db.commit()
    
    return redirect(url_for('sales_list'))

@app.route('/return_sale/<int:sale_id>', methods=['GET', 'POST'])
def return_sale(sale_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    sale = db.execute('''
        SELECT invoices.*, items.name as item_name 
        FROM invoices 
        LEFT JOIN items ON invoices.item_id = items.id 
        WHERE invoices.id = ?
    ''', (sale_id,)).fetchone()
    
    if request.method == 'POST':
        return_quantity = int(request.form['return_quantity'])
        reason = request.form['reason']
        
        if return_quantity <= sale['quantity_sold']:
            # إعادة الكمية المرتجعة إلى المخزون
            db.execute('UPDATE items SET quantity = quantity + ? WHERE id = ?', (return_quantity, sale['item_id']))
            
            # تسجيل المرتجع في جدول المرتجعات
            db.execute('''
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
            
            return_amount = return_quantity * sale['selling_price']
            db.execute('''
                INSERT INTO returns_log (sale_id, item_name, return_quantity, return_amount, reason, return_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (sale_id, sale['item_name'], return_quantity, return_amount, reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            # تحديث الفاتورة الأصلية (تقليل الكمية أو حذفها)
            new_quantity = sale['quantity_sold'] - return_quantity
            if new_quantity > 0:
                new_total = new_quantity * sale['selling_price']
                db.execute('UPDATE invoices SET quantity_sold = ?, total = ? WHERE id = ?', (new_quantity, new_total, sale_id))
            else:
                db.execute('DELETE FROM invoices WHERE id = ?', (sale_id,))
            
            db.commit()
            return redirect(url_for('sales_list'))
    
    return render_template('return_sale.html', sale=sale)

@app.route('/returns_report')
def returns_report():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    
    # إنشاء جدول المرتجعات إذا لم يكن موجوداً
    db.execute('''
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
    
    returns = db.execute('SELECT * FROM returns_log ORDER BY return_date DESC').fetchall()
    total_returns = db.execute('SELECT COALESCE(SUM(return_amount), 0) as total FROM returns_log').fetchone()['total']
    
    return render_template('returns_report.html', returns=returns, total_returns=total_returns)
@app.route('/delete_item/<int:item_id>')
def delete_item(item_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    db.execute('DELETE FROM items WHERE id = ?', (item_id,))
    db.commit()
    return redirect(url_for('inventory'))
if __name__ == '__main__':
    print("=" * 50)
    print("🚀 تشغيل نظام إدارة محل بن الشيخ ")
    print("=" * 50)
    print("📱 افتح المتصفح على: http://127.0.0.1:5000")
    print("👤 اسم المستخدم: admin")
    print("🔑 كلمة المرور: admin123")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)