import os
import functools
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, g, abort
)
from werkzeug.security import check_password_hash
from database import get_db_connection, init_db

# Create dedicated Administrator Flask Application
app = Flask(__name__)
app.secret_key = os.environ.get("ADMIN_SECRET_KEY", "quizmaster-admin-control-center-secret-key-2026")

# Initialize database
with app.app_context():
    init_db()

# --- Admin Session Middleware & Security Guards ---

@app.before_request
def load_logged_in_admin():
    """Loads admin user from session before each request."""
    user_id = session.get("admin_id")
    if user_id is None:
        g.user = None
    else:
        conn = get_db_connection()
        g.user = conn.execute(
            "SELECT id, username, email, role, created_at FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        conn.close()

def admin_required(view):
    """Decorator to require administrator authentication."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None or g.user["role"] != "admin":
            flash("Administrator login required to access this control console.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(**kwargs)
    return wrapped_view

@app.context_processor
def inject_admin_globals():
    return dict(current_user=g.user)


# --- Admin Authentication Routes ---

@app.route("/")
def root():
    """Redirects to Admin Dashboard if authenticated, else to Admin Login."""
    if g.user and g.user["role"] == "admin":
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Dedicated Administrator Login."""
    if g.user and g.user["role"] == "admin":
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email_or_user = request.form.get("email_or_user", "").strip()
        password = request.form.get("password", "")

        if not email_or_user or not password:
            flash("Please enter administrator credentials.", "danger")
            return render_template("admin/login.html")

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ? OR username = ?",
            (email_or_user.lower(), email_or_user)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            if user["role"] != "admin":
                flash("Access Denied: This account does not have administrator privileges. Please use the Student Portal.", "danger")
                return render_template("admin/login.html")

            session.clear()
            session["admin_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            flash(f"Welcome to Admin Control Center, {user['username']}!", "success")
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid administrator credentials. Please verify your login.", "danger")

    return render_template("admin/login.html")


@app.route("/logout")
def logout():
    """Logs out admin and terminates secure session."""
    session.clear()
    flash("Administrator session terminated successfully.", "info")
    return redirect(url_for("login"))


# --- Admin Dashboard & Resource Management ---

@app.route("/dashboard")
@admin_required
def dashboard():
    """Admin Dashboard overview."""
    conn = get_db_connection()

    # System Metrics
    total_users = conn.execute("SELECT COUNT(*) AS c FROM users WHERE role = 'user'").fetchone()["c"]
    total_quizzes = conn.execute("SELECT COUNT(*) AS c FROM quizzes").fetchone()["c"]
    total_questions = conn.execute("SELECT COUNT(*) AS c FROM questions").fetchone()["c"]
    total_attempts = conn.execute("SELECT COUNT(*) AS c FROM results").fetchone()["c"]

    avg_score_res = conn.execute("SELECT AVG(percentage) AS avg_p FROM results").fetchone()["avg_p"]
    platform_avg = round(avg_score_res, 1) if avg_score_res is not None else 0

    # Quizzes list with question counts
    quizzes = conn.execute("""
        SELECT q.*, COUNT(ques.id) AS question_count
        FROM quizzes q
        LEFT JOIN questions ques ON q.id = ques.quiz_id
        GROUP BY q.id
        ORDER BY q.id ASC
    """).fetchall()

    # Recent Questions list
    questions = conn.execute("""
        SELECT ques.*, q.title AS quiz_title
        FROM questions ques
        JOIN quizzes q ON ques.quiz_id = q.id
        ORDER BY ques.id DESC
        LIMIT 10
    """).fetchall()

    # Recent Student Results
    recent_results = conn.execute("""
        SELECT r.*, u.username, u.email, q.title AS quiz_title
        FROM results r
        JOIN users u ON r.user_id = u.id
        JOIN quizzes q ON r.quiz_id = q.id
        ORDER BY r.date DESC
        LIMIT 8
    """).fetchall()

    conn.close()

    metrics = {
        "users": total_users,
        "quizzes": total_quizzes,
        "questions": total_questions,
        "attempts": total_attempts,
        "platform_avg": platform_avg
    }

    return render_template(
        "admin/dashboard.html",
        metrics=metrics,
        quizzes=quizzes,
        questions=questions,
        recent_results=recent_results
    )


# Admin Quiz Management
@app.route("/quiz/add", methods=["GET", "POST"])
@admin_required
def admin_add_quiz():
    """Create a new quiz."""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "General").strip()
        time_limit = int(request.form.get("time_limit", 10))
        icon = request.form.get("icon", "bi-journal-code").strip()

        if not title or not description:
            flash("Title and description are required.", "danger")
            return render_template("admin/quiz_form.html", action="Add")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO quizzes (title, description, category, time_limit, icon) VALUES (?, ?, ?, ?, ?)",
            (title, description, category, time_limit, icon)
        )
        conn.commit()
        conn.close()

        flash(f"Quiz '{title}' created successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("admin/quiz_form.html", action="Add", quiz=None)


@app.route("/quiz/edit/<int:quiz_id>", methods=["GET", "POST"])
@admin_required
def admin_edit_quiz(quiz_id):
    """Edit an existing quiz."""
    conn = get_db_connection()
    quiz = conn.execute("SELECT * FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()

    if not quiz:
        conn.close()
        flash("Quiz not found.", "danger")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "General").strip()
        time_limit = int(request.form.get("time_limit", 10))
        icon = request.form.get("icon", "bi-journal-code").strip()

        if not title or not description:
            flash("Title and description are required.", "danger")
            return render_template("admin/quiz_form.html", action="Edit", quiz=quiz)

        conn.execute(
            "UPDATE quizzes SET title = ?, description = ?, category = ?, time_limit = ?, icon = ? WHERE id = ?",
            (title, description, category, time_limit, icon, quiz_id)
        )
        conn.commit()
        conn.close()

        flash(f"Quiz '{title}' updated successfully!", "success")
        return redirect(url_for("dashboard"))

    conn.close()
    return render_template("admin/quiz_form.html", action="Edit", quiz=quiz)


@app.route("/quiz/delete/<int:quiz_id>", methods=["POST"])
@admin_required
def admin_delete_quiz(quiz_id):
    """Delete a quiz."""
    conn = get_db_connection()
    conn.execute("DELETE FROM quizzes WHERE id = ?", (quiz_id,))
    conn.commit()
    conn.close()
    flash("Quiz and its associated questions/results deleted successfully.", "info")
    return redirect(url_for("dashboard"))


# Admin Question Management
@app.route("/question/add", methods=["GET", "POST"])
@admin_required
def admin_add_question():
    """Add a new question."""
    conn = get_db_connection()
    quizzes = conn.execute("SELECT id, title FROM quizzes ORDER BY title ASC").fetchall()

    if request.method == "POST":
        quiz_id = request.form.get("quiz_id")
        question = request.form.get("question", "").strip()
        opt_a = request.form.get("option_a", "").strip()
        opt_b = request.form.get("option_b", "").strip()
        opt_c = request.form.get("option_c", "").strip()
        opt_d = request.form.get("option_d", "").strip()
        correct_answer = request.form.get("correct_answer", "").strip().upper()
        explanation = request.form.get("explanation", "").strip()

        if not all([quiz_id, question, opt_a, opt_b, opt_c, opt_d, correct_answer]):
            flash("All question fields and correct answer are required.", "danger")
            return render_template("admin/question_form.html", action="Add", quizzes=quizzes, pre_selected_quiz=quiz_id)

        conn.execute("""
            INSERT INTO questions (quiz_id, question, option_a, option_b, option_c, option_d, correct_answer, explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (quiz_id, question, opt_a, opt_b, opt_c, opt_d, correct_answer, explanation))
        conn.commit()
        conn.close()

        flash("Question added successfully!", "success")
        return redirect(url_for("dashboard"))

    pre_selected_quiz = request.args.get("quiz_id", "")
    conn.close()
    return render_template("admin/question_form.html", action="Add", quizzes=quizzes, question=None, pre_selected_quiz=pre_selected_quiz)


@app.route("/question/edit/<int:question_id>", methods=["GET", "POST"])
@admin_required
def admin_edit_question(question_id):
    """Edit an existing question."""
    conn = get_db_connection()
    question = conn.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
    quizzes = conn.execute("SELECT id, title FROM quizzes ORDER BY title ASC").fetchall()

    if not question:
        conn.close()
        flash("Question not found.", "danger")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        quiz_id = request.form.get("quiz_id")
        q_text = request.form.get("question", "").strip()
        opt_a = request.form.get("option_a", "").strip()
        opt_b = request.form.get("option_b", "").strip()
        opt_c = request.form.get("option_c", "").strip()
        opt_d = request.form.get("option_d", "").strip()
        correct_answer = request.form.get("correct_answer", "").strip().upper()
        explanation = request.form.get("explanation", "").strip()

        if not all([quiz_id, q_text, opt_a, opt_b, opt_c, opt_d, correct_answer]):
            flash("All fields are required.", "danger")
            return render_template("admin/question_form.html", action="Edit", quizzes=quizzes, question=question)

        conn.execute("""
            UPDATE questions
            SET quiz_id = ?, question = ?, option_a = ?, option_b = ?, option_c = ?, option_d = ?, correct_answer = ?, explanation = ?
            WHERE id = ?
        """, (quiz_id, q_text, opt_a, opt_b, opt_c, opt_d, correct_answer, explanation, question_id))
        conn.commit()
        conn.close()

        flash("Question updated successfully!", "success")
        return redirect(url_for("dashboard"))

    conn.close()
    return render_template("admin/question_form.html", action="Edit", quizzes=quizzes, question=question)


@app.route("/question/delete/<int:question_id>", methods=["POST"])
@admin_required
def admin_delete_question(question_id):
    """Delete a question."""
    conn = get_db_connection()
    conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    conn.commit()
    conn.close()
    flash("Question deleted successfully.", "info")
    return redirect(url_for("dashboard"))


# Admin Users & Results List
@app.route("/users")
@admin_required
def admin_users():
    """List all registered users with their participation stats."""
    conn = get_db_connection()
    users = conn.execute("""
        SELECT u.*, COUNT(r.id) AS total_quizzes, AVG(r.percentage) AS avg_score
        FROM users u
        LEFT JOIN results r ON u.id = r.user_id
        GROUP BY u.id
        ORDER BY u.created_at DESC
    """).fetchall()
    conn.close()
    return render_template("admin/users.html", users=users)


@app.route("/user/toggle-role/<int:user_id>", methods=["POST"])
@admin_required
def admin_toggle_role(user_id):
    """Toggle user role between user and admin."""
    if user_id == g.user["id"]:
        flash("You cannot change your own role.", "warning")
        return redirect(url_for("admin_users"))

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if user:
        new_role = "user" if user["role"] == "admin" else "admin"
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
        conn.commit()
        flash(f"User '{user['username']}' role updated to '{new_role}'.", "success")
    conn.close()
    return redirect(url_for("admin_users"))


@app.route("/user/delete/<int:user_id>", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    """Delete a user account."""
    if user_id == g.user["id"]:
        flash("You cannot delete your own account while logged in.", "danger")
        return redirect(url_for("admin_users"))

    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    flash("User account deleted successfully.", "info")
    return redirect(url_for("admin_users"))


@app.route("/results")
@admin_required
def admin_results():
    """View and filter all quiz attempts across the platform."""
    search_query = request.args.get("search", "").strip()
    quiz_filter = request.args.get("quiz_id", "")

    conn = get_db_connection()
    quizzes = conn.execute("SELECT id, title FROM quizzes ORDER BY title ASC").fetchall()

    sql = """
        SELECT r.*, u.username, u.email, q.title AS quiz_title
        FROM results r
        JOIN users u ON r.user_id = u.id
        JOIN quizzes q ON r.quiz_id = q.id
        WHERE 1=1
    """
    params = []

    if search_query:
        sql += " AND (u.username LIKE ? OR u.email LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])

    if quiz_filter:
        sql += " AND r.quiz_id = ?"
        params.append(quiz_filter)

    sql += " ORDER BY r.date DESC"
    results = conn.execute(sql, params).fetchall()
    conn.close()

    return render_template(
        "admin/results.html",
        results=results,
        quizzes=quizzes,
        search_query=search_query,
        quiz_filter=quiz_filter
    )


# --- Error Handlers ---

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


if __name__ == "__main__":
    port = int(os.environ.get("ADMIN_PORT", 5001))
    print(f"🛡️ QuizMaster Admin Control Center running at http://127.0.0.1:{port}")
    app.run(debug=True, port=port)
