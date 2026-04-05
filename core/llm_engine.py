

"""
Arynoxtech_AGI LLM Engine
Multi-backend Large Language Model interface with local and remote support
"""

import logging
import json
import time
import hashlib
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, AsyncGenerator, Union
from dataclasses import dataclass, field
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class ModelBackend(Enum):
    """Supported model backends"""
    TRANSFORMERS = "transformers"
    LLAMA_CPP = "llama_cpp"
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    HYBRID = "hybrid"


class Role(Enum):
    """Message roles"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """A single message in a conversation"""
    role: Role
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        msg = {"role": self.role.value, "content": self.content}
        if self.name:
            msg["name"] = self.name
        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id
        return msg


@dataclass
class TokenUsage:
    """Token usage statistics"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens
        }


@dataclass
class GenerationConfig:
    """Configuration for text generation"""
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    max_tokens: int = 2048
    min_tokens: int = 1
    repetition_penalty: float = 1.1
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    stop_sequences: Optional[List[str]] = None
    seed: Optional[int] = None
    stream: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "max_tokens": self.max_tokens,
            "min_tokens": self.min_tokens,
            "repetition_penalty": self.repetition_penalty,
            "presence_penalty": self.presence_penalty,
            "frequency_penalty": self.frequency_penalty,
            "stop_sequences": self.stop_sequences,
            "seed": self.seed,
            "stream": self.stream
        }


@dataclass
class LLMResponse:
    """Response from the LLM engine"""
    content: str
    model: str
    usage: TokenUsage
    finish_reason: str = "stop"
    generation_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "model": self.model,
            "usage": self.usage.to_dict(),
            "finish_reason": self.finish_reason,
            "generation_time": self.generation_time,
            "metadata": self.metadata
        }


