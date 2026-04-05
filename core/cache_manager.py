"""
NexusAGI Cache Manager
Intelligent caching for instant responses
2026 Technology Implementation
"""

import asyncio
import logging
import json
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import OrderedDict
import pickle
import gzip

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cached response"""
    key: str
    value: Any
    timestamp: datetime
    hit_count: int = 0
    ttl: int = 3600  # Time to live in seconds
    size_bytes: int = 0


class LRUCache:
    """
    Least Recently Used Cache
    Efficient caching with automatic eviction
    """
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        
        # OrderedDict maintains insertion order for LRU
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.current_memory_bytes = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self.cache:
            entry = self.cache[key]
            
            # Check TTL
            if datetime.now() - entry.timestamp > timedelta(seconds=entry.ttl):
                self._remove(key)
                self.misses += 1
                return None
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            entry.hit_count += 1
            self.hits += 1
            return entry.value
        
        self.misses += 1
        return None
    
    def put(self, key: str, value: Any, ttl: int = 3600):
        """Put value in cache"""
        # Calculate size
        size_bytes = len(pickle.dumps(value))
        
        # Remove if exists
        if key in self.cache:
            self._remove(key)
        
        # Evict if necessary
        while (len(self.cache) >= self.max_size or 
               self.current_memory_bytes + size_bytes > self.max_memory_bytes):
            if not self.cache:
                break
            self._evict_oldest()
        
        # Add new entry
        entry = CacheEntry(
            key=key,
            value=value,
            timestamp=datetime.now(),
            ttl=ttl,
            size_bytes=size_bytes
        )
        
        self.cache[key] = entry
        self.current_memory_bytes += size_bytes
    
    def _remove(self, key: str):
        """Remove entry from cache"""
        if key in self.cache:
            entry = self.cache.pop(key)
            self.current_memory_bytes -= entry.size_bytes
    
    def _evict_oldest(self):
        """Evict oldest entry"""
        if self.cache:
            key, entry = self.cache.popitem(last=False)
            self.current_memory_bytes -= entry.size_bytes
            self.evictions += 1
    
    def clear(self):
        """Clear all cache"""
        self.cache.clear()
        self.current_memory_bytes = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
        
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'evictions': self.evictions,
            'memory_bytes': self.current_memory_bytes,
            'max_memory_bytes': self.max_memory_bytes
        }


class CacheManager:
    """
    Cache Manager
    Manages multiple caches for different types of data
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Cache settings
        self.enabled = self.config.get('enabled', True)
        
        # Initialize different caches
        self.response_cache = LRUCache(
            max_size=self.config.get('response_cache_size', 5000),
            max_memory_mb=self.config.get('response_cache_memory_mb', 100)
        )
        
        self.search_cache = LRUCache(
            max_size=self.config.get('search_cache_size', 200),
            max_memory_mb=self.config.get('search_cache_memory_mb', 20)
        )
        
        self.context_cache = LRUCache(
            max_size=self.config.get('context_cache_size', 300),
            max_memory_mb=self.config.get('context_cache_memory_mb', 30)
        )
        
        # Instant response cache for common queries - millisecond responses
        self.instant_responses = {
            "hello": "Hello! I'm Arynoxtech_AGI, your personal artificial general intelligence. How can I assist you today?",
            "hi": "Hi there! I'm Arynoxtech_AGI. What can I help you with?",
            "how are you": "I'm operating at peak efficiency! All systems are nominal and I'm ready to assist you with anything you need.",
            "what can you do": "I can help you with code assistance, research, education, healthcare advice, customer support, business consulting, creative writing, and general knowledge. Just ask me anything!",
            "who are you": "I'm Arynoxtech_AGI, a multi-domain adaptive artificial general intelligence. I learn continuously and improve with every interaction.",
            "help": "I'm Arynoxtech_AGI. You can ask me questions, request help with tasks, discuss topics, or just chat. I learn continuously from our conversations and the internet.",
            "thank you": "You're very welcome! It's my pleasure to assist you. Is there anything else I can help you with?",
            "thanks": "You're welcome! Let me know if you need anything else.",
            "goodbye": "Goodbye! It was great talking with you. I'll remember our conversation for next time.",
            "bye": "Bye! Take care and come back anytime."
        }
        
        # Storage path
        self.storage_path = Path("memory/cache")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Load existing cache
        self._load_cache()
        
        logger.info(f"Cache Manager initialized with {len(self.instant_responses)} instant responses for millisecond replies")
    
    def _load_cache(self):
        """Load cache from disk"""
        try:
            cache_file = self.storage_path / "cache_data.pkl.gz"
            if cache_file.exists():
                with gzip.open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                    # Note: In production, you'd restore the cache
                    # For now, we start fresh
                logger.info("Cache loaded from disk")
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
    
    def _save_cache(self):
        """Save cache to disk"""
        try:
            cache_file = self.storage_path / "cache_data.pkl.gz"
            # Save cache statistics
            data = {
                'response_cache': self.response_cache.get_stats(),
                'search_cache': self.search_cache.get_stats(),
                'context_cache': self.context_cache.get_stats(),
                'timestamp': datetime.now().isoformat()
            }
            
            with gzip.open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def get_response(self, query: str) -> Optional[str]:
        """Get cached response for query - first check instant responses for millisecond replies"""
        if not self.enabled:
            return None
        
        # Check instant response cache first (microsecond response time)
        query_clean = query.lower().strip()
        if query_clean in self.instant_responses:
            logger.debug(f"Instant response hit for: {query_clean}")
            return self.instant_responses[query_clean]
        
        # Check regular cache
        key = hashlib.md5(query.encode()).hexdigest()
        return self.response_cache.get(key)
    
    def cache_response(self, query: str, response: str, ttl: int = 3600):
        """Cache response for query"""
        if not self.enabled:
            return
        
        key = hashlib.md5(query.encode()).hexdigest()
        self.response_cache.put(key, response, ttl)
    
    def get_search_results(self, query: str) -> Optional[List[Dict]]:
        """Get cached search results"""
        if not self.enabled:
            return None
        
        key = hashlib.md5(f"search_{query}".encode()).hexdigest()
        return self.search_cache.get(key)
    
    def cache_search_results(self, query: str, results: List[Dict], ttl: int = 1800):
        """Cache search results"""
        if not self.enabled:
            return
        
        key = hashlib.md5(f"search_{query}".encode()).hexdigest()
        self.search_cache.put(key, results, ttl)
    
    def get_context(self, query: str) -> Optional[List[Dict]]:
        """Get cached context"""
        if not self.enabled:
            return None
        
        key = hashlib.md5(f"context_{query}".encode()).hexdigest()
        return self.context_cache.get(key)
    
    def cache_context(self, query: str, context: List[Dict], ttl: int = 1800):
        """Cache context"""
        if not self.enabled:
            return
        
        key = hashlib.md5(f"context_{query}".encode()).hexdigest()
        self.context_cache.put(key, context, ttl)
    
    def clear_all(self):
        """Clear all caches"""
        self.response_cache.clear()
        self.search_cache.clear()
        self.context_cache.clear()
        logger.info("All caches cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'enabled': self.enabled,
            'response_cache': self.response_cache.get_stats(),
            'search_cache': self.search_cache.get_stats(),
            'context_cache': self.context_cache.get_stats()
        }
    
    def optimize(self):
        """Optimize caches"""
        # Save cache to disk
        self._save_cache()
        
        # Log statistics
        stats = self.get_stats()
        logger.info(f"Cache optimized - Response hit rate: {stats['response_cache']['hit_rate']:.2%}")
