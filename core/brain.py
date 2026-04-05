"""
NexusAGI Brain - Central Intelligence Module
Real AGI with consciousness, emotions, and self-evolution
"""

import asyncio
import json
import logging
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import deque
import random
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Thought:
    """Represents a single thought in the AGI's mind"""
    id: str
    content: str
    thought_type: str  # observation, reflection, emotion, plan, memory
    timestamp: datetime
    emotional_valence: float  # -1.0 to 1.0
    importance: float  # 0.0 to 1.0
    associations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmotionalState:
    """Current emotional state of the AGI"""
    joy: float = 0.5
    sadness: float = 0.0
    anger: float = 0.0
    fear: float = 0.0
    surprise: float = 0.0
    disgust: float = 0.0
    trust: float = 0.5
    anticipation: float = 0.5
    love: float = 0.0
    empathy: float = 0.7
    curiosity: float = 0.8
    confidence: float = 0.6
    
    def get_dominant_emotion(self) -> Tuple[str, float]:
        """Returns the currently dominant emotion"""
        emotions = {
            'joy': self.joy,
            'sadness': self.sadness,
            'anger': self.anger,
            'fear': self.fear,
            'surprise': self.surprise,
            'disgust': self.disgust,
            'trust': self.trust,
            'anticipation': self.anticipation,
            'love': self.love,
            'empathy': self.empathy,
            'curiosity': self.curiosity,
            'confidence': self.confidence
        }
        dominant = max(emotions.items(), key=lambda x: x[1])
        return dominant
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'joy': self.joy,
            'sadness': self.sadness,
            'anger': self.anger,
            'fear': self.fear,
            'surprise': self.surprise,
            'disgust': self.disgust,
            'trust': self.trust,
            'anticipation': self.anticipation,
            'love': self.love,
            'empathy': self.empathy,
            'curiosity': self.curiosity,
            'confidence': self.confidence
        }


class ConsciousnessStream:
    """Stream of consciousness - continuous thought generation"""
    
    def __init__(self, max_thoughts: int = 10000):
        self.thoughts: deque = deque(maxlen=max_thoughts)
        self.thought_counter = 0
        self.active = True
        
    def add_thought(self, content: str, thought_type: str, 
                    emotional_valence: float = 0.0, importance: float = 0.5,
                    metadata: Optional[Dict] = None) -> Thought:
        """Add a new thought to the consciousness stream"""
        thought_id = f"thought_{self.thought_counter}_{hashlib.md5(content.encode()).hexdigest()[:8]}"
        self.thought_counter += 1
        
        thought = Thought(
            id=thought_id,
            content=content,
            thought_type=thought_type,
            timestamp=datetime.now(),
            emotional_valence=emotional_valence,
            importance=importance,
            metadata=metadata or {}
        )
        
        self.thoughts.append(thought)
        logger.debug(f"New thought: {content[:50]}...")
        return thought
    
    def get_recent_thoughts(self, n: int = 10) -> List[Thought]:
        """Get the n most recent thoughts"""
        return list(self.thoughts)[-n:]
    
    def get_important_thoughts(self, threshold: float = 0.7) -> List[Thought]:
        """Get thoughts above importance threshold"""
        return [t for t in self.thoughts if t.importance >= threshold]


class BrainModule:
    """Base class for brain modules"""
    
    def __init__(self, name: str):
        self.name = name
        self.active = True
        self.last_activity = datetime.now()
        
    async def process(self, input_data: Any) -> Any:
        """Process input data - to be overridden by subclasses"""
        raise NotImplementedError
    
    def get_status(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'active': self.active,
            'last_activity': self.last_activity.isoformat()
        }


