/**
 * ============================================
 * AI-DRIVEN CLOUD SECURITY DASHBOARD
 * Main JavaScript Application
 * ============================================
 * 
 * This file connects the frontend to the FastAPI backend.
 * All API calls use JWT authentication.
 */

// ============================================
// CONFIGURATION
// ============================================

/**
 * Backend API base URL
 * Change this if backend is hosted elsewhere
 */
const API_BASE_URL = 'http://localhost:8000/api';

// ============================================
// SESSION MANAGEMENT
// ============================================

/**
 * Check if user is authenticated
 * @returns {boolean} True if user is logged in
 */
function isAuthenticated() {
    return sessionStorage.getItem('isLoggedIn') === 'true' &&
        sessionStorage.getItem('authToken') !== null;
}

/**
 * Get JWT token from session
 * @returns {string|null} JWT token or null
 */
function getAuthToken() {
    return sessionStorage.getItem('authToken');
}

/**
 * Get current user info
 * @returns {Object|null} User object or null if not logged in
 */
function getCurrentUser() {
    const userJson = sessionStorage.getItem('currentUser');
    return userJson ? JSON.parse(userJson) : null;
}

/**
 * Set user session after login
 * @param {Object} user - User object to store
 * @param {string} token - JWT token
 */
function setUserSession(user, token) {
    sessionStorage.setItem('isLoggedIn', 'true');
    sessionStorage.setItem('currentUser', JSON.stringify(user));
    sessionStorage.setItem('authToken', token);
}

/**
 * Clear user session on logout
 */
function clearUserSession() {
    sessionStorage.removeItem('isLoggedIn');
    sessionStorage.removeItem('currentUser');
    sessionStorage.removeItem('authToken');
}

/**
 * Redirect to login if not authenticated
 * Call this on protected pages
 */
function requireAuth() {
    if (!isAuthenticated()) {
        window.location.href = 'index.html';
        return false;
    }
    return true;
}

// ============================================
// API HELPER FUNCTIONS
// ============================================

/**
 * Make authenticated API request
 * @param {string} endpoint - API endpoint (without base URL)
 * @param {Object} options - Fetch options
 * @returns {Promise<Object>} Response data
 */
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;

    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    // Add auth token if available
    const token = getAuthToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
        ...options,
        headers
    });

    // Handle 401 - redirect to login
    if (response.status === 401) {
        clearUserSession();
        window.location.href = 'index.html';
        throw new Error('Session expired');
    }

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'API request failed');
    }

    return response.json();
}

// ============================================
// API FUNCTIONS - Connected to Backend
// ============================================

/**
 * Login API call
 * POST /api/auth/login
 * @param {string} username 
 * @param {string} password 
 * @returns {Promise<Object>} Response with success status and user data
 */
async function apiLogin(username, password) {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Login error:', error);
        return { success: false, error: 'Network error. Is the backend running?' };
    }
}

/**
 * Fetch dashboard statistics
 * GET /api/dashboard/stats
 * @returns {Promise<Object>} Dashboard statistics
 */
async function apiGetDashboardStats() {
    return apiRequest('/dashboard/stats');
}

/**
 * Fetch all incidents
 * GET /api/incidents
 * @returns {Promise<Array>} List of incidents
 */
async function apiGetIncidents() {
    return apiRequest('/incidents');
}

/**
 * Fetch incident details by ID
 * GET /api/incidents/{incident_id}
 * @param {number} incidentId - Incident ID
 * @returns {Promise<Object|null>} Incident details or null if not found
 */
async function apiGetIncidentDetails(incidentId) {
    try {
        return await apiRequest(`/incidents/${incidentId}`);
    } catch (error) {
        console.error('Error fetching incident details:', error);
        return null;
    }
}

/**
 * Trigger incident response action
 * POST /api/incidents/{incident_id}/respond
 * @param {number} incidentId - Incident ID
 * @param {string} action - Action type
 * @returns {Promise<Object>} Response with success status
 */
async function apiTriggerResponse(incidentId, action) {
    return apiRequest(`/incidents/${incidentId}/respond`, {
        method: 'POST',
        body: JSON.stringify({ action })
    });
}

// ============================================
// UI HELPER FUNCTIONS
// ============================================

