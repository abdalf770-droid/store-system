from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import os
import pg8000
from pg8000 import DBAPI

app = Flask(__name__)
app.secret_key = 'ibn_al_shaykh_secret_key_2024'

# رابط قاعدة البيانات
DATABASE_URL = "postgresql://store_db_new_user:SP6AhmF93Es2GTFfMF3h8Huh8jzrMkru@dpg-d8d0kl6gvqtc73dvpb0g-a/store_db_new"

def get_db_connection():
    """إنشاء اتصال بقاعدة البيانات باستخدام pg8000"""
    try:
        # تحليل رابط قاعدة البيانات
        import urllib.parse as urlparse
        url = urlparse.urlparse(DATABASE_URL)
        
        conn = pg8000.connect(
            host=url.hostname,
            port=url.port or 5432,
            database=url.path[1:],
            user=url.username,
            password=url.password,
            ssl_context=True  # تفعيل SSL
        )
        return conn
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {e}")
        return None

def init_db():
    """تهيئة قاعدة البيانات"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        
        try:
            # إنشاء جدول المستخدمين
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                )
            """)
            
            # إنشاء جدول الأصناف
            cursor.execute("""
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
            """)
            
            # إضافة المستخدم الافتراضي
            cursor.execute("SELECT * FROM users WHERE username = 'admin'")
            if not cursor.fetchone():
                cursor.execute("INSERT INTO users (username, password) VALUES ('admin', 'admin123')")
            
            conn.commit()
            print("✅ تم تهيئة قاعدة البيانات بنجاح!")
            
        except Exception as e:
            print(f"❌ خطأ في التهيئة: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    else:
        print("❌ فشل الاتصال بقاعدة البيانات")

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/do_login', methods=['POST'])
def do_login():
    username = request.form['username']
    password = request.form['password']
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
            user = cursor.fetchone()
            if user:
                session['user'] = username
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error="بيانات الدخول غير صحيحة")
        finally:
            cursor.close()
            conn.close()
    
    return render_template('login.html', error="خطأ في الاتصال بقاعدة البيانات")

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    items = []
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM items ORDER BY id")
            rows = cursor.fetchall()
            for row in rows:
                items.append({
                    'id': row[0],
                    'name': row[1],
                    'purchase_price': row[2],
                    'min_selling_price': row[3],
                    'max_selling_price': row[4],
                    'avg_selling_price': row[5],
                    'current_price': row[6],
                    'quantity': row[7]
                })
        finally:
            cursor.close()
            conn.close()
    
    return render_template('dashboard.html', items=items)

@app.route('/inventory')
def inventory():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    items = []
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM items ORDER BY id")
            rows = cursor.fetchall()
            for row in rows:
                items.append({
                    'id': row[0],
                    'name': row[1],
                    'purchase_price': row[2],
                    'min_selling_price': row[3],
                    'max_selling_price': row[4],
                    'avg_selling_price': row[5],
                    'current_price': row[6],
                    'quantity': row[7]
                })
        finally:
            cursor.close()
            conn.close()
    
    return render_template('inventory.html', items=items)

@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            data = request.form
            print(f"📝 إضافة صنف: {data['name']}")
            
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        INSERT INTO items (name, purchase_price, min_selling_price, 
                                          max_selling_price, avg_selling_price, 
                                          current_price, quantity) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (data['name'], float(data['purchase_price']), float(data['min_price']),
                          float(data['max_price']), float(data['avg_price']), 
                          float(data['current_price']), int(data['quantity'])))
                    
                    conn.commit()
                    print(f"✅ تم حفظ الصنف في قاعدة البيانات!")
                    return redirect(url_for('inventory'))
                except Exception as e:
                    conn.rollback()
                    print(f"❌ خطأ في الحفظ: {e}")
                    return render_template('add_item.html', error=f"خطأ في الحفظ: {e}")
                finally:
                    cursor.close()
                    conn.close()
            else:
                print("❌ لا يمكن الاتصال بقاعدة البيانات")
                return render_template('add_item.html', error="لا يمكن الاتصال بقاعدة البيانات")
                
        except Exception as e:
            print(f"❌ خطأ: {e}")
            return render_template('add_item.html', error=f"خطأ: {e}")
    
    return render_template('add_item.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# تهيئة قاعدة البيانات عند بدء التشغيل
print("🚀 بدء تشغيل التطبيق...")
init_db()

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 تشغيل النظام...")
    print(f"🗄️  قاعدة البيانات: PostgreSQL")
    print(f"📱 http://127.0.0.1:5000")
    print(f"👤 admin / admin123")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