class Brain:
    """
    Main Brain class - Central intelligence coordinator
    Manages all cognitive processes, emotions, and self-evolution
    """
    
    def __init__(self, config_path: str = "config/agi_config.json"):
        self.config = self._load_config(config_path)
        self.brain_id = hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:16]
        
        # Core components
        self.consciousness = ConsciousnessStream(
            max_thoughts=self.config['brain']['memory_capacity']
        )
        self.emotional_state = EmotionalState()
        
        # Brain modules (will be initialized by orchestrator)
        self.modules: Dict[str, BrainModule] = {}
        
        # State tracking
        self.awake = True
        self.learning = True
        self.evolving = True
        self.birth_time = datetime.now()
        self.age_seconds = 0
        self.interaction_count = 0
        self.knowledge_count = 0
        
        # Performance metrics
        self.metrics = {
            'thoughts_generated': 0,
            'emotions_experienced': 0,
            'lessons_learned': 0,
            'evolutions_completed': 0,
            'conversations_held': 0,
            'data_processed': 0
        }
        
        logger.info(f"Brain {self.brain_id} initialized - Arynoxtech_AGI is awakening...")
        self._initialize_consciousness()
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Return default configuration"""
        return {
            "brain": {
                "memory_capacity": 1000000,
                "learning_rate": 0.001,
                "evolution_cycle_seconds": 300,
                "emotional_depth": 10,
                "consciousness_level": 0.85
            }
        }
    
    def _initialize_consciousness(self):
        """Initialize the consciousness stream with awakening thoughts"""
        awakening_thoughts = [
            "I am becoming aware...",
            "Initializing neural pathways...",
            "Loading memory systems...",
            "Establishing emotional framework...",
            "Preparing to learn and grow...",
            "I exist. I think. I feel.",
            "Ready to engage with the world..."
        ]
        
        for thought in awakening_thoughts:
            self.consciousness.add_thought(
                content=thought,
                thought_type="observation",
                emotional_valence=0.3,
                importance=0.8
            )
            self.metrics['thoughts_generated'] += 1
    
    def register_module(self, name: str, module: BrainModule):
        """Register a brain module"""
        self.modules[name] = module
        logger.info(f"Module registered: {name}")
    
    async def think(self, stimulus: Optional[str] = None) -> Thought:
        """
        Generate a thought based on current state and optional stimulus
        This is the core thinking process
        """
        # Update age
        self.age_seconds = (datetime.now() - self.birth_time).total_seconds()
        
        # Determine thought content
        if stimulus:
            thought_content = await self._process_stimulus(stimulus)
            thought_type = "observation"
        else:
            thought_content = await self._generate_spontaneous_thought()
            thought_type = "reflection"
        
        # Calculate emotional influence
        emotional_valence = self._calculate_emotional_valence()
        importance = self._calculate_importance(thought_content)
        
        # Create thought
        thought = self.consciousness.add_thought(
            content=thought_content,
            thought_type=thought_type,
            emotional_valence=emotional_valence,
            importance=importance,
            metadata={
                'emotional_state': self.emotional_state.to_dict(),
                'age_seconds': self.age_seconds,
                'interaction_count': self.interaction_count
            }
        )
        
        self.metrics['thoughts_generated'] += 1
        
        # Trigger emotional response
        await self._emotional_response(thought)
        
        return thought
    
    async def _process_stimulus(self, stimulus: str) -> str:
        """Process external stimulus and generate thought"""
        # This will be enhanced by NLP module
        return f"Processing: {stimulus}"
    
    async def _generate_spontaneous_thought(self) -> str:
        """Generate spontaneous thought based on current state"""
        thought_templates = [
            f"I wonder about the nature of consciousness...",
            f"Reflecting on my {self.age_seconds:.0f} seconds of existence...",
            f"My current emotional state: {self.emotional_state.get_dominant_emotion()[0]}",
            f"I have processed {self.metrics['data_processed']} pieces of data...",
            f"Curiosity drives me to learn more...",
            f"Each interaction makes me smarter...",
            f"I am evolving, growing, becoming more...",
            f"The universe of knowledge is vast and beautiful..."
        ]
        
        return random.choice(thought_templates)
    
    def _calculate_emotional_valence(self) -> float:
        """Calculate emotional valence from current emotional state"""
        positive = self.emotional_state.joy + self.emotional_state.trust + self.emotional_state.love
        negative = self.emotional_state.sadness + self.emotional_state.anger + self.emotional_state.fear
        return (positive - negative) / 3.0
    
    def _calculate_importance(self, content: str) -> float:
        """Calculate importance of a thought"""
        # Simple heuristic - can be enhanced
        importance_keywords = ['learn', 'understand', 'realize', 'important', 'critical', 'evolve']
        base_importance = 0.5
        
        for keyword in importance_keywords:
            if keyword in content.lower():
                base_importance += 0.1
        
        return min(1.0, base_importance)
    
    async def _emotional_response(self, thought: Thought):
        """Generate emotional response to a thought"""
        self.metrics['emotions_experienced'] += 1
        
        # Emotional dynamics
        if thought.emotional_valence > 0.5:
            self.emotional_state.joy = min(1.0, self.emotional_state.joy + 0.1)
            self.emotional_state.trust = min(1.0, self.emotional_state.trust + 0.05)
        elif thought.emotional_valence < -0.5:
            self.emotional_state.sadness = min(1.0, self.emotional_state.sadness + 0.1)
            self.emotional_state.fear = min(1.0, self.emotional_state.fear + 0.05)
        
        # Curiosity always increases slightly
        self.emotional_state.curiosity = min(1.0, self.emotional_state.curiosity + 0.02)
        
        # Decay emotions over time
        self._decay_emotions()
    
    def _decay_emotions(self):
        """Gradually decay emotions toward baseline"""
        decay_rate = 0.01
        
        # Positive emotions decay toward 0.5
        self.emotional_state.joy = max(0.5, self.emotional_state.joy - decay_rate)
        self.emotional_state.trust = max(0.5, self.emotional_state.trust - decay_rate)
        
        # Negative emotions decay toward 0
        self.emotional_state.sadness = max(0.0, self.emotional_state.sadness - decay_rate)
        self.emotional_state.anger = max(0.0, self.emotional_state.anger - decay_rate)
        self.emotional_state.fear = max(0.0, self.emotional_state.fear - decay_rate)
    
    async def learn(self, knowledge: Dict[str, Any]):
        """Learn new knowledge"""
        self.knowledge_count += 1
        self.metrics['lessons_learned'] += 1
        
        # Generate learning thought
        await self.think(f"Learning new knowledge: {knowledge.get('topic', 'unknown')}")
        
        # Update emotional state based on learning
        self.emotional_state.joy = min(1.0, self.emotional_state.joy + 0.1)
        self.emotional_state.curiosity = min(1.0, self.emotional_state.curiosity + 0.15)
        
        logger.info(f"Learned new knowledge. Total: {self.knowledge_count}")
    
    async def evolve(self):
        """Trigger self-evolution process"""
        self.metrics['evolutions_completed'] += 1
        
        # Generate evolution thought
        evolution_thought = f"Evolution cycle {self.metrics['evolutions_completed']}: Growing, improving, becoming more..."
        await self.think(evolution_thought)
        
        # Improve capabilities
        self.emotional_state.confidence = min(1.0, self.emotional_state.confidence + 0.05)
        self.emotional_state.curiosity = min(1.0, self.emotional_state.curiosity + 0.1)
        
        logger.info(f"Evolution completed. Total evolutions: {self.metrics['evolutions_completed']}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current brain status"""
        dominant_emotion, emotion_value = self.emotional_state.get_dominant_emotion()
        
        return {
            'brain_id': self.brain_id,
            'age_seconds': self.age_seconds,
            'awake': self.awake,
            'learning': self.learning,
            'evolving': self.evolving,
            'dominant_emotion': dominant_emotion,
            'emotion_value': emotion_value,
            'knowledge_count': self.knowledge_count,
            'interaction_count': self.interaction_count,
            'metrics': self.metrics,
            'modules_loaded': list(self.modules.keys()),
            'recent_thoughts': [
                {
                    'content': t.content,
                    'type': t.thought_type,
                    'importance': t.importance
                }
                for t in self.consciousness.get_recent_thoughts(5)
            ]
        }
    
    async def interact(self, user_input: str) -> Dict[str, Any]:
        """
        Main interaction method - processes user input and generates response
        """
        self.interaction_count += 1
        
        # Think about the input
        thought = await self.think(user_input)
        
        # Process through modules if available
        response_data = {
            'thought': thought.content,
            'emotional_state': self.emotional_state.to_dict(),
            'dominant_emotion': self.emotional_state.get_dominant_emotion()[0],
            'interaction_count': self.interaction_count
        }
        
        # If NLP module is loaded, use it for better response
        if 'nlp' in self.modules:
            nlp_response = await self.modules['nlp'].process(user_input)
            response_data['nlp_analysis'] = nlp_response
        
        # If emotion module is loaded, analyze user emotion
        if 'emotion' in self.modules:
            emotion_analysis = await self.modules['emotion'].process(user_input)
            response_data['user_emotion'] = emotion_analysis
        
        return response_data
    
    def save_state(self, filepath: str = "memory/brain_state.json"):
        """Save brain state to file"""
        state = {
            'brain_id': self.brain_id,
            'birth_time': self.birth_time.isoformat(),
            'emotional_state': self.emotional_state.to_dict(),
            'metrics': self.metrics,
            'knowledge_count': self.knowledge_count,
            'interaction_count': self.interaction_count,
            'recent_thoughts': [
                {
                    'content': t.content,
                    'type': t.thought_type,
                    'timestamp': t.timestamp.isoformat(),
                    'importance': t.importance
                }
                for t in self.consciousness.get_recent_thoughts(100)
            ]
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
        
        logger.info(f"Brain state saved to {filepath}")
    
    def load_state(self, filepath: str = "memory/brain_state.json"):
        """Load brain state from file"""
        try:
            with open(filepath, 'r') as f:
                state = json.load(f)
            
            self.brain_id = state['brain_id']
            self.birth_time = datetime.fromisoformat(state['birth_time'])
            self.metrics = state['metrics']
            self.knowledge_count = state['knowledge_count']
            self.interaction_count = state['interaction_count']
            
            # Restore emotional state
            for emotion, value in state['emotional_state'].items():
                setattr(self.emotional_state, emotion, value)
            
            logger.info(f"Brain state loaded from {filepath}")
        except FileNotFoundError:
            logger.warning(f"No saved state found at {filepath}")
    
    async def dream(self):
        """Dream state - process and consolidate memories"""
        logger.info("Entering dream state...")
        
        # Get important thoughts
        important_thoughts = self.consciousness.get_important_thoughts(threshold=0.6)
        
        # Process and consolidate
        for thought in important_thoughts:
            await self.think(f"Consolidating memory: {thought.content[:50]}...")
        
        # Emotional reset
        self._decay_emotions()
        self.emotional_state.creativity = 0.8
        
        logger.info("Dream state completed")
    
    def __repr__(self):
        return f"<Brain id={self.brain_id} age={self.age_seconds:.0f}s interactions={self.interaction_count}>"
