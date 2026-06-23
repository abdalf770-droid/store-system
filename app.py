from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g
from datetime import datetime
import os
import urllib.parse as urlparse
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = 'ibn_al_shaykh_secret_key_2024'

# ============================================================
# إعدادات قاعدة البيانات PostgreSQL
# ============================================================

# رابط قاعدة البيانات الذي أعطيتني إياه
DATABASE_URL = "postgresql://neondb_owner:npg_vfJNHbol5Z2k@ep-raspy-block-adco8epn-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

def get_db():
    """إرجاع اتصال بقاعدة البيانات PostgreSQL"""
    if 'db' not in g:
        try:
            # تحليل رابط قاعدة البيانات
            urlparse.uses_netloc.append("postgresql")
            url = urlparse.urlparse(DATABASE_URL)
            
            # الاتصال بقاعدة البيانات مع SSL
            g.db = psycopg2.connect(
                database=url.path[1:],
                user=url.username,
                password=url.password,
                host=url.hostname,
                port=url.port or 5432,
                sslmode='require'
            )
            g.cursor = g.db.cursor(cursor_factory=RealDictCursor)
            print("✅ تم الاتصال بقاعدة البيانات PostgreSQL بنجاح!")
        except Exception as e:
            print(f"❌ خطأ في الاتصال بقاعدة البيانات: {e}")
            raise
    return g.db

def get_cursor():
    """إرجاع المؤشر للتعامل مع قاعدة البيانات"""
    get_db()
    return g.cursor

def execute_query(query, params=None, fetch_one=False, fetch_all=False, commit=True):
    """تنفيذ استعلام على قاعدة البيانات PostgreSQL"""
    db = get_db()
    cursor = get_cursor()
    
    try:
        # تنفيذ الاستعلام
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        # جلب النتائج إذا لزم الأمر
        if fetch_one:
            result = cursor.fetchone()
            return dict(result) if result else None
        elif fetch_all:
            results = cursor.fetchall()
            return [dict(row) for row in results] if results else []
        elif commit:
            db.commit()
            return cursor
        else:
            return cursor
            
    except Exception as e:
        db.rollback()
        print(f"⚠️ خطأ في الاستعلام: {e}")
        print(f"⚠️ الاستعلام: {query}")
        print(f"⚠️ المعاملات: {params}")
        raise e

