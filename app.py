import os
import sqlite3
from flask import Flask, render_template, request, redirect, session

app = Flask(__name__)
app.secret_key = "super_secret_key_change_this"

DATABASE = "database.db"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "0639296170"

# ------------------ DATABASE ------------------

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    # جدول الأعضاء
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT UNIQUE,
        password TEXT
    )
    """)
    # جدول الورد اليومي
    c.execute("""
    CREATE TABLE IF NOT EXISTS daily (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day INTEGER,
        user_id INTEGER,
        surah TEXT,
        from_ayah INTEGER,
        to_ayah INTEGER,
        done INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()

def get_db():
    return sqlite3.connect(DATABASE)

# ------------------ ROUTES ------------------

# الصفحة الرئيسية
@app.route("/")
def home():
    return redirect("/login")  # الآن أي طلب root يذهب مباشرة للـ login

# ------------------ LOGIN ------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # تسجيل دخول الأدمن
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/admin")

        # تسجيل دخول الأعضاء
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE phone=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session["user_id"] = user[0]
            return redirect("/daily")
        else:
            error = "بيانات غير صحيحة"
    return render_template("login.html", error=error)

# ------------------ DAILY PAGE ------------------
@app.route("/daily", methods=["GET", "POST"])
def daily():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT daily.id, users.name, daily.surah, daily.from_ayah, daily.to_ayah, daily.done, daily.user_id "
              "FROM daily JOIN users ON daily.user_id = users.id")
    records = c.fetchall()

    if request.method == "POST":
        daily_id = request.form["daily_id"]
        c.execute("UPDATE daily SET done=1 WHERE id=? AND user_id=?", (daily_id, user_id))
        conn.commit()
        return redirect("/daily")

    conn.close()
    return render_template("daily.html", records=records, user_id=user_id)

# ------------------ ADMIN PANEL ------------------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if "admin" not in session:
        return redirect("/login")

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()

    if request.method == "POST":
        user_id = request.form["user_id"]
        surah = request.form["surah"]
        from_ayah = request.form["from_ayah"]
        to_ayah = request.form["to_ayah"]

        c.execute("""
        INSERT INTO daily (day, user_id, surah, from_ayah, to_ayah)
        VALUES (1, ?, ?, ?, ?)
        """, (user_id, surah, from_ayah, to_ayah))
        conn.commit()
        return redirect("/admin")

    conn.close()
    return render_template("admin.html", users=users)

# ------------------ LOGOUT ------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ------------------ RUN ------------------
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
