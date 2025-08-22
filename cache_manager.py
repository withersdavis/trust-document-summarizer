"""
Advanced Cache Manager - Comprehensive caching system for RAG optimization
"""

import os
import json
import pickle
import hashlib
import sqlite3
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
from datetime import datetime, timedelta
import time
import logging
import threading
from dataclasses import dataclass, asdict
import numpy as np

from semantic_extractor import Fact


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    data: Any
    created_at: datetime
    accessed_at: datetime
    access_count: int
    size_bytes: int
    ttl_seconds: int
    version: str
    tags: List[str]
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.ttl_seconds <= 0:
            return False
        return datetime.now() > (self.created_at + timedelta(seconds=self.ttl_seconds))
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['accessed_at'] = self.accessed_at.isoformat()
        return data


class CacheStats:
    """Cache statistics tracker"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.storage_bytes = 0
        self.entries_count = 0
        self.start_time = datetime.now()
        self.lock = threading.Lock()
    
    def record_hit(self):
        """Record cache hit"""
        with self.lock:
            self.hits += 1
    
    def record_miss(self):
        """Record cache miss"""
        with self.lock:
            self.misses += 1
    
    def record_eviction(self, size_bytes: int = 0):
        """Record cache eviction"""
        with self.lock:
            self.evictions += 1
            self.storage_bytes -= size_bytes
            self.entries_count -= 1
    
    def record_storage(self, size_bytes: int):
        """Record storage addition"""
        with self.lock:
            self.storage_bytes += size_bytes
            self.entries_count += 1
    
    def get_hit_rate(self) -> float:
        """Calculate hit rate"""
        total = self.hits + self.misses
        return self.hits / max(1, total)
    
    def get_stats(self) -> Dict:
        """Get statistics dictionary"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        return {
            'hits': self.hits,
            'misses': self.misses,
            'evictions': self.evictions,
            'hit_rate': self.get_hit_rate(),
            'entries_count': self.entries_count,
            'storage_mb': self.storage_bytes / (1024 * 1024),
            'uptime_hours': uptime / 3600
        }


class LRUCache:
    """LRU (Least Recently Used) Cache implementation"""
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 500):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache: Dict[str, CacheEntry] = {}
        self.access_order: List[str] = []
        self.stats = CacheStats()
        self.lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        with self.lock:
            if key not in self.cache:
                self.stats.record_miss()
                return None
            
            entry = self.cache[key]
            
            # Check if expired
            if entry.is_expired():
                self._remove_entry(key)
                self.stats.record_miss()
                return None
            
            # Update access info
            entry.accessed_at = datetime.now()
            entry.access_count += 1
            
            # Move to front of access order
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)
            
            self.stats.record_hit()
            return entry.data
    
    def put(self, key: str, data: Any, ttl_seconds: int = 3600, 
            version: str = "1.0", tags: List[str] = None) -> bool:
        """Put item in cache"""
        with self.lock:
            # Calculate size
            size_bytes = self._calculate_size(data)
            
            # Check if item is too large
            if size_bytes > self.max_memory_bytes:
                self.logger.warning(f"Item too large for cache: {size_bytes} bytes")
                return False
            
            # Remove existing entry if present
            if key in self.cache:
                self._remove_entry(key)
            
            # Ensure space is available
            self._ensure_space(size_bytes)
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                data=data,
                created_at=datetime.now(),
                accessed_at=datetime.now(),
                access_count=1,
                size_bytes=size_bytes,
                ttl_seconds=ttl_seconds,
                version=version,
                tags=tags or []
            )
            
            # Add to cache
            self.cache[key] = entry
            self.access_order.append(key)
            self.stats.record_storage(size_bytes)
            
            return True
    
    def _ensure_space(self, needed_bytes: int):
        """Ensure enough space is available in cache"""
        # Check memory constraint
        while (self.stats.storage_bytes + needed_bytes > self.max_memory_bytes and 
               self.cache):
            oldest_key = self.access_order[0]
            self._remove_entry(oldest_key)
        
        # Check size constraint
        while len(self.cache) >= self.max_size and self.cache:
            oldest_key = self.access_order[0]
            self._remove_entry(oldest_key)
    
    def _remove_entry(self, key: str):
        """Remove entry from cache"""
        if key in self.cache:
            entry = self.cache[key]
            del self.cache[key]
            if key in self.access_order:
                self.access_order.remove(key)
            self.stats.record_eviction(entry.size_bytes)
    
    def _calculate_size(self, data: Any) -> int:
        """Calculate size of data in bytes"""
        try:
            return len(pickle.dumps(data))
        except:
            return len(str(data).encode())
    
    def clear(self):
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.access_order.clear()
            self.stats.storage_bytes = 0
            self.stats.entries_count = 0
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        return self.stats.get_stats()


