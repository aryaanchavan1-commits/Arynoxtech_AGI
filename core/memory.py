"""
Arynoxtech_AGI Memory Systems
Short-term, Long-term, Episodic, and Semantic Memory
"""

import json
import logging
import time
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import deque, defaultdict
import pickle
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Memory:
    """Base memory unit"""
    id: str
    content: Any
    memory_type: str  # short_term, long_term, episodic, semantic
    timestamp: datetime
    importance: float  # 0.0 to 1.0
    emotional_valence: float  # -1.0 to 1.0
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    associations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def access(self):
        """Record memory access"""
        self.access_count += 1
        self.last_accessed = datetime.now()
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'content': str(self.content)[:1000],  # Truncate for storage
            'memory_type': self.memory_type,
            'timestamp': self.timestamp.isoformat(),
            'importance': self.importance,
            'emotional_valence': self.emotional_valence,
            'access_count': self.access_count,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'associations': self.associations,
            'metadata': self.metadata
        }


class ShortTermMemory:
    """
    Short-term Memory (Working Memory)
    Limited capacity, fast access, temporary storage
    """
    
    def __init__(self, capacity: int = 100):
        self.capacity = capacity
        self.memories: deque = deque(maxlen=capacity)
        self.index: Dict[str, Memory] = {}
        
    def store(self, content: Any, importance: float = 0.5, 
              emotional_valence: float = 0.0, metadata: Optional[Dict] = None) -> Memory:
        """Store a memory in short-term memory"""
        memory_id = f"stm_{len(self.memories)}_{hashlib.md5(str(content).encode()).hexdigest()[:8]}"
        
        memory = Memory(
            id=memory_id,
            content=content,
            memory_type='short_term',
            timestamp=datetime.now(),
            importance=importance,
            emotional_valence=emotional_valence,
            metadata=metadata or {}
        )
        
        # Remove oldest if at capacity
        if len(self.memories) >= self.capacity:
            oldest = self.memories[0]
            if oldest.id in self.index:
                del self.index[oldest.id]
        
        self.memories.append(memory)
        self.index[memory_id] = memory
        
        logger.debug(f"Stored short-term memory: {memory_id}")
        return memory
    
    def retrieve(self, memory_id: str) -> Optional[Memory]:
        """Retrieve a specific memory by ID"""
        memory = self.index.get(memory_id)
        if memory:
            memory.access()
        return memory
    
    def get_recent(self, n: int = 10) -> List[Memory]:
        """Get n most recent memories"""
        return list(self.memories)[-n:]
    
    def get_important(self, threshold: float = 0.7) -> List[Memory]:
        """Get memories above importance threshold"""
        return [m for m in self.memories if m.importance >= threshold]
    
    def search(self, query: str, limit: int = 10) -> List[Memory]:
        """Search memories by content"""
        results = []
        query_lower = query.lower()
        
        for memory in self.memories:
            if query_lower in str(memory.content).lower():
                memory.access()
                results.append(memory)
                if len(results) >= limit:
                    break
        
        return results
    
    def clear(self):
        """Clear all short-term memories"""
        self.memories.clear()
        self.index.clear()
        logger.info("Short-term memory cleared")
    
    def get_status(self) -> Dict:
        return {
            'capacity': self.capacity,
            'current_count': len(self.memories),
            'utilization': len(self.memories) / self.capacity
        }


