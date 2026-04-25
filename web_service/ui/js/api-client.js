/**
 * API Client for X-AnyLabeling Web Service
 */

class APIClient {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl || '';
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const response = await fetch(url, {
            ...options,
            headers: {
                ...options.headers,
            },
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return response.json();
    }

    // Health check
    async health() {
        return this.request('/api/health');
    }

    // Models
    async getModels() {
        return this.request('/api/models');
    }

    async getModel(modelId) {
        return this.request(`/api/models/${modelId}`);
    }

    // Formats
    async getFormats() {
        return this.request('/api/formats');
    }

    // Upload
    async uploadFile(file, sessionId = null) {
        const formData = new FormData();
        formData.append('file', file);
        if (sessionId) {
            formData.append('session_id', sessionId);
        }

        const response = await fetch(`${this.baseUrl}/api/upload`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
            throw new Error(error.detail || 'Upload failed');
        }

        return response.json();
    }

    async uploadMultipleFiles(files, sessionId = null) {
        const formData = new FormData();
        for (const file of files) {
            formData.append('files', file);
        }
        if (sessionId) {
            formData.append('session_id', sessionId);
        }

        const response = await fetch(`${this.baseUrl}/api/upload/multiple`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
            throw new Error(error.detail || 'Upload failed');
        }

        return response.json();
    }

    async getSessionFiles(sessionId) {
        return this.request(`/api/session/${sessionId}/files`);
    }

    async deleteSession(sessionId) {
        return this.request(`/api/session/${sessionId}`, { method: 'DELETE' });
    }

    // Processing
    async startProcessing(sessionId, modelId, outputFormat, options = {}, labelingMode = 'auto', specificClasses = null) {
        return this.request('/api/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: sessionId,
                model_id: modelId,
                output_format: outputFormat,
                options: options || {},
                labeling_mode: labelingMode,
                specific_classes: specificClasses,
            }),
        });
    }

    async getJobStatus(jobId) {
        return this.request(`/api/status/${jobId}`);
    }

    async getJobResult(jobId) {
        return this.request(`/api/result/${jobId}`);
    }

    getDownloadUrl(jobId) {
        return `${this.baseUrl}/api/download/${jobId}`;
    }
}

// Export for use in app.js
window.APIClient = APIClient;
