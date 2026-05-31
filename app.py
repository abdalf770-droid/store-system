from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'ibn_al_shaykh_secret_key_2024'

# قاعدة البيانات - تخزن في مكان دائم على Render
DB_PATH = '/var/data/store.db'
if not os.environ.get('RENDER'):
    DB_PATH = 'store.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# تهيئة قاعدة البيانات
def init_db():
    conn = get_db()
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
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    conn = get_db()
    items = conn.execute('SELECT * FROM items').fetchall()
    conn.close()
    return render_template('dashboard.html', items=items)

@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if request.method == 'POST':
        data = request.form
        conn = get_db()
        conn.execute('''
            INSERT INTO items (name, purchase_price, min_selling_price, 
                              max_selling_price, avg_selling_price, 
                              current_price, quantity) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (data['name'], float(data['purchase_price']), float(data['min_price']),
              float(data['max_price']), float(data['avg_price']), 
              float(data['current_price']), int(data['quantity'])))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    return render_template('add_item.html')

@app.route('/delete_item/<int:id>')
def delete_item(id):
    conn = get_db()
    conn.execute('DELETE FROM items WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
