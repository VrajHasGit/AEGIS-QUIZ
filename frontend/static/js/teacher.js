// static/js/teacher.js
const socket = io();

socket.on("teacher_alert", function (data) {
  const logBoard = document.getElementById("violation-logs");
  if (!logBoard) return;
  const newLog = document.createElement("div");

  const student = String(data.student ?? "Student");
  const reason = String(data.reason ?? "Policy violation");
  newLog.className = "alert-item danger";
  const strong = document.createElement("strong");
  strong.textContent = student;
  newLog.appendChild(strong);
  newLog.append(`: ${reason}`);

  logBoard.prepend(newLog);

  // Highlight row safely if present.
  const studentRow = document.getElementById(`row-${data.student}`);
  if (studentRow) {
    studentRow.style.backgroundColor = "#ffcccc";
  }
});
