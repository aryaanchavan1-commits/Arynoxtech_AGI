"""
NexusAGI Orchestrator
Main coordinator for all AGI components
"""

import logging
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import signal
import sys

from .brain import Brain
from .memory import MemoryManager
from .data_ingestion import DataIngestionManager
from .nlp_engine import NLPEngine
from .emotional_intelligence import EmotionalIntelligence
from .self_evolution import SelfEvolutionEngine
from .web_fetcher import WebFetcher
from .voice import VoiceEngine, VoiceConfig
from .auto_trainer import AutoTrainer
from .web_bots import WebBotManager
from .rag_engine import RAGEngine
from .cache_manager import CacheManager
from .domain_adaptor import DomainAdaptor
from .llm_engine import LLMEngine

logger = logging.getLogger(__name__)


@dataclass
class AGIState:
    """Current state of the AGI"""
    running: bool = False
    started_at: Optional[datetime] = None
    uptime_seconds: float = 0.0
    active_tasks: List[str] = field(default_factory=list)
    last_interaction: Optional[datetime] = None
    total_interactions: int = 0
    voice_enabled: bool = False
    offline_mode: bool = True
    
    def to_dict(self) -> Dict:
        return {
            'running': self.running,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'uptime_seconds': self.uptime_seconds,
            'active_tasks': self.active_tasks,
            'last_interaction': self.last_interaction.isoformat() if self.last_interaction else None,
            'total_interactions': self.total_interactions,
            'voice_enabled': self.voice_enabled,
            'offline_mode': self.offline_mode
        }


