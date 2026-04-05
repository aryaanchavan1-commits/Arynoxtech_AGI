"""
Arynoxtech_AGI Client - Main user-facing API for the library

This module provides the simple ArynoxtechAGI class that users interact with.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from arynoxtech_agi.config import Config, Domain
from arynoxtech_agi.response import Response

logger = logging.getLogger(__name__)


class ArynoxtechAGI:
    """
    Main Arynoxtech_AGI client for multi-domain AGI capabilities.

    This is the primary class users interact with when using Arynoxtech_AGI as a library.

    Example:
        >>> from arynoxtech_agi import ArynoxtechAGI
        >>> agi = ArynoxtechAGI()
        >>> response = agi.chat("Hello!")
        >>> print(response.text)
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        offline_mode: bool = True,
        cache_enabled: bool = True,
    ):
        """
        Initialize Arynoxtech_AGI.

        Args:
            config: Configuration object. If None, uses default config.
            offline_mode: If True, operates without internet (default: True).
            cache_enabled: If True, enables response caching (default: True).
        """
        self.config = config or Config(
            offline_mode=offline_mode,
            cache_enabled=cache_enabled
        )
        self._orchestrator = None
        self._initialized = False

        # Import here to avoid circular imports
        from core.orchestrator import AGIOrchestrator
        self._OrchestratorClass = AGIOrchestrator

        logger.info(f"Arynoxtech_AGI v2.0.0 initialized (offline_mode={offline_mode})")

    def _ensure_initialized(self):
        """Lazily initialize the orchestrator on first use."""
        if not self._initialized:
            # Try to find config file in multiple locations
            config_paths = [
                "config/agi_config.json",
                Path(__file__).parent.parent / "config" / "agi_config.json",
                Path.home() / ".arynoxtech_agi" / "config.json",
            ]
            
            config_path = None
            for path in config_paths:
                if Path(path).exists():
                    config_path = str(path)
                    break
            
            # If no config found, use defaults (orchestrator will handle this)
            if config_path is None:
                logger.info("No config file found, using defaults")
                config_path = "config/agi_config.json"  # Will trigger default config in orchestrator
            
            self._orchestrator = self._OrchestratorClass(
                config_path=config_path
            )
            # Override config settings
            if self.config.offline_mode:
                self._orchestrator.state.offline_mode = True
            
            # Start the orchestrator automatically
            loop = self._get_or_create_event_loop()
            loop.run_until_complete(self._orchestrator.start())
            
            self._initialized = True

    def process(
        self,
        message: str,
        domain: Optional[Union[str, Domain]] = None,
        user_id: Optional[str] = None,
        use_voice: bool = False,
    ) -> Response:
        """
        Process a query through the AGI system. Alias for chat().

        This is the main method for interacting with the AGI.

        Args:
            message: The user's message or question.
            domain: Optional domain to force (e.g., "code_assistant", Domain.CODE_ASSISTANT).
                    If None, auto-detects domain.
            user_id: Optional user identifier for personalization.
            use_voice: If True, speaks the response (requires voice extras).

        Returns:
            Response object containing:
                - text: The AGI's response text
                - domain: Detected/forced domain name
                - confidence: Domain detection confidence (0-1)
                - emotional_state: AGI's emotional state
                - user_emotion: Detected user emotion
                - cached: Whether response was cached
                - metadata: Additional information

        Example:
            >>> agi = ArynoxtechAGI()
            >>> response = agi.process("Explain quantum computing")
            >>> print(response.text)
        """
        return self.chat(message, domain, user_id, use_voice)

    def chat(
        self,
        message: str,
        domain: Optional[Union[str, Domain]] = None,
        user_id: Optional[str] = None,
        use_voice: bool = False,
    ) -> Response:
        """
        Chat with the AGI. This is the main method users will use.

        Args:
            message: The user's message or question.
            domain: Optional domain to force (e.g., "code_assistant", Domain.CODE_ASSISTANT).
                    If None, auto-detects domain.
            user_id: Optional user identifier for personalization.
            use_voice: If True, speaks the response (requires voice extras).

        Returns:
            Response object containing:
                - text: The AGI's response text
                - domain: Detected/forced domain name
                - confidence: Domain detection confidence (0-1)
                - emotional_state: AGI's emotional state
                - user_emotion: Detected user emotion
                - cached: Whether response was cached
                - metadata: Additional information

        Example:
            >>> agi = ArynoxtechAGI()
            >>> response = agi.chat("I need help with my Python code")
            >>> print(response.text)
            >>> print(response.domain)  # 'code_assistant'
            >>> print(response.confidence)  # 0.85
        """
        self._ensure_initialized()

        # Convert domain enum to string if needed
        if isinstance(domain, Domain):
            domain = domain.value

        # Run async interact in sync context
        loop = self._get_or_create_event_loop()
        result = loop.run_until_complete(
            self._orchestrator.interact(
                user_input=message,
                user_id=user_id,
                use_voice=use_voice
            )
        )

        return Response(result)

    async def chat_async(
        self,
        message: str,
        domain: Optional[Union[str, Domain]] = None,
        user_id: Optional[str] = None,
        use_voice: bool = False,
    ) -> Response:
        """
        Async version of chat() for use in async applications.

        Args:
            message: The user's message or question.
            domain: Optional domain to force.
            user_id: Optional user identifier.
            use_voice: If True, speaks the response.

        Returns:
            Response object.
        """
        self._ensure_initialized()

        if isinstance(domain, Domain):
            domain = domain.value

        result = await self._orchestrator.interact(
            user_input=message,
            user_id=user_id,
            use_voice=use_voice
        )

        return Response(result)

    def load_file(self, file_path: str) -> Dict[str, Any]:
        """
        Load and learn from a file (PDF, CSV, TXT, JSON).

        Args:
            file_path: Path to the file to load.

        Returns:
            Dict with success status and file metadata.

        Example:
            >>> agi = ArynoxtechAGI()
            >>> result = agi.load_file("document.pdf")
            >>> print(result['success'])  # True
            >>> print(result['chunks'])  # 15
        """
        self._ensure_initialized()

        loop = self._get_or_create_event_loop()
        result = loop.run_until_complete(
            self._orchestrator.process_file(file_path)
        )

        return result

    def search(
        self,
        query: str,
        limit: int = 10
    ) -> Dict[str, List[Dict]]:
        """
        Search across all knowledge sources.

        Args:
            query: Search query.
            limit: Maximum number of results.

        Returns:
            Dict with 'memory', 'web', and 'data' result lists.

        Example:
            >>> agi = ArynoxtechAGI()
            >>> results = agi.search("machine learning")
            >>> print(f"Found {len(results['memory'])} memory results")
        """
        self._ensure_initialized()

        loop = self._get_or_create_event_loop()
        result = loop.run_until_complete(
            self._orchestrator.search_knowledge(query, limit)
        )

        return result

    def list_domains(self) -> List[Dict[str, Any]]:
        """
        Get list of available domains.

        Returns:
            List of domain info dicts with name, description, specializations.

        Example:
            >>> agi = ArynoxtechAGI()
            >>> domains = agi.list_domains()
            >>> for d in domains:
            ...     print(f"{d['display_name']}: {d['description']}")
        """
        self._ensure_initialized()
        return self._orchestrator.domain_adaptor.get_available_domains()

    def set_domain(self, domain: Union[str, Domain]) -> bool:
        """
        Manually set the current domain.

        Args:
            domain: Domain name string or Domain enum.

        Returns:
            True if domain was set successfully.

        Example:
            >>> agi = ArynoxtechAGI()
            >>> agi.set_domain("code_assistant")
            >>> response = agi.chat("Help me fix this bug")
        """
        self._ensure_initialized()

        if isinstance(domain, Domain):
            domain = domain.value

        return self._orchestrator.domain_adaptor.set_domain(domain)

    def get_status(self) -> Dict[str, Any]:
        """
        Get AGI system status.

        Returns:
            Dict with system status including uptime, domains, metrics.

        Example:
            >>> agi = ArynoxtechAGI()
            >>> status = agi.get_status()
            >>> print(f"Uptime: {status['state']['uptime_seconds']} seconds")
        """
        self._ensure_initialized()

        loop = self._get_or_create_event_loop()
        result = loop.run_until_complete(
            self._orchestrator.get_status()
        )

        return result

    def start_api_server(
        self,
        host: str = "0.0.0.0",
        port: int = 8000
    ):
        """
        Start the AGI as a REST API server.

        Args:
            host: Server host (default: 0.0.0.0).
            port: Server port (default: 8000).

        Example:
            >>> agi = ArynoxtechAGI()
            >>> agi.start_api_server(port=8080)
        """
        self._ensure_initialized()

        loop = self._get_or_create_event_loop()
        loop.run_until_complete(
            self._orchestrator.run_interactive(use_voice=False)
        )

    def shutdown(self):
        """
        Shutdown the AGI gracefully.

        Call this when done using the AGI to clean up resources.
        """
        if self._orchestrator:
            loop = self._get_or_create_event_loop()
            loop.run_until_complete(self._orchestrator.shutdown())
            self._initialized = False
            logger.info("Arynoxtech_AGI shut down")

    def _get_or_create_event_loop(self):
        """Get or create an event loop for sync operations."""
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - shutdown AGI."""
        self.shutdown()
        return False

    def __repr__(self):
        return f"ArynoxtechAGI(v2.0.0, initialized={self._initialized})"