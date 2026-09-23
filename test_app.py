import unittest
import uuid
from student_app import app as student_app
from admin_app import app as admin_app
from database import init_db, get_db_connection

class StudentAppTestCase(unittest.TestCase):
    def setUp(self):
        student_app.config['TESTING'] = True
        student_app.config['WTF_CSRF_ENABLED'] = False
        self.client = student_app.test_client()
        init_db()

    def tearDown(self):
        with self.client.session_transaction() as sess:
            sess.clear()

    def test_student_home_and_login(self):
        """Test student landing page and student login."""
        res_home = self.client.get('/')
        self.assertEqual(res_home.status_code, 200)
        self.assertIn(b'QuizMaster', res_home.data)

        # Login as student
        res_login = self.client.post('/login', data=dict(
            email_or_user='rahul@gmail.com',
            password='rahul123'
        ), follow_redirects=True)
        self.assertEqual(res_login.status_code, 200)
        self.assertIn(b'Welcome, Rahul', res_login.data)
        self.assertIn(b'Student Portal', res_login.data)

    def test_student_quiz_flow(self):
        """Test taking a quiz and viewing result in the student app."""
        self.client.post('/login', data=dict(
            email_or_user='rahul@gmail.com',
            password='rahul123'
        ), follow_redirects=True)

        conn = get_db_connection()
        quiz = conn.execute("SELECT * FROM quizzes LIMIT 1").fetchone()
        quiz_id = quiz["id"] if quiz else 1
        questions = conn.execute("SELECT id, correct_answer FROM questions WHERE quiz_id = ?", (quiz_id,)).fetchall()
        conn.close()

        res_quiz = self.client.get(f'/quiz/{quiz_id}')
        self.assertEqual(res_quiz.status_code, 200)
        self.assertIn(quiz["title"].encode() if quiz else b'Python', res_quiz.data)

        # Submit answers
        submission_data = {f"question_{q['id']}": q['correct_answer'] for q in questions}
        res_submit = self.client.post(f'/quiz/{quiz_id}/submit', data=submission_data, follow_redirects=True)
        self.assertEqual(res_submit.status_code, 200)
        self.assertIn(b'Results', res_submit.data)
        self.assertIn(b'Detailed Question Review', res_submit.data)

    def test_student_registration(self):
        """Test student account creation."""
        suffix = uuid.uuid4().hex[:6]
        res = self.client.post('/register', data=dict(
            username=f'Student_{suffix}',
            email=f'student_{suffix}@test.com',
            password='password123',
            confirm_password='password123'
        ), follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Student Dashboard', res.data)


class AdminAppTestCase(unittest.TestCase):
    def setUp(self):
        admin_app.config['TESTING'] = True
        admin_app.config['WTF_CSRF_ENABLED'] = False
        self.client = admin_app.test_client()
        init_db()

    def tearDown(self):
        with self.client.session_transaction() as sess:
            sess.clear()

    def test_admin_access_control(self):
        """Test that regular students cannot log in to the admin app."""
        # Student trying to log into Admin app
        res_student_attempt = self.client.post('/login', data=dict(
            email_or_user='rahul@gmail.com',
            password='rahul123'
        ), follow_redirects=True)
        self.assertIn(b'Access Denied', res_student_attempt.data)

        # Unauthenticated access to dashboard redirects to login
        res_dash = self.client.get('/dashboard', follow_redirects=True)
        self.assertIn(b'Administrator login required', res_dash.data)

    def test_admin_login_and_management(self):
        """Test admin login, dashboard, and quiz creation."""
        # Admin login
        res_login = self.client.post('/login', data=dict(
            email_or_user='admin@quizmaster.com',
            password='admin123'
        ), follow_redirects=True)
        self.assertEqual(res_login.status_code, 200)
        self.assertIn(b'Admin Management Console', res_login.data)
        self.assertIn(b'Active Quizzes', res_login.data)

        # Add quiz
        res_add = self.client.post('/quiz/add', data=dict(
            title='Django Framework Mastery',
            description='Test models, views, and templates in Django',
            category='Django',
            time_limit=20,
            icon='bi-globe'
        ), follow_redirects=True)
        self.assertEqual(res_add.status_code, 200)
        self.assertIn(b'Django Framework Mastery', res_add.data)

if __name__ == '__main__':
    unittest.main()
