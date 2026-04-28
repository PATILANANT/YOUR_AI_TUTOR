// ============================================================
// features.js — Knowledge Graph, YouTube, Voice, Mastery
// ============================================================

// ==================== KNOWLEDGE GRAPH ====================

let kgNetwork = null;

async function buildKnowledgeGraph() {
  const user = getUser();
  if (!user) return showToast('Please login first', 'error');

  const btn = document.getElementById('kg-btn');
  const statusEl = document.getElementById('kg-status');
  btn.disabled = true;
  statusEl.textContent = '🔄 Extracting concepts from PDF...';
  statusEl.classList.remove('hidden');
  statusEl.className = 'text-xs text-amber-400 mt-1.5';

  try {
    const res = await apiCall('/knowledge_graph/extract', 'POST', {
      user_id: String(user.user_id)
    });

    statusEl.textContent = `✅ Found ${res.node_count} concepts, ${res.edge_count} connections`;
    statusEl.className = 'text-xs text-emerald-400 mt-1.5';

    renderKnowledgeGraph(res.graph);
    showToast(`Concept Map: ${res.node_count} concepts found`, 'success');
  } catch (err) {
    statusEl.textContent = '❌ ' + err.message;
    statusEl.className = 'text-xs text-red-400 mt-1.5';
    showToast('Knowledge graph failed: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
  }
}

async function loadKnowledgeGraph() {
  const user = getUser();
  if (!user) return;
  try {
    const res = await apiCall(`/knowledge_graph/${user.user_id}`);
    if (res.node_count > 0) {
      renderKnowledgeGraph(res.graph);
    }
  } catch (e) { /* no graph yet */ }
}

function renderKnowledgeGraph(graphData) {
  const section = document.getElementById('kg-section');
  const container = document.getElementById('kg-container');
  const statsEl = document.getElementById('kg-stats');
  section.classList.remove('hidden');

  const nodes = new vis.DataSet(graphData.nodes);
  const edges = new vis.DataSet(graphData.edges);

  const options = {
    physics: {
      forceAtlas2Based: { gravitationalConstant: -30, centralGravity: 0.005, springLength: 120 },
      solver: 'forceAtlas2Based',
      stabilization: { iterations: 100 }
    },
    nodes: {
      shape: 'dot',
      scaling: { min: 10, max: 30 },
      font: { color: '#ffffff', size: 12, face: 'Inter' },
      borderWidth: 2
    },
    edges: {
      width: 1,
      smooth: { type: 'curvedCW', roundness: 0.2 }
    },
    interaction: {
      hover: true,
      tooltipDelay: 200,
      navigationButtons: false
    }
  };

  if (kgNetwork) kgNetwork.destroy();
  kgNetwork = new vis.Network(container, { nodes, edges }, options);

  // Show stats
  const mastered = graphData.nodes.filter(n => n.mastery >= 70).length;
  const developing = graphData.nodes.filter(n => n.mastery >= 40 && n.mastery < 70).length;
  const unlearned = graphData.nodes.filter(n => n.mastery < 40).length;

  statsEl.innerHTML = `
    <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-emerald-400"></span> Mastered: ${mastered}</span>
    <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-amber-400"></span> Developing: ${developing}</span>
    <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-indigo-400"></span> Unlearned: ${unlearned}</span>
    <span>Total: ${graphData.nodes.length} concepts</span>
  `;

  // Click handler for nodes
  kgNetwork.on('click', function (params) {
    if (params.nodes.length > 0) {
      const nodeId = params.nodes[0];
      const node = graphData.nodes.find(n => n.id === nodeId);
      if (node) {
        const input = document.getElementById('chat-input');
        input.value = `Explain ${node.label} in detail`;
        input.focus();
      }
    }
  });
}


// ==================== YOUTUBE INTEGRATION ====================

async function ingestYouTube() {
  const urlInput = document.getElementById('yt-url');
  const url = urlInput.value.trim();
  if (!url) return showToast('Please paste a YouTube URL', 'warning');

  const user = getUser();
  if (!user) return showToast('Please login first', 'error');

  const btn = document.getElementById('yt-btn');
  const statusEl = document.getElementById('yt-status');
  btn.disabled = true;
  statusEl.textContent = '🔄 Extracting transcript...';
  statusEl.classList.remove('hidden');
  statusEl.className = 'text-xs text-amber-400 mt-1.5';

  try {
    const res = await apiCall('/youtube_ingest', 'POST', {
      url: url,
      user_id: String(user.user_id)
    });

    statusEl.textContent = `✅ Video processed (${res.chunks_added} chunks added)`;
    statusEl.className = 'text-xs text-emerald-400 mt-1.5';

    // Show summary in chat
    const summary = res.summary || 'Video transcript added to your knowledge base.';
    appendBubble('assistant', `## 🎬 YouTube Video Summary\n\n${summary}\n\n*${res.chunks_added} chunks added to your knowledge base. Use Normal Tutor mode to ask questions about it.*`);

    pdfUploaded = true; // Enable RAG mode
    urlInput.value = '';
    showToast('YouTube video processed!', 'success');
  } catch (err) {
    statusEl.textContent = '❌ ' + err.message;
    statusEl.className = 'text-xs text-red-400 mt-1.5';
    showToast('YouTube failed: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
  }
}


// ==================== VOICE RECORDING ====================

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

async function toggleRecording() {
  if (isRecording) {
    stopRecording();
  } else {
    startRecording();
  }
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
      await transcribeAudio(audioBlob);
    };

    mediaRecorder.start();
    isRecording = true;

    const btn = document.getElementById('voice-btn');
    const label = document.getElementById('voice-label');
    btn.classList.add('border-red-500', 'text-red-400');
    btn.classList.remove('border-zinc-600/50', 'text-zinc-400');
    label.innerHTML = '<span class="rec-pulse">●</span> Recording... (tap to stop)';

    // Auto-stop after 60 seconds
    setTimeout(() => { if (isRecording) stopRecording(); }, 60000);
  } catch (err) {
    showToast('Microphone access denied', 'error');
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }
  isRecording = false;

  const btn = document.getElementById('voice-btn');
  const label = document.getElementById('voice-label');
  btn.classList.remove('border-red-500', 'text-red-400');
  btn.classList.add('border-zinc-600/50', 'text-zinc-400');
  label.textContent = 'Record Doubt';
}

