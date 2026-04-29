import os
import json
import uuid
import sqlite3
import random
import string
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_socketio import SocketIO, emit, join_room
from ai_engine import generate_quiz_data 
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')

app = Flask(__name__, 
            template_folder=os.path.join(FRONTEND_DIR, 'templates'),
            static_folder=os.path.join(FRONTEND_DIR, 'static'))

app.secret_key = os.getenv("FLASK_SECRET_KEY", "cluely_super_secret_key_123")
socketio = SocketIO(app, cors_allowed_origins="*")

DB_PATH = os.path.join(BASE_DIR, 'database', 'aegis_quiz.db')

# --- ERROR HANDLERS ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html',
        error_code=404,
        error_title='Page Not Found',
        error_message='The page you are looking for does not exist or has been moved.',
        action_url='/',
        action_text='← Go Home'
    ), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('error.html',
        error_code=500,
        error_title='Internal Server Error',
        error_message='Something went wrong on our end. Please try again later or contact your administrator.',
        action_url='/',
        action_text='← Go Home'
    ), 500

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html',
        error_code=403,
        error_title='Access Denied',
        error_message='You do not have permission to access this resource.',
        action_url='/',
        action_text='← Go Home'
    ), 403

# --- Database Connection (SQLite) ---
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enables dict-like access: row['column']
    return conn

