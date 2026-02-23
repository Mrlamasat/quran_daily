from flask import Flask, render_template, request, redirect, url_for, make_response
import sqlite3
import random
import datetime

app = Flask(__name__)

DB = 'db.sqlite'

# ---------- قاعدة البيانات ---------- #
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    # جدول الأعضاء
    c.execute('''CREATE TABLE IF NOT EXISTS members (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT,
                 number TEXT UNIQUE,
                 otp TEXT)''')
    # جدول الورد اليومي
    c.execute('''CREATE TABLE IF NOT EXISTS daily_ward (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 day INTEGER,
                 member_id INTEGER,
                 from_aya TEXT,
                 to_aya TEXT)''')
    # جدول حالة القراءة
    c.execute('''CREATE TABLE IF NOT EXISTS progress (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 day INTEGER,
                 member_id INTEGER,
                 done INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

# ---------- توليد OTP ---------- #
def generate_otp():
    return str(random.randint(100000, 999999))

# ---------- التحقق من الجلسة ---------- #
def get_current_member():
    member_number = request.cookies.get('member_number')
    if member_number:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT id, name FROM members WHERE number=?", (member_number,))
        member = c.fetchone()
        conn.close()
        if member:
            return {'id': member[0], 'name': member[1]}
    return None

# ---------- الصفحات ---------- #

@app.route('/', methods=['GET', 'POST'])
def login():
    member = get_current_member()
    if member:
        return redirect(url_for('daily'))

    msg = ''
    if request.method == 'POST':
        number = request.form.get('number')
        otp_input = request.form.get('otp')

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT id, otp FROM members WHERE number=?", (number,))
        row = c.fetchone()

        if row:
            if otp_input:
                # تحقق من OTP
                if otp_input == row[1]:
                    resp = make_response(redirect(url_for('daily')))
                    resp.set_cookie('member_number', number)
                    conn.close()
                    return resp
                else:
                    msg = 'رمز التحقق غير صحيح'
            else:
                # توليد OTP جديد
                otp = generate_otp()
                c.execute("UPDATE members SET otp=? WHERE number=?", (otp, number))
                conn.commit()
                msg = f'رمز التحقق للعضو {number}: {otp} (استخدمه مرة واحدة)'
        else:
            msg = 'الرقم غير مسجل'
        conn.close()
    return render_template('login.html', msg=msg)

@app.route('/daily', methods=['GET', 'POST'])
def daily():
    member = get_current_member()
    if not member:
        return redirect(url_for('login'))

    # اليوم الحالي تلقائيًا (يمكن تغييره حسب الحاجة)
    today = 6  # مثال: اليوم السادس
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # جلب الورد اليومي لكل الأعضاء
    c.execute('''
        SELECT m.id, m.name, d.from_aya, d.to_aya,
               COALESCE(p.done,0)
        FROM daily_ward d
        JOIN members m ON d.member_id=m.id
        LEFT JOIN progress p ON p.member_id=m.id AND p.day=d.day
        WHERE d.day=?
    ''', (today,))
    wards = c.fetchall()

    if request.method == 'POST':
        # تحديث علامة ✅ للعضو الحالي فقط
        c.execute("INSERT OR REPLACE INTO progress (day, member_id, done) VALUES (?,?,?)",
                  (today, member['id'], 1))
        conn.commit()
        return redirect(url_for('daily'))

    conn.close()
    return render_template('daily.html', wards=wards, current_member_id=member['id'])

@app.route('/admin')
def admin():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    # جلب كل الأعضاء
    c.execute("SELECT id, name, number FROM members")
    members = c.fetchall()
    # جلب الورد اليومي
    c.execute("SELECT day, member_id, from_aya, to_aya FROM daily_ward")
    wards = c.fetchall()
    conn.close()
    return render_template('admin.html', members=members, wards=wards)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
