from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "online-election-secret-key"

DATABASE = "election.db"


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            has_voted INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            party TEXT NOT NULL,
            votes INTEGER DEFAULT 0
        )
    """)

    # Add sample candidates if table is empty
    cursor.execute("SELECT COUNT(*) FROM candidates")
    count = cursor.fetchone()[0]

    if count == 0:
        candidates = [
            ("Rahul Sharma", "Development Party"),
            ("Priya Patil", "Student Party"),
            ("Amit Kumar", "Progress Party")
        ]

        cursor.executemany(
            "INSERT INTO candidates (name, party) VALUES (?, ?)",
            candidates
        )

    conn.commit()
    conn.close()


# ---------------- HOME ----------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please fill all fields.")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        conn = get_db()

        try:
            conn.execute(
                """
                INSERT INTO users (name, email, password)
                VALUES (?, ?, ?)
                """,
                (name, email, hashed_password)
            )

            conn.commit()
            flash("Registration successful. Please login.")
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            flash("Email already registered.")
            return redirect(url_for("register"))

        finally:
            conn.close()

    return render_template("register.html")


# ---------------- USER LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            return redirect(url_for("vote"))

        flash("Invalid email or password.")

    return render_template("login.html")


# ---------------- ADMIN LOGIN ----------------

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Demo admin credentials
        if username == "admin" and password == "admin123":

            session["admin"] = True

            return redirect(url_for("admin"))

        flash("Invalid admin username or password.")

    return render_template("admin_login.html")


# ---------------- ADMIN DASHBOARD ----------------

@app.route("/admin")
def admin():

    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    candidates = conn.execute(
        "SELECT * FROM candidates ORDER BY votes DESC"
    ).fetchall()

    users = conn.execute(
        "SELECT id, name, email, has_voted FROM users"
    ).fetchall()

    conn.close()

    return render_template(
        "result.html",
        candidates=candidates,
        users=users,
        admin=True
    )


# ---------------- VOTING PAGE ----------------

@app.route("/vote", methods=["GET", "POST"])
def vote():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    candidates = conn.execute(
        "SELECT * FROM candidates"
    ).fetchall()

    if request.method == "POST":

        if user["has_voted"] == 1:
            conn.close()
            flash("You have already voted.")
            return redirect(url_for("vote"))

        candidate_id = request.form.get("candidate")

        if not candidate_id:
            conn.close()
            flash("Please select a candidate.")
            return redirect(url_for("vote"))

        candidate = conn.execute(
            "SELECT * FROM candidates WHERE id = ?",
            (candidate_id,)
        ).fetchone()

        if not candidate:
            conn.close()
            flash("Invalid candidate.")
            return redirect(url_for("vote"))

        conn.execute(
            "UPDATE candidates SET votes = votes + 1 WHERE id = ?",
            (candidate_id,)
        )

        conn.execute(
            "UPDATE users SET has_voted = 1 WHERE id = ?",
            (session["user_id"],)
        )

        conn.commit()
        conn.close()

        return redirect(url_for("results"))

    conn.close()

    return render_template(
        "vote.html",
        candidates=candidates,
        user=user
    )


# ---------------- RESULTS ----------------

@app.route("/results")
def results():

    conn = get_db()

    candidates = conn.execute(
        """
        SELECT * FROM candidates
        ORDER BY votes DESC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "result.html",
        candidates=candidates,
        users=None,
        admin=False
    )


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("index"))


# ---------------- RUN APPLICATION ----------------

if __name__ == "__main__":
    init_db()

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )