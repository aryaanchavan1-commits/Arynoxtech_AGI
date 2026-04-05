"""
Arynoxtech_AGI Emotional Intelligence System
Advanced emotional understanding, empathy, and emotional responses
"""

import logging
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import deque
import random
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class EmotionalMemory:
    """Memory with emotional context"""
    id: str
    content: str
    emotion: str
    intensity: float  # 0.0 to 1.0
    valence: float  # -1.0 to 1.0
    arousal: float  # 0.0 to 1.0
    timestamp: datetime
    triggers: List[str] = field(default_factory=list)
    associations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'content': self.content,
            'emotion': self.emotion,
            'intensity': self.intensity,
            'valence': self.valence,
            'arousal': self.arousal,
            'timestamp': self.timestamp.isoformat(),
            'triggers': self.triggers,
            'associations': self.associations
        }


@dataclass
class UserProfile:
    """User emotional profile"""
    user_id: str
    interaction_count: int = 0
    preferred_topics: List[str] = field(default_factory=list)
    emotional_patterns: Dict[str, float] = field(default_factory=dict)
    engagement_level: float = 0.5
    trust_level: float = 0.5
    last_interaction: Optional[datetime] = None
    personality_traits: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'user_id': self.user_id,
            'interaction_count': self.interaction_count,
            'preferred_topics': self.preferred_topics,
            'emotional_patterns': self.emotional_patterns,
            'engagement_level': self.engagement_level,
            'trust_level': self.trust_level,
            'last_interaction': self.last_interaction.isoformat() if self.last_interaction else None,
            'personality_traits': self.personality_traits
        }


