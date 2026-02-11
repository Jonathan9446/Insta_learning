"""
AI Models Module
Handles multiple AI providers (Gemini + OpenRouter)
"""

from .ai_orchestrator import AIOrchestrator, ai_orchestrator
from .gemini_handler import GeminiHandler, gemini_handler
from .openrouter_handler import OpenRouterHandler, openrouter_handler
from .model_configs import GEMINI_MODELS, OPENROUTER_MODELS, ALL_MODELS

__all__ = [
    'AIOrchestrator',
    'ai_orchestrator',
    'GeminiHandler',
    'gemini_handler',
    'OpenRouterHandler',
    'openrouter_handler',
    'GEMINI_MODELS',
    'OPENROUTER_MODELS',
    'ALL_MODELS'
]
