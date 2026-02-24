/**
 * AI Memory SDK — User Dashboard
 * Full dashboard logic: auth, stats, memories, timeline, heatmap, graph, export
 */

// ── Config ──
const API = CONFIG.API_URL;
const TENANT = 'default-tenant';
const PAGE_SIZE = 15;

// ── State ──
let allMemories = [];
let filteredMemories = [];
let currentPage = 0;
let sortField = 'created_at';
let sortDir = -1; // -1 = descending
let searchQuery = '';
let activeFilter = 'all';
let graphZoom = 1;
let graphOffset = { x: 0, y: 0 };
let graphDragging = false;
let graphDragStart = { x: 0, y: 0 };
let graphNodes = [];
let graphEdges = [];

// ── Auth Check ──
(function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = 'login.html';
        return;
    }
    // Decode JWT payload for display
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const email = payload.sub || 'User';
        document.getElementById('userEmail').textContent = email;
        const name = email.split('@')[0];
        document.getElementById('welcomeTitle').textContent = `Welcome back, ${name}`;
    } catch (e) {
        document.getElementById('userEmail').textContent = 'User';
    }
})();

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
    setupListeners();
});

// ── API Helper ──
async function apiFetch(path, options = {}) {
    const token = localStorage.getItem('token');
    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        'X-Tenant-ID': TENANT,
        ...options.headers
    };
    const res = await fetch(`${API}${path}`, { ...options, headers });
    if (res.status === 401 || res.status === 403) {
        localStorage.removeItem('token');
        window.location.href = 'login.html';
        throw new Error('Unauthorized');
    }
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

// ── Load Dashboard ──
async function loadDashboard() {
    try {
        const data = await apiFetch('/user/memories?limit=500');
        allMemories = data.memories || [];
        filteredMemories = [...allMemories];

        renderStats(data);
        renderTimeline();
        renderHeatmap();
        renderKnowledgeGraph();
        applyFilters();
    } catch (err) {
        console.error('Dashboard load failed:', err);
        toast('Failed to load dashboard data', 'error');
    }
}

// ── Stats ──
function renderStats(data) {
    const active = allMemories.filter(m => m.is_active);
    const totalCount = data.total_count || allMemories.length;
    const activeCount = data.active_count || active.length;

    document.getElementById('statTotal').textContent = totalCount;
    document.getElementById('statTotalSub').textContent =
        `${totalCount - activeCount} deleted`;

    document.getElementById('statActive').textContent = activeCount;
    document.getElementById('statActiveSub').textContent =
        activeCount > 0 ? `${((activeCount / Math.max(totalCount, 1)) * 100).toFixed(0)}% retention` : 'No memories yet';

    // Avg confidence
    if (active.length > 0) {
        const avg = active.reduce((s, m) => s + m.confidence, 0) / active.length;
        document.getElementById('statConfidence').textContent = `${(avg * 100).toFixed(0)}%`;
        document.getElementById('statConfSub').textContent =
            avg >= 0.8 ? 'Excellent quality' : avg >= 0.6 ? 'Good quality' : 'Needs review';
    } else {
        document.getElementById('statConfidence').textContent = '—';
        document.getElementById('statConfSub').textContent = 'No data yet';
    }

    // Health score
    const health = computeHealthScore(active);
    renderHealthRing(health);
}

function computeHealthScore(memories) {
    if (memories.length === 0) return 0;

    // Factor 1: Average confidence (0-40 points)
    const avgConf = memories.reduce((s, m) => s + m.confidence, 0) / memories.length;
    const confScore = avgConf * 40;

    // Factor 2: Freshness — ratio of memories updated < 7 days ago (0-30 points)
    const now = Date.now();
    const recentCount = memories.filter(m => {
        const d = new Date(m.updated_at || m.created_at).getTime();
        return (now - d) < 7 * 86400000;
    }).length;
    const freshnessScore = (recentCount / memories.length) * 30;

    // Factor 3: Coverage — unique subjects (0-30 points, capped at 10+)
    const subjects = new Set(memories.map(m => m.subject));
    const coverageScore = Math.min(subjects.size / 10, 1) * 30;

    return Math.round(confScore + freshnessScore + coverageScore);
}