class LongTermMemory:
    """
    Long-term Memory
    Large capacity, persistent storage, slower access
    """
    
    def __init__(self, storage_path: str = "memory/long_term"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.memories: Dict[str, Memory] = {}
        self.index_file = self.storage_path / "memory_index.json"
        
        # Load existing memories
        self._load_index()
        
    def _load_index(self):
        """Load memory index from disk"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    index_data = json.load(f)
                
                for memory_id, memory_data in index_data.items():
                    memory = Memory(
                        id=memory_data['id'],
                        content=memory_data['content'],
                        memory_type='long_term',
                        timestamp=datetime.fromisoformat(memory_data['timestamp']),
                        importance=memory_data['importance'],
                        emotional_valence=memory_data['emotional_valence'],
                        access_count=memory_data['access_count'],
                        last_accessed=datetime.fromisoformat(memory_data['last_accessed']) if memory_data['last_accessed'] else None,
                        associations=memory_data['associations'],
                        metadata=memory_data['metadata']
                    )
                    self.memories[memory_id] = memory
                
                logger.info(f"Loaded {len(self.memories)} long-term memories")
            except Exception as e:
                logger.error(f"Error loading memory index: {e}")
    
    def _save_index(self):
        """Save memory index to disk"""
        index_data = {}
        for memory_id, memory in self.memories.items():
            index_data[memory_id] = memory.to_dict()
        
        with open(self.index_file, 'w') as f:
            json.dump(index_data, f, indent=2)
    
    def store(self, content: Any, importance: float = 0.5,
              emotional_valence: float = 0.0, metadata: Optional[Dict] = None) -> Memory:
        """Store a memory in long-term memory"""
        memory_id = f"ltm_{len(self.memories)}_{hashlib.md5(str(content).encode()).hexdigest()[:8]}"
        
        memory = Memory(
            id=memory_id,
            content=content,
            memory_type='long_term',
            timestamp=datetime.now(),
            importance=importance,
            emotional_valence=emotional_valence,
            metadata=metadata or {}
        )
        
        self.memories[memory_id] = memory
        self._save_index()
        
        logger.debug(f"Stored long-term memory: {memory_id}")
        return memory
    
    def retrieve(self, memory_id: str) -> Optional[Memory]:
        """Retrieve a specific memory by ID"""
        memory = self.memories.get(memory_id)
        if memory:
            memory.access()
            self._save_index()
        return memory
    
    def search(self, query: str, limit: int = 20) -> List[Memory]:
        """Search memories by content"""
        results = []
        query_lower = query.lower()
        
        for memory in self.memories.values():
            if query_lower in str(memory.content).lower():
                memory.access()
                results.append(memory)
                if len(results) >= limit:
                    break
        
        # Sort by importance and recency
        results.sort(key=lambda m: (m.importance, m.timestamp), reverse=True)
        return results
    
    def get_important(self, threshold: float = 0.7) -> List[Memory]:
        """Get memories above importance threshold"""
        return [m for m in self.memories.values() if m.importance >= threshold]
    
    def consolidate(self, memory: Memory):
        """Consolidate a memory from short-term to long-term"""
        if memory.id not in self.memories:
            self.memories[memory.id] = memory
            memory.memory_type = 'long_term'
            self._save_index()
            logger.info(f"Consolidated memory to long-term: {memory.id}")
    
    def get_status(self) -> Dict:
        return {
            'total_memories': len(self.memories),
            'storage_path': str(self.storage_path)
        }


class EpisodicMemory:
    """
    Episodic Memory
    Stores personal experiences and events
    """
    
    def __init__(self, storage_path: str = "memory/episodic"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.episodes: List[Dict] = []
        self.episodes_file = self.storage_path / "episodes.json"
        
        self._load_episodes()
    
    def _load_episodes(self):
        """Load episodes from disk"""
        if self.episodes_file.exists():
            try:
                with open(self.episodes_file, 'r') as f:
                    self.episodes = json.load(f)
                logger.info(f"Loaded {len(self.episodes)} episodes")
            except Exception as e:
                logger.error(f"Error loading episodes: {e}")
    
    def _save_episodes(self):
        """Save episodes to disk"""
        with open(self.episodes_file, 'w') as f:
            json.dump(self.episodes, f, indent=2)
    
    def record_episode(self, event: str, context: Dict[str, Any],
                       emotional_state: Dict[str, float], importance: float = 0.5):
        """Record a new episode"""
        episode = {
            'id': f"episode_{len(self.episodes)}_{hashlib.md5(event.encode()).hexdigest()[:8]}",
            'event': event,
            'context': context,
            'emotional_state': emotional_state,
            'importance': importance,
            'timestamp': datetime.now().isoformat(),
            'recall_count': 0
        }
        
        self.episodes.append(episode)
        self._save_episodes()
        
        logger.info(f"Recorded episode: {event[:50]}...")
        return episode
    
    def recall_episodes(self, query: Optional[str] = None, 
                       emotional_filter: Optional[str] = None,
                       limit: int = 10) -> List[Dict]:
        """Recall episodes based on query or emotional filter"""
        results = []
        
        for episode in reversed(self.episodes):  # Most recent first
            match = True
            
            if query:
                if query.lower() not in episode['event'].lower():
                    match = False
            
            if emotional_filter and match:
                dominant_emotion = max(episode['emotional_state'].items(), 
                                     key=lambda x: x[1])[0]
                if dominant_emotion != emotional_filter:
                    match = False
            
            if match:
                episode['recall_count'] += 1
                results.append(episode)
                if len(results) >= limit:
                    break
        
        self._save_episodes()
        return results
    
    def get_recent_episodes(self, n: int = 10) -> List[Dict]:
        """Get n most recent episodes"""
        return self.episodes[-n:]
    
    def get_important_episodes(self, threshold: float = 0.7) -> List[Dict]:
        """Get episodes above importance threshold"""
        return [e for e in self.episodes if e['importance'] >= threshold]
    
    def get_status(self) -> Dict:
        return {
            'total_episodes': len(self.episodes),
            'storage_path': str(self.storage_path)
        }


class SemanticMemory:
    """
    Semantic Memory
    Stores factual knowledge and concepts
    """
    
    def __init__(self, storage_path: str = "memory/semantic"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.concepts: Dict[str, Dict] = {}
        self.relationships: Dict[str, List[str]] = defaultdict(list)
        self.concepts_file = self.storage_path / "concepts.json"
        
        self._load_concepts()
    
    def _load_concepts(self):
        """Load concepts from disk"""
        if self.concepts_file.exists():
            try:
                with open(self.concepts_file, 'r') as f:
                    data = json.load(f)
                    self.concepts = data.get('concepts', {})
                    self.relationships = defaultdict(list, data.get('relationships', {}))
                logger.info(f"Loaded {len(self.concepts)} concepts")
            except Exception as e:
                logger.error(f"Error loading concepts: {e}")
    
    def _save_concepts(self):
        """Save concepts to disk"""
        data = {
            'concepts': self.concepts,
            'relationships': dict(self.relationships)
        }
        
        with open(self.concepts_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_concept(self, name: str, definition: str, 
                   properties: Optional[Dict] = None,
                   category: Optional[str] = None) -> Dict:
        """Add a new concept"""
        concept = {
            'name': name,
            'definition': definition,
            'properties': properties or {},
            'category': category,
            'created': datetime.now().isoformat(),
            'access_count': 0,
            'confidence': 0.8
        }
        
        self.concepts[name.lower()] = concept
        self._save_concepts()
        
        logger.info(f"Added concept: {name}")
        return concept
    
    def get_concept(self, name: str) -> Optional[Dict]:
        """Get a concept by name"""
        concept = self.concepts.get(name.lower())
        if concept:
            concept['access_count'] += 1
            self._save_concepts()
        return concept
    
    def add_relationship(self, concept1: str, concept2: str, relationship_type: str):
        """Add a relationship between concepts"""
        key = f"{concept1.lower()}:{relationship_type}"
        if concept2.lower() not in self.relationships[key]:
            self.relationships[key].append(concept2.lower())
            self._save_concepts()
            logger.debug(f"Added relationship: {concept1} -{relationship_type}-> {concept2}")
    
    def get_related_concepts(self, concept_name: str, relationship_type: Optional[str] = None) -> List[str]:
        """Get concepts related to a given concept"""
        related = []
        concept_lower = concept_name.lower()
        
        for key, concepts in self.relationships.items():
            if concept_lower in key:
                if relationship_type is None or relationship_type in key:
                    related.extend(concepts)
        
        return list(set(related))
    
    def search_concepts(self, query: str, limit: int = 20) -> List[Dict]:
        """Search concepts by name or definition"""
        results = []
        query_lower = query.lower()
        
        for concept in self.concepts.values():
            if (query_lower in concept['name'].lower() or 
                query_lower in concept['definition'].lower()):
                concept['access_count'] += 1
                results.append(concept)
                if len(results) >= limit:
                    break
        
        self._save_concepts()
        return results
    
    def learn_from_text(self, text: str, source: str = "unknown"):
        """Extract and learn concepts from text"""
        # Simple keyword extraction - can be enhanced with NLP
        words = text.split()
        
        # Look for potential concepts (capitalized words, phrases)
        potential_concepts = []
        for i, word in enumerate(words):
            if word[0].isupper() and len(word) > 3:
                potential_concepts.append(word)
        
        # Add as concepts
        for concept_name in potential_concepts[:10]:  # Limit to 10 per text
            if concept_name.lower() not in self.concepts:
                self.add_concept(
                    name=concept_name,
                    definition=f"Concept learned from {source}",
                    properties={'source': source, 'context': text[:200]}
                )
    
    def get_status(self) -> Dict:
        return {
            'total_concepts': len(self.concepts),
            'total_relationships': sum(len(v) for v in self.relationships.values()),
            'storage_path': str(self.storage_path)
        }


class MemoryManager:
    """
    Central Memory Manager
    Coordinates all memory systems
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Initialize memory systems
        self.short_term = ShortTermMemory(
            capacity=self.config.get('short_term_capacity', 100)
        )
        self.long_term = LongTermMemory(
            storage_path=self.config.get('long_term_path', 'memory/long_term')
        )
        self.episodic = EpisodicMemory(
            storage_path=self.config.get('episodic_path', 'memory/episodic')
        )
        self.semantic = SemanticMemory(
            storage_path=self.config.get('semantic_path', 'memory/semantic')
        )
        
        # Memory consolidation settings
        self.consolidation_threshold = self.config.get('consolidation_threshold', 0.7)
        self.consolidation_interval = self.config.get('consolidation_interval', 60)  # seconds
        self.last_consolidation = datetime.now()
        
        logger.info("Memory Manager initialized")
    
    def store(self, content: Any, memory_type: str = 'auto',
              importance: float = 0.5, emotional_valence: float = 0.0,
              metadata: Optional[Dict] = None) -> Memory:
        """
        Store a memory in the appropriate memory system
        """
        if memory_type == 'auto':
            # Auto-select based on importance
            if importance >= self.consolidation_threshold:
                memory_type = 'long_term'
            else:
                memory_type = 'short_term'
        
        if memory_type == 'short_term':
            return self.short_term.store(content, importance, emotional_valence, metadata)
        elif memory_type == 'long_term':
            return self.long_term.store(content, importance, emotional_valence, metadata)
        else:
            raise ValueError(f"Unknown memory type: {memory_type}")
    
    def retrieve(self, memory_id: str) -> Optional[Memory]:
        """Retrieve a memory by ID from any memory system"""
        # Try short-term first
        memory = self.short_term.retrieve(memory_id)
        if memory:
            return memory
        
        # Try long-term
        memory = self.long_term.retrieve(memory_id)
        if memory:
            return memory
        
        return None
    
    def search(self, query: str, memory_types: Optional[List[str]] = None,
               limit: int = 20) -> List[Memory]:
        """Search across all memory systems"""
        if memory_types is None:
            memory_types = ['short_term', 'long_term']
        
        results = []
        
        if 'short_term' in memory_types:
            results.extend(self.short_term.search(query, limit))
        
        if 'long_term' in memory_types:
            results.extend(self.long_term.search(query, limit))
        
        # Sort by importance and recency
        results.sort(key=lambda m: (m.importance, m.timestamp), reverse=True)
        return results[:limit]
    
    def record_episode(self, event: str, context: Dict[str, Any],
                      emotional_state: Dict[str, float], importance: float = 0.5):
        """Record an episodic memory"""
        return self.episodic.record_episode(event, context, emotional_state, importance)
    
    def add_concept(self, name: str, definition: str, **kwargs) -> Dict:
        """Add a semantic concept"""
        return self.semantic.add_concept(name, definition, **kwargs)
    
    def get_concept(self, name: str) -> Optional[Dict]:
        """Get a semantic concept"""
        return self.semantic.get_concept(name)
    
    async def consolidate_memories(self):
        """
        Consolidate important short-term memories to long-term
        This should be called periodically
        """
        now = datetime.now()
        if (now - self.last_consolidation).total_seconds() < self.consolidation_interval:
            return
        
        # Get important short-term memories
        important_memories = self.short_term.get_important(self.consolidation_threshold)
        
        for memory in important_memories:
            self.long_term.consolidate(memory)
        
        self.last_consolidation = now
        logger.info(f"Consolidated {len(important_memories)} memories to long-term")
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all memory systems"""
        return {
            'short_term': self.short_term.get_status(),
            'long_term': self.long_term.get_status(),
            'episodic': self.episodic.get_status(),
            'semantic': self.semantic.get_status(),
            'last_consolidation': self.last_consolidation.isoformat()
        }
    
    def save_all(self):
        """Save all memory systems to disk"""
        self.long_term._save_index()
        self.episodic._save_episodes()
        self.semantic._save_concepts()
        logger.info("All memory systems saved")