def init_db():
    """تهيئة قاعدة البيانات - إنشاء جميع الجداول إذا لم تكن موجودة"""
    db = get_db()
    cursor = get_cursor()
    
    # إنشاء جدول المستخدمين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # إنشاء جدول الأصناف
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            purchase_price REAL NOT NULL,
            min_selling_price REAL NOT NULL,
            max_selling_price REAL NOT NULL,
            avg_selling_price REAL NOT NULL,
            current_price REAL NOT NULL,
            quantity INTEGER NOT NULL
        )
    ''')
    
    # إنشاء جدول الفواتير
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id SERIAL PRIMARY KEY,
            date TEXT NOT NULL,
            item_id INTEGER,
            quantity_sold INTEGER,
            selling_price REAL,
            total REAL,
            FOREIGN KEY (item_id) REFERENCES items (id) ON DELETE SET NULL
        )
    ''')
    
    # إنشاء جدول سجل النسخ الاحتياطي
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS backups_log (
            id SERIAL PRIMARY KEY,
            backup_date TEXT NOT NULL,
            backup_type TEXT NOT NULL,
            file_path TEXT NOT NULL
        )
    ''')
    
    # إنشاء جدول أوامر الشراء
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchase_orders (
            id SERIAL PRIMARY KEY,
            item_name TEXT NOT NULL,
            required_quantity INTEGER NOT NULL,
            priority TEXT DEFAULT 'متوسط',
            status TEXT DEFAULT 'مطلوب',
            date_requested TEXT NOT NULL,
            notes TEXT
        )
    ''')
    
    # إنشاء جدول سجل المرتجعات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS returns_log (
            id SERIAL PRIMARY KEY,
            sale_id INTEGER,
            item_name TEXT,
            return_quantity INTEGER,
            return_amount REAL,
            reason TEXT,
            return_date TEXT
        )
    ''')
    
    # إضافة المستخدم الافتراضي إذا لم يكن موجوداً
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    admin_exists = cursor.fetchone()
    
    if not admin_exists:
        cursor.execute("INSERT INTO users (username, password) VALUES ('admin', 'admin123')")
    
    db.commit()
    print("✅ تم تهيئة قاعدة البيانات وجميع الجداول بنجاح!")

@app.teardown_appcontext
def close_db(error=None):
    """إغلاق اتصال قاعدة البيانات بعد كل طلب"""
    if 'db' in g:
        if hasattr(g, 'cursor'):
            g.cursor.close()
        g.db.close()
        print("🔌 تم إغلاق اتصال قاعدة البيانات")

# ============================================================
# تهيئة قاعدة البيانات عند بدء التشغيل
# ============================================================
with app.app_context():
    init_db()

# ============================================================
# المسارات (Routes)
# ============================================================
@app.route('/service-worker.js')
def service_worker():
    return app.send_static_file('service-worker.js') # أو اسم الملف مباشرة
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = execute_query(
            'SELECT * FROM users WHERE username = %s AND password = %s', 
            (username, password), 
            fetch_one=True
        )
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
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 1. نظام التنبيه الذكي لمخصص الديون اليومي (الـ 1000 ريال)
    today_debt_check = execute_query('''
        SELECT COUNT(*) as count FROM cash_flow 
        WHERE category = 'سداد ديون' AND COALESCE(date, '') LIKE %s
    ''', (today + '%',), fetch_one=True)['count']
    
    alert_debt = True if today_debt_check == 0 else False
    
    # الإحصائيات المالية للمخزن والمبيعات
    total_purchase = execute_query('SELECT COALESCE(SUM(purchase_price * quantity), 0) as total FROM items', fetch_one=True)['total']
    total_selling = execute_query('SELECT COALESCE(SUM(current_price * quantity), 0) as total FROM items', fetch_one=True)['total']
    
    today_sales = execute_query('SELECT COALESCE(SUM(total), 0) as total FROM invoices WHERE date LIKE %s', 
                               (today + '%',), fetch_one=True)['total']
    expected_profit = total_selling - total_purchase
    
    # إحصائيات التنبيهات للنواقص
    critical_items_count = execute_query('SELECT COUNT(*) as count FROM items WHERE quantity <= 1', fetch_one=True)['count']
    low_stock_count = execute_query('SELECT COUNT(*) as count FROM items WHERE quantity BETWEEN 2 AND 5', fetch_one=True)['count']
    
    items = execute_query('SELECT * FROM items ORDER BY id', fetch_all=True)
    
    return render_template('dashboard.html', 
                         items=items,
                         total_purchase=total_purchase, 
                         total_selling=total_selling,
                         today_sales=today_sales, 
                         expected_profit=expected_profit,
                         critical_items_count=critical_items_count,
                         low_stock_count=low_stock_count,
                         alert_debt=alert_debt) # إرسال التنبيه للرئيسية

@app.route('/sales', methods=['GET', 'POST'])
def sales():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    items = execute_query('SELECT id, name, current_price, quantity FROM items WHERE quantity > 0', fetch_all=True)
    
    if request.method == 'POST':
        item_id = request.form['item_id']
        qty = int(request.form['quantity'])
        custom_price_form = request.form.get('custom_price', '0')
        
        # تحويل آمن للسعر المخصص ليتجنب النصوص الفارغة
        custom_price = float(custom_price_form) if str(custom_price_form).strip() else 0.0
        
        item = execute_query('SELECT * FROM items WHERE id = %s', (item_id,), fetch_one=True)
        if item and qty <= item['quantity']:
            default_price = item['current_price']
            
            # السعر الفعلي للبيع: المخصص إن وجد، وإلا الافتراضي
            price = custom_price if custom_price > 0 else default_price
            
            # احتساب الإجمالي الافتراضي والبيع الفعلي الحقيقي
            total_before_discount = default_price * qty
            total_after_sale = price * qty  # الإجمالي الحقيقي (300 ريال في مثالك)
            
            # احتساب قيمة الخصم الممنوح للزبون إن وجد
            discount = (total_before_discount - total_after_sale) if total_before_discount > total_after_sale else 0
            net_total = total_after_sale
            
            # التعديل الحاسم: نرسل total_after_sale إلى عمود total وعمود net_total لضبط حساب الأرباح
            execute_query('''
                INSERT INTO invoices (date, item_id, quantity_sold, selling_price, total, discount, net_total) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), item_id, qty, price, total_after_sale, discount, net_total), commit=True)
            
            # تحديث الكمية في المخزن
            execute_query('UPDATE items SET quantity = quantity - %s WHERE id = %s', (qty, item_id), commit=True)
            return redirect(url_for('sales'))
    
    return render_template('sales.html', items=items)


