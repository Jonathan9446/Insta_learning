/**
 * AI Chat Interface
 * Handles chat UI and AI interactions
 */

class AIChat {
    constructor() {
        this.sessionId = null;
        this.messages = [];
        this.isTyping = false;
        
        this.setupEventListeners();
    }

    setupEventListeners() {
        const sendBtn = document.getElementById('sendBtn');
        const chatInput = document.getElementById('chatInput');
        const clearChatBtn = document.getElementById('clearChatBtn');
        const exportChatBtn = document.getElementById('exportChatBtn');
        
        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendMessage());
        }
        
        if (chatInput) {
            chatInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }
        
        if (clearChatBtn) {
            clearChatBtn.addEventListener('click', () => this.clearChat());
        }
        
        if (exportChatBtn) {
            exportChatBtn.addEventListener('click', () => this.exportChat());
        }
        
        // Suggestion chips
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('chip')) {
                const prompt = e.target.getAttribute('data-prompt');
                if (prompt) {
                    document.getElementById('chatInput').value = prompt;
                    this.sendMessage();
                }
            }
        });
    }

    /**
     * Set session ID
     */
    setSession(sessionId) {
        this.sessionId = sessionId;
        console.log('📝 Session set:', sessionId);
    }

    /**
     * Send message to AI
     */
    async sendMessage() {
        const chatInput = document.getElementById('chatInput');
        const prompt = chatInput.value.trim();
        
        if (!prompt) return;
        if (!this.sessionId) {
            Utils.showToast('No active session', 'error');
            return;
        }
        
        // Clear input
        chatInput.value = '';
        
        // Add user message
        this.addMessage('user', prompt);
        
        // Show typing indicator
        this.showTyping();
        
        try {
            const response = await Utils.apiRequest('/api/ai/query', 'POST', {
                session_id: this.sessionId,
                prompt: prompt,
                model_id: window.ModelSelector.getSelectedModel(),
                enable_sync: window.SyncManager.isSyncEnabled()
            });
            
            this.hideTyping();
            
            if (response.success) {
                this.addMessage('assistant', response.text, response.model);
                console.log('✅ AI response received');
            } else {
                throw new Error(response.error || 'AI request failed');
            }
            
        } catch (error) {
            this.hideTyping();
            console.error('❌ AI error:', error);
            Utils.showToast('AI request failed: ' + error.message, 'error');
        }
    }

    /**
     * Add message to chat
     */
    addMessage(role, content, model = null) {
        const messagesContainer = document.getElementById('chatMessages');
        if (!messagesContainer) return;
        
        // Remove welcome message if exists
        const welcomeMsg = messagesContainer.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.remove();
        }
        
        const messageElement = document.createElement('div');
        messageElement.className = `message ${role}`;
        
        const avatar = role === 'user' ? '👤' : '🤖';
        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        messageElement.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                <div class="message-bubble">${this.formatContent(content)}</div>
                <div class="message-time">${time}${model ? ' • ' + model : ''}</div>
            </div>
        `;
        
        messagesContainer.appendChild(messageElement);
        
        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // Store message
        this.messages.push({ role, content, time, model });
    }

    /**
     * Format message content
     */
    formatContent(content) {
        // Convert newlines to <br>
        content = content.replace(/\n/g, '<br>');
        
        // Make URLs clickable
        content = content.replace(
            /(https?:\/\/[^\s]+)/g,
            '<a href="$1" target="_blank">$1</a>'
        );
        
        // Timestamps are already in <span class="timestamp"> from backend
        
        return content;
    }

    /**
     * Show typing indicator
     */
    showTyping() {
        const messagesContainer = document.getElementById('chatMessages');
        if (!messagesContainer || this.isTyping) return;
        
        this.isTyping = true;
        
        const typingElement = document.createElement('div');
        typingElement.className = 'message assistant';
        typingElement.id = 'typingIndicator';
        typingElement.innerHTML = `
            <div class="message-avatar">🤖</div>
            <div class="message-content">
                <div class="typing-indicator">
                    <div class="typing-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
        `;
        
        messagesContainer.appendChild(typingElement);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    /**
     * Hide typing indicator
     */
    hideTyping() {
        const typingIndicator = document.getElementById('typingIndicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
        this.isTyping = false;
    }

    /**
     * Clear chat
     */
    async clearChat() {
        if (!confirm('Clear all chat messages?')) return;
        
        try {
            if (this.sessionId) {
                await Utils.apiRequest(`/api/chat/history/${this.sessionId}`, 'DELETE');
            }
            
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
            
            this.messages = [];
            Utils.showToast('Chat cleared', 'success');
            
        } catch (error) {
            console.error('❌ Clear chat error:', error);
            Utils.showToast('Failed to clear chat', 'error');
        }
    }

    /**
     * Export chat
     */
    async exportChat() {
        if (!this.sessionId) {
            Utils.showToast('No active session', 'error');
            return;
        }
        
        try {
            const response = await Utils.apiRequest(`/api/chat/export/${this.sessionId}`);
            
            if (response.success) {
                const content = JSON.stringify(response.export_data, null, 2);
                const filename = `chat_export_${this.sessionId}_${Date.now()}.json`;
                
                Utils.downloadTextFile(content, filename);
                Utils.showToast('Chat exported successfully', 'success');
            }
            
        } catch (error) {
            console.error('❌ Export error:', error);
            Utils.showToast('Failed to export chat', 'error');
        }
    }
}

// Create global instance
window.AIChat = new AIChat();
