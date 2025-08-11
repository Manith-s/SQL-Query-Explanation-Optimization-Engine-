"""
LLM adapter interface and factory.

Provides abstract interface for LLM providers and factory to instantiate them.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from app.providers.provider_dummy import DummyLLMProvider
from app.providers.provider_ollama import OllamaLLMProvider


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate text response from prompt.
        
        Args:
            prompt: The input prompt to send to the LLM
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Generated text response
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the LLM provider is available.
        
        Returns:
            True if provider can be used, False otherwise
        """
        pass


def get_llm(provider_name: Optional[str] = None) -> LLMProvider:
    """
    Factory function to get LLM provider instance.
    
    Args:
        provider_name: Name of the provider to use. If None, uses default.
        
    Returns:
        LLM provider instance
    """
    if provider_name is None:
        provider_name = "dummy"
    
    providers = {
        "dummy": DummyLLMProvider,
        "ollama": OllamaLLMProvider,
    }
    
    provider_class = providers.get(provider_name.lower())
    if provider_class is None:
        raise ValueError(f"Unknown LLM provider: {provider_name}")
    
    return provider_class()
