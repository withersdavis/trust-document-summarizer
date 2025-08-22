"""
Performance Optimizer - Comprehensive optimization system for RAG trust document processor
"""

import os
import time
import json
import hashlib
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from multiprocessing import Pool, cpu_count
from typing import List, Dict, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
from datetime import datetime, timedelta
import numpy as np

from semantic_extractor import Fact, SemanticFactExtractor
from vector_store import DocumentVectorStore
from rag_generator import RAGSummaryGenerator
from smart_chunker import SmartChunker, DocumentChunk
from cache_manager import CacheManager


@dataclass
class PerformanceMetrics:
    """Performance tracking metrics"""
    operation: str
    start_time: float
    end_time: float
    duration: float
    memory_usage: Dict[str, float]
    cache_hits: int
    cache_misses: int
    items_processed: int
    parallel_workers: int
    batch_size: int
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class OptimizationResult:
    """Result of optimization with metrics"""
    success: bool
    data: Any
    metrics: PerformanceMetrics
    optimizations_applied: List[str]
    error_message: str = ""


class PerformanceMonitor:
    """Monitor and track performance metrics"""
    
    def __init__(self):
        self.metrics_history: List[PerformanceMetrics] = []
        self.start_times: Dict[str, float] = {}
        self.cache_stats: Dict[str, Dict] = {}
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def start_operation(self, operation: str) -> None:
        """Start timing an operation"""
        self.start_times[operation] = time.time()
    
    def end_operation(self, operation: str, items_processed: int = 1, 
                     parallel_workers: int = 1, batch_size: int = 1) -> PerformanceMetrics:
        """End timing and create metrics"""
        end_time = time.time()
        start_time = self.start_times.get(operation, end_time)
        duration = end_time - start_time
        
        # Get memory usage
        memory_usage = self._get_memory_usage()
        
        # Get cache stats
        cache_hits = sum(stats.get('hits', 0) for stats in self.cache_stats.values())
        cache_misses = sum(stats.get('misses', 0) for stats in self.cache_stats.values())
        
        metrics = PerformanceMetrics(
            operation=operation,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            memory_usage=memory_usage,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            items_processed=items_processed,
            parallel_workers=parallel_workers,
            batch_size=batch_size
        )
        
        self.metrics_history.append(metrics)
        self.logger.info(f"Operation '{operation}' completed in {duration:.2f}s")
        
        return metrics
    
    def _get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage"""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            return {
                'rss': memory_info.rss / 1024 / 1024,  # MB
                'vms': memory_info.vms / 1024 / 1024,  # MB
                'percent': process.memory_percent()
            }
        except ImportError:
            return {'rss': 0, 'vms': 0, 'percent': 0}
    
    def update_cache_stats(self, cache_name: str, stats: Dict):
        """Update cache statistics"""
        self.cache_stats[cache_name] = stats
    
    def get_optimization_report(self) -> Dict:
        """Generate comprehensive optimization report"""
        if not self.metrics_history:
            return {"error": "No metrics available"}
        
        recent_metrics = self.metrics_history[-10:]  # Last 10 operations
        
        # Calculate averages
        avg_duration = np.mean([m.duration for m in recent_metrics])
        total_cache_hits = sum(m.cache_hits for m in recent_metrics)
        total_cache_misses = sum(m.cache_misses for m in recent_metrics)
        cache_hit_rate = total_cache_hits / max(1, total_cache_hits + total_cache_misses)
        
        # Memory statistics
        memory_stats = [m.memory_usage for m in recent_metrics if m.memory_usage]
        avg_memory = np.mean([m['rss'] for m in memory_stats]) if memory_stats else 0
        
        return {
            'summary': {
                'operations_tracked': len(self.metrics_history),
                'average_duration': avg_duration,
                'cache_hit_rate': cache_hit_rate,
                'average_memory_mb': avg_memory
            },
            'recent_operations': [m.to_dict() for m in recent_metrics],
            'cache_statistics': self.cache_stats,
            'recommendations': self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []
        
        if not self.metrics_history:
            return recommendations
        
        # Analyze recent metrics
        recent = self.metrics_history[-5:]
        
        # Check cache hit rate
        total_hits = sum(m.cache_hits for m in recent)
        total_misses = sum(m.cache_misses for m in recent)
        if total_hits + total_misses > 0:
            hit_rate = total_hits / (total_hits + total_misses)
            if hit_rate < 0.5:
                recommendations.append("Consider increasing cache size or adjusting cache policies")
        
        # Check parallelization usage
        avg_workers = np.mean([m.parallel_workers for m in recent])
        if avg_workers < 2:
            recommendations.append("Consider using more parallel workers for large operations")
        
        # Check batch sizes
        avg_batch = np.mean([m.batch_size for m in recent])
        if avg_batch < 10:
            recommendations.append("Consider increasing batch sizes for better throughput")
        
        return recommendations


class BatchProcessor:
    """Optimized batch processing for documents and facts"""
    
    def __init__(self, max_workers: int = None, batch_size: int = 50):
        self.max_workers = max_workers or min(cpu_count(), 8)
        self.batch_size = batch_size
        self.logger = logging.getLogger(__name__)
    
    def parallel_fact_extraction(self, chunks: List[DocumentChunk]) -> List[Fact]:
        """Extract facts from chunks in parallel"""
        self.logger.info(f"Starting parallel fact extraction for {len(chunks)} chunks")
        
        def extract_chunk_facts(chunk: DocumentChunk) -> List[Fact]:
            extractor = SemanticFactExtractor()
            return extractor.extract_facts(
                chunk.text,
                chunk.start_page,
                chunk.start_char
            )
        
        all_facts = []
        
        # Process chunks in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(extract_chunk_facts, chunk): i 
                for i, chunk in enumerate(chunks)
            }
            
            # Collect results
            for future in as_completed(futures):
                try:
                    chunk_facts = future.result()
                    all_facts.extend(chunk_facts)
                except Exception as e:
                    self.logger.error(f"Error processing chunk: {e}")
        
        self.logger.info(f"Extracted {len(all_facts)} facts from {len(chunks)} chunks")
        return all_facts
    
    def batch_vector_operations(self, vector_store: DocumentVectorStore, 
                               facts: List[Fact], document_id: str) -> int:
        """Batch vector database operations for efficiency"""
        if not facts:
            return 0
        
        # Group facts into batches
        batches = [facts[i:i + self.batch_size] 
                  for i in range(0, len(facts), self.batch_size)]
        
        self.logger.info(f"Indexing {len(facts)} facts in {len(batches)} batches")
        
        total_indexed = 0
        for i, batch in enumerate(batches):
            try:
                count = vector_store.index_facts(batch, document_id)
                total_indexed += count
                
                if (i + 1) % 10 == 0 or (i + 1) == len(batches):
                    self.logger.info(f"Processed batch {i + 1}/{len(batches)}")
                    
            except Exception as e:
                self.logger.error(f"Error in batch {i + 1}: {e}")
        
        return total_indexed
    
    def parallel_document_processing(self, pdf_paths: List[str], 
                                   processor_func) -> List[OptimizationResult]:
        """Process multiple documents in parallel"""
        self.logger.info(f"Processing {len(pdf_paths)} documents in parallel")
        
        results = []
        
        with ProcessPoolExecutor(max_workers=min(len(pdf_paths), self.max_workers)) as executor:
            # Submit all tasks
            futures = {
                executor.submit(processor_func, pdf_path): pdf_path 
                for pdf_path in pdf_paths
            }
            
            # Collect results
            for future in as_completed(futures):
                pdf_path = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    self.logger.info(f"Completed processing: {Path(pdf_path).name}")
                except Exception as e:
                    self.logger.error(f"Error processing {pdf_path}: {e}")
                    # Create error result
                    error_result = OptimizationResult(
                        success=False,
                        data={},
                        metrics=PerformanceMetrics(
                            operation="document_processing",
                            start_time=time.time(),
                            end_time=time.time(),
                            duration=0,
                            memory_usage={},
                            cache_hits=0,
                            cache_misses=0,
                            items_processed=0,
                            parallel_workers=1,
                            batch_size=1
                        ),
                        optimizations_applied=[],
                        error_message=str(e)
                    )
                    results.append(error_result)
        
        return results


class QueryOptimizer:
    """Optimize semantic search queries with caching and indexing"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.query_embeddings_cache = {}
        self.common_queries = [
            "trust creation date grantor settlor",
            "beneficiary distribution rules",
            "trustee powers authority",
            "tax provisions estate gift",
            "termination conditions end trust"
        ]
        self.logger = logging.getLogger(__name__)
    
    def precompute_common_embeddings(self, vector_store: DocumentVectorStore):
        """Pre-compute embeddings for common queries"""
        self.logger.info("Pre-computing embeddings for common queries")
        
        for query in self.common_queries:
            try:
                # Perform search to cache the embedding
                vector_store.semantic_search(query, top_k=1)
                self.logger.debug(f"Pre-computed embedding for: {query}")
            except Exception as e:
                self.logger.error(f"Error pre-computing embedding for '{query}': {e}")
    
    def optimized_search(self, vector_store: DocumentVectorStore, 
                        query: str, top_k: int = 10, 
                        filters: Dict = None) -> Tuple[List[Dict], bool]:
        """Perform optimized semantic search with caching"""
        # Create cache key
        cache_key = self._create_search_cache_key(query, top_k, filters)
        
        # Check cache first
        cached_result = self.cache_manager.get_search_result(cache_key)
        if cached_result:
            return cached_result, True  # Cache hit
        
        # Perform search
        results = vector_store.semantic_search(query, top_k, filters)
        
        # Cache the result
        self.cache_manager.cache_search_result(cache_key, results)
        
        return results, False  # Cache miss
    
    def _create_search_cache_key(self, query: str, top_k: int, 
                                filters: Dict = None) -> str:
        """Create cache key for search"""
        key_parts = [query, str(top_k)]
        if filters:
            key_parts.append(json.dumps(filters, sort_keys=True))
        
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()


