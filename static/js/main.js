// ===== Helpers =====
const $ = id => document.getElementById(id);

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;   // textContent = safe (no HTML injection)
  return node;
}

function fillChips(container, items, type, emptyText) {
  container.replaceChildren();
  if (!items || !items.length) {
    container.appendChild(el("span", "muted small", emptyText || "—"));
    return;
  }
  items.forEach(item => container.appendChild(el("span", `chip ${type}`, item)));
}

function fillList(container, items) {
  container.replaceChildren(...(items || []).map(item => el("li", null, item)));
}

function scoreColor(value) {
  if (value >= 85) return "var(--good)";
  if (value >= 70) return "var(--primary)";
  if (value >= 50) return "var(--warn)";
  return "var(--error)";
}

// Job match uses softer thresholds (50% = partial match, not a failure)
function matchColor(value) {
  if (value >= 75) return "var(--good)";
  if (value >= 50) return "var(--primary)";
  if (value >= 30) return "var(--warn)";
  return "var(--error)";
}

function animateNumber(node, target, suffix = "") {
  const start = performance.now();
  const duration = 900;
  function step(now) {
    const progress = Math.min((now - start) / duration, 1);
    node.textContent = Math.round(target * progress) + suffix;
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// ===== Dark mode =====
const themeToggle = $("themeToggle");
const root = document.documentElement;

function setTheme(theme) {
  root.setAttribute("data-theme", theme);
  themeToggle.textContent = theme === "dark" ? "☀️" : "🌙";
  try { localStorage.setItem("theme", theme); } catch (e) {}
}

let savedTheme = "light";
try { savedTheme = localStorage.getItem("theme") || "light"; } catch (e) {}
setTheme(savedTheme);

themeToggle.addEventListener("click", () => {
  setTheme(root.getAttribute("data-theme") === "dark" ? "light" : "dark");
});

// ===== Upload + validation =====
const dropZone = $("dropZone");
const fileInput = $("resume");
const fileName = $("fileName");
const errorMsg = $("errorMsg");
const form = $("analyzeForm");
const submitBtn = $("submitBtn");

const ALLOWED = ["pdf", "docx"];
const MAX_SIZE = 4 * 1024 * 1024;

function validateFile(file) {
  if (!file) return "Please upload your resume first.";
  const ext = file.name.split(".").pop().toLowerCase();
  if (!ALLOWED.includes(ext)) return "Only PDF or DOCX files are allowed.";
  if (file.size > MAX_SIZE) return "File is too large (max 4MB).";
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

// ===== Loading overlay =====
const LOADING_STEPS = [
  "📄 Reading your resume...",
  "🧠 Extracting skills...",
  "🎯 Matching with the job...",
  "✨ Asking the AI coach...",
  "📊 Building your report...",
];
let loaderTimer;

function setLoading(isLoading) {
  submitBtn.disabled = isLoading;
  submitBtn.textContent = isLoading ? "Analyzing... ⏳" : "Analyze My Resume";
  $("loader").classList.toggle("hidden", !isLoading);
  clearInterval(loaderTimer);
  if (isLoading) {
    let i = 0;
    $("loaderText").textContent = LOADING_STEPS[0];
    loaderTimer = setInterval(() => {
      i = Math.min(i + 1, LOADING_STEPS.length - 1);
      $("loaderText").textContent = LOADING_STEPS[i];
    }, 1800);
  }
}

// ===== Render: score =====
function renderScore(score) {
  const gauge = $("scoreGauge");
  gauge.style.setProperty("--gauge-color", scoreColor(score.score));
  gauge.style.setProperty("--value", 0);
  setTimeout(() => gauge.style.setProperty("--value", score.score), 60);
  animateNumber($("scoreValue"), score.score);

  $("scoreGrade").textContent = score.grade;
  $("scoreGrade").style.color = scoreColor(score.score);

  const box = $("breakdown");
  box.replaceChildren();
  score.breakdown.forEach(item => {
    const pct = Math.round((item.score / item.max) * 100);
    const row = el("div", "bar-row");
    const head = el("div", "bar-head");
    head.append(el("span", null, item.label), el("span", "muted", `${item.score}/${item.max}`));
    const track = el("div", "bar-track");
    const fill = el("div", "bar-fill");
    fill.style.background = scoreColor(pct);
    track.appendChild(fill);
    row.append(head, track);
    box.appendChild(row);
    setTimeout(() => (fill.style.width = pct + "%"), 60);
  });
}

// ===== Render: job match =====
function renderMatch(match) {
  const card = $("matchCard");
  if (!match) {
    card.classList.add("hidden");
    return;
  }
  card.classList.remove("hidden");

  animateNumber($("matchScore"), match.match_score, "%");
  $("matchScore").style.background = matchColor(match.match_score);

  const bar = $("matchBar");
  bar.style.width = "0";
  bar.style.background = matchColor(match.match_score);
  setTimeout(() => (bar.style.width = match.match_score + "%"), 60);

  fillChips($("matchedSkills"), match.matched_skills, "good", "No matching skills found.");
  fillChips($("missingSkills"), match.missing_skills, "bad", "Nothing missing — great match! 🎉");
  fillChips($("missingKeywords"), match.missing_keywords, "neutral", "No important keywords missing.");
}

// ===== Render: ATS =====
function renderATS(ats) {
  if (!ats) return;
  animateNumber($("atsScore"), ats.score, "%");
  $("atsScore").style.background = scoreColor(ats.score);

  const bar = $("atsBar");
  bar.style.width = "0";
  bar.style.background = scoreColor(ats.score);
  setTimeout(() => (bar.style.width = ats.score + "%"), 60);

  const list = $("atsChecks");
  list.replaceChildren();
  ats.checks.forEach(check => {
    const li = el("li", check.passed ? "pass" : "fail");
    li.appendChild(el("span", "ats-icon", check.passed ? "✅" : "⚠️"));
    const body = el("div");
    body.append(el("strong", null, check.label), el("p", "muted small", check.message));
    li.appendChild(body);
    list.appendChild(li);
  });
}

// ===== Render: recommended roles =====
const JOB_SITES = [
  ["LinkedIn", t => `https://www.linkedin.com/jobs/search/?keywords=${encodeURIComponent(t)}`],
  ["Indeed", t => `https://www.indeed.com/jobs?q=${encodeURIComponent(t)}`],
  ["Google Jobs", t => `https://www.google.com/search?q=${encodeURIComponent(t + " jobs")}`],
];

function renderRoles(ai, match) {
  const card = $("rolesCard");
  const roles = (ai && ai.suggested_roles) || [];
  if (!roles.length) {
    card.classList.add("hidden");
    return;
  }
  card.classList.remove("hidden");

  // Low match → show roles ABOVE the job match card with a helpful message
  const lowMatch = Boolean(match) && match.match_score < 40;
  $("rolesNotice").classList.toggle("hidden", !lowMatch);
  if (lowMatch) $("matchCard").before(card);
  else $("matchCard").after(card);

  const list = $("rolesList");
  list.replaceChildren();
  roles.forEach(role => {
    const item = el("div", "role-card");

    const head = el("div", "role-head");
    head.append(
      el("h4", null, role.title),
      el("span", `fit-badge ${role.fit === "High" ? "high" : "medium"}`, `${role.fit} fit`)
    );
    item.appendChild(head);
    if (role.reason) item.appendChild(el("p", "muted small", role.reason));

    if (role.matching_skills.length) {
      item.appendChild(el("p", "role-label", "✅ Your matching skills"));
      const chips = el("div", "chips");
      fillChips(chips, role.matching_skills, "good");
      item.appendChild(chips);
    }
    if (role.skills_to_learn.length) {
      item.appendChild(el("p", "role-label", "📚 Skills to learn"));
      const chips = el("div", "chips");
      fillChips(chips, role.skills_to_learn, "neutral");
      item.appendChild(chips);
    }

    const links = el("div", "role-links");
    JOB_SITES.forEach(([name, buildUrl]) => {
      const a = el("a", "btn-small", name);
      a.href = buildUrl(role.title);
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      links.appendChild(a);
    });
    item.appendChild(links);
    list.appendChild(item);
  });
}

// ===== Render: skills =====
function renderSkills(skills) {
  $("skillCount").textContent = skills.count;
  const box = $("skillsByCategory");
  box.replaceChildren();
  Object.entries(skills.by_category)
    .sort((a, b) => b[1].length - a[1].length)
    .forEach(([category, list]) => {
      const group = el("div", "skill-group");
      group.appendChild(el("h4", null, `${category} (${list.length})`));
      const chips = el("div", "chips");
      fillChips(chips, list, "neutral");
      group.appendChild(chips);
      box.appendChild(group);
    });
}

// ===== Render: AI feedback =====
function renderAI(ai, aiUsed) {
  $("aiNotice").classList.toggle("hidden", aiUsed);
  const card = $("aiCard");
  if (!ai) {
    card.classList.add("hidden");
    return;
  }
  card.classList.remove("hidden");
  $("overallFeedback").textContent = ai.overall_feedback;
  $("proSummary").textContent = ai.professional_summary;
  fillList($("strengths"), ai.strengths);
  fillList($("improvements"), ai.improvements);
}

function renderTips(tips) {
  fillList($("tips"), tips.length ? tips : ["Great job — no quick fixes needed! 🎉"]);
}

// ===== Show / hide views =====
const uploadView = [form, $("features"), $("hero")];
const results = $("results");

function showResults(data) {
  renderScore(data.score);
  renderMatch(data.match);
  renderATS(data.ats);
  renderRoles(data.ai, data.match);
  renderSkills(data.skills);
  renderAI(data.ai, data.ai_used);
  renderTips(data.score.tips);

  uploadView.forEach(node => node.classList.add("hidden"));
  results.classList.remove("hidden");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

$("newAnalysis").addEventListener("click", () => {
  results.classList.add("hidden");
  uploadView.forEach(node => node.classList.remove("hidden"));
  form.reset();
  fileName.textContent = "";
  errorMsg.textContent = "";
  window.scrollTo({ top: 0, behavior: "smooth" });
});

$("copySummary").addEventListener("click", async () => {
  const btn = $("copySummary");
  try {
    await navigator.clipboard.writeText($("proSummary").textContent);
    btn.textContent = "✅ Copied";
  } catch (e) {
    btn.textContent = "❌ Copy failed";
  }
  setTimeout(() => (btn.textContent = "📋 Copy"), 1800);
});

// ===== Submit with fetch (no page reload) =====
form.addEventListener("submit", async e => {
  e.preventDefault();
  const error = validateFile(fileInput.files[0]);
  if (error) {
    errorMsg.textContent = error;
    return;
  }
  errorMsg.textContent = "";
  setLoading(true);

  try {
    const response = await fetch("/analyze", { method: "POST", body: new FormData(form) });
    const data = await response.json().catch(() => ({ error: "Unexpected server response." }));
    if (!response.ok || data.error) throw new Error(data.error || "Something went wrong.");
    showResults(data);
  } catch (err) {
    errorMsg.textContent = err.message;
  } finally {
    setLoading(false);
  }
});

// ===== Download PDF report (browser "Save as PDF") =====
$("downloadReport").addEventListener("click", () => {
  $("reportMeta").textContent = `ResumeIQ Report · Generated ${new Date().toLocaleString()}`;
  window.print();
});