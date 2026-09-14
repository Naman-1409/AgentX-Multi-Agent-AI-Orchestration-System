// Multi-Agent Collaborative System - Frontend App Logic

const API_BASE = window.location.origin;

// Application State
const state = {
  currentUser: JSON.parse(localStorage.getItem('currentUser') || 'null'),
  currentProject: null,
  activeTab: 'tasks',
  eventSource: null,
  projects: []
};

// Track if user explicitly edited the path
let isUserCustomizedPath = false;

// DOM Elements
const authView = document.getElementById('auth-view');
const dashboardView = document.getElementById('dashboard-view');
const meetingView = document.getElementById('meeting-view');
const loginForm = document.getElementById('login-form');
const userDisplay = document.getElementById('user-display');
const btnLogout = document.getElementById('btn-logout');
const brandHome = document.getElementById('brand-home');

const projectListGrid = document.getElementById('project-list-grid');
const newProjectModal = document.getElementById('new-project-modal');
const btnNewProjectModal = document.getElementById('btn-new-project-modal');
const btnCloseProjectModal = document.getElementById('btn-close-project-modal');
const newProjectForm = document.getElementById('new-project-form');
const newProjectTitle = document.getElementById('new-project-title');
const newProjectPath = document.getElementById('new-project-path');

const settingsModal = document.getElementById('settings-modal');
const btnOpenSettings = document.getElementById('btn-open-settings');
const btnCloseSettingsModal = document.getElementById('btn-close-settings-modal');
const settingsForm = document.getElementById('settings-form');

const btnBackDashboard = document.getElementById('btn-back-dashboard');
const btnDeleteProject = document.getElementById('btn-delete-project');
const btnStartRun = document.getElementById('btn-start-run');
const meetingMessagesContainer = document.getElementById('meeting-messages-container');
const meetingHumanForm = document.getElementById('meeting-human-form');
const meetingHumanInput = document.getElementById('meeting-human-input');
const subtasksContainer = document.getElementById('subtasks-container');
const deliverableContainer = document.getElementById('deliverable-container');

// Resizer & Slider Elements
const panelWidthSlider = document.getElementById('panel-width-slider');
const sliderPctLabel = document.getElementById('slider-pct-label');
const paneResizer = document.getElementById('pane-resizer');

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
  setupEventListeners();
  initWorkspaceResizer();
  if (state.currentUser) {
    showDashboard();
  } else {
    showAuth();
  }
});