/**
 * Get CSS class for severity badge (Tailwind CSS)
 * @param {string} severity - Severity level
 * @returns {string} CSS class name
 */
function getSeverityClass(severity) {
    const severityLower = severity.toLowerCase();
    const classMap = {
        'critical': 'bg-severity-critical/15 text-severity-critical border-severity-critical/30',
        'high': 'bg-severity-high/15 text-severity-high border-severity-high/30',
        'medium': 'bg-severity-medium/15 text-severity-medium border-severity-medium/30',
        'low': 'bg-severity-low/15 text-severity-low border-severity-low/30'
    };
    return classMap[severityLower] || classMap['low'];
}

/**
 * Get CSS class for status badge (Tailwind CSS)
 * @param {string} status - Status value
 * @returns {string} CSS class name
 */
function getStatusClass(status) {
    const statusLower = status.toLowerCase().replace(' ', '-');
    const classMap = {
        'detected': 'bg-status-detected/15 text-status-detected border-status-detected/30',
        'investigating': 'bg-status-investigating/15 text-status-investigating border-status-investigating/30',
        'resolved': 'bg-status-resolved/15 text-status-resolved border-status-resolved/30',
        'mitigated': 'bg-status-mitigated/15 text-status-mitigated border-status-mitigated/30',
        'response-initiated': 'bg-status-investigating/15 text-status-investigating border-status-investigating/30'
    };
    return classMap[statusLower] || classMap['detected'];
}

/**
 * Format large numbers with commas
 * @param {number} num - Number to format
 * @returns {string} Formatted number string
 */
function formatNumber(num) {
    return num.toLocaleString();
}

/**
 * Show a temporary alert message
 * @param {string} message - Message to display
 * @param {string} type - Alert type (success, warning, info, danger)
 * @param {number} duration - Duration in ms before auto-hide
 */
function showAlert(message, type = 'info', duration = 3000) {
    const existingAlerts = document.querySelectorAll('.alert-popup');
    existingAlerts.forEach(alert => alert.remove());

    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-popup`;
    alert.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 2000;
        min-width: 300px;
        animation: slideIn 0.3s ease;
    `;
    alert.innerHTML = `
        <span class="alert-icon">
            ${type === 'success' ? '✓' : type === 'danger' ? '✕' : 'ℹ'}
        </span>
        <span>${message}</span>
    `;

    document.body.appendChild(alert);

    setTimeout(() => {
        alert.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => alert.remove(), 300);
    }, duration);
}

/**
 * Update user info in sidebar
 */
function updateSidebarUserInfo() {
    const user = getCurrentUser();
    if (!user) return;

    const userNameEl = document.querySelector('.user-name');
    const userRoleEl = document.querySelector('.user-role');
    const userAvatarEl = document.querySelector('.user-avatar');

    if (userNameEl) userNameEl.textContent = user.name;
    if (userRoleEl) userRoleEl.textContent = user.role;
    if (userAvatarEl) userAvatarEl.textContent = user.name.charAt(0).toUpperCase();
}

/**
 * Set active navigation link based on current page
 */
function setActiveNavLink() {
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    const navLinks = document.querySelectorAll('.nav-link');

    navLinks.forEach(link => {
        link.classList.remove('active');
        const href = link.getAttribute('href');
        if (href === currentPage) {
            link.classList.add('active');
        }
    });
}

// ============================================
// LOGIN PAGE FUNCTIONS
// ============================================

/**
 * Initialize login page
 */
function initLoginPage() {
    const loginForm = document.getElementById('loginForm');
    const errorDiv = document.getElementById('loginError');

    if (!loginForm) return;

    // If already logged in, redirect to dashboard
    if (isAuthenticated()) {
        window.location.href = 'dashboard.html';
        return;
    }

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;
        const submitBtn = loginForm.querySelector('button[type="submit"]');

        submitBtn.disabled = true;
        submitBtn.textContent = 'Signing in...';
        errorDiv.classList.remove('show');

        try {
            const response = await apiLogin(username, password);

            if (response.success) {
                setUserSession(response.data, response.token);
                window.location.href = 'dashboard.html';
            } else {
                errorDiv.textContent = response.error;
                errorDiv.classList.add('show');
            }
        } catch (error) {
            errorDiv.textContent = 'Network error. Please check if backend is running.';
            errorDiv.classList.add('show');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Sign In';
        }
    });
}

