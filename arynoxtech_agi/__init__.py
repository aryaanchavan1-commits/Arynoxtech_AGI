"""
Arynoxtech_AGI - Multi-Domain Adaptive Artificial General Intelligence

A pip-installable Python library for AGI capabilities.
Works across 8+ industries: Customer Support, Healthcare, Education, 
Code Assistance, Research, Business, Creative Writing, and General Knowledge.

Quick Start:
    >>> from arynoxtech_agi import ArynoxtechAGI
    >>> agi = ArynoxtechAGI()
    >>> response = agi.chat("Hello!")
    >>> print(response.text)

Installation:
    pip install Arynoxtech_AGI
"""

__version__ = "2.0.1"
__author__ = "Aryan Chavan"
__license__ = "MIT"

# Main public API
from arynoxtech_agi.client import ArynoxtechAGI
from arynoxtech_agi.config import Config, Domain
from arynoxtech_agi.response import Response

# Core components (advanced usage)
from core.orchestrator import AGIOrchestrator
from core.brain import Brain
from core.memory import MemoryManager
from core.nlp_engine import NLPEngine
from core.emotional_intelligence import EmotionalIntelligence
from core.domain_adaptor import DomainAdaptor
from core.rag_engine import RAGEngine
from core.self_evolution import SelfEvolutionEngine
from core.voice import VoiceEngine
from core.cache_manager import CacheManager

__all__ = [
    # Public API (users should use these)
    "ArynoxtechAGI",
    "Config",
    "Domain",
    "Response",
    
    # Core components (advanced)
    "AGIOrchestrator",
    "Brain",
    "MemoryManager",
    "NLPEngine",
    "EmotionalIntelligence",
    "DomainAdaptor",
    "RAGEngine",
    "SelfEvolutionEngine",
    "VoiceEngine",
    "CacheManager",
]

# Package metadata
__package_info__ = {
    "name": "Arynoxtech_AGI",
    "version": __version__,
    "description": "Multi-Domain Adaptive Artificial General Intelligence",
    "author": __author__,
    "license": __license__,
    "url": "https://github.com/aryaanchavan1-commits/Arynoxtech_AGI",
    "domains": [
        "Customer Support",
        "Healthcare Advisor", 
        "Education Tutor",
        "Code Assistant",
        "Research Assistant",
        "Business Consulting",
        "Creative Writing",
        "General Knowledge",
    ],
}