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

function getProfile(convId) {
  const key = convId ? `ai_tutor_profile_${convId}` : "ai_tutor_profile";
  const raw = localStorage.getItem(key);
  return raw
    ? JSON.parse(raw)
    : { goal: null, syllabus: [], progress: {}, weak_topics: {} };
}

function setProfile(profile, convId) {
  const key = convId ? `ai_tutor_profile_${convId}` : "ai_tutor_profile";
  localStorage.setItem(key, JSON.stringify(profile));
  // Also update global profile for backward compatibility
  if (convId) {
    localStorage.setItem("ai_tutor_profile", JSON.stringify(profile));
  }
}

function clearConversationProfile(convId) {
  if (convId) {
    localStorage.removeItem(`ai_tutor_profile_${convId}`);
  }
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

// ---------- Conversation Management ----------

function getCurrentConversationId() {
  return localStorage.getItem("ai_tutor_current_conv_id");
}

function setCurrentConversationId(id) {
  localStorage.setItem("ai_tutor_current_conv_id", String(id));
}

function clearCurrentConversationId() {
  localStorage.removeItem("ai_tutor_current_conv_id");
}

async function createConversation(title = "New Chat") {
  const user = getUser();
  if (!user) return null;
  const res = await apiCall("/conversations", "POST", {
    user_id: user.user_id,
    title,
  });
  setCurrentConversationId(res.conversation_id);
  return res.conversation_id;
}

async function loadConversationList() {
  const user = getUser();
  if (!user) return [];
  const res = await apiCall(`/conversations/${user.user_id}`);
  return res.conversations || [];
}

async function loadConversationMessages(convId) {
  const user = getUser();
  if (!user || !convId) return [];
  const res = await apiCall(`/messages/${convId}`);
  return res.messages || [];
}

async function saveMessageToServer(role, content) {
  const user = getUser();
  if (!user) return;

  let convId = getCurrentConversationId();

  // Auto-create a conversation if none is active
  if (!convId) {
    convId = await createConversation("New Chat");
  }

  const res = await apiCall(`/conversations/${convId}/message`, "POST", {
    role,
    content,
    user_id: user.user_id,
  });

  // If the server auto-titled the conversation, refresh sidebar
  if (res.auto_title && typeof refreshConversationList === "function") {
    refreshConversationList();
  }

  return res;
}

// ---------- Conversation Profile API ----------

async function loadConversationProfileFromServer(convId) {
  if (!convId) return null;
  try {
    const res = await apiCall(`/conversations/${convId}/profile`);
    return res.profile || null;
  } catch (e) {
    console.error('Failed to load conversation profile:', e);
    return null;
  }
}

async function saveConversationProfileToServer(convId, profile) {
  const user = getUser();
  if (!user || !convId) return;
  try {
    await apiCall(`/conversations/${convId}/profile`, "POST", {
      user_id: user.user_id,
      profile
    });
  } catch (e) {
    console.error('Failed to save conversation profile:', e);
  }
}

async function loadConversationMasteryFromServer(convId) {
  if (!convId) return null;
  try {
    const res = await apiCall(`/conversations/${convId}/mastery`);
    return res;
  } catch (e) {
    console.error('Failed to load conversation mastery:', e);
    return null;
  }
}

async function loadUserConversationsWithProfiles() {
  const user = getUser();
  if (!user) return [];
  try {
    const res = await apiCall(`/user/${user.user_id}/conversations_with_profiles`);
    return res.conversations || [];
  } catch (e) {
    console.error('Failed to load conversations with profiles:', e);
    return [];
  }
}

async function renameConversationAPI(convId, newTitle) {
  const user = getUser();
  if (!user) return;
  await apiCall(`/conversations/${convId}/rename`, "PUT", {
    user_id: user.user_id,
    title: newTitle,
  });
}

async function deleteConversationAPI(convId) {
  const user = getUser();
  if (!user) return;
  await apiCall(`/conversations/${convId}?user_id=${user.user_id}`, "DELETE");
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
  clearCurrentConversationId();
  // Clear all conversation profiles from localStorage
  const keys = Object.keys(localStorage);
  keys.forEach(k => {
    if (k.startsWith('ai_tutor_profile')) localStorage.removeItem(k);
  });
  showToast("Logged out", "info");
  setTimeout(() => (window.location.href = "index.html"), 500);
}

// ---------- Init on every page ----------

document.addEventListener("DOMContentLoaded", () => {
  updateNavAuth();
});
