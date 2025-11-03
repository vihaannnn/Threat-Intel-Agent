"""
Multi-model LLM support for the threat intelligence agent
Supports OpenAI, Llama, Qwen, and Mistral models with automatic fallback
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Union, AsyncGenerator
import json

# OpenAI
import openai

# Local LLM support
try:
    from transformers import AutoTokenizer, AutoModelForCausalLM, TextStreamer
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    import llama_cpp
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False

from utils.config import OPENAI_KEY, OPENAI_MODEL, PREFER_LOCAL_MODELS, PREFERRED_LOCAL_MODEL

logger = logging.getLogger("LLM")

class LLMProvider:
    """Unified LLM interface supporting multiple models"""
    
    def __init__(self, model_name: str = "auto", device: str = "auto"):
        self.model_name = model_name
        self.device = device
        self.openai_client = None
        self.local_model = None
        self.tokenizer = None
        self.streamer = None
        
        # Initialize based on model preference
        if model_name == "auto":
            self._auto_select_model()
        else:
            self._initialize_model(model_name)
    
    def _auto_select_model(self):
        """Auto-select best available model with hybrid fallback and env preference"""
        # Respect environment preference to force local
        if PREFER_LOCAL_MODELS:
            logger.info("PREFER_LOCAL_MODELS=true → forcing local model selection")
            if self._try_local_model(preferred=PREFERRED_LOCAL_MODEL):
                return
            logger.warning("Preferred local model not available; falling back to auto local selection")
            if self._try_local_model():
                return
            logger.warning("No local models available; attempting OpenAI as last resort")
            if OPENAI_KEY and self._test_openai():
                self.model_name = "openai"
                self.openai_client = openai.OpenAI(api_key=OPENAI_KEY)
                logger.info("Using OpenAI LLM (fallback)")
                return
            raise RuntimeError("No local models available and OpenAI not usable")

        # Default behavior: prefer OpenAI first
        if OPENAI_KEY and self._test_openai():
            self.model_name = "openai"
            self.openai_client = openai.OpenAI(api_key=OPENAI_KEY)
            logger.info("Using OpenAI LLM (primary)")
            return
        
        # Fallback to local models
        logger.info("OpenAI not available, trying local models...")
        if self._try_local_model():
            return
        
        logger.warning("Could not initialize any local models; trying llama.cpp/transformers defaults")
        
        # Final fallback
        if TRANSFORMERS_AVAILABLE:
            self.model_name = "llama-3.1-8b"
            self._initialize_transformers()
            logger.info("Using transformers with default model")
        elif LLAMA_CPP_AVAILABLE:
            self.model_name = "llama-cpp"
            self._initialize_llama_cpp()
            logger.info("Using llama.cpp")
        else:
            raise RuntimeError("No LLM models available. Install transformers or llama-cpp, or set OPENAI_API_KEY")

    def _try_local_model(self, preferred: Optional[str] = None) -> bool:
        """Attempt to initialize a local transformers model. Returns True if successful."""
        try:
            from core.model_manager import LocalModelManager
            model_manager = LocalModelManager()
            models_info = model_manager.list_models()

            # Preferred model path
            if preferred and preferred in models_info and models_info[preferred]["downloaded"]:
                logger.info(f"Using preferred local model: {preferred}")
                self.model_name = preferred
                self._initialize_transformers()
                return True

            # Otherwise choose the largest downloaded model
            downloaded_models = [
                name for name, info in models_info.items() 
                if info["downloaded"]
            ]
            if downloaded_models:
                best_model = max(downloaded_models, key=lambda x: models_info[x]["size_gb"])
                logger.info(f"Using downloaded local model: {best_model}")
                self.model_name = best_model
                self._initialize_transformers()
                return True
        except Exception as e:
            logger.warning(f"Local model check failed: {e}")
        return False
    
    def _test_openai(self) -> bool:
        """Test OpenAI API availability"""
        try:
            client = openai.OpenAI(api_key=OPENAI_KEY)
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=10
            )
            return True
        except Exception:
            return False
    
    def _initialize_llama_cpp(self):
        """Initialize llama.cpp model"""
        if not LLAMA_CPP_AVAILABLE:
            raise ImportError("llama-cpp not available")
        
        # Try to load a local model file
        model_paths = [
            "models/llama-3.1-8b-instruct.gguf",
            "models/llama-3.1-8b-instruct-q4_k_m.gguf",
            "models/llama-3.1-8b-instruct-q8_0.gguf"
        ]
        
        model_path = None
        for path in model_paths:
            try:
                import os
                if os.path.exists(path):
                    model_path = path
                    break
            except:
                continue
        
        if not model_path:
            logger.warning("No local GGUF model found, will use OpenAI fallback")
            self.model_name = "openai"
            self.openai_client = openai.OpenAI(api_key=OPENAI_KEY)
            return
        
        self.local_model = llama_cpp.Llama(
            model_path=model_path,
            n_ctx=4096,
            n_threads=4,
            verbose=False
        )
    
    def _initialize_transformers(self):
        """Initialize transformers model"""
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers not available")
        
        model_map = {
            "llama-3.1-8b": "meta-llama/Llama-3.1-8B-Instruct",
            "llama-3.1-70b": "meta-llama/Llama-3.1-70B-Instruct",
            "qwen2.5-7b": "Qwen/Qwen2.5-7B-Instruct",
            "qwen2.5-14b": "Qwen/Qwen2.5-14B-Instruct",
            "mistral-7b": "mistralai/Mistral-7B-Instruct-v0.3",
            "mixtral-8x7b": "mistralai/Mixtral-8x7B-Instruct-v0.1"
        }
        
        model_path = model_map.get(self.model_name, "meta-llama/Llama-3.1-8B-Instruct")
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.local_model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None,
            low_cpu_mem_usage=True
        )
        
        if torch.cuda.is_available() and self.device == "auto":
            self.device = "cuda"
        else:
            self.device = "cpu"
    
    def _initialize_model(self, model_name: str):
        """Initialize specific model"""
        if model_name == "openai":
            if not OPENAI_KEY:
                raise ValueError("OPENAI_KEY required for OpenAI LLM")
            self.openai_client = openai.OpenAI(api_key=OPENAI_KEY)
        elif model_name == "llama-cpp":
            self._initialize_llama_cpp()
        elif model_name in ["llama-3.1-8b", "llama-3.1-70b", "qwen2.5-7b", "qwen2.5-14b", "mistral-7b", "mixtral-8x7b"]:
            self._initialize_transformers()
        else:
            raise ValueError(f"Unknown model: {model_name}")
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.0,
        max_tokens: int = 1000,
        stream: bool = False
    ) -> Union[str, AsyncGenerator[str, None]]:
        """Generate chat completion"""
        if self.model_name == "openai":
            return await self._chat_openai(messages, temperature, max_tokens, stream)
        else:
            return await self._chat_local(messages, temperature, max_tokens, stream)
    
    async def _chat_openai(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float, 
        max_tokens: int,
        stream: bool
    ) -> Union[str, AsyncGenerator[str, None]]:
        """Generate completion using OpenAI API"""
        try:
            response = self.openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream
            )
            
            if stream:
                async def stream_generator():
                    for chunk in response:
                        if chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content
                return stream_generator()
            else:
                return response.choices[0].message.content
                
        except Exception as e:
            logger.error(f"OpenAI chat error: {e}")
            raise
    
    async def _chat_local(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float, 
        max_tokens: int,
        stream: bool
    ) -> Union[str, AsyncGenerator[str, None]]:
        """Generate completion using local models"""
        try:
            if self.model_name == "llama-cpp" and self.local_model:
                return await self._chat_llama_cpp(messages, temperature, max_tokens, stream)
            elif TRANSFORMERS_AVAILABLE and self.tokenizer and self.local_model:
                return await self._chat_transformers(messages, temperature, max_tokens, stream)
            else:
                raise RuntimeError("No local LLM model available")
                
        except Exception as e:
            logger.error(f"Local chat error: {e}")
            raise
    
    async def _chat_llama_cpp(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float, 
        max_tokens: int,
        stream: bool
    ) -> Union[str, AsyncGenerator[str, None]]:
        """Generate completion using llama.cpp"""
        def _generate():
            # Convert messages to prompt format
            prompt = self._format_messages_llama(messages)
            
            if stream:
                return self.local_model(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True
                )
            else:
                response = self.local_model(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=False
                )
                return response['choices'][0]['text']
        
        # Run in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _generate)
        
        if stream:
            async def stream_generator():
                for chunk in result:
                    if 'choices' in chunk and chunk['choices'][0]['text']:
                        yield chunk['choices'][0]['text']
            return stream_generator()
        else:
            return result
    
    async def _chat_transformers(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float, 
        max_tokens: int,
        stream: bool
    ) -> Union[str, AsyncGenerator[str, None]]:
        """Generate completion using transformers"""
        def _generate():
            # Format messages for the model
            prompt = self._format_messages_transformers(messages)
            
            # Tokenize
            inputs = self.tokenizer(prompt, return_tensors="pt")
            if self.device == "cuda":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate
            with torch.no_grad():
                outputs = self.local_model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    do_sample=temperature > 0,
                    pad_token_id=self.tokenizer.eos_token_id,
                    streamer=self.streamer if stream else None
                )
            
            # Decode response
            response = self.tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
            return response
        
        # Run in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _generate)
        
        if stream:
            # For streaming, we'd need to implement proper streaming with transformers
            # For now, return the full response
            async def stream_generator():
                yield result
            return stream_generator()
        else:
            return result
    
    def _format_messages_llama(self, messages: List[Dict[str, str]]) -> str:
        """Format messages for llama.cpp"""
        prompt = ""
        for message in messages:
            role = message["role"]
            content = message["content"]
            if role == "system":
                prompt += f"<|system|>\n{content}\n<|user|>\n"
            elif role == "user":
                prompt += f"{content}\n"
            elif role == "assistant":
                prompt += f"<|assistant|>\n{content}\n"
        prompt += "<|assistant|>\n"
        return prompt
    
    def _format_messages_transformers(self, messages: List[Dict[str, str]]) -> str:
        """Format messages for transformers models"""
        prompt = ""
        for message in messages:
            role = message["role"]
            content = message["content"]
            if role == "system":
                prompt += f"<|system|>\n{content}\n"
            elif role == "user":
                prompt += f"<|user|>\n{content}\n"
            elif role == "assistant":
                prompt += f"<|assistant|>\n{content}\n"
        prompt += "<|assistant|>\n"
        return prompt

# Global LLM provider instance
_llm_provider = None

def get_llm_provider(model_name: str = "auto", device: str = "auto") -> LLMProvider:
    """Get global LLM provider instance"""
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = LLMProvider(model_name, device)
    return _llm_provider

async def chat_completion(
    messages: List[Dict[str, str]], 
    model_name: str = "auto",
    temperature: float = 0.0,
    max_tokens: int = 1000,
    stream: bool = False
) -> Union[str, AsyncGenerator[str, None]]:
    """Convenience function for chat completion"""
    provider = get_llm_provider(model_name)
    return await provider.chat_completion(messages, temperature, max_tokens, stream)
