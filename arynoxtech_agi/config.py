"""
Arynoxtech_AGI Configuration Module

Provides configuration classes for the Arynoxtech_AGI library.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any


class Domain(Enum):
    """
    Available domains in Arynoxtech_AGI.
    
    Use these to specify which domain the AGI should operate in.
    
    Example:
        >>> from arynoxtech_agi import ArynoxtechAGI, Domain
        >>> agi = ArynoxtechAGI()
        >>> response = agi.chat("Help me debug", domain=Domain.CODE_ASSISTANT)
    """
    CUSTOMER_SUPPORT = "customer_support"
    HEALTH_ADVISOR = "health_advisor"
    EDUCATION_TUTOR = "education_tutor"
    CODE_ASSISTANT = "code_assistant"
    RESEARCH_ASSISTANT = "research_assistant"
    BUSINESS_CONSULTING = "business_consulting"
    CREATIVE_WRITING = "creative_writing"
    GENERAL_KNOWLEDGE = "general_knowledge"


@dataclass
class Config:
    """
    Configuration for Arynoxtech_AGI.
    
    Attributes:
        offline_mode: If True, operates without internet connection.
        cache_enabled: If True, caches responses for faster replies.
        cache_size_mb: Maximum cache size in megabytes.
        max_concurrent_requests: Maximum simultaneous API requests.
        request_timeout: Timeout for requests in seconds.
        enabled_domains: List of domains to enable. None enables all.
        voice_enabled: If True, enables voice features (requires voice extras).
        evolution_enabled: If True, enables self-evolution features.
        learning_rate: Learning rate for self-improvement.
        memory_capacity: Maximum number of memories to store.
    
    Example:
        >>> from arynoxtech_agi import ArynoxtechAGI, Config
        >>> config = Config(
        ...     offline_mode=True,
        ...     cache_enabled=True,
        ...     enabled_domains=["code_assistant", "customer_support"]
        ... )
        >>> agi = ArynoxtechAGI(config=config)
    """
    
    # Core settings
    offline_mode: bool = True
    cache_enabled: bool = True
    cache_size_mb: int = 50
    
    # Performance settings
    max_concurrent_requests: int = 100
    request_timeout: int = 30
    
    # Domain settings
    enabled_domains: Optional[List[str]] = None
    default_domain: str = "general_knowledge"
    
    # Feature flags
    voice_enabled: bool = False
    evolution_enabled: bool = True
    web_learning_enabled: bool = False
    
    # Brain settings
    learning_rate: float = 0.001
    memory_capacity: int = 1000000
    consciousness_level: float = 0.85
    
    # Model settings
    conversation_model: str = "microsoft/DialoGPT-medium"
    emotion_model: str = "j-hartmann/emotion-english-distilroberta-base"
    
    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    
    # Storage settings
    data_folder: str = "data"
    memory_folder: str = "memory"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "offline_mode": self.offline_mode,
            "cache_enabled": self.cache_enabled,
            "cache_size_mb": self.cache_size_mb,
            "max_concurrent_requests": self.max_concurrent_requests,
            "request_timeout": self.request_timeout,
            "enabled_domains": self.enabled_domains,
            "default_domain": self.default_domain,
            "voice_enabled": self.voice_enabled,
            "evolution_enabled": self.evolution_enabled,
            "web_learning_enabled": self.web_learning_enabled,
            "learning_rate": self.learning_rate,
            "memory_capacity": self.memory_capacity,
            "consciousness_level": self.consciousness_level,
            "conversation_model": self.conversation_model,
            "emotion_model": self.emotion_model,
            "api_host": self.api_host,
            "api_port": self.api_port,
            "api_workers": self.api_workers,
            "data_folder": self.data_folder,
            "memory_folder": self.memory_folder,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create config from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class VoiceConfig:
    """
    Voice feature configuration.
    
    Attributes:
        enabled: If True, voice features are active.
        speech_recognition_engine: Engine for speech recognition.
        tts_engine: Engine for text-to-speech.
        language: Language code (e.g., "en-US").
        speech_rate: Words per minute for TTS.
        volume: Volume level (0.0 to 1.0).
    """
    enabled: bool = False
    speech_recognition_engine: str = "google"
    tts_engine: str = "pyttsx3"
    language: str = "en-US"
    speech_rate: int = 150
    volume: float = 0.9