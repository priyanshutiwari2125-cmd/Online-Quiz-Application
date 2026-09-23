import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, abort
from database import get_db_connection
from decorators import login_required

student_bp = Blueprint("student", __name__)

@student_bp.route("/dashboard")
@login_required
def dashboard():
    """Student Dashboard with statistics, available quizzes, and attempt history."""
    # If an admin lands here, guide them to their dedicated control center
    if g.user["role"] == "admin":
        flash("Logged in as Administrator. Redirected to Admin Management Console.", "info")
        return redirect(url_for("admin.admin_dashboard"))

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


@student_bp.route("/quiz/<int:quiz_id>")
@login_required
def take_quiz(quiz_id):
    """Quiz taking interface for students."""
    conn = get_db_connection()
    quiz = conn.execute("SELECT * FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()

    if not quiz:
        conn.close()
        flash("Quiz not found.", "danger")
        return redirect(url_for("student.dashboard"))

    questions = conn.execute("SELECT * FROM questions WHERE quiz_id = ? ORDER BY id ASC", (quiz_id,)).fetchall()
    conn.close()

    if not questions:
        flash("This quiz currently has no questions. Please try another quiz.", "warning")
        return redirect(url_for("student.dashboard"))

    return render_template("student/quiz.html", quiz=quiz, questions=questions, total_questions=len(questions))


@student_bp.route("/quiz/<int:quiz_id>/submit", methods=["POST"])
@login_required
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
        return redirect(url_for("student.dashboard"))

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
    return redirect(url_for("student.view_result", result_id=result_id))


@student_bp.route("/result/<int:result_id>")
@login_required
def view_result(result_id):
    """Displays detailed score and question-by-question review for student."""
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
        return redirect(url_for("student.dashboard"))

    # Only owner or admin can view result
    if result["user_id"] != g.user["id"] and g.user["role"] != "admin":
        conn.close()
        flash("Unauthorized to view this result.", "danger")
        return redirect(url_for("student.dashboard"))

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


@student_bp.route("/leaderboard")
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