// Helper to clean terminal prompt paste
function cleanTerminalPrompt(str) {
  if (!str) return '';
  let clean = str.trim();
  // If user pasted something like "arpitsaxena683gmail.com@Arpits-MacBook-Air-2 temp %"
  const match = clean.match(/[\s:@~]([a-zA-Z0-9_\-\.\/]+)\s*[%$#]\s*$/);
  if (match) {
    clean = match[1].trim();
  } else if (clean.endsWith('%') || clean.endsWith('$') || clean.endsWith('#')) {
    const parts = clean.replace(/[%$#\s]+$/, '').split(/\s+/);
    if (parts.length > 0) clean = parts[parts.length - 1];
  }
  return clean;
}

// --- Event Listeners ---
function setupEventListeners() {
  // Brand / Home navigation
  brandHome.addEventListener('click', () => {
    if (state.currentUser) showDashboard();
  });

  // Track if user manually changes storage path
  newProjectPath.addEventListener('input', () => {
    isUserCustomizedPath = true;
  });

  // Auto-generate target path ONLY if user hasn't manually customized it
  newProjectTitle.addEventListener('input', () => {
    if (!isUserCustomizedPath) {
      const titleVal = newProjectTitle.value.trim();
      if (titleVal) {
        const slug = titleVal.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
        newProjectPath.value = `/Volumes/VAIBHAV/major project/generated_projects/${slug}`;
      }
    }
  });

  // Auth Form Submit
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    try {
      const resp = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await resp.json();
      if (resp.ok) {
        state.currentUser = data.user;
        localStorage.setItem('currentUser', JSON.stringify(data.user));
        showDashboard();
      } else {
        alert(data.detail || 'Login failed');
      }
    } catch (err) {
      console.error(err);
      alert('Error connecting to backend API');
    }
  });

  // Logout
  btnLogout.addEventListener('click', () => {
    state.currentUser = null;
    localStorage.removeItem('currentUser');
    if (state.eventSource) state.eventSource.close();
    showAuth();
  });

  // Modals
  btnNewProjectModal.addEventListener('click', () => {
    isUserCustomizedPath = false;
    newProjectForm.reset();
    newProjectModal.classList.remove('hidden');
    newProjectPath.value = `/Volumes/VAIBHAV/major project/generated_projects/my_project`;
  });
  btnCloseProjectModal.addEventListener('click', () => {
    newProjectModal.classList.add('hidden');
  });
  btnOpenSettings.addEventListener('click', () => {
    loadSettings();
    settingsModal.classList.remove('hidden');
  });
  btnCloseSettingsModal.addEventListener('click', () => {
    settingsModal.classList.add('hidden');
  });

  // New Project Form Submit
  newProjectForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const title = newProjectTitle.value.trim();
    const description = document.getElementById('new-project-desc').value.trim();
    const goal = document.getElementById('new-project-goal').value.trim();
    const model = document.getElementById('new-project-model').value;
    const storage_path = cleanTerminalPrompt(newProjectPath.value);

    try {
      const resp = await fetch(`${API_BASE}/api/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          description,
          goal,
          storage_path,
          user_id: state.currentUser.id,
          config: { model }
        })
      });
      const data = await resp.json();
      if (resp.ok) {
        newProjectModal.classList.add('hidden');
        newProjectForm.reset();
        isUserCustomizedPath = false;
        openMeetingRoom(data.project.id);
      } else {
        alert('Failed to create project');
      }
    } catch (err) {
      console.error(err);
      alert('Error creating project');
    }
  });

  // Settings Form Submit
  settingsForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const gemini = document.getElementById('key-gemini').value;
    const openai = document.getElementById('key-openai').value;
    const anthropic = document.getElementById('key-anthropic').value;
    const ollama_url = document.getElementById('key-ollama').value;

    try {
      const resp = await fetch(`${API_BASE}/api/settings/keys`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gemini, openai, anthropic, ollama_url })
      });
      if (resp.ok) {
        alert('AI Gateway settings saved successfully');
        settingsModal.classList.add('hidden');
      }
    } catch (err) {
      alert('Failed to save settings');
    }
  });

  // Back to Dashboard (Auto-cleanup active runner port)
  btnBackDashboard.addEventListener('click', () => {
    if (state.eventSource) state.eventSource.close();
    // Auto-terminate any running sandbox process
    fetch(`${API_BASE}/api/runner/force-stop`, { method: 'POST' }).catch(() => {});
    showDashboard();
  });

  // Delete Project from Meeting Room Header
  if (btnDeleteProject) {
    btnDeleteProject.addEventListener('click', () => {
      if (state.currentProject) {
        deleteProject(state.currentProject.id, state.currentProject.title);
      }
    });
  }

  // Start Multi-Agent Run
  btnStartRun.addEventListener('click', async () => {
    if (!state.currentProject) return;
    const provider = state.currentProject.config?.model || 'smart_simulation';
    btnStartRun.disabled = true;
    btnStartRun.innerHTML = '⏳ Orchestrating Team...';

    try {
      const resp = await fetch(`${API_BASE}/api/projects/${state.currentProject.id}/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider })
      });
      if (!resp.ok) {
        alert('Failed to start orchestration run');
        btnStartRun.disabled = false;
        btnStartRun.innerHTML = '▶️ Run Multi-Agent Team';
      }
    } catch (err) {
      console.error(err);
      btnStartRun.disabled = false;
      btnStartRun.innerHTML = '▶️ Run Multi-Agent Team';
    }
  });

  // Human Message in Meeting Room
  meetingHumanForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const content = meetingHumanInput.value.trim();
    if (!content || !state.currentProject) return;

    // Clear input immediately
    meetingHumanInput.value = '';

    try {
      await fetch(`${API_BASE}/api/projects/${state.currentProject.id}/meeting/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sender: state.currentUser ? state.currentUser.name || state.currentUser.username : 'Human Observer',
          role: 'Human Observer',
          content: content
        })
      });
    } catch (err) {
      console.error(err);
    }
  });
}

// --- View Transitions ---
function showAuth() {
  authView.classList.remove('hidden');
  dashboardView.classList.add('hidden');
  meetingView.classList.add('hidden');
  userDisplay.textContent = '';
  btnLogout.classList.add('hidden');
  btnOpenSettings.classList.add('hidden');
}

function showDashboard() {
  authView.classList.add('hidden');
  dashboardView.classList.remove('hidden');
  meetingView.classList.add('hidden');
  userDisplay.textContent = `👤 ${state.currentUser.name || state.currentUser.username}`;
  btnLogout.classList.remove('hidden');
  btnOpenSettings.classList.remove('hidden');
  loadProjects();
}

async function loadProjects() {
  try {
    const resp = await fetch(`${API_BASE}/api/projects?user_id=${state.currentUser.id}`);
    const data = await resp.json();
    state.projects = data.projects || [];
    renderProjectsList();
  } catch (err) {
    console.error(err);
  }
}

function renderProjectsList() {
  projectListGrid.innerHTML = '';
  if (state.projects.length === 0) {
    projectListGrid.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 3rem 1rem; color: var(--text-secondary);">
        <p style="font-size: 1.1rem; margin-bottom: 1rem;">No projects created yet.</p>
        <button class="btn btn-primary" onclick="document.getElementById('btn-new-project-modal').click()">
          ✨ Create Your First Project
        </button>
      </div>
    `;
    return;
  }

  state.projects.forEach(p => {
    const card = document.createElement('div');
    card.className = 'project-card';
    card.onclick = () => openMeetingRoom(p.id);

    const dateStr = new Date(p.created_at).toLocaleString([], {
      month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit'
    });

    const statusBadge = `<span class="badge badge-${p.status}">${p.status.replace('_', ' ')}</span>`;
    const storagePathDisplay = p.storage_path ? `<div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.5rem; word-break: break-all;">📁 ${escapeHtml(p.storage_path)}</div>` : '';

    card.innerHTML = `
      <div>
        <div class="project-card-header">
          <h3 class="project-card-title">${escapeHtml(p.title)}</h3>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            ${statusBadge}
            <button class="btn-delete-card" title="Delete Project" onclick="event.stopPropagation(); deleteProject('${p.id}', '${escapeHtml(p.title)}');">
              🗑️
            </button>
          </div>
        </div>
        ${storagePathDisplay}
        <p class="project-card-desc">${escapeHtml(p.description || p.goal || 'No description provided.')}</p>
      </div>
      <div class="project-card-footer">
        <span>📅 ${dateStr}</span>
        <span style="color: var(--primary); font-weight: 600;">Open Meeting Room &rarr;</span>
      </div>
    `;
    projectListGrid.appendChild(card);
  });
}

