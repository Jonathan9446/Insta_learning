"""
AI Model Configurations
Defines all available AI models
"""

# ============================================
# GOOGLE GEMINI MODELS
# ============================================
GEMINI_MODELS = {
    'gemini-2.0-flash-exp': {
        'id': 'gemini-2.0-flash-exp',
        'name': 'Gemini 2.0 Flash (Experimental)',
        'provider': 'google',
        'description': 'Latest experimental model, very fast',
        'context_window': 1000000,
        'max_tokens': 8192,
        'free': True,
        'recommended_for': ['general', 'summary', 'word_analysis']
    },
    'gemini-1.5-pro': {
        'id': 'gemini-1.5-pro',
        'name': 'Gemini 1.5 Pro',
        'provider': 'google',
        'description': 'Most capable model, huge context',
        'context_window': 2000000,
        'max_tokens': 8192,
        'free': True,
        'recommended_for': ['complex', 'detailed', 'long_videos']
    },
    'gemini-1.5-flash': {
        'id': 'gemini-1.5-flash',
        'name': 'Gemini 1.5 Flash',
        'provider': 'google',
        'description': 'Fast and efficient',
        'context_window': 1000000,
        'max_tokens': 8192,
        'free': True,
        'recommended_for': ['quick', 'simple']
    },
    'gemini-pro': {
        'id': 'gemini-pro',
        'name': 'Gemini Pro',
        'provider': 'google',
        'description': 'Original Gemini Pro',
        'context_window': 32000,
        'max_tokens': 8192,
        'free': True,
        'recommended_for': ['general']
    }
}

# ============================================
# OPENROUTER MODELS (FREE TIER)
# ============================================
OPENROUTER_MODELS = {
    'openai/gpt-3.5-turbo': {
        'id': 'openai/gpt-3.5-turbo',
        'name': 'ChatGPT 3.5 Turbo',
        'provider': 'openrouter',
        'description': 'Fast and reliable OpenAI model',
        'context_window': 16385,
        'max_tokens': 4096,
        'free': True,
        'recommended_for': ['general', 'conversation']
    },
    'anthropic/claude-3-haiku': {
        'id': 'anthropic/claude-3-haiku',
        'name': 'Claude 3 Haiku',
        'provider': 'openrouter',
        'description': 'Fast Anthropic model',
        'context_window': 200000,
        'max_tokens': 4096,
        'free': True,
        'recommended_for': ['quick', 'simple']
    },
    'google/gemini-pro-1.5': {
        'id': 'google/gemini-pro-1.5',
        'name': 'Gemini Pro 1.5 (OpenRouter)',
        'provider': 'openrouter',
        'description': 'Google Gemini via OpenRouter',
        'context_window': 2000000,
        'max_tokens': 8192,
        'free': True,
        'recommended_for': ['long_videos', 'detailed']
    },
    'meta-llama/llama-3.1-8b-instruct:free': {
        'id': 'meta-llama/llama-3.1-8b-instruct:free',
        'name': 'Llama 3.1 8B',
        'provider': 'openrouter',
        'description': 'Meta\'s open model - compact',
        'context_window': 128000,
        'max_tokens': 4096,
        'free': True,
        'recommended_for': ['quick', 'simple']
    },
    'meta-llama/llama-3.1-70b-instruct:free': {
        'id': 'meta-llama/llama-3.1-70b-instruct:free',
        'name': 'Llama 3.1 70B',
        'provider': 'openrouter',
        'description': 'Meta\'s large model - very capable',
        'context_window': 128000,
        'max_tokens': 8192,
        'free': True,
        'recommended_for': ['complex', 'detailed']
    },
    'mistralai/mistral-7b-instruct:free': {
        'id': 'mistralai/mistral-7b-instruct:free',
        'name': 'Mistral 7B',
        'provider': 'openrouter',
        'description': 'Efficient European model',
        'context_window': 32768,
        'max_tokens': 4096,
        'free': True,
        'recommended_for': ['general']
    },
    'google/gemma-2-9b-it:free': {
        'id': 'google/gemma-2-9b-it:free',
        'name': 'Gemma 2 9B',
        'provider': 'openrouter',
        'description': 'Google\'s lightweight model',
        'context_window': 8192,
        'max_tokens': 4096,
        'free': True,
        'recommended_for': ['simple']
    },
    'qwen/qwen-2-7b-instruct:free': {
        'id': 'qwen/qwen-2-7b-instruct:free',
        'name': 'Qwen 2 7B',
        'provider': 'openrouter',
        'description': 'Multilingual model',
        'context_window': 32768,
        'max_tokens': 4096,
        'free': True,
        'recommended_for': ['translation', 'multilingual']
    },
    'microsoft/phi-3-mini-128k-instruct:free': {
        'id': 'microsoft/phi-3-mini-128k-instruct:free',
        'name': 'Phi-3 Mini',
        'provider': 'openrouter',
        'description': 'Microsoft\'s compact model',
        'context_window': 128000,
        'max_tokens': 4096,
        'free': True,
        'recommended_for': ['quick']
    },
    'openchat/openchat-7b:free': {
        'id': 'openchat/openchat-7b:free',
        'name': 'OpenChat 7B',
        'provider': 'openrouter',
        'description': 'Community chat model',
        'context_window': 8192,
        'max_tokens': 4096,
        'free': True,
        'recommended_for': ['conversation']
    }
}

# ============================================
# COMBINED MODEL LIST
# ============================================
ALL_MODELS = {**GEMINI_MODELS, **OPENROUTER_MODELS}


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_model_by_id(model_id: str):
    """Get model config by ID"""
    return ALL_MODELS.get(model_id)


def get_models_by_provider(provider: str):
    """Get all models for a provider"""
    return {
        k: v for k, v in ALL_MODELS.items()
        if v['provider'] == provider
    }


def get_recommended_models(query_type: str):
    """Get recommended models for query type"""
    recommended = []
    
    for model_id, config in ALL_MODELS.items():
        if query_type in config.get('recommended_for', []):
            recommended.append(model_id)
    
    return recommended


def get_default_model():
    """Get default model"""
    return 'gemini-2.0-flash-exp'
