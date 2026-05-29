from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'test'

# بيانات تجريبية فقط (بدون قاعدة بيانات)
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin123':
            session['user'] = 'admin'
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='خطأ')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', 
                         total_purchase=10000,
                         total_selling=15000,
                         today_sales=500,
                         expected_profit=5000,
                         critical_items_count=0,
                         low_stock_count=0)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# باقي المسارات المؤقتة
@app.route('/sales')
def sales(): return "صفحة المبيعات - قيد التطوير"
@app.route('/inventory')
def inventory(): return "صفحة المخازن - قيد التطوير"
@app.route('/users')
def users(): return "صفحة المستخدمين - قيد التطوير"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