// Delete Project Function
async function deleteProject(projectId, projectName) {
  const confirmed = confirm(`Are you sure you want to delete "${projectName || 'this project'}"? This action cannot be undone.`);
  if (!confirmed) return;

  try {
    const resp = await fetch(`${API_BASE}/api/projects/${projectId}`, {
      method: 'DELETE'
    });
    if (resp.ok) {
      if (state.currentProject && state.currentProject.id === projectId) {
        if (state.eventSource) state.eventSource.close();
        state.currentProject = null;
        showDashboard();
      } else {
        loadProjects();
      }
    } else {
      alert('Failed to delete project.');
    }
  } catch (err) {
    console.error(err);
    alert('Error connecting to backend API.');
  }
}

// --- Meeting Room Workspace ---
async function openMeetingRoom(projectId) {
  authView.classList.add('hidden');
  dashboardView.classList.add('hidden');
  meetingView.classList.remove('hidden');

  if (state.eventSource) {
    state.eventSource.close();
    state.eventSource = null;
  }

  // 1. Fully Clear Old Project In-Memory State & Files
  state.ideFiles = {};
  state.activeIdeFile = null;
  
  const fileListEl = document.getElementById('ide-file-list');
  const fileTabsEl = document.getElementById('ide-file-tabs');
  const codeEditorEl = document.getElementById('ide-code-editor');
  const currentFilenameEl = document.getElementById('ide-current-filename');
  const previewIframe = document.getElementById('ide-preview-iframe');

  if (fileListEl) fileListEl.innerHTML = '<div style="font-size:0.75rem; color:var(--text-muted); padding:0.5rem;">Loading files...</div>';
  if (fileTabsEl) fileTabsEl.innerHTML = '';
  if (codeEditorEl) codeEditorEl.value = '<!-- Loading project files... -->';
  if (currentFilenameEl) currentFilenameEl.textContent = 'index.html';
  if (previewIframe) previewIframe.src = 'about:blank';

  // Reset agent card indicators to idle
  ['ManagerAgent', 'FrontendAgent', 'BackendAgent', 'DatabaseAgent', 'IntegrationAgent', 'TestingAgent', 'DocumentationAgent'].forEach(ag => {
    updateAgentCard(ag, 'idle', 'Idle');
  });

  try {
    const resp = await fetch(`${API_BASE}/api/projects/${projectId}`);
    const data = await resp.json();
    state.currentProject = data.project;

    // Set Header Info
    document.getElementById('meeting-project-title').textContent = data.project.title;
    document.getElementById('meeting-project-desc').textContent = data.project.description || data.project.goal;
    
    const storageInfo = document.getElementById('meeting-storage-info');
    if (data.project.storage_path) {
      storageInfo.innerHTML = `📁 Storage Location: <code>${escapeHtml(data.project.storage_path)}</code>`;
    } else {
      storageInfo.innerHTML = '';
    }

    updateStatusBadge(data.project.status);
    renderInitialMeetingLogs(data.meeting_logs || []);
    renderSubtasks(data.subtasks || []);
    if (data.project.deliverable) {
      renderDeliverable(data.project.deliverable);
    } else {
      deliverableContainer.innerHTML = `
        <p style="color: var(--text-muted); font-size: 0.85rem; text-align: center; margin-top: 2rem;">
          Deliverables will be synthesized here upon completion of all worker tasks.
        </p>
      `;
    }

    if (data.room_state) {
      updateRoomState(data.room_state);
    }

    // Load actual files from project storage
    loadIdeFiles(projectId);

    // Connect SSE Stream
    connectMeetingSSE(projectId);

  } catch (err) {
    console.error(err);
    alert('Error loading meeting room');
  }
}

