import os
import json
import functools
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, g, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection, init_db

# Create dedicated Student Flask Application
app = Flask(__name__)
app.secret_key = os.environ.get("STUDENT_SECRET_KEY", "quizmaster-student-portal-secret-key-2026")

# Initialize database
with app.app_context():
    init_db()

# --- Student Session Middleware & Auth ---

@app.before_request
def load_logged_in_student():
    """Loads student from session before each request."""
    user_id = session.get("student_id")
    if user_id is None:
        g.user = None
    else:
        conn = get_db_connection()
        g.user = conn.execute(
            "SELECT id, username, email, role, created_at FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        conn.close()

def student_login_required(view):
    """Decorator to require student login."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("Please sign in with your student account to access this page.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(**kwargs)
    return wrapped_view

@app.context_processor
def inject_student_globals():
    return dict(current_user=g.user)


# --- Student Routes ---

@app.route("/")
def index():
    """Student Portal Landing Page."""
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
        "users_count": conn.execute("SELECT COUNT(*) AS c FROM users WHERE role = 'user'").fetchone()["c"],
        "questions_count": conn.execute("SELECT COUNT(*) AS c FROM questions").fetchone()["c"],
        "attempts_count": conn.execute("SELECT COUNT(*) AS c FROM results").fetchone()["c"]
    }
    conn.close()
    return render_template("index.html", quizzes=quizzes, stats=stats)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Dedicated Student Login."""
    if g.user:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email_or_user = request.form.get("email_or_user", "").strip()
        password = request.form.get("password", "")

        if not email_or_user or not password:
            flash("Please enter both email/username and password.", "danger")
            return render_template("student/login.html")

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ? OR username = ?",
            (email_or_user.lower(), email_or_user)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            # Verify student role
            session.clear()
            session["student_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            flash(f"Welcome, {user['username']}!", "success")
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email/username or password. Please try again.", "danger")

    return render_template("student/login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Dedicated Student Registration."""
    if g.user:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("student/register.html", username=username, email=email)

        if len(password) < 4:
            flash("Password must be at least 4 characters long.", "danger")
            return render_template("student/register.html", username=username, email=email)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("student/register.html", username=username, email=email)

        conn = get_db_connection()
        existing = conn.execute("SELECT id FROM users WHERE email = ? OR username = ?", (email, username)).fetchone()
        if existing:
            conn.close()
            flash("Username or Email is already registered. Please sign in.", "warning")
            return redirect(url_for("login"))

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
        session["student_id"] = new_user_id
        session["username"] = username
        session["role"] = "user"

        flash(f"Welcome to QuizMaster, {username}! Your student account is ready.", "success")
        return redirect(url_for("dashboard"))

    return render_template("student/register.html")


@app.route("/logout")
def logout():
    """Logs out student and clears session."""
    session.clear()
    flash("You have been successfully logged out from Student Portal.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@student_login_required
def dashboard():
    """Student Dashboard with statistics, available quizzes, and attempt history."""
    conn = get_db_connection()

    # 1. Available Quizzes with question count
    quizzes = conn.execute("""
        SELECT q.*, COUNT(ques.id) AS question_count
        FROM quizzes q
        LEFT JOIN questions ques ON q.id = ques.quiz_id
        GROUP BY q.id
        ORDER BY q.id ASC
    """).fetchall()

    # 2. User's previous attempts
    user_results = conn.execute("""
        SELECT r.*, q.title AS quiz_title, q.category AS quiz_category
        FROM results r
        JOIN quizzes q ON r.quiz_id = q.id
        WHERE r.user_id = ?
        ORDER BY r.date DESC
    """, (g.user["id"],)).fetchall()

    # 3. User Statistics
    total_attempts = len(user_results)
    avg_score = round(sum(r["percentage"] for r in user_results) / total_attempts, 1) if total_attempts > 0 else 0
    best_score = round(max((r["percentage"] for r in user_results), default=0), 1)

    # 4. Global Leaderboard (Top 5 scorers)
    leaderboard = conn.execute("""
        SELECT u.username, COUNT(r.id) AS total_quizzes, ROUND(AVG(r.percentage), 1) AS avg_percent, MAX(r.percentage) AS max_percent
        FROM results r
        JOIN users u ON r.user_id = u.id
        WHERE u.role = 'user'
        GROUP BY u.id
        ORDER BY avg_percent DESC, total_quizzes DESC
        LIMIT 5
    """).fetchall()

    conn.close()

    user_stats = {
        "total_attempts": total_attempts,
        "avg_score": avg_score,
        "best_score": best_score
    }

    return render_template(
        "student/dashboard.html",
        quizzes=quizzes,
        user_results=user_results,
        user_stats=user_stats,
        leaderboard=leaderboard
    )


@app.route("/quiz/<int:quiz_id>")
@student_login_required
def take_quiz(quiz_id):
    """Quiz taking interface."""
    conn = get_db_connection()
    quiz = conn.execute("SELECT * FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()

    if not quiz:
        conn.close()
        flash("Quiz not found.", "danger")
        return redirect(url_for("dashboard"))

    questions = conn.execute("SELECT * FROM questions WHERE quiz_id = ? ORDER BY id ASC", (quiz_id,)).fetchall()
    conn.close()

    if not questions:
        flash("This quiz currently has no questions. Please try another quiz.", "warning")
        return redirect(url_for("dashboard"))

    return render_template("student/quiz.html", quiz=quiz, questions=questions, total_questions=len(questions))


@app.route("/quiz/<int:quiz_id>/submit", methods=["POST"])
@student_login_required
def submit_quiz(quiz_id):
    """Evaluates quiz answers, saves result, and redirects to result page."""
    conn = get_db_connection()
    quiz = conn.execute("SELECT * FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()
    if not quiz:
        conn.close()
        abort(404)

    questions = conn.execute("SELECT * FROM questions WHERE quiz_id = ? ORDER BY id ASC", (quiz_id,)).fetchall()

    total_questions = len(questions)
    if total_questions == 0:
        conn.close()
        flash("Cannot submit an empty quiz.", "danger")
        return redirect(url_for("dashboard"))

    score = 0
    user_answers = {}

    for question in questions:
        q_id = str(question["id"])
        selected = request.form.get(f"question_{q_id}")
        user_answers[q_id] = selected

        if selected and selected.upper() == question["correct_answer"].upper():
            score += 1

    percentage = round((score / total_questions) * 100, 2)
    answers_json = json.dumps(user_answers)

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO results (user_id, quiz_id, score, total, percentage, answers_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (g.user["id"], quiz_id, score, total_questions, percentage, answers_json))
    result_id = cursor.lastrowid
    conn.commit()
    conn.close()

    flash("Quiz submitted successfully! Here is your score breakdown.", "success")
    return redirect(url_for("view_result", result_id=result_id))


@app.route("/result/<int:result_id>")
@student_login_required
def view_result(result_id):
    """Displays detailed score and question-by-question review."""
    conn = get_db_connection()
    result = conn.execute("""
        SELECT r.*, q.title AS quiz_title, q.description AS quiz_desc, q.category AS quiz_category, u.username
        FROM results r
        JOIN quizzes q ON r.quiz_id = q.id
        JOIN users u ON r.user_id = u.id
        WHERE r.id = ?
    """, (result_id,)).fetchone()

    if not result:
        conn.close()
        flash("Result record not found.", "danger")
        return redirect(url_for("dashboard"))

    if result["user_id"] != g.user["id"] and g.user["role"] != "admin":
        conn.close()
        flash("Unauthorized to view this result.", "danger")
        return redirect(url_for("dashboard"))

    questions = conn.execute("SELECT * FROM questions WHERE quiz_id = ? ORDER BY id ASC", (result["quiz_id"],)).fetchall()
    conn.close()

    user_answers = {}
    if result["answers_json"]:
        try:
            user_answers = json.loads(result["answers_json"])
        except Exception:
            user_answers = {}

    pct = result["percentage"]
    if pct >= 80:
        feedback = {"msg": "Outstanding! Excellent Mastery.", "color": "success", "icon": "bi-trophy-fill"}
    elif pct >= 60:
        feedback = {"msg": "Good Job! Solid understanding.", "color": "primary", "icon": "bi-hand-thumbs-up-fill"}
    elif pct >= 40:
        feedback = {"msg": "Keep Practicing! You are getting there.", "color": "warning", "icon": "bi-lightning-charge-fill"}
    else:
        feedback = {"msg": "Need More Practice! Review the concepts and try again.", "color": "danger", "icon": "bi-book-half"}

    return render_template(
        "student/result.html",
        result=result,
        questions=questions,
        user_answers=user_answers,
        feedback=feedback
    )


@app.route("/leaderboard")
def leaderboard():
    """Global Leaderboard view showing top students across all quizzes."""
    conn = get_db_connection()
    top_scorers = conn.execute("""
        SELECT u.username, u.email,
               COUNT(r.id) AS total_quizzes,
               ROUND(AVG(r.percentage), 1) AS avg_percent,
               MAX(r.percentage) AS max_percent,
               SUM(r.score) AS total_points
        FROM results r
        JOIN users u ON r.user_id = u.id
        WHERE u.role = 'user'
        GROUP BY u.id
        ORDER BY total_points DESC, avg_percent DESC
        LIMIT 20
    """).fetchall()
    conn.close()
    return render_template("student/leaderboard.html", top_scorers=top_scorers)


# --- Error Handlers ---

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


if __name__ == "__main__":
    port = int(os.environ.get("STUDENT_PORT", 5000))
    print(f"🎓 QuizMaster Student Portal running at http://127.0.0.1:{port}")
    app.run(debug=True, port=port)
