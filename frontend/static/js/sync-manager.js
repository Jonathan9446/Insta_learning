/**
 * Sync Manager
 * Manages synchronization between video playback and AI responses
 */

class SyncManager {
    constructor() {
        this.syncEnabled = true;
        this.currentTime = 0;
        this.activeSegments = new Set();
        this.transcriptSegments = [];
        
        this.setupEventListeners();
    }

    setupEventListeners() {
        const syncToggle = document.getElementById('syncToggle');
        if (syncToggle) {
            syncToggle.addEventListener('change', (e) => {
                this.syncEnabled = e.target.checked;
                console.log('🔄 Sync:', this.syncEnabled ? 'Enabled' : 'Disabled');
                
                if (this.syncEnabled) {
                    this.updateHighlights();
                } else {
                    this.clearHighlights();
                }
            });
        }
    }

    /**
     * Set transcript data
     */
    setTranscript(transcriptData) {
        if (transcriptData && transcriptData.segments) {
            this.transcriptSegments = transcriptData.segments;
            console.log('📝 Transcript loaded:', this.transcriptSegments.length, 'segments');
        }
    }

    /**
     * Video time update handler
     */
    onVideoTimeUpdate(currentTime) {
        this.currentTime = currentTime;
        
        if (this.syncEnabled) {
            this.updateHighlights();
        }
    }

    /**
     * Update highlighted segments
     */
    updateHighlights() {
        if (!this.syncEnabled) return;
        
        // Find active timestamps in current view
        const timestamps = document.querySelectorAll('.timestamp');
        
        timestamps.forEach(timestamp => {
            const time = parseFloat(timestamp.getAttribute('data-time'));
            
            // Highlight if within 3 seconds of current time
            if (Math.abs(time - this.currentTime) <= 3) {
                timestamp.classList.add('active');
                
                // Auto-scroll to active timestamp
                this.scrollToElement(timestamp);
            } else {
                timestamp.classList.remove('active');
            }
        });
    }

    /**
     * Clear all highlights
     */
    clearHighlights() {
        const timestamps = document.querySelectorAll('.timestamp.active');
        timestamps.forEach(ts => ts.classList.remove('active'));
    }

    /**
     * Scroll to element
     */
    scrollToElement(element) {
        const chatContainer = document.getElementById('chatMessages');
        if (!chatContainer) return;
        
        const containerRect = chatContainer.getBoundingClientRect();
        const elementRect = element.getBoundingClientRect();
        
        // Check if element is out of view
        if (elementRect.top < containerRect.top || elementRect.bottom > containerRect.bottom) {
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    /**
     * Find segment at time
     */
    findSegmentAtTime(time) {
        return this.transcriptSegments.find(segment => 
            segment.start <= time && segment.end >= time
        );
    }

    /**
     * Get context window (segments around current time)
     */
    getContextWindow(windowSeconds = 30) {
        const startTime = this.currentTime - windowSeconds;
        const endTime = this.currentTime + windowSeconds;
        
        return this.transcriptSegments.filter(segment =>
            (segment.start >= startTime && segment.start <= endTime) ||
            (segment.end >= startTime && segment.end <= endTime)
        );
    }

    /**
     * Enable/disable sync
     */
    setSync(enabled) {
        this.syncEnabled = enabled;
        
        const toggle = document.getElementById('syncToggle');
        if (toggle) {
            toggle.checked = enabled;
        }
        
        if (enabled) {
            this.updateHighlights();
        } else {
            this.clearHighlights();
        }
    }

    /**
     * Is sync enabled
     */
    isSyncEnabled() {
        return this.syncEnabled;
    }
}

// Create global instance
window.SyncManager = new SyncManager();