function connectMeetingSSE(projectId) {
  state.eventSource = new EventSource(`${API_BASE}/api/projects/${projectId}/meeting/stream`);
  const streamStatus = document.getElementById('stream-status');

  state.eventSource.onopen = () => {
    streamStatus.textContent = '● Live Connected';
    streamStatus.style.color = 'var(--success)';
  };

  state.eventSource.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      handleMeetingEvent(payload);
    } catch (e) {
      console.error(e);
    }
  };

  state.eventSource.onerror = () => {
    streamStatus.textContent = '○ Reconnecting...';
    streamStatus.style.color = 'var(--warning)';
  };
}

function handleMeetingEvent(event) {
  if (event.type === 'message') {
    appendMeetingMessage(event.data);
    if (event.data && (event.data.message_type === 'synthesis' || event.data.metadata?.deliverable)) {
      if (state.currentProject) {
        loadIdeFiles(state.currentProject.id);
        reloadSandboxIframe();
      }
    }
  } else if (event.type === 'agent_status_change') {
    updateAgentCard(event.agent, event.status, event.activity);
    if (event.room_state) updateRoomState(event.room_state);
  } else if (event.type === 'progress_update') {
    document.getElementById('meeting-progress-bar').style.width = `${event.progress}%`;
    if (event.status) updateStatusBadge(event.status);
  } else if (event.type === 'init') {
    if (event.room_state) updateRoomState(event.room_state);
  }
  
  // Reload subtasks when message updates
  if (state.currentProject) {
    fetchSubtasks(state.currentProject.id);
  }
}

function updateRoomState(roomState) {
  if (roomState.progress !== undefined) {
    document.getElementById('meeting-progress-bar').style.width = `${roomState.progress}%`;
  }
  if (roomState.agents) {
    Object.keys(roomState.agents).forEach(agentName => {
      const info = roomState.agents[agentName];
      updateAgentCard(agentName, info.status, info.activity);
    });
  }
}

function updateAgentCard(agentName, status, activity) {
  const indicator = document.getElementById(`indicator-${agentName}`);
  const statusText = document.getElementById(`status-text-${agentName}`);
  if (indicator) {
    indicator.className = `agent-status-indicator ${status}`;
  }
  if (statusText) {
    statusText.textContent = activity || status;
  }
}

function updateStatusBadge(status) {
  const badge = document.getElementById('meeting-status-badge');
  badge.className = `badge badge-${status}`;
  badge.textContent = status.replace('_', ' ');

  if (status === 'completed') {
    btnStartRun.disabled = false;
    btnStartRun.innerHTML = '🔄 Re-run Team';
    // Load deliverable
    if (state.currentProject) {
      fetch(`${API_BASE}/api/projects/${state.currentProject.id}`)
        .then(r => r.json())
        .then(d => {
          if (d.project.deliverable) renderDeliverable(d.project.deliverable);
        });
    }
  } else if (status === 'in_progress') {
    btnStartRun.disabled = true;
    btnStartRun.innerHTML = '⏳ Multi-Agent Team Running...';
  } else {
    btnStartRun.disabled = false;
    btnStartRun.innerHTML = '▶️ Run Multi-Agent Team';
  }
}

function renderInitialMeetingLogs(logs) {
  meetingMessagesContainer.innerHTML = '';
  logs.forEach(log => appendMeetingMessage(log));
}

function appendMeetingMessage(log) {
  const msgEl = document.createElement('div');
  msgEl.className = `meeting-message ${log.message_type || 'chat'}`;

  const timeStr = new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

  msgEl.innerHTML = `
    <div class="message-meta">
      <span class="message-sender">${escapeHtml(log.sender)} <small style="color: var(--text-muted);">(${escapeHtml(log.role)})</small></span>
      <span>${timeStr}</span>
    </div>
    <div class="message-content">${formatMarkdown(log.content)}</div>
  `;

  meetingMessagesContainer.appendChild(msgEl);
  meetingMessagesContainer.scrollTop = meetingMessagesContainer.scrollHeight;
}

async function fetchSubtasks(projectId) {
  try {
    const resp = await fetch(`${API_BASE}/api/projects/${projectId}/subtasks`);
    const data = await resp.json();
    renderSubtasks(data.subtasks || []);
  } catch (e) {}
}

