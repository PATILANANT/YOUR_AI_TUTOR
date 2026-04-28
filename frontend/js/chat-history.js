// ============================================================
// chat-history.js — Chat history sidebar & conversation management
// ============================================================

let activeConvId = getCurrentConversationId();

// --- Refresh sidebar conversation list ---
async function refreshConversationList() {
  const list = document.getElementById('conv-list');
  if (!list) return;

  try {
    const convs = await loadConversationList();
    list.innerHTML = '';

    if (convs.length === 0) {
      list.innerHTML = '<p class="text-xs text-zinc-500 px-3 py-4 text-center">No conversations yet</p>';
      return;
    }

    convs.forEach(c => {
      const isActive = String(c.id) === String(activeConvId);
      const item = document.createElement('div');
      item.className = `group flex items-center gap-2 px-3 py-2.5 rounded-xl cursor-pointer transition-all text-sm ${isActive ? 'bg-indigo-600/15 text-indigo-300 border border-indigo-500/20' : 'text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200 border border-transparent'}`;
      item.dataset.convId = c.id;
      item.onclick = (e) => {
        if (e.target.closest('.conv-actions')) return;
        switchConversation(c.id);
      };

      const title = c.title || 'New Chat';
      const shortTitle = title.length > 28 ? title.slice(0, 28) + '…' : title;

      item.innerHTML = `
        <svg class="w-4 h-4 flex-shrink-0 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/></svg>
        <span class="flex-1 truncate">${shortTitle}</span>
        <div class="conv-actions hidden group-hover:flex items-center gap-0.5">
          <button onclick="renameConv(${c.id}, event)" class="p-1 rounded hover:bg-zinc-700/60" title="Rename">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
          </button>
          <button onclick="deleteConv(${c.id}, event)" class="p-1 rounded hover:bg-red-600/30 hover:text-red-400" title="Delete">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
          </button>
        </div>`;
      list.appendChild(item);
    });
  } catch (e) {
    console.error('Failed to load conversations:', e);
  }
}

// --- Switch to a conversation ---
async function switchConversation(convId) {
  activeConvId = String(convId);
  setCurrentConversationId(convId);

  // Close history panel on mobile
  if (window.innerWidth < 1024) {
    const panel = document.getElementById('history-panel');
    if (!panel.classList.contains('-translate-x-full')) {
        panel.classList.add('-translate-x-full');
    }
  }

  // Clear current chat UI
  const container = document.getElementById('chat-messages');
  container.innerHTML = '';

  // Hide quiz
  document.getElementById('quiz-section').classList.add('hidden');
  quizQuestions = [];
  quizAnswers = [];

  // Load conversation profile from server
  try {
    const profile = await loadConversationProfileFromServer(convId);
    if (profile) {
      setProfile(profile, convId);
    } else {
      // Reset to empty profile for this conversation
      setProfile({ goal: null, syllabus: [], progress: {}, weak_topics: {} }, convId);
    }
  } catch (e) {
    console.error('Failed to load conversation profile:', e);
  }

  // Load messages from server
  try {
    const msgs = await loadConversationMessages(convId);
    if (msgs.length === 0) {
      container.innerHTML = `<div id="welcome-state" class="flex flex-col items-center justify-center h-full text-center">
        <div class="w-16 h-16 rounded-2xl bg-indigo-600/15 flex items-center justify-center text-3xl mb-5">🎓</div>
        <h2 class="text-2xl font-bold mb-2">Ready to Learn?</h2>
        <p class="text-zinc-400 max-w-md text-sm leading-relaxed">Ask any topic below and your AI tutor will teach you.</p>
      </div>`;
    } else {
      // Clear localStorage and populate from DB
      clearMessages();
      msgs.forEach(m => {
        appendBubble(m.role, m.content, false);
      });
      // Synchronize localStorage with the loaded conversation
      setMessages(msgs.map(m => ({ role: m.role, content: m.content })));
    }
    scrollChat();
  } catch (e) {
    console.error('Failed to load messages:', e);
    showToast('Failed to load messages', 'error');
  }

  refreshConversationList();
}

// --- Start a new chat ---
async function startNewChat() {
  clearCurrentConversationId();
  clearMessages();
  activeConvId = null;

  // Reset profile for new conversation
  setProfile({ goal: null, syllabus: [], progress: {}, weak_topics: {} });

  // Close history panel on mobile
  if (window.innerWidth < 1024) {
    const panel = document.getElementById('history-panel');
    panel.classList.add('-translate-x-full');
  }

  quizQuestions = [];
  quizAnswers = [];
  document.getElementById('quiz-section').classList.add('hidden');

  const container = document.getElementById('chat-messages');
  container.innerHTML = `<div id="welcome-state" class="flex flex-col items-center justify-center h-full text-center">
    <div class="w-16 h-16 rounded-2xl bg-indigo-600/15 flex items-center justify-center text-3xl mb-5">🎓</div>
    <h2 class="text-2xl font-bold mb-2">Ready to Learn?</h2>
    <p class="text-zinc-400 max-w-md text-sm leading-relaxed">Ask any topic below and your AI tutor will teach you.</p>
  </div>`;

  refreshConversationList();
}

// --- Rename ---
async function renameConv(convId, event) {
  event.stopPropagation();
  const newTitle = prompt('Enter new name:');
  if (!newTitle || !newTitle.trim()) return;
  try {
    await renameConversationAPI(convId, newTitle.trim());
    showToast('Chat renamed', 'success');
    refreshConversationList();
  } catch (e) {
    showToast('Rename failed', 'error');
  }
}

// --- Delete ---
async function deleteConv(convId, event) {
  event.stopPropagation();
  if (!confirm('Delete this conversation?')) return;
  try {
    await deleteConversationAPI(convId);
    showToast('Chat deleted', 'info');
    if (String(convId) === String(activeConvId)) {
      startNewChat();
    }
    refreshConversationList();
  } catch (e) {
    showToast('Delete failed', 'error');
  }
}

// --- Toggle history panel on mobile ---
function toggleHistoryPanel() {
  const panel = document.getElementById('history-panel');
  panel.classList.toggle('-translate-x-full');
}
