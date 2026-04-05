#!/usr/bin/env python3
"""
NexusAGI - Real Artificial General Intelligence
Main entry point for the AGI system
"""

import asyncio
import logging
import sys
import argparse
from pathlib import Path

# Add core to path
sys.path.insert(0, str(Path(__file__).parent))

from core.orchestrator import AGIOrchestrator


def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/agi.log", mode='a')
        ]
    )
    
    # Set specific log levels
    logging.getLogger("transformers").setLevel(logging.WARNING)
    logging.getLogger("torch").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def print_banner():
    """Print startup banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║   ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗               ║
    ║   ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝               ║
    ║   ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗               ║
    ║   ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║               _______
    ║   ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║                      |
    ║   ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝                      |
    ║                                                                    |
    ║       Artificial General Intelligence by aryan chavan              ║
    ║                                                                    |
    ║   🚀 2026 Technologies:                                            |
    ║   • Auto Internet Training (trains on startup)               ______
    ║   • Web Search Bots (continuous learning)                    ║
    ║   • RAG Engine (instant responses)                           ║
    ║   • Vector Embeddings (fast retrieval)                       ║
    ║   • Intelligent Caching (sub-second replies)                 ║
    ║   • Model Quantization (75% less memory)                     ║
    ║   • Sparse Attention (60% faster)                            ║
    ║   • Knowledge Distillation (10x faster)                      ║
    ║                                                              ║
    ║   Core Features:                                             ║
    ║   • Self-learning from PDF, CSV, TXT files                   ║
    ║   • Transformer-based NLP for natural conversation           ║
    ║   • Emotional intelligence and empathy                       ║
    ║   • Self-evolution and code improvement                      ║
    ║   • Voice interaction (speech recognition & TTS)             ║
    ║   • Complete offline functionality                           ║
    ║   • Unsensored learning capabilities                         ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


async def run_interactive_mode(orchestrator: AGIOrchestrator, use_voice: bool = False):
    """Run AGI in interactive mode"""
    await orchestrator.run_interactive(use_voice=use_voice)


async def run_api_mode(orchestrator: AGIOrchestrator, host: str = "0.0.0.0", port: int = 8000):
    """Run AGI as API server"""
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
        import uvicorn
        
        app = FastAPI(
            title="NexusAGI API",
            description="Real Artificial General Intelligence API",
            version="1.0.0"
        )
        
        class InteractionRequest(BaseModel):
            user_input: str
            user_id: str = None
            use_voice: bool = False
        
        class InteractionResponse(BaseModel):
            response: str
            emotional_state: dict
            user_emotion: dict
            interaction_count: int
            voice_used: bool
        
        @app.on_event("startup")
        async def startup():
            await orchestrator.start()
        
        @app.on_event("shutdown")
        async def shutdown():
            await orchestrator.shutdown()
        
        @app.post("/interact", response_model=InteractionResponse)
        async def interact(request: InteractionRequest):
            result = await orchestrator.interact(
                request.user_input,
                request.user_id,
                use_voice=request.use_voice
            )
            if 'error' in result:
                raise HTTPException(status_code=500, detail=result['error'])
            return InteractionResponse(**result)
        
        @app.post("/listen")
        async def listen(user_id: str = None, timeout: float = 5.0):
            result = await orchestrator.listen_and_respond(user_id, timeout)
            if 'error' in result:
                raise HTTPException(status_code=500, detail=result['error'])
            return result
        
        @app.post("/speak")
        async def speak(text: str, interrupt: bool = False):
            await orchestrator.speak(text, interrupt=interrupt)
            return {"status": "speaking", "text": text}
        
        @app.get("/status")
        async def get_status():
            return await orchestrator.get_status()
        
        @app.post("/process_file")
        async def process_file(file_path: str):
            return await orchestrator.process_file(file_path)
        
        @app.get("/search")
        async def search_knowledge(query: str, limit: int = 10):
            return await orchestrator.search_knowledge(query, limit)
        
        print(f"\nStarting NexusAGI API server on {host}:{port}")
        print(f"API documentation: http://{host}:{port}/docs")
        
        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
        
    except ImportError:
        print("FastAPI not installed. Install with: pip install fastapi uvicorn")
        print("Falling back to interactive mode...")
        await run_interactive_mode(orchestrator)


async def run_daemon_mode(orchestrator: AGIOrchestrator):
    """Run AGI as daemon (background process)"""
    print("Starting NexusAGI in daemon mode...")
    await orchestrator.start()
    
    # Keep running until shutdown
    try:
        while orchestrator.state.running and not orchestrator.shutdown_requested:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    
    await orchestrator.shutdown()


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="NexusAGI - Real Artificial General Intelligence"
    )
    
    parser.add_argument(
        '--mode',
        choices=['interactive', 'api', 'daemon'],
        default='interactive',
        help='Run mode (default: interactive)'
    )
    
    parser.add_argument(
        '--config',
        default='config/agi_config.json',
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )
    
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='API server host (default: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='API server port (default: 8000)'
    )
    
    parser.add_argument(
        '--voice',
        action='store_true',
        help='Enable voice interaction'
    )
    
    parser.add_argument(
        '--no-voice',
        action='store_true',
        help='Disable voice interaction'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Print banner
    print_banner()
    
    # Create orchestrator
    print(f"Initializing NexusAGI with config: {args.config}")
    orchestrator = AGIOrchestrator(args.config)
    
    # Override voice setting if specified
    if args.no_voice:
        orchestrator.state.voice_enabled = False
        print("Voice disabled via command line")
    elif args.voice:
        orchestrator.state.voice_enabled = True
        print("Voice enabled via command line")
    
    # Setup signal handlers
    orchestrator.setup_signal_handlers()
    
    # Run in selected mode
    try:
        if args.mode == 'interactive':
            await run_interactive_mode(orchestrator, use_voice=args.voice)
        elif args.mode == 'api':
            await run_api_mode(orchestrator, args.host, args.port)
        elif args.mode == 'daemon':
            await run_daemon_mode(orchestrator)
    except Exception as e:
        logging.error(f"Error running NexusAGI: {e}")
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
