// Knowledge-base Search Engine Frontend JavaScript

class KnowledgeBaseApp {
    constructor() {
        this.apiBaseUrl = 'http://localhost:8000';
        this.documents = [];
        this.initializeEventListeners();
        this.checkApiConnection();
    }

    initializeEventListeners() {
        // File upload events
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const searchButton = document.getElementById('searchButton');
        const searchInput = document.getElementById('searchInput');

        // Upload area click
        uploadArea.addEventListener('click', () => fileInput.click());

        // File input change
        fileInput.addEventListener('change', (e) => this.handleFileUpload(e.target.files));

        // Drag and drop events
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            this.handleFileUpload(e.dataTransfer.files);
        });

        // Search events
        searchButton.addEventListener('click', () => this.performSearch());
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.performSearch();
            }
        });
    }

    async handleFileUpload(files) {
        if (!files || files.length === 0) return;

        const uploadProgress = document.getElementById('uploadProgress');
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');

        uploadProgress.style.display = 'block';

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            
            // Validate file type
            if (!this.isValidFileType(file)) {
                this.showStatus(`Invalid file type: ${file.name}. Only PDF and TXT files are supported.`, 'error');
                continue;
            }

            // Validate file size (50MB limit)
            if (file.size > 50 * 1024 * 1024) {
                this.showStatus(`File too large: ${file.name}. Maximum size is 50MB.`, 'error');
                continue;
            }

            try {
                progressText.textContent = `Uploading ${file.name}...`;
                progressFill.style.width = '0%';

                const formData = new FormData();
                formData.append('file', file);

                const response = await fetch(`${this.apiBaseUrl}/documents`, {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    const result = await response.json();
                    progressFill.style.width = '100%';
                    this.showStatus(`Successfully uploaded: ${file.name}`, 'success');
                    this.loadDocuments(); // Refresh document list
                } else {
                    const error = await response.json();
                    throw new Error(error.detail || 'Upload failed');
                }
            } catch (error) {
                this.showStatus(`Failed to upload ${file.name}: ${error.message}`, 'error');
            }
        }

        // Hide progress after a delay
        setTimeout(() => {
            uploadProgress.style.display = 'none';
        }, 2000);
    }

    isValidFileType(file) {
        const validTypes = ['application/pdf', 'text/plain'];
        const validExtensions = ['.pdf', '.txt'];
        
        return validTypes.includes(file.type) || 
               validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
    }

    async loadDocuments() {
        const documentsList = document.getElementById('documentsList');
        const documentsLoading = document.getElementById('documentsLoading');

        documentsLoading.style.display = 'block';

        try {
            const response = await fetch(`${this.apiBaseUrl}/documents`);
            
            if (response.ok) {
                const data = await response.json();
                this.documents = data.documents;
                this.renderDocuments();
            } else {
                throw new Error('Failed to load documents');
            }
        } catch (error) {
            documentsList.innerHTML = `<div class="loading">Failed to load documents: ${error.message}</div>`;
        } finally {
            documentsLoading.style.display = 'none';
        }
    }

    renderDocuments() {
        const documentsList = document.getElementById('documentsList');

        if (this.documents.length === 0) {
            documentsList.innerHTML = '<div class="loading">No documents uploaded yet.</div>';
            return;
        }

        const documentsHtml = this.documents.map(doc => `
            <div class="document-item">
                <div class="document-info">
                    <div class="document-name">${this.escapeHtml(doc.filename)}</div>
                    <div class="document-meta">
                        ${doc.file_type.toUpperCase()} • ${this.formatFileSize(doc.file_size)} • 
                        ${this.formatDate(doc.upload_date)} • ${doc.chunk_count} chunks
                    </div>
                </div>
                <div class="document-status status-${doc.processing_status}">
                    ${doc.processing_status}
                </div>
                <div class="document-actions">
                    <button class="btn-delete" onclick="app.deleteDocument('${doc.id}')">Delete</button>
                </div>
            </div>
        `).join('');

        documentsList.innerHTML = documentsHtml;
    }

    async deleteDocument(documentId) {
        if (!confirm('Are you sure you want to delete this document?')) {
            return;
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/documents/${documentId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.showStatus('Document deleted successfully', 'success');
                this.loadDocuments(); // Refresh document list
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Delete failed');
            }
        } catch (error) {
            this.showStatus(`Failed to delete document: ${error.message}`, 'error');
        }
    }

    async performSearch() {
        const searchInput = document.getElementById('searchInput');
        const searchButton = document.getElementById('searchButton');
        const searchResults = document.getElementById('searchResults');
        const searchLoading = document.getElementById('searchLoading');

        const query = searchInput.value.trim();
        if (!query) {
            this.showStatus('Please enter a search query', 'error');
            return;
        }

        // Show loading state
        searchLoading.style.display = 'block';
        searchResults.style.display = 'none';
        searchButton.disabled = true;

        try {
            const response = await fetch(`${this.apiBaseUrl}/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    query: query,
                    top_k: 5
                })
            });

            if (response.ok) {
                const result = await response.json();
                this.renderSearchResults(result);
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Search failed');
            }
        } catch (error) {
            console.error('Search error:', error);
            this.showStatus(`Search failed: ${error.message}. Make sure documents are uploaded and processed.`, 'error');
        } finally {
            searchLoading.style.display = 'none';
            searchButton.disabled = false;
        }
    }

    renderSearchResults(result) {
        const searchResults = document.getElementById('searchResults');
        const answerContent = document.getElementById('answerContent');
        const sourcesList = document.getElementById('sourcesList');

        // Format and render answer with better structure
        const formattedAnswer = this.formatAnswer(result.answer);
        answerContent.innerHTML = formattedAnswer;

        // Render sources
        if (result.citations && result.citations.length > 0) {
            const sourcesHtml = result.citations.map(citation => `
                <div class="source-item">
                    <div class="source-title">${this.escapeHtml(citation.filename)}</div>
                    <div class="source-content">${this.escapeHtml(citation.content)}</div>
                    <div class="source-score">Relevance: ${(citation.relevance_score * 100).toFixed(1)}%</div>
                </div>
            `).join('');
            sourcesList.innerHTML = sourcesHtml;
        } else {
            sourcesList.innerHTML = '<div class="loading">No sources found</div>';
        }

        searchResults.style.display = 'block';
    }

    formatAnswer(answer) {
        if (!answer) return '';
        
        // First convert bold text BEFORE escaping HTML to avoid double escaping
        let formatted = answer;
        
        // Convert bold text (markdown style)
        formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        
        // Now escape HTML for safety (but preserve our <strong> tags)
        formatted = formatted.replace(/&/g, '&amp;')
                            .replace(/</g, '&lt;')
                            .replace(/>/g, '&gt;')
                            .replace(/"/g, '&quot;')
                            .replace(/'/g, '&#39;');
        
        // Restore our strong tags
        formatted = formatted.replace(/&lt;strong&gt;(.+?)&lt;\/strong&gt;/g, '<strong>$1</strong>');
        
        // Convert bullet points
        formatted = formatted.replace(/^[•\-\*]\s+(.+)$/gm, '<div class="bullet-point">$1</div>');
        
        // Convert numbered lists
        formatted = formatted.replace(/^\d+\.\s+(.+)$/gm, '<div class="bullet-point">$1</div>');
        
        // Convert line breaks to proper spacing
        formatted = formatted.replace(/\n\n/g, '</p><p>');
        formatted = formatted.replace(/\n/g, '<br>');
        
        // Wrap in paragraphs
        if (!formatted.includes('<p>')) {
            formatted = '<p>' + formatted + '</p>';
        }
        
        return formatted;
    }

    showStatus(message, type = 'info') {
        const statusMessage = document.getElementById('statusMessage');
        statusMessage.textContent = message;
        statusMessage.className = `status-message status-${type}`;
        statusMessage.style.display = 'block';

        // Auto-hide after 5 seconds
        setTimeout(() => {
            statusMessage.style.display = 'none';
        }, 5000);
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async checkApiConnection() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/health`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            if (response.ok) {
                const health = await response.json();
                if (health.status === 'healthy') {
                    this.showStatus('Connected to API successfully', 'success');
                    this.loadDocuments();
                } else {
                    this.showStatus('API is not healthy', 'error');
                }
            } else {
                throw new Error('API not responding');
            }
        } catch (error) {
            this.showStatus(`Cannot connect to API: ${error.message}. Make sure the server is running on port 8000.`, 'error');
            console.error('API connection error:', error);
        }
    }
}

// Initialize the application when the page loads
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new KnowledgeBaseApp();
});