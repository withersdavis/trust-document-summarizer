#!/usr/bin/env python3
"""
Performance Optimization Demo - Quick demonstration of performance improvements
"""

import time
import os
from pathlib import Path
from performance_optimizer import RAGPerformanceOptimizer
from rag_processor import RAGTrustProcessor


def quick_performance_demo():
    """Quick demonstration of performance optimization"""
    print("\n" + "="*60)
    print("RAG PERFORMANCE OPTIMIZATION DEMO")
    print("="*60)
    
    # Test with a small document
    test_file = "data/2006 Eric Russell ILIT.pdf"
    if not Path(test_file).exists():
        print(f"❌ Test file not found: {test_file}")
        return
    
    print(f"📄 Testing with: {Path(test_file).name}")
    
    # Test 1: Standard processing (baseline)
    print(f"\n🔄 Standard RAG Processing (baseline)...")
    start_time = time.time()
    
    try:
        standard_processor = RAGTrustProcessor(use_cache=False, use_database=False)
        result1 = standard_processor.process_document(test_file, "results")
        
        baseline_time = time.time() - start_time
        print(f"✅ Standard processing: {baseline_time:.2f}s")
        
        if result1.success:
            print(f"  - Facts extracted: {result1.document_stats.get('facts_extracted', 0)}")
            print(f"  - Citations created: {result1.document_stats.get('citations_created', 0)}")
        else:
            print(f"  - Error: {result1.error_message}")
            return
    
    except Exception as e:
        print(f"❌ Standard processing failed: {e}")
        return
    
    # Test 2: Optimized processing (first run)
    print(f"\n⚡ Optimized Processing (1st run - building cache)...")
    start_time = time.time()
    
    try:
        optimizer = RAGPerformanceOptimizer(use_cache=True, max_workers=4)
        result2 = optimizer.optimize_document_processing(test_file)
        
        opt_time_1 = time.time() - start_time
        print(f"✅ Optimized (1st): {opt_time_1:.2f}s")
        
        if result2.success:
            print(f"  - Memory usage: {result2.metrics.memory_usage.get('rss', 0):.1f}MB")
            print(f"  - Cache hits: {result2.metrics.cache_hits}")
            print(f"  - Cache misses: {result2.metrics.cache_misses}")
            print(f"  - Optimizations: {', '.join(result2.optimizations_applied)}")
            print(f"  - Improvement: {baseline_time/opt_time_1:.1f}x faster than baseline")
        else:
            print(f"  - Error: {result2.error_message}")
            return
    
    except Exception as e:
        print(f"❌ Optimized processing (1st) failed: {e}")
        return
    
    # Test 3: Optimized processing (second run - using cache)
    print(f"\n🚀 Optimized Processing (2nd run - using cache)...")
    start_time = time.time()
    
    try:
        result3 = optimizer.optimize_document_processing(test_file)
        
        opt_time_2 = time.time() - start_time
        print(f"✅ Optimized (2nd): {opt_time_2:.2f}s")
        
        if result3.success:
            print(f"  - Cache hits: {result3.metrics.cache_hits}")
            print(f"  - Cache misses: {result3.metrics.cache_misses}")
            print(f"  - Optimizations: {', '.join(result3.optimizations_applied)}")
            print(f"  - Improvement: {baseline_time/opt_time_2:.1f}x faster than baseline")
            print(f"  - Cache speedup: {opt_time_1/opt_time_2:.1f}x faster than 1st run")
        else:
            print(f"  - Error: {result3.error_message}")
    
    except Exception as e:
        print(f"❌ Optimized processing (2nd) failed: {e}")
        return
    
    # Performance Summary
    print(f"\n📈 PERFORMANCE SUMMARY:")
    print(f"  📊 Baseline (standard):     {baseline_time:.2f}s")
    print(f"  ⚡ Optimized (1st run):     {opt_time_1:.2f}s ({baseline_time/opt_time_1:.1f}x faster)")
    print(f"  🚀 Optimized (cached):      {opt_time_2:.2f}s ({baseline_time/opt_time_2:.1f}x faster)")
    print(f"  🎯 Cache effectiveness:     {opt_time_1/opt_time_2:.1f}x improvement")
    
    # Cache Statistics
    cache_stats = optimizer.get_performance_report()
    print(f"\n💾 CACHE STATISTICS:")
    print(f"  - Total operations: {cache_stats['summary']['operations_tracked']}")
    print(f"  - Cache hit rate: {cache_stats['summary']['cache_hit_rate']:.1%}")
    print(f"  - Average memory: {cache_stats['summary']['average_memory_mb']:.1f}MB")
    
    if cache_stats.get('recommendations'):
        print(f"  - Recommendations: {'; '.join(cache_stats['recommendations'])}")
    
    print(f"\n✅ Demo completed successfully!")


def demo_cache_manager():
    """Quick demo of cache manager capabilities"""
    print(f"\n" + "="*60)
    print("CACHE MANAGER DEMO")
    print("="*60)
    
    try:
        from cache_manager import CacheManager
        
        cache_manager = CacheManager()
        
        # Demo fact caching
        from semantic_extractor import Fact
        test_facts = [
            Fact("Sample fact 1", 1, 0, "test", 0.9, [], "context"),
            Fact("Sample fact 2", 2, 100, "test", 0.8, [], "context")
        ]
        
        print(f"💾 Caching sample facts...")
        success = cache_manager.cache_facts("demo_doc_123", test_facts)
        print(f"  - Facts cached: {'Yes' if success else 'No'}")
        
        # Retrieve facts
        retrieved = cache_manager.get_facts("demo_doc_123")
        print(f"  - Facts retrieved: {len(retrieved) if retrieved else 0}")
        
        # Demo summary caching
        test_summary = {
            'meta': {'processing_method': 'demo'},
            'summary': {'executive': 'Demo summary'},
            'citations': {'001': {'page': 1, 'text': 'Demo citation'}}
        }
        
        print(f"💾 Caching sample summary...")
        success = cache_manager.cache_summary("demo_doc_123", test_summary)
        print(f"  - Summary cached: {'Yes' if success else 'No'}")
        
        # Get cache stats
        stats = cache_manager.get_cache_stats()
        print(f"💽 Cache Statistics:")
        print(f"  - Memory entries: {stats['memory_cache']['entries_count']}")
        print(f"  - Memory usage: {stats['memory_cache']['storage_mb']:.2f}MB")
        print(f"  - Hit rate: {stats['total_hit_rate']:.1%}")
        
        print(f"✅ Cache manager demo completed!")
        
    except Exception as e:
        print(f"❌ Cache manager demo failed: {e}")


if __name__ == "__main__":
    # Set environment to reduce warnings
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    
    print("🚀 STARTING PERFORMANCE OPTIMIZATION DEMO")
    
    try:
        quick_performance_demo()
        demo_cache_manager()
    except KeyboardInterrupt:
        print("\n⚠️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
    
    print("\n🎉 Demo completed!")