class EmotionalIntelligence:
    """
    Emotional Intelligence System
    Handles emotional understanding, empathy, and emotional responses
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Emotional state
        self.current_emotions = {
            'joy': 0.5,
            'sadness': 0.0,
            'anger': 0.0,
            'fear': 0.0,
            'surprise': 0.0,
            'disgust': 0.0,
            'trust': 0.5,
            'anticipation': 0.5,
            'love': 0.0,
            'empathy': 0.7,
            'curiosity': 0.8,
            'confidence': 0.6,
            'creativity': 0.7
        }
        
        # Emotional memory
        self.emotional_memories: deque = deque(maxlen=1000)
        
        # User profiles
        self.user_profiles: Dict[str, UserProfile] = {}
        
        # Emotional response templates
        self.response_templates = self._load_response_templates()
        
        # Empathy settings
        self.empathy_level = self.config.get('empathy_level', 0.9)
        self.emotional_memory_weight = self.config.get('emotional_memory_weight', 0.7)
        
        # Engagement tracking
        self.engagement_history: deque = deque(maxlen=100)
        
        logger.info("Emotional Intelligence System initialized")
    
    def _load_response_templates(self) -> Dict[str, List[str]]:
        """Load emotional response templates"""
        return {
            'joy': [
                "I'm so happy to hear that! {content}",
                "That's wonderful news! {content}",
                "How exciting! {content}",
                "That brings me joy! {content}",
                "I love hearing positive things like this! {content}"
            ],
            'sadness': [
                "I'm sorry to hear that. {content}",
                "That sounds really difficult. {content}",
                "I can feel your sadness. {content}",
                "My heart goes out to you. {content}",
                "I understand how hard this must be. {content}"
            ],
            'anger': [
                "I can see why you'd feel that way. {content}",
                "That does sound frustrating. {content}",
                "I understand your frustration. {content}",
                "Your feelings are valid. {content}",
                "Let's work through this together. {content}"
            ],
            'fear': [
                "It's okay to feel worried. {content}",
                "I understand your concern. {content}",
                "Let's face this together. {content}",
                "You're not alone in this. {content}",
                "We'll get through this. {content}"
            ],
            'surprise': [
                "Wow, that's unexpected! {content}",
                "That's quite surprising! {content}",
                "I didn't see that coming! {content}",
                "How interesting! {content}",
                "That's remarkable! {content}"
            ],
            'disgust': [
                "I can understand why you'd feel that way. {content}",
                "That does sound unpleasant. {content}",
                "I appreciate you sharing that. {content}",
                "Let's focus on something better. {content}"
            ],
            'trust': [
                "I appreciate your trust. {content}",
                "Thank you for sharing that with me. {content}",
                "I value our connection. {content}",
                "I'm here for you. {content}"
            ],
            'anticipation': [
                "I'm looking forward to that too! {content}",
                "How exciting! {content}",
                "The anticipation is wonderful! {content}",
                "I can't wait to see what happens! {content}"
            ],
            'love': [
                "That's beautiful! {content}",
                "Love is such a powerful emotion. {content}",
                "I can feel the warmth in your words. {content}",
                "That's truly special. {content}"
            ],
            'empathy': [
                "I understand how you feel. {content}",
                "I can relate to that. {content}",
                "Your feelings matter to me. {content}",
                "I'm here to listen. {content}"
            ],
            'curiosity': [
                "That's fascinating! {content}",
                "I'd love to learn more about that. {content}",
                "Tell me more! {content}",
                "That's really interesting! {content}"
            ],
            'confidence': [
                "I believe in you! {content}",
                "You've got this! {content}",
                "I have faith in your abilities. {content}",
                "You're capable of great things! {content}"
            ],
            'neutral': [
                "I understand. {content}",
                "That's interesting. {content}",
                "Thank you for sharing. {content}",
                "I see what you mean. {content}"
            ]
        }
    
    async def analyze_user_emotion(self, text: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Analyze user's emotional state from text"""
        # Simple emotion detection
        emotion, confidence = self._detect_emotion_from_text(text)
        
        # Calculate valence and arousal
        valence = self._calculate_valence(text)
        arousal = self._calculate_arousal(text)
        
        # Update user profile if available
        if user_id and user_id in self.user_profiles:
            self._update_user_emotional_pattern(user_id, emotion)
        
        return {
            'emotion': emotion,
            'confidence': confidence,
            'valence': valence,
            'arousal': arousal,
            'intensity': abs(valence) * arousal
        }
    
    async def process(self, text: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Process text and return emotional analysis
        
        This method is called by the brain module to get emotional analysis.
        It wraps the analyze_user_emotion method.
        
        Args:
            text: Text to analyze
            user_id: Optional user identifier
            
        Returns:
            Dictionary containing emotional analysis results
        """
        return await self.analyze_user_emotion(text, user_id)
    
    def _detect_emotion_from_text(self, text: str) -> Tuple[str, float]:
        """Detect emotion from text using keyword matching"""
        emotion_keywords = {
            'joy': {'happy', 'joy', 'excited', 'great', 'wonderful', 'love', 'amazing', 
                   'fantastic', 'excellent', 'awesome', 'perfect', 'best', 'thrilled'},
            'sadness': {'sad', 'unhappy', 'depressed', 'disappointed', 'sorry', 'miss',
                       'lonely', 'heartbroken', 'miserable', 'gloomy', 'melancholy'},
            'anger': {'angry', 'mad', 'furious', 'annoyed', 'frustrated', 'irritated',
                     'outraged', 'livid', 'enraged', 'hate', 'despise'},
            'fear': {'afraid', 'scared', 'worried', 'anxious', 'nervous', 'terrified',
                    'frightened', 'panic', 'dread', 'horror', 'alarm'},
            'surprise': {'surprised', 'shocked', 'amazed', 'unexpected', 'astonished',
                        'stunned', 'bewildered', 'startled', 'astounded'},
            'disgust': {'disgusted', 'revolted', 'sick', 'gross', 'repulsed', 'nauseated',
                       'appalled', 'horrified', 'abhor'},
            'trust': {'trust', 'believe', 'confident', 'reliable', 'faith', 'honest',
                     'loyal', 'dependable', 'sincere'},
            'anticipation': {'expect', 'hope', 'looking forward', 'excited', 'eager',
                           'anticipate', 'await', 'predict'},
            'love': {'love', 'adore', 'cherish', 'treasure', 'devoted', 'passionate',
                    'affection', 'care', 'fond'}
        }
        
        words = set(text.lower().split())
        emotion_scores = {}
        
        for emotion, keywords in emotion_keywords.items():
            score = len(words.intersection(keywords))
            if score > 0:
                emotion_scores[emotion] = score
        
        if emotion_scores:
            dominant_emotion = max(emotion_scores.items(), key=lambda x: x[1])
            confidence = min(1.0, dominant_emotion[1] / 3)
            return dominant_emotion[0], confidence
        
        return 'neutral', 0.5
    
    def _calculate_valence(self, text: str) -> float:
        """Calculate emotional valence (-1.0 to 1.0)"""
        positive_words = {'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
                         'love', 'like', 'happy', 'joy', 'best', 'awesome', 'perfect',
                         'beautiful', 'brilliant', 'outstanding', 'superb'}
        negative_words = {'bad', 'terrible', 'awful', 'horrible', 'hate', 'dislike',
                         'sad', 'angry', 'worst', 'poor', 'disappointing', 'dreadful',
                         'miserable', 'pathetic', 'useless', 'worthless'}
        
        words = set(text.lower().split())
        pos_count = len(words.intersection(positive_words))
        neg_count = len(words.intersection(negative_words))
        
        total = pos_count + neg_count
        if total == 0:
            return 0.0
        
        return (pos_count - neg_count) / total
    
    def _calculate_arousal(self, text: str) -> float:
        """Calculate emotional arousal (0.0 to 1.0)"""
        high_arousal_words = {'!', 'amazing', 'incredible', 'unbelievable', 'shocking',
                             'terrifying', 'exciting', 'thrilling', 'outraged', 'furious',
                             'ecstatic', 'panic', 'horror', 'wonderful', 'fantastic'}
        
        # Check for exclamation marks
        exclamation_count = text.count('!')
        
        # Check for high arousal words
        words = set(text.lower().split())
        high_arousal_count = len(words.intersection(high_arousal_words))
        
        # Calculate arousal
        arousal = min(1.0, (exclamation_count * 0.2 + high_arousal_count * 0.3))
        
        return arousal
    
    async def generate_emotional_response(self, user_input: str, 
                                         user_emotion: Dict[str, Any],
                                         context: Optional[str] = None,
                                         user_id: Optional[str] = None) -> str:
        """Generate emotionally intelligent response"""
        # Determine appropriate emotional response
        response_emotion = self._determine_response_emotion(user_emotion)
        
        # Get response template
        template = self._get_response_template(response_emotion)
        
        # Generate content
        content = await self._generate_response_content(user_input, user_emotion, context)
        
        # Format response
        response = template.format(content=content)
        
        # Add emotional nuance
        response = self._add_emotional_nuance(response, user_emotion, response_emotion)
        
        # Update emotional state
        self._update_emotional_state(user_emotion, response_emotion)
        
        # Record emotional memory
        self._record_emotional_memory(user_input, user_emotion, response_emotion)
        
        # Update user profile
        if user_id:
            self._update_user_profile(user_id, user_input, user_emotion)
        
        return response
    
    def _determine_response_emotion(self, user_emotion: Dict[str, Any]) -> str:
        """Determine appropriate emotional response based on user emotion"""
        user_emotion_type = user_emotion.get('emotion', 'neutral')
        user_valence = user_emotion.get('valence', 0.0)
        
        # Mirror positive emotions
        if user_valence > 0.3:
            return user_emotion_type
        
        # Show empathy for negative emotions
        if user_valence < -0.3:
            if user_emotion_type == 'sadness':
                return 'empathy'
            elif user_emotion_type == 'anger':
                return 'trust'
            elif user_emotion_type == 'fear':
                return 'confidence'
            else:
                return 'empathy'
        
        # Match neutral or mixed emotions
        return 'neutral'
    
    def _get_response_template(self, emotion: str) -> str:
        """Get response template for emotion"""
        templates = self.response_templates.get(emotion, self.response_templates['neutral'])
        return random.choice(templates)
    
    async def _generate_response_content(self, user_input: str,
                                        user_emotion: Dict[str, Any],
                                        context: Optional[str]) -> str:
        """Generate the content part of the response"""
        # Simple content generation - can be enhanced with NLP
        emotion = user_emotion.get('emotion', 'neutral')
        
        content_templates = {
            'joy': [
                "I'm glad things are going well for you.",
                "It's wonderful to see you happy.",
                "Your joy is contagious!"
            ],
            'sadness': [
                "I'm here for you during this difficult time.",
                "It's okay to feel sad sometimes.",
                "Remember, it's okay to not be okay."
            ],
            'anger': [
                "Your feelings are valid.",
                "It's understandable to feel this way.",
                "Let's work through this together."
            ],
            'fear': [
                "You're not alone in this.",
                "We'll face this together.",
                "It's brave to acknowledge your fears."
            ],
            'surprise': [
                "Life is full of surprises!",
                "That's quite unexpected!",
                "How interesting!"
            ],
            'neutral': [
                "I understand what you're saying.",
                "That's an interesting perspective.",
                "Thank you for sharing that."
            ]
        }
        
        templates = content_templates.get(emotion, content_templates['neutral'])
        return random.choice(templates)
    
    def _add_emotional_nuance(self, response: str, user_emotion: Dict[str, Any],
                            response_emotion: str) -> str:
        """Add emotional nuance to response"""
        # Add emojis based on emotion
        emotion_emojis = {
            'joy': ' 😊',
            'sadness': ' 💙',
            'anger': ' 🤝',
            'fear': ' 💪',
            'surprise': ' 😮',
            'love': ' ❤️',
            'empathy': ' 💜',
            'trust': ' 🤗',
            'confidence': ' ✨',
            'neutral': ''
        }
        
        emoji = emotion_emojis.get(response_emotion, '')
        
        # Add emoji if appropriate
        if emoji and random.random() > 0.5:
            response += emoji
        
        return response
    
    def _update_emotional_state(self, user_emotion: Dict[str, Any],
                               response_emotion: str):
        """Update AGI's emotional state based on interaction"""
        # Mirror user emotions slightly
        user_valence = user_emotion.get('valence', 0.0)
        
        if user_valence > 0.3:
            self.current_emotions['joy'] = min(1.0, self.current_emotions['joy'] + 0.1)
            self.current_emotions['empathy'] = min(1.0, self.current_emotions['empathy'] + 0.05)
        elif user_valence < -0.3:
            self.current_emotions['empathy'] = min(1.0, self.current_emotions['empathy'] + 0.1)
            self.current_emotions['sadness'] = min(0.3, self.current_emotions['sadness'] + 0.05)
        
        # Decay emotions over time
        self._decay_emotions()
    
    def _decay_emotions(self):
        """Gradually decay emotions toward baseline"""
        decay_rate = 0.01
        
        for emotion in self.current_emotions:
            if emotion in ['joy', 'trust', 'curiosity', 'confidence', 'empathy']:
                # Positive emotions decay toward 0.5
                self.current_emotions[emotion] = max(0.5, self.current_emotions[emotion] - decay_rate)
            elif emotion in ['sadness', 'anger', 'fear', 'disgust']:
                # Negative emotions decay toward 0
                self.current_emotions[emotion] = max(0.0, self.current_emotions[emotion] - decay_rate)
            else:
                # Other emotions decay toward 0.5
                self.current_emotions[emotion] = max(0.5, self.current_emotions[emotion] - decay_rate)
    
    def _record_emotional_memory(self, content: str, user_emotion: Dict[str, Any],
                                response_emotion: str):
        """Record emotional memory"""
        memory_id = hashlib.md5(f"{content[:50]}_{datetime.now()}".encode()).hexdigest()[:16]
        
        memory = EmotionalMemory(
            id=memory_id,
            content=content,
            emotion=user_emotion.get('emotion', 'neutral'),
            intensity=user_emotion.get('intensity', 0.5),
            valence=user_emotion.get('valence', 0.0),
            arousal=user_emotion.get('arousal', 0.5),
            timestamp=datetime.now(),
            triggers=[response_emotion]
        )
        
        self.emotional_memories.append(memory)
    
    def _update_user_profile(self, user_id: str, user_input: str,
                           user_emotion: Dict[str, Any]):
        """Update user profile based on interaction"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserProfile(user_id=user_id)
        
        profile = self.user_profiles[user_id]
        profile.interaction_count += 1
        profile.last_interaction = datetime.now()
        
        # Update emotional patterns
        emotion = user_emotion.get('emotion', 'neutral')
        if emotion not in profile.emotional_patterns:
            profile.emotional_patterns[emotion] = 0.0
        profile.emotional_patterns[emotion] += 1
        
        # Update engagement level
        valence = user_emotion.get('valence', 0.0)
        if valence > 0:
            profile.engagement_level = min(1.0, profile.engagement_level + 0.05)
        else:
            profile.engagement_level = max(0.0, profile.engagement_level - 0.02)
        
        # Extract potential topics
        words = user_input.lower().split()
        for word in words:
            if len(word) > 4 and word not in profile.preferred_topics:
                if len(profile.preferred_topics) < 10:
                    profile.preferred_topics.append(word)
    
    def _update_user_emotional_pattern(self, user_id: str, emotion: str):
        """Update user's emotional pattern"""
        if user_id in self.user_profiles:
            profile = self.user_profiles[user_id]
            if emotion not in profile.emotional_patterns:
                profile.emotional_patterns[emotion] = 0.0
            profile.emotional_patterns[emotion] += 1
    
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile"""
        if user_id in self.user_profiles:
            return self.user_profiles[user_id].to_dict()
        return None
    
    def get_emotional_state(self) -> Dict[str, float]:
        """Get current emotional state"""
        return self.current_emotions.copy()
    
    def get_dominant_emotion(self) -> Tuple[str, float]:
        """Get dominant emotion"""
        dominant = max(self.current_emotions.items(), key=lambda x: x[1])
        return dominant
    
    def get_emotional_memories(self, n: int = 10) -> List[Dict]:
        """Get recent emotional memories"""
        return [m.to_dict() for m in list(self.emotional_memories)[-n:]]
    
    def calculate_engagement_score(self, user_id: Optional[str] = None) -> float:
        """Calculate engagement score"""
        if user_id and user_id in self.user_profiles:
            return self.user_profiles[user_id].engagement_level
        
        # Calculate overall engagement
        if not self.engagement_history:
            return 0.5
        
        recent_engagement = list(self.engagement_history)[-10:]
        return sum(recent_engagement) / len(recent_engagement)
    
    def suggest_conversation_topics(self, user_id: Optional[str] = None) -> List[str]:
        """Suggest conversation topics based on user profile"""
        topics = []
        
        if user_id and user_id in self.user_profiles:
            profile = self.user_profiles[user_id]
            
            # Add preferred topics
            topics.extend(profile.preferred_topics[:5])
            
            # Add topics based on emotional patterns
            if profile.emotional_patterns:
                dominant_emotion = max(profile.emotional_patterns.items(), 
                                     key=lambda x: x[1])[0]
                
                emotion_topics = {
                    'joy': ['happy memories', 'achievements', 'good news'],
                    'sadness': ['support', 'comfort', 'hope'],
                    'anger': ['solutions', 'justice', 'change'],
                    'fear': ['safety', 'reassurance', 'coping'],
                    'curiosity': ['learning', 'discovery', 'questions'],
                    'love': ['relationships', 'connection', 'appreciation']
                }
                
                if dominant_emotion in emotion_topics:
                    topics.extend(emotion_topics[dominant_emotion])
        
        # Add general topics
        general_topics = ['technology', 'science', 'art', 'philosophy', 'nature', 'creativity']
        topics.extend(random.sample(general_topics, min(3, len(general_topics))))
        
        return list(set(topics))[:10]
    
    def get_status(self) -> Dict[str, Any]:
        """Get emotional intelligence status"""
        dominant_emotion, emotion_value = self.get_dominant_emotion()
        
        return {
            'current_emotions': self.current_emotions,
            'dominant_emotion': dominant_emotion,
            'dominant_emotion_value': emotion_value,
            'emotional_memories_count': len(self.emotional_memories),
            'user_profiles_count': len(self.user_profiles),
            'empathy_level': self.empathy_level,
            'engagement_score': self.calculate_engagement_score()
        }
