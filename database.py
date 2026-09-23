import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_NAME = "database.db"

def get_db_connection():
    """Establishes and returns a connection to SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Initializes tables and seeds starting data if database is empty."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 2. Quizzes Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quizzes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT DEFAULT 'General',
        time_limit INTEGER DEFAULT 10,
        icon TEXT DEFAULT 'bi-terminal',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 3. Questions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id INTEGER NOT NULL,
        question TEXT NOT NULL,
        option_a TEXT NOT NULL,
        option_b TEXT NOT NULL,
        option_c TEXT NOT NULL,
        option_d TEXT NOT NULL,
        correct_answer TEXT NOT NULL,
        explanation TEXT,
        FOREIGN KEY (quiz_id) REFERENCES quizzes (id) ON DELETE CASCADE
    )
    """)

    # 4. Results Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        quiz_id INTEGER NOT NULL,
        score INTEGER NOT NULL,
        total INTEGER NOT NULL,
        percentage REAL NOT NULL,
        answers_json TEXT,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (quiz_id) REFERENCES quizzes (id) ON DELETE CASCADE
    )
    """)

    conn.commit()

    # Check if admin user already exists; if not, seed data
    cursor.execute("SELECT COUNT(*) as count FROM users")
    user_count = cursor.fetchone()["count"]

    if user_count == 0:
        # Seed Admin & Sample User
        admin_pass = generate_password_hash("admin123")
        user_pass = generate_password_hash("rahul123")

        cursor.execute(
            "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
            ("Admin", "admin@quizmaster.com", admin_pass, "admin")
        )
        cursor.execute(
            "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
            ("Rahul", "rahul@gmail.com", user_pass, "user")
        )
        conn.commit()

    # Check if quizzes exist
    cursor.execute("SELECT COUNT(*) as count FROM quizzes")
    quiz_count = cursor.fetchone()["count"]

    if quiz_count == 0:
        # 1. Python Basics Quiz
        cursor.execute(
            "INSERT INTO quizzes (title, description, category, time_limit, icon) VALUES (?, ?, ?, ?, ?)",
            (
                "Python Basics",
                "Test your foundational knowledge in Python syntax, data types, control structures, and built-in functions.",
                "Python",
                10,
                "bi-filetype-py"
            )
        )
        quiz_1_id = cursor.lastrowid

        python_questions = [
            (
                quiz_1_id,
                "Which keyword is used to define a function in Python?",
                "function",
                "def",
                "define",
                "func",
                "B",
                "In Python, 'def' is the keyword used to define a function."
            ),
            (
                quiz_1_id,
                "Which data type is immutable in Python?",
                "List",
                "Dictionary",
                "Tuple",
                "Set",
                "C",
                "Tuples are immutable sequences in Python; their elements cannot be modified after creation."
            ),
            (
                quiz_1_id,
                "What is the output of `type(5 / 2)` in Python 3?",
                "<class 'int'>",
                "<class 'float'>",
                "<class 'double'>",
                "<class 'number'>",
                "B",
                "The `/` operator in Python 3 performs true division and returns a float (2.5)."
            ),
            (
                quiz_1_id,
                "Which symbol is used for single-line comments in Python?",
                "//",
                "/*",
                "#",
                "--",
                "C",
                "In Python, the hash `#` symbol starts a single-line comment."
            ),
            (
                quiz_1_id,
                "How do you insert an element at the end of a list named `items`?",
                "items.add(5)",
                "items.insert_last(5)",
                "items.append(5)",
                "items.push(5)",
                "C",
                "The `.append()` method is used to add an item to the end of a list."
            ),
            (
                quiz_1_id,
                "Which built-in function returns the number of items in an object?",
                "length()",
                "count()",
                "size()",
                "len()",
                "D",
                "`len()` is the built-in function that returns length or count of items in sequences and mappings."
            ),
            (
                quiz_1_id,
                "What is the correct file extension for Python source files?",
                ".pyt",
                ".pt",
                ".py",
                ".python",
                "C",
                "Python source code files use the `.py` extension."
            ),
            (
                quiz_1_id,
                "What will `bool([])` evaluate to in Python?",
                "True",
                "False",
                "None",
                "Error",
                "B",
                "Empty collections like `[]`, `{}`, `()`, `\"\"` evaluate to False in a boolean context."
            ),
            (
                quiz_1_id,
                "Which statement is used to handle exceptions in Python?",
                "try ... catch",
                "try ... except",
                "do ... catch",
                "try ... handle",
                "B",
                "Python uses `try` and `except` blocks for structured exception handling."
            ),
            (
                quiz_1_id,
                "Which built-in Python module is used to work with SQLite databases without installing third-party packages?",
                "mysqldb",
                "pysql",
                "sqlite3",
                "sqlitelib",
                "C",
                "`sqlite3` is a built-in Python standard library module for SQLite database interaction."
            )
        ]

        cursor.executemany("""
            INSERT INTO questions (quiz_id, question, option_a, option_b, option_c, option_d, correct_answer, explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, python_questions)

        # 2. Flask Web Framework Quiz
        cursor.execute(
            "INSERT INTO quizzes (title, description, category, time_limit, icon) VALUES (?, ?, ?, ?, ?)",
            (
                "Flask Basics",
                "Assess your understanding of Flask routing, templates (Jinja2), HTTP methods, sessions, and request handling.",
                "Web Framework",
                10,
                "bi-globe"
            )
        )
        quiz_2_id = cursor.lastrowid

        flask_questions = [
            (
                quiz_2_id,
                "What classification best describes the Flask framework?",
                "Full-stack Monolith",
                "Microframework",
                "CMS Framework",
                "Frontend Library",
                "B",
                "Flask is known as a microframework because it keeps the core simple but extensible."
            ),
            (
                quiz_2_id,
                "Which templating engine is used by default in Flask?",
                "Django Templates",
                "EJS",
                "Jinja2",
                "Mustache",
                "C",
                "Flask comes pre-configured with the Jinja2 templating engine."
            ),
            (
                quiz_2_id,
                "What decorator is used in Flask to bind a function to a URL route?",
                "@app.route()",
                "@app.url()",
                "@app.path()",
                "@app.bind()",
                "A",
                "`@app.route('/path')` is the standard decorator used to define URL endpoints in Flask."
            ),
            (
                quiz_2_id,
                "By default, which HTTP methods does a Flask route respond to?",
                "GET and POST",
                "GET only",
                "POST only",
                "ALL methods",
                "B",
                "By default, a Flask route only answers to GET requests unless `methods=['GET', 'POST']` is specified."
            ),
            (
                quiz_2_id,
                "Where does Flask look for HTML template files by default?",
                "static/",
                "views/",
                "templates/",
                "public/",
                "C",
                "Flask automatically searches inside the `templates/` folder for HTML template rendering."
            ),
            (
                quiz_2_id,
                "Which function is used to render an HTML file with context variables in Flask?",
                "render_view()",
                "render_template()",
                "display_html()",
                "send_template()",
                "B",
                "`render_template('index.html', ...)` is the standard Flask function to render Jinja2 templates."
            ),
            (
                quiz_2_id,
                "How do you access form data sent via POST in a Flask view?",
                "request.args['field']",
                "request.form['field']",
                "request.data['field']",
                "request.post['field']",
                "B",
                "`request.form` contains data submitted via POST/form-encoded requests."
            ),
            (
                quiz_2_id,
                "Which object is used in Flask to store data across multiple requests for a specific user?",
                "session",
                "cache",
                "storage",
                "cookie_jar",
                "A",
                "The `session` object in Flask allows storing data across requests using cryptographically signed cookies."
            ),
            (
                quiz_2_id,
                "What Flask function generates a URL for a given view function name?",
                "url_for()",
                "get_url()",
                "create_link()",
                "redirect_to()",
                "A",
                "`url_for('endpoint_name')` generates dynamic URLs based on function names."
            ),
            (
                quiz_2_id,
                "What is required to be configured on the Flask app to use sessions securely?",
                "app.config['DATABASE']",
                "app.secret_key",
                "app.debug_key",
                "app.security_token",
                "B",
                "`app.secret_key` is required to sign session cookies and protect against tampering."
            )
        ]

        cursor.executemany("""
            INSERT INTO questions (quiz_id, question, option_a, option_b, option_c, option_d, correct_answer, explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, flask_questions)

        # 3. Open Source & Computer Science Fundamentals Quiz
        cursor.execute(
            "INSERT INTO quizzes (title, description, category, time_limit, icon) VALUES (?, ?, ?, ?, ?)",
            (
                "Open Source & CS Fundamentals",
                "Explore open-source software principles, licenses, version control (Git), and general computer science concepts.",
                "Open Source",
                10,
                "bi-git"
            )
        )
        quiz_3_id = cursor.lastrowid

        os_questions = [
            (
                quiz_3_id,
                "Which license is a popular permissive open-source license that allows commercial use with minimal restrictions?",
                "GPL v3",
                "MIT License",
                "Proprietary EULA",
                "Creative Commons Non-Commercial",
                "B",
                "The MIT License is a very permissive open-source license that allows reuse, modification, and commercial distribution."
            ),
            (
                quiz_3_id,
                "What command is used to record repository changes locally in Git?",
                "git push",
                "git add",
                "git commit",
                "git record",
                "C",
                "`git commit -m 'message'` saves staged changes into the local git repository history."
            ),
            (
                quiz_3_id,
                "SQLite is what type of Database Management System?",
                "Client-Server Distributed RDBMS",
                "Serverless, Self-Contained SQL Database Engine",
                "NoSQL Key-Value Store",
                "Graph Database",
                "B",
                "SQLite is a serverless, zero-configuration, transactional SQL database engine stored in a single disk file."
            ),
            (
                quiz_3_id,
                "Which protocol is used for secure communication over a computer network in web browsers?",
                "HTTP",
                "FTP",
                "HTTPS",
                "SMTP",
                "C",
                "HTTPS (HTTP Secure) uses TLS/SSL encryption to secure communications over the Internet."
            ),
            (
                quiz_3_id,
                "In Python, what package manager is used to download and install packages from PyPI?",
                "npm",
                "pip",
                "gem",
                "cargo",
                "B",
                "`pip` is the standard package installer for Python."
            ),
            (
                quiz_3_id,
                "What does MVC stand for in software architecture?",
                "Model-View-Controller",
                "Multi-Value-Collection",
                "Main-Visual-Component",
                "Modular-Virtual-Container",
                "A",
                "MVC stands for Model-View-Controller, an architectural pattern that separates data, UI, and control logic."
            ),
            (
                quiz_3_id,
                "Which HTTP status code signifies that a requested resource was not found?",
                "200",
                "301",
                "404",
                "500",
                "C",
                "HTTP status 404 indicates 'Not Found' on the server."
            ),
            (
                quiz_3_id,
                "What data format uses key-value pairs and is widely used for web APIs and configuration?",
                "XML",
                "JSON",
                "CSV",
                "YAML",
                "B",
                "JSON (JavaScript Object Notation) is a lightweight text-based format for data interchange."
            ),
            (
                quiz_3_id,
                "What is a virtual environment in Python used for?",
                "Running code in virtual machines (VMs)",
                "Isolating project dependencies and package versions",
                "Encrypting Python bytecode",
                "Simulating CPU speeds",
                "B",
                "Python virtual environments (`venv`) isolate dependencies and avoid package version conflicts between projects."
            ),
            (
                quiz_3_id,
                "Which organization maintains the official definition of 'Open Source' software?",
                "W3C",
                "Open Source Initiative (OSI)",
                "Apache Software Foundation",
                "Free Software Foundation (FSF)",
                "B",
                "The Open Source Initiative (OSI) maintains the Open Source Definition and approves compliant licenses."
            )
        ]

        cursor.executemany("""
            INSERT INTO questions (quiz_id, question, option_a, option_b, option_c, option_d, correct_answer, explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, os_questions)

        conn.commit()

    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully with schema and seed data.")
