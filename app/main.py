from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"
DB_NAME = "student_dashboard.db"

# --- DATABASE CONNECTION HELPER ---
def get_db_connection():
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row  # Access columns by name
        return conn
    except Exception as e:
        print("DB connection failed:", e)
        return None


# --- 1. HOME PAGE (PREDICTION & INPUT) ---
@app.route("/", methods=["GET", "POST"])
def index():
    internal_avg = external = total = category = None

    if request.method == "POST":
        attendance = float(request.form["attendance"])
        i1 = float(request.form["i1"])
        i2 = float(request.form["i2"])
        external = float(request.form["external"])

        internal_avg = round((i1 + i2) / 2, 2)
        total = round(internal_avg + external, 2)

        if total >= 75:
            category = "Best"
        elif total >= 60:
            category = "Good"
        elif total >= 40:
            category = "Average"
        else:
            category = "Poor"

        conn = get_db_connection()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO predictions
                    (attendance, internal_exam_1, internal_exam_2,
                     avg_internal, external_marks, total_marks, performance)
                    VALUES (?,?,?,?,?,?,?)
                """, (attendance, i1, i2, internal_avg, external, total, category))
                conn.commit()
                conn.close()
            except Exception as e:
                print("DB insert failed:", e)

    return render_template(
        "index.html",
        internal_avg=internal_avg,
        external=external,
        total=total,
        category=category
    )


# --- 2. DASHBOARD ---
@app.route("/dashboard")
def dashboard():
    conn = get_db_connection()
    if not conn:
        return render_template("dashboard.html", data=[], risk_students=[])

    try:
        cur = conn.cursor()
        # No 'dictionary=True' in sqlite3, row_factory handles it
        cur.execute("""
            SELECT attendance, avg_internal, external_marks,
                   total_marks, performance, created_at
            FROM predictions
            ORDER BY created_at DESC
        """)
        data = cur.fetchall()
        conn.close()

        risk_students = []
        for row in data:
            reasons = []
            intervention = "None"

            # SQLite rows behave like dicts due to row_factory
            if row['attendance'] < 75:
                reasons.append("Low Attendance")
                intervention = "Parent Meeting"

            if row['total_marks'] < 50:
                reasons.append("Academic Failure")
                if intervention == "None":
                    intervention = "Remedial Classes"
                else:
                    intervention += " & Remedial Classes"

            if reasons:
                # Convert row to dict to append extra fields (Rows are immutable)
                row_dict = dict(row)
                row_dict['risk_factors'] = " + ".join(reasons)
                row_dict['intervention'] = intervention
                risk_students.append(row_dict)

        return render_template("dashboard.html", data=data, risk_students=risk_students)

    except Exception as e:
        return f"<h1>Error loading dashboard: {e}</h1>"


# --- 3. CLEAR HISTORY ---
@app.route('/clear', methods=['POST'])
def clear_history():
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM predictions")
            conn.commit()
            conn.close()
        except Exception as e:
            print("Clear failed:", e)

    return redirect(url_for('dashboard'))


# --- 4. DATABASE SETUP ---
@app.route('/init_db')
def init_db():
    conn = get_db_connection()
    if not conn:
        return "<h1 style='color:red;'>Database not available</h1>"

    try:
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS predictions")
        # SQLite uses AUTOINCREMENT differently, usually implied by INTEGER PRIMARY KEY
        cur.execute("""
            CREATE TABLE predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attendance REAL,
                internal_exam_1 REAL,
                internal_exam_2 REAL,
                avg_internal REAL,
                external_marks REAL,
                total_marks REAL,
                performance TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

        return "<h1 style='color:green;'>Database Initialized Successfully (SQLite)</h1>"

    except Exception as e:
        return f"<h1 style='color:red;'>Setup Failed: {e}</h1>"


def check_and_create_db():
    # SQLite creates the file automatically on connect
    if not os.path.exists(DB_NAME):
        print("Database file not found. Initializing...")
        try:
            # Re-use init_db logic indirectly or just let init_db handle table creation
            # Here we just ensure the empty file is creatable
            conn = sqlite3.connect(DB_NAME)
            conn.close()
            print("Database file created.")
        except Exception as e:
            print("Failed to create database file:", e)
    else:
        print("Database file found.")


if __name__ == "__main__":
    check_and_create_db()
    app.run(debug=True)