function renderSubtasks(subtasks) {
  if (!subtasks || subtasks.length === 0) return;

  subtasksContainer.innerHTML = '';
  subtasks.forEach(st => {
    const item = document.createElement('div');
    item.className = 'subtask-item';
    
    const badgeClass = st.status === 'completed' ? 'badge-completed' : (st.status === 'in_progress' ? 'badge-in_progress' : 'badge-created');
    
    item.innerHTML = `
      <div class="subtask-item-header">
        <h5>${escapeHtml(st.title)}</h5>
        <span class="badge ${badgeClass}">${st.status}</span>
      </div>
      <p>${escapeHtml(st.description)}</p>
      <div style="font-size: 0.75rem; color: var(--primary); margin-top: 0.35rem;">
        Worker: ${escapeHtml(st.worker_type.toUpperCase())}
      </div>
    `;
    subtasksContainer.appendChild(item);
  });
}

function renderDeliverable(deliverable) {
  if (!deliverable) return;
  const storagePath = deliverable.storage_path || (state.currentProject ? state.currentProject.storage_path : '');
  const savedFiles = deliverable.saved_files || ['index.html', 'test.js', 'README.md'];

  const filesBadges = savedFiles.map(f => `<span style="background: rgba(99,102,241,0.15); border:1px solid rgba(99,102,241,0.3); padding:0.2rem 0.5rem; border-radius:6px; font-size:0.75rem; font-family:var(--font-mono); margin-right:0.4rem;">📄 ${f}</span>`).join(' ');

  deliverableContainer.innerHTML = `
    <div style="margin-bottom: 1.5rem;">
      <h3 style="font-size: 1.2rem; margin-bottom: 0.5rem; color: var(--success);">${escapeHtml(deliverable.title || 'Final Deliverable')}</h3>
      <p style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 1rem;">${escapeHtml(deliverable.summary || '')}</p>
      
      <!-- Disk Location & Live Preview -->
      <div class="glass-panel" style="padding: 1rem; margin-bottom: 1.25rem; border-color: rgba(16, 185, 129, 0.3);">
        <div style="font-size: 0.85rem; margin-bottom: 0.5rem;">
          📁 <strong>Physical Storage Location:</strong><br>
          <code style="word-break: break-all; color: var(--secondary);">${escapeHtml(storagePath)}</code>
        </div>
        <div style="margin-top: 0.5rem; font-size: 0.8rem; margin-bottom: 0.75rem;">
          <strong>Generated Files:</strong> ${filesBadges}
        </div>
        <div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
          <a href="/apps/${state.currentProject.id}/" target="_blank" class="btn btn-success" style="font-size: 0.85rem; padding: 0.5rem 1rem;">
            🚀 Open Live Web App Preview &rarr;
          </a>
        </div>
      </div>
    </div>

    ${deliverable.research ? `
      <div style="margin-bottom: 1.5rem;">
        <h4 style="font-size: 1rem; margin-bottom: 0.5rem; color: var(--secondary);">🔍 Architecture & Research Report</h4>
        <div class="glass-panel" style="padding: 1rem; font-size: 0.85rem;">
          ${formatMarkdown(deliverable.research)}
        </div>
      </div>
    ` : ''}

    ${deliverable.code ? `
      <div style="margin-bottom: 1.5rem;">
        <h4 style="font-size: 1rem; margin-bottom: 0.5rem; color: var(--primary);">💻 Application Source Code</h4>
        <div class="glass-panel" style="padding: 1rem; font-size: 0.85rem;">
          ${formatMarkdown(deliverable.code)}
        </div>
      </div>
    ` : ''}

    ${deliverable.tests ? `
      <div style="margin-bottom: 1.5rem;">
        <h4 style="font-size: 1rem; margin-bottom: 0.5rem; color: #10b981;">🧪 Automated Verification & Test Suite</h4>
        <div class="glass-panel" style="padding: 1rem; font-size: 0.85rem;">
          ${formatMarkdown(deliverable.tests)}
        </div>
      </div>
    ` : ''}

    ${deliverable.docs ? `
      <div style="margin-bottom: 1.5rem;">
        <h4 style="font-size: 1rem; margin-bottom: 0.5rem; color: var(--accent);">📝 Documentation & Usage Manual</h4>
        <div class="glass-panel" style="padding: 1rem; font-size: 0.85rem;">
          ${formatMarkdown(deliverable.docs)}
        </div>
      </div>
    ` : ''}
  `;
}

