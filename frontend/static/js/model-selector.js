/**
 * Model Selector
 * Handles AI model selection and management
 */

class ModelSelector {
    constructor() {
        this.availableModels = [];
        this.selectedModel = 'gemini-2.0-flash-exp';
        
        this.loadModels();
        this.setupEventListeners();
    }

    setupEventListeners() {
        const modelSelect = document.getElementById('modelSelect');
        if (modelSelect) {
            modelSelect.addEventListener('change', (e) => {
                this.selectedModel = e.target.value;
                console.log('🤖 Model selected:', this.selectedModel);
            });
        }
    }

    /**
     * Load available models from API
     */
    async loadModels() {
        try {
            const response = await Utils.apiRequest('/api/ai/models');
            
            if (response.success && response.models) {
                this.availableModels = response.models;
                this.populateModelSelect();
                console.log('✅ Loaded', response.models.length, 'AI models');
            }
        } catch (error) {
            console.error('❌ Failed to load models:', error);
            Utils.showToast('Failed to load AI models', 'error');
        }
    }

    /**
     * Populate model select dropdown
     */
    populateModelSelect() {
        const modelSelect = document.getElementById('modelSelect');
        if (!modelSelect) return;
        
        // Clear existing options
        modelSelect.innerHTML = '';
        
        // Group models by provider
        const grouped = this.groupModelsByProvider();
        
        // Add Google Gemini models
        if (grouped.google && grouped.google.length > 0) {
            const geminiGroup = document.createElement('optgroup');
            geminiGroup.label = '🔷 Google Gemini (Recommended)';
            
            grouped.google.forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = this.formatModelName(model);
                geminiGroup.appendChild(option);
            });
            
            modelSelect.appendChild(geminiGroup);
        }
        
        // Add OpenRouter models
        if (grouped.openrouter && grouped.openrouter.length > 0) {
            const orGroup = document.createElement('optgroup');
            orGroup.label = '🌐 OpenRouter Models';
            
            grouped.openrouter.forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = this.formatModelName(model);
                orGroup.appendChild(option);
            });
            
            modelSelect.appendChild(orGroup);
        }
        
        // Set default selection
        modelSelect.value = this.selectedModel;
    }

    /**
     * Group models by provider
     */
    groupModelsByProvider() {
        const grouped = {};
        
        this.availableModels.forEach(model => {
            if (!grouped[model.provider]) {
                grouped[model.provider] = [];
            }
            grouped[model.provider].push(model);
        });
        
        return grouped;
    }

    /**
     * Format model name for display
     */
    formatModelName(model) {
        let name = model.name;
        
        // Add emoji indicators
        if (model.id.includes('flash') || model.id.includes('haiku')) {
            name = '⚡ ' + name;
        } else if (model.id.includes('pro') || model.id.includes('70b')) {
            name = '🧠 ' + name;
        }
        
        return name;
    }

    /**
     * Get selected model
     */
    getSelectedModel() {
        return this.selectedModel;
    }

    /**
     * Set selected model
     */
    setSelectedModel(modelId) {
        this.selectedModel = modelId;
        
        const modelSelect = document.getElementById('modelSelect');
        if (modelSelect) {
            modelSelect.value = modelId;
        }
    }

    /**
     * Get model info
     */
    getModelInfo(modelId) {
        return this.availableModels.find(m => m.id === modelId);
    }
}

// Create global instance
window.ModelSelector = new ModelSelector();
