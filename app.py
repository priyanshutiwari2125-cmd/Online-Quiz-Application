import os
import sys
import threading
import time
from student_app import app as student_app
from admin_app import app as admin_app

def run_student_server():
    student_app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

def run_admin_server():
    admin_app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)

if __name__ == "__main__":
    print("=" * 65)
    print("QUIZMASTER: DUAL SEPARATE APPLICATION SERVERS RUNNING")
    print("=" * 65)
    print("Student Application:      http://127.0.0.1:5000")
    print("   -> Student Login:       http://127.0.0.1:5000/login")
    print("   -> Demo Credentials:    rahul@gmail.com / rahul123")
    print()
    print("Admin Application:        http://127.0.0.1:5001")
    print("   -> Admin Login:         http://127.0.0.1:5001/login")
    print("   -> Demo Credentials:    admin@quizmaster.com / admin123")
    print("=" * 65)

    student_thread = threading.Thread(target=run_student_server, daemon=True)
    admin_thread = threading.Thread(target=run_admin_server, daemon=True)

    student_thread.start()
    admin_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping application servers...")
        sys.exit(0)