// --- Tabs Helper ---
window.switchSideTab = function(tabName) {
  const btnTasks = document.getElementById('tab-btn-tasks');
  const btnDeliverable = document.getElementById('tab-btn-deliverable');
  const btnIde = document.getElementById('tab-btn-ide');
  const contentTasks = document.getElementById('tab-content-tasks');
  const contentDeliverable = document.getElementById('tab-content-deliverable');
  const contentIde = document.getElementById('tab-content-ide');

  // Reset all
  [btnTasks, btnDeliverable, btnIde].forEach(b => b && b.classList.remove('active'));
  [contentTasks, contentDeliverable, contentIde].forEach(c => c && c.classList.add('hidden'));

  if (tabName === 'tasks') {
    btnTasks.classList.add('active');
    contentTasks.classList.remove('hidden');
  } else if (tabName === 'deliverable') {
    btnDeliverable.classList.add('active');
    contentDeliverable.classList.remove('hidden');
  } else if (tabName === 'ide') {
    btnIde.classList.add('active');
    contentIde.classList.remove('hidden');
    if (state.currentProject) {
      loadIdeFiles(state.currentProject.id);
      runSandboxRunner(state.currentProject.id);
    }
  }
};

// --- Live IDE & Compiler / Sandbox State & Helpers ---
state.ideFiles = {};
state.activeIdeFile = 'index.html';

async function loadIdeFiles(projectId) {
  if (!projectId) return;
  try {
    const resp = await fetch(`${API_BASE}/api/projects/${projectId}/files`);
    const data = await resp.json();
    state.ideFiles = data.files || {};
    renderIdeWorkspace();
  } catch (err) {
    console.error('Error loading IDE files:', err);
  }
}

function renderIdeWorkspace() {
  const fileListEl = document.getElementById('ide-file-list');
  const fileTabsEl = document.getElementById('ide-file-tabs');
  const codeEditorEl = document.getElementById('ide-code-editor');
  const currentFilenameEl = document.getElementById('ide-current-filename');

  const fileKeys = Object.keys(state.ideFiles);
  if (fileKeys.length === 0) {
    fileListEl.innerHTML = '<div style="font-size:0.75rem; color:var(--text-muted); padding:0.5rem;">No files created yet. Run the Multi-Agent team to generate files.</div>';
    fileTabsEl.innerHTML = '<span class="ide-file-tab active">📄 index.html</span>';
    codeEditorEl.value = '<!-- Files will appear here once generated by the Multi-Agent team -->';
    return;
  }

  // Ensure active file is valid
  if (!state.ideFiles[state.activeIdeFile]) {
    state.activeIdeFile = fileKeys[0];
  }

  // Render Sidebar Tree
  fileListEl.innerHTML = '';
  fileKeys.forEach(fn => {
    const item = document.createElement('div');
    item.className = `ide-tree-item ${fn === state.activeIdeFile ? 'active' : ''}`;
    item.onclick = () => selectIdeFile(fn);
    const icon = fn.endsWith('.html') ? '🌐' : (fn.endsWith('.js') ? '⚡' : (fn.endsWith('.css') ? '🎨' : (fn.endsWith('.md') ? '📝' : '📄')));
    item.innerHTML = `${icon} ${escapeHtml(fn)}`;
    fileListEl.appendChild(item);
  });

  // Render Tabs
  fileTabsEl.innerHTML = '';
  fileKeys.forEach(fn => {
    const tab = document.createElement('span');
    tab.className = `ide-file-tab ${fn === state.activeIdeFile ? 'active' : ''}`;
    tab.onclick = () => selectIdeFile(fn);
    const icon = fn.endsWith('.html') ? '🌐' : (fn.endsWith('.js') ? '⚡' : (fn.endsWith('.css') ? '🎨' : '📄'));
    tab.innerHTML = `${icon} ${escapeHtml(fn)}`;
    fileTabsEl.appendChild(tab);
  });

  // Update Editor Content
  currentFilenameEl.textContent = state.activeIdeFile;
  codeEditorEl.value = state.ideFiles[state.activeIdeFile]?.content || '';
}

function selectIdeFile(filename) {
  // Save in memory before switching
  const codeEditorEl = document.getElementById('ide-code-editor');
  if (state.ideFiles[state.activeIdeFile]) {
    state.ideFiles[state.activeIdeFile].content = codeEditorEl.value;
  }

  state.activeIdeFile = filename;
  renderIdeWorkspace();
}

