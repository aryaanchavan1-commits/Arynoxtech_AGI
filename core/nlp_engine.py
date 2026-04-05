"""
Arynoxtech_AGI NLP Engine
Transformer-based Natural Language Processing and Conversation
"""

import logging
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """Represents a single turn in conversation"""
    id: str
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    emotion: Optional[str] = None
    sentiment: Optional[float] = None
    entities: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'emotion': self.emotion,
            'sentiment': self.sentiment,
            'entities': self.entities,
            'metadata': self.metadata
        }


@dataclass
class NLPAnalysis:
    """Results of NLP analysis"""
    text: str
    sentiment: float  # -1.0 to 1.0
    emotion: str
    emotion_confidence: float
    entities: List[Dict[str, str]]
    keywords: List[str]
    summary: Optional[str] = None
    language: str = 'en'
    complexity: float = 0.5
    
    def to_dict(self) -> Dict:
        return {
            'text': self.text[:200],
            'sentiment': self.sentiment,
            'emotion': self.emotion,
            'emotion_confidence': self.emotion_confidence,
            'entities': self.entities,
            'keywords': self.keywords,
            'summary': self.summary,
            'language': self.language,
            'complexity': self.complexity
        }


class NLPEngine:
    """
    NLP Engine with Transformer models and LLM integration
    Handles conversation, sentiment analysis, entity extraction, etc.
    """
    
    def __init__(self, config: Optional[Dict] = None, data_ingestion=None, llm_engine=None):
        import threading
        
        self.config = config or {}
        self.data_ingestion = data_ingestion
        self.llm_engine = llm_engine
        
        # Model configurations
        self.models = {
            'conversation': self.config.get('conversation_model', 'microsoft/DialoGPT-medium'),
            'emotion': self.config.get('emotion_model', 'j-hartmann/emotion-english-distilroberta-base'),
            'sentiment': self.config.get('sentiment_model', 'nlptown/bert-base-multilingual-uncased-sentiment'),
            'ner': self.config.get('ner_model', 'dbmdz/bert-large-cased-finetuned-conll03-english'),
            'summarization': self.config.get('summarization_model', 'facebook/bart-large-cnn'),
            'qa': self.config.get('qa_model', 'deepset/roberta-base-squad2')
        }
        
        # Loaded models (lazy loading)
        self._loaded_models = {}
        self._tokenizers = {}
        
        # Preload settings
        self.preload_models = self.config.get('preload_models', ['sentiment', 'emotion'])
        self.models_preloaded = False
        
        # Conversation history
        self.conversation_history: List[ConversationTurn] = []
        self.max_history = self.config.get('max_history', 50)
        
        # Thread safety locks
        self._nltk_lock = threading.Lock()
        self._model_lock = threading.Lock()
        
        # Initialize basic NLP tools (non-blocking)
        self._init_basic_nlp()
        
        logger.info("NLP Engine initialized - models will be loaded on first use")
    
    def _init_basic_nlp(self):
        """Initialize basic NLP tools that don't require heavy models"""
        self.nltk_available = False
        self._nltk_initialized = False
        self._nltk_import_started = False
        
        # COMPLETELY avoid NLTK import at init time - do NOT import anything here
        # NLTK will be fully initialized lazily when first needed, with timeout protection
        logger.info("NLTK will be initialized lazily when needed (no import at startup)")
    
    def _ensure_nltk_initialized(self):
        """Lazy initialization of NLTK with non-blocking timeout and thread safety"""
        # Fast path
        if self._nltk_initialized:
            return
        
        # Use lock to prevent multiple threads from trying to initialize simultaneously
        with self._nltk_lock:
            # Double-check inside lock
            if self._nltk_initialized:
                return
            
            # Prevent multiple concurrent initialization attempts
            if hasattr(self, '_nltk_import_started') and self._nltk_import_started:
                # Already initializing, use fallback for now
                logger.debug("NLTK initialization in progress, using fallback")
                return
                
            self._nltk_import_started = True
            
            try:
                # Use threading with timeout to avoid blocking main thread
                import threading
                import queue
                import sys
                
                result_queue = queue.Queue()
                
                def import_nltk_worker():
                    try:
                        import nltk
                        # Download required data if not present
                        try:
                            nltk.data.find('tokenizers/punkt')
                        except LookupError:
                            nltk.download('punkt', quiet=True)
                        try:
                            nltk.data.find('corpora/stopwords')
                        except LookupError:
                            nltk.download('stopwords', quiet=True)
                        try:
                            nltk.data.find('taggers/averaged_perceptron_tagger')
                        except LookupError:
                            nltk.download('averaged_perceptron_tagger', quiet=True)
                        
                        result_queue.put(('success', None))
                    except Exception as e:
                        result_queue.put(('error', str(e)))
                
                # Start import in separate thread
                thread = threading.Thread(target=import_nltk_worker, daemon=True)
                thread.start()
                thread.join(timeout=3)  # 3 second timeout - much faster than 10
                
                if thread.is_alive():
                    logger.warning("NLTK import timed out after 3 seconds - using fallback methods")
                    self.nltk_available = False
                else:
                    try:
                        status, error = result_queue.get_nowait()
                        if status == 'success':
                            self.nltk_available = True
                            self._nltk_initialized = True
                            logger.info("✅ NLTK initialized successfully (non-blocking)")
                        else:
                            logger.warning(f"NLTK initialization failed: {error} - using fallback methods")
                            self.nltk_available = False
                    except queue.Empty:
                        logger.warning("NLTK initialization timeout - using fallback methods")
                        self.nltk_available = False
                        
            except Exception as e:
                logger.warning(f"NLTK setup failed: {e} - using fallback methods")
                self.nltk_available = False
            finally:
                self._nltk_import_started = False
    
    async def load_model(self, model_name: str):
        """Lazy load a model when needed"""
        if model_name in self._loaded_models:
            return self._loaded_models[model_name]
        
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
            import torch
            
            logger.info(f"Loading model: {model_name}")
            
            # Load tokenizer
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            self._tokenizers[model_name] = tokenizer
            
            # Load model based on type
            if 'DialoGPT' in model_name or 'conversation' in model_name.lower():
                model = AutoModelForCausalLM.from_pretrained(model_name)
                self._loaded_models[model_name] = {
                    'model': model,
                    'tokenizer': tokenizer,
                    'type': 'conversation'
                }
            else:
                # Use pipeline for other models
                task = self._get_task_for_model(model_name)
                # Cast to Any to bypass strict type checking for dynamic pipeline tasks
                from typing import cast
                pipe = pipeline(cast(Any, task), model=model_name)
                self._loaded_models[model_name] = {
                    'pipeline': pipe,
                    'type': task
                }
            
            logger.info(f"Model loaded successfully: {model_name}")
            return self._loaded_models[model_name]
            
        except Exception as e:
            logger.error(f"Error loading model {model_name}: {e}")
            return None
    
    def _get_task_for_model(self, model_name: str) -> str:
        """Determine the task type for a model"""
        model_lower = model_name.lower()
        
        if 'emotion' in model_lower:
            return 'text-classification'
        elif 'sentiment' in model_lower:
            return 'sentiment-analysis'
        elif 'ner' in model_lower or 'conll' in model_lower:
            return 'ner'
        elif 'summarization' in model_lower or 'bart' in model_lower:
            return 'summarization'
        elif 'qa' in model_lower or 'squad' in model_lower:
            return 'question-answering'
        else:
            return 'text-generation'
    
    async def analyze_text(self, text: str) -> NLPAnalysis:
        """Perform comprehensive NLP analysis on text"""
        # Sentiment analysis
        sentiment = await self._analyze_sentiment(text)
        
        # Emotion detection
        emotion, emotion_confidence = await self._detect_emotion(text)
        
        # Entity extraction
        entities = await self._extract_entities(text)
        
        # Keyword extraction
        keywords = self._extract_keywords(text)
        
        # Complexity analysis
        complexity = self._analyze_complexity(text)
        
        return NLPAnalysis(
            text=text,
            sentiment=sentiment,
            emotion=emotion,
            emotion_confidence=emotion_confidence,
            entities=entities,
            keywords=keywords,
            complexity=complexity
        )
    
    async def process(self, text: str) -> Dict[str, Any]:
        """Process text and return NLP analysis as dictionary
        
        This method is called by the brain module to get NLP analysis.
        It wraps the analyze_text method and returns a dictionary.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary containing NLP analysis results
        """
        analysis = await self.analyze_text(text)
        return analysis.to_dict()
    
    async def _analyze_sentiment(self, text: str) -> float:
        """Analyze sentiment of text"""
        try:
            model_info = await self.load_model(self.models['sentiment'])
            if model_info and 'pipeline' in model_info:
                result = model_info['pipeline'](text[:512])
                
                # Convert to -1 to 1 scale
                label = result[0]['label']
                score = result[0]['score']
                
                # Parse label (e.g., "5 stars" -> 5)
                if 'star' in label.lower():
                    stars = int(label[0])
                    return (stars - 3) / 2  # Convert 1-5 to -1 to 1
                elif 'positive' in label.lower():
                    return score
                elif 'negative' in label.lower():
                    return -score
                else:
                    return 0.0
            else:
                # Fallback to simple sentiment
                return self._simple_sentiment(text)
                
        except Exception as e:
            logger.warning(f"Sentiment analysis failed: {e}")
            return self._simple_sentiment(text)
    
    def _simple_sentiment(self, text: str) -> float:
        """Simple rule-based sentiment analysis"""
        positive_words = {'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 
                         'love', 'like', 'happy', 'joy', 'best', 'awesome', 'perfect'}
        negative_words = {'bad', 'terrible', 'awful', 'horrible', 'hate', 'dislike', 
                         'sad', 'angry', 'worst', 'poor', 'disappointing'}
        
        words = set(text.lower().split())
        pos_count = len(words.intersection(positive_words))
        neg_count = len(words.intersection(negative_words))
        
        total = pos_count + neg_count
        if total == 0:
            return 0.0
        
        return (pos_count - neg_count) / total
    
    async def _detect_emotion(self, text: str) -> Tuple[str, float]:
        """Detect emotion in text"""
        try:
            model_info = await self.load_model(self.models['emotion'])
            if model_info and 'pipeline' in model_info:
                result = model_info['pipeline'](text[:512])
                return result[0]['label'], result[0]['score']
            else:
                return self._simple_emotion(text)
                
        except Exception as e:
            logger.warning(f"Emotion detection failed: {e}")
            return self._simple_emotion(text)
    
    def _simple_emotion(self, text: str) -> Tuple[str, float]:
        """Simple rule-based emotion detection"""
        emotion_keywords = {
            'joy': {'happy', 'joy', 'excited', 'great', 'wonderful', 'love'},
            'sadness': {'sad', 'unhappy', 'depressed', 'disappointed', 'sorry'},
            'anger': {'angry', 'mad', 'furious', 'annoyed', 'frustrated'},
            'fear': {'afraid', 'scared', 'worried', 'anxious', 'nervous'},
            'surprise': {'surprised', 'shocked', 'amazed', 'unexpected'},
            'disgust': {'disgusted', 'revolted', 'sick', 'gross'},
            'trust': {'trust', 'believe', 'confident', 'reliable'},
            'anticipation': {'expect', 'hope', 'looking forward', 'excited'}
        }
        
        words = set(text.lower().split())
        emotion_scores = {}
        
        for emotion, keywords in emotion_keywords.items():
            score = len(words.intersection(keywords))
            if score > 0:
                emotion_scores[emotion] = score
        
        if emotion_scores:
            dominant_emotion = max(emotion_scores.items(), key=lambda x: x[1])
            return dominant_emotion[0], min(1.0, dominant_emotion[1] / 3)
        
        return 'neutral', 0.5
    
    async def _extract_entities(self, text: str) -> List[Dict[str, str]]:
        """Extract named entities from text"""
        try:
            model_info = await self.load_model(self.models['ner'])
            if model_info and 'pipeline' in model_info:
                results = model_info['pipeline'](text[:512])
                
                entities = []
                for result in results:
                    entities.append({
                        'text': result['word'],
                        'type': result['entity'],
                        'confidence': result['score']
                    })
                
                return entities
            else:
                return self._simple_entity_extraction(text)
                
        except Exception as e:
            logger.warning(f"Entity extraction failed: {e}")
            return self._simple_entity_extraction(text)
    
    def _simple_entity_extraction(self, text: str) -> List[Dict[str, str]]:
        """Simple rule-based entity extraction"""
        entities = []
        
        # Look for capitalized words (potential proper nouns)
        words = text.split()
        for i, word in enumerate(words):
            if word[0].isupper() and len(word) > 2 and word.lower() not in {'the', 'a', 'an', 'is', 'are', 'was', 'were'}:
                # Check if it's part of a multi-word entity
                entity_text = word
                j = i + 1
                while j < len(words) and words[j][0].isupper():
                    entity_text += " " + words[j]
                    j += 1
                
                entities.append({
                    'text': entity_text,
                    'type': 'PROPER_NOUN',
                    'confidence': 0.7
                })
        
        return entities[:10]  # Limit to 10 entities
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        try:
            # Ensure NLTK is initialized if needed
            self._ensure_nltk_initialized()
            
            if self.nltk_available:
                from nltk.corpus import stopwords
                from nltk.tokenize import word_tokenize
                
                stop_words = set(stopwords.words('english'))
                words = word_tokenize(text.lower())
                
                # Filter out stop words and short words
                keywords = [word for word in words if word.isalnum() 
                           and word not in stop_words and len(word) > 2]
                
                # Count frequency
                from collections import Counter
                word_freq = Counter(keywords)
                
                # Return top keywords
                return [word for word, freq in word_freq.most_common(10)]
            else:
                return self._simple_keyword_extraction(text)
                
        except Exception as e:
            logger.warning(f"Keyword extraction failed: {e}")
            return self._simple_keyword_extraction(text)
    
    def _simple_keyword_extraction(self, text: str) -> List[str]:
        """Simple keyword extraction"""
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 
                     'would', 'could', 'should', 'may', 'might', 'can', 'shall',
                     'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from'}
        
        words = text.lower().split()
        keywords = [word for word in words if word.isalnum() 
                   and word not in stop_words and len(word) > 3]
        
        from collections import Counter
        word_freq = Counter(keywords)
        return [word for word, freq in word_freq.most_common(10)]
    
    def _analyze_complexity(self, text: str) -> float:
        """Analyze text complexity (0.0 to 1.0)"""
        words = text.split()
        sentences = text.split('.')
        
        if not words or not sentences:
            return 0.5
        
        # Average word length
        avg_word_length = sum(len(word) for word in words) / len(words)
        
        # Average sentence length
        avg_sentence_length = len(words) / len(sentences)
        
        # Normalize to 0-1 scale
        complexity = min(1.0, (avg_word_length / 10 + avg_sentence_length / 30) / 2)
        
        return complexity
    
    async def generate_response(self, user_input: str, 
                               context: Optional[str] = None,
                               max_length: int = 200) -> str:
        """Generate a response to user input
        
        This method uses a hybrid approach:
        1. First tries RAG for factual questions about ingested documents
        2. Falls back to conversational response if no answer found
        """
        try:
            # Analyze user input
            analysis = await self.analyze_text(user_input)
            
            # Add to conversation history
            self._add_to_history('user', user_input, analysis)
            
            # Try RAG first for factual questions
            rag_answer = await self.answer_question_with_rag(user_input)
            
            if rag_answer and len(rag_answer) > 10:
                # Use RAG answer if it's substantial
                response = rag_answer
                logger.info(f"Using RAG answer for question: {user_input[:50]}...")
            else:
                # Fall back to conversational response
                response = await self._generate_conversational_response(
                    user_input, analysis, context, max_length
                )
                logger.info(f"Using conversational response for: {user_input[:50]}...")
            
            # Add response to history
            response_analysis = await self.analyze_text(response)
            self._add_to_history('assistant', response, response_analysis)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return self._fallback_response(user_input)
    
    async def _generate_conversational_response(self, user_input: str,
                                               analysis: NLPAnalysis,
                                               context: Optional[str],
                                               max_length: int) -> str:
        """Generate conversational response using available methods"""
        try:
            # Try using DialoGPT if available
            model_info = await self.load_model(self.models['conversation'])
            if model_info and model_info.get('type') == 'conversation':
                return await self._generate_with_dialogpt(user_input, max_length)
            
            # Fallback to template-based response
            return self._generate_template_response(user_input, analysis)
            
        except Exception as e:
            logger.warning(f"Conversational generation failed: {e}")
            return self._generate_template_response(user_input, analysis)
    
    async def _generate_with_dialogpt(self, user_input: str, max_length: int) -> str:
        """Generate response using DialoGPT"""
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            model_info = self._loaded_models.get(self.models['conversation'])
            if not model_info:
                return self._fallback_response(user_input)
            
            model = model_info['model']
            tokenizer = model_info['tokenizer']
            
            # Encode user input
            input_ids = tokenizer.encode(user_input + tokenizer.eos_token, return_tensors='pt')
            
            # Generate response
            with torch.no_grad():
                output = model.generate(
                    input_ids,
                    max_length=max_length,
                    num_return_sequences=1,
                    no_repeat_ngram_size=2,
                    do_sample=True,
                    top_k=50,
                    top_p=0.95,
                    temperature=0.7
                )
            
            # Decode response
            response = tokenizer.decode(output[0], skip_special_tokens=True)
            
            # Remove user input from response
            response = response[len(user_input):].strip()
            
            return response if response else self._fallback_response(user_input)
            
        except Exception as e:
            logger.error(f"DialoGPT generation failed: {e}")
            return self._fallback_response(user_input)
    
    def _generate_template_response(self, user_input: str, analysis: NLPAnalysis) -> str:
        """Generate response using templates"""
        # Emotional responses
        emotion_responses = {
            'joy': [
                "I'm glad to hear that! ",
                "That's wonderful! ",
                "How exciting! "
            ],
            'sadness': [
                "I'm sorry to hear that. ",
                "That sounds difficult. ",
                "I understand how you feel. "
            ],
            'anger': [
                "I can see why you'd feel that way. ",
                "That does sound frustrating. ",
                "I understand your frustration. "
            ],
            'fear': [
                "It's okay to feel worried. ",
                "I understand your concern. ",
                "Let's work through this together. "
            ],
            'surprise': [
                "Wow, that's unexpected! ",
                "That's quite surprising! ",
                "I didn't see that coming! "
            ]
        }
        
        # Get emotional prefix
        emotion_prefix = ""
        if analysis.emotion in emotion_responses:
            import random
            emotion_prefix = random.choice(emotion_responses[analysis.emotion])
        
        # Generate content-based response
        if '?' in user_input:
            # Question
            response = f"{emotion_prefix}That's an interesting question. "
            response += "Let me think about that... "
            response += f"Based on my understanding, I'd say that {self._generate_answer(user_input)}"
        else:
            # Statement
            response = f"{emotion_prefix}I understand. "
            response += f"That's a good point about {analysis.keywords[0] if analysis.keywords else 'that topic'}. "
            response += "Tell me more about what you think."
        
        return response
    
    def _generate_answer(self, question: str) -> str:
        """Generate an answer to a question"""
        # Simple answer generation - can be enhanced with QA model
        question_lower = question.lower()
        
        if 'what' in question_lower:
            return "it depends on the context and specific details."
        elif 'why' in question_lower:
            return "there are several factors that contribute to this."
        elif 'how' in question_lower:
            return "it involves a process that requires careful consideration."
        elif 'when' in question_lower:
            return "timing is important and depends on various factors."
        elif 'where' in question_lower:
            return "location plays a key role in this context."
        else:
            return "it's a complex topic with multiple perspectives."
    
    def _fallback_response(self, user_input: str) -> str:
        """Fallback response when all else fails"""
        fallbacks = [
            "That's an interesting point. Could you tell me more?",
            "I'm processing what you said. Can you elaborate?",
            "I find that fascinating. What else do you think about it?",
            "Thank you for sharing that with me. I'm learning from our conversation.",
            "That gives me something to think about. Please continue."
        ]
        
        import random
        return random.choice(fallbacks)
    
    def _add_to_history(self, role: str, content: str, analysis: Optional[NLPAnalysis] = None):
        """Add a turn to conversation history"""
        turn_id = hashlib.md5(f"{role}_{content[:50]}_{datetime.now()}".encode()).hexdigest()[:16]
        
        turn = ConversationTurn(
            id=turn_id,
            role=role,
            content=content,
            timestamp=datetime.now(),
            emotion=analysis.emotion if analysis else None,
            sentiment=analysis.sentiment if analysis else None,
            entities=analysis.entities if analysis else []
        )
        
        self.conversation_history.append(turn)
        
        # Trim history if needed
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
    
    def get_conversation_history(self, n: int = 10) -> List[Dict]:
        """Get recent conversation history"""
        return [turn.to_dict() for turn in self.conversation_history[-n:]]
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary of conversation"""
        if not self.conversation_history:
            return {'turns': 0, 'summary': 'No conversation yet'}
        
        user_turns = [t for t in self.conversation_history if t.role == 'user']
        assistant_turns = [t for t in self.conversation_history if t.role == 'assistant']
        
        # Calculate average sentiment
        sentiments = [t.sentiment for t in self.conversation_history if t.sentiment is not None]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0
        
        # Get dominant emotion
        emotions = [t.emotion for t in self.conversation_history if t.emotion]
        from collections import Counter
        emotion_counts = Counter(emotions)
        dominant_emotion = emotion_counts.most_common(1)[0][0] if emotions else 'neutral'
        
        return {
            'total_turns': len(self.conversation_history),
            'user_turns': len(user_turns),
            'assistant_turns': len(assistant_turns),
            'average_sentiment': avg_sentiment,
            'dominant_emotion': dominant_emotion,
            'duration_minutes': (self.conversation_history[-1].timestamp - 
                               self.conversation_history[0].timestamp).total_seconds() / 60
        }
    
    async def summarize_text(self, text: str, max_length: int = 150) -> str:
        """Summarize text"""
        try:
            model_info = await self.load_model(self.models['summarization'])
            if model_info and 'pipeline' in model_info:
                result = model_info['pipeline'](text[:1024], max_length=max_length, 
                                               min_length=30, do_sample=False)
                return result[0]['summary_text']
            else:
                return self._simple_summarize(text)
                
        except Exception as e:
            logger.warning(f"Summarization failed: {e}")
            return self._simple_summarize(text)
    
    def _simple_summarize(self, text: str) -> str:
        """Simple extractive summarization"""
        sentences = text.split('.')
        
        if len(sentences) <= 3:
            return text
        
        # Return first 3 sentences as summary
        return '. '.join(sentences[:3]) + '.'
    
    async def answer_question(self, question: str, context: str) -> str:
        """Answer a question given context"""
        try:
            model_info = await self.load_model(self.models['qa'])
            if model_info and 'pipeline' in model_info:
                result = model_info['pipeline'](question=question, context=context[:2000])
                return result['answer']
            else:
                return self._simple_qa(question, context)
                
        except Exception as e:
            logger.warning(f"Question answering failed: {e}")
            return self._simple_qa(question, context)
    
    def _simple_qa(self, question: str, context: str) -> str:
        """Simple keyword-based question answering"""
        question_words = set(question.lower().split())
        context_sentences = context.split('.')
        
        # Find sentence with most question word overlap
        best_sentence = ""
        best_score = 0
        
        for sentence in context_sentences:
            sentence_words = set(sentence.lower().split())
            score = len(question_words.intersection(sentence_words))
            if score > best_score:
                best_score = score
                best_sentence = sentence
        
        return best_sentence.strip() if best_sentence else "I couldn't find a specific answer in the context."
    
    def get_status(self) -> Dict[str, Any]:
        """Get NLP engine status"""
        return {
            'models_configured': list(self.models.keys()),
            'models_loaded': list(self._loaded_models.keys()),
            'models_preloaded': self.models_preloaded,
            'conversation_history_length': len(self.conversation_history),
            'nltk_available': self.nltk_available
        }

    async def preload_models_async(self):
        """Preload priority models in background for faster first response"""
        if self.models_preloaded:
            return
        
        logger.info("Preloading priority models in background...")
        preload_tasks = []
        
        for model_key in self.preload_models:
            if model_key in self.models:
                # Create task but don't await - run in background
                task = asyncio.create_task(self.load_model(self.models[model_key]))
                preload_tasks.append(task)
        
        if preload_tasks:
            # Wait for all preload tasks to complete (with timeout)
            try:
                await asyncio.wait_for(
                    asyncio.gather(*preload_tasks, return_exceptions=True),
                    timeout=30  # 30 second max preload time
                )
                self.models_preloaded = True
                logger.info(f"✅ Preloaded {len(preload_tasks)} models - ready for instant responses!")
            except asyncio.TimeoutError:
                logger.warning("Model preload timed out - models will load on demand")
            except Exception as e:
                logger.warning(f"Model preload failed: {e} - models will load on demand")
    
    async def search_ingested_data(self, query: str, limit: int = 5) -> List[str]:
        """Search ingested data for relevant context
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of relevant text chunks
        """
        if not self.data_ingestion:
            logger.warning("Data ingestion module not available")
            return []
        
        try:
            # Search through ingested data
            results = self.data_ingestion.search(query, limit=limit)
            
            # Extract relevant chunks
            relevant_chunks = []
            for data in results:
                # Add chunks that contain the query
                for chunk in data.chunks:
                    if query.lower() in chunk.lower():
                        relevant_chunks.append(chunk)
                        if len(relevant_chunks) >= limit:
                            break
                
                if len(relevant_chunks) >= limit:
                    break
            
            # If no exact matches, return first chunks from results
            if not relevant_chunks and results:
                for data in results[:limit]:
                    if data.chunks:
                        relevant_chunks.append(data.chunks[0])
            
            logger.info(f"Found {len(relevant_chunks)} relevant chunks for query: {query[:50]}...")
            return relevant_chunks
            
        except Exception as e:
            logger.error(f"Error searching ingested data: {e}")
            return []
    
    async def answer_question_with_rag(self, question: str, max_context_length: int = 2000) -> str:
        """Answer a question using Retrieval-Augmented Generation (RAG)
        
        This method searches ingested data for relevant context and uses
        the QA model to find the answer.
        
        Args:
            question: Question to answer
            max_context_length: Maximum length of context to use
            
        Returns:
            Answer to the question
        """
        try:
            # Search for relevant context
            relevant_chunks = await self.search_ingested_data(question, limit=3)
            
            if not relevant_chunks:
                logger.info("No relevant context found in ingested data")
                return ""
            
            # Combine chunks into context
            context = "\n\n".join(relevant_chunks)
            if len(context) > max_context_length:
                context = context[:max_context_length]
            
            # Use QA model to find answer
            answer = await self.answer_question(question, context)
            
            logger.info(f"RAG answer generated for question: {question[:50]}...")
            return answer
            
        except Exception as e:
            logger.error(f"Error in RAG question answering: {e}")
            return ""
