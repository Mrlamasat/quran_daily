from flask import Flask, render_template, request, redirect, url_for, make_response
import sqlite3
import json
import random

app = Flask(__name__)

DB = 'db.sqlite'
QURAN_FILE = 'quran.json'

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS members (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT,
                 number TEXT UNIQUE,
                 otp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS daily_ward (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 day INTEGER,
                 member_id INTEGER,
                 sura TEXT,
                 part_number INTEGER,
                 from_aya INTEGER,
                 to_aya INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS progress (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 day INTEGER,
                 member_id INTEGER,
                 done INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def generate_otp():
    return str(random.randint(100000, 999999))

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
                if otp_input == row[1]:
                    resp = make_response(redirect(url_for('daily')))
                    resp.set_cookie('member_number', number)
                    conn.close()
                    return resp
                else:
                    msg = 'رمز التحقق غير صحيح'
            else:
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
    today = 6
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''
        SELECT m.id, m.name, d.sura, d.from_aya, d.to_aya,
               COALESCE(p.done,0)
        FROM daily_ward d
        JOIN members m ON d.member_id=m.id
        LEFT JOIN progress p ON p.member_id=m.id AND p.day=d.day
        WHERE d.day=?
    ''', (today,))
    wards = c.fetchall()
    if request.method == 'POST':
        c.execute("INSERT OR REPLACE INTO progress (day, member_id, done) VALUES (?,?,?)",
                  (today, member['id'], 1))
        conn.commit()
        return redirect(url_for('daily'))
    conn.close()
    return render_template('daily.html', wards=wards, current_member_id=member['id'])

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, name, number FROM members")
    members = c.fetchall()
    with open(QURAN_FILE, 'r', encoding='utf-8') as f:
        quran = json.load(f)
    suras = sorted(list({item['surah_name']: item['juz'] for item in quran}.items()), key=lambda x:x[0])
    msg = ''
    if request.method == 'POST':
        member_id = int(request.form.get('member_id'))
        sura_name = request.form.get('sura')
        part_number = int(request.form.get('part_number'))
        part_ayas = [item for item in quran if item['surah_name']==sura_name and item['juz']==part_number]
        if part_ayas:
            from_aya = part_ayas[0]['aya']
            to_aya = part_ayas[-1]['aya']
            today = 6
            c.execute('INSERT INTO daily_ward (day, member_id, sura, part_number, from_aya, to_aya) VALUES (?,?,?,?,?,?)',
                      (today, member_id, sura_name, part_number, from_aya, to_aya))
            conn.commit()
            msg = f"تم حفظ ورد اليوم للعضو {member_id}"
        else:
            msg = "خطأ في بيانات الجزء"
    conn.close()
    return render_template('admin.html', members=members, suras=suras, msg=msg)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