// ============================================
// DASHBOARD PAGE FUNCTIONS
// ============================================

async function initDashboardPage() {
    if (!requireAuth()) return;

    updateSidebarUserInfo();
    setActiveNavLink();

    await loadDashboardStats();
    await loadRecentIncidents();
}

async function loadDashboardStats() {
    try {
        const stats = await apiGetDashboardStats();

        const totalLogsEl = document.getElementById('totalLogs');
        const totalIncidentsEl = document.getElementById('totalIncidents');
        const criticalCountEl = document.getElementById('criticalCount');
        const highCountEl = document.getElementById('highCount');

        if (totalLogsEl) totalLogsEl.textContent = formatNumber(stats.total_logs_ingested);
        if (totalIncidentsEl) totalIncidentsEl.textContent = formatNumber(stats.total_incidents_detected);
        if (criticalCountEl) criticalCountEl.textContent = formatNumber(stats.critical_incidents);
        if (highCountEl) highCountEl.textContent = formatNumber(stats.high_incidents);
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
        showAlert('Failed to load dashboard stats', 'danger');
    }
}

async function loadRecentIncidents() {
    const listContainer = document.getElementById('recentIncidentsList');
    if (!listContainer) return;

    try {
        const incidents = await apiGetIncidents();
        const recentIncidents = incidents.slice(0, 5);

        listContainer.innerHTML = recentIncidents.map(incident => `
            <li class="flex items-center justify-between py-4 border-b border-border last:border-b-0">
                <div class="flex items-center gap-4">
                    <span class="inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-medium ${getSeverityClass(incident.severity)}">${incident.severity}</span>
                    <div class="flex flex-col">
                        <span class="font-mono text-sm font-medium text-foreground">#${incident.incident_id}</span>
                        <span class="text-xs text-muted-foreground">${incident.timestamp}</span>
                    </div>
                </div>
                <a href="incident_details.html?id=${incident.incident_id}" class="rounded-md border border-border bg-transparent px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors">View</a>
            </li>
        `).join('');
    } catch (error) {
        console.error('Error loading recent incidents:', error);
        listContainer.innerHTML = '<li class="text-muted-foreground text-center py-8">Failed to load incidents</li>';
    }
}

// ============================================
// INCIDENTS LIST PAGE FUNCTIONS
// ============================================

async function initIncidentsPage() {
    if (!requireAuth()) return;

    updateSidebarUserInfo();
    setActiveNavLink();

    await loadIncidentsTable();
}

