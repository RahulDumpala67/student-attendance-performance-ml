from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

# --- DATABASE CONNECTION HELPER ---
def get_db_connection():
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "root"),
            database=os.getenv("DB_NAME", "student_dashboard"),
            port=int(os.getenv("DB_PORT", 3306))
        )
    except Exception as e:
        print("DB connection failed:", e)
        return str(e)


# --- 1. HOME PAGE (PREDICTION & INPUT) ---
@app.route("/", methods=["GET", "POST"])
def index():
    internal_avg = external = total = category = None

    if request.method == "POST":

        try:
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
            if hasattr(conn, 'cursor'): # Check if it's a real connection object
                try:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO predictions
                        (attendance, internal_exam_1, internal_exam_2,
                         avg_internal, external_marks, total_marks, performance)
                        VALUES (%s,%s,%s,%s,%s,%s,%s)
                    """, (attendance, i1, i2, internal_avg, external, total, category))
                    conn.commit()
                    cur.close()
                    conn.close()
                except Exception as e:
                    print("DB insert failed:", e)
            else:
                print("DB unavailable for insert")

        except ValueError:
            pass # Handle invalid input

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
    
    # If error string or None
    if not hasattr(conn, 'cursor'):
        return render_template("dashboard.html", data=[], risk_students=[])

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT attendance, avg_internal, external_marks,
                   total_marks, performance, created_at
            FROM predictions
            ORDER BY created_at DESC
        """)
        data = cur.fetchall()
        cur.close()
        conn.close()

        risk_students = []
        for row in data:
            reasons = []
            intervention = "None"

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
                row['risk_factors'] = " + ".join(reasons)
                row['intervention'] = intervention
                risk_students.append(row)

        return render_template("dashboard.html", data=data, risk_students=risk_students)

    except Exception as e:
        return f"<h1>Error loading dashboard: {e}</h1>"


# --- 3. CLEAR HISTORY ---
@app.route('/clear', methods=['POST'])
def clear_history():
    conn = get_db_connection()
    if hasattr(conn, 'cursor'):
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM predictions")
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print("Clear failed:", e)

    return redirect(url_for('dashboard'))


# --- 4. DATABASE SETUP ---
@app.route('/init_db')
def init_db():
    conn = get_db_connection()
    
    if isinstance(conn, str):
        return f"<h1 style='color:red;'>Database Connection Failed: {conn}</h1>"
    
    if not conn:
         return "<h1 style='color:red;'>Unknown Database Error</h1>"

    try:
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS predictions")
        cur.execute("""
            CREATE TABLE predictions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                attendance FLOAT,
                internal_exam_1 FLOAT,
                internal_exam_2 FLOAT,
                avg_internal FLOAT,
                external_marks FLOAT,
                total_marks FLOAT,
                performance VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

        return "<h1 style='color:green;'>MySQL Database Initialized Successfully</h1>"

    except Exception as e:
        return f"<h1 style='color:red;'>Setup Failed: {e}</h1>"


if __name__ == "__main__":
    app.run(debug=True)
