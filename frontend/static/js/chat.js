/**
 * AI Memory Chat - Frontend JavaScript
 * Handles chat interface, memory display, and API communication
 */

// Configuration
const API_BASE_URL = CONFIG.API_URL;
const TENANT_ID = 'default-tenant';

// State
let userId = null;
let sessionId = null;
let isProcessing = false;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeUser();
    setupEventListeners();
    loadMemories();
});

/**
 * Initialize user identity
 */
function initializeUser() {
    // Get or generate user ID
    userId = localStorage.getItem('memory_user_id');

    if (!userId) {
        userId = `user-${generateUUID()}`;
        localStorage.setItem('memory_user_id', userId);
    }

    sessionId = `session-${generateUUID()}`;

    document.getElementById('userId').textContent = userId.substring(0, 16) + '...';
    updateStatus('ready', 'Ready');
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    const clearSessionButton = document.getElementById('clearSession');
    const refreshButton = document.getElementById('refreshMemories');
    const closeModalButton = document.getElementById('closeModal');
    const logoutButton = document.getElementById('logoutButton');

    // Check for auth token
    const token = localStorage.getItem('auth_token');
    if (!token && window.location.pathname.endsWith('chat.html')) {
        window.location.href = 'login.html';
        return;
    }

    if (logoutButton) {
        logoutButton.addEventListener('click', () => {
            localStorage.removeItem('auth_token');
            localStorage.removeItem('memory_user_id');
            window.location.href = 'login.html';
        });
    }

    // Send message
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Auto-resize textarea
    messageInput.addEventListener('input', () => {
        messageInput.style.height = 'auto';
        messageInput.style.height = messageInput.scrollHeight + 'px';
    });

    // Clear session
    clearSessionButton.addEventListener('click', clearSession);

    // Refresh memories
    refreshButton.addEventListener('click', loadMemories);

    // Close modal
    closeModalButton.addEventListener('click', closeModal);
}

/**
 * Send chat message
 */
