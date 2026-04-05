"""
Tests for Arynoxtech_AGI package.

This module tests the core functionality of Arynoxtech_AGI.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestArynoxtechAGI:
    """Test suite for Arynoxtech_AGI main class."""

    def test_import_main_class(self):
        """Test that we can import the main ArynoxtechAGI class."""
        from arynoxtech_agi import ArynoxtechAGI
        assert ArynoxtechAGI is not None

    def test_arynoxtechagi_has_process_method(self):
        """Test that ArynoxtechAGI has a process method."""
        from arynoxtech_agi import ArynoxtechAGI
        assert hasattr(ArynoxtechAGI, 'process'), "ArynoxtechAGI should have a process method"
        assert callable(getattr(ArynoxtechAGI, 'process')), "process should be callable"

    def test_arynoxtechagi_has_chat_method(self):
        """Test that ArynoxtechAGI has a chat method."""
        from arynoxtech_agi import ArynoxtechAGI
        assert hasattr(ArynoxtechAGI, 'chat'), "ArynoxtechAGI should have a chat method"
        assert callable(getattr(ArynoxtechAGI, 'chat')), "chat should be callable"

    def test_import_config(self):
        """Test that we can import Config and Domain."""
        from arynoxtech_agi import Config, Domain
        assert Config is not None
        assert Domain is not None

    def test_import_response(self):
        """Test that we can import Response class."""
        from arynoxtech_agi import Response
        assert Response is not None

    def test_domain_enum_values(self):
        """Test that Domain enum has expected values."""
        from arynoxtech_agi import Domain
        
        expected_domains = [
            "CUSTOMER_SUPPORT",
            "HEALTH_ADVISOR",
            "EDUCATION_TUTOR",
            "CODE_ASSISTANT",
            "RESEARCH_ASSISTANT",
            "BUSINESS_CONSULTING",
            "CREATIVE_WRITING",
            "GENERAL_KNOWLEDGE",
        ]
        
        for domain_name in expected_domains:
            assert hasattr(Domain, domain_name), f"Missing domain: {domain_name}"

    def test_config_default_values(self):
        """Test Config dataclass default values."""
        from arynoxtech_agi import Config
        
        config = Config()
        assert config.offline_mode == True
        assert config.cache_enabled == True
        assert config.cache_size_mb == 50
        assert config.default_domain == "general_knowledge"

    def test_config_to_dict(self):
        """Test Config to_dict method."""
        from arynoxtech_agi import Config
        
        config = Config(offline_mode=False, cache_enabled=False)
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict["offline_mode"] == False
        assert config_dict["cache_enabled"] == False

    def test_config_from_dict(self):
        """Test Config from_dict class method."""
        from arynoxtech_agi import Config
        
        data = {"offline_mode": False, "cache_enabled": False}
        config = Config.from_dict(data)
        
        assert config.offline_mode == False
        assert config.cache_enabled == False

    def test_response_from_dict(self):
        """Test Response initialization from dictionary."""
        from arynoxtech_agi import Response
        
        raw_data = {
            "response": "Hello, world!",
            "domain": "general_knowledge",
            "domain_name": "General Knowledge",
            "domain_confidence": 0.95,
            "emotional_state": {"joy": 0.8, "neutral": 0.2},
            "user_emotion": {"emotion": "happy", "confidence": 0.9},
            "interaction_count": 42,
            "timestamp": "2024-01-01T12:00:00",
            "voice_used": False,
            "rag_used": True,
            "cached": False,
            "nlp_response": "test response",
            "brain_thought": "test thought",
        }
        
        response = Response(raw_data)
        
        assert response.text == "Hello, world!"
        assert response.domain == "general_knowledge"
        assert response.confidence == 0.95
        assert response.cached == False
        assert response.rag_used == True

    def test_response_dominant_emotion(self):
        """Test Response dominant_emotion property."""
        from arynoxtech_agi import Response
        
        raw_data = {
            "response": "Test",
            "emotional_state": {"joy": 0.8, "sadness": 0.1, "neutral": 0.1},
        }
        
        response = Response(raw_data)
        assert response.dominant_emotion == "joy"

    def test_response_to_dict(self):
        """Test Response to_dict method."""
        from arynoxtech_agi import Response
        
        raw_data = {
            "response": "Test response",
            "domain": "test_domain",
            "domain_name": "Test Domain",
            "domain_confidence": 0.75,
            "emotional_state": {"neutral": 1.0},
            "user_emotion": {"emotion": "neutral"},
            "interaction_count": 1,
            "timestamp": "2024-01-01",
            "voice_used": False,
            "rag_used": False,
            "cached": False,
            "nlp_response": "",
            "brain_thought": "",
        }
        
        response = Response(raw_data)
        result = response.to_dict()
        
        assert isinstance(result, dict)
        assert result["text"] == "Test response"
        assert result["domain"] == "test_domain"
        assert result["confidence"] == 0.75

    def test_response_str(self):
        """Test Response __str__ method."""
        from arynoxtech_agi import Response
        
        raw_data = {"response": "Hello!"}
        response = Response(raw_data)
        
        assert str(response) == "Hello!"

    def test_response_repr(self):
        """Test Response __repr__ method."""
        from arynoxtech_agi import Response
        
        raw_data = {
            "response": "A very long response text...",
            "domain": "test",
            "domain_confidence": 0.85,
            "cached": False,
        }
        
        response = Response(raw_data)
        repr_str = repr(response)
        
        assert "Response" in repr_str
        assert "test" in repr_str
        assert "0.85" in repr_str


class TestPackageMetadata:
    """Test package metadata."""

    def test_version(self):
        """Test package version."""
        from arynoxtech_agi import __version__
        assert __version__ == "2.0.1"

    def test_author(self):
        """Test package author."""
        from arynoxtech_agi import __author__
        assert __author__ == "Aryan Chavan"

    def test_license(self):
        """Test package license."""
        from arynoxtech_agi import __license__
        assert __license__ == "MIT"

    def test_package_info(self):
        """Test package info dictionary."""
        from arynoxtech_agi import __package_info__
        
        assert isinstance(__package_info__, dict)
        assert __package_info__["name"] == "Arynoxtech_AGI"
        assert __package_info__["version"] == "2.0.1"
        assert isinstance(__package_info__["domains"], list)
        assert len(__package_info__["domains"]) > 0


class TestCoreImports:
    """Test that core components can be imported."""

    def test_import_orchestrator(self):
        """Test importing AGIOrchestrator."""
        from core.orchestrator import AGIOrchestrator
        assert AGIOrchestrator is not None

    def test_import_brain(self):
        """Test importing Brain."""
        from core.brain import Brain
        assert Brain is not None

    def test_import_memory(self):
        """Test importing MemoryManager."""
        from core.memory import MemoryManager
        assert MemoryManager is not None

    def test_import_nlp_engine(self):
        """Test importing NLPEngine."""
        from core.nlp_engine import NLPEngine
        assert NLPEngine is not None

    def test_import_domain_adaptor(self):
        """Test importing DomainAdaptor."""
        from core.domain_adaptor import DomainAdaptor
        assert DomainAdaptor is not None

    def test_import_rag_engine(self):
        """Test importing RAGEngine."""
        from core.rag_engine import RAGEngine
        assert RAGEngine is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])