class ResourceManager:
    """Manage resources and connections efficiently"""
    
    def __init__(self):
        self.vector_store_pool = {}
        self.llm_client_pool = {}
        self.connection_stats = {}
        self.logger = logging.getLogger(__name__)
    
    def get_vector_store(self, collection_name: str = "trust_facts") -> DocumentVectorStore:
        """Get vector store from pool"""
        if collection_name not in self.vector_store_pool:
            self.vector_store_pool[collection_name] = DocumentVectorStore(collection_name)
            self.logger.debug(f"Created new vector store: {collection_name}")
        
        return self.vector_store_pool[collection_name]
    
    def batch_llm_calls(self, prompts: List[str], model: str = "claude-3-haiku-20240307") -> List[str]:
        """Batch LLM API calls for efficiency"""
        self.logger.info(f"Processing {len(prompts)} LLM requests in batch")
        
        results = []
        
        # Group prompts into reasonable batches (API limits)
        batch_size = 5
        batches = [prompts[i:i + batch_size] for i in range(0, len(prompts), batch_size)]
        
        for batch in batches:
            batch_results = self._process_llm_batch(batch, model)
            results.extend(batch_results)
            
            # Small delay to respect rate limits
            time.sleep(0.1)
        
        return results
    
    def _process_llm_batch(self, prompts: List[str], model: str) -> List[str]:
        """Process a batch of LLM prompts"""
        results = []
        
        try:
            from anthropic import Anthropic
            client = Anthropic()
            
            for prompt in prompts:
                response = client.messages.create(
                    model=model,
                    max_tokens=500,
                    temperature=0.3,
                    messages=[{"role": "user", "content": prompt}]
                )
                results.append(response.content[0].text)
        except Exception as e:
            self.logger.error(f"Error in LLM batch processing: {e}")
            # Return empty results on error
            results = ["Error: Unable to process request"] * len(prompts)
        
        return results