async function sendMessage() {
    if (isProcessing) return;

    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();

    if (!message) return;

    isProcessing = true;
    updateStatus('processing', 'Thinking...');

    // Clear input
    messageInput.value = '';
    messageInput.style.height = 'auto';

    // Add user message to chat
    addMessage('user', message);

    try {
        // Call chat API
        const token = localStorage.getItem('auth_token');
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
                'X-Tenant-ID': TENANT_ID
            },
            body: JSON.stringify({
                message: message,
                tenant_id: TENANT_ID,
                session_id: sessionId
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        // Add assistant response
        addMessage('assistant', data.response, {
            memories_retrieved: data.memories_retrieved,
            memories_ingested: data.memories_ingested,
            latency_ms: data.latency_ms
        });

        // Reload memories if new ones were ingested
        if (data.memories_ingested > 0) {
            setTimeout(loadMemories, 500);
        }

        updateStatus('ready', 'Ready');

    } catch (error) {
        console.error('Chat error:', error);
        addMessage('system', `Error: ${error.message}`);
        updateStatus('error', 'Error');
    } finally {
        isProcessing = false;
    }
}

/**
 * Add message to chat
 */
function addMessage(role, content, metadata = null) {
    const messagesContainer = document.getElementById('messages');

    // Remove welcome message if exists
    const welcomeMessage = messagesContainer.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${role}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;

    messageDiv.appendChild(contentDiv);

    // Add metadata for assistant messages
    if (role === 'assistant' && metadata) {
        const metaDiv = document.createElement('div');
        metaDiv.className = 'message-meta';
        metaDiv.innerHTML = `
            <span>📥 ${metadata.memories_ingested} ingested</span>
            <span>📤 ${metadata.memories_retrieved} retrieved</span>
            <span>⏱️ ${metadata.latency_ms.toFixed(0)}ms</span>
        `;
        messageDiv.appendChild(metaDiv);
    }

    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

/**
 * Load memories from API
 */
async function loadMemories() {
    try {
        const token = localStorage.getItem('auth_token');
        const response = await fetch(`${API_BASE_URL}/user/memories?limit=100`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'X-Tenant-ID': TENANT_ID
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        displayMemories(data.memories, data.active_count);

    } catch (error) {
        console.error('Load memories error:', error);
    }
}

/**
 * Display memories in panel
 */
function displayMemories(memories, activeCount) {
    const memoryList = document.getElementById('memoryList');
    const memoryCount = document.getElementById('memoryCount');

    memoryCount.textContent = activeCount;

    if (memories.length === 0) {
        memoryList.innerHTML = `
            <div class="empty-state">
                <p>No memories yet</p>
                <p class="empty-hint">Start chatting to create memories</p>
            </div>
        `;
        return;
    }

    // Filter active memories only
    const activeMemories = memories.filter(m => m.is_active);

    memoryList.innerHTML = activeMemories.map(memory => `
        <div class="memory-item" data-id="${memory.id}">
            <div class="memory-header">
                <span class="memory-subject">${escapeHtml(memory.subject)}</span>
                <span class="memory-version">v${memory.version}</span>
            </div>
            <div class="memory-body">
                <span class="memory-predicate">${escapeHtml(memory.predicate)}</span>
                <span class="memory-object">${escapeHtml(memory.object)}</span>
            </div>
            <div class="memory-footer">
                <span class="memory-confidence">Confidence: ${(memory.confidence * 100).toFixed(0)}%</span>
                <span class="memory-scope">${memory.scope}</span>
                <div class="memory-actions">
                    <button class="btn-icon-small" onclick="viewHistory('${escapeHtml(memory.subject)}', '${escapeHtml(memory.predicate)}')" title="View history">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"></circle>
                            <polyline points="12 6 12 12 16 14"></polyline>
                        </svg>
                    </button>
                    <button class="btn-icon-small btn-delete" onclick="deleteMemory('${memory.id}')" title="Delete">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

/**
 * Delete memory
 */
async function deleteMemory(memoryId) {
    if (!confirm('Delete this memory? This action cannot be undone.')) {
        return;
    }

    try {
        const token = localStorage.getItem('auth_token');
        const response = await fetch(`${API_BASE_URL}/user/memories/${memoryId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`,
                'X-Tenant-ID': TENANT_ID
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        // Reload memories
        loadMemories();
        addMessage('system', 'Memory deleted');

    } catch (error) {
        console.error('Delete memory error:', error);
        alert(`Failed to delete memory: ${error.message}`);
    }
}

/**
 * View version history
 */
async function viewHistory(subject, predicate) {
    try {
        const token = localStorage.getItem('auth_token');
        const response = await fetch(
            `${API_BASE_URL}/api/v1/user/memories/${encodeURIComponent(subject)}/${encodeURIComponent(predicate)}/history`,
            {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'X-Tenant-ID': TENANT_ID
                }
            }
        );

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        displayVersionHistory(data);

    } catch (error) {
        console.error('View history error:', error);
        alert(`Failed to load history: ${error.message}`);
    }
}

/**
 * Display version history in modal
 */
function displayVersionHistory(data) {
    const modalBody = document.getElementById('modalBody');

    modalBody.innerHTML = `
        <div class="history-header">
            <p><strong>Subject:</strong> ${escapeHtml(data.subject)}</p>
            <p><strong>Predicate:</strong> ${escapeHtml(data.predicate)}</p>
            <p><strong>Total Versions:</strong> ${data.total_versions}</p>
        </div>
        <div class="history-list">
            ${data.versions.map(version => `
                <div class="history-item ${version.is_active ? 'active' : 'inactive'}">
                    <div class="history-version">Version ${version.version}</div>
                    <div class="history-object">${escapeHtml(version.object)}</div>
                    <div class="history-meta">
                        <span>Confidence: ${(version.confidence * 100).toFixed(0)}%</span>
                        <span>${version.is_active ? '✓ Active' : '✗ Inactive'}</span>
                        <span>${new Date(version.created_at).toLocaleString()}</span>
                    </div>
                </div>
            `).join('')}
        </div>
    `;

    document.getElementById('memoryModal').style.display = 'flex';
}

/**
 * Close modal
 */
function closeModal() {
    document.getElementById('memoryModal').style.display = 'none';
}

/**
 * Clear session
 */
function clearSession() {
    if (!confirm('Start a new session? This will create a new user ID.')) {
        return;
    }

    localStorage.removeItem('memory_user_id');
    location.reload();
}

/**
 * Update status indicator
 */
function updateStatus(status, text) {
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');

    statusDot.className = `status-dot status-${status}`;
    statusText.textContent = text;
}

/**
 * Generate UUID
 */
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

/**
 * Escape HTML
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make functions available globally
window.deleteMemory = deleteMemory;
window.viewHistory = viewHistory;
