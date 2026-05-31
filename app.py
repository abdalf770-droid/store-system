from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import os
import asyncpg
import asyncio

app = Flask(__name__)
app.secret_key = 'ibn_al_shaykh_secret_key_2024'

# رابط قاعدة البيانات
DATABASE_URL = "postgresql://store_db_new_user:SP6AhmF93Es2GTFfMF3h8Huh8jzrMkru@dpg-d8d0kl6gvqtc73dvpb0g-a/store_db_new"

def run_async(coro):
    """تشغيل دوال غير متزامنة في Flask"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

async def get_db_connection():
    """إنشاء اتصال بقاعدة البيانات"""
    try:
        conn = await asyncpg.connect(DATABASE_URL.replace('postgresql://', 'postgres://') + '?sslmode=require')
        print("✅ تم الاتصال بقاعدة البيانات بنجاح!")
        return conn
    except Exception as e:
        print(f"❌ خطأ في الاتصال بقاعدة البيانات: {e}")
        return None

async def init_db_async():
    """تهيئة قاعدة البيانات (غير متزامن)"""
    conn = await get_db_connection()
    if not conn:
        print("❌ فشل الاتصال بقاعدة البيانات، لا يمكن التهيئة")
        return
    
    try:
        # إنشاء جدول المستخدمين
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        
        # إنشاء جدول الأصناف
        await conn.execute("""
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
        
        # إضافة المستخدم الافتراضي إذا لم يكن موجوداً
        user_exists = await conn.fetchval("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        if user_exists == 0:
            await conn.execute("INSERT INTO users (username, password) VALUES ('admin', 'admin123')")
            print("✅ تم إضافة المستخدم الافتراضي (admin/admin123)")
        
        print("✅ تم تهيئة قاعدة البيانات وجميع الجداول بنجاح!")
        
    except Exception as e:
        print(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")
    finally:
        await conn.close()

def init_db():
    """تهيئة قاعدة البيانات (بواجهة متزامنة)"""
    run_async(init_db_async())

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/do_login', methods=['POST'])
def do_login():
    username = request.form['username']
    password = request.form['password']
    
    async def check_user():
        conn = await get_db_connection()
        if not conn:
            return None
        try:
            row = await conn.fetchrow("SELECT * FROM users WHERE username = $1 AND password = $2", username, password)
            return row
        finally:
            await conn.close()
    
    user = run_async(check_user())
    if user:
        session['user'] = username
        return redirect(url_for('dashboard'))
    else:
        return render_template('login.html', error="بيانات الدخول غير صحيحة")

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    async def get_items():
        conn = await get_db_connection()
        if not conn:
            return []
        try:
            rows = await conn.fetch("SELECT * FROM items ORDER BY id")
            return [dict(row) for row in rows]
        finally:
            await conn.close()
    
    items = run_async(get_items())
    return render_template('dashboard.html', items=items)

@app.route('/inventory')
def inventory():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    async def get_items():
        conn = await get_db_connection()
        if not conn:
            return []
        try:
            rows = await conn.fetch("SELECT * FROM items ORDER BY id")
            return [dict(row) for row in rows]
        finally:
            await conn.close()
    
    items = run_async(get_items())
    return render_template('inventory.html', items=items)

@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        data = request.form
        print(f"📝 إضافة صنف: {data['name']}")
        
        async def add_item_async():
            conn = await get_db_connection()
            if not conn:
                return False
            try:
                await conn.execute("""
                    INSERT INTO items (name, purchase_price, min_selling_price, 
                                      max_selling_price, avg_selling_price, 
                                      current_price, quantity) 
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, data['name'], float(data['purchase_price']), float(data['min_price']),
                    float(data['max_price']), float(data['avg_price']), 
                    float(data['current_price']), int(data['quantity']))
                return True
            except Exception as e:
                print(f"❌ خطأ في الحفظ: {e}")
                return False
            finally:
                await conn.close()
        
        success = run_async(add_item_async())
        if success:
            print(f"✅ تم حفظ الصنف '{data['name']}' في قاعدة البيانات!")
            return redirect(url_for('inventory'))
        else:
            return render_template('add_item.html', error="فشل حفظ البيانات في قاعدة البيانات")
    
    return render_template('add_item.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# تهيئة قاعدة البيانات عند بدء التشغيل
print("=" * 50)
print("🚀 بدء تشغيل نظام إدارة المخزون")
print("=" * 50)
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
