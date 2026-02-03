from flask import Flask, render_template, request, flash, redirect, url_for
import mysql.connector

app = Flask(__name__)
app.secret_key = "supersecretkey"

# --- DATABASE CONNECTION HELPER ---
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="rahul@123",
        database="student_dashboard",
        auth_plugin="mysql_native_password"
    )

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

            # Determine Performance Category
            if total >= 75:
                category = "Best"
            elif total >= 60:
                category = "Good"
            elif total >= 40:
                category = "Average"
            else:
                category = "Poor"

            # Save to Database
            db = get_db_connection()
            cur = db.cursor()
            cur.execute("""
                INSERT INTO predictions
                (attendance, internal_exam_1, internal_exam_2,
                 avg_internal, external_marks, total_marks, performance)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (attendance, i1, i2, internal_avg, external, total, category))
            
            db.commit()
            cur.close()
            db.close()
        except Exception as e:
            print(f"Error saving data: {e}")

    return render_template(
        "index.html",
        internal_avg=internal_avg,
        external=external,
        total=total,
        category=category
    )

# --- 2. DASHBOARD (ANALYTICS & RISK DETECTION) ---
@app.route("/dashboard")
def dashboard():
    try:
        db = get_db_connection()
        cur = db.cursor(dictionary=True) 
        
        # Select all data needed for charts and risk analysis
        cur.execute("""
            SELECT attendance, avg_internal, external_marks,
                total_marks, performance, created_at
            FROM predictions
            ORDER BY created_at DESC
        """)
        
        data = cur.fetchall()
        cur.close()
        db.close()
        
        # --- RISK ANALYSIS ENGINE ---
        risk_students = []
        
        for row in data:
            reasons = []
            intervention = "None"
            
            # Rule 1: Attendance Risk (< 75%)
            if row['attendance'] < 75:
                reasons.append("Low Attendance")
                intervention = "Parent Meeting"
                
            # Rule 2: Academic Risk (< 50%)
            if row['total_marks'] < 50:
                reasons.append("Academic Failure")
                if intervention == "None":
                    intervention = "Remedial Classes"
                else:
                    intervention += " & Remedial Classes"
            
            # If any risk found, add to the alert list
            if reasons:
                row['risk_factors'] = " + ".join(reasons)
                row['intervention'] = intervention
                risk_students.append(row)

        return render_template("dashboard.html", data=data, risk_students=risk_students)
    
    except Exception as e:
        return f"<h1>Error loading dashboard: {e}</h1><p>Did you run /init_db yet?</p>"

# --- 3. CLEAR HISTORY ---
@app.route('/clear', methods=['POST'])
def clear_history():
    try:
        db = get_db_connection()
        cur = db.cursor()
        cur.execute("DELETE FROM predictions")
        db.commit()
        print("History Cleared Successfully!")
        cur.close()
        db.close()
    except Exception as e:
        print(f"Error clearing history: {e}")
        
    return redirect(url_for('dashboard'))

# --- 4. DATABASE SETUP (THE FIX) ---
# Run this route once to fix "Table not found" or "Unknown column" errors
@app.route('/init_db')
def init_db():
    try:
        db = get_db_connection()
        cur = db.cursor()
        
        # Drop old table if exists
        cur.execute("DROP TABLE IF EXISTS predictions")
        
        # Create new table with ALL required columns
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
        db.commit()
        cur.close()
        db.close()
        return """
            <h1 style='color:green; font-family:sans-serif;'>✅ Database Initialized Successfully!</h1>
            <p style='font-family:sans-serif;'>The table 'predictions' has been recreated with the correct columns.</p>
            <a href='/' style='font-size:1.2rem;'>Go to App Home</a>
        """
    except Exception as e:
        return f"<h1 style='color:red;'>❌ Setup Failed: {e}</h1>"

if __name__ == "__main__":
    app.run(debug=True)