async function loadIncidentsTable() {
    const tableBody = document.getElementById('incidentsTableBody');
    if (!tableBody) return;

    try {
        const incidents = await apiGetIncidents();

        tableBody.innerHTML = incidents.map(incident => `
            <tr class="border-b border-border hover:bg-muted/50 transition-colors">
                <td class="px-6 py-4">
                    <div class="flex flex-col">
                        <span class="font-mono text-sm font-medium text-foreground">#${incident.incident_id}</span>
                        <span class="text-xs text-muted-foreground truncate max-w-xs">${incident.description || ''}</span>
                    </div>
                </td>
                <td class="px-6 py-4">
                    <span class="inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-medium ${getSeverityClass(incident.severity)}">${incident.severity}</span>
                </td>
                <td class="px-6 py-4">
                    <span class="inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-medium ${getStatusClass(incident.status)}">${incident.status}</span>
                </td>
                <td class="px-6 py-4 font-mono text-sm text-muted-foreground">${incident.timestamp}</td>
                <td class="px-6 py-4 text-right">
                    <a href="incident_details.html?id=${incident.incident_id}" class="rounded-md border border-border bg-transparent px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors">
                        View Details
                    </a>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading incidents:', error);
        tableBody.innerHTML = '<tr><td colspan="5" class="px-6 py-12 text-center text-muted-foreground">Failed to load incidents</td></tr>';
    }
}

// ============================================
// INCIDENT DETAILS PAGE FUNCTIONS
// ============================================

async function initIncidentDetailsPage() {
    if (!requireAuth()) return;

    updateSidebarUserInfo();
    setActiveNavLink();

    const urlParams = new URLSearchParams(window.location.search);
    const incidentId = parseInt(urlParams.get('id'));

    if (!incidentId) {
        showAlert('Invalid incident ID', 'danger');
        setTimeout(() => window.location.href = 'incidents.html', 2000);
        return;
    }

    await loadIncidentDetails(incidentId);
}

async function loadIncidentDetails(incidentId) {
    try {
        const incident = await apiGetIncidentDetails(incidentId);

        if (!incident) {
            showAlert('Incident not found', 'danger');
            setTimeout(() => window.location.href = 'incidents.html', 2000);
            return;
        }

        document.getElementById('incidentId').textContent = `#${incident.incident_id}`;
        document.getElementById('incidentSeverity').innerHTML =
            `<span class="inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-medium ${getSeverityClass(incident.severity)}">${incident.severity}</span>`;
        document.getElementById('incidentStatus').innerHTML =
            `<span class="inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-medium ${getStatusClass(incident.status)}">${incident.status}</span>`;
        document.getElementById('incidentTimestamp').textContent = incident.timestamp;
        document.getElementById('incidentSourceIp').textContent = incident.source_ip;
        document.getElementById('incidentDestination').textContent = incident.destination;
        document.getElementById('incidentAnomalyType').textContent = incident.anomaly_type;
        document.getElementById('incidentConfidence').textContent = `${incident.confidence_score}%`;
        document.getElementById('incidentDescription').textContent = incident.description;
        document.getElementById('incidentRecommendation').textContent = incident.recommended_action;

        const actionsList = document.getElementById('actionsTakenList');
        if (actionsList) {
            actionsList.innerHTML = incident.actions_taken.map(action =>
                `<li class="flex items-center gap-2 text-sm text-foreground py-2 border-b border-border last:border-b-0">
                    <svg class="h-4 w-4 text-primary flex-shrink-0" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
                    ${action}
                </li>`
            ).join('');
        }

        const triggerBtn = document.getElementById('triggerResponseBtn');
        if (triggerBtn) {
            triggerBtn.addEventListener('click', () => handleTriggerResponse(incidentId));
        }
    } catch (error) {
        console.error('Error loading incident details:', error);
        showAlert('Failed to load incident details', 'danger');
    }
}

async function handleTriggerResponse(incidentId) {
    const btn = document.getElementById('triggerResponseBtn');
    if (!btn) return;

    const confirmed = confirm(
        `Are you sure you want to trigger automated response for incident #${incidentId}?\n\n` +
        `This will initiate the recommended security actions.`
    );

    if (!confirmed) return;

    btn.disabled = true;
    btn.textContent = 'Processing...';

    try {
        const response = await apiTriggerResponse(incidentId, 'automated_response');

        if (response.success) {
            showAlert(response.message, 'success', 5000);

            const statusEl = document.getElementById('incidentStatus');
            if (statusEl) {
                statusEl.innerHTML = '<span class="badge badge-investigating">Response Initiated</span>';
            }

            // Update actions list
            const actionsList = document.getElementById('actionsTakenList');
            if (actionsList && response.actions_taken) {
                const newActions = response.actions_taken.map(action =>
                    `<li>${action}</li>`
                ).join('');
                actionsList.innerHTML += newActions;
            }

            btn.textContent = 'Response Triggered ✓';
            btn.classList.remove('btn-danger');
            btn.classList.add('btn-success');
        } else {
            throw new Error('Response failed');
        }
    } catch (error) {
        showAlert('Failed to trigger response. Please try again.', 'danger');
        btn.disabled = false;
        btn.textContent = 'Trigger Response';
    }
}

// ============================================
// LOGOUT FUNCTION
// ============================================

function handleLogout() {
    clearUserSession();
    window.location.href = 'index.html';
}

// ============================================
// PAGE INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';

    const logoutBtns = document.querySelectorAll('.logout-btn');
    logoutBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            handleLogout();
        });
    });

    switch (currentPage) {
        case 'index.html':
        case '':
            initLoginPage();
            break;
        case 'dashboard.html':
            initDashboardPage();
            break;
        case 'incidents.html':
            initIncidentsPage();
            break;
        case 'incident_details.html':
            initIncidentDetailsPage();
            break;
    }
});

// Animation styles
const animationStyles = document.createElement('style');
animationStyles.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(animationStyles);