// Save Code Back to Disk
async function saveIdeCode() {
  if (!state.currentProject || !state.activeIdeFile) return;
  const codeEditorEl = document.getElementById('ide-code-editor');
  const saveStatusEl = document.getElementById('ide-save-status');
  const content = codeEditorEl.value;

  saveStatusEl.textContent = '⏳ Saving...';
  saveStatusEl.style.color = 'var(--warning)';

  try {
    const resp = await fetch(`${API_BASE}/api/projects/${state.currentProject.id}/files/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename: state.activeIdeFile,
        content: content
      })
    });

    if (resp.ok) {
      if (state.ideFiles[state.activeIdeFile]) {
        state.ideFiles[state.activeIdeFile].content = content;
      }
      saveStatusEl.textContent = '✅ Saved & Synced';
      saveStatusEl.style.color = 'var(--success)';

      // Auto refresh sandbox preview
      reloadSandboxIframe();
    } else {
      saveStatusEl.textContent = '❌ Save failed';
      saveStatusEl.style.color = 'var(--danger)';
    }
  } catch (err) {
    console.error(err);
    saveStatusEl.textContent = '❌ Error';
    saveStatusEl.style.color = 'var(--danger)';
  }
}

// Start / Trigger Sandbox on Port 8080 with PID tracking
async function runSandboxRunner(projectId) {
  if (!projectId) return;
  const runBtn = document.getElementById('btn-run-sandbox');
  const stopBtn = document.getElementById('btn-stop-sandbox');
  if (runBtn) {
    runBtn.disabled = true;
    runBtn.innerHTML = '⏳ Launching Sandbox...';
  }

  try {
    const resp = await fetch(`${API_BASE}/api/projects/${projectId}/runner/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ port: 8080 })
    });
    const data = await resp.json();
    if (data.url) {
      const externalLink = document.getElementById('btn-external-sandbox');
      const iframe = document.getElementById('ide-preview-iframe');
      const cacheBustUrl = `${data.url}/?t=${Date.now()}`;
      if (externalLink) {
        externalLink.href = cacheBustUrl;
        externalLink.innerHTML = `🌐 Open Port ${data.port} →`;
      }
      if (iframe) iframe.src = cacheBustUrl;
      if (runBtn) {
        runBtn.innerHTML = `🟢 Running (PID: ${data.pid || 'Active'})`;
        runBtn.style.background = 'var(--success)';
      }
    }
  } catch (err) {
    console.error('Error starting runner on port 8080:', err);
    if (runBtn) {
      runBtn.innerHTML = '❌ Runner Error';
      runBtn.style.background = 'var(--danger)';
    }
  } finally {
    if (runBtn) runBtn.disabled = false;
  }
}

// Force Stop / Clean up Server on Port 8080
async function stopSandboxRunner() {
  const runBtn = document.getElementById('btn-run-sandbox');
  const stopBtn = document.getElementById('btn-stop-sandbox');
  const iframe = document.getElementById('ide-preview-iframe');

  if (stopBtn) {
    stopBtn.disabled = true;
    stopBtn.innerHTML = '⏳ Stopping...';
  }

  try {
    const resp = await fetch(`${API_BASE}/api/runner/force-stop`, { method: 'POST' });
    const data = await resp.json();
    if (iframe) iframe.src = 'about:blank';
    if (runBtn) {
      runBtn.innerHTML = '▶️ Run on Port 8080';
      runBtn.style.background = '';
    }
    if (stopBtn) {
      stopBtn.innerHTML = '🛑 Stopped';
      setTimeout(() => {
        stopBtn.innerHTML = '🛑 Force Stop Server';
        stopBtn.disabled = false;
      }, 1500);
    }
  } catch (err) {
    console.error('Error stopping sandbox runner:', err);
    if (stopBtn) {
      stopBtn.innerHTML = '❌ Error';
      stopBtn.disabled = false;
    }
  }
}

// Wire up Stop Server button
document.addEventListener('DOMContentLoaded', () => {
  const btnStop = document.getElementById('btn-stop-sandbox');
  if (btnStop) {
    btnStop.addEventListener('click', () => {
      stopSandboxRunner();
    });
  }
});

function reloadSandboxIframe() {
  const iframe = document.getElementById('ide-preview-iframe');
  const externalLink = document.getElementById('btn-external-sandbox');
  const baseUrl = externalLink ? externalLink.href.split('?')[0] : 'http://127.0.0.1:8080';
  if (iframe) {
    iframe.src = `${baseUrl.replace(/\/+$/, '')}/?t=${Date.now()}`;
  }
}

