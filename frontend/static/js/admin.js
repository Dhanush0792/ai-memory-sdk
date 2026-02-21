/* ============================================================
   AI Memory SDK — Admin Dashboard JS
   Handles: auth, stats, user CRUD, audit logs, system health,
            credential provisioning, search/filter, toasts
   ============================================================ */

const API = window.location.origin;
let allUsers = [];
let currentFilter = 'all';
let searchTimeout = null;
let currentAuditFilter = '';

// ── Auth Guard ──
document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('token');
    const role = localStorage.getItem('role');

    if (!token || role !== 'admin') {
        window.location.href = 'login.html';
        return;
    }

    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload.role !== 'admin') {
            window.location.href = 'login.html';
            return;
        }
        document.getElementById('adminEmail').textContent = payload.sub || 'Admin';
    } catch (e) {
        localStorage.clear();
        window.location.href = 'login.html';
        return;
    }

    // Initial Load
    loadStats();
    loadUsers();
    loadHealth();
    loadAuditLogs();
});

// ── Logout ──
document.getElementById('logoutBtn').addEventListener('click', () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    window.location.href = 'login.html';
});

// ── API Helper ──
async function adminFetch(endpoint, opts = {}) {
    const token = localStorage.getItem('token');
    const res = await fetch(`${API}/api/v1/admin${endpoint}`, {
        ...opts,
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            ...opts.headers
        }
    });

    if (res.status === 401 || res.status === 403) {
        toast('Session expired', 'error');
        setTimeout(() => { localStorage.clear(); window.location.href = 'login.html'; }, 800);
        throw new Error('Unauthorized');
    }

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'API Error' }));
        throw new Error(err.detail || `Error ${res.status}`);
    }

    if (res.status === 204) return null;
    return res.json();
}

// ── Stats ──
async function loadStats() {
    try {
        const stats = await adminFetch('/stats');
        animateNumber('statTotalUsers', stats.total_users);
        animateNumber('statActiveUsers', stats.active_users);
        animateNumber('statTotalMemories', stats.total_memories);
        animateNumber('statRecentLogins', stats.recent_logins_24h);

        // Disabled = total - active
        const disabled = Math.max(0, stats.total_users - stats.active_users);
        animateNumber('statDisabledUsers', disabled);

        // Memory breakdown
        renderMemoryBreakdown(stats.memory_count_per_user, stats.total_memories);
    } catch (e) {
        console.error('Stats load failed:', e);
    }
}

