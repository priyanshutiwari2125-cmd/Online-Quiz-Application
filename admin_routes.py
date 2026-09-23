from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from database import get_db_connection
from decorators import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/dashboard")
@admin_required
def admin_dashboard():
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
@admin_bp.route("/quiz/add", methods=["GET", "POST"])
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
        return redirect(url_for("admin.admin_dashboard"))

    return render_template("admin/quiz_form.html", action="Add", quiz=None)


@admin_bp.route("/quiz/edit/<int:quiz_id>", methods=["GET", "POST"])
@admin_required
def admin_edit_quiz(quiz_id):
    """Edit an existing quiz."""
    conn = get_db_connection()
    quiz = conn.execute("SELECT * FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()

    if not quiz:
        conn.close()
        flash("Quiz not found.", "danger")
        return redirect(url_for("admin.admin_dashboard"))

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
        return redirect(url_for("admin.admin_dashboard"))

    conn.close()
    return render_template("admin/quiz_form.html", action="Edit", quiz=quiz)


@admin_bp.route("/quiz/delete/<int:quiz_id>", methods=["POST"])
@admin_required
def admin_delete_quiz(quiz_id):
    """Delete a quiz."""
    conn = get_db_connection()
    conn.execute("DELETE FROM quizzes WHERE id = ?", (quiz_id,))
    conn.commit()
    conn.close()
    flash("Quiz and its associated questions/results deleted successfully.", "info")
    return redirect(url_for("admin.admin_dashboard"))


# Admin Question Management
@admin_bp.route("/question/add", methods=["GET", "POST"])
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
        return redirect(url_for("admin.admin_dashboard"))

    pre_selected_quiz = request.args.get("quiz_id", "")
    conn.close()
    return render_template("admin/question_form.html", action="Add", quizzes=quizzes, question=None, pre_selected_quiz=pre_selected_quiz)


@admin_bp.route("/question/edit/<int:question_id>", methods=["GET", "POST"])
@admin_required
def admin_edit_question(question_id):
    """Edit an existing question."""
    conn = get_db_connection()
    question = conn.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
    quizzes = conn.execute("SELECT id, title FROM quizzes ORDER BY title ASC").fetchall()

    if not question:
        conn.close()
        flash("Question not found.", "danger")
        return redirect(url_for("admin.admin_dashboard"))

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
        return redirect(url_for("admin.admin_dashboard"))

    conn.close()
    return render_template("admin/question_form.html", action="Edit", quizzes=quizzes, question=question)


@admin_bp.route("/question/delete/<int:question_id>", methods=["POST"])
@admin_required
def admin_delete_question(question_id):
    """Delete a question."""
    conn = get_db_connection()
    conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    conn.commit()
    conn.close()
    flash("Question deleted successfully.", "info")
    return redirect(url_for("admin.admin_dashboard"))


# Admin Users & Results List
@admin_bp.route("/users")
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


@admin_bp.route("/user/toggle-role/<int:user_id>", methods=["POST"])
@admin_required
def admin_toggle_role(user_id):
    """Toggle user role between user and admin."""
    if user_id == g.user["id"]:
        flash("You cannot change your own role.", "warning")
        return redirect(url_for("admin.admin_users"))

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if user:
        new_role = "user" if user["role"] == "admin" else "admin"
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
        conn.commit()
        flash(f"User '{user['username']}' role updated to '{new_role}'.", "success")
    conn.close()
    return redirect(url_for("admin.admin_users"))


@admin_bp.route("/user/delete/<int:user_id>", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    """Delete a user account."""
    if user_id == g.user["id"]:
        flash("You cannot delete your own account while logged in.", "danger")
        return redirect(url_for("admin.admin_users"))

    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    flash("User account deleted successfully.", "info")
    return redirect(url_for("admin.admin_users"))


@admin_bp.route("/results")
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