function renderHealthRing(score) {
    const circumference = 2 * Math.PI * 20; // r=20
    const offset = circumference - (score / 100) * circumference;

    const ring = document.getElementById('healthRingFill');
    const num = document.getElementById('healthNum');

    // Color based on score
    let color = '#EF4444';
    if (score >= 70) color = '#22C55E';
    else if (score >= 40) color = '#F59E0B';

    ring.style.stroke = color;
    ring.style.strokeDashoffset = offset;
    num.textContent = score;
    num.style.color = color;
}

// ── Memory Timeline (SVG) ──
function renderTimeline() {
    const svg = document.getElementById('timelineSvg');
    const container = document.getElementById('timelineContainer');
    if (!svg || allMemories.length === 0) {
        svg.innerHTML = '<text x="50%" y="50%" text-anchor="middle" fill="#52525B" font-size="13" font-family="Inter">No timeline data yet</text>';
        return;
    }

    const width = container.clientWidth;
    const height = 170;
    const padding = { top: 15, right: 20, bottom: 30, left: 40 };
    const plotW = width - padding.left - padding.right;
    const plotH = height - padding.top - padding.bottom;

    // Group by day (last 30 days)
    const now = new Date();
    const days = [];
    for (let i = 29; i >= 0; i--) {
        const d = new Date(now);
        d.setDate(d.getDate() - i);
        days.push(d.toISOString().slice(0, 10));
    }

    const countMap = {};
    days.forEach(d => countMap[d] = 0);
    allMemories.forEach(m => {
        const day = (m.created_at || '').slice(0, 10);
        if (countMap[day] !== undefined) countMap[day]++;
    });

    const values = days.map(d => countMap[d]);
    const maxVal = Math.max(...values, 1);

    // Build points
    const points = values.map((v, i) => ({
        x: padding.left + (i / (days.length - 1)) * plotW,
        y: padding.top + plotH - (v / maxVal) * plotH,
        val: v,
        date: days[i]
    }));

    // SVG content
    const defs = `<defs>
        <linearGradient id="timelineGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#4F8EF7" stop-opacity="0.3"/>
            <stop offset="100%" stop-color="#4F8EF7" stop-opacity="0"/>
        </linearGradient>
    </defs>`;

    // Grid lines
    let gridLines = '';
    for (let i = 0; i <= 4; i++) {
        const y = padding.top + (i / 4) * plotH;
        gridLines += `<line x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}" class="timeline-grid-line"/>`;
    }

    // Area path
    const linePoints = points.map(p => `${p.x},${p.y}`).join(' ');
    const areaPath = `M${points[0].x},${padding.top + plotH} L${linePoints} L${points[points.length - 1].x},${padding.top + plotH} Z`;
    const linePath = `M${linePoints}`;

    // X-axis labels (show every 5th)
    let labels = '';
    points.forEach((p, i) => {
        if (i % 5 === 0 || i === points.length - 1) {
            const label = days[i].slice(5); // MM-DD
            labels += `<text x="${p.x}" y="${height - 5}" text-anchor="middle" class="timeline-label">${label}</text>`;
        }
    });

    // Y-axis labels
    for (let i = 0; i <= 4; i++) {
        const v = Math.round((1 - i / 4) * maxVal);
        const y = padding.top + (i / 4) * plotH;
        labels += `<text x="${padding.left - 8}" y="${y + 4}" text-anchor="end" class="timeline-label">${v}</text>`;
    }

    // Dots
    let dots = '';
    points.forEach((p, i) => {
        if (p.val > 0) {
            dots += `<circle cx="${p.x}" cy="${p.y}" r="3" class="timeline-dot" data-idx="${i}"/>`;
        }
    });

    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
    svg.innerHTML = `${defs}${gridLines}
        <polygon class="timeline-area" points="${points.map(p => `${p.x},${p.y}`).join(' ')} ${points[points.length - 1].x},${padding.top + plotH} ${points[0].x},${padding.top + plotH}"/>
        <polyline class="timeline-line" points="${linePoints}"/>
        ${dots}${labels}`;

    // Tooltip handling
    const tooltip = document.getElementById('timelineTooltip');
    svg.querySelectorAll('.timeline-dot').forEach(dot => {
        dot.addEventListener('mouseenter', (e) => {
            const idx = parseInt(dot.dataset.idx);
            const p = points[idx];
            tooltip.textContent = `${p.date}: ${p.val} ${p.val === 1 ? 'memory' : 'memories'}`;
            tooltip.style.left = `${p.x}px`;
            tooltip.style.top = `${p.y - 35}px`;
            tooltip.classList.add('visible');
        });
        dot.addEventListener('mouseleave', () => {
            tooltip.classList.remove('visible');
        });
    });
}

