import os
import json
import uuid
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_socketio import SocketIO, emit, join_room
import mysql.connector
from ai_engine import generate_quiz_data 
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
socketio = SocketIO(app, cors_allowed_origins="*")

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

# --- Database Connection ---
def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

# --- AUTH & DASHBOARD ---
@app.route('/')
def index():
    if 'teacher_id' in session: return redirect(url_for('dashboard'))
    return render_template('auth/login.html')

@app.route('/login', methods=['POST'])
def login():
    email, password = request.form.get('email'), request.form.get('password')
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM teachers WHERE email = %s AND password_hash = %s", (email, password))
    teacher = cursor.fetchone()
    if teacher:
        session['teacher_id'], session['teacher_name'] = teacher['id'], teacher['username']
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
    cursor = db.cursor(dictionary=True)
    
    # Check if email already exists
    cursor.execute("SELECT id FROM teachers WHERE email = %s", (email,))
    if cursor.fetchone():
        flash('An account with this email already exists.', 'error')
        return redirect(url_for('index'))
    
    # Create the teacher account
    cursor.execute("INSERT INTO teachers (username, email, password_hash) VALUES (%s, %s, %s)",
                   (username, email, password))
    db.commit()
    
    flash('Account created successfully! Please sign in.', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'teacher_id' not in session:
        return redirect(url_for('index'))
    
    # 1. Connect to DB
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # 2. Fetch quizzes for this specific teacher
    # We join with the exam_sessions table to count how many students have joined
    query = """
        SELECT q.id, q.title, q.access_code, 
        (SELECT COUNT(*) FROM exam_sessions WHERE quiz_id = q.id) as student_count
        FROM quizzes q 
        WHERE q.teacher_id = %s
        ORDER BY q.id DESC
    """
    cursor.execute(query, (session['teacher_id'],))
    quizzes = cursor.fetchall()
    
    # 3. Pass the 'quizzes' list to your HTML template
    return render_template('teacher/dashboard.html', quizzes=quizzes)

# --- QUIZ GENERATION (AI) ---
@app.route('/api/generate', methods=['POST'])
def handle_ai_generation():
    try:
        data = request.json
        topic, count = data.get('topic'), data.get('num_questions')
        duration = data.get('duration', 30)
        quiz_data = generate_quiz_data(topic, count)
        if not quiz_data: return jsonify({"status": "error", "message": "AI failed"}), 500
        
        db = get_db()
        cursor = db.cursor()
        access_code = str(uuid.uuid4())[:8].upper()
        cursor.execute("INSERT INTO quizzes (teacher_id, title, topic, access_code, duration_minutes) VALUES (%s, %s, %s, %s, %s)",
                       (session['teacher_id'], f"{topic} Quiz", topic, access_code, duration))
        quiz_id = cursor.lastrowid
        
        for q in quiz_data:
            cursor.execute("""INSERT INTO questions 
                (quiz_id, question_text, option_a, option_b, option_c, option_d, correct_answer) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (quiz_id, q.get('question_text'), q.get('option_a'), q.get('option_b'), 
                 q.get('option_c'), q.get('option_d'), q.get('correct_answer')))
        db.commit()
        return jsonify({"status": "success", "code": access_code})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- DELETE QUIZ ---
@app.route('/api/quiz/<int:quiz_id>', methods=['DELETE'])
def delete_quiz(quiz_id):
    if 'teacher_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Verify teacher owns this quiz
    cursor.execute("SELECT id FROM quizzes WHERE id = %s AND teacher_id = %s", (quiz_id, session['teacher_id']))
    quiz = cursor.fetchone()
    if not quiz:
        return jsonify({"status": "error", "message": "Quiz not found or access denied"}), 404
    
    # Cascade delete: sessions → questions → quiz
    cursor.execute("DELETE FROM exam_sessions WHERE quiz_id = %s", (quiz_id,))
    cursor.execute("DELETE FROM questions WHERE quiz_id = %s", (quiz_id,))
    cursor.execute("DELETE FROM quizzes WHERE id = %s", (quiz_id,))
    db.commit()
    
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
        
        # 1. Create the Quiz Entry
        cursor.execute("INSERT INTO quizzes (teacher_id, title, topic, access_code, duration_minutes) VALUES (%s, %s, %s, %s, %s)",
                       (session['teacher_id'], title, topic, access_code, duration))
        quiz_id = cursor.lastrowid
        
        # 2. Get the questions from the dynamic form
        questions = request.form.getlist('question[]')
        opt_as = request.form.getlist('opt_a[]')
        opt_bs = request.form.getlist('opt_b[]')
        opt_cs = request.form.getlist('opt_c[]')
        opt_ds = request.form.getlist('opt_d[]')
        answers = request.form.getlist('correct[]')
        
        # 3. Save each question
        for i in range(len(questions)):
            cursor.execute("""INSERT INTO questions 
                (quiz_id, question_text, option_a, option_b, option_c, option_d, correct_answer) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (quiz_id, questions[i], opt_as[i], opt_bs[i], opt_cs[i], opt_ds[i], answers[i]))
        
        db.commit()
        return redirect(url_for('dashboard'))

    return render_template('teacher/manual_builder.html')

# --- LIVE MONITORING ROUTE ---
@app.route('/teacher/monitor/<int:quiz_id>')
def monitor_quiz(quiz_id):
    if 'teacher_id' not in session: return redirect(url_for('index'))
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Get quiz details including duration
    cursor.execute("SELECT title, access_code, duration_minutes FROM quizzes WHERE id = %s", (quiz_id,))
    quiz = cursor.fetchone()
    
    # Get all student sessions for this quiz
    cursor.execute("""
        SELECT id, student_name, status, score, violation_count 
        FROM exam_sessions 
        WHERE quiz_id = %s
    """, (quiz_id,))
    students = cursor.fetchall()
    
    return render_template('teacher/monitor.html', quiz=quiz, students=students, quiz_id=quiz_id)

# --- TEACHER ANSWER SHEET REVIEW ---
@app.route('/teacher/review/<int:quiz_id>')
def review_quiz(quiz_id):
    if 'teacher_id' not in session: return redirect(url_for('index'))
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Verify teacher owns this quiz
    cursor.execute("SELECT id, title, topic, access_code FROM quizzes WHERE id = %s AND teacher_id = %s",
                   (quiz_id, session['teacher_id']))
    quiz = cursor.fetchone()
    if not quiz:
        return render_template('error.html',
            error_code=403,
            error_title='Access Denied',
            error_message='You do not have permission to view this quiz.',
            action_url='/dashboard',
            action_text='← Back to Dashboard'
        ), 403
    
    # Get all questions for the quiz
    cursor.execute("SELECT * FROM questions WHERE quiz_id = %s", (quiz_id,))
    questions = cursor.fetchall()
    
    # Get all student sessions with responses
    cursor.execute("""
        SELECT id, student_name, status, score, violation_count, responses 
        FROM exam_sessions 
        WHERE quiz_id = %s
        ORDER BY score DESC
    """, (quiz_id,))
    students = cursor.fetchall()
    
    # Parse JSON responses for each student
    for student in students:
        raw = student.get('responses')
        if raw:
            student['parsed_responses'] = json.loads(raw)
            # Build a map for easy lookup
            student['response_map'] = {str(r['question_id']): r for r in student['parsed_responses']}
        else:
            student['parsed_responses'] = []
            student['response_map'] = {}
    
    # Calculate stats
    completed = [s for s in students if s['status'] == 'completed']
    avg_score = round(sum(s['score'] for s in completed) / len(completed), 1) if completed else 0
    
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
        cursor = db.cursor(dictionary=True)
        
        # 1. Check if the quiz exists
        cursor.execute("SELECT id, title FROM quizzes WHERE access_code = %s", (code,))
        quiz = cursor.fetchone()
        
        if quiz:
            # 2. Register the student session in the database
            cursor.execute("""
                INSERT INTO exam_sessions (quiz_id, student_name, status, violation_count) 
                VALUES (%s, %s, 'waiting', 0)
            """, (quiz['id'], name))
            db.commit()
            
            # 3. Store info in session so we know who they are on the next page
            session['student_session_id'] = cursor.lastrowid
            session['quiz_id'] = quiz['id']
            session['student_name'] = name
            
            return redirect(url_for('waiting_room'))
        else:
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
    return render_template('student/waiting_room.html')

@app.route('/exam')
def exam_page():
    # 1. Validation check
    if 'quiz_id' not in session:
        return redirect(url_for('join_quiz'))
        
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # 2. Fetch quiz info (duration + title)
    cursor.execute("SELECT title, duration_minutes FROM quizzes WHERE id = %s", (session.get('quiz_id'),))
    quiz_info = cursor.fetchone()
    quiz_duration = quiz_info.get('duration_minutes', 30) if quiz_info else 30
    quiz_title = quiz_info.get('title', 'Exam') if quiz_info else 'Exam'
    
    # 3. Fetch questions
    cursor.execute("""
        SELECT id, question_text, option_a, option_b, option_c, option_d 
        FROM questions WHERE quiz_id = %s
    """, (session.get('quiz_id'),))
    
    questions = cursor.fetchall()
    
    # 4. Handle empty quiz
    if not questions:
        return render_template('error.html',
            error_code=404,
            error_title='No Questions Found',
            error_message='This quiz has no questions. Please contact your teacher.',
            action_url='/student/join',
            action_text='← Back to Join'
        ), 404

    return render_template('student/quiz.html', questions=questions, quiz_duration=quiz_duration, quiz_title=quiz_title)

# --- SUBMISSION & RESULTS ---
@app.route('/submit_exam', methods=['POST'])
def submit_exam():
    data = request.json
    submitted_answers = data.get('answers') 
    quiz_id = session.get('quiz_id')
    session_id = session.get('student_session_id')
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    

    # Fetch correct answers
    cursor.execute("SELECT id, correct_answer FROM questions WHERE quiz_id = %s", (quiz_id,))
    actual_questions = cursor.fetchall()
    correct_map = {str(q['id']): q['correct_answer'] for q in actual_questions}
    
    correct_count = 0
    # Store detailed responses in a list to save as JSON in the DB
    detailed_results = []

    for ans in submitted_answers:
        q_id = str(ans.get('question_id'))
        student_choice = ans.get('choice')
        is_correct = (q_id in correct_map and student_choice == correct_map[q_id])
        
        if is_correct:
            correct_count += 1
            
        detailed_results.append({
            "question_id": q_id,
            "student_choice": student_choice,
            "is_correct": is_correct
        })

    score_percentage = round((correct_count / len(actual_questions)) * 100) if actual_questions else 0
    
    # Update DB - We store the detailed_results as a JSON string in a new column 'responses'
    # Make sure your 'exam_sessions' table has a 'responses' column (TEXT or JSON type)
    cursor.execute("""
        UPDATE exam_sessions 
        SET status = 'completed', score = %s, responses = %s 
        WHERE id = %s
    """, (score_percentage, json.dumps(detailed_results), session_id))
    db.commit()
    
    return jsonify({"status": "success", "redirect": url_for('show_results')})

@app.route('/results')
def show_results():
    session_id = session.get('student_session_id')
    quiz_id = session.get('quiz_id')
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("SELECT score, violation_count, responses FROM exam_sessions WHERE id = %s", (session_id,))
    session_data = cursor.fetchone()
    
    # 2. Add this check to prevent the 'NoneType' error
    raw_responses = session_data.get('responses')
    if raw_responses:
        student_responses = json.loads(raw_responses)
    else:
        student_responses = [] # Fallback to empty list
    
    cursor.execute("SELECT * FROM questions WHERE quiz_id = %s", (quiz_id,))
    questions = cursor.fetchall()
    
    response_map = {str(r['question_id']): r for r in student_responses}

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
    cursor.execute("UPDATE exam_sessions SET status = 'verified' WHERE id = %s", (student_id,))
    db.commit()
    
    # Notify that specific student they are now verified
    emit('status_verified', {'id': student_id}, to=quiz_id)

@socketio.on('security_violation')
def handle_violation(data):
    session_id = session.get('student_session_id')
    quiz_id = str(session.get('quiz_id'))
    student_name = session.get('student_name')
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE exam_sessions SET violation_count = violation_count + 1 WHERE id = %s", (session_id,))
    db.commit()
    
    # Broadcast specifically to the teacher's monitor room
    emit('monitor_update', {
        'name': student_name,
        'reason': data.get('reason'),
        'status': 'Violation Detected'
    }, to=quiz_id)
@socketio.on('teacher_start_exam')
def start_exam(data):
    emit('force_start', {}, to=str(data['quiz_id']))

@socketio.on('teacher_approve_resume')
def handle_approval(data):
    quiz_id = str(data.get('quiz_id'))
    student_name = data.get('name')
    # Signal the room, target the student
    emit('resume_exam', {'target_student': student_name}, to=quiz_id)

@socketio.on('teacher_deny_resume')
def handle_denial(data):
    quiz_id = str(data.get('quiz_id'))
    student_name = data.get('name')
    
    # Update exam session status to terminated
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE exam_sessions SET status = 'terminated' WHERE quiz_id = %s AND student_name = %s",
                   (data.get('quiz_id'), student_name))
    db.commit()
    
    # Signal the student
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