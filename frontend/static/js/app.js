/**
 * Main Application
 * Orchestrates all frontend modules and initializes the app
 */

class App {
    constructor() {
        this.currentSession = null;
        this.currentVideoData = null;
        this.transcriptData = null;
        
        this.init();
    }

    /**
     * Initialize application
     */
    init() {
        console.log('🚀 Initializing AI Video Learning Platform...');
        
        this.setupEventListeners();
        this.checkUrlParams();
        
        console.log('✅ App initialized');
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Process video button
        const processBtn = document.getElementById('processVideoBtn');
        if (processBtn) {
            processBtn.addEventListener('click', () => this.processVideo());
        }

        // Video URL input (Enter key)
        const videoInput = document.getElementById('videoUrlInput');
        if (videoInput) {
            videoInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    this.processVideo();
                }
            });
        }

        // New video button
        const newVideoBtn = document.getElementById('newVideoBtn');
        if (newVideoBtn) {
            newVideoBtn.addEventListener('click', () => this.resetApp());
        }

        // Example links
        const exampleLinks = document.querySelectorAll('.example-link');
        exampleLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                const url = e.target.getAttribute('data-url');
                if (url) {
                    document.getElementById('videoUrlInput').value = url;
                    this.processVideo();
                }
            });
        });

        // Settings button (placeholder)
        const settingsBtn = document.getElementById('settingsBtn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => {
                Utils.showToast('Settings feature coming soon!', 'info');
            });
        }
    }

    /**
     * Check URL parameters for direct video loading
     */
    checkUrlParams() {
        const urlParams = new URLSearchParams(window.location.search);
        const videoUrl = urlParams.get('v');
        
        if (videoUrl) {
            document.getElementById('videoUrlInput').value = decodeURIComponent(videoUrl);
            this.processVideo();
        }
    }

    /**
     * Process video from URL
     */
    async processVideo() {
        const videoInput = document.getElementById('videoUrlInput');
        const platformSelect = document.getElementById('platformSelect');
        
        const videoUrl = videoInput.value.trim();
        const platform = platformSelect.value;

        // Validate URL
        if (!videoUrl) {
            Utils.showToast('Please enter a video URL', 'warning');
            videoInput.focus();
            return;
        }

        if (!Utils.validateUrl(videoUrl)) {
            Utils.showToast('Please enter a valid URL', 'error');
            videoInput.focus();
            return;
        }

        // Show loading
        Utils.showLoading(true, 'Processing video...');

        try {
            console.log('🎬 Processing video:', videoUrl);

            // Call API to process video
            const response = await Utils.apiRequest('/api/video/process', 'POST', {
                video_url: videoUrl,
                platform: platform
            });

            Utils.showLoading(false);

            if (response.success) {
                this.onVideoProcessed(response);
            } else {
                throw new Error(response.error || 'Failed to process video');
            }

        } catch (error) {
            Utils.showLoading(false);
            console.error('❌ Video processing error:', error);
            Utils.showToast('Error: ' + error.message, 'error');
        }
    }

    /**
     * Handle successful video processing
     */
    async onVideoProcessed(response) {
        console.log('✅ Video processed:', response);

        this.currentSession = response.session_id;
        this.currentVideoData = response.video_info;

        // Hide input section, show player section
        document.getElementById('videoInputSection').classList.add('hidden');
        document.getElementById('videoPlayerSection').classList.remove('hidden');

        // Load video in player
        if (window.VideoPlayer) {
            window.VideoPlayer.loadVideo(
                response.video_info,
                response.platform
            );
        }

        // Set session in AI chat
        if (window.AIChat) {
            window.AIChat.setSession(response.session_id);
        }

        // Load transcript if available
        if (response.transcript_available) {
            await this.loadTranscript(response.session_id);
        } else {
            Utils.showToast('Transcript not available for this video', 'warning');
        }

        // Show success message
        const cacheMsg = response.cached ? ' (from cache)' : '';
        Utils.showToast('Video loaded successfully' + cacheMsg, 'success');
    }

    /**
     * Load transcript data
     */
    async loadTranscript(sessionId) {
        try {
            console.log('📝 Loading transcript...');

            const response = await Utils.apiRequest(`/api/video/transcript/${sessionId}`);

            if (response.success && response.transcript) {
                this.transcriptData = response.transcript;

                // Set transcript in sync manager
                if (window.SyncManager) {
                    window.SyncManager.setTranscript(response.transcript);
                }

                console.log('✅ Transcript loaded:', response.metadata);
            } else {
                console.warn('⚠️ Transcript not available');
            }

        } catch (error) {
            console.error('❌ Transcript loading error:', error);
        }
    }

    /**
     * Reset app to initial state
     */
    resetApp() {
        if (!confirm('Start over with a new video?')) return;

        // Clear session
        this.currentSession = null;
        this.currentVideoData = null;
        this.transcriptData = null;

        // Clear input
        document.getElementById('videoUrlInput').value = '';
        document.getElementById('platformSelect').value = 'auto';

        // Show input section, hide player
        document.getElementById('videoInputSection').classList.remove('hidden');
        document.getElementById('videoPlayerSection').classList.add('hidden');

        // Clear chat
        if (window.AIChat) {
            window.AIChat.messages = [];
            const messagesContainer = document.getElementById('chatMessages');
            if (messagesContainer) {
                messagesContainer.innerHTML = `
                    <div class="welcome-message">
                        <i class="fas fa-magic"></i>
                        <h4>AI Assistant Ready!</h4>
                        <p>Ask me anything about this video:</p>
                        <div class="suggestion-chips">
                            <button class="chip" data-prompt="Summarize this video">📝 Summarize</button>
                            <button class="chip" data-prompt="Break down difficult words with pronunciation and meaning">📚 Word Analysis</button>
                            <button class="chip" data-prompt="Explain the main concepts">💡 Explain</button>
                        </div>
                    </div>
                `;
            }
        }

        console.log('🔄 App reset');
        Utils.showToast('Ready for new video', 'success');
    }

    /**
     * Get current session
     */
    getCurrentSession() {
        return this.currentSession;
    }

    /**
     * Get current video data
     */
    getCurrentVideoData() {
        return this.currentVideoData;
    }

    /**
     * Get transcript data
     */
    getTranscriptData() {
        return this.transcriptData;
    }

    /**
     * Export current session
     */
    async exportSession() {
        if (!this.currentSession) {
            Utils.showToast('No active session to export', 'warning');
            return;
        }

        try {
            const response = await Utils.apiRequest(`/api/video/export/${this.currentSession}`);

            if (response.success) {
                const content = JSON.stringify(response.export_data, null, 2);
                const filename = `session_export_${this.currentSession}_${Date.now()}.json`;

                Utils.downloadTextFile(content, filename);
                Utils.showToast('Session exported successfully', 'success');
            }

        } catch (error) {
            console.error('❌ Export error:', error);
            Utils.showToast('Failed to export session', 'error');
        }
    }

    /**
     * Share video (copy URL)
     */
    async shareVideo() {
        if (!this.currentVideoData) {
            Utils.showToast('No video loaded', 'warning');
            return;
        }

        const shareUrl = `${window.location.origin}?v=${encodeURIComponent(this.currentVideoData.url || '')}`;
        
        try {
            await navigator.clipboard.writeText(shareUrl);
            Utils.showToast('Share link copied to clipboard!', 'success');
        } catch (error) {
            console.error('❌ Share error:', error);
            Utils.showToast('Failed to copy link', 'error');
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.App = new App();
});

// Make app globally available
window.App = window.App || {};
          