// --- Draggable Split Resizer & Slider Manager ---
function initWorkspaceResizer() {
  const slider = document.getElementById('panel-width-slider');
  const sliderLabel = document.getElementById('slider-pct-label');
  const resizer = document.getElementById('pane-resizer');
  const workspaceGrid = document.querySelector('.meeting-workspace-grid');
  const logCard = document.querySelector('.log-stream-card');
  const sideCard = document.querySelector('.side-panel-card');

  // Load saved preference (default 50%)
  const savedWidth = parseInt(localStorage.getItem('workspaceRightWidthPct') || '50', 10);
  applyPanelWidth(savedWidth);

  if (slider) {
    slider.value = savedWidth;
    slider.addEventListener('input', () => {
      const val = parseInt(slider.value, 10);
      applyPanelWidth(val);
    });
  }

  // Draggable Divider Handlers
  if (resizer && workspaceGrid) {
    let isDragging = false;

    resizer.addEventListener('mousedown', (e) => {
      isDragging = true;
      resizer.classList.add('active');
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    });

    document.addEventListener('mousemove', (e) => {
      if (!isDragging || !workspaceGrid) return;
      const rect = workspaceGrid.getBoundingClientRect();
      const relativeX = e.clientX - rect.left;
      const totalWidth = rect.width;
      
      const leftPct = (relativeX / totalWidth) * 100;
      let rightPct = Math.round(100 - leftPct);

      // Constrain between 20% and 80%
      rightPct = Math.max(20, Math.min(80, rightPct));
      applyPanelWidth(rightPct);
    });

    document.addEventListener('mouseup', () => {
      if (isDragging) {
        isDragging = false;
        resizer.classList.remove('active');
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      }
    });

    // Touch support for mobile/tablets
    resizer.addEventListener('touchstart', (e) => {
      isDragging = true;
      resizer.classList.add('active');
    }, { passive: true });

    document.addEventListener('touchmove', (e) => {
      if (!isDragging || !workspaceGrid || !e.touches[0]) return;
      const rect = workspaceGrid.getBoundingClientRect();
      const relativeX = e.touches[0].clientX - rect.left;
      const totalWidth = rect.width;
      
      const leftPct = (relativeX / totalWidth) * 100;
      let rightPct = Math.round(100 - leftPct);
      rightPct = Math.max(20, Math.min(80, rightPct));
      applyPanelWidth(rightPct);
    }, { passive: true });

    document.addEventListener('touchend', () => {
      if (isDragging) {
        isDragging = false;
        resizer.classList.remove('active');
      }
    });
  }
}

function applyPanelWidth(rightPct) {
  const logCard = document.querySelector('.log-stream-card');
  const sideCard = document.querySelector('.side-panel-card');
  const slider = document.getElementById('panel-width-slider');
  const sliderLabel = document.getElementById('slider-pct-label');

  const leftPct = 100 - rightPct;

  if (logCard) logCard.style.flex = `0 0 calc(${leftPct}% - 10px)`;
  if (sideCard) sideCard.style.flex = `0 0 calc(${rightPct}% - 10px)`;
  
  if (slider) slider.value = rightPct;
  if (sliderLabel) sliderLabel.textContent = `${rightPct}%`;

  localStorage.setItem('workspaceRightWidthPct', rightPct.toString());
}

// Connect IDE UI Event Listeners
document.addEventListener('DOMContentLoaded', () => {
  const btnSaveCode = document.getElementById('btn-save-ide-code');
  const btnRunSandbox = document.getElementById('btn-run-sandbox');
  const btnReloadIframe = document.getElementById('btn-reload-sandbox-iframe');

  if (btnSaveCode) btnSaveCode.addEventListener('click', saveIdeCode);
  if (btnRunSandbox) btnRunSandbox.addEventListener('click', () => {
    if (state.currentProject) {
      saveIdeCode();
      runSandboxRunner(state.currentProject.id);
    }
  });
  if (btnReloadIframe) btnReloadIframe.addEventListener('click', reloadSandboxIframe);
});

// --- Settings Helper ---
async function loadSettings() {
  try {
    const resp = await fetch(`${API_BASE}/api/settings/status`);
    const data = await resp.json();
    if (data.ollama_url) {
      document.getElementById('key-ollama').value = data.ollama_url;
    }
  } catch (e) {}
}

// --- Markdown Formatter Utility ---
function formatMarkdown(text) {
  if (!text) return '';
  let html = escapeHtml(text);

  // Fenced Code blocks
  html = html.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<pre><code class="language-${lang}">${code}</code></pre>`;
  });

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Headings
  html = html.replace(/^### (.*$)/gim, '<h4 style="margin: 0.5rem 0; font-size: 1rem;">$1</h4>');
  html = html.replace(/^## (.*$)/gim, '<h3 style="margin: 0.75rem 0; font-size: 1.15rem;">$1</h3>');
  html = html.replace(/^# (.*$)/gim, '<h2 style="margin: 1rem 0; font-size: 1.3rem;">$1</h2>');

  // Bold & Italics
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

  // Blockquotes
  html = html.replace(/^\> (.*$)/gim, '<blockquote style="border-left: 3px solid var(--primary); padding-left: 0.75rem; margin: 0.5rem 0; color: var(--text-secondary);">$1</blockquote>');

  // Line breaks
  html = html.replace(/\n/g, '<br>');

  return html;
}

function escapeHtml(str) {
  if (typeof str !== 'string') return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

