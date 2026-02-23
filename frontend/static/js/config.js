/**
 * AI Memory SDK — Frontend Configuration
 * Centralized settings for API endpoints and environment detection.
 */

const CONFIG = {
    // Determine if running locally
    isLocal: window.location.hostname === 'localhost' ||
        window.location.hostname === '127.0.0.1' ||
        window.location.protocol === 'file:',

    // Backend API Base URL
    // Replace with your actual Render URL if different
    get API_URL() {
        return this.isLocal
            ? 'http://localhost:8000/api/v1'
            : 'https://ai-memory-sdk.onrender.com/api/v1';
    },

    // UI Configuration
    TENANT_ID: 'default-tenant'
};

// Export to window for global access
window.CONFIG = CONFIG;
