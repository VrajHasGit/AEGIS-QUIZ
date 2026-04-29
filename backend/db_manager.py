import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'database', 'aegis_quiz.db')

def setup_database():
    print(f"Initializing SQLite database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create Teachers
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Create Quizzes
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS quizzes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        topic TEXT,
        access_code TEXT NOT NULL UNIQUE,
        duration_minutes INTEGER DEFAULT 30,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE
    )
    ''')

    # Create Questions
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id INTEGER NOT NULL,
        question_text TEXT NOT NULL,
        option_a TEXT NOT NULL,
        option_b TEXT NOT NULL,
        option_c TEXT NOT NULL,
        option_d TEXT NOT NULL,
        correct_answer TEXT NOT NULL,
        FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
    )
    ''')

    # Create Exam Sessions
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS exam_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id INTEGER NOT NULL,
        student_name TEXT NOT NULL,
        status TEXT DEFAULT 'waiting',
        score REAL DEFAULT NULL,
        violation_count INTEGER DEFAULT 0,
        responses TEXT DEFAULT NULL,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
    )
    ''')

    # Check if admin exists
    cursor.execute("SELECT id FROM teachers WHERE email = 'admin@cluely.ai'")
    if not cursor.fetchone():
        # Using a dummy hash for now, but in real app we'd use werkzeug
        cursor.execute("INSERT INTO teachers (username, email, password_hash) VALUES (?, ?, ?)",
                       ('Admin Teacher', 'admin@cluely.ai', 'admin123'))
    
    conn.commit()
    conn.close()
    print("Database setup complete.")

if __name__ == "__main__":
    setup_database()
