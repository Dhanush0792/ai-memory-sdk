// AI Memory SDK - Clean, minimal frontend

let config = {
    apiKey: '',
    userId: '',
    apiUrl: 'http://localhost:8001'
};

// Load config from localStorage
function loadConfig() {
    const saved = localStorage.getItem('memorySDKConfig');
    if (saved) {
        config = JSON.parse(saved);
        document.getElementById('apiKey').value = config.apiKey;
        document.getElementById('userId').value = config.userId;
        document.getElementById('apiUrl').value = config.apiUrl;

        if (config.apiKey && config.userId) {
            document.getElementById('mainContent').style.display = 'block';
            loadStats();
            loadMemories();
        }
    }
}

// Toggle configuration panel
function toggleConfig() {
    const form = document.getElementById('configForm');
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
}

// Save configuration
function saveConfig() {
    config.apiKey = document.getElementById('apiKey').value.trim();
    config.userId = document.getElementById('userId').value.trim();
    config.apiUrl = document.getElementById('apiUrl').value.trim();

    if (!config.apiKey || !config.userId) {
        alert('Please enter both API Key and User ID');
        return;
    }

    localStorage.setItem('memorySDKConfig', JSON.stringify(config));
    document.getElementById('mainContent').style.display = 'block';
    document.getElementById('configForm').style.display = 'none';

    loadStats();
    loadMemories();
}

// API Helper
async function apiCall(endpoint, options = {}) {
    const url = `${config.apiUrl}${endpoint}`;
    const headers = {
        'Authorization': `Bearer ${config.apiKey}`,
        'X-User-ID': config.userId,
        'Content-Type': 'application/json',
        ...options.headers
    };

    const response = await fetch(url, {
        ...options,
        headers
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return await response.json();
}

// Load statistics
async function loadStats() {
    try {
        const stats = await apiCall('/api/v1/memory/stats');
        const text = `Total memories: ${stats.total || 0}
Facts: ${stats.by_type?.fact || 0}
Preferences: ${stats.by_type?.preference || 0}
Events: ${stats.by_type?.event || 0}`;
        document.getElementById('statsText').textContent = text;
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// Load memories
async function loadMemories() {
    try {
        const memories = await apiCall('/api/v1/memory?limit=100');
        displayMemories(memories);
    } catch (error) {
        console.error('Failed to load memories:', error);
    }
}

// Display memories in table
function displayMemories(memories) {
    const tbody = document.getElementById('memoryTableBody');

    if (!memories || memories.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="empty-message">No memories yet</td></tr>';
        return;
    }

    tbody.innerHTML = memories.map(m => `
        <tr>
            <td>${escapeHtml(m.type)}</td>
            <td>${escapeHtml(m.content)}</td>
            <td>${new Date(m.created_at).toLocaleString()}</td>
            <td><button onclick="deleteMemory('${m.id}')">Delete</button></td>
        </tr>
    `).join('');
}

// Add memory
async function addMemory() {
    const content = document.getElementById('memoryContent').value.trim();
    const type = document.getElementById('memoryType').value;
    const errorEl = document.getElementById('addMemoryError');

    errorEl.classList.remove('visible');

    if (!content) {
        errorEl.textContent = 'Please enter memory content';
        errorEl.classList.add('visible');
        return;
    }

    try {
        await apiCall('/api/v1/memory', {
            method: 'POST',
            body: JSON.stringify({
                content,
                type,
                metadata: {}
            })
        });

        document.getElementById('memoryContent').value = '';
        loadStats();
        loadMemories();
    } catch (error) {
        errorEl.textContent = 'Failed to add memory: ' + error.message;
        errorEl.classList.add('visible');
    }
}

// Delete memory
async function deleteMemory(memoryId) {
    if (!confirm('Delete this memory?')) {
        return;
    }

    try {
        await apiCall(`/api/v1/memory/${memoryId}`, {
            method: 'DELETE'
        });

        loadStats();
        loadMemories();
    } catch (error) {
        alert('Failed to delete memory: ' + error.message);
    }
}

// Send chat message
async function sendChat() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    const autoSave = document.getElementById('autoSave').checked;
    const errorEl = document.getElementById('chatError');

    errorEl.classList.remove('visible');

    if (!message) return;

    addChatMessage(message, 'user');
    input.value = '';

    try {
        const response = await apiCall('/api/v1/chat', {
            method: 'POST',
            body: JSON.stringify({
                message,
                auto_save: autoSave
            })
        });

        addChatMessage(response.response, 'assistant');

        if (response.memories_extracted > 0) {
            loadStats();
            loadMemories();
        }
    } catch (error) {
        errorEl.textContent = 'Chat failed: ' + error.message;
        errorEl.classList.add('visible');
    }
}

// Add chat message to UI
function addChatMessage(text, sender) {
    const container = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}`;
    messageDiv.textContent = text;
    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
}

// Handle chat enter key
function handleChatKeyPress(event) {
    if (event.key === 'Enter') {
        sendChat();
    }
}

// Export data
async function exportData() {
    try {
        const data = await apiCall('/api/v1/gdpr/export');

        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `memory-export-${config.userId}-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    } catch (error) {
        alert('Failed to export data: ' + error.message);
    }
}

// Delete all data
async function deleteAllData() {
    const confirmation = prompt('This will permanently delete ALL your data. Type "DELETE" to confirm:');

    if (confirmation !== 'DELETE') {
        return;
    }

    try {
        await apiCall('/api/v1/gdpr/delete', {
            method: 'DELETE'
        });

        loadStats();
        loadMemories();
    } catch (error) {
        alert('Failed to delete data: ' + error.message);
    }
}

// Utility: Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize
document.addEventListener('DOMContentLoaded', loadConfig);
