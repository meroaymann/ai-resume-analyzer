// ===== Dark mode =====
const themeToggle = document.getElementById("themeToggle");
const root = document.documentElement;

function setTheme(theme) {
  root.setAttribute("data-theme", theme);
  themeToggle.textContent = theme === "dark" ? "☀️" : "🌙";
  try { localStorage.setItem("theme", theme); } catch (e) {}
}

let saved = "light";
try { saved = localStorage.getItem("theme") || "light"; } catch (e) {}
setTheme(saved);

themeToggle.addEventListener("click", () => {
  setTheme(root.getAttribute("data-theme") === "dark" ? "light" : "dark");
});

// ===== Upload + validation =====
const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("resume");
const fileName = document.getElementById("fileName");
const errorMsg = document.getElementById("errorMsg");
const form = document.getElementById("analyzeForm");
const submitBtn = document.getElementById("submitBtn");

const ALLOWED = ["pdf", "docx"];
const MAX_SIZE = 5 * 1024 * 1024;

function validateFile(file) {
  if (!file) return "Please upload your resume first.";
  const ext = file.name.split(".").pop().toLowerCase();
  if (!ALLOWED.includes(ext)) return "Only PDF or DOCX files are allowed.";
  if (file.size > MAX_SIZE) return "File is too large (max 5MB).";
  return "";
}

function showFile(file) {
  const error = validateFile(file);
  errorMsg.textContent = error;
  fileName.textContent = error ? "" : `📎 ${file.name}`;
}

fileInput.addEventListener("change", () => showFile(fileInput.files[0]));

["dragenter", "dragover"].forEach(evt =>
  dropZone.addEventListener(evt, e => { e.preventDefault(); dropZone.classList.add("dragover"); })
);
["dragleave", "drop"].forEach(evt =>
  dropZone.addEventListener(evt, e => { e.preventDefault(); dropZone.classList.remove("dragover"); })
);
dropZone.addEventListener("drop", e => {
  fileInput.files = e.dataTransfer.files;
  showFile(fileInput.files[0]);
});

form.addEventListener("submit", e => {
  const error = validateFile(fileInput.files[0]);
  if (error) {
    e.preventDefault();
    errorMsg.textContent = error;
    return;
  }
  submitBtn.disabled = true;
  submitBtn.textContent = "Analyzing... ⏳";
});

// Reset the button if the user comes back with the browser's Back button
window.addEventListener("pageshow", () => {
  submitBtn.disabled = false;
  submitBtn.textContent = "Analyze My Resume";
});