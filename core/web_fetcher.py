"""
Arynoxtech_AGI Web Fetcher
Internet data fetching for continuous learning
"""

import logging
import json
import asyncio
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from urllib.parse import urlparse
import aiohttp
import feedparser
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)


@dataclass
class WebContent:
    """Represents content fetched from the web"""
    id: str
    url: str
    title: str
    content: str
    summary: Optional[str] = None
    source_type: str = 'web'  # web, rss, api
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    keywords: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'url': self.url,
            'title': self.title,
            'content': self.content[:1000],
            'summary': self.summary,
            'source_type': self.source_type,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
            'keywords': self.keywords,
            'topics': self.topics
        }


class WebFetcher:
    """
    Web Fetcher for continuous learning from the internet
    Supports RSS feeds, web scraping, and API calls
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Configuration
        self.enabled = self.config.get('enabled', True)
        self.rss_feeds = self.config.get('rss_feeds', [
            'https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml',
            'https://feeds.bbci.co.uk/news/technology/rss.xml',
            'https://feeds.feedburner.com/TechCrunch/',
            'https://www.reddit.com/r/technology/.rss'
        ])
        
        # Storage
        self.fetched_content: Dict[str, WebContent] = {}
        self.storage_path = Path("memory/web_content")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Tracking
        self.fetched_urls: Set[str] = set()
        self.last_fetch: Optional[datetime] = None
        self.fetch_count = 0
        
        # Rate limiting
        self.request_delay = self.config.get('request_delay', 2.0)  # seconds
        self.max_requests_per_hour = self.config.get('max_requests_per_hour', 100)
        self.request_timestamps: List[datetime] = []
        
        # Load existing content
        self._load_content()
        
        logger.info("Web Fetcher initialized")
    
    def _load_content(self):
        """Load previously fetched content"""
        index_file = self.storage_path / "content_index.json"
        
        if index_file.exists():
            try:
                with open(index_file, 'r') as f:
                    index_data = json.load(f)
                
                for content_id, content_info in index_data.items():
                    self.fetched_content[content_id] = WebContent(
                        id=content_info['id'],
                        url=content_info['url'],
                        title=content_info['title'],
                        content=content_info['content'],
                        summary=content_info.get('summary'),
                        source_type=content_info.get('source_type', 'web'),
                        timestamp=datetime.fromisoformat(content_info['timestamp']),
                        metadata=content_info.get('metadata', {}),
                        keywords=content_info.get('keywords', []),
                        topics=content_info.get('topics', [])
                    )
                    self.fetched_urls.add(content_info['url'])
                
                logger.info(f"Loaded {len(self.fetched_content)} previously fetched items")
            except Exception as e:
                logger.error(f"Error loading content index: {e}")
    
    def _save_content(self):
        """Save content index to disk"""
        index_file = self.storage_path / "content_index.json"
        
        index_data = {}
        for content_id, content in self.fetched_content.items():
            index_data[content_id] = content.to_dict()
        
        with open(index_file, 'w') as f:
            json.dump(index_data, f, indent=2)
    
    def _can_make_request(self) -> bool:
        """Check if we can make a request (rate limiting)"""
        now = datetime.now()
        
        # Remove old timestamps
        self.request_timestamps = [
            ts for ts in self.request_timestamps
            if (now - ts).total_seconds() < 3600
        ]
        
        # Check rate limit
        if len(self.request_timestamps) >= self.max_requests_per_hour:
            logger.warning("Rate limit reached, waiting...")
            return False
        
        return True
    
    def _record_request(self):
        """Record a request timestamp"""
        self.request_timestamps.append(datetime.now())
    
    async def fetch_rss_feeds(self) -> List[WebContent]:
        """Fetch content from RSS feeds"""
        if not self.enabled:
            return []
        
        fetched_items = []
        
        for feed_url in self.rss_feeds:
            try:
                if not self._can_make_request():
                    break
                
                logger.info(f"Fetching RSS feed: {feed_url}")
                
                # Parse RSS feed
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:5]:  # Limit to 5 entries per feed
                    if entry.link in self.fetched_urls:
                        continue
                    
                    # Fetch full content
                    content = await self._fetch_web_page(entry.link)
                    
                    if content:
                        web_content = WebContent(
                            id=hashlib.md5(entry.link.encode()).hexdigest()[:16],
                            url=entry.link,
                            title=entry.get('title', 'Untitled'),
                            content=content,
                            summary=entry.get('summary', ''),
                            source_type='rss',
                            metadata={
                                'feed_url': feed_url,
                                'published': entry.get('published', ''),
                                'author': entry.get('author', '')
                            }
                        )
                        
                        # Extract keywords and topics
                        web_content.keywords = self._extract_keywords(content)
                        web_content.topics = self._extract_topics(content)
                        
                        fetched_items.append(web_content)
                        self.fetched_content[web_content.id] = web_content
                        self.fetched_urls.add(entry.link)
                        
                        await asyncio.sleep(self.request_delay)
                
                self._record_request()
                
            except Exception as e:
                logger.error(f"Error fetching RSS feed {feed_url}: {e}")
        
        if fetched_items:
            self._save_content()
            self.fetch_count += len(fetched_items)
            self.last_fetch = datetime.now()
            logger.info(f"Fetched {len(fetched_items)} items from RSS feeds")
        
        return fetched_items
    
    async def _fetch_web_page(self, url: str) -> Optional[str]:
        """Fetch and parse a web page"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        html = await response.text()
                        
                        # Parse HTML
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Remove script and style elements
                        for script in soup(["script", "style"]):
                            script.decompose()
                        
                        # Get text
                        text = soup.get_text()
                        
                        # Clean up text
                        lines = (line.strip() for line in text.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        text = ' '.join(chunk for chunk in chunks if chunk)
                        
                        return text
                    
        except Exception as e:
            logger.error(f"Error fetching web page {url}: {e}")
        
        return None
    
    async def search_web(self, query: str, max_results: int = 5) -> List[WebContent]:
        """Search the web for information"""
        if not self.enabled:
            return []
        
        # This is a simplified implementation
        # In production, you would use a proper search API
        
        logger.info(f"Searching web for: {query}")
        
        # For now, return empty list
        # In a real implementation, you would:
        # 1. Use a search API (Google, Bing, etc.)
        # 2. Fetch results
        # 3. Parse and return content
        
        return []
    
    async def fetch_specific_url(self, url: str) -> Optional[WebContent]:
        """Fetch content from a specific URL"""
        if not self.enabled:
            return None
        
        if url in self.fetched_urls:
            logger.info(f"URL already fetched: {url}")
            return self.fetched_content.get(hashlib.md5(url.encode()).hexdigest()[:16])
        
        if not self._can_make_request():
            logger.warning("Rate limit reached")
            return None
        
        try:
            content = await self._fetch_web_page(url)
            
            if content:
                # Extract title from content or URL
                title = self._extract_title(content, url)
                
                web_content = WebContent(
                    id=hashlib.md5(url.encode()).hexdigest()[:16],
                    url=url,
                    title=title,
                    content=content,
                    source_type='web',
                    metadata={
                        'domain': urlparse(url).netloc
                    }
                )
                
                # Extract keywords and topics
                web_content.keywords = self._extract_keywords(content)
                web_content.topics = self._extract_topics(content)
                
                self.fetched_content[web_content.id] = web_content
                self.fetched_urls.add(url)
                self._save_content()
                
                self._record_request()
                self.fetch_count += 1
                self.last_fetch = datetime.now()
                
                logger.info(f"Fetched content from {url}")
                return web_content
            
        except Exception as e:
            logger.error(f"Error fetching URL {url}: {e}")
        
        return None
    
    def _extract_title(self, content: str, url: str) -> str:
        """Extract title from content or URL"""
        # Try to find title in first few lines
        lines = content.split('\n')[:10]
        for line in lines:
            line = line.strip()
            if 10 < len(line) < 200 and not line.startswith('http'):
                return line
        
        # Fallback to URL
        return urlparse(url).path.split('/')[-1].replace('-', ' ').title()
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        # Simple keyword extraction
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'can', 'shall',
                     'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
                     'and', 'or', 'but', 'not', 'so', 'if', 'then', 'than', 'too',
                     'very', 'just', 'about', 'above', 'after', 'again', 'all', 'am',
                     'any', 'as', 'at', 'be', 'because', 'before', 'below', 'between',
                     'both', 'but', 'by', 'can', 'did', 'do', 'does', 'down', 'during',
                     'each', 'few', 'for', 'from', 'further', 'get', 'got', 'had', 'has',
                     'have', 'he', 'her', 'here', 'hers', 'herself', 'him', 'himself',
                     'his', 'how', 'i', 'if', 'in', 'into', 'is', 'it', 'its', 'itself',
                     'me', 'more', 'most', 'my', 'myself', 'no', 'nor', 'not', 'now',
                     'of', 'off', 'on', 'once', 'only', 'or', 'other', 'our', 'ours',
                     'ourselves', 'out', 'over', 'own', 's', 'same', 'she', 'should',
                     'so', 'some', 'such', 't', 'than', 'that', 'the', 'their', 'theirs',
                     'them', 'themselves', 'then', 'there', 'these', 'they', 'this',
                     'those', 'through', 'to', 'too', 'under', 'until', 'up', 'very',
                     'was', 'we', 'were', 'what', 'when', 'where', 'which', 'while',
                     'who', 'whom', 'why', 'will', 'with', 'you', 'your', 'yours',
                     'yourself', 'yourselves'}
        
        words = re.findall(r'\b[a-z]{4,}\b', text.lower())
        keywords = [word for word in words if word not in stop_words]
        
        # Count frequency
        from collections import Counter
        word_freq = Counter(keywords)
        
        # Return top keywords
        return [word for word, freq in word_freq.most_common(20)]
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract topics from text"""
        # Simple topic extraction based on common categories
        topic_keywords = {
            'technology': ['technology', 'tech', 'software', 'hardware', 'computer', 'ai',
                          'artificial', 'intelligence', 'machine', 'learning', 'data',
                          'algorithm', 'programming', 'code', 'developer', 'app'],
            'science': ['science', 'scientific', 'research', 'study', 'experiment',
                       'discovery', 'physics', 'chemistry', 'biology', 'medicine'],
            'business': ['business', 'company', 'market', 'economy', 'finance',
                        'investment', 'startup', 'entrepreneur', 'industry'],
            'politics': ['politics', 'government', 'policy', 'election', 'vote',
                        'democrat', 'republican', 'law', 'legislation'],
            'health': ['health', 'medical', 'doctor', 'hospital', 'disease',
                      'treatment', 'patient', 'wellness', 'fitness'],
            'entertainment': ['entertainment', 'movie', 'film', 'music', 'game',
                            'celebrity', 'actor', 'actress', 'show', 'tv'],
            'sports': ['sports', 'game', 'team', 'player', 'match', 'score',
                      'championship', 'league', 'tournament'],
            'world': ['world', 'international', 'global', 'country', 'nation',
                     'war', 'peace', 'conflict', 'diplomacy']
        }
        
        text_lower = text.lower()
        detected_topics = []
        
        for topic, keywords in topic_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    detected_topics.append(topic)
                    break
        
        return list(set(detected_topics))
    
    async def continuous_learning(self, interval: int = 3600):
        """Continuously fetch and learn from web content"""
        logger.info(f"Starting continuous learning (interval: {interval}s)")
        
        while True:
            try:
                if self.enabled:
                    # Fetch RSS feeds
                    new_content = await self.fetch_rss_feeds()
                    
                    if new_content:
                        logger.info(f"Learned from {len(new_content)} new web sources")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in continuous learning: {e}")
                await asyncio.sleep(interval)
    
    def search_local_content(self, query: str, limit: int = 10) -> List[WebContent]:
        """Search locally stored web content"""
        results = []
        query_lower = query.lower()
        
        for content in self.fetched_content.values():
            if (query_lower in content.title.lower() or
                query_lower in content.content.lower() or
                any(query_lower in keyword for keyword in content.keywords)):
                results.append(content)
                if len(results) >= limit:
                    break
        
        return results
    
    def get_content_by_topic(self, topic: str, limit: int = 10) -> List[WebContent]:
        """Get content by topic"""
        results = []
        
        for content in self.fetched_content.values():
            if topic.lower() in [t.lower() for t in content.topics]:
                results.append(content)
                if len(results) >= limit:
                    break
        
        return results
    
    def get_recent_content(self, n: int = 10) -> List[WebContent]:
        """Get recently fetched content"""
        sorted_content = sorted(
            self.fetched_content.values(),
            key=lambda x: x.timestamp,
            reverse=True
        )
        return sorted_content[:n]
    
    def get_status(self) -> Dict[str, Any]:
        """Get web fetcher status"""
        return {
            'enabled': self.enabled,
            'total_content_fetched': len(self.fetched_content),
            'unique_urls': len(self.fetched_urls),
            'fetch_count': self.fetch_count,
            'last_fetch': self.last_fetch.isoformat() if self.last_fetch else None,
            'rss_feeds_configured': len(self.rss_feeds),
            'requests_this_hour': len(self.request_timestamps)
        }