// ── Confidence Heatmap ──
function renderHeatmap() {
    const grid = document.getElementById('heatmapGrid');
    const active = allMemories.filter(m => m.is_active);

    if (active.length === 0) {
        grid.innerHTML = '<div style="color:#52525B;font-size:0.85rem;grid-column:1/-1;text-align:center;padding:2rem 0">No memories to visualize</div>';
        return;
    }

    grid.innerHTML = active.map(m => {
        const conf = m.confidence;
        let bg;
        if (conf >= 0.85) bg = 'rgba(34,197,94,0.55)';
        else if (conf >= 0.7) bg = 'rgba(79,142,247,0.55)';
        else if (conf >= 0.5) bg = 'rgba(245,158,11,0.55)';
        else bg = 'rgba(239,68,68,0.55)';

        return `<div class="heatmap-cell" style="background:${bg}" title="${esc(m.subject)} → ${esc(m.predicate)}: ${(conf * 100).toFixed(0)}%"></div>`;
    }).join('');
}

// ── Knowledge Graph (Canvas) ──
function renderKnowledgeGraph() {
    const canvas = document.getElementById('graphCanvas');
    const container = document.getElementById('graphContainer');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = container.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const active = allMemories.filter(m => m.is_active);
    if (active.length === 0) {
        ctx.fillStyle = '#52525B';
        ctx.font = '13px Inter';
        ctx.textAlign = 'center';
        ctx.fillText('No data to graph', rect.width / 2, rect.height / 2);
        return;
    }

    // Build graph data
    const subjectMap = {};
    const predicateSet = new Set();

    active.forEach(m => {
        if (!subjectMap[m.subject]) {
            subjectMap[m.subject] = [];
        }
        subjectMap[m.subject].push(m);
        predicateSet.add(m.predicate);
    });

    const subjects = Object.keys(subjectMap);
    graphNodes = [];
    graphEdges = [];

    // Position subjects in a circle
    const cx = rect.width / 2;
    const cy = rect.height / 2;
    const radius = Math.min(cx, cy) * 0.65;

    subjects.forEach((subj, i) => {
        const angle = (i / subjects.length) * Math.PI * 2 - Math.PI / 2;
        graphNodes.push({
            id: subj,
            x: cx + Math.cos(angle) * radius,
            y: cy + Math.sin(angle) * radius,
            type: 'subject',
            label: subj.length > 14 ? subj.slice(0, 14) + '…' : subj,
            memories: subjectMap[subj]
        });
    });

    // Add object nodes and edges
    let objectIdx = 0;
    active.forEach(m => {
        const fromNode = graphNodes.find(n => n.id === m.subject);
        if (!fromNode) return;

        const objKey = `${m.subject}::${m.predicate}::${m.object}`;
        let toNode = graphNodes.find(n => n.id === objKey);
        if (!toNode) {
            const angle = Math.atan2(fromNode.y - cy, fromNode.x - cx);
            const dist = radius * 0.35 + (objectIdx % 3) * 25;
            toNode = {
                id: objKey,
                x: fromNode.x + Math.cos(angle + (objectIdx % 5 - 2) * 0.4) * dist,
                y: fromNode.y + Math.sin(angle + (objectIdx % 5 - 2) * 0.4) * dist,
                type: 'object',
                label: m.object.length > 16 ? m.object.slice(0, 16) + '…' : m.object
            };
            graphNodes.push(toNode);
            objectIdx++;
        }

        graphEdges.push({
            from: fromNode,
            to: toNode,
            label: m.predicate,
            confidence: m.confidence
        });
    });

    document.getElementById('graphNodeCount').textContent =
        `${subjects.length} subjects · ${graphEdges.length} relationships`;

    drawGraph(ctx, rect.width, rect.height);
}