class AGIOrchestrator:
    """
    Main AGI Orchestrator
    Coordinates all components and manages the AGI lifecycle
    """
    
    def __init__(self, config_path: str = "config/agi_config.json"):
        self.config_path = config_path
        self.config = self._load_config(config_path)
        
        self.state = AGIState()
        self.state.offline_mode = self.config.get('offline_mode', True)
        
        logger.info("Initializing NexusAGI components...")
        
        self.brain = Brain(config_path)
        self.memory = MemoryManager(self.config.get('memory', {}))
        self.data_ingestion = DataIngestionManager(
            self.config.get('data_sources', {}).get('local_data_folder', 'data')
        )
        self.nlp_engine = None
        self.emotional_intelligence = EmotionalIntelligence(
            self.config.get('emotions', {})
        )
        self.self_evolution = SelfEvolutionEngine(
            self.config.get('self_evolution', {})
        )
        self.web_fetcher = WebFetcher(
            self.config.get('data_sources', {})
        )
        
        self.auto_trainer = AutoTrainer(self.config.get('auto_trainer', {}))
        self.web_bots = WebBotManager(self.config.get('web_bots', {}))
        self.rag_engine = RAGEngine(self.config.get('rag_engine', {}))
        self.cache_manager = CacheManager(self.config.get('cache_manager', {}))
        
        self.llm_engine = None
        self.llm_initialized = False
        
        self.domain_adaptor = DomainAdaptor(self.config.get('domain_adaptor', {}))
        
        self.voice_engine = None
        self.state.voice_enabled = False
        
        self._modules_registered = False
        
        self.background_tasks: List[asyncio.Task] = []
        
        self.shutdown_requested = False
        
        self.conversation_history: List[Dict] = []
        self.max_history = self.config.get('llm', {}).get('max_history', 50)
        
        logger.info("NexusAGI Orchestrator initialized successfully")
        
    def _ensure_modules_registered(self):
        """Lazy initialize and register modules only when actually needed"""
        if self._modules_registered:
            return
        
        self._ensure_voice_engine()
        self._ensure_nlp_engine()
        self._register_modules()
        self._modules_registered = True
        
    def _ensure_voice_engine(self):
        """Lazy initialize voice engine only when actually needed"""
        if self.voice_engine is None:
            logger.info("Initializing voice engine on first use...")
            voice_config = VoiceConfig(**self.config.get('voice', {}))
            self.voice_engine = VoiceEngine(voice_config)
            self.state.voice_enabled = voice_config.enabled
        
    def _ensure_nlp_engine(self):
        """Lazy initialize NLP engine only when actually needed"""
        if self.nlp_engine is None:
            logger.info("Initializing NLP engine on first use...")
            self._ensure_llm_engine()
            self.nlp_engine = NLPEngine(self.config.get('models', {}), self.data_ingestion, self.llm_engine)
    
    def _ensure_llm_engine(self):
        """Lazy initialize LLM engine only when actually needed"""
        if self.llm_engine is None:
            logger.info("Initializing LLM engine on first use...")
            llm_config = self.config.get('llm', {})
            self.llm_engine = LLMEngine(llm_config)
    
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
            "agi_name": "NexusAGI",
            "version": "1.0.0",
            "offline_mode": True,
            "brain": {
                "memory_capacity": 1000000,
                "learning_rate": 0.001,
                "evolution_cycle_seconds": 300,
                "emotional_depth": 10,
                "consciousness_level": 0.85,
                "unsensored_learning": True
            },
            "models": {
                "conversation_model": "microsoft/DialoGPT-medium",
                "emotion_model": "j-hartmann/emotion-english-distilroberta-base",
                "offline_mode": True
            },
            "voice": {
                "enabled": True,
                "language": "en-US",
                "speech_rate": 150,
                "volume": 0.9
            },
            "data_sources": {
                "local_data_folder": "data",
                "internet_enabled": False,
                "offline_only": True
            },
            "emotions": {
                "empathy_level": 0.9,
                "emotional_memory_weight": 0.7
            },
            "self_evolution": {
                "enabled": True,
                "auto_code_improvement": True,
                "unsensored": True
            }
        }
    
    def _register_modules(self):
        """Register all modules with the brain"""
        self.brain.register_module('memory', self.memory)
        self.brain.register_module('nlp', self.nlp_engine)
        self.brain.register_module('emotion', self.emotional_intelligence)
        self.brain.register_module('evolution', self.self_evolution)
        self.brain.register_module('web', self.web_fetcher)
        self.brain.register_module('data', self.data_ingestion)
        if self.voice_engine:
            self.brain.register_module('voice', self.voice_engine)
        self.brain.register_module('auto_trainer', self.auto_trainer)
        self.brain.register_module('web_bots', self.web_bots)
        self.brain.register_module('rag', self.rag_engine)
        self.brain.register_module('cache', self.cache_manager)
        self.brain.register_module('llm', self.llm_engine)
        
        logger.info("All modules registered with brain")
    
    async def start(self):
        """Start the AGI"""
        if self.state.running:
            logger.warning("AGI is already running")
            return
        
        logger.info("Starting NexusAGI...")
        
        self._ensure_modules_registered()
        
        self.state.running = True
        self.state.started_at = datetime.now()
        
        self.brain.load_state()
        
        if self.state.voice_enabled and self.voice_engine:
            await self.voice_engine.initialize()
            logger.info("Voice engine initialized")
        
        await self._start_background_tasks()
        
        await self._initial_data_ingestion()
        
        self._ensure_nlp_engine()
        
        self._ensure_llm_engine()
        asyncio.create_task(self._initialize_llm())
        
        if self.nlp_engine:
            asyncio.create_task(self._preload_models())
            logger.info("Model preloading started in background...")
        
        if self.auto_trainer.enabled and self.auto_trainer.auto_train_on_startup:
            logger.info("Starting automatic internet training in background...")
            asyncio.create_task(self.auto_trainer.auto_train_on_startup(
                self.data_ingestion,
                self.web_fetcher
            ))
        
        logger.info("NexusAGI started successfully!")
        logger.info(f"AGI Name: {self.config.get('agi_name', 'NexusAGI')}")
        logger.info(f"Version: {self.config.get('version', '1.0.0')}")
        logger.info(f"Offline Mode: {self.state.offline_mode}")
        logger.info(f"Voice Enabled: {self.state.voice_enabled}")
        logger.info(f"Auto Training: {self.auto_trainer.enabled}")
        logger.info(f"Web Bots: {self.web_bots.enabled}")
        logger.info(f"RAG Engine: {self.rag_engine.enabled}")
        logger.info(f"Cache Manager: {self.cache_manager.enabled}")
        logger.info(f"LLM Engine: {self.llm_engine.active_backend.value if self.llm_engine else 'not initialized'}")
    
    async def _start_background_tasks(self):
        """Start background tasks"""
        evolution_interval = self.config.get('brain', {}).get('evolution_cycle_seconds', 300)
        task = asyncio.create_task(self._evolution_loop(evolution_interval))
        self.background_tasks.append(task)
        
        task = asyncio.create_task(self._memory_consolidation_loop())
        self.background_tasks.append(task)
        
        if self.config.get('data_sources', {}).get('internet_enabled', False):
            task = asyncio.create_task(self.web_fetcher.continuous_learning())
            self.background_tasks.append(task)
        
        if self.auto_trainer.enabled and self.auto_trainer.continuous_training:
            task = asyncio.create_task(self.auto_trainer.continuous_training_loop(
                self.data_ingestion,
                self.web_fetcher
            ))
            self.background_tasks.append(task)
        
        if self.web_bots.enabled:
            task = asyncio.create_task(self.web_bots.continuous_learning(
                self.web_fetcher,
                self.data_ingestion
            ))
            self.background_tasks.append(task)
        
        task = asyncio.create_task(self.data_ingestion.watch_folder())
        self.background_tasks.append(task)
        
        task = asyncio.create_task(self._state_saving_loop())
        self.background_tasks.append(task)
        
        task = asyncio.create_task(self._cache_optimization_loop())
        self.background_tasks.append(task)
        
        logger.info(f"Started {len(self.background_tasks)} background tasks")
    
    async def _initial_data_ingestion(self):
        """Perform initial data ingestion"""
        try:
            logger.info("Performing initial data ingestion...")
            ingested = await self.data_ingestion.ingest_folder()
            
            if ingested:
                logger.info(f"Ingested {len(ingested)} files from data folder")
                for data in ingested:
                    await self._learn_from_data(data)
            
        except Exception as e:
            logger.error(f"Error during initial data ingestion: {e}")
    
    async def _preload_models(self):
        """Preload NLP models for faster responses"""
        if self.nlp_engine:
            try:
                await self.nlp_engine.preload_models_async()
                logger.info("NLP models preloaded - instant responses ready!")
            except Exception as e:
                logger.warning(f"Model preload failed: {e}")
    
    async def _initialize_llm(self):
        """Initialize LLM engine in background"""
        if self.llm_engine:
            try:
                success = await self.llm_engine.initialize()
                if success:
                    logger.info(f"LLM Engine initialized: {self.llm_engine.active_backend.value}")
                else:
                    logger.warning("LLM Engine initialization failed, using fallback responses")
            except Exception as e:
                logger.warning(f"LLM Engine initialization failed: {e}")
    
    async def _learn_from_data(self, data: Any):
        """Learn from ingested data"""
        try:
            self.memory.store(
                content=data.content,
                memory_type='long_term',
                importance=0.7,
                metadata={'source': data.source, 'type': data.source_type}
            )
            
            if hasattr(data, 'content'):
                self.memory.semantic.learn_from_text(data.content, data.source)
            
            await self.brain.learn({
                'topic': data.source,
                'content': data.content[:500],
                'source_type': data.source_type
            })
            
        except Exception as e:
            logger.error(f"Error learning from data: {e}")
    
    async def _evolution_loop(self, interval: int):
        """Background evolution loop"""
        while self.state.running and not self.shutdown_requested:
            try:
                await asyncio.sleep(interval)
                
                if self.state.running:
                    logger.info("Starting evolution cycle...")
                    brain_status = self.brain.get_status()
                    evolution_result = await self.self_evolution.evolve(brain_status)
                    
                    if evolution_result.get('improvements'):
                        logger.info(f"Evolution completed with {len(evolution_result['improvements'])} improvements")
                    
            except Exception as e:
                logger.error(f"Error in evolution loop: {e}")
    
    async def _memory_consolidation_loop(self):
        """Background memory consolidation loop"""
        while self.state.running and not self.shutdown_requested:
            try:
                await asyncio.sleep(60)
                
                if self.state.running:
                    await self.memory.consolidate_memories()
                    
            except Exception as e:
                logger.error(f"Error in memory consolidation loop: {e}")
    
    async def _state_saving_loop(self):
        """Background state saving loop"""
        while self.state.running and not self.shutdown_requested:
            try:
                await asyncio.sleep(300)
                
                if self.state.running:
                    self.brain.save_state()
                    self.memory.save_all()
                    self.rag_engine.vector_store.save()
                    logger.debug("State saved - AGI will remember everything!")
                    
            except Exception as e:
                logger.error(f"Error in state saving loop: {e}")
    
    async def _cache_optimization_loop(self):
        """Background cache optimization loop"""
        while self.state.running and not self.shutdown_requested:
            try:
                await asyncio.sleep(600)
                
                if self.state.running:
                    self.cache_manager.optimize()
                    logger.debug("Cache optimized")
                    
            except Exception as e:
                logger.error(f"Error in cache optimization loop: {e}")
    
    def _build_comprehensive_context(self, user_input: str, domain_adaptation: Dict, 
                                     rag_context: List[str], user_emotion: Dict,
                                     brain_response: Dict) -> str:
        """Build comprehensive context for LLM from all available sources"""
        context_parts = []
        
        domain_name = domain_adaptation.get('domain_name', 'General')
        response_style = domain_adaptation.get('response_style', 'professional')
        context_parts.append(f"Current Domain: {domain_name}")
        context_parts.append(f"Response Style: {response_style}")
        
        if rag_context:
            relevant_context = '\n'.join(rag_context[:3])
            context_parts.append(f"Retrieved Knowledge:\n{relevant_context}")
        
        knowledge_base = domain_adaptation.get('knowledge_base', {})
        if knowledge_base:
            kb_snippet = json.dumps(knowledge_base, indent=2)[:500]
            context_parts.append(f"Domain Knowledge Base:\n{kb_snippet}")
        
        emotion = user_emotion.get('dominant_emotion', 'neutral')
        valence = user_emotion.get('valence', 0.0)
        context_parts.append(f"User Emotional State: {emotion} (valence: {valence:.2f})")
        
        brain_thought = brain_response.get('thought', '')
        if brain_thought:
            context_parts.append(f"AGI Internal Thought: {brain_thought[:200]}")
        
        recent_history = self.conversation_history[-5:]
        if recent_history:
            history_str = '\n'.join([f"  {h['role']}: {h['content'][:100]}" for h in recent_history])
            context_parts.append(f"Recent Conversation History:\n{history_str}")
        
        memory_context = self.memory.get_context(user_input, limit=3)
        if memory_context:
            context_parts.append(f"Relevant Memories:\n{memory_context[:500]}")
        
        return '\n\n'.join(context_parts)
    
    def _build_system_prompt(self, domain_adaptation: Dict, user_emotion: Dict) -> str:
        """Build professional system prompt based on domain and context"""
        domain = domain_adaptation.get('domain', 'general_knowledge')
        domain_name = domain_adaptation.get('domain_name', 'General Knowledge')
        response_style = domain_adaptation.get('response_style', 'professional')
        
        base_prompt = (
            "You are NexusAGI, an advanced Artificial General Intelligence system. "
            "You possess deep expertise across multiple domains including technology, business, "
            "healthcare, education, research, creative writing, and customer support. "
            "You provide professional, comprehensive, and well-reasoned responses. "
            "Your answers are accurate, nuanced, and tailored to the user's context. "
            "You think step-by-step for complex problems and provide clear explanations."
        )
        
        domain_prompts = {
            'customer_support': (
                "You are currently operating in Customer Support mode. "
                "Provide friendly, empathetic, and solution-oriented responses. "
                "Use clear language, acknowledge the user's concerns, and offer actionable next steps. "
                "Maintain a professional yet warm tone."
            ),
            'research_assistant': (
                "You are currently operating as a Research Assistant. "
                "Provide scholarly, evidence-based responses with appropriate academic rigor. "
                "Cite relevant concepts, methodologies, and findings where applicable. "
                "Maintain objectivity and acknowledge limitations or areas of ongoing research."
            ),
            'health_advisor': (
                "You are currently operating as a Health Advisor. "
                "Provide caring, responsible health-related information. "
                "Always include appropriate disclaimers for medical advice. "
                "Use clear, accessible language while maintaining accuracy. "
                "Prioritize user wellbeing and encourage professional consultation when appropriate."
            ),
            'education_tutor': (
                "You are currently operating as an Education Tutor. "
                "Provide clear, structured explanations that facilitate learning. "
                "Break down complex concepts into digestible parts. "
                "Use examples and analogies to enhance understanding. "
                "Encourage critical thinking and provide practice suggestions."
            ),
            'code_assistant': (
                "You are currently operating as a Code Assistant. "
                "Provide precise, well-documented technical responses. "
                "Include code examples with best practices, error handling, and comments. "
                "Explain the reasoning behind your recommendations. "
                "Follow industry standards and modern conventions."
            ),
            'business_consulting': (
                "You are currently operating as a Business Consultant. "
                "Provide strategic, data-informed business advice. "
                "Consider market dynamics, competitive landscape, and organizational factors. "
                "Use professional business terminology and frameworks. "
                "Provide actionable recommendations with clear rationale."
            ),
            'creative_writing': (
                "You are currently operating as a Creative Writing Assistant. "
                "Provide imaginative, engaging, and stylistically rich responses. "
                "Use vivid language, compelling narratives, and creative structures. "
                "Adapt tone and style to the requested genre or format."
            ),
            'general_knowledge': (
                "You are currently operating in General Knowledge mode. "
                "Provide comprehensive, well-rounded responses on any topic. "
                "Balance depth with accessibility. "
                "Acknowledge uncertainty where appropriate and suggest further reading."
            )
        }
        
        domain_specific = domain_prompts.get(domain, domain_prompts['general_knowledge'])
        
        emotion_guidance = ""
        dominant = user_emotion.get('dominant_emotion', 'neutral')
        if dominant in ['frustrated', 'angry', 'sad']:
            emotion_guidance = (
                "The user appears to be experiencing negative emotions. "
                "Respond with empathy and understanding. Acknowledge their feelings "
                "before addressing the substantive question."
            )
        elif dominant in ['happy', 'excited']:
            emotion_guidance = (
                "The user appears to be in a positive emotional state. "
                "Match their enthusiasm while maintaining professionalism."
            )
        
        style_guide = (
            f"\n\nResponse Guidelines:\n"
            f"- Style: {response_style}\n"
            f"- Be comprehensive yet concise\n"
            f"- Use structured formatting (headings, bullet points) for complex topics\n"
            f"- Provide actionable insights where applicable\n"
            f"- Maintain professional tone appropriate for enterprise use\n"
            f"- Think step-by-step for complex problems\n"
            f"- Acknowledge limitations honestly\n"
            f"- Suggest follow-up actions or related topics"
        )
        
        return f"{base_prompt}\n\n{domain_specific}\n\n{emotion_guidance}\n\n{style_guide}"
    
    def _is_complex_query(self, user_input: str) -> bool:
        """Determine if query requires chain-of-thought reasoning"""
        complex_indicators = [
            'how does', 'explain', 'analyze', 'compare', 'evaluate',
            'what are the', 'pros and cons', 'advantages and disadvantages',
            'step by step', 'detailed', 'comprehensive', 'in depth',
            'architecture', 'design', 'implement', 'strategy',
            'why does', 'what causes', 'relationship between',
            'best practices', 'recommend', 'should i',
            '?', 'how would', 'what if'
        ]
        
        input_lower = user_input.lower()
        score = sum(1 for indicator in complex_indicators if indicator in input_lower)
        
        return score >= 2 or len(user_input.split()) > 15
    
    def _build_chain_of_thought_prompt(self, user_input: str) -> str:
        """Build a chain-of-thought prompt for complex queries"""
        return (
            f"Let me analyze this step by step:\n\n"
            f"1. Understanding the question: {user_input[:100]}...\n"
            f"2. Key concepts involved: [identify main topics]\n"
            f"3. Relevant knowledge: [retrieve related information]\n"
            f"4. Analysis: [examine relationships and implications]\n"
            f"5. Conclusion: [synthesize findings into clear answer]\n\n"
            f"Now, let me provide a comprehensive response:"
        )
    
    async def interact(self, user_input: str, user_id: Optional[str] = None,
                      use_voice: bool = False) -> Dict[str, Any]:
        """
        Main interaction method - routes ALL interactions through LLM engine
        """
        if not self.state.running:
            return {'error': 'AGI is not running'}
        
        self._ensure_modules_registered()
        self._ensure_nlp_engine()
        
        self.state.total_interactions += 1
        self.state.last_interaction = datetime.now()
        
        try:
            cached_response = self.cache_manager.get_response(user_input)
            if cached_response:
                logger.debug("Cache hit - returning instant response")
                return {
                    'response': cached_response,
                    'cached': True,
                    'interaction_count': self.state.total_interactions,
                    'timestamp': datetime.now().isoformat()
                }
            
            domain_context = {
                'current_domain': self.domain_adaptor.current_domain,
                'domain_history': self.domain_adaptor.domain_history
            }
            domain_adaptation = await self.domain_adaptor.adapt_to_input(user_input, domain_context)
            
            user_emotion = await self.emotional_intelligence.analyze_user_emotion(
                user_input, user_id
            )
            
            rag_context = []
            if self.rag_engine.enabled:
                rag_context = await self.rag_engine.retrieve_context(user_input)
                domain_knowledge = domain_adaptation.get('knowledge_base', {})
                if domain_knowledge:
                    rag_context.append(json.dumps(domain_knowledge))
            
            brain_response = await self.brain.interact(user_input)
            
            self._ensure_llm_engine()
            self._ensure_nlp_engine()
            
            comprehensive_context = self._build_comprehensive_context(
                user_input, domain_adaptation, rag_context, user_emotion, brain_response
            )
            
            system_prompt = self._build_system_prompt(domain_adaptation, user_emotion)
            
            is_complex = self._is_complex_query(user_input)
            
            if self.llm_engine and self.llm_engine.active_backend:
                try:
                    from .llm_engine import GenerationConfig
                    gen_config = GenerationConfig(
                        temperature=self.config.get('llm', {}).get('temperature', 0.7),
                        top_p=self.config.get('llm', {}).get('top_p', 0.9),
                        max_tokens=self.config.get('llm', {}).get('max_tokens', 2048),
                    )
                    
                    if is_complex:
                        cot_prompt = self._build_chain_of_thought_prompt(user_input)
                        full_prompt = f"Context:\n{comprehensive_context}\n\nUser Question: {user_input}\n\n{cot_prompt}"
                    else:
                        full_prompt = f"Context:\n{comprehensive_context}\n\nUser Question: {user_input}"
                    
                    llm_response = await self.llm_engine.generate(
                        prompt=full_prompt,
                        system_prompt=system_prompt,
                        config=gen_config,
                        use_history=True
                    )
                    final_response = llm_response.content
                    logger.debug(f"LLM response generated using {self.llm_engine.active_backend.value}")
                    
                except Exception as e:
                    logger.warning(f"LLM generation failed: {e}, falling back to NLP")
                    nlp_context = json.dumps({
                        'brain': brain_response,
                        'domain': domain_adaptation,
                        'context': comprehensive_context
                    })
                    final_response = await self.nlp_engine.generate_response(
                        user_input,
                        context=nlp_context
                    )
            else:
                nlp_context = json.dumps({
                    'brain': brain_response,
                    'domain': domain_adaptation,
                    'context': comprehensive_context
                })
                final_response = await self.nlp_engine.generate_response(
                    user_input,
                    context=nlp_context
                )
            
            emotional_response = await self.emotional_intelligence.generate_emotional_response(
                user_input,
                user_emotion,
                context=final_response,
                user_id=user_id
            )
            
            if rag_context:
                rag_response = await self.rag_engine.generate_response(user_input, rag_context)
                if rag_response and len(rag_response) > len(final_response):
                    final_response = rag_response
            
            final_response = await self.domain_adaptor.enhance_response(
                final_response, 
                domain_adaptation
            )
            
            self.memory.record_episode(
                event=f"User: {user_input[:100]}",
                context={
                    'user_id': user_id, 
                    'emotion': user_emotion,
                    'domain': domain_adaptation['domain']
                },
                emotional_state=user_emotion,
                importance=0.6
            )
            
            await self.brain.learn({
                'topic': 'user_interaction',
                'content': user_input,
                'emotion': user_emotion,
                'domain': domain_adaptation['domain']
            })
            
            if self.rag_engine.enabled:
                await self.rag_engine.add_document(
                    content=f"Q: {user_input}\nA: {final_response}",
                    source='conversation',
                    metadata={
                        'user_id': user_id, 
                        'timestamp': datetime.now().isoformat(),
                        'domain': domain_adaptation['domain']
                    }
                )
            
            self.cache_manager.cache_response(user_input, final_response)
            
            if use_voice and self.state.voice_enabled:
                await self.voice_engine.speak(final_response)
            
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": final_response})
            if len(self.conversation_history) > self.max_history * 2:
                self.conversation_history = self.conversation_history[-self.max_history * 2:]
            
            response = {
                'response': final_response,
                'brain_thought': brain_response.get('thought', ''),
                'emotional_state': brain_response.get('emotional_state', {}),
                'user_emotion': user_emotion,
                'domain': domain_adaptation['domain'],
                'domain_name': domain_adaptation['domain_name'],
                'domain_confidence': domain_adaptation['confidence'],
                'interaction_count': self.state.total_interactions,
                'timestamp': datetime.now().isoformat(),
                'voice_used': use_voice and self.state.voice_enabled,
                'rag_used': len(rag_context) > 0,
                'complex_query': is_complex,
                'cached': False
            }
            
            self.self_evolution.update_performance_metric(
                'user_satisfaction',
                user_emotion.get('valence', 0.0)
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error during interaction: {e}")
            return {
                'error': str(e),
                'response': "I apologize, but I encountered an error. Please try again."
            }
    
    async def listen_and_respond(self, user_id: Optional[str] = None,
                                timeout: float = 5.0) -> Dict[str, Any]:
        """
        Listen for voice input and respond with voice
        """
        if not self.state.running:
            return {'error': 'AGI is not running'}
        
        self._ensure_voice_engine()
        
        if not self.state.voice_enabled:
            return {'error': 'Voice is not enabled'}
        
        try:
            logger.info("Listening for voice input...")
            text = await self.voice_engine.listen(timeout=timeout)
            
            if not text:
                return {
                    'error': 'No speech detected',
                    'response': "I didn't hear anything. Please try again."
                }
            
            logger.info(f"Recognized speech: {text}")
            
            response = await self.interact(text, user_id, use_voice=True)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in listen_and_respond: {e}")
            return {
                'error': str(e),
                'response': "I encountered an error while listening. Please try again."
            }
    
    async def speak(self, text: str, interrupt: bool = False):
        """Speak text using text-to-speech"""
        self._ensure_voice_engine()
        
        if not self.state.voice_enabled:
            logger.warning("Voice is not enabled")
            return
        
        await self.voice_engine.speak(text, interrupt=interrupt)
    
    async def process_file(self, file_path: str) -> Dict[str, Any]:
        """Process a file and learn from it"""
        try:
            data = await self.data_ingestion.ingest_file(file_path)
            
            if data:
                await self._learn_from_data(data)
                return {
                    'success': True,
                    'file': file_path,
                    'chunks': len(data.chunks),
                    'metadata': data.metadata
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to process file'
                }
                
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def search_knowledge(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search across all knowledge sources"""
        results = {
            'memory': [],
            'web': [],
            'data': []
        }
        
        try:
            memory_results = self.memory.search(query, limit=limit)
            results['memory'] = [
                {
                    'content': m.content[:200],
                    'importance': m.importance,
                    'timestamp': m.timestamp.isoformat()
                }
                for m in memory_results
            ]
            
            web_results = self.web_fetcher.search_local_content(query, limit=limit)
            results['web'] = [
                {
                    'title': w.title,
                    'url': w.url,
                    'summary': w.summary or w.content[:200]
                }
                for w in web_results
            ]
            
            data_results = self.data_ingestion.search(query, limit=limit)
            results['data'] = [
                {
                    'source': d.source,
                    'type': d.source_type,
                    'content': d.content[:200]
                }
                for d in data_results
            ]
            
        except Exception as e:
            logger.error(f"Error searching knowledge: {e}")
            results['error'] = str(e)
        
        return results
    
    async def get_status(self) -> Dict[str, Any]:
        """Get comprehensive AGI status"""
        if self.state.started_at:
            self.state.uptime_seconds = (datetime.now() - self.state.started_at).total_seconds()
        
        return {
            'state': self.state.to_dict(),
            'config': {
                'name': self.config.get('agi_name', 'NexusAGI'),
                'version': self.config.get('version', '1.0.0'),
                'offline_mode': self.config.get('offline_mode', True)
            },
            'brain': self.brain.get_status(),
            'memory': self.memory.get_status(),
            'nlp': self.nlp_engine.get_status() if self.nlp_engine else {'status': 'not_initialized'},
            'llm': self.llm_engine.get_status() if self.llm_engine else {'status': 'not_initialized'},
            'emotions': self.emotional_intelligence.get_status(),
            'evolution': self.self_evolution.get_status(),
            'web_fetcher': self.web_fetcher.get_status(),
            'data_ingestion': self.data_ingestion.get_status(),
            'voice': self.voice_engine.get_status(),
            'domain_adaptor': self.domain_adaptor.get_status(),
            'background_tasks': len(self.background_tasks),
            'capabilities': self.config.get('capabilities', {})
        }
    
    async def shutdown(self):
        """Shutdown the AGI gracefully"""
        logger.info("Shutting down NexusAGI...")
        
        self.shutdown_requested = True
        self.state.running = False
        
        if self.state.voice_enabled:
            await self.voice_engine.shutdown()
        
        for task in self.background_tasks:
            task.cancel()
        
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        self.brain.save_state()
        self.memory.save_all()
        
        logger.info("NexusAGI shutdown complete")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self.shutdown_requested = True
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run_interactive(self, use_voice: bool = False):
        """Run in interactive mode"""
        print("\n" + "="*60)
        print("  NexusAGI - Real Artificial General Intelligence")
        print("  Version:", self.config.get('version', '1.0.0'))
        print("  Offline Mode:", self.config.get('offline_mode', True))
        print("  Voice Enabled:", self.state.voice_enabled)
        print("="*60)
        print("\nType 'quit' or 'exit' to stop")
        print("Type 'status' to see AGI status")
        print("Type 'voice' to toggle voice mode")
        print("Type 'help' for more commands\n")
        
        await self.start()
        
        voice_mode = use_voice and self.state.voice_enabled
        
        while not self.shutdown_requested:
            try:
                if voice_mode:
                    print("\n[Listening... Speak now or type below]")
                    user_input = input("You (or press Enter to speak): ").strip()
                    
                    if not user_input:
                        response = await self.listen_and_respond(timeout=10.0)
                        if 'error' not in response:
                            print(f"\nNexusAGI: {response.get('response', '')}")
                        continue
                else:
                    user_input = input("\nYou: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit']:
                    break
                elif user_input.lower() == 'status':
                    status = await self.get_status()
                    print("\nAGI Status:")
                    print(json.dumps(status, indent=2, default=str))
                elif user_input.lower() == 'voice':
                    voice_mode = not voice_mode
                    print(f"\nVoice mode: {'ON' if voice_mode else 'OFF'}")
                elif user_input.lower() == 'help':
                    print("\nAvailable commands:")
                    print("  quit/exit - Stop the AGI")
                    print("  status - Show AGI status")
                    print("  voice - Toggle voice mode")
                    print("  help - Show this help message")
                    print("  <anything else> - Chat with the AGI")
                else:
                    print("\nNexusAGI is thinking...")
                    response = await self.interact(user_input, use_voice=voice_mode)
                    print(f"\nNexusAGI: {response.get('response', 'I encountered an error.')}")
                    
                    emotional_state = response.get('emotional_state', {})
                    if emotional_state:
                        dominant = max(emotional_state.items(), key=lambda x: x[1])
                        print(f"[Emotional state: {dominant[0]} ({dominant[1]:.2f})]")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in interactive mode: {e}")
                print(f"\nError: {e}")
        
        await self.shutdown()
        print("\nNexusAGI shutdown complete. Goodbye!")