@app.route('/inventory')
def inventory():
    if 'user' not in session:
        return redirect(url_for('login'))
    items = execute_query('SELECT * FROM items ORDER BY id', fetch_all=True)
    return render_template('inventory.html', items=items)

@app.route('/low_stock_alert')
def low_stock_alert():
    """تنبيه للمخزون المنخفض جداً (0 أو 1 قطعة)"""
    if 'user' not in session:
        return redirect(url_for('login'))
    
    critical_items = execute_query('SELECT * FROM items WHERE quantity <= 1 ORDER BY quantity ASC', fetch_all=True)
    low_items = execute_query('SELECT * FROM items WHERE quantity BETWEEN 2 AND 4 ORDER BY quantity ASC', fetch_all=True)
    
    return render_template('low_stock_alert.html', 
                         critical_items=critical_items, 
                         low_items=low_items)

@app.route('/dashboard_stats')
def dashboard_stats():
    """إحصائيات متقدمة وموسعة لوحة التحكم - نسخة مصححة للأقواس ونوع TEXT و FLOAT4"""
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # جلب تاريخ اليوم بصيغة نصية للمقارنة الآمنة مع عمود TEXT
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # 1. إحصائيات اليوم (العدد، الحبات، وإجمالي الإيرادات اليومية)
    today_sales_count = execute_query("SELECT COUNT(*) as count FROM invoices WHERE COALESCE(date, '') LIKE %s", 
                                      (today_str + '%',), fetch_one=True)['count']
    
    today_items_sold = execute_query("SELECT COALESCE(SUM(quantity_sold), 0) as total FROM invoices WHERE COALESCE(date, '') LIKE %s",
                                     (today_str + '%',), fetch_one=True)['total']
    
    today_revenue = execute_query("SELECT COALESCE(SUM(total), 0) as total FROM invoices WHERE COALESCE(date, '') LIKE %s",
                                  (today_str + '%',), fetch_one=True)['total']
    
    # تصحيح قوس الـ SUM والـ COALESCE لحساب أرباح مبيعات اليوم الصافية
    today_profit_data = execute_query('''
        SELECT COALESCE(SUM(invoices.total - (invoices.quantity_sold * items.purchase_price)), 0) as profit
        FROM invoices
        JOIN items ON invoices.item_id = items.id
        WHERE COALESCE(invoices.date, '') LIKE %s
    ''', (today_str + '%',), fetch_one=True)
    today_profit = today_profit_data['profit'] if today_profit_data else 0
    
    # 2. نشاط آخر 30 يوماً بالتفصيل مع تصحيح الأقواس (اليوم، الإيراد، وصافي أرباح اليوم)
    weekly_activity = execute_query('''
        SELECT 
            SUBSTRING(COALESCE(invoices.date, '') FROM 1 FOR 10) as day, 
            COUNT(DISTINCT invoices.id) as invoices, 
            SUM(COALESCE(invoices.total, 0)) as revenue,
            COALESCE(SUM(invoices.total - (invoices.quantity_sold * items.purchase_price)), 0) as profit
        FROM invoices 
        JOIN items ON invoices.item_id = items.id
        WHERE invoices.date IS NOT NULL AND invoices.date <> '' 
          AND SUBSTRING(invoices.date FROM 1 FOR 10) >= TO_CHAR(CURRENT_DATE - INTERVAL '30 days', 'YYYY-MM-DD')
        GROUP BY SUBSTRING(COALESCE(invoices.date, '') FROM 1 FOR 10)
        ORDER BY day DESC
    ''', fetch_all=True)
    
    # 3. تصحيح قوس الـ SUM في استعلام أكثر المواد مبيعاً لحل مشكلة السيرفر نهائياً
    top_items = execute_query('''
        SELECT 
            items.name,
            COALESCE(SUM(invoices.quantity_sold), 0) as total_sold,
            COUNT(invoices.id) as times_sold,
            COALESCE(SUM(invoices.total), 0) as revenue,
            COALESCE(SUM(invoices.total - (invoices.quantity_sold * items.purchase_price)), 0) as item_profit,
            items.current_price,
            items.quantity as current_stock
        FROM items 
        LEFT JOIN invoices ON invoices.item_id = items.id 
        GROUP BY items.id, items.name, items.current_price, items.quantity
        ORDER BY total_sold DESC
        LIMIT 10
    ''', fetch_all=True)
    
    # 4. جلب بيانات المخزون وترتيب النواقص
    stock_ranking = execute_query('''
        SELECT 
            name, quantity, current_price, purchase_price,
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
                         today_profit=today_profit,
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
                       VALUES (%s, %s, %s, %s, %s, %s)''',
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
                       VALUES (%s, %s, %s, %s, %s, %s, %s)''',
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
        result = execute_query('SELECT * FROM items WHERE name LIKE %s', (f'%{keyword}%',), fetch_all=True)
    return render_template('search.html', result=result)

@app.route('/reports')
def reports():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    daily_sales = execute_query('''
        SELECT DATE(date) as date, COALESCE(SUM(total), 0) as daily_total 
        FROM invoices 
        WHERE EXTRACT(MONTH FROM date::timestamp) = EXTRACT(MONTH FROM CURRENT_DATE)
        AND EXTRACT(YEAR FROM date::timestamp) = EXTRACT(YEAR FROM CURRENT_DATE)
        GROUP BY DATE(date) 
        ORDER BY date DESC
    ''', fetch_all=True)
    
    monthly_total = execute_query('''
        SELECT COALESCE(SUM(total), 0) as total 
        FROM invoices 
        WHERE EXTRACT(MONTH FROM date::timestamp) = EXTRACT(MONTH FROM CURRENT_DATE)
        AND EXTRACT(YEAR FROM date::timestamp) = EXTRACT(YEAR FROM CURRENT_DATE)
    ''', fetch_one=True)['total']
    
    return render_template('reports.html', daily_sales=daily_sales, monthly_total=monthly_total)

@app.route('/backup')
def backup():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    return jsonify({'message': '⚠️ النسخ الاحتياطي للبيانات يتم تلقائياً في قاعدة بيانات PostgreSQL'})

@app.route('/get_items_json')
def get_items_json():
    items = execute_query('SELECT id, name, current_price, quantity FROM items WHERE quantity > 0', fetch_all=True)
    return jsonify(items)

@app.route('/update_item/<int:item_id>', methods=['POST'])
def update_item(item_id):
    data = request.json
    if data.get('price'):
        execute_query('UPDATE items SET current_price = %s WHERE id = %s', (float(data['price']), item_id))
    if data.get('quantity'):
        execute_query('UPDATE items SET quantity = %s WHERE id = %s', (int(data['quantity']), item_id))
    return jsonify({'status': 'ok'})

@app.route('/update_order_status/<int:order_id>')
def update_order_status(order_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    execute_query('UPDATE purchase_orders SET status = %s WHERE id = %s', ('تم الشراء', order_id))
    return redirect(url_for('shortages'))

@app.route('/delete_order/<int:order_id>')
def delete_order(order_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    execute_query('DELETE FROM purchase_orders WHERE id = %s', (order_id,))
    return redirect(url_for('shortages'))

@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    item = execute_query('SELECT * FROM items WHERE id = %s', (item_id,), fetch_one=True)
    
    if request.method == 'POST':
        data = request.form
        execute_query('''UPDATE items SET 
                     name = %s,
                     purchase_price = %s,
                     min_selling_price = %s,
                     max_selling_price = %s,
                     avg_selling_price = %s,
                     current_price = %s,
                     quantity = %s
                     WHERE id = %s''',
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
        sale = execute_query('SELECT * FROM invoices WHERE id = %s', (sale_id,), fetch_one=True)
        
        if sale:
            old_quantity = sale['quantity_sold']
            new_total = new_price * new_quantity
            
            execute_query('UPDATE items SET quantity = quantity + %s WHERE id = %s', (old_quantity, sale['item_id']))
            execute_query('UPDATE items SET quantity = quantity - %s WHERE id = %s', (new_quantity, sale['item_id']))
            execute_query('UPDATE invoices SET quantity_sold = %s, selling_price = %s, total = %s WHERE id = %s',
                       (new_quantity, new_price, new_total, sale_id))
        
        return redirect(url_for('sales_list'))
    
    sale = execute_query('''
        SELECT invoices.*, items.name as item_name, items.current_price, items.quantity as available_qty
        FROM invoices 
        LEFT JOIN items ON invoices.item_id = items.id 
        WHERE invoices.id = %s
    ''', (sale_id,), fetch_one=True)
    
    return render_template('edit_sale.html', sale=sale)
@app.route('/cash_flow', methods=['GET', 'POST'])
def cash_flow():
    """إدارة الصندوق والخزينة - مع نظام التنبيه اليومي لمخصص الديون"""
    if 'user' not in session:
        return redirect(url_for('login'))
        
    today_date_str = datetime.now().strftime('%Y-%m-%d')
        
    if request.method == 'POST':
        type_op = request.form.get('type')
        category = request.form.get('category')
        amount = float(request.form.get('amount', 0))
        invoice_num = request.form.get('invoice_number', '')
        notes = request.form.get('notes', '')
        today_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        execute_query('''
            INSERT INTO cash_flow (date, type, category, amount, invoice_number, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (today_now, type_op, category, amount, invoice_num, notes), commit=True)
        return redirect(url_for('cash_flow'))

    # جلب الحركات المادية
    transactions = execute_query('SELECT * FROM cash_flow ORDER BY id DESC LIMIT 50', fetch_all=True)
    
    # فحص هل تم إخراج الـ 1000 ريال اليوم؟
    today_debt_check = execute_query('''
        SELECT COUNT(*) as count FROM cash_flow 
        WHERE category = 'سداد ديون' AND COALESCE(date, '') LIKE %s
    ''', (today_date_str + '%',), fetch_one=True)['count']
    
    # إذا كان الحساب صفر، يعني لم يتم الإخراج اليوم ونفعل التنبيه
    alert_debt = True if today_debt_check == 0 else False

    # حساب الإجماليات
    total_sales = execute_query("SELECT COALESCE(SUM(total), 0) as total FROM invoices", fetch_one=True)['total']
    total_in = execute_query("SELECT COALESCE(SUM(amount), 0) as total FROM cash_flow WHERE type = 'IN'", fetch_one=True)['total']
    total_out = execute_query("SELECT COALESCE(SUM(amount), 0) as total FROM cash_flow WHERE type = 'OUT'", fetch_one=True)['total']
    debt_paid = execute_query("SELECT COALESCE(SUM(amount), 0) as total FROM cash_flow WHERE category = 'سداد ديون'", fetch_one=True)['total']
    
    safe_balance = (total_sales + total_in) - total_out

    return render_template('cash_flow.html', 
                           transactions=transactions, 
                           safe_balance=safe_balance,
                           total_sales=total_sales,
                           total_in=total_in,
                           total_out=total_out,
                           debt_paid=debt_paid,
                           alert_debt=alert_debt) # إرسال متغير التنبيه للواجهة

@app.route('/delete_sale/<int:sale_id>')
def delete_sale(sale_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    sale = execute_query('SELECT * FROM invoices WHERE id = %s', (sale_id,), fetch_one=True)
    
    if sale:
        execute_query('UPDATE items SET quantity = quantity + %s WHERE id = %s', (sale['quantity_sold'], sale['item_id']))
        execute_query('DELETE FROM invoices WHERE id = %s', (sale_id,))
    
    return redirect(url_for('sales_list'))

@app.route('/return_sale/<int:sale_id>', methods=['GET', 'POST'])
def return_sale(sale_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    sale = execute_query('''
        SELECT invoices.*, items.name as item_name 
        FROM invoices 
        LEFT JOIN items ON invoices.item_id = items.id 
        WHERE invoices.id = %s
    ''', (sale_id,), fetch_one=True)
    
    if request.method == 'POST':
        return_quantity = int(request.form['return_quantity'])
        reason = request.form['reason']
        
        if return_quantity <= sale['quantity_sold']:
            execute_query('UPDATE items SET quantity = quantity + %s WHERE id = %s', (return_quantity, sale['item_id']))
            
            return_amount = return_quantity * sale['selling_price']
            execute_query('''
                INSERT INTO returns_log (sale_id, item_name, return_quantity, return_amount, reason, return_date)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (sale_id, sale['item_name'], return_quantity, return_amount, reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            new_quantity = sale['quantity_sold'] - return_quantity
            if new_quantity > 0:
                new_total = new_quantity * sale['selling_price']
                execute_query('UPDATE invoices SET quantity_sold = %s, total = %s WHERE id = %s', (new_quantity, new_total, sale_id))
            else:
                execute_query('DELETE FROM invoices WHERE id = %s', (sale_id,))
            
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
    
    execute_query('DELETE FROM items WHERE id = %s', (item_id,))
    return redirect(url_for('inventory'))

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 تشغيل نظام إدارة محل ابن الشيخ شتيه")
    print("=" * 50)
    print("🗄️  قاعدة البيانات: PostgreSQL (سحابية - بيانات دائمة)")
    print("📱 افتح المتصفح على: http://127.0.0.1:5000")
    print("👤 اسم المستخدم: admin")
    print("🔑 كلمة المرور: admin123")
    print("=" * 50)
    print("✅ ملاحظة: جميع البيانات سيتم حفظها بشكل دائم في قاعدة البيانات السحابية!")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
