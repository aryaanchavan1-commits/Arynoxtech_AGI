"""
Arynoxtech_AGI Web Bots
Intelligent web search bots for continuous learning
"""

import asyncio
import logging
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
import aiohttp
from bs4 import BeautifulSoup
import re
import time
import random

logger = logging.getLogger(__name__)


@dataclass
class WebBot:
    """Represents a web search bot"""
    id: str
    name: str
    bot_type: str  # searcher, crawler, analyzer, learner
    target_topics: List[str]
    search_queries: List[str]
    active: bool = True
    last_run: Optional[datetime] = None
    items_found: int = 0
    success_rate: float = 1.0


class WebBotManager:
    """
    Web Bot Manager
    Manages multiple bots for continuous web searching and learning
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Bot settings
        self.enabled = self.config.get('enabled', True)
        self.max_concurrent_bots = self.config.get('max_concurrent_bots', 3)
        self.bot_run_interval = self.config.get('bot_run_interval', 600)  # 10 minutes
        self.max_results_per_bot = self.config.get('max_results_per_bot', 20)
        
        # Search engines
        self.search_engines = self.config.get('search_engines', [
            'https://www.google.com/search?q=',
            'https://duckduckgo.com/html/?q=',
            'https://www.bing.com/search?q='
        ])
        
        # Initialize bots
        self.bots: Dict[str, WebBot] = {}
        self._initialize_bots()
        
        # Storage
        self.storage_path = Path("memory/web_bots")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Performance tracking
        self.bot_stats = {
            'total_searches': 0,
            'total_items_found': 0,
            'total_errors': 0,
            'last_bot_run': None
        }
        
        # Load existing data
        self._load_bot_data()
        
        logger.info(f"Web Bot Manager initialized with {len(self.bots)} bots")
    
    def _initialize_bots(self):
        """Initialize default web bots"""
        default_bots = [
            {
                'id': 'ai_research_bot',
                'name': 'AI Research Bot',
                'bot_type': 'searcher',
                'target_topics': ['artificial intelligence', 'machine learning', 'deep learning'],
                'search_queries': [
                    'latest AI research papers 2026',
                    'neural network breakthroughs',
                    'transformer architecture improvements',
                    'reinforcement learning advances'
                ]
            },
            {
                'id': 'tech_news_bot',
                'name': 'Tech News Bot',
                'bot_type': 'crawler',
                'target_topics': ['technology', 'software', 'hardware'],
                'search_queries': [
                    'latest technology news',
                    'software development trends',
                    'hardware innovations',
                    'startup funding rounds'
                ]
            },
            {
                'id': 'science_bot',
                'name': 'Science Bot',
                'bot_type': 'analyzer',
                'target_topics': ['science', 'physics', 'chemistry', 'biology'],
                'search_queries': [
                    'scientific discoveries 2026',
                    'physics breakthroughs',
                    'chemistry innovations',
                    'biology research'
                ]
            },
            {
                'id': 'knowledge_bot',
                'name': 'Knowledge Bot',
                'bot_type': 'learner',
                'target_topics': ['education', 'learning', 'knowledge'],
                'search_queries': [
                    'online learning resources',
                    'educational content',
                    'knowledge management',
                    'study techniques'
                ]
            },
            {
                'id': 'world_news_bot',
                'name': 'World News Bot',
                'bot_type': 'crawler',
                'target_topics': ['world', 'international', 'global'],
                'search_queries': [
                    'world news today',
                    'international affairs',
                    'global events',
                    'breaking news'
                ]
            }
        ]
        
        for bot_data in default_bots:
            bot = WebBot(
                id=bot_data['id'],
                name=bot_data['name'],
                bot_type=bot_data['bot_type'],
                target_topics=bot_data['target_topics'],
                search_queries=bot_data['search_queries']
            )
            self.bots[bot.id] = bot
    
    def _load_bot_data(self):
        """Load previously saved bot data"""
        index_file = self.storage_path / "bots_index.json"
        
        if index_file.exists():
            try:
                with open(index_file, 'r') as f:
                    data = json.load(f)
                
                self.bot_stats = data.get('stats', self.bot_stats)
                
                # Update bot stats
                for bot_data in data.get('bots', []):
                    if bot_data['id'] in self.bots:
                        bot = self.bots[bot_data['id']]
                        bot.last_run = datetime.fromisoformat(bot_data['last_run']) if bot_data.get('last_run') else None
                        bot.items_found = bot_data.get('items_found', 0)
                        bot.success_rate = bot_data.get('success_rate', 1.0)
                
                logger.info(f"✅ Loaded bot data - Bots remember their previous work!")
            except Exception as e:
                logger.error(f"Error loading bot data: {e}")
    
    def _save_bot_data(self):
        """Save bot data to disk"""
        index_file = self.storage_path / "bots_index.json"
        
        data = {
            'stats': self.bot_stats,
            'bots': [
                {
                    'id': bot.id,
                    'name': bot.name,
                    'last_run': bot.last_run.isoformat() if bot.last_run else None,
                    'items_found': bot.items_found,
                    'success_rate': bot.success_rate
                }
                for bot in self.bots.values()
            ]
        }
        
        with open(index_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    async def run_all_bots(self, web_fetcher=None, data_ingestion_manager=None):
        """Run all active bots"""
        if not self.enabled:
            logger.info("Web bots disabled")
            return
        
        logger.info(f"🤖 Running {len(self.bots)} web bots...")
        
        # Run bots concurrently (limited by max_concurrent_bots)
        semaphore = asyncio.Semaphore(self.max_concurrent_bots)
        
        async def run_bot_with_semaphore(bot):
            async with semaphore:
                await self._run_bot(bot, web_fetcher, data_ingestion_manager)
        
        tasks = [run_bot_with_semaphore(bot) for bot in self.bots.values() if bot.active]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Save bot data (PERSISTENT MEMORY)
        self._save_bot_data()
        
        logger.info(f"✅ All bots completed - Results saved to disk for tomorrow!")
    
    async def _run_bot(self, bot: WebBot, web_fetcher=None, data_ingestion_manager=None):
        """Run a single bot"""
        logger.info(f"Running bot: {bot.name}")
        
        try:
            # Select random search queries
            queries = random.sample(bot.search_queries, min(3, len(bot.search_queries)))
            
            items_found = 0
            for query in queries:
                if items_found >= self.max_results_per_bot:
                    break
                
                # Search for content
                results = await self._search_web(query)
                
                for url in results:
                    if items_found >= self.max_results_per_bot:
                        break
                    
                    # Fetch and process content
                    success = await self._process_url(url, bot, web_fetcher, data_ingestion_manager)
                    if success:
                        items_found += 1
                    
                    # Small delay
                    await asyncio.sleep(0.5)
            
            # Update bot stats
            bot.items_found += items_found
            bot.last_run = datetime.now()
            self.bot_stats['total_searches'] += 1
            self.bot_stats['total_items_found'] += items_found
            self.bot_stats['last_bot_run'] = datetime.now().isoformat()
            
            logger.info(f"Bot {bot.name} found {items_found} items")
            
        except Exception as e:
            logger.error(f"Error running bot {bot.name}: {e}")
            self.bot_stats['total_errors'] += 1
            bot.success_rate = max(0.0, bot.success_rate - 0.1)
    
    async def _search_web(self, query: str) -> List[str]:
        """Search the web for a query"""
        urls = []
        
        try:
            # Use a random search engine
            engine_url = random.choice(self.search_engines)
            search_url = f"{engine_url}{query.replace(' ', '+')}"
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                async with session.get(search_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Extract links
                        for link in soup.find_all('a', href=True):
                            href = link['href']
                            
                            # Filter for actual URLs
                            if href.startswith('http') and not any(x in href for x in ['google.com', 'duckduckgo.com', 'bing.com']):
                                # Clean URL
                                clean_url = href.split('&')[0]
                                if clean_url not in urls:
                                    urls.append(clean_url)
                        
                        # Limit results
                        urls = urls[:10]
                        
        except Exception as e:
            logger.error(f"Error searching web: {e}")
        
        return urls
    
    async def _process_url(self, url: str, bot: WebBot, 
                           web_fetcher=None, data_ingestion_manager=None) -> bool:
        """Process a URL and extract content"""
        try:
            # Fetch content
            content = await self._fetch_content(url)
            
            if not content or len(content) < 100:
                return False
            
            # Store in web fetcher if available
            if web_fetcher:
                from core.web_fetcher import WebContent
                web_content = WebContent(
                    id=hashlib.md5(url.encode()).hexdigest()[:16],
                    url=url,
                    title=self._extract_title(content, url),
                    content=content,
                    source_type='bot',
                    metadata={
                        'bot_id': bot.id,
                        'bot_name': bot.name,
                        'found_at': datetime.now().isoformat()
                    }
                )
                web_fetcher.fetched_content[web_content.id] = web_content
                web_fetcher.fetched_urls.add(url)
            
            # Process with data ingestion if available
            if data_ingestion_manager:
                await data_ingestion_manager.ingest_text(
                    content,
                    source=url,
                    source_type='web'
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing URL {url}: {e}")
            return False
    
    async def _fetch_content(self, url: str) -> Optional[str]:
        """Fetch content from a URL"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        html = await response.text()
                        
                        # Parse HTML
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Remove unwanted elements
                        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                            element.decompose()
                        
                        # Get text
                        text = soup.get_text()
                        
                        # Clean up text
                        lines = (line.strip() for line in text.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        text = ' '.join(chunk for chunk in chunks if chunk)
                        
                        return text
                        
        except Exception as e:
            logger.error(f"Error fetching content from {url}: {e}")
        
        return None
    
    def _extract_title(self, content: str, url: str) -> str:
        """Extract title from content or URL"""
        lines = content.split('\n')[:10]
        for line in lines:
            line = line.strip()
            if 10 < len(line) < 200 and not line.startswith('http'):
                return line
        
        # Fallback to URL
        from urllib.parse import urlparse
        return urlparse(url).path.split('/')[-1].replace('-', ' ').title()
    
    async def continuous_learning(self, web_fetcher=None, data_ingestion_manager=None):
        """Continuously run bots for learning"""
        if not self.enabled:
            return
        
        logger.info(f"Starting continuous bot learning (interval: {self.bot_run_interval}s)")
        
        while True:
            try:
                await self.run_all_bots(web_fetcher, data_ingestion_manager)
                await asyncio.sleep(self.bot_run_interval)
                
            except Exception as e:
                logger.error(f"Error in continuous bot learning: {e}")
                await asyncio.sleep(self.bot_run_interval)
    
    def add_custom_bot(self, bot_id: str, name: str, bot_type: str, 
                       target_topics: List[str], search_queries: List[str]):
        """Add a custom bot"""
        bot = WebBot(
            id=bot_id,
            name=name,
            bot_type=bot_type,
            target_topics=target_topics,
            search_queries=search_queries
        )
        self.bots[bot_id] = bot
        logger.info(f"Added custom bot: {name}")
    
    def get_bot_stats(self) -> Dict[str, Any]:
        """Get bot statistics"""
        return {
            **self.bot_stats,
            'total_bots': len(self.bots),
            'active_bots': sum(1 for bot in self.bots.values() if bot.active),
            'enabled': self.enabled
        }
