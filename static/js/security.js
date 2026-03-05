// static/js/security.js

// 1. Force Fullscreen on Start
function startExam() {
  const elem = document.documentElement;
  if (elem.requestFullscreen) {
    elem.requestFullscreen();
  }
  // Hide the start button and show the quiz
  document.getElementById("start-btn").style.display = "none";
  document.getElementById("quiz-content").style.display = "block";
}

// 2. Tab Switch & Window Blur Detection
// 'visibilitychange' catches tab switching
document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    reportViolation("Tab Switch Detected");
  }
});

// 'blur' catches clicking on a second monitor or another app (like Alt+Tab)
window.addEventListener("blur", () => {
  reportViolation("Window Focus Lost (Possible App Switch)");
});

// 3. Prevent Exiting Fullscreen
document.addEventListener("fullscreenchange", () => {
  if (!document.fullscreenElement) {
    reportViolation("Exited Fullscreen Mode");
    // Optional: Block the screen until they go back to fullscreen
    forceReentry();
  }
});

// 4. Disable "Cheater" Keyboard Shortcuts & Right Click
document.addEventListener("contextmenu", (e) => e.preventDefault()); // Disable Right-Click

document.addEventListener("keydown", (e) => {
  // Disable F12, Ctrl+Shift+I (DevTools), Ctrl+U (View Source)
  if (
    e.key === "F12" ||
    (e.ctrlKey && e.shiftKey && e.key === "I") ||
    (e.ctrlKey && e.key === "u")
  ) {
    e.preventDefault();
    reportViolation("Attempted to access Developer Tools");
  }
  // Disable PrintScreen
  if (e.key === "PrintScreen") {
    navigator.clipboard.writeText(""); // Clear clipboard
    alert("Screenshots are disabled.");
  }
});

// 5. Signal the Backend
function reportViolation(reason) {
  console.warn("Violation:", reason);

  // Send to Flask server via Socket.io
  socket.emit("security_breach", {
    reason: reason,
    student_id: session_student_id,
    timestamp: new Date().toISOString(),
  });

  // Alert student
  alert(`SECURITY WARNING: ${reason}. Your teacher has been notified.`);
}