class RAGPerformanceOptimizer:
    """Main performance optimizer class"""
    
    def __init__(self, use_cache: bool = True, max_workers: int = None):
        self.use_cache = use_cache
        self.cache_manager = CacheManager() if use_cache else None
        self.performance_monitor = PerformanceMonitor()
        self.batch_processor = BatchProcessor(max_workers)
        self.query_optimizer = QueryOptimizer(self.cache_manager) if use_cache else None
        self.resource_manager = ResourceManager()
        self.logger = logging.getLogger(__name__)
    
    def optimize_document_processing(self, pdf_path: str) -> OptimizationResult:
        """Optimize processing of a single document"""
        self.performance_monitor.start_operation("optimize_document_processing")
        optimizations_applied = []
        
        try:
            # Check cache for full document processing
            if self.cache_manager:
                doc_hash = self.cache_manager._get_file_hash(pdf_path)
                cached_summary = self.cache_manager.get_summary(doc_hash)
                if cached_summary:
                    optimizations_applied.append("summary_cache_hit")
                    metrics = self.performance_monitor.end_operation(
                        "optimize_document_processing", 1, 1, 1
                    )
                    return OptimizationResult(
                        success=True,
                        data=cached_summary,
                        metrics=metrics,
                        optimizations_applied=optimizations_applied
                    )
            
            # Extract text and create chunks
            from pdf_processor import PDFProcessor
            pdf_processor = PDFProcessor(use_cache=self.use_cache)
            full_text, pages = pdf_processor.extract_text_from_pdf(pdf_path)
            
            # Determine processing strategy
            if len(full_text) > 50000:  # Large document
                optimizations_applied.append("chunked_processing")
                chunker = SmartChunker()
                chunks = chunker.chunk_document(pages)
                
                # Parallel fact extraction
                optimizations_applied.append("parallel_fact_extraction")
                facts = self.batch_processor.parallel_fact_extraction(chunks)
            else:
                # Standard processing with caching
                optimizations_applied.append("standard_processing")
                extractor = SemanticFactExtractor()
                facts = extractor.extract_from_pages(pages)
            
            # Deduplicate and rank
            extractor = SemanticFactExtractor()
            facts = extractor.deduplicate_facts(facts)
            facts = extractor.rank_facts_by_importance(facts)
            
            # Cache facts if enabled
            if self.cache_manager:
                doc_hash = self.cache_manager._get_file_hash(pdf_path)
                self.cache_manager.cache_facts(doc_hash, facts)
                optimizations_applied.append("facts_cached")
            
            # Optimized vector indexing
            vector_store = self.resource_manager.get_vector_store()
            doc_id = Path(pdf_path).stem
            
            # Batch vector operations
            optimizations_applied.append("batch_vector_operations")
            self.batch_processor.batch_vector_operations(vector_store, facts, doc_id)
            
            # Pre-compute common query embeddings
            if self.query_optimizer:
                self.query_optimizer.precompute_common_embeddings(vector_store)
                optimizations_applied.append("precomputed_embeddings")
            
            # Generate summary with optimizations
            generator = RAGSummaryGenerator(vector_store)
            summary = generator.generate_summary(pdf_path, facts)
            
            # Cache summary
            if self.cache_manager:
                doc_hash = self.cache_manager._get_file_hash(pdf_path)
                self.cache_manager.cache_summary(doc_hash, summary)
                optimizations_applied.append("summary_cached")
            
            metrics = self.performance_monitor.end_operation(
                "optimize_document_processing",
                items_processed=len(facts),
                parallel_workers=self.batch_processor.max_workers,
                batch_size=self.batch_processor.batch_size
            )
            
            return OptimizationResult(
                success=True,
                data=summary,
                metrics=metrics,
                optimizations_applied=optimizations_applied
            )
            
        except Exception as e:
            self.logger.error(f"Error in optimized processing: {e}")
            metrics = self.performance_monitor.end_operation("optimize_document_processing")
            return OptimizationResult(
                success=False,
                data={},
                metrics=metrics,
                optimizations_applied=optimizations_applied,
                error_message=str(e)
            )
    
    def optimize_batch_processing(self, pdf_paths: List[str]) -> List[OptimizationResult]:
        """Optimize batch processing of multiple documents"""
        self.performance_monitor.start_operation("optimize_batch_processing")
        
        # Process documents in parallel
        results = self.batch_processor.parallel_document_processing(
            pdf_paths, 
            self.optimize_document_processing
        )
        
        metrics = self.performance_monitor.end_operation(
            "optimize_batch_processing",
            items_processed=len(pdf_paths),
            parallel_workers=self.batch_processor.max_workers,
            batch_size=len(pdf_paths)
        )
        
        self.logger.info(f"Batch processing completed: {len(results)} results")
        return results
    
    def optimize_semantic_search(self, vector_store: DocumentVectorStore,
                                query: str, top_k: int = 10) -> Tuple[List[Dict], Dict]:
        """Perform optimized semantic search"""
        self.performance_monitor.start_operation("optimize_semantic_search")
        
        if self.query_optimizer:
            results, cache_hit = self.query_optimizer.optimized_search(
                vector_store, query, top_k
            )
            optimization_info = {"cache_hit": cache_hit}
        else:
            results = vector_store.semantic_search(query, top_k)
            optimization_info = {"cache_hit": False}
        
        metrics = self.performance_monitor.end_operation(
            "optimize_semantic_search",
            items_processed=len(results)
        )
        
        optimization_info["metrics"] = metrics
        return results, optimization_info
    
    def get_performance_report(self) -> Dict:
        """Get comprehensive performance report"""
        report = self.performance_monitor.get_optimization_report()
        
        # Add cache statistics if available
        if self.cache_manager:
            cache_stats = self.cache_manager.get_cache_stats()
            report["cache_statistics"] = cache_stats
            self.performance_monitor.update_cache_stats("main_cache", cache_stats)
        
        return report
    
    def clear_caches(self):
        """Clear all caches"""
        if self.cache_manager:
            self.cache_manager.clear_all_caches()
            self.logger.info("All caches cleared")


