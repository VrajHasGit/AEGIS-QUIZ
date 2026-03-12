// static/js/security.js
// AEGIS Security Module — importable by quiz.html
// Usage: initSecurity(socket, studentName, quizId, onLockdown)

let _socket = null;
let _studentName = '';
let _quizId = '';
let _lockdownCallback = null;
let _violationCount = 0;

function initSecurity(socket, studentName, quizId, onLockdown) {
  _socket = socket;
  _studentName = studentName;
  _quizId = quizId;
  _lockdownCallback = onLockdown;
  _violationCount = 0;

  // --- Tab Switch & Visibility Detection ---
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      reportViolation('Tab Switch Detected');
    }
  });

  // --- Window Blur (Alt+Tab, second monitor click) ---
  window.addEventListener('blur', () => {
    reportViolation('Window Focus Lost');
  });

  // --- Fullscreen Exit Detection ---
  document.addEventListener('fullscreenchange', () => {
    if (!document.fullscreenElement) {
      reportViolation('Exited Fullscreen Mode');
    }
  });

  // --- Disable Right-Click ---
  document.addEventListener('contextmenu', (e) => e.preventDefault());

  // --- Disable Copy/Paste/Cut/Select-All ---
  document.addEventListener('copy', (e) => e.preventDefault());
  document.addEventListener('paste', (e) => e.preventDefault());
  document.addEventListener('cut', (e) => e.preventDefault());

  // --- Disable Cheater Keyboard Shortcuts ---
  document.addEventListener('keydown', (e) => {
    // F12, Ctrl+Shift+I (DevTools), Ctrl+U (View Source)
    if (
      e.key === 'F12' ||
      (e.ctrlKey && e.shiftKey && e.key === 'I') ||
      (e.ctrlKey && e.key === 'u')
    ) {
      e.preventDefault();
      reportViolation('Attempted to access Developer Tools');
    }

    // Ctrl+C, Ctrl+V, Ctrl+A
    if (e.ctrlKey && ['c', 'v', 'a'].includes(e.key.toLowerCase())) {
      e.preventDefault();
    }

    // PrintScreen
    if (e.key === 'PrintScreen') {
      try { navigator.clipboard.writeText(''); } catch(_) {}
      reportViolation('Screenshot attempt blocked');
    }
  });

  // --- Disable Text Selection via CSS ---
  document.body.style.userSelect = 'none';
  document.body.style.webkitUserSelect = 'none';
}

function getViolationCount() {
  return _violationCount;
}

function reportViolation(reason) {
  if (!_socket) return;

  _violationCount++;

  console.warn('[AEGIS] Violation:', reason, '| Total:', _violationCount);

  // Emit to backend
  _socket.emit('security_violation', {
    type: reason,
    reason: reason,
    student_name: _studentName,
    quiz_id: _quizId,
    name: _studentName,
    timestamp: new Date().toISOString()
  });

  // Trigger lockdown UI callback with reason and count
  if (_lockdownCallback) {
    _lockdownCallback(reason, _violationCount);
  }
}
