#!/usr/bin/env python3
"""
Simple test script to debug Ollama connection.
"""

import sys
import os
sys.path.insert(0, 'src')

from app.core.config import settings
from app.providers.provider_ollama import OllamaLLMProvider

def test_ollama():
    print("Testing Ollama connection...")
    print(f"OLLAMA_HOST: {settings.OLLAMA_HOST}")
    print(f"LLM_MODEL: {settings.LLM_MODEL}")
    print(f"LLM_TIMEOUT_S: {settings.LLM_TIMEOUT_S}")
    
    # Test availability
    print(f"Ollama available: {OllamaLLMProvider.is_available()}")
    
    # Test simple completion
    try:
        provider = OllamaLLMProvider()
        result = provider.complete("What is SQL?")
        print(f"Success! Result: {result[:100]}...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_ollama()
