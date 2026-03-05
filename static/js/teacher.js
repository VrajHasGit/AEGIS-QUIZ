// static/js/teacher.js
const socket = io();

socket.on("teacher_alert", function (data) {
  const logBoard = document.getElementById("violation-logs");
  const newLog = document.createElement("div");

  newLog.className = "alert-item danger"; // CSS for red background
  newLog.innerHTML = `<strong>${data.student}</strong>: ${data.reason}`;

  logBoard.prepend(newLog);

  // Logic to highlight the student's row in red
  document.getElementById(`row-${data.student}`).style.backgroundColor =
    "#ffcccc";
});
