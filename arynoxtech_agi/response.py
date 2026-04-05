"""
Arynoxtech_AGI Response Module

Provides the Response class for AGI chat responses.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Response:
    """
    Response from Arynoxtech_AGI chat interaction.
    
    Attributes:
        text: The AGI's response text.
        domain: The domain that was detected/used.
        domain_name: Human-readable domain name.
        confidence: Domain detection confidence (0.0 to 1.0).
        emotional_state: AGI's emotional state dict.
        user_emotion: Detected user emotion.
        interaction_count: Total interactions since startup.
        timestamp: Response timestamp.
        voice_used: Whether voice was used.
        rag_used: Whether RAG was used.
        cached: Whether response was from cache.
        nlp_response: Raw NLP engine response.
        brain_thought: Brain's thought about the input.
    
    Example:
        >>> from arynoxtech_agi import ArynoxtechAGI
        >>> agi = ArynoxtechAGI()
        >>> response = agi.chat("Hello!")
        >>> print(response.text)
        >>> print(response.domain)
        >>> print(response.confidence)
    """
    
    text: str
    domain: str
    domain_name: str
    confidence: float
    emotional_state: Dict[str, float]
    user_emotion: Dict[str, Any]
    interaction_count: int
    timestamp: str
    voice_used: bool
    rag_used: bool
    cached: bool
    nlp_response: str
    brain_thought: str
    
    def __init__(self, raw_data: Dict[str, Any]):
        """
        Initialize Response from orchestrator result.
        
        Args:
            raw_data: Raw response dictionary from orchestrator.interact()
        """
        self.text = raw_data.get('response', '')
        self.domain = raw_data.get('domain', 'general_knowledge')
        self.domain_name = raw_data.get('domain_name', 'General Knowledge')
        self.confidence = raw_data.get('domain_confidence', 0.5)
        self.emotional_state = raw_data.get('emotional_state', {})
        self.user_emotion = raw_data.get('user_emotion', {})
        self.interaction_count = raw_data.get('interaction_count', 0)
        self.timestamp = raw_data.get('timestamp', '')
        self.voice_used = raw_data.get('voice_used', False)
        self.rag_used = raw_data.get('rag_used', False)
        self.cached = raw_data.get('cached', False)
        self.nlp_response = raw_data.get('nlp_response', '')
        self.brain_thought = raw_data.get('brain_thought', '')
    
    def __str__(self) -> str:
        """Return the response text."""
        return self.text
    
    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"Response(domain='{self.domain}', "
            f"confidence={self.confidence:.2f}, "
            f"cached={self.cached}, "
            f"text='{self.text[:50]}...')"
        )
    
    @property
    def dominant_emotion(self) -> str:
        """Get the dominant emotion from emotional state."""
        if not self.emotional_state:
            return "neutral"
        return max(self.emotional_state, key=self.emotional_state.get)
    
    @property
    def emotion_confidence(self) -> float:
        """Get the confidence of the dominant emotion."""
        if not self.emotional_state:
            return 0.0
        return max(self.emotional_state.values())
    
    @property
    def user_dominant_emotion(self) -> str:
        """Get the detected dominant user emotion."""
        if not self.user_emotion:
            return "neutral"
        return self.user_emotion.get('emotion', 'neutral')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            'text': self.text,
            'domain': self.domain,
            'domain_name': self.domain_name,
            'confidence': self.confidence,
            'emotional_state': self.emotional_state,
            'user_emotion': self.user_emotion,
            'interaction_count': self.interaction_count,
            'timestamp': self.timestamp,
            'voice_used': self.voice_used,
            'rag_used': self.rag_used,
            'cached': self.cached,
            'nlp_response': self.nlp_response,
            'brain_thought': self.brain_thought,
            'dominant_emotion': self.dominant_emotion,
            'user_dominant_emotion': self.user_dominant_emotion,
        }