async function transcribeAudio(blob) {
  const user = getUser();
  if (!user) return;

  const statusEl = document.getElementById('voice-status');
  statusEl.textContent = '🔄 Transcribing...';
  statusEl.classList.remove('hidden');
  statusEl.className = 'text-xs text-amber-400 mt-1.5';

  try {
    const formData = new FormData();
    formData.append('user_id', String(user.user_id));
    formData.append('audio', blob, 'voice_note.webm');

    const res = await apiUpload('/voice_transcribe', formData);
    const text = res.transcription;

    if (text) {
      document.getElementById('chat-input').value = text;
      statusEl.textContent = '✅ Transcribed! Review and hit Send.';
      statusEl.className = 'text-xs text-emerald-400 mt-1.5';
      showToast('Voice transcribed!', 'success');
    } else {
      statusEl.textContent = '❌ Could not understand audio';
      statusEl.className = 'text-xs text-red-400 mt-1.5';
    }
  } catch (err) {
    statusEl.textContent = '❌ ' + err.message;
    statusEl.className = 'text-xs text-red-400 mt-1.5';
    showToast('Transcription failed', 'error');
  }
}


// ==================== TOPIC MASTERY ====================

// Mastery panel is now on the Dashboard page.
// This function is called after quiz submission on the learning page.
async function showMasteryAfterQuiz(conceptsTracked) {
  if (!conceptsTracked || conceptsTracked.length === 0) return;
  const names = conceptsTracked.map(c => c.charAt(0).toUpperCase() + c.slice(1)).join(', ');
  showToast(`Mastery tracked: ${names}. Check Dashboard for details!`, 'info');
}

