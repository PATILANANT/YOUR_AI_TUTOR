// ============================================================
// app.js — Shared state, API helpers, auth, and utilities
// ============================================================

const API_BASE = "";

// ---------- State Management (localStorage) ----------

function getUser() {
  const raw = localStorage.getItem("ai_tutor_user");
  return raw ? JSON.parse(raw) : null;
}

function setUser(user) {
  localStorage.setItem("ai_tutor_user", JSON.stringify(user));
}

function clearUser() {
  localStorage.removeItem("ai_tutor_user");
}

function getProfile() {
  const raw = localStorage.getItem("ai_tutor_profile");
  return raw
    ? JSON.parse(raw)
    : { goal: null, syllabus: [], progress: {}, weak_topics: {} };
}

function setProfile(profile) {
  localStorage.setItem("ai_tutor_profile", JSON.stringify(profile));
}

function getMessages() {
  const raw = localStorage.getItem("ai_tutor_messages");
  return raw ? JSON.parse(raw) : [];
}

function setMessages(messages) {
  localStorage.setItem("ai_tutor_messages", JSON.stringify(messages));
}

function clearMessages() {
  localStorage.removeItem("ai_tutor_messages");
}

// ---------- Auth Guard ----------

function requireAuth() {
  const user = getUser();
  if (!user || !user.user_id) {
    window.location.href = "login.html";
    return false;
  }
  return true;
}

// ---------- API Helper ----------

async function apiCall(endpoint, method = "GET", body = null) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };

  if (body && method !== "GET") {
    opts.body = JSON.stringify(body);
  }

  const res = await fetch(`${API_BASE}${endpoint}`, opts);

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "API Error");
  }

  return res.json();
}

async function apiUpload(endpoint, formData) {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Upload Error");
  }

  return res.json();
}

// ---------- Toast Notifications ----------

function showToast(message, type = "success") {
  const existing = document.getElementById("toast-container");
  if (existing) existing.remove();

  const colors = {
    success: "bg-emerald-600",
    error: "bg-red-600",
    info: "bg-indigo-600",
    warning: "bg-amber-600",
  };

  const container = document.createElement("div");
  container.id = "toast-container";
  container.className = `fixed top-6 right-6 z-[9999] px-5 py-3 rounded-xl text-white text-sm font-medium shadow-2xl ${colors[type] || colors.info} transition-all duration-300 transform translate-x-0 opacity-100`;
  container.textContent = message;
  document.body.appendChild(container);

  setTimeout(() => {
    container.classList.add("opacity-0", "translate-x-4");
    setTimeout(() => container.remove(), 300);
  }, 3000);
}

// ---------- Quiz Parser (mirrors Python parse_quiz) ----------

function parseQuiz(quizText) {
  const questions = [];
  const lines = quizText.trim().split("\n");

  for (const line of lines) {
    if (line.includes("|")) {
      const parts = line.split("|");
      if (parts.length >= 7) {
        questions.push({
          question: parts[1].trim(),
          options: [
            parts[2].trim(),
            parts[3].trim(),
            parts[4].trim(),
            parts[5].trim(),
          ],
          answer: parts[6].trim().toLowerCase()[0],
        });
      }
    }
  }

  return questions;
}

// ---------- Performance Analysis (mirrors smart_engine.py) ----------

function analyzePerformance(profile) {
  const progress = profile.progress || {};
  const weakTopics = profile.weak_topics || {};

  const keys = Object.keys(progress);
  if (keys.length === 0) {
    return { status: "start", message: "Start learning by asking a topic." };
  }

  const scores = Object.values(progress);
  const avgScore = scores.reduce((a, b) => a + b, 0) / scores.length;

  return {
    avg_score: avgScore,
    weak_topics: Object.keys(weakTopics),
    total_topics: keys.length,
  };
}

// ---------- Markdown Renderer ----------

function renderMarkdown(text) {
  if (typeof marked !== "undefined") {
    return marked.parse(text);
  }
  // Basic fallback
  return text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/\n/g, "<br>");
}

// ---------- Navbar Auth State ----------

function updateNavAuth() {
  const user = getUser();
  const authArea = document.getElementById("nav-auth");
  if (!authArea) return;

  if (user && user.user_id) {
    authArea.innerHTML = `
      <span class="text-zinc-400 text-sm mr-3">Hi, <span class="text-indigo-400 font-semibold">${user.username}</span></span>
      <button onclick="logout()" class="px-4 py-2 text-sm rounded-lg bg-zinc-700/60 hover:bg-red-600/80 text-zinc-300 hover:text-white transition-all duration-200">Logout</button>
    `;
  } else {
    authArea.innerHTML = `
      <a href="login.html" class="px-5 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-all duration-200 font-medium">Login</a>
    `;
  }
}

function logout() {
  clearUser();
  clearMessages();
  localStorage.removeItem("ai_tutor_profile");
  showToast("Logged out", "info");
  setTimeout(() => (window.location.href = "index.html"), 500);
}

// ---------- Init on every page ----------

document.addEventListener("DOMContentLoaded", () => {
  updateNavAuth();
});