class PersistentCache:
    """Persistent cache using SQLite database"""
    
    def __init__(self, db_path: str = "cache.db"):
        self.db_path = db_path
        self.stats = CacheStats()
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    data BLOB,
                    created_at TEXT,
                    accessed_at TEXT,
                    access_count INTEGER,
                    size_bytes INTEGER,
                    ttl_seconds INTEGER,
                    version TEXT,
                    tags TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at ON cache_entries(created_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_accessed_at ON cache_entries(accessed_at)
            """)
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from persistent cache"""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT data, created_at, ttl_seconds, access_count FROM cache_entries WHERE key = ?",
                        (key,)
                    )
                    row = cursor.fetchone()
                    
                    if not row:
                        self.stats.record_miss()
                        return None
                    
                    data_blob, created_at_str, ttl_seconds, access_count = row
                    
                    # Check expiration
                    created_at = datetime.fromisoformat(created_at_str)
                    if ttl_seconds > 0 and datetime.now() > (created_at + timedelta(seconds=ttl_seconds)):
                        # Remove expired entry
                        cursor.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                        self.stats.record_miss()
                        return None
                    
                    # Update access info
                    cursor.execute(
                        "UPDATE cache_entries SET accessed_at = ?, access_count = ? WHERE key = ?",
                        (datetime.now().isoformat(), access_count + 1, key)
                    )
                    
                    # Deserialize data
                    data = pickle.loads(data_blob)
                    self.stats.record_hit()
                    return data
                    
            except Exception as e:
                self.logger.error(f"Error getting from persistent cache: {e}")
                self.stats.record_miss()
                return None
    
    def put(self, key: str, data: Any, ttl_seconds: int = 86400, 
            version: str = "1.0", tags: List[str] = None) -> bool:
        """Put item in persistent cache"""
        with self.lock:
            try:
                # Serialize data
                data_blob = pickle.dumps(data)
                size_bytes = len(data_blob)
                
                now = datetime.now().isoformat()
                tags_str = json.dumps(tags or [])
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Insert or replace entry
                    cursor.execute("""
                        INSERT OR REPLACE INTO cache_entries 
                        (key, data, created_at, accessed_at, access_count, size_bytes, ttl_seconds, version, tags)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (key, data_blob, now, now, 1, size_bytes, ttl_seconds, version, tags_str))
                    
                    self.stats.record_storage(size_bytes)
                    return True
                    
            except Exception as e:
                self.logger.error(f"Error putting to persistent cache: {e}")
                return False
    
    def clear(self):
        """Clear all entries from persistent cache"""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM cache_entries")
                    self.stats.storage_bytes = 0
                    self.stats.entries_count = 0
            except Exception as e:
                self.logger.error(f"Error clearing persistent cache: {e}")
    
    def cleanup_expired(self) -> int:
        """Clean up expired entries"""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Find expired entries
                    now = datetime.now()
                    cursor.execute("""
                        SELECT key, created_at, ttl_seconds 
                        FROM cache_entries 
                        WHERE ttl_seconds > 0
                    """)
                    
                    expired_keys = []
                    for key, created_at_str, ttl_seconds in cursor.fetchall():
                        created_at = datetime.fromisoformat(created_at_str)
                        if now > (created_at + timedelta(seconds=ttl_seconds)):
                            expired_keys.append(key)
                    
                    # Remove expired entries
                    if expired_keys:
                        placeholders = ','.join(['?' for _ in expired_keys])
                        cursor.execute(f"DELETE FROM cache_entries WHERE key IN ({placeholders})", expired_keys)
                    
                    return len(expired_keys)
                    
            except Exception as e:
                self.logger.error(f"Error cleaning up expired entries: {e}")
                return 0
    
    def get_stats(self) -> Dict:
        """Get persistent cache statistics"""
        return self.stats.get_stats()


class CacheManager:
    """Advanced cache manager with multiple cache layers"""
    
    def __init__(self, cache_dir: str = "cache", 
                 memory_cache_size: int = 1000,
                 memory_cache_mb: int = 500):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize cache layers
        self.memory_cache = LRUCache(memory_cache_size, memory_cache_mb)
        self.persistent_cache = PersistentCache(str(self.cache_dir / "persistent.db"))
        
        # Cache-specific configurations
        self.cache_configs = {
            'facts': {'ttl': 3600 * 24, 'memory': True, 'persistent': True},  # 24 hours
            'embeddings': {'ttl': 3600 * 24 * 7, 'memory': True, 'persistent': True},  # 7 days
            'summaries': {'ttl': 3600 * 2, 'memory': True, 'persistent': True},  # 2 hours
            'search_results': {'ttl': 3600, 'memory': True, 'persistent': False},  # 1 hour, memory only
        }
        
        self.logger = logging.getLogger(__name__)
        
        # Start background cleanup task
        self._start_cleanup_task()
    
    def _get_file_hash(self, file_path: str) -> str:
        """Get file hash for cache key"""
        try:
            file_path = Path(file_path)
            stat = file_path.stat()
            # Use file path, size, and modification time
            content = f"{file_path}_{stat.st_size}_{stat.st_mtime}"
            return hashlib.md5(content.encode()).hexdigest()
        except:
            return hashlib.md5(str(file_path).encode()).hexdigest()
    
    def cache_facts(self, document_hash: str, facts: List[Fact]) -> bool:
        """Cache extracted facts"""
        key = f"facts_{document_hash}"
        config = self.cache_configs['facts']
        
        # Serialize facts
        fact_dicts = [fact.to_dict() for fact in facts]
        
        success = True
        if config['memory']:
            success &= self.memory_cache.put(key, fact_dicts, config['ttl'], tags=['facts'])
        
        if config['persistent']:
            success &= self.persistent_cache.put(key, fact_dicts, config['ttl'], tags=['facts'])
        
        self.logger.debug(f"Cached {len(facts)} facts for document {document_hash[:8]}")
        return success
    
    def get_facts(self, document_hash: str) -> Optional[List[Fact]]:
        """Get cached facts"""
        key = f"facts_{document_hash}"
        
        # Try memory cache first
        fact_dicts = self.memory_cache.get(key)
        if fact_dicts is not None:
            # Reconstruct Fact objects
            facts = []
            for fact_dict in fact_dicts:
                fact = Fact(**fact_dict)
                facts.append(fact)
            return facts
        
        # Try persistent cache
        fact_dicts = self.persistent_cache.get(key)
        if fact_dicts is not None:
            # Store in memory cache for next access
            self.memory_cache.put(key, fact_dicts, self.cache_configs['facts']['ttl'])
            
            # Reconstruct Fact objects
            facts = []
            for fact_dict in fact_dicts:
                fact = Fact(**fact_dict)
                facts.append(fact)
            return facts
        
        return None
    
    def cache_embeddings(self, text_hash: str, embeddings: np.ndarray) -> bool:
        """Cache text embeddings"""
        key = f"embeddings_{text_hash}"
        config = self.cache_configs['embeddings']
        
        # Convert numpy array to list for serialization
        embeddings_list = embeddings.tolist() if isinstance(embeddings, np.ndarray) else embeddings
        
        success = True
        if config['memory']:
            success &= self.memory_cache.put(key, embeddings_list, config['ttl'], tags=['embeddings'])
        
        if config['persistent']:
            success &= self.persistent_cache.put(key, embeddings_list, config['ttl'], tags=['embeddings'])
        
        return success
    
    def get_embeddings(self, text_hash: str) -> Optional[np.ndarray]:
        """Get cached embeddings"""
        key = f"embeddings_{text_hash}"
        
        # Try memory cache first
        embeddings_list = self.memory_cache.get(key)
        if embeddings_list is not None:
            return np.array(embeddings_list)
        
        # Try persistent cache
        embeddings_list = self.persistent_cache.get(key)
        if embeddings_list is not None:
            # Store in memory cache
            self.memory_cache.put(key, embeddings_list, self.cache_configs['embeddings']['ttl'])
            return np.array(embeddings_list)
        
        return None
    
    def cache_summary(self, document_hash: str, summary: Dict, version: str = "1.0") -> bool:
        """Cache RAG summary"""
        key = f"summary_{document_hash}_{version}"
        config = self.cache_configs['summaries']
        
        success = True
        if config['memory']:
            success &= self.memory_cache.put(key, summary, config['ttl'], version, ['summaries'])
        
        if config['persistent']:
            success &= self.persistent_cache.put(key, summary, config['ttl'], version, ['summaries'])
        
        self.logger.debug(f"Cached summary for document {document_hash[:8]} version {version}")
        return success
    
    def get_summary(self, document_hash: str, version: str = "1.0") -> Optional[Dict]:
        """Get cached summary"""
        key = f"summary_{document_hash}_{version}"
        
        # Try memory cache first
        summary = self.memory_cache.get(key)
        if summary is not None:
            return summary
        
        # Try persistent cache
        summary = self.persistent_cache.get(key)
        if summary is not None:
            # Store in memory cache
            self.memory_cache.put(key, summary, self.cache_configs['summaries']['ttl'])
            return summary
        
        return None
    
    def cache_search_result(self, query_hash: str, results: List[Dict]) -> bool:
        """Cache search results"""
        key = f"search_{query_hash}"
        config = self.cache_configs['search_results']
        
        # Only use memory cache for search results (short TTL)
        return self.memory_cache.put(key, results, config['ttl'], tags=['search'])
    
    def get_search_result(self, query_hash: str) -> Optional[List[Dict]]:
        """Get cached search results"""
        key = f"search_{query_hash}"
        return self.memory_cache.get(key)
    
    def invalidate_document(self, document_hash: str):
        """Invalidate all cache entries for a document"""
        # Clear from memory cache
        keys_to_remove = [key for key in self.memory_cache.cache.keys() 
                         if document_hash in key]
        for key in keys_to_remove:
            self.memory_cache._remove_entry(key)
        
        # Clear from persistent cache
        try:
            with sqlite3.connect(self.persistent_cache.db_path) as conn:
                conn.execute("DELETE FROM cache_entries WHERE key LIKE ?", (f"%{document_hash}%",))
        except Exception as e:
            self.logger.error(f"Error invalidating document cache: {e}")
        
        self.logger.info(f"Invalidated cache for document {document_hash[:8]}")
    
    def get_cache_stats(self) -> Dict:
        """Get comprehensive cache statistics"""
        memory_stats = self.memory_cache.get_stats()
        persistent_stats = self.persistent_cache.get_stats()
        
        return {
            'memory_cache': memory_stats,
            'persistent_cache': persistent_stats,
            'total_hit_rate': (memory_stats['hits'] + persistent_stats['hits']) / 
                            max(1, memory_stats['hits'] + memory_stats['misses'] + 
                                persistent_stats['hits'] + persistent_stats['misses']),
            'cache_configs': self.cache_configs
        }
    
    def clear_all_caches(self):
        """Clear all cache layers"""
        self.memory_cache.clear()
        self.persistent_cache.clear()
        self.logger.info("All caches cleared")
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(3600)  # Run every hour
                    expired_count = self.persistent_cache.cleanup_expired()
                    if expired_count > 0:
                        self.logger.info(f"Cleaned up {expired_count} expired cache entries")
                except Exception as e:
                    self.logger.error(f"Error in cache cleanup: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()


if __name__ == "__main__":
    # Test cache manager
    print("\n" + "="*60)
    print("ADVANCED CACHE MANAGER TEST")
    print("="*60)
    
    # Create cache manager
    cache_manager = CacheManager()
    
    # Test fact caching
    print("\n1. Testing fact caching...")
    from semantic_extractor import Fact
    
    test_facts = [
        Fact("Test fact 1", 1, 100, "test", 0.9, [], "context 1"),
        Fact("Test fact 2", 2, 200, "test", 0.8, [], "context 2"),
    ]
    
    doc_hash = "test_doc_123"
    success = cache_manager.cache_facts(doc_hash, test_facts)
    print(f"  - Cached facts: {success}")
    
    # Retrieve facts
    retrieved_facts = cache_manager.get_facts(doc_hash)
    print(f"  - Retrieved {len(retrieved_facts)} facts" if retrieved_facts else "  - No facts retrieved")
    
    # Test summary caching
    print("\n2. Testing summary caching...")
    test_summary = {
        'meta': {'processing_method': 'test'},
        'summary': {'executive': 'Test executive summary'},
        'citations': {'001': {'page': 1, 'text': 'Test citation'}}
    }
    
    success = cache_manager.cache_summary(doc_hash, test_summary)
    print(f"  - Cached summary: {success}")
    
    # Retrieve summary
    retrieved_summary = cache_manager.get_summary(doc_hash)
    print(f"  - Retrieved summary: {bool(retrieved_summary)}")
    
    # Test search result caching
    print("\n3. Testing search result caching...")
    test_results = [
        {'id': '1', 'score': 0.9, 'text': 'Result 1'},
        {'id': '2', 'score': 0.8, 'text': 'Result 2'}
    ]
    
    query_hash = hashlib.md5("test query".encode()).hexdigest()
    success = cache_manager.cache_search_result(query_hash, test_results)
    print(f"  - Cached search results: {success}")
    
    # Retrieve search results
    retrieved_results = cache_manager.get_search_result(query_hash)
    print(f"  - Retrieved {len(retrieved_results)} results" if retrieved_results else "  - No results retrieved")
    
    # Test cache statistics
    print("\n4. Cache statistics:")
    stats = cache_manager.get_cache_stats()
    print(f"  - Memory cache hit rate: {stats['memory_cache']['hit_rate']:.1%}")
    print(f"  - Memory cache entries: {stats['memory_cache']['entries_count']}")
    print(f"  - Memory cache storage: {stats['memory_cache']['storage_mb']:.1f}MB")
    print(f"  - Persistent cache hit rate: {stats['persistent_cache']['hit_rate']:.1%}")
    print(f"  - Total hit rate: {stats['total_hit_rate']:.1%}")
    
    # Test cache invalidation
    print("\n5. Testing cache invalidation...")
    cache_manager.invalidate_document(doc_hash)
    
    # Try to retrieve after invalidation
    retrieved_after = cache_manager.get_facts(doc_hash)
    print(f"  - Facts after invalidation: {bool(retrieved_after)}")
    
    print(f"\n✅ Cache manager test completed")