def optimize_document_processing(pdf_path: str, use_cache: bool = True) -> OptimizationResult:
    """
    Convenience function to optimize single document processing
    """
    optimizer = RAGPerformanceOptimizer(use_cache=use_cache)
    return optimizer.optimize_document_processing(pdf_path)


def optimize_batch_processing(pdf_paths: List[str], use_cache: bool = True) -> List[OptimizationResult]:
    """
    Convenience function to optimize batch processing
    """
    optimizer = RAGPerformanceOptimizer(use_cache=use_cache)
    return optimizer.optimize_batch_processing(pdf_paths)


if __name__ == "__main__":
    import sys
    
    # Test optimization system
    print("\n" + "="*80)
    print("PERFORMANCE OPTIMIZATION SYSTEM TEST")
    print("="*80)
    
    # Test single document optimization
    test_pdf = "data/2006 Eric Russell ILIT.pdf"
    if Path(test_pdf).exists():
        print(f"\n📊 Testing single document optimization: {Path(test_pdf).name}")
        
        # Test with cache
        optimizer = RAGPerformanceOptimizer(use_cache=True)
        result = optimizer.optimize_document_processing(test_pdf)
        
        if result.success:
            print(f"✅ Optimization successful!")
            print(f"  - Processing time: {result.metrics.duration:.2f}s")
            print(f"  - Items processed: {result.metrics.items_processed}")
            print(f"  - Cache hits: {result.metrics.cache_hits}")
            print(f"  - Memory usage: {result.metrics.memory_usage.get('rss', 0):.1f}MB")
            print(f"  - Optimizations applied: {', '.join(result.optimizations_applied)}")
        else:
            print(f"❌ Optimization failed: {result.error_message}")
        
        # Test second run to check caching
        print(f"\n🔄 Testing cache effectiveness (second run):")
        result2 = optimizer.optimize_document_processing(test_pdf)
        
        if result2.success:
            print(f"✅ Second run completed!")
            print(f"  - Processing time: {result2.metrics.duration:.2f}s")
            print(f"  - Cache hits: {result2.metrics.cache_hits}")
            print(f"  - Optimizations applied: {', '.join(result2.optimizations_applied)}")
            
            # Calculate speedup
            speedup = result.metrics.duration / max(0.001, result2.metrics.duration)
            print(f"  - Speedup: {speedup:.1f}x faster")
        
        # Generate performance report
        print(f"\n📈 Performance Report:")
        report = optimizer.get_performance_report()
        print(f"  - Operations tracked: {report['summary']['operations_tracked']}")
        print(f"  - Average duration: {report['summary']['average_duration']:.2f}s")
        print(f"  - Cache hit rate: {report['summary']['cache_hit_rate']:.1%}")
        print(f"  - Average memory: {report['summary']['average_memory_mb']:.1f}MB")
        
        if report.get('recommendations'):
            print(f"  - Recommendations:")
            for rec in report['recommendations']:
                print(f"    • {rec}")
    
    else:
        print(f"⚠️  Test file not found: {test_pdf}")
    
    print(f"\n✅ Performance optimization system test completed")