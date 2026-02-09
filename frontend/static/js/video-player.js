/**
 * Video Player Manager
 * Handles video playback and embedding
 */

class VideoPlayer {
    constructor() {
        this.currentVideo = null;
        this.platform = null;
        this.player = null;
        this.currentTime = 0;
        this.duration = 0;
        this.isPlaying = false;
        
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Video player iframe message listener
        window.addEventListener('message', (event) => {
            this.handlePlayerMessage(event);
        });
    }

    /**
     * Load video in player
     */
    loadVideo(videoInfo, platform) {
        this.platform = platform;
        this.currentVideo = videoInfo;
        
        const playerElement = document.getElementById('videoPlayer');
        
        if (platform === 'youtube') {
            this.loadYouTubeVideo(videoInfo.id, playerElement);
        } else if (platform === 'facebook') {
            this.loadFacebookVideo(videoInfo.url, playerElement);
        }
        
        this.updateVideoInfo(videoInfo);
    }

    /**
     * Load YouTube video
     */
    loadYouTubeVideo(videoId, playerElement) {
        const embedUrl = `https://www.youtube.com/embed/${videoId}?enablejsapi=1&origin=${window.location.origin}`;
        playerElement.src = embedUrl;
        
        console.log('✅ YouTube video loaded:', videoId);
    }

    /**
     * Load Facebook video
     */
    loadFacebookVideo(videoUrl, playerElement) {
        const encodedUrl = encodeURIComponent(videoUrl);
        const embedUrl = `https://www.facebook.com/plugins/video.php?href=${encodedUrl}&show_text=false&appId`;
        playerElement.src = embedUrl;
        
        console.log('✅ Facebook video loaded');
    }

    /**
     * Update video info display
     */
    updateVideoInfo(videoInfo) {
        const titleElement = document.getElementById('videoTitle');
        const metaElement = document.getElementById('videoMeta');
        
        titleElement.textContent = videoInfo.title || 'Video';
        
        let metaText = '';
        if (videoInfo.uploader) {
            metaText += videoInfo.uploader;
        }
        if (videoInfo.views) {
            metaText += ` • ${this.formatViews(videoInfo.views)} views`;
        }
        if (videoInfo.duration) {
            metaText += ` • ${Utils.formatTimestamp(videoInfo.duration)}`;
        }
        
        metaElement.textContent = metaText;
    }

    /**
     * Format view count
     */
    formatViews(views) {
        if (views >= 1000000) {
            return (views / 1000000).toFixed(1) + 'M';
        } else if (views >= 1000) {
            return (views / 1000).toFixed(1) + 'K';
        }
        return views.toString();
    }

    /**
     * Jump to timestamp
     */
    jumpToTime(seconds) {
        console.log('⏩ Jumping to:', seconds);
        
        if (this.platform === 'youtube') {
            this.jumpYouTube(seconds);
        } else if (this.platform === 'facebook') {
            this.jumpFacebook(seconds);
        }
        
        // Notify sync manager
        if (window.SyncManager) {
            window.SyncManager.onVideoTimeUpdate(seconds);
        }
    }

    /**
     * Jump to time in YouTube
     */
    jumpYouTube(seconds) {
        const playerElement = document.getElementById('videoPlayer');
        
        if (playerElement && playerElement.contentWindow) {
            playerElement.contentWindow.postMessage(JSON.stringify({
                event: 'command',
                func: 'seekTo',
                args: [seconds, true]
            }), '*');
        }
    }

    /**
     * Jump to time in Facebook (limited support)
     */
    jumpFacebook(seconds) {
        // Facebook embedded player has limited JS API
        console.log('Facebook player: seeking to', seconds);
        Utils.showToast('Facebook video seeking has limited support', 'warning');
    }

    /**
     * Handle player messages
     */
    handlePlayerMessage(event) {
        // Handle YouTube player messages
        try {
            const data = JSON.parse(event.data);
            
            if (data.event === 'onStateChange') {
                this.handleStateChange(data.info);
            } else if (data.event === 'infoDelivery') {
                this.handleInfoDelivery(data.info);
            }
        } catch (error) {
            // Not a JSON message, ignore
        }
    }

    /**
     * Handle player state change
     */
    handleStateChange(state) {
        // YouTube player states:
        // -1: unstarted, 0: ended, 1: playing, 2: paused, 3: buffering, 5: cued
        this.isPlaying = (state === 1);
        
        console.log('Player state:', state, this.isPlaying ? 'Playing' : 'Paused');
    }

    /**
     * Handle info delivery from player
     */
    handleInfoDelivery(info) {
        if (info.currentTime !== undefined) {
            this.currentTime = info.currentTime;
            
            // Notify sync manager
            if (window.SyncManager) {
                window.SyncManager.onVideoTimeUpdate(this.currentTime);
            }
        }
        
        if (info.duration !== undefined) {
            this.duration = info.duration;
        }
    }

    /**
     * Get current playback time
     */
    getCurrentTime() {
        return this.currentTime;
    }

    /**
     * Check if video is playing
     */
    isVideoPlaying() {
        return this.isPlaying;
    }
}

// Create global instance
window.VideoPlayer = new VideoPlayer();

// Make jumpToTime globally accessible
window.jumpToTime = (seconds) => {
    window.VideoPlayer.jumpToTime(seconds);
};
