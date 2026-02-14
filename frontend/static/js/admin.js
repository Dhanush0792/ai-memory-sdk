const API_BASE_URL = window.location.origin;

// Auth Check
document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('auth_token');
    if (!token) {
        window.location.href = 'login.html';
        return;
    }

    // Decode token payload to check role (simple client-side check)
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload.role !== 'admin') {
            alert('Access Denied: Admin privileges required.');
            window.location.href = 'chat.html';
            return;
        }
        document.getElementById('adminEmail').textContent = payload.sub; // Or active user email if available
    } catch (e) {
        localStorage.removeItem('auth_token');
        window.location.href = 'login.html';
    }

    // Initial Load
    loadStats();
    loadUsers();
});

// Logout
document.getElementById('logoutBtn').addEventListener('click', () => {
    localStorage.removeItem('auth_token');
    window.location.href = 'login.html';
});

// API Helper
async function fetchAdmin(endpoint, options = {}) {
    const token = localStorage.getItem('auth_token');
    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...options.headers
    };

    const response = await fetch(`${API_BASE_URL}/api/v1/admin${endpoint}`, {
        ...options,
        headers
    });

    if (response.status === 401 || response.status === 403) {
        alert('Session expired or unauthorized');
        window.location.href = 'login.html';
        throw new Error('Unauthorized');
    }

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'API Error');
    }

    return response.json();
}

// Load Stats
async function loadStats() {
    try {
        const stats = await fetchAdmin('/stats');
        document.getElementById('statTotalUsers').textContent = stats.total_users;
        document.getElementById('statActiveUsers').textContent = stats.active_users;
        document.getElementById('statTotalMemories').textContent = stats.total_memories;
        document.getElementById('statRecentLogins').textContent = stats.recent_logins_24h;
    } catch (e) {
        console.error('Failed to load stats', e);
    }
}

// Load Users
async function loadUsers() {
    const tbody = document.getElementById('usersTableBody');
    tbody.innerHTML = '<tr><td colspan="6" class="px-6 py-8 text-center text-slate-500">Loading...</td></tr>';

    try {
        const users = await fetchAdmin('/users');

        if (users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="px-6 py-8 text-center text-slate-500">No users found</td></tr>';
            return;
        }

        tbody.innerHTML = users.map(user => `
            <tr class="border-b border-white/5 hover:bg-white/5 transition-colors">
                <td class="px-6 py-4">
                    <div class="font-medium text-white">${escapeHtml(user.full_name || 'Unknown')}</div>
                    <div class="text-xs text-slate-500">${escapeHtml(user.email)}</div>
                </td>
                <td class="px-6 py-4">
                    <span class="${user.role === 'admin' ? 'role-admin' : 'role-user'}">
                        ${user.role.toUpperCase()}
                    </span>
                </td>
                <td class="px-6 py-4">
                    <span class="status-badge ${user.is_active ? 'status-active' : 'status-inactive'}">
                        ${user.is_active ? 'Active' : 'Disabled'}
                    </span>
                </td>
                <td class="px-6 py-4 text-slate-400">
                    ${user.last_login_at ? new Date(user.last_login_at).toLocaleString() : 'Never'}
                </td>
                <td class="px-6 py-4 text-slate-400">
                    ${new Date(user.created_at).toLocaleDateString()}
                </td>
                <td class="px-6 py-4 text-right">
                    ${user.role !== 'admin' && user.is_active ? `
                        <button onclick="disableUser('${user.id}')" class="text-red-400 hover:text-red-300 text-sm font-medium hover:underline">
                            Disable
                        </button>
                    ` : ''}
                </td>
            </tr>
        `).join('');
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="6" class="px-6 py-8 text-center text-red-400">Error: ${e.message}</td></tr>`;
    }
}

// Create User
document.getElementById('createUserForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    const originalText = btn.textContent;
    btn.textContent = 'Creating...';
    btn.disabled = true;

    try {
        const payload = {
            full_name: document.getElementById('newFullName').value,
            email: document.getElementById('newEmail').value,
            password: document.getElementById('newPassword').value,
            role: document.getElementById('newRole').value
        };

        await fetchAdmin('/create-user', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        closeCreateUserModal();
        e.target.reset();
        loadUsers();
        loadStats();
        alert('User created successfully');
    } catch (err) {
        alert(err.message);
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
});

// Disable User
async function disableUser(userId) {
    if (!confirm('Are you sure you want to disable this user? They will lose access immediately.')) return;

    try {
        await fetchAdmin(`/disable-user/${userId}`, { method: 'PATCH' });
        loadUsers();
        loadStats();
    } catch (err) {
        alert(err.message);
    }
}

// Modal Logic
window.openCreateUserModal = () => {
    document.getElementById('createUserModal').classList.remove('hidden');
}

window.closeCreateUserModal = () => {
    document.getElementById('createUserModal').classList.add('hidden');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