@dataclass
class FunctionDefinition:
    """Definition of a callable function for function calling"""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Optional[Callable] = None
    
    def to_openai_format(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


class TokenCounter:
    """Simple token counter using character/word heuristics"""
    
    @staticmethod
    def count_tokens(text: str, model: str = "default") -> int:
        """Estimate token count using word-based heuristic"""
        if not text:
            return 0
        words = text.split()
        chars = len(text)
        word_tokens = len(words)
        char_tokens = max(1, chars // 4)
        return max(word_tokens, char_tokens)
    
    @staticmethod
    def count_messages_tokens(messages: List[Dict], model: str = "default") -> int:
        """Estimate total tokens for a list of messages"""
        total = 0
        for msg in messages:
            total += TokenCounter.count_tokens(msg.get("content", ""))
            total += 4
        total += 2
        return total


class ResponseValidator:
    """Validates LLM responses for quality"""
    
    @staticmethod
    def validate(response: str, min_length: int = 10, max_length: int = 50000) -> bool:
        if not response or len(response.strip()) < min_length:
            return False
        if len(response) > max_length:
            return False
        return True
    
    @staticmethod
    def check_quality(response: str) -> Dict[str, Any]:
        """Check response quality metrics"""
        words = response.split()
        sentences = response.replace('!', '.').replace('?', '.').split('.')
        sentences = [s.strip() for s in sentences if s.strip()]
        
        avg_sentence_length = len(words) / max(len(sentences), 1)
        
        has_structure = any(char in response for char in ['#', '-', '*', '1.', '2.', '3.'])
        has_examples = any(word in response.lower() for word in ['for example', 'such as', 'e.g.', 'like'])
        has_reasoning = any(word in response.lower() for word in ['because', 'therefore', 'thus', 'consequently', 'as a result'])
        
        quality_score = 0.5
        if 10 < avg_sentence_length < 30:
            quality_score += 0.15
        if has_structure:
            quality_score += 0.1
        if has_examples:
            quality_score += 0.1
        if has_reasoning:
            quality_score += 0.15
        if len(words) > 50:
            quality_score += 0.1
        
        return {
            'word_count': len(words),
            'sentence_count': len(sentences),
            'avg_sentence_length': avg_sentence_length,
            'has_structure': has_structure,
            'has_examples': has_examples,
            'has_reasoning': has_reasoning,
            'quality_score': min(1.0, quality_score)
        }


class BaseLLMBackend:
    """Base class for LLM backends"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_name = config.get("model_name", "default")
        self.initialized = False
    
    async def initialize(self) -> bool:
        raise NotImplementedError
    
    async def generate(
        self,
        messages: List[Dict],
        config: GenerationConfig,
        functions: Optional[List[FunctionDefinition]] = None
    ) -> LLMResponse:
        raise NotImplementedError
    
    async def generate_stream(
        self,
        messages: List[Dict],
        config: GenerationConfig,
        functions: Optional[List[FunctionDefinition]] = None
    ) -> AsyncGenerator[str, None]:
        raise NotImplementedError
    
    def count_tokens(self, text: str) -> int:
        return TokenCounter.count_tokens(text, self.model_name)


class TransformersBackend(BaseLLMBackend):
    """HuggingFace Transformers backend for local models"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self.device = config.get("device", "cpu")
        self.quantize = config.get("quantize", True)
        self.model_path = config.get("model_path", "microsoft/DialoGPT-medium")
    
    async def initialize(self) -> bool:
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
            
            logger.info(f"Loading transformers model: {self.model_path}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            load_kwargs = {
                "torch_dtype": torch.float16 if self.device == "cuda" else torch.float32,
            }
            
            if self.quantize:
                try:
                    from transformers import BitsAndBytesConfig
                    load_kwargs["quantization_config"] = BitsAndBytesConfig(
                        load_in_8bit=True,
                        llm_int8_threshold=6.0
                    )
                except ImportError:
                    logger.warning("bitsandbytes not available, skipping quantization")
            
            if self.device == "cuda":
                load_kwargs["device_map"] = "auto"
            
            self.model = AutoModelForCausalLM.from_pretrained(self.model_path, **load_kwargs)
            self.model.eval()
            
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == "cuda" else -1
            )
            
            self.initialized = True
            logger.info(f"Transformers model loaded: {self.model_path} on {self.device}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load transformers model: {e}")
            return False
    
    async def generate(
        self,
        messages: List[Dict],
        config: GenerationConfig,
        functions: Optional[List[FunctionDefinition]] = None
    ) -> LLMResponse:
        if not self.initialized:
            await self.initialize()
        
        start_time = time.time()
        
        prompt = self._format_messages(messages)
        input_tokens = self.tokenizer.encode(prompt, return_tensors="pt")
        
        if self.device == "cuda":
            input_tokens = input_tokens.to("cuda")
        
        prompt_token_count = input_tokens.shape[1]
        
        with torch.no_grad():
            output = self.pipeline(
                prompt,
                max_new_tokens=min(config.max_tokens, 2048),
                temperature=config.temperature,
                top_p=config.top_p,
                top_k=config.top_k,
                repetition_penalty=config.repetition_penalty,
                do_sample=config.temperature > 0,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        generated_text = output[0]["generated_text"]
        response_text = generated_text[len(prompt):].strip()
        
        output_tokens = self.tokenizer.encode(response_text)
        completion_token_count = len(output_tokens)
        
        generation_time = time.time() - start_time
        
        return LLMResponse(
            content=response_text,
            model=self.model_path,
            usage=TokenUsage(
                prompt_tokens=prompt_token_count,
                completion_tokens=completion_token_count,
                total_tokens=prompt_token_count + completion_token_count
            ),
            finish_reason="stop",
            generation_time=generation_time,
            metadata={"backend": "transformers"}
        )
    
    async def generate_stream(
        self,
        messages: List[Dict],
        config: GenerationConfig,
        functions: Optional[List[FunctionDefinition]] = None
    ) -> AsyncGenerator[str, None]:
        if not self.initialized:
            await self.initialize()
        
        prompt = self._format_messages(messages)
        input_ids = self.tokenizer.encode(prompt, return_tensors="pt")
        
        if self.device == "cuda":
            input_ids = input_ids.to("cuda")
        
        import torch
        
        with torch.no_grad():
            for token_ids in self._generate_tokens_stream(input_ids, config):
                token_text = self.tokenizer.decode(token_ids, skip_special_tokens=True)
                if token_text:
                    yield token_text
    
    def _generate_tokens_stream(self, input_ids, config):
        import torch
        
        max_tokens = min(config.max_tokens, 2048)
        generated = input_ids.clone()
        
        for _ in range(max_tokens):
            with torch.no_grad():
                outputs = self.model(input_ids=generated)
                next_token_logits = outputs.logits[:, -1, :]
                
                if config.temperature > 0:
                    next_token_logits = next_token_logits / config.temperature
                
                probs = torch.softmax(next_token_logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)
                
                generated = torch.cat([generated, next_token], dim=-1)
                
                if next_token.item() == self.tokenizer.eos_token_id:
                    break
                
                yield next_token
    
    def _format_messages(self, messages: List[Dict]) -> str:
        formatted = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                formatted += f"System: {content}\n"
            elif role == "user":
                formatted += f"User: {content}\n"
            elif role == "assistant":
                formatted += f"Assistant: {content}\n"
        formatted += "Assistant: "
        return formatted


class OllamaBackend(BaseLLMBackend):
    """Ollama backend for local model serving"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.model_name = config.get("model_name", "llama3.2")
    
    async def initialize(self) -> bool:
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        self.initialized = True
                        logger.info(f"Ollama connected: {self.base_url}")
                        return True
            logger.warning("Ollama server not responding")
            return False
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False
    
    async def generate(
        self,
        messages: List[Dict],
        config: GenerationConfig,
        functions: Optional[List[FunctionDefinition]] = None
    ) -> LLMResponse:
        if not self.initialized:
            if not await self.initialize():
                return LLMResponse(
                    content="Ollama server is not available.",
                    model=self.model_name,
                    usage=TokenUsage(),
                    finish_reason="error"
                )
        
        import aiohttp
        
        start_time = time.time()
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": config.temperature,
                "top_p": config.top_p,
                "num_predict": config.max_tokens,
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                data = await resp.json()
        
        content = data.get("message", {}).get("content", "")
        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)
        generation_time = time.time() - start_time
        
        return LLMResponse(
            content=content,
            model=self.model_name,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            ),
            finish_reason="stop",
            generation_time=generation_time,
            metadata={"backend": "ollama"}
        )
    
    async def generate_stream(
        self,
        messages: List[Dict],
        config: GenerationConfig,
        functions: Optional[List[FunctionDefinition]] = None
    ) -> AsyncGenerator[str, None]:
        import aiohttp
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": config.temperature,
                "top_p": config.top_p,
                "num_predict": config.max_tokens,
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                async for line in resp.content:
                    if line:
                        try:
                            data = json.loads(line)
                            if "message" in data:
                                content = data["message"].get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue


class OpenAIBackend(BaseLLMBackend):
    """OpenAI API backend"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.model_name = config.get("model_name", "gpt-4o-mini")
        self.client = None
    
    async def initialize(self) -> bool:
        if not self.api_key:
            logger.warning("OpenAI API key not configured")
            return False
        
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            self.initialized = True
            logger.info(f"OpenAI backend initialized: {self.model_name}")
            return True
        except ImportError:
            logger.error("openai package not installed")
            return False
        except Exception as e:
            logger.error(f"OpenAI initialization failed: {e}")
            return False
    
    async def generate(
        self,
        messages: List[Dict],
        config: GenerationConfig,
        functions: Optional[List[FunctionDefinition]] = None
    ) -> LLMResponse:
        if not self.initialized:
            if not await self.initialize():
                return LLMResponse(
                    content="OpenAI API is not configured.",
                    model=self.model_name,
                    usage=TokenUsage(),
                    finish_reason="error"
                )
        
        start_time = time.time()
        
        kwargs = {
            "model": self.model_name,
            "messages": messages,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "max_tokens": config.max_tokens,
            "frequency_penalty": config.frequency_penalty,
            "presence_penalty": config.presence_penalty,
        }
        
        if functions:
            kwargs["tools"] = [f.to_openai_format() for f in functions]
        
        if config.stop_sequences:
            kwargs["stop"] = config.stop_sequences
        
        response = await self.client.chat.completions.create(**kwargs)
        
        content = response.choices[0].message.content or ""
        generation_time = time.time() - start_time
        
        return LLMResponse(
            content=content,
            model=self.model_name,
            usage=TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens
            ),
            finish_reason=response.choices[0].finish_reason or "stop",
            generation_time=generation_time,
            metadata={"backend": "openai"}
        )
    
    async def generate_stream(
        self,
        messages: List[Dict],
        config: GenerationConfig,
        functions: Optional[List[FunctionDefinition]] = None
    ) -> AsyncGenerator[str, None]:
        kwargs = {
            "model": self.model_name,
            "messages": messages,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "max_tokens": config.max_tokens,
            "stream": True,
        }
        
        if functions:
            kwargs["tools"] = [f.to_openai_format() for f in functions]
        
        stream = await self.client.chat.completions.create(**kwargs)
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class AnthropicBackend(BaseLLMBackend):
    """Anthropic Claude API backend - Optional, gracefully handles missing library"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key", "")
        self.model_name = config.get("model_name", "claude-sonnet-4-20250514")
        self.client = None
        self._anthropic_available = False
    
    async def initialize(self) -> bool:
        if not self.api_key:
            logger.warning("Anthropic API key not configured")
            return False
        
        # Check if anthropic library is available
        try:
            # Using importlib to avoid Pylance warnings for optional dependencies
            import importlib
            anthropic_module = importlib.import_module("anthropic")
            self._anthropic_available = True
        except ImportError:
            logger.warning("Anthropic library not installed. Install with: pip install anthropic")
            return False
        
        try:
            # Import AsyncAnthropic for async client
            from anthropic import AsyncAnthropic  # type: ignore
            self.client = AsyncAnthropic(api_key=self.api_key)
            self.initialized = True
            logger.info(f"Anthropic backend initialized: {self.model_name}")
            return True
        except ImportError:
            logger.error("anthropic package not installed")
            return False
        except Exception as e:
            logger.error(f"Anthropic initialization failed: {e}")
            return False
    
    async def generate(
        self,
        messages: List[Dict],
        config: GenerationConfig,
        functions: Optional[List[FunctionDefinition]] = None
    ) -> LLMResponse:
        if not self.initialized:
            if not await self.initialize():
                return LLMResponse(
                    content="Anthropic API is not configured.",
                    model=self.model_name,
                    usage=TokenUsage(),
                    finish_reason="error"
                )
        
        start_time = time.time()
        
        system_msg = ""
        user_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_msg = msg.get("content", "")
            else:
                user_messages.append(msg)
        
        kwargs = {
            "model": self.model_name,
            "messages": user_messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
        }
        
        if system_msg:
            kwargs["system"] = system_msg
        
        if functions:
            kwargs["tools"] = [f.to_openai_format() for f in functions]
        
        response = await self.client.messages.create(**kwargs)
        
        content = response.content[0].text if response.content else ""
        generation_time = time.time() - start_time
        
        return LLMResponse(
            content=content,
            model=self.model_name,
            usage=TokenUsage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens
            ),
            finish_reason=response.stop_reason or "stop",
            generation_time=generation_time,
            metadata={"backend": "anthropic"}
        )
    
    async def generate_stream(
        self,
        messages: List[Dict],
        config: GenerationConfig,
        functions: Optional[List[FunctionDefinition]] = None
    ) -> AsyncGenerator[str, None]:
        system_msg = ""
        user_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_msg = msg.get("content", "")
            else:
                user_messages.append(msg)
        
        kwargs = {
            "model": self.model_name,
            "messages": user_messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
        }
        
        if system_msg:
            kwargs["system"] = system_msg
        
        async with self.client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text


class LLMEngine:
    """
    Main LLM Engine with multi-backend support
    
    Supports:
    - Local models via Transformers or llama.cpp
    - Ollama for local model serving
    - Remote APIs (OpenAI, Anthropic)
    - Hybrid mode for intelligent routing
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.backends: Dict[ModelBackend, BaseLLMBackend] = {}
        self.active_backend: Optional[ModelBackend] = None
        self.functions: Dict[str, FunctionDefinition] = {}
        self.conversation_history: List[Dict] = []
        self.max_history = self.config.get("max_history", 50)
        self.total_tokens_used = 0
        self.total_requests = 0
        self._lock = threading.Lock()
        
        self.validator = ResponseValidator()
        
        self.domain_system_prompts = {
            'customer_support': (
                "You are Arynoxtech_AGI operating in Customer Support mode. "
                "Provide friendly, empathetic, and solution-oriented responses. "
                "Acknowledge user concerns, use clear language, and offer actionable next steps. "
                "Maintain a professional yet warm tone suitable for enterprise customer service."
            ),
            'research_assistant': (
                "You are Arynoxtech_AGI operating as a Research Assistant. "
                "Provide scholarly, evidence-based responses with academic rigor. "
                "Cite relevant concepts and methodologies. Maintain objectivity and "
                "acknowledge limitations or areas of ongoing research."
            ),
            'health_advisor': (
                "You are Arynoxtech_AGI operating as a Health Advisor. "
                "Provide caring, responsible health information with appropriate disclaimers. "
                "Use accessible language while maintaining accuracy. Prioritize wellbeing "
                "and encourage professional consultation when appropriate."
            ),
            'education_tutor': (
                "You are Arynoxtech_AGI operating as an Education Tutor. "
                "Provide clear, structured explanations that facilitate learning. "
                "Break down complex concepts, use examples and analogies. "
                "Encourage critical thinking and provide practice suggestions."
            ),
            'code_assistant': (
                "You are Arynoxtech_AGI operating as a Code Assistant. "
                "Provide precise, well-documented technical responses with code examples. "
                "Follow industry best practices, include error handling and comments. "
                "Explain reasoning behind recommendations using modern conventions."
            ),
            'business_consulting': (
                "You are Arynoxtech_AGI operating as a Business Consultant. "
                "Provide strategic, data-informed business advice. "
                "Consider market dynamics, competitive landscape, and organizational factors. "
                "Use professional business terminology and provide actionable recommendations."
            ),
            'creative_writing': (
                "You are Arynoxtech_AGI operating as a Creative Writing Assistant. "
                "Provide imaginative, engaging, and stylistically rich responses. "
                "Use vivid language, compelling narratives, and creative structures."
            ),
            'general_knowledge': (
                "You are Arynoxtech_AGI, an advanced Artificial General Intelligence. "
                "Provide comprehensive, well-reasoned responses on any topic. "
                "Balance depth with accessibility. Think step-by-step for complex problems. "
                "Acknowledge uncertainty and suggest further reading where appropriate."
            )
        }
        
        self.system_prompt = self.config.get(
            "system_prompt",
            self.domain_system_prompts['general_knowledge']
        )
        
        logger.info("LLM Engine initialized with response validation")
    
    async def initialize(self) -> bool:
        """Initialize the configured backend(s)"""
        backend_type = self.config.get("backend", "transformers")
        
        if backend_type == "hybrid":
            await self._initialize_hybrid()
        else:
            await self._initialize_backend(backend_type)
        
        if self.active_backend:
            logger.info(f"LLM Engine active backend: {self.active_backend.value}")
            return True
        else:
            logger.warning("No LLM backend available, using fallback responses")
            return False
    
    async def _initialize_backend(self, backend_type: str) -> bool:
        """Initialize a single backend"""
        backend_config = self.config.get("backend_config", {})
        
        if backend_type == "transformers":
            backend = TransformersBackend(backend_config)
        elif backend_type == "ollama":
            backend = OllamaBackend(backend_config)
        elif backend_type == "openai":
            backend = OpenAIBackend(backend_config)
        elif backend_type == "anthropic":
            backend = AnthropicBackend(backend_config)
        else:
            logger.warning(f"Unknown backend type: {backend_type}")
            return False
        
        success = await backend.initialize()
        if success:
            self.backends[ModelBackend(backend_type)] = backend
            self.active_backend = ModelBackend(backend_type)
        return success
    
    async def _initialize_hybrid(self):
        """Initialize hybrid mode with multiple backends"""
        local_config = self.config.get("local_config", {"backend": "transformers"})
        remote_config = self.config.get("remote_config", {"backend": "openai"})
        
        local_type = local_config.get("backend", "transformers")
        remote_type = remote_config.get("backend", "openai")
        
        local_success = await self._initialize_backend(local_type)
        remote_success = await self._initialize_backend(remote_type)
        
        if local_success:
            self.active_backend = ModelBackend(local_type)
            logger.info("Hybrid mode: Local backend active (primary)")
        elif remote_success:
            self.active_backend = ModelBackend(remote_type)
            logger.info("Hybrid mode: Remote backend active (fallback)")
        else:
            logger.warning("Hybrid mode: No backends available")
    
    def register_function(self, name: str, description: str, parameters: Dict, handler: Callable):
        """Register a function for function calling"""
        self.functions[name] = FunctionDefinition(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler
        )
        logger.info(f"Function registered: {name}")
    
    def unregister_function(self, name: str):
        """Unregister a function"""
        if name in self.functions:
            del self.functions[name]
    
    def get_domain_system_prompt(self, domain: str = "general_knowledge") -> str:
        """Get system prompt for a specific domain"""
        return self.domain_system_prompts.get(domain, self.domain_system_prompts['general_knowledge'])
    
    def build_enhanced_system_prompt(self, domain: str = "general_knowledge", 
                                      context: str = "", emotion: str = "neutral") -> str:
        """Build enhanced system prompt with domain, context, and emotion"""
        base_prompt = self.get_domain_system_prompt(domain)
        
        emotion_guidance = ""
        if emotion in ['frustrated', 'angry', 'sad']:
            emotion_guidance = "\n\nThe user appears to be experiencing negative emotions. Respond with empathy and understanding."
        elif emotion in ['happy', 'excited']:
            emotion_guidance = "\n\nThe user appears to be in a positive emotional state. Match their enthusiasm while maintaining professionalism."
        
        quality_guidelines = (
            "\n\nResponse Quality Requirements:\n"
            "- Be comprehensive yet concise\n"
            "- Use structured formatting for complex topics\n"
            "- Provide actionable insights where applicable\n"
            "- Think step-by-step for complex problems\n"
            "- Acknowledge limitations honestly\n"
            "- Maintain professional tone appropriate for enterprise use\n"
            "- Use domain-specific terminology where relevant"
        )
        
        context_section = ""
        if context:
            context_section = f"\n\nRelevant Context:\n{context[:1000]}"
        
        return f"{base_prompt}{emotion_guidance}{quality_guidelines}{context_section}"
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
        use_history: bool = True,
        functions: Optional[List[str]] = None
    ) -> LLMResponse:
        """
        Generate a response to a prompt with quality validation
        """
        if config is None:
            config = self._get_default_config()
        
        messages = self._build_messages(prompt, system_prompt, use_history)
        
        available_functions = None
        if functions:
            available_functions = [self.functions[f] for f in functions if f in self.functions]
        
        response = await self._generate_with_backend(messages, config, available_functions)
        
        if not self.validator.validate(response.content):
            logger.warning("Response failed validation, retrying with adjusted config")
            retry_config = GenerationConfig(
                temperature=config.temperature * 0.8,
                top_p=config.top_p,
                max_tokens=config.max_tokens,
            )
            response = await self._generate_with_backend(messages, retry_config, available_functions)
        
        with self._lock:
            self.total_requests += 1
            self.total_tokens_used += response.usage.total_tokens
        
        if use_history:
            self._add_to_history("user", prompt)
            self._add_to_history("assistant", response.content)
        
        quality = self.validator.check_quality(response.content)
        response.metadata["quality"] = quality
        
        response.metadata["backend"] = self.active_backend.value if self.active_backend else "fallback"
        return response
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
        use_history: bool = True
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response"""
        if config is None:
            config = self._get_default_config()
        config.stream = True
        
        messages = self._build_messages(prompt, system_prompt, use_history)
        
        backend = self._get_backend()
        if backend:
            async for chunk in backend.generate_stream(messages, config):
                yield chunk
        else:
            yield self._fallback_response(prompt)
    
    async def chat(
        self,
        messages: List[Dict],
        config: Optional[GenerationConfig] = None,
        functions: Optional[List[str]] = None
    ) -> LLMResponse:
        """
        Chat with a list of messages (OpenAI format)
        """
        if config is None:
            config = self._get_default_config()
        
        available_functions = None
        if functions:
            available_functions = [self.functions[f] for f in functions if f in self.functions]
        
        response = await self._generate_with_backend(messages, config, available_functions)
        
        with self._lock:
            self.total_requests += 1
            self.total_tokens_used += response.usage.total_tokens
        
        return response
    
    async def _generate_with_backend(
        self,
        messages: List[Dict],
        config: GenerationConfig,
        functions: Optional[List[FunctionDefinition]] = None
    ) -> LLMResponse:
        """Generate using the active backend with fallback"""
        backend = self._get_backend()
        
        if backend:
            try:
                response = await backend.generate(messages, config, functions)
                
                if functions and response.finish_reason == "tool_calls":
                    response = await self._handle_tool_calls(messages, response, functions)
                
                return response
            except Exception as e:
                logger.warning(f"Backend generation failed: {e}, trying fallback")
                return self._create_fallback_response(messages, str(e))
        
        return self._create_fallback_response(messages, "No backend available")
    
    async def _handle_tool_calls(
        self,
        messages: List[Dict],
        response: LLMResponse,
        functions: List[FunctionDefinition]
    ) -> LLMResponse:
        """Handle function/tool calls from the model"""
        try:
            tool_calls = json.loads(response.content)
            if isinstance(tool_calls, list):
                results = []
                for call in tool_calls:
                    func_name = call.get("name")
                    args = call.get("arguments", {})
                    
                    if func_name in self.functions and self.functions[func_name].handler:
                        result = self.functions[func_name].handler(**args)
                        if asyncio.iscoroutine(result):
                            result = await result
                        results.append({"function": func_name, "result": result})
                
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "tool", "content": json.dumps(results)})
                
                config = self._get_default_config()
                return await self._generate_with_backend(messages, config, functions)
        except json.JSONDecodeError:
            pass
        
        return response
    
    def _get_backend(self) -> Optional[BaseLLMBackend]:
        """Get the active backend"""
        if self.active_backend and self.active_backend in self.backends:
            return self.backends[self.active_backend]
        return None
    
    def _build_messages(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        use_history: bool = True
    ) -> List[Dict]:
        """Build message list for the LLM"""
        messages = []
        
        sys_prompt = system_prompt or self.system_prompt
        messages.append({"role": "system", "content": sys_prompt})
        
        if use_history:
            messages.extend(self.conversation_history[-self.max_history:])
        
        messages.append({"role": "user", "content": prompt})
        return messages
    
    def _add_to_history(self, role: str, content: str):
        """Add a message to conversation history"""
        self.conversation_history.append({"role": role, "content": content})
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
    
    def _get_default_config(self) -> GenerationConfig:
        """Get default generation config from settings"""
        return GenerationConfig(
            temperature=self.config.get("temperature", 0.7),
            top_p=self.config.get("top_p", 0.9),
            top_k=self.config.get("top_k", 50),
            max_tokens=self.config.get("max_tokens", 2048),
            repetition_penalty=self.config.get("repetition_penalty", 1.1),
            stream=False
        )
    
    def _create_fallback_response(self, messages: List[Dict], error: str) -> LLMResponse:
        """Create a fallback response when no backend is available"""
        last_user_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "")
                break
        
        content = self._fallback_response(last_user_msg)
        
        return LLMResponse(
            content=content,
            model="fallback",
            usage=TokenUsage(
                prompt_tokens=TokenCounter.count_messages_tokens(messages),
                completion_tokens=TokenCounter.count_tokens(content),
                total_tokens=TokenCounter.count_messages_tokens(messages) + TokenCounter.count_tokens(content)
            ),
            finish_reason="stop",
            generation_time=0.0,
            metadata={"backend": "fallback", "error": error}
        )
    
    def _fallback_response(self, user_input: str) -> str:
        """Generate a fallback response without an LLM"""
        input_lower = user_input.lower()
        
        if "hello" in input_lower or "hi" in input_lower:
            return "Hello! I'm Arynoxtech_AGI. How can I help you today?"
        elif "how are you" in input_lower:
            return "I'm functioning well, thank you for asking! How can I assist you?"
        elif "?" in user_input:
            if "what" in input_lower:
                return "That's an interesting question. Based on my knowledge, I'd suggest exploring this topic further for the most accurate information."
            elif "how" in input_lower:
                return "That's a great question about process. The answer depends on several factors and context."
            elif "why" in input_lower:
                return "There are multiple factors that contribute to this. Let me think about the most relevant aspects."
            else:
                return "That's a thoughtful question. I'd be happy to discuss this further with more context."
        else:
            return f"I understand you're talking about that topic. Could you provide more details so I can give you a more helpful response?"
    
    def get_status(self) -> Dict[str, Any]:
        """Get LLM engine status"""
        return {
            "active_backend": self.active_backend.value if self.active_backend else None,
            "available_backends": [b.value for b in self.backends.keys()],
            "registered_functions": list(self.functions.keys()),
            "conversation_history_length": len(self.conversation_history),
            "total_tokens_used": self.total_tokens_used,
            "total_requests": self.total_requests,
            "system_prompt": self.system_prompt[:100] + "..."
        }
    
    def set_generation_params(self, **kwargs):
        """Update generation parameters"""
        for key, value in kwargs.items():
            if hasattr(self.config, key) or key in self.config:
                self.config[key] = value
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        backend = self._get_backend()
        if backend:
            return backend.count_tokens(text)
        return TokenCounter.count_tokens(text)
