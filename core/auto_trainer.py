"""
NexusAGI Auto Trainer
Automatic internet training on startup and continuous learning
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

logger = logging.getLogger(__name__)


@dataclass
class TrainingSource:
    """Represents a training source"""
    url: str
    source_type: str
    priority: int = 1
    domain: str = "general"
    last_trained: Optional[datetime] = None
    success_count: int = 0
    failure_count: int = 0


class ContentDeduplicator:
    """Smart deduplication to avoid learning same content"""
    
    def __init__(self, max_entries: int = 10000):
        self.content_hashes: Set[str] = set()
        self.url_hashes: Set[str] = set()
        self.max_entries = max_entries
        self.stats = {'duplicates_blocked': 0, 'unique_stored': 0}
    
    def is_duplicate_url(self, url: str) -> bool:
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        if url_hash in self.url_hashes:
            self.stats['duplicates_blocked'] += 1
            return True
        return False
    
    def is_duplicate_content(self, content: str) -> bool:
        content_hash = hashlib.sha256(content[:2000].encode()).hexdigest()
        if content_hash in self.content_hashes:
            self.stats['duplicates_blocked'] += 1
            return True
        return False
    
    def add_url(self, url: str):
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        self.url_hashes.add(url_hash)
        self.stats['unique_stored'] += 1
        self._cleanup()
    
    def add_content(self, content: str):
        content_hash = hashlib.sha256(content[:2000].encode()).hexdigest()
        self.content_hashes.add(content_hash)
        self.stats['unique_stored'] += 1
        self._cleanup()
    
    def _cleanup(self):
        if len(self.url_hashes) > self.max_entries:
            self.url_hashes = set(list(self.url_hashes)[-self.max_entries//2:])
        if len(self.content_hashes) > self.max_entries:
            self.content_hashes = set(list(self.content_hashes)[-self.max_entries//2:])
    
    def get_stats(self) -> Dict:
        return {
            **self.stats,
            'unique_urls': len(self.url_hashes),
            'unique_contents': len(self.content_hashes)
        }


class AutoTrainer:
    """
    Automatic Internet Trainer
    Trains the AGI from internet data on every startup
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        self.enabled = self.config.get('enabled', True)
        self.auto_train_on_startup = self.config.get('auto_train_on_startup', True)
        self.continuous_training = self.config.get('continuous_training', True)
        self.training_interval = self.config.get('training_interval', 1800)
        self.max_sources_per_session = self.config.get('max_sources_per_session', 50)
        self.min_content_length = self.config.get('min_content_length', 100)
        
        self.search_engines = self.config.get('search_engines', [
            'https://www.google.com/search?q=',
            'https://duckduckgo.com/html/?q=',
            'https://www.bing.com/search?q='
        ])
        
        self.search_topics = self.config.get('search_topics', [
            'latest AI research 2026',
            'artificial general intelligence breakthroughs',
            'machine learning algorithms',
            'neural network architectures',
            'natural language processing advances',
            'computer vision technology',
            'robotics and automation',
            'quantum computing applications',
            'AI ethics and safety',
            'deep learning optimization',
            'transformer architecture improvements',
            'reinforcement learning',
            'generative AI models',
            'large language models',
            'multimodal AI systems',
            'AI in healthcare',
            'AI in finance',
            'autonomous vehicles technology',
            'AI drug discovery',
            'edge AI computing',
            'federated learning',
            'neural architecture search',
            'AI chip design',
            'computational biology AI',
            'AI climate solutions',
            'software engineering best practices 2026',
            'cloud computing trends',
            'cybersecurity threats and solutions',
            'blockchain technology advances',
            'IoT and smart devices',
            '5G and 6G networks',
            'data science methodologies',
            'MLOps and model deployment',
            'agile development practices',
            'DevOps automation',
            'microservices architecture',
            'API design patterns',
            'database optimization techniques',
            'web development frameworks',
            'mobile app development trends',
            'business strategy and innovation',
            'startup funding and venture capital',
            'digital marketing strategies',
            'leadership and management',
            'project management methodologies',
            'financial analysis techniques',
            'market research methods',
            'customer experience optimization',
            'supply chain management',
            'sustainable business practices',
            'medical research breakthroughs',
            'mental health awareness',
            'nutrition and wellness',
            'exercise science',
            'sleep optimization',
            'preventive healthcare',
            'telemedicine advances',
            'biotechnology innovations',
            'cancer research progress',
            'neuroscience discoveries',
            'educational technology',
            'online learning platforms',
            'STEM education methods',
            'cognitive learning science',
            'personalized education',
            'skill development strategies',
            'academic research methods',
            'student engagement techniques',
            'curriculum design',
            'assessment and evaluation',
            'space exploration news',
            'renewable energy advances',
            'environmental conservation',
            'climate change solutions',
            'sustainable agriculture',
            'ocean research discoveries',
            'materials science innovations',
            'physics breakthroughs',
            'chemistry advances',
            'genetics and genomics'
        ])
        
        self.rss_feeds = self.config.get('rss_feeds', [
            'https://arxiv.org/rss/cs.AI',
            'https://arxiv.org/rss/cs.LG',
            'https://arxiv.org/rss/cs.CL',
            'https://arxiv.org/rss/cs.CV',
            'https://arxiv.org/rss/cs.RO',
            'https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml',
            'https://feeds.bbci.co.uk/news/technology/rss.xml',
            'https://feeds.feedburner.com/TechCrunch/',
            'https://www.reddit.com/r/technology/.rss',
            'https://feeds.arstechnica.com/arstechnica/index',
            'https://www.wired.com/feed/rss',
            'https://www.nature.com/nature.rss',
            'https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=science',
            'https://github.com/trending',
            'https://huggingface.co/api/daily_papers',
            'https://blog.google/technology/ai/rss/',
            'https://openai.com/blog/rss.xml',
            'https://www.technologyreview.com/feed/',
            'https://feeds.feedburner.com/oreilly/radar',
            'https://www.theverge.com/rss/index.xml',
            'https://venturebeat.com/category/ai/feed/',
            'https://www.reuters.com/technology/rss',
            'https://www.sciencedaily.com/rss/computers_math/artificial_intelligence.xml',
            'https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id=latest'
        ])
        
        self.academic_sources = self.config.get('academic_sources', [
            {'name': 'arXiv AI', 'url': 'https://arxiv.org/list/cs.AI/recent', 'domain': 'research'},
            {'name': 'arXiv ML', 'url': 'https://arxiv.org/list/cs.LG/recent', 'domain': 'research'},
            {'name': 'arXiv NLP', 'url': 'https://arxiv.org/list/cs.CL/recent', 'domain': 'research'},
            {'name': 'PubMed AI', 'url': 'https://pubmed.ncbi.nlm.nih.gov/?term=artificial+intelligence', 'domain': 'health'},
            {'name': 'Google Scholar', 'url': 'https://scholar.google.com/scholar?q=machine+learning+2026', 'domain': 'research'},
        ])
        
        self.technical_sources = self.config.get('technical_sources', [
            {'name': 'GitHub Trending', 'url': 'https://github.com/trending', 'domain': 'technology'},
            {'name': 'Stack Overflow', 'url': 'https://stackoverflow.com/questions/tagged/machine-learning', 'domain': 'technology'},
            {'name': 'Hacker News', 'url': 'https://news.ycombinator.com/', 'domain': 'technology'},
            {'name': 'Dev.to', 'url': 'https://dev.to/t/ai', 'domain': 'technology'},
            {'name': 'Medium AI', 'url': 'https://medium.com/tag/artificial-intelligence', 'domain': 'technology'},
        ])
        
        self.sources: Dict[str, TrainingSource] = {}
        self.trained_urls: Set[str] = set()
        
        self.deduplicator = ContentDeduplicator()
        
        self.storage_path = Path("memory/training_data")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.domain_storage: Dict[str, Path] = {}
        for domain in ['technology', 'business', 'health', 'education', 'research', 'general', 'science']:
            domain_path = self.storage_path / domain
            domain_path.mkdir(parents=True, exist_ok=True)
            self.domain_storage[domain] = domain_path
        
        self.training_stats = {
            'total_sources_trained': 0,
            'total_content_processed': 0,
            'total_training_time': 0.0,
            'last_training_session': None,
            'successful_trainings': 0,
            'failed_trainings': 0,
            'duplicates_blocked': 0,
            'domains_trained': {}
        }
        
        self._load_training_data()
        
        logger.info("Auto Trainer initialized with multi-domain learning")
    
    def _load_training_data(self):
        """Load previously trained data"""
        index_file = self.storage_path / "training_index.json"
        
        if index_file.exists():
            try:
                with open(index_file, 'r') as f:
                    data = json.load(f)
                
                self.trained_urls = set(data.get('trained_urls', []))
                self.training_stats = data.get('stats', self.training_stats)
                
                for source_data in data.get('sources', []):
                    source = TrainingSource(
                        url=source_data['url'],
                        source_type=source_data['source_type'],
                        priority=source_data.get('priority', 1),
                        domain=source_data.get('domain', 'general'),
                        last_trained=datetime.fromisoformat(source_data['last_trained']) if source_data.get('last_trained') else None,
                        success_count=source_data.get('success_count', 0),
                        failure_count=source_data.get('failure_count', 0)
                    )
                    self.sources[source.url] = source
                
                logger.info(f"Loaded {len(self.trained_urls)} previously trained URLs")
            except Exception as e:
                logger.error(f"Error loading training data: {e}")
    
    def _save_training_data(self):
        """Save training data to disk"""
        index_file = self.storage_path / "training_index.json"
        
        data = {
            'trained_urls': list(self.trained_urls),
            'stats': self.training_stats,
            'sources': [
                {
                    'url': source.url,
                    'source_type': source.source_type,
                    'priority': source.priority,
                    'domain': source.domain,
                    'last_trained': source.last_trained.isoformat() if source.last_trained else None,
                    'success_count': source.success_count,
                    'failure_count': source.failure_count
                }
                for source in self.sources.values()
            ]
        }
        
        with open(index_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _detect_domain_for_content(self, content: str, url: str) -> str:
        """Detect which domain the content belongs to"""
        content_lower = content.lower()
        url_lower = url.lower()
        combined = content_lower + " " + url_lower
        
        domain_keywords = {
            'technology': ['code', 'software', 'programming', 'developer', 'api', 'database', 'cloud', 'devops', 'algorithm'],
            'business': ['revenue', 'profit', 'market', 'startup', 'investment', 'strategy', 'finance', 'sales', 'marketing'],
            'health': ['medical', 'health', 'disease', 'treatment', 'patient', 'clinical', 'therapy', 'diagnosis', 'wellness'],
            'education': ['learning', 'student', 'teaching', 'curriculum', 'school', 'university', 'course', 'exam', 'academic'],
            'research': ['study', 'research', 'paper', 'experiment', 'hypothesis', 'findings', 'analysis', 'methodology', 'peer-reviewed'],
            'science': ['physics', 'chemistry', 'biology', 'quantum', 'molecule', 'atom', 'energy', 'experiment', 'discovery'],
        }
        
        scores = {}
        for domain, keywords in domain_keywords.items():
            score = sum(1 for kw in keywords if kw in combined)
            scores[domain] = score
        
        if max(scores.values()) == 0:
            return 'general'
        
        return max(scores, key=scores.get)
    
    async def auto_train_on_startup(self, data_ingestion_manager=None, web_fetcher=None):
        """Automatically train from internet on startup"""
        if not self.enabled or not self.config.get('auto_train_on_startup', True):
            logger.info("Auto training disabled")
            return
        
        logger.info("Starting automatic internet training on startup...")
        start_time = time.time()
        
        try:
            new_sources = await self._discover_new_sources()
            logger.info(f"Discovered {len(new_sources)} new sources")
            
            trained_count = 0
            domain_counts = {}
            tasks = []
            
            for source in new_sources[:self.max_sources_per_session]:
                if trained_count >= self.max_sources_per_session:
                    break
                
                task = asyncio.create_task(self._train_from_source_safe(source, data_ingestion_manager, web_fetcher))
                tasks.append(task)
                
                await asyncio.sleep(0.2)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, dict) and r.get('success'):
                    trained_count += 1
                    domain = r.get('domain', 'general')
                    domain_counts[domain] = domain_counts.get(domain, 0) + 1
            
            training_time = time.time() - start_time
            self.training_stats['total_sources_trained'] += trained_count
            self.training_stats['total_training_time'] += training_time
            self.training_stats['last_training_session'] = datetime.now().isoformat()
            self.training_stats['successful_trainings'] += trained_count
            self.training_stats['domains_trained'].update(domain_counts)
            self.training_stats['duplicates_blocked'] = self.deduplicator.get_stats()['duplicates_blocked']
            
            self._save_training_data()
            
            logger.info(f"Auto training completed: {trained_count} sources trained in {training_time:.2f}s")
            logger.info(f"Domains trained: {domain_counts}")
            
        except Exception as e:
            logger.error(f"Error during auto training: {e}")
            self.training_stats['failed_trainings'] += 1
    
    async def _discover_new_sources(self) -> List[TrainingSource]:
        """Discover new training sources from the internet"""
        sources = []
        
        for topic in self.search_topics:
            try:
                for engine_url in self.search_engines[:2]:
                    search_url = f"{engine_url}{topic.replace(' ', '+')}"
                    
                    results = await self._fetch_search_results(search_url)
                    
                    for result_url in results:
                        if result_url not in self.trained_urls and not self.deduplicator.is_duplicate_url(result_url):
                            domain = self._detect_domain_for_content(topic, result_url)
                            source = TrainingSource(
                                url=result_url,
                                source_type='search',
                                priority=5,
                                domain=domain
                            )
                            sources.append(source)
                    
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"Error discovering sources for topic '{topic}': {e}")
        
        for rss_url in self.rss_feeds[:10]:
            try:
                feed_sources = await self._fetch_rss_feed(rss_url)
                sources.extend(feed_sources)
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Error fetching RSS feed {rss_url}: {e}")
        
        for tech_source in self.technical_sources:
            try:
                tech_sources = await self._fetch_technical_source(tech_source)
                sources.extend(tech_sources)
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Error fetching technical source {tech_source['name']}: {e}")
        
        return sources
    
    async def _fetch_rss_feed(self, rss_url: str) -> List[TrainingSource]:
        """Fetch URLs from RSS feed"""
        sources = []
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                async with session.get(rss_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        content = await response.text()
                        soup = BeautifulSoup(content, 'xml')
                        
                        for item in soup.find_all('item')[:5]:
                            link = item.find('link')
                            if link and link.text:
                                url = link.text.strip()
                                if url not in self.trained_urls and not self.deduplicator.is_duplicate_url(url):
                                    source = TrainingSource(
                                        url=url,
                                        source_type='rss',
                                        priority=7,
                                        domain='research'
                                    )
                                    sources.append(source)
        except Exception as e:
            logger.error(f"Error fetching RSS feed: {e}")
        
        return sources
    
    async def _fetch_technical_source(self, tech_source: Dict) -> List[TrainingSource]:
        """Fetch URLs from technical sources"""
        sources = []
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                async with session.get(tech_source['url'], headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        for link in soup.find_all('a', href=True):
                            href = link['href']
                            if href.startswith('http') or href.startswith('/'):
                                if href.startswith('/'):
                                    href = f"https://{tech_source['url'].split('/')[2]}{href}"
                                
                                if href not in self.trained_urls and not self.deduplicator.is_duplicate_url(href):
                                    source = TrainingSource(
                                        url=href,
                                        source_type='technical',
                                        priority=6,
                                        domain=tech_source.get('domain', 'technology')
                                    )
                                    sources.append(source)
                                    if len(sources) >= 5:
                                        break
        except Exception as e:
            logger.error(f"Error fetching technical source: {e}")
        
        return sources
    
    async def _fetch_search_results(self, search_url: str) -> List[str]:
        """Fetch URLs from search results"""
        urls = []
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                async with session.get(search_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        for link in soup.find_all('a', href=True):
                            href = link['href']
                            
                            if href.startswith('http') and not any(x in href for x in ['google.com', 'duckduckgo.com', 'bing.com']):
                                clean_url = href.split('&')[0]
                                if clean_url not in urls:
                                    urls.append(clean_url)
                        
                        urls = urls[:10]
                        
        except Exception as e:
            logger.error(f"Error fetching search results: {e}")
        
        return urls
    
    async def _train_from_source(self, source: TrainingSource, 
                                   data_ingestion_manager=None, 
                                   web_fetcher=None) -> Dict[str, Any]:
        """Train from a single source"""
        try:
            content = await asyncio.wait_for(self._fetch_content(source.url), timeout=15.0)
            
            if not content or len(content) < self.min_content_length:
                return {'success': False, 'reason': 'content_too_short'}
            
            if self.deduplicator.is_duplicate_content(content):
                return {'success': False, 'reason': 'duplicate_content'}
            
            domain = source.domain or self._detect_domain_for_content(content, source.url)
            
            if data_ingestion_manager:
                await data_ingestion_manager.ingest_text(
                    content,
                    source=source.url,
                    source_type='web'
                )
            
            if web_fetcher:
                from core.web_fetcher import WebContent
                web_content = WebContent(
                    id=hashlib.md5(source.url.encode()).hexdigest()[:16],
                    url=source.url,
                    title=self._extract_title(content, source.url),
                    content=content,
                    source_type='web',
                    metadata={'trained_at': datetime.now().isoformat(), 'domain': domain}
                )
                web_fetcher.fetched_content[web_content.id] = web_content
                web_fetcher.fetched_urls.add(source.url)
            
            domain_path = self.domain_storage.get(domain, self.domain_storage['general'])
            content_file = domain_path / f"{hashlib.md5(source.url.encode()).hexdigest()[:12]}.json"
            content_data = {
                'url': source.url,
                'title': self._extract_title(content, source.url),
                'content': content[:50000],
                'domain': domain,
                'trained_at': datetime.now().isoformat(),
                'source_type': source.source_type
            }
            with open(content_file, 'w', encoding='utf-8') as f:
                json.dump(content_data, f, indent=2, ensure_ascii=False)
            
            self.trained_urls.add(source.url)
            self.deduplicator.add_url(source.url)
            self.deduplicator.add_content(content)
            source.last_trained = datetime.now()
            source.success_count += 1
            
            logger.info(f"Trained from: {source.url} (domain: {domain})")
            return {'success': True, 'domain': domain}
            
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching {source.url}")
            source.failure_count += 1
            return {'success': False, 'reason': 'timeout'}
        except Exception as e:
            logger.error(f"Error training from {source.url}: {e}")
            source.failure_count += 1
            return {'success': False, 'reason': str(e)}
    
    async def _train_from_source_safe(self, source: TrainingSource, 
                                        data_ingestion_manager=None, 
                                        web_fetcher=None) -> Dict[str, Any]:
        """Safe wrapper for training that handles all exceptions"""
        try:
            return await self._train_from_source(source, data_ingestion_manager, web_fetcher)
        except Exception as e:
            logger.error(f"Unexpected error training from {source.url}: {e}")
            return {'success': False, 'reason': str(e)}
    
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
                        
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                            element.decompose()
                        
                        text = soup.get_text()
                        
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
        
        from urllib.parse import urlparse
        return urlparse(url).path.split('/')[-1].replace('-', ' ').title()
    
    async def continuous_training_loop(self, data_ingestion_manager=None, web_fetcher=None):
        """Continuously train from internet in the background"""
        if not self.enabled or not self.continuous_training:
            return
        
        logger.info(f"Starting continuous training (interval: {self.training_interval}s)")
        
        while True:
            try:
                new_sources = await self._discover_new_sources()
                
                trained_count = 0
                domain_counts = {}
                for source in new_sources[:10]:
                    result = await self._train_from_source(source, data_ingestion_manager, web_fetcher)
                    if result.get('success'):
                        trained_count += 1
                        domain = result.get('domain', 'general')
                        domain_counts[domain] = domain_counts.get(domain, 0) + 1
                    await asyncio.sleep(1)
                
                self._save_training_data()
                
                if trained_count > 0:
                    logger.info(f"Continuous training: {trained_count} new sources learned (domains: {domain_counts})")
                
                await asyncio.sleep(self.training_interval)
                
            except Exception as e:
                logger.error(f"Error in continuous training: {e}")
                await asyncio.sleep(self.training_interval)
    
    def get_training_stats(self) -> Dict[str, Any]:
        """Get training statistics"""
        return {
            **self.training_stats,
            'total_trained_urls': len(self.trained_urls),
            'total_sources': len(self.sources),
            'enabled': self.enabled,
            'auto_train_on_startup': self.auto_train_on_startup,
            'continuous_training': self.continuous_training,
            'deduplication': self.deduplicator.get_stats(),
            'search_topics_count': len(self.search_topics),
            'rss_feeds_count': len(self.rss_feeds)
        }
