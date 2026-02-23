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
    // Defaulting to the most likely Render URL based on repository name
    get API_URL() {
        const url = this.isLocal
            ? 'http://localhost:8000/api/v1'
            : 'https://ai-memory-sdk.onrender.com/api/v1';

        // Diagnostic log for the user to see in their browser console (F12)
        console.log(`[SDK CONFIG] Mode: ${this.isLocal ? 'DEVELOPMENT' : 'PRODUCTION'}`);
        console.log(`[SDK CONFIG] API Endpoint: ${url}`);
        return url;
    },

    // UI Configuration
    TENANT_ID: 'default-tenant'
};

// Global Error Helper for Fetch
window.handleFetchError = (err, context) => {
    console.group(`[SDK ERROR] ${context}`);
    console.error('Message:', err.message);
    console.error('Stack:', err.stack);
    console.log('Current Host:', window.location.hostname);
    console.log('Target API:', CONFIG.API_URL);
    console.groupEnd();

    if (err.message === 'Failed to fetch') {
        return `Failed to connect to backend at ${CONFIG.API_URL}. Check if the Render service is sleeping or if CORS is blocking this origin (${window.location.origin}).`;
    }
    return err.message;
};

// Export to window for global access
window.CONFIG = CONFIG;
