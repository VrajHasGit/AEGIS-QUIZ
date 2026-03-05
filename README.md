<p align="center">
  <h1 align="center">🛡️ AEGIS QUIZ</h1>
  <p align="center">
    <strong>AI-Enhanced, Guardian-Integrated Secure Quiz Platform</strong>
  </p>
  <p align="center">
    A real-time, anti-cheat online examination system built with Flask, Socket.IO, and Google Gemini AI.
  </p>
  <p align="center">
    <a href="#features">Features</a> •
    <a href="#tech-stack">Tech Stack</a> •
    <a href="#getting-started">Getting Started</a> •
    <a href="#database">Database</a> •
    <a href="#project-structure">Structure</a> •
    <a href="#license">License</a>
  </p>
</p>

---

## ✨ Features

### 👩‍🏫 For Teachers
- **Dashboard** — Create, manage, and monitor all quizzes from one place.
- **AI-Powered Quiz Generation** — Instantly generate MCQ quizzes on any topic using **Google Gemini AI**.
- **Manual Quiz Builder** — Craft custom quizzes question-by-question with full control.
- **Live Monitoring** — Watch students take the exam in real-time via WebSockets.
- **Anti-Cheat Alerts** — Get instant violation alerts when a student switches tabs, minimizes the window, or attempts to copy.

### 🎓 For Students
- **Join via Access Code** — Enter a short code to join any live exam. No account needed.
- **Waiting Room** — Students wait in a real-time lobby until the teacher starts the exam.
- **Timed Exams** — Complete the quiz under a set time limit.
- **Instant Results** — View score, correct answers, and violation count immediately after submission.

### 🔒 Security & Integrity
- **Tab-Switch Detection** — Flags students who navigate away from the exam window.
- **Copy-Paste Prevention** — Disables right-click and text selection during exams.
- **Violation Counter** — Tracks and reports total security violations per student.
- **Teacher-Controlled Resumption** — Teachers can approve or deny a student's request to continue after a violation.

---

## 🛠️ Tech Stack