function animateNumber(id, target) {
    const el = document.getElementById(id);
    if (!el) return;
    const start = 0;
    const duration = 600;
    const startTime = performance.now();

    function step(now) {
        const progress = Math.min((now - startTime) / duration, 1);
        const ease = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(start + (target - start) * ease).toLocaleString();
        if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
}

// ── Memory Breakdown ──
function renderMemoryBreakdown(perUser, total) {
    const el = document.getElementById('memoryBreakdown');
    if (!perUser || perUser.length === 0) {
        el.innerHTML = '<div style="color:#52525B;text-align:center;padding:2rem 0">No memory data yet</div>';
        return;
    }

    const max = Math.max(...perUser.map(u => u.count));
    el.innerHTML = perUser.map(u => {
        const pct = max > 0 ? (u.count / max * 100) : 0;
        const label = u.user_id.length > 18 ? u.user_id.slice(0, 16) + '…' : u.user_id;
        return `
            <div class="mem-bar-row">
                <span class="mem-bar-label" title="${escapeHtml(u.user_id)}">${escapeHtml(label)}</span>
                <div class="mem-bar-track">
                    <div class="mem-bar-fill" style="width:${pct}%"></div>
                </div>
                <span class="mem-bar-count">${u.count}</span>
            </div>
        `;
    }).join('');
}

// ── Users ──
async function loadUsers() {
    const tbody = document.getElementById('usersTableBody');
    tbody.innerHTML = '<tr><td colspan="6" class="admin-table-empty">Loading users...</td></tr>';

    try {
        allUsers = await adminFetch('/users?limit=200');
        renderUsers();
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="6" class="admin-table-empty" style="color:#EF4444">${escapeHtml(e.message)}</td></tr>`;
    }
}

function renderUsers() {
    const tbody = document.getElementById('usersTableBody');
    const search = document.getElementById('userSearch').value.toLowerCase().trim();

    let filtered = allUsers;
    if (currentFilter === 'active') filtered = filtered.filter(u => u.is_active);
    if (currentFilter === 'disabled') filtered = filtered.filter(u => !u.is_active);
    if (search) {
        filtered = filtered.filter(u =>
            (u.full_name || '').toLowerCase().includes(search) ||
            u.email.toLowerCase().includes(search)
        );
    }

    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="admin-table-empty">No users found</td></tr>';
        return;
    }

    tbody.innerHTML = filtered.map(user => `
        <tr>
            <td>
                <div class="td-name">${escapeHtml(user.full_name || 'Unknown')}</div>
                <div class="td-email">${escapeHtml(user.email)}</div>
            </td>
            <td>
                <span class="badge ${user.role === 'admin' ? 'badge-admin' : 'badge-user'}">
                    ${user.role.toUpperCase()}
                </span>
            </td>
            <td>
                <span class="badge ${user.is_active ? 'badge-active' : 'badge-disabled'}">
                    <span class="badge-dot"></span>
                    ${user.is_active ? 'Active' : 'Disabled'}
                </span>
            </td>
            <td style="color:#71717A;font-size:0.8rem">
                ${user.last_login_at ? formatDate(user.last_login_at) : '<span style="color:#3F3F46">Never</span>'}
            </td>
            <td style="color:#71717A;font-size:0.8rem">
                ${formatDate(user.created_at)}
            </td>
            <td style="text-align:right">
                ${user.role !== 'admin' ? `
                    ${user.is_active
                ? `<button class="admin-icon-btn disable" title="Disable user" onclick="disableUser('${user.id}')">
                             <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>
                           </button>`
                : `<button class="admin-icon-btn enable" title="Enable user" onclick="enableUser('${user.id}')">
                             <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                           </button>`
            }
                ` : ''}
            </td>
        </tr>
    `).join('');
}

// ── Filter buttons ──
document.querySelectorAll('[data-filter]').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('[data-filter]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentFilter = btn.dataset.filter;
        renderUsers();
    });
});

// ── Search ──
document.getElementById('userSearch').addEventListener('input', () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(renderUsers, 200);
});

// ── Disable / Enable User ──
async function disableUser(userId) {
    if (!confirm('Disable this user? They will lose access immediately.')) return;
    try {
        await adminFetch(`/disable-user/${userId}`, { method: 'PATCH' });
        toast('User disabled', 'success');
        loadUsers();
        loadStats();
        loadAuditLogs();
    } catch (e) { toast(e.message, 'error'); }
}

async function enableUser(userId) {
    try {
        await adminFetch(`/enable-user/${userId}`, { method: 'PATCH' });
        toast('User enabled', 'success');
        loadUsers();
        loadStats();
        loadAuditLogs();
    } catch (e) { toast(e.message, 'error'); }
}

// ── Create User ──
function openCreateModal() {
    document.getElementById('createModal').classList.add('open');
    document.getElementById('createModalTitle').textContent = 'Create New User';
    document.getElementById('createUserForm').reset();
    document.getElementById('createUserForm').style.display = 'block';
}

function closeCreateModal() {
    document.getElementById('createModal').classList.remove('open');
}

async function handleCreateUser(e) {
    e.preventDefault();
    const btn = document.getElementById('createSubmitBtn');
    const email = document.getElementById('newEmail').value;
    const password = document.getElementById('newPassword').value;

    btn.textContent = 'Creating...';
    btn.disabled = true;

    try {
        await adminFetch('/create-user', {
            method: 'POST',
            body: JSON.stringify({
                full_name: document.getElementById('newName').value,
                email,
                password,
                role: document.getElementById('newRole').value,
            })
        });

        closeCreateModal();
        showCredentialModal(email, password);
        loadUsers();
        loadStats();
        loadAuditLogs();
    } catch (err) {
        toast(err.message, 'error');
    } finally {
        btn.textContent = 'Create User';
        btn.disabled = false;
    }
}

// ── Password Generator ──
function generatePassword() {
    const chars = 'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#$%&*';
    let pass = '';
    for (let i = 0; i < 14; i++) pass += chars[Math.floor(Math.random() * chars.length)];
    document.getElementById('newPassword').value = pass;
}

// ── Credential Modal ──
function showCredentialModal(email, password) {
    document.getElementById('credEmail').textContent = email;
    document.getElementById('credPassword').textContent = password;
    document.getElementById('credLoginUrl').textContent = `${window.location.origin}/login.html`;
    document.getElementById('credModal').classList.add('open');
}

function closeCredModal() {
    document.getElementById('credModal').classList.remove('open');
}

function copyField(elementId, btn) {
    const text = document.getElementById(elementId).textContent;
    navigator.clipboard.writeText(text).then(() => {
        const orig = btn.textContent;
        btn.textContent = 'Copied!';
        btn.classList.add('copied');
        setTimeout(() => { btn.textContent = orig; btn.classList.remove('copied'); }, 1500);
    });
}

function copyAllCredentials() {
    const email = document.getElementById('credEmail').textContent;
    const password = document.getElementById('credPassword').textContent;
    const url = document.getElementById('credLoginUrl').textContent;
    const text = `Login Credentials\n─────────────────\nEmail: ${email}\nPassword: ${password}\nLogin URL: ${url}`;
    navigator.clipboard.writeText(text).then(() => {
        toast('All credentials copied to clipboard', 'success');
    });
}

// ── Audit Logs ──
async function loadAuditLogs() {
    const tbody = document.getElementById('auditTableBody');
    tbody.innerHTML = '<tr><td colspan="5" class="admin-table-empty">Loading...</td></tr>';

    try {
        const filter = currentAuditFilter ? `?action_type=${currentAuditFilter}&limit=30` : '?limit=30';
        const data = await adminFetch(`/audit-logs${filter}`);

        if (!data.logs || data.logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="admin-table-empty">No audit logs yet</td></tr>';
            return;
        }

        tbody.innerHTML = data.logs.map(log => `
            <tr>
                <td>
                    <span class="audit-action ${escapeHtml(log.action_type)}">${escapeHtml(log.action_type)}</span>
                </td>
                <td style="font-size:0.8rem;color:#A1A1AA">${escapeHtml(log.admin_email)}</td>
                <td style="font-size:0.8rem">${escapeHtml(log.target_email)}</td>
                <td style="font-size:0.78rem;color:#52525B;font-family:'JetBrains Mono',monospace">
                    ${log.metadata ? escapeHtml(JSON.stringify(log.metadata)) : '—'}
                </td>
                <td style="font-size:0.78rem;color:#71717A">${log.timestamp ? formatDate(log.timestamp) : '—'}</td>
            </tr>
        `).join('');
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="5" class="admin-table-empty" style="color:#EF4444">${escapeHtml(e.message)}</td></tr>`;
    }
}

function filterAudit(type) {
    currentAuditFilter = type;
    // Update active classes
    document.querySelectorAll('.admin-panel:last-child .admin-btn-secondary').forEach(b => b.classList.remove('active'));
    const id = type === '' ? 'auditAll' : type === 'CREATE_USER' ? 'auditCreate' : type === 'DISABLE_USER' ? 'auditDisable' : 'auditEnable';
    document.getElementById(id).classList.add('active');
    loadAuditLogs();
}

// ── System Health ──
async function loadHealth() {
    const el = document.getElementById('healthBody');
    const statusEl = document.getElementById('statSystemStatus');

    try {
        const h = await adminFetch('/system-health');

        // System status stat card
        const statusClass = h.status === 'operational' ? 'health-ok' : h.status === 'degraded' ? 'health-warn' : 'health-error';
        statusEl.innerHTML = `<span class="${statusClass}" style="font-size:1rem">● ${h.status.charAt(0).toUpperCase() + h.status.slice(1)}</span>`;

        // Health panel
        el.innerHTML = `
            <div class="health-row">
                <span class="health-label">Database</span>
                <span class="health-value ${h.database === 'connected' ? 'health-ok' : 'health-error'}">
                    ${h.database === 'connected' ? '● Connected' : '● Disconnected'}
                </span>
            </div>
            <div class="health-row">
                <span class="health-label">Users Table</span>
                <span class="health-value health-ok">${(h.tables?.users ?? '?').toLocaleString()} rows</span>
            </div>
            <div class="health-row">
                <span class="health-label">Memories Table</span>
                <span class="health-value health-ok">${(h.tables?.memories ?? '?').toLocaleString()} rows</span>
            </div>
            <div class="health-row">
                <span class="health-label">Audit Logs</span>
                <span class="health-value health-ok">${(h.tables?.admin_audit_logs ?? '?').toLocaleString()} entries</span>
            </div>
            <div class="health-row">
                <span class="health-label">Disabled Users</span>
                <span class="health-value ${(h.disabled_users || 0) > 0 ? 'health-warn' : 'health-ok'}">${h.disabled_users || 0}</span>
            </div>
            <div class="health-row">
                <span class="health-label">Memories Today</span>
                <span class="health-value health-ok">${h.memories_today || 0}</span>
            </div>
        `;
    } catch (e) {
        statusEl.innerHTML = '<span class="health-error" style="font-size:1rem">● Error</span>';
        el.innerHTML = `<div style="color:#EF4444;text-align:center;padding:1rem">${escapeHtml(e.message)}</div>`;
    }
}

// ── Utilities ──
function formatDate(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    const now = new Date();
    const diff = now - d;

    // If less than 24h, show relative
    if (diff < 86400000) {
        const hrs = Math.floor(diff / 3600000);
        if (hrs < 1) {
            const mins = Math.floor(diff / 60000);
            return mins < 1 ? 'Just now' : `${mins}m ago`;
        }
        return `${hrs}h ago`;
    }
    // If less than 7 days, show relative
    if (diff < 604800000) {
        return `${Math.floor(diff / 86400000)}d ago`;
    }
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

function toast(msg, type = 'info') {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.className = `admin-toast ${type} show`;
    clearTimeout(el._t);
    el._t = setTimeout(() => { el.classList.remove('show'); }, 3000);
}

// Close modals with Escape
document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
        closeCreateModal();
        closeCredModal();
    }
});

// Close modals on overlay click
document.getElementById('createModal').addEventListener('click', e => {
    if (e.target === e.currentTarget) closeCreateModal();
});
document.getElementById('credModal').addEventListener('click', e => {
    if (e.target === e.currentTarget) closeCredModal();
});
