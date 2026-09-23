import functools
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/")
def index():
    """Landing Home Page with available quizzes preview."""
    conn = get_db_connection()
    quizzes = conn.execute("""
        SELECT q.*, COUNT(ques.id) AS question_count
        FROM quizzes q
        LEFT JOIN questions ques ON q.id = ques.quiz_id
        GROUP BY q.id
        ORDER BY q.id ASC
    """).fetchall()

    stats = {
        "quizzes_count": len(quizzes),
        "users_count": conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"],
        "questions_count": conn.execute("SELECT COUNT(*) AS c FROM questions").fetchone()["c"],
        "attempts_count": conn.execute("SELECT COUNT(*) AS c FROM results").fetchone()["c"]
    }
    conn.close()
    return render_template("index.html", quizzes=quizzes, stats=stats)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """User Registration Route."""
    if g.user:
        if g.user["role"] == "admin":
            return redirect(url_for("admin.admin_dashboard"))
        return redirect(url_for("student.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html", username=username, email=email)

        if len(password) < 4:
            flash("Password must be at least 4 characters long.", "danger")
            return render_template("register.html", username=username, email=email)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html", username=username, email=email)

        conn = get_db_connection()
        existing = conn.execute("SELECT id FROM users WHERE email = ? OR username = ?", (email, username)).fetchone()
        if existing:
            conn.close()
            flash("Username or Email already registered. Please log in.", "warning")
            return redirect(url_for("auth.login"))

        hashed_pass = generate_password_hash(password)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, 'user')",
            (username, email, hashed_pass)
        )
        new_user_id = cursor.lastrowid
        conn.commit()
        conn.close()

        session.clear()
        session["user_id"] = new_user_id
        session["username"] = username
        session["role"] = "user"
        flash(f"Welcome to QuizMaster, {username}! Your account has been created.", "success")
        return redirect(url_for("student.dashboard"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """User and Admin Login Route - Separates Admin and Student directly to their dashboards."""
    if g.user:
        if g.user["role"] == "admin":
            return redirect(url_for("admin.admin_dashboard"))
        return redirect(url_for("student.dashboard"))

    if request.method == "POST":
        email_or_user = request.form.get("email_or_user", "").strip()
        password = request.form.get("password", "")

        if not email_or_user or not password:
            flash("Please enter both credentials.", "danger")
            return render_template("login.html")

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ? OR username = ?",
            (email_or_user.lower(), email_or_user)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            flash(f"Welcome back, {user['username']}!", "success")
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)

            # Strict destination separation: Admin -> Admin Console, Student -> Student Dashboard
            if user["role"] == "admin":
                return redirect(url_for("admin.admin_dashboard"))
            return redirect(url_for("student.dashboard"))
        else:
            flash("Invalid email/username or password. Please try again.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    """Logs out current user and clears session."""
    session.clear()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for("auth.login"))