| Layer        | Technology                                                       |
| ------------ | ---------------------------------------------------------------- |
| **Backend**  | [Flask](https://flask.palletsprojects.com/) (Python)             |
| **Real-Time**| [Flask-SocketIO](https://flask-socketio.readthedocs.io/) (WebSockets) |
| **Database** | [MySQL](https://www.mysql.com/)                                  |
| **AI Engine**| [Google Gemini API](https://ai.google.dev/) (`gemini-2.5-flash`) |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript                                  |

---

## 🚀 Getting Started

Follow these steps to run AEGIS Quiz locally on your machine.

### Prerequisites

Make sure you have the following installed:

- **Python 3.9+** — [Download](https://www.python.org/downloads/)
- **MySQL Server** — [Download](https://dev.mysql.com/downloads/mysql/)
- **Git** — [Download](https://git-scm.com/downloads)
- **Google Gemini API Key** — [Get one here](https://aistudio.google.com/app/apikey)

### 1. Clone the Repository

```bash
git clone https://github.com/VrajHasGit/AEGIS-QUIZ.git
cd AEGIS-QUIZ
```

### 2. Create a Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up the Database

Open your MySQL client (MySQL Workbench, terminal, etc.) and run the setup script:

```bash
mysql -u root -p < database/setup.sql
```

Or manually execute the contents of `database/setup.sql` in your MySQL GUI. This will:
- Create the `aegis_quiz_db` database
- Create all 4 required tables (`teachers`, `quizzes`, `questions`, `exam_sessions`)
- Insert a sample teacher account for testing

### 5. Configure Environment Variables

Create a `.env` file in the project root:

```env
# --- MySQL Database Credentials ---
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=aegis_quiz_db

# --- Google Gemini AI Key ---
GEMINI_API_KEY=your_gemini_api_key_here

# --- Flask Secret Key (For secure sessions) ---
FLASK_SECRET_KEY=your_random_secret_key_here
```

> 💡 **Tip**: Generate a Flask secret key by running `python -c "import secrets; print(secrets.token_hex(24))"`

### 6. Run the Application

```bash
python app.py
```

The server will start at **http://localhost:5000**

### 7. Log In

Use the default test credentials:

| Field    | Value              |
| -------- | ------------------ |
| Email    | `admin@aegis.com`  |
| Password | `admin123`         |

---

## 🗄️ Database

AEGIS Quiz uses **MySQL** with 4 core tables. The full schema is in [`database/setup.sql`](database/setup.sql).

### Entity Relationship

```
┌──────────────┐       ┌──────────────┐       ┌──────────────────┐
│   teachers   │───1:N─│   quizzes    │───1:N─│    questions     │
│──────────────│       │──────────────│       │──────────────────│
│ id (PK)      │       │ id (PK)      │       │ id (PK)          │
│ username     │       │ teacher_id   │──FK   │ quiz_id      (FK)│
│ email        │       │ title        │       │ question_text    │
│ password_hash│       │ topic        │       │ option_a/b/c/d   │
│ created_at   │       │ access_code  │       │ correct_answer   │
└──────────────┘       │ duration_min │       └──────────────────┘
                       │ created_at   │
                       └──────┬───────┘
                              │
                              │ 1:N
                              ▼
                       ┌──────────────────┐
                       │  exam_sessions   │
                       │──────────────────│
                       │ id (PK)          │
                       │ quiz_id      (FK)│
                       │ student_name     │
                       │ status           │
                       │ score            │
                       │ violation_count  │
                       │ responses (JSON) │
                       │ started_at       │
                       └──────────────────┘
```

### Table Descriptions

| Table             | Purpose                                                            |
| ----------------- | ------------------------------------------------------------------ |
| `teachers`        | Stores teacher accounts (login credentials)                        |
| `quizzes`         | Quiz metadata — title, topic, access code, duration, owner         |
| `questions`       | Individual MCQs with 4 options and a correct answer key            |
| `exam_sessions`   | Tracks each student attempt — score, violations, and JSON responses|

---

## 📁 Project Structure

```
AEGIS-QUIZ/
├── app.py                  # Main Flask application & Socket.IO events
├── ai_engine.py            # Google Gemini AI quiz generation engine
├── db_manager.py           # Database utility functions
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (not committed)
├── .gitignore              # Git ignore rules
│
├── database/
│   └── setup.sql           # Full MySQL schema & seed data
│
├── static/
│   ├── css/
│   │   ├── main.css        # Global styles
│   │   └── exam.css        # Exam-specific styles
│   └── js/
│       ├── teacher.js      # Teacher dashboard logic
│       ├── student.js      # Student exam logic
│       └── security.js     # Anti-cheat detection system
│
└── templates/
    ├── base.html            # Base layout template
    ├── auth/
    │   └── login.html       # Teacher login page
    ├── teacher/
    │   ├── dashboard.html   # Quiz management dashboard
    │   ├── ai_gen.html      # AI quiz generator interface
    │   ├── manual_builder.html  # Manual quiz creation form
    │   ├── monitor.html     # Live exam monitoring console
    │   └── report.html      # Quiz report & analytics
    └── student/
        ├── join.html        # Access code entry page
        ├── waiting_room.html# Pre-exam waiting lobby
        ├── quiz.html        # Live exam interface
        └── results.html     # Post-exam score & review
```

---

## 🔑 API Routes Overview

| Method | Route                          | Description                      |
| ------ | ------------------------------ | -------------------------------- |
| GET    | `/`                            | Login page (redirects if logged in) |
| POST   | `/login`                       | Teacher authentication           |
| GET    | `/dashboard`                   | Teacher quiz dashboard           |
| POST   | `/api/generate`                | AI quiz generation endpoint      |
| GET/POST | `/teacher/create-manual`     | Manual quiz builder              |
| GET    | `/teacher/monitor/<quiz_id>`   | Live monitoring page             |
| GET/POST | `/student/join`              | Student quiz entry               |
| GET    | `/waiting_room`                | Student waiting lobby            |
| GET    | `/exam`                        | Live exam page                   |
| POST   | `/submit_exam`                 | Submit answers & grade           |
| GET    | `/results`                     | View exam results                |
| GET    | `/logout`                      | Clear session & logout           |

---

## 📡 Real-Time WebSocket Events

| Event                   | Direction         | Description                                |
| ----------------------- | ----------------- | ------------------------------------------ |
| `join_room`             | Client → Server   | Join a quiz monitoring room                |
| `verify_student`        | Teacher → Server  | Verify a student's identity                |
| `teacher_start_exam`    | Teacher → Server  | Start the exam for all students            |
| `security_violation`    | Student → Server  | Report a tab-switch or copy attempt        |
| `submit_justification`  | Student → Server  | Send violation justification to teacher    |
| `teacher_approve_resume`| Teacher → Server  | Allow student to resume after violation    |
| `status_verified`       | Server → Student  | Confirm student verification               |
| `force_start`           | Server → Students | Signal all students to begin the exam      |
| `monitor_update`        | Server → Teacher  | Live violation/status broadcast            |
| `resume_exam`           | Server → Student  | Allow specific student to continue         |

---

## 📝 License

This project is open-source and available under the [MIT License](LICENSE).

---

<p align="center">
  Built with ❤️ by <a href="https://github.com/VrajHasGit">VrajHasGit</a>
</p>
