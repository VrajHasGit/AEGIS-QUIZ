-- =============================================
-- AEGIS QUIZ - Database Setup Script
-- Run this script to create the full database
-- =============================================

CREATE DATABASE IF NOT EXISTS aegis_quiz_db;
USE aegis_quiz_db;

-- ---------------------------------------------
-- 1. Teachers Table
-- Stores teacher login credentials
-- ---------------------------------------------
CREATE TABLE IF NOT EXISTS teachers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------
-- 2. Quizzes Table
-- Each quiz belongs to a teacher
-- ---------------------------------------------
CREATE TABLE IF NOT EXISTS quizzes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    teacher_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    topic VARCHAR(255),
    access_code VARCHAR(8) NOT NULL UNIQUE,
    duration_minutes INT DEFAULT 30,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE
);

-- ---------------------------------------------
-- 3. Questions Table
-- MCQ questions linked to a quiz
-- ---------------------------------------------
CREATE TABLE IF NOT EXISTS questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    quiz_id INT NOT NULL,
    question_text TEXT NOT NULL,
    option_a VARCHAR(500) NOT NULL,
    option_b VARCHAR(500) NOT NULL,
    option_c VARCHAR(500) NOT NULL,
    option_d VARCHAR(500) NOT NULL,
    correct_answer CHAR(1) NOT NULL,
    FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
);

-- ---------------------------------------------
-- 4. Exam Sessions Table
-- Tracks each student's attempt at a quiz
-- ---------------------------------------------
CREATE TABLE IF NOT EXISTS exam_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    quiz_id INT NOT NULL,
    student_name VARCHAR(100) NOT NULL,
    status ENUM('waiting', 'verified', 'in_progress', 'completed') DEFAULT 'waiting',
    score DECIMAL(5,2) DEFAULT NULL,
    violation_count INT DEFAULT 0,
    responses JSON DEFAULT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
);

-- ---------------------------------------------
-- Sample Teacher Account (for testing)
-- Email: admin@aegis.com | Password: admin123
-- ---------------------------------------------
INSERT INTO teachers (username, email, password_hash) 
VALUES ('Admin Teacher', 'admin@aegis.com', 'admin123')
ON DUPLICATE KEY UPDATE username = username;