# --- AUTH & DASHBOARD ---
@app.route('/')
def index():
    if 'teacher_id' in session: return redirect(url_for('dashboard'))
    return render_template('auth/login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM teachers WHERE email = ?", (email,))
    teacher = cursor.fetchone()
    db.close()
    
    if teacher:
        # Check password hash (fallback to plain text for the default admin account if not yet hashed)
        if check_password_hash(teacher['password_hash'], password) or teacher['password_hash'] == password:
            session['teacher_id'] = teacher['id']
            session['teacher_name'] = teacher['username']
            return redirect(url_for('dashboard'))
            
    return render_template('error.html',
            error_code=401,
            error_title='Login Failed',
            error_message='Invalid email or password. Please check your credentials and try again.',
            action_url='/',
            action_text='← Try Again'
        ), 401

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm = request.form.get('confirm_password')
    
    if not all([username, email, password, confirm]):
        flash('All fields are required.', 'error')
        return redirect(url_for('index'))
    
    if password != confirm:
        flash('Passwords do not match.', 'error')
        return redirect(url_for('index'))
    
    if len(password) < 6:
        flash('Password must be at least 6 characters.', 'error')
        return redirect(url_for('index'))
    
    db = get_db()
    cursor = db.cursor()
    
    # Check if email already exists
    cursor.execute("SELECT id FROM teachers WHERE email = ?", (email,))
    if cursor.fetchone():
        db.close()
        flash('An account with this email already exists.', 'error')
        return redirect(url_for('index'))
    
    # Create the teacher account with hashed password
    hashed_pw = generate_password_hash(password)
    cursor.execute("INSERT INTO teachers (username, email, password_hash) VALUES (?, ?, ?)",
                   (username, email, hashed_pw))
    db.commit()
    db.close()
    
    flash('Account created successfully! Please sign in.', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'teacher_id' not in session:
        return redirect(url_for('index'))
    
    db = get_db()
    cursor = db.cursor()
    
    # Fetch quizzes for this specific teacher
    # SQLite subquery for count
    query = """
        SELECT q.id, q.title, q.access_code, 
        (SELECT COUNT(*) FROM exam_sessions WHERE quiz_id = q.id) as student_count
        FROM quizzes q 
        WHERE q.teacher_id = ?
        ORDER BY q.id DESC
    """
    cursor.execute(query, (session['teacher_id'],))
    quizzes = cursor.fetchall()
    db.close()
    
    return render_template('teacher/dashboard.html', quizzes=quizzes)

# --- QUIZ GENERATION (AI) ---
@app.route('/api/generate', methods=['POST'])
def handle_ai_generation():
    if 'teacher_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    try:
        data = request.json
        topic, count = data.get('topic'), data.get('num_questions')
        duration = data.get('duration', 30)
        quiz_data = generate_quiz_data(topic, count)
        if not quiz_data: return jsonify({"status": "error", "message": "AI failed"}), 500
        
        db = get_db()
        cursor = db.cursor()
        access_code = str(uuid.uuid4())[:8].upper()
        cursor.execute("INSERT INTO quizzes (teacher_id, title, topic, access_code, duration_minutes) VALUES (?, ?, ?, ?, ?)",
                       (session['teacher_id'], f"{topic} Quiz", topic, access_code, duration))
        quiz_id = cursor.lastrowid
        
        for q in quiz_data:
            cursor.execute("""INSERT INTO questions 
                (quiz_id, question_text, option_a, option_b, option_c, option_d, correct_answer) 
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (quiz_id, q.get('question_text'), q.get('option_a'), q.get('option_b'), 
                 q.get('option_c'), q.get('option_d'), q.get('correct_answer')))
        db.commit()
        db.close()
        return jsonify({"status": "success", "code": access_code})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- DELETE QUIZ ---
@app.route('/api/quiz/<int:quiz_id>', methods=['DELETE'])
def delete_quiz(quiz_id):
    if 'teacher_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    
    db = get_db()
    cursor = db.cursor()
    
    # Verify teacher owns this quiz
    cursor.execute("SELECT id FROM quizzes WHERE id = ? AND teacher_id = ?", (quiz_id, session['teacher_id']))
    quiz = cursor.fetchone()
    if not quiz:
        db.close()
        return jsonify({"status": "error", "message": "Quiz not found or access denied"}), 404
    
    # SQLite cascade delete (if enabled) or manual
    cursor.execute("DELETE FROM exam_sessions WHERE quiz_id = ?", (quiz_id,))
    cursor.execute("DELETE FROM questions WHERE quiz_id = ?", (quiz_id,))
    cursor.execute("DELETE FROM quizzes WHERE id = ?", (quiz_id,))
    db.commit()
    db.close()
    
    return jsonify({"status": "success", "message": "Quiz deleted"})

@app.route('/teacher/create-manual', methods=['GET', 'POST'])
def create_manual():
    if 'teacher_id' not in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form.get('quiz_title')
        topic = request.form.get('topic')
        duration = request.form.get('duration')
        
        db = get_db()
        cursor = db.cursor()
        access_code = str(uuid.uuid4())[:8].upper()
        
        cursor.execute("INSERT INTO quizzes (teacher_id, title, topic, access_code, duration_minutes) VALUES (?, ?, ?, ?, ?)",
                       (session['teacher_id'], title, topic, access_code, duration))
        quiz_id = cursor.lastrowid
        
        questions = request.form.getlist('question[]')
        opt_as = request.form.getlist('opt_a[]')
        opt_bs = request.form.getlist('opt_b[]')
        opt_cs = request.form.getlist('opt_c[]')
        opt_ds = request.form.getlist('opt_d[]')
        answers = request.form.getlist('correct[]')
        
        for i in range(len(questions)):
            cursor.execute("""INSERT INTO questions 
                (quiz_id, question_text, option_a, option_b, option_c, option_d, correct_answer) 
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (quiz_id, questions[i], opt_as[i], opt_bs[i], opt_cs[i], opt_ds[i], answers[i]))
        
        db.commit()
        db.close()
        return redirect(url_for('dashboard'))

    return render_template('teacher/manual_builder.html')

@app.route('/teacher/monitor/<int:quiz_id>')
def monitor_quiz(quiz_id):
    if 'teacher_id' not in session: return redirect(url_for('index'))
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT title, access_code, duration_minutes FROM quizzes WHERE id = ?", (quiz_id,))
    quiz = cursor.fetchone()
    
    cursor.execute("""
        SELECT id, student_name, status, score, violation_count 
        FROM exam_sessions 
        WHERE quiz_id = ?
    """, (quiz_id,))
    students = cursor.fetchall()
    db.close()
    
    return render_template('teacher/monitor.html', quiz=quiz, students=students, quiz_id=quiz_id)

@app.route('/teacher/review/<int:quiz_id>')
def review_quiz(quiz_id):
    if 'teacher_id' not in session: return redirect(url_for('index'))
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, title, topic, access_code FROM quizzes WHERE id = ? AND teacher_id = ?",
                   (quiz_id, session['teacher_id']))
    quiz = cursor.fetchone()
    if not quiz:
        db.close()
        return render_template('error.html',
            error_code=403,
            error_title='Access Denied',
            error_message='You do not have permission to view this quiz.',
            action_url='/dashboard',
            action_text='← Back to Dashboard'
        ), 403
    
    cursor.execute("SELECT * FROM questions WHERE quiz_id = ?", (quiz_id,))
    questions = cursor.fetchall()
    
    cursor.execute("""
        SELECT id, student_name, status, score, violation_count, responses 
        FROM exam_sessions 
        WHERE quiz_id = ?
        ORDER BY score DESC
    """, (quiz_id,))
    students = [dict(row) for row in cursor.fetchall()]
    
    for student in students:
        raw = student.get('responses')
        if raw:
            student['parsed_responses'] = json.loads(raw)
            student['response_map'] = {str(r['question_id']): r for r in student['parsed_responses']}
        else:
            student['parsed_responses'] = []
            student['response_map'] = {}
    
    completed = [s for s in students if s['status'] == 'completed']
    avg_score = round(sum(s['score'] for s in completed) / len(completed), 1) if completed else 0
    db.close()
    
    return render_template('teacher/review.html',
        quiz=quiz, questions=questions, students=students,
        quiz_id=quiz_id, avg_score=avg_score, total_completed=len(completed))

# --- STUDENT FLOW ---
@app.route('/student/join', methods=['GET', 'POST'])
def join_quiz():
    if request.method == 'POST':
        code = request.form.get('code')
        name = request.form.get('name')
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, title FROM quizzes WHERE access_code = ?", (code,))
        quiz = cursor.fetchone()
        
        if quiz:
            cursor.execute("""
                INSERT INTO exam_sessions (quiz_id, student_name, status, violation_count) 
                VALUES (?, ?, 'waiting', 0)
            """, (quiz['id'], name))
            db.commit()
            session['student_session_id'] = cursor.lastrowid
            session['quiz_id'] = quiz['id']
            session['student_name'] = name
            db.close()
            return redirect(url_for('waiting_room'))
        else:
            db.close()
            return render_template('error.html',
                error_code=403,
                error_title='Invalid Access Code',
                error_message='The access code you entered is invalid. Please check with your teacher and try again.',
                action_url='/student/join',
                action_text='← Try Again'
            ), 403
            
    return render_template('student/join.html')

@app.route('/waiting_room')
def waiting_room():
    session_id = session.get('student_session_id')
    if not session_id: return redirect(url_for('join_quiz'))
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT status FROM exam_sessions WHERE id = ?", (session_id,))
    session_data = cursor.fetchone()
    db.close()
    
    if session_data and session_data['status'] in ('active', 'verified'):
        return redirect(url_for('exam_page'))
        
    return render_template('student/waiting_room.html')

@app.route('/exam')
def exam_page():
    if 'quiz_id' not in session: return redirect(url_for('join_quiz'))
        
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT title, duration_minutes FROM quizzes WHERE id = ?", (session.get('quiz_id'),))
    quiz_info = cursor.fetchone()
    quiz_duration = quiz_info['duration_minutes'] if quiz_info else 30
    quiz_title = quiz_info['title'] if quiz_info else 'Exam'
    
    cursor.execute("""
        SELECT id, question_text, option_a, option_b, option_c, option_d 
        FROM questions WHERE quiz_id = ?
    """, (session.get('quiz_id'),))
    questions = [dict(q) for q in cursor.fetchall()]
    db.close()
    
    if not questions:
        return render_template('error.html',
            error_code=404,
            error_title='No Questions Found',
            error_message='This quiz has no questions. Please contact your teacher.',
            action_url='/student/join',
            action_text='← Back to Join'
        ), 404

    return render_template('student/quiz.html', questions=questions, quiz_duration=quiz_duration, quiz_title=quiz_title)

@app.route('/submit_exam', methods=['POST'])
def submit_exam():
    data = request.json
    submitted_answers = data.get('answers') 
    quiz_id = session.get('quiz_id')
    session_id = session.get('student_session_id')
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, correct_answer FROM questions WHERE quiz_id = ?", (quiz_id,))
    actual_questions = cursor.fetchall()
    correct_map = {str(q['id']): q['correct_answer'] for q in actual_questions}
    
    correct_count = 0
    detailed_results = []
    for ans in submitted_answers:
        q_id = str(ans.get('question_id'))
        student_choice = ans.get('choice')
        is_correct = (q_id in correct_map and student_choice == correct_map[q_id])
        if is_correct: correct_count += 1
        detailed_results.append({"question_id": q_id, "student_choice": student_choice, "is_correct": is_correct})

    score_percentage = round((correct_count / len(actual_questions)) * 100) if actual_questions else 0
    cursor.execute("""
        UPDATE exam_sessions 
        SET status = 'completed', score = ?, responses = ? 
        WHERE id = ?
    """, (score_percentage, json.dumps(detailed_results), session_id))
    db.commit()
    db.close()
    return jsonify({"status": "success", "redirect": url_for('show_results')})

@app.route('/results')
def show_results():
    session_id = session.get('student_session_id')
    quiz_id = session.get('quiz_id')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT score, violation_count, responses FROM exam_sessions WHERE id = ?", (session_id,))
    session_data = cursor.fetchone()
    
    raw_responses = session_data['responses']
    student_responses = json.loads(raw_responses) if raw_responses else []
    
    cursor.execute("SELECT * FROM questions WHERE quiz_id = ?", (quiz_id,))
    questions = cursor.fetchall()
    response_map = {str(r['question_id']): r for r in student_responses}
    db.close()

    return render_template('student/results.html', 
                           score=session_data['score'], 
                           violations=session_data['violation_count'],
                           questions=questions,
                           response_map=response_map)

# --- REAL-TIME SOCKETS ---
@socketio.on('join_room')
def on_join(data):
    join_room(str(data['quiz_id']))

@socketio.on('verify_student')
def verify_student(data):
    student_id = data['student_id']
    quiz_id = str(session.get('quiz_id'))
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE exam_sessions SET status = 'verified' WHERE id = ?", (student_id,))
    db.commit()
    db.close()
    emit('status_verified', {'id': student_id}, to=quiz_id)

@socketio.on('security_violation')
def handle_violation(data):
    session_id = session.get('student_session_id')
    quiz_id = str(session.get('quiz_id'))
    student_name = session.get('student_name')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE exam_sessions SET violation_count = violation_count + 1 WHERE id = ?", (session_id,))
    db.commit()
    db.close()
    emit('monitor_update', {'name': student_name, 'reason': data.get('reason'), 'status': 'Violation Detected'}, to=quiz_id)

@socketio.on('teacher_start_exam')
def start_exam(data):
    quiz_id = data['quiz_id']
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE exam_sessions SET status = 'active' WHERE quiz_id = ? AND status = 'waiting'", (quiz_id,))
    db.commit()
    db.close()
    emit('force_start', {}, to=str(quiz_id))

@socketio.on('teacher_approve_resume')
def handle_approval(data):
    quiz_id = str(data.get('quiz_id'))
    student_name = data.get('name')
    emit('resume_exam', {'target_student': student_name}, to=quiz_id)

@socketio.on('teacher_deny_resume')
def handle_denial(data):
    quiz_id = str(data.get('quiz_id'))
    student_name = data.get('name')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE exam_sessions SET status = 'terminated' WHERE quiz_id = ? AND student_name = ?",
                   (data.get('quiz_id'), student_name))
    db.commit()
    db.close()
    emit('exam_terminated', {'target_student': student_name}, to=quiz_id)

@socketio.on('submit_justification')
def handle_justification(data):
    quiz_id = str(session.get('quiz_id'))
    emit('receive_justification', data, to=quiz_id)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)