function drawGraph(ctx, w, h) {
    ctx.clearRect(0, 0, w, h);
    ctx.save();

    // Apply zoom and pan
    ctx.translate(w / 2 + graphOffset.x, h / 2 + graphOffset.y);
    ctx.scale(graphZoom, graphZoom);
    ctx.translate(-w / 2, -h / 2);

    // Draw edges
    graphEdges.forEach(edge => {
        ctx.beginPath();
        ctx.moveTo(edge.from.x, edge.from.y);
        ctx.lineTo(edge.to.x, edge.to.y);
        ctx.strokeStyle = `rgba(79, 142, 247, ${0.15 + edge.confidence * 0.25})`;
        ctx.lineWidth = 1;
        ctx.stroke();

        // Edge label
        const mx = (edge.from.x + edge.to.x) / 2;
        const my = (edge.from.y + edge.to.y) / 2;
        ctx.fillStyle = 'rgba(161, 161, 170, 0.5)';
        ctx.font = '9px JetBrains Mono';
        ctx.textAlign = 'center';
        ctx.fillText(edge.label.length > 12 ? edge.label.slice(0, 12) + '…' : edge.label, mx, my - 4);
    });

    // Draw nodes
    graphNodes.forEach(node => {
        const r = node.type === 'subject' ? 8 : 5;
        const color = node.type === 'subject' ? '#4F8EF7' : 'rgba(167, 139, 250, 0.7)';

        // Glow
        ctx.beginPath();
        ctx.arc(node.x, node.y, r + 4, 0, Math.PI * 2);
        ctx.fillStyle = node.type === 'subject' ? 'rgba(79, 142, 247, 0.1)' : 'rgba(167, 139, 250, 0.08)';
        ctx.fill();

        // Node
        ctx.beginPath();
        ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();

        // Label
        ctx.fillStyle = '#A1A1AA';
        ctx.font = node.type === 'subject' ? 'bold 11px Inter' : '10px Inter';
        ctx.textAlign = 'center';
        ctx.fillText(node.label, node.x, node.y + r + 14);
    });

    ctx.restore();
}

// Graph interaction
function setupGraphInteraction() {
    const canvas = document.getElementById('graphCanvas');
    const container = document.getElementById('graphContainer');

    canvas.addEventListener('mousedown', (e) => {
        graphDragging = true;
        graphDragStart = { x: e.clientX - graphOffset.x, y: e.clientY - graphOffset.y };
    });

    window.addEventListener('mousemove', (e) => {
        if (!graphDragging) return;
        graphOffset.x = e.clientX - graphDragStart.x;
        graphOffset.y = e.clientY - graphDragStart.y;
        const ctx = canvas.getContext('2d');
        drawGraph(ctx, container.clientWidth, container.clientHeight);
    });

    window.addEventListener('mouseup', () => { graphDragging = false; });

    document.getElementById('graphZoomIn').addEventListener('click', () => {
        graphZoom = Math.min(graphZoom * 1.2, 3);
        const ctx = canvas.getContext('2d');
        drawGraph(ctx, container.clientWidth, container.clientHeight);
    });

    document.getElementById('graphZoomOut').addEventListener('click', () => {
        graphZoom = Math.max(graphZoom / 1.2, 0.3);
        const ctx = canvas.getContext('2d');
        drawGraph(ctx, container.clientWidth, container.clientHeight);
    });

    document.getElementById('graphReset').addEventListener('click', () => {
        graphZoom = 1;
        graphOffset = { x: 0, y: 0 };
        const ctx = canvas.getContext('2d');
        drawGraph(ctx, container.clientWidth, container.clientHeight);
    });
}

// ── Memory Table ──
function applyFilters() {
    let list = [...allMemories].filter(m => m.is_active);

    // Search (natural language — match any field)
    if (searchQuery) {
        const q = searchQuery.toLowerCase();
        // NL aliases
        const nlMap = {
            'job': ['works_at', 'role', 'position', 'job', 'employer', 'company'],
            'name': ['name', 'called', 'known_as', 'full_name'],
            'location': ['lives_in', 'located', 'city', 'country', 'location'],
            'preference': ['prefers', 'likes', 'preference', 'favorite'],
            'skill': ['knows', 'skill', 'uses', 'expert', 'proficient']
        };

        // Expand NL query
        let expandedTerms = [q];
        Object.entries(nlMap).forEach(([key, aliases]) => {
            if (q.includes(key)) {
                expandedTerms = expandedTerms.concat(aliases);
            }
        });

        list = list.filter(m => {
            const text = `${m.subject} ${m.predicate} ${m.object}`.toLowerCase();
            return expandedTerms.some(t => text.includes(t));
        });
    }

    // Filter
    if (activeFilter === 'high') list = list.filter(m => m.confidence >= 0.75);
    if (activeFilter === 'low') list = list.filter(m => m.confidence < 0.75);

    // Sort
    list.sort((a, b) => {
        let va = a[sortField];
        let vb = b[sortField];
        if (typeof va === 'string') va = va.toLowerCase();
        if (typeof vb === 'string') vb = vb.toLowerCase();
        if (va < vb) return -1 * sortDir;
        if (va > vb) return 1 * sortDir;
        return 0;
    });

    filteredMemories = list;
    currentPage = 0;
    renderTable();
}

function renderTable() {
    const tbody = document.getElementById('memoryTableBody');
    const total = filteredMemories.length;
    const start = currentPage * PAGE_SIZE;
    const end = Math.min(start + PAGE_SIZE, total);
    const page = filteredMemories.slice(start, end);

    document.getElementById('memoryTotalLabel').textContent = `${total} ${total === 1 ? 'memory' : 'memories'}`;
    document.getElementById('paginationInfo').textContent =
        total > 0 ? `Showing ${start + 1}–${end} of ${total}` : 'No memories found';

    document.getElementById('prevPage').disabled = currentPage === 0;
    document.getElementById('nextPage').disabled = end >= total;

    if (page.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7"><div class="dash-table-empty">
            <p>${searchQuery ? 'No memories match your search' : 'No memories yet'}</p>
            <p style="font-size:0.8rem">${searchQuery ? 'Try a different query' : 'Chat with the AI to create memories'}</p>
        </div></td></tr>`;
        return;
    }

    tbody.innerHTML = page.map(m => {
        const conf = m.confidence;
        const confClass = conf >= 0.75 ? 'conf-high' : conf >= 0.5 ? 'conf-mid' : 'conf-low';
        const confWidth = `${(conf * 100).toFixed(0)}%`;
        const date = new Date(m.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

        return `<tr>
            <td class="td-subject">${esc(m.subject)}</td>
            <td class="td-predicate">${esc(m.predicate)}</td>
            <td class="td-object" title="${esc(m.object)}">${esc(m.object)}</td>
            <td>
                <div class="confidence-bar">
                    <div class="confidence-track"><div class="confidence-fill ${confClass}" style="width:${confWidth}"></div></div>
                    <span style="font-size:0.75rem">${(conf * 100).toFixed(0)}%</span>
                </div>
            </td>
            <td><span class="version-badge">v${m.version}</span></td>
            <td style="font-size:0.78rem;white-space:nowrap">${date}</td>
            <td>
                <div class="dash-table-actions">
                    <button class="dash-icon-btn" onclick="viewHistory('${esc(m.subject)}','${esc(m.predicate)}')" title="Version history">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                    </button>
                    <button class="dash-icon-btn danger" onclick="deleteMemory('${m.id}')" title="Delete memory">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
                    </button>
                </div>
            </td>
        </tr>`;
    }).join('');
}

// ── Version History ──
async function viewHistory(subject, predicate) {
    try {
        const data = await apiFetch(
            `/api/v1/user/memories/${encodeURIComponent(subject)}/${encodeURIComponent(predicate)}/history`
        );

        const modal = document.getElementById('modalOverlay');
        const body = document.getElementById('modalBody');
        document.getElementById('modalTitle').textContent = `${subject} → ${predicate}`;

        body.innerHTML = data.versions.map((v, i) => `
            <div class="version-item ${v.is_active ? 'current' : ''}">
                <div class="version-item-header">
                    <span>Version ${v.version} ${v.is_active ? '(current)' : ''}</span>
                    <span>${new Date(v.created_at).toLocaleString()}</span>
                </div>
                <div class="version-item-value">${esc(v.object)}</div>
                <div class="version-item-meta">
                    <span>Confidence: ${(v.confidence * 100).toFixed(0)}%</span>
                    <span>${v.is_active ? '✓ Active' : '✗ Superseded'}</span>
                </div>
            </div>
        `).join('');

        modal.classList.add('open');
    } catch (err) {
        toast('Failed to load version history', 'error');
    }
}

// ── Delete Memory ──
async function deleteMemory(id) {
    if (!confirm('Delete this memory? It will be soft-deleted.')) return;

    try {
        await apiFetch(`/api/v1/user/memories/${id}`, { method: 'DELETE' });
        toast('Memory deleted', 'success');
        loadDashboard();
    } catch (err) {
        toast(`Delete failed: ${err.message}`, 'error');
    }
}

// ── GDPR Export ──
async function exportData() {
    const btn = document.getElementById('exportBtn');
    btn.disabled = true;
    btn.innerHTML = 'Exporting...';

    try {
        const data = await apiFetch('/api/v1/user/memories?limit=10000');

        const exportPayload = {
            exported_at: new Date().toISOString(),
            user_memories: data.memories,
            total_count: data.total_count,
            active_count: data.active_count,
            metadata: {
                format: 'AI Memory SDK GDPR Export',
                version: '1.0',
                note: 'This file contains all your AI memory data. You may request deletion by contacting support.'
            }
        };

        const blob = new Blob([JSON.stringify(exportPayload, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ai-memory-export-${new Date().toISOString().slice(0, 10)}.json`;
        a.click();
        URL.revokeObjectURL(url);
        toast('Data exported successfully', 'success');
    } catch (err) {
        toast(`Export failed: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> Export All Data`;
    }
}

// ── Listeners ──
function setupListeners() {
    // Logout
    document.getElementById('logoutBtn').addEventListener('click', () => {
        localStorage.removeItem('token');
        localStorage.removeItem('role');
        window.location.href = 'login.html';
    });

    // Search (debounced)
    let searchTimer;
    document.getElementById('memorySearch').addEventListener('input', (e) => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => {
            searchQuery = e.target.value.trim();
            applyFilters();
        }, 250);
    });

    // Filters
    document.querySelectorAll('.dash-filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.dash-filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            activeFilter = btn.dataset.filter;
            applyFilters();
        });
    });

    // Sort
    document.querySelectorAll('.dash-table thead th[data-sort]').forEach(th => {
        th.addEventListener('click', () => {
            const field = th.dataset.sort;
            if (sortField === field) {
                sortDir *= -1;
            } else {
                sortField = field;
                sortDir = 1;
            }
            document.querySelectorAll('.dash-table thead th').forEach(h => h.classList.remove('sorted'));
            th.classList.add('sorted');
            applyFilters();
        });
    });

    // Pagination
    document.getElementById('prevPage').addEventListener('click', () => {
        if (currentPage > 0) { currentPage--; renderTable(); }
    });
    document.getElementById('nextPage').addEventListener('click', () => {
        if ((currentPage + 1) * PAGE_SIZE < filteredMemories.length) { currentPage++; renderTable(); }
    });

    // Modal close
    document.getElementById('modalClose').addEventListener('click', closeModal);
    document.getElementById('modalOverlay').addEventListener('click', (e) => {
        if (e.target === e.currentTarget) closeModal();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });

    // Export
    document.getElementById('exportBtn').addEventListener('click', exportData);

    // Graph interaction
    setupGraphInteraction();

    // Resize handler
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            renderTimeline();
            renderKnowledgeGraph();
        }, 200);
    });
}

function closeModal() {
    document.getElementById('modalOverlay').classList.remove('open');
}

// ── Toast ──
function toast(message, type = 'info') {
    const el = document.getElementById('toast');
    el.textContent = message;
    el.className = `dash-toast ${type} show`;
    setTimeout(() => { el.classList.remove('show'); }, 3000);
}

// ── Escape HTML ──
function esc(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ── Global exports ──
window.viewHistory = viewHistory;
window.deleteMemory = deleteMemory;
