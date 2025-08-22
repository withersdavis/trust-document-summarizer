#!/usr/bin/env python3
"""
Performance Optimization Test Suite - Test and benchmark the performance improvements
"""

import os
import time
import json
from pathlib import Path
from typing import List, Dict, Tuple
import statistics

from performance_optimizer import RAGPerformanceOptimizer, optimize_document_processing
from cache_manager import CacheManager
from rag_processor import RAGTrustProcessor


def measure_processing_time(func, *args, **kwargs) -> Tuple[float, any]:
    """Measure execution time of a function"""
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    return end_time - start_time, result


def test_single_document_optimization():
    """Test optimization on a single document"""
    print("\n" + "="*80)
    print("SINGLE DOCUMENT OPTIMIZATION TEST")
    print("="*80)
    
    test_file = "data/2006 Eric Russell ILIT.pdf"
    if not Path(test_file).exists():
        print(f"❌ Test file not found: {test_file}")
        return None
    
    results = {}
    
    # Test 1: Standard RAG processor (baseline)
    print(f"\n📊 Testing baseline RAG processor...")
    standard_processor = RAGTrustProcessor(use_cache=False, use_database=False)
    
    baseline_time, baseline_result = measure_processing_time(
        standard_processor.process_document,
        test_file,
        "results"
    )
    
    results['baseline'] = {
        'processing_time': baseline_time,
        'success': baseline_result.success,
        'citations_count': len(baseline_result.summary.get('citations', {})) if baseline_result.success else 0,
        'facts_extracted': baseline_result.document_stats.get('facts_extracted', 0) if baseline_result.success else 0
    }
    
    print(f"  ✅ Baseline: {baseline_time:.2f}s")
    print(f"  - Success: {baseline_result.success}")
    if baseline_result.success:
        print(f"  - Facts: {results['baseline']['facts_extracted']}")
        print(f"  - Citations: {results['baseline']['citations_count']}")
    
    # Test 2: Optimized processor (first run - cache miss)
    print(f"\n⚡ Testing optimized processor (first run)...")
    optimizer = RAGPerformanceOptimizer(use_cache=True, max_workers=4)
    
    opt_time_1, opt_result_1 = measure_processing_time(
        optimizer.optimize_document_processing,
        test_file
    )
    
    results['optimized_first'] = {
        'processing_time': opt_time_1,
        'success': opt_result_1.success,
        'cache_hits': opt_result_1.metrics.cache_hits if opt_result_1.success else 0,
        'cache_misses': opt_result_1.metrics.cache_misses if opt_result_1.success else 0,
        'optimizations_applied': opt_result_1.optimizations_applied if opt_result_1.success else [],
        'memory_mb': opt_result_1.metrics.memory_usage.get('rss', 0) if opt_result_1.success else 0
    }
    
    print(f"  ✅ Optimized (1st): {opt_time_1:.2f}s")
    if opt_result_1.success:
        print(f"  - Cache hits: {results['optimized_first']['cache_hits']}")
        print(f"  - Cache misses: {results['optimized_first']['cache_misses']}")
        print(f"  - Memory: {results['optimized_first']['memory_mb']:.1f}MB")
        print(f"  - Optimizations: {', '.join(results['optimized_first']['optimizations_applied'])}")
    
    # Test 3: Optimized processor (second run - cache hit)
    print(f"\n🚀 Testing optimized processor (second run - cached)...")
    
    opt_time_2, opt_result_2 = measure_processing_time(
        optimizer.optimize_document_processing,
        test_file
    )
    
    results['optimized_second'] = {
        'processing_time': opt_time_2,
        'success': opt_result_2.success,
        'cache_hits': opt_result_2.metrics.cache_hits if opt_result_2.success else 0,
        'cache_misses': opt_result_2.metrics.cache_misses if opt_result_2.success else 0,
        'optimizations_applied': opt_result_2.optimizations_applied if opt_result_2.success else [],
        'speedup': baseline_time / max(0.001, opt_time_2)
    }
    
    print(f"  ✅ Optimized (2nd): {opt_time_2:.2f}s")
    if opt_result_2.success:
        print(f"  - Cache hits: {results['optimized_second']['cache_hits']}")
        print(f"  - Cache misses: {results['optimized_second']['cache_misses']}")
        print(f"  - Speedup: {results['optimized_second']['speedup']:.1f}x faster")
        print(f"  - Optimizations: {', '.join(results['optimized_second']['optimizations_applied'])}")
    
    # Performance summary
    print(f"\n📈 PERFORMANCE SUMMARY:")
    print(f"  - Baseline time: {baseline_time:.2f}s")
    print(f"  - Optimized (1st): {opt_time_1:.2f}s ({baseline_time/max(0.001, opt_time_1):.1f}x)")
    print(f"  - Optimized (2nd): {opt_time_2:.2f}s ({baseline_time/max(0.001, opt_time_2):.1f}x)")
    print(f"  - Cache effectiveness: {opt_time_1/max(0.001, opt_time_2):.1f}x improvement")
    
    return results


def test_batch_processing_optimization():
    """Test optimization on multiple documents"""
    print("\n" + "="*80)
    print("BATCH PROCESSING OPTIMIZATION TEST")
    print("="*80)
    
    # Select test files
    test_files = [
        "data/2006 Eric Russell ILIT.pdf",
        "data/1998 Eric Russell Family Trust Agreement.pdf",
    ]
    
    # Filter existing files
    existing_files = [f for f in test_files if Path(f).exists()]
    if not existing_files:
        print("❌ No test files found")
        return None
    
    print(f"📁 Testing with {len(existing_files)} documents:")
    for f in existing_files:
        print(f"  - {Path(f).name}")
    
    # Test 1: Sequential standard processing
    print(f"\n📊 Testing sequential standard processing...")
    standard_times = []
    
    for pdf_path in existing_files:
        processor = RAGTrustProcessor(use_cache=False, use_database=False)
        exec_time, result = measure_processing_time(
            processor.process_document,
            pdf_path,
            "results"
        )
        standard_times.append(exec_time)
        print(f"  - {Path(pdf_path).name}: {exec_time:.2f}s")
    
    standard_total = sum(standard_times)
    print(f"  ✅ Total sequential time: {standard_total:.2f}s")
    
    # Test 2: Optimized batch processing
    print(f"\n⚡ Testing optimized batch processing...")
    optimizer = RAGPerformanceOptimizer(use_cache=True, max_workers=2)
    
    batch_time, batch_results = measure_processing_time(
        optimizer.optimize_batch_processing,
        existing_files
    )
    
    successful_results = [r for r in batch_results if r.success]
    
    print(f"  ✅ Batch processing time: {batch_time:.2f}s")
    print(f"  - Successful: {len(successful_results)}/{len(existing_files)}")
    print(f"  - Speedup: {standard_total/max(0.001, batch_time):.1f}x faster")
    
    # Individual document times in batch
    for i, result in enumerate(batch_results):
        if result.success:
            doc_name = Path(existing_files[i]).name
            print(f"  - {doc_name}: {result.metrics.duration:.2f}s")
    
    return {
        'sequential_total': standard_total,
        'batch_total': batch_time,
        'speedup': standard_total / max(0.001, batch_time),
        'files_processed': len(successful_results),
        'individual_times': [r.metrics.duration for r in successful_results]
    }


def test_caching_effectiveness():
    """Test caching system effectiveness"""
    print("\n" + "="*80)
    print("CACHING EFFECTIVENESS TEST")
    print("="*80)
    
    cache_manager = CacheManager()
    
    # Clear caches for clean test
    cache_manager.clear_all_caches()
    print("🗑️  Cleared all caches for clean test")
    
    test_file = "data/2006 Eric Russell ILIT.pdf"
    if not Path(test_file).exists():
        print(f"❌ Test file not found: {test_file}")
        return None
    
    optimizer = RAGPerformanceOptimizer(use_cache=True)
    
    # Multiple runs to test caching
    run_times = []
    cache_stats = []
    
    print(f"\n🔄 Running multiple iterations to test caching:")
    for i in range(5):
        print(f"  Run {i+1}/5...", end=" ")
        
        exec_time, result = measure_processing_time(
            optimizer.optimize_document_processing,
            test_file
        )
        
        run_times.append(exec_time)
        
        if result.success:
            cache_stats.append({
                'hits': result.metrics.cache_hits,
                'misses': result.metrics.cache_misses,
                'optimizations': result.optimizations_applied
            })
            
            hit_rate = result.metrics.cache_hits / max(1, result.metrics.cache_hits + result.metrics.cache_misses)
            print(f"{exec_time:.2f}s (cache hit rate: {hit_rate:.1%})")
        else:
            print(f"Failed: {result.error_message}")
    
    # Analyze results
    if run_times:
        print(f"\n📊 Caching Analysis:")
        print(f"  - First run: {run_times[0]:.2f}s")
        print(f"  - Average subsequent: {statistics.mean(run_times[1:]):.2f}s")
        print(f"  - Best time: {min(run_times):.2f}s")
        print(f"  - Cache improvement: {run_times[0]/min(run_times[1:]) if len(run_times) > 1 else 1:.1f}x")
        
        # Cache statistics
        cache_report = cache_manager.get_cache_stats()
        print(f"  - Total hit rate: {cache_report['total_hit_rate']:.1%}")
        print(f"  - Memory cache entries: {cache_report['memory_cache']['entries_count']}")
        print(f"  - Memory usage: {cache_report['memory_cache']['storage_mb']:.1f}MB")
        
        return {
            'run_times': run_times,
            'cache_improvement': run_times[0]/min(run_times[1:]) if len(run_times) > 1 else 1,
            'cache_stats': cache_report
        }
    
    return None


def test_parallel_processing():
    """Test parallel processing effectiveness"""
    print("\n" + "="*80)
    print("PARALLEL PROCESSING TEST")
    print("="*80)
    
    test_file = "data/Jerry Simons Trust.pdf"  # Large document
    if not Path(test_file).exists():
        print(f"❌ Large test file not found: {test_file}")
        test_file = "data/2006 Eric Russell ILIT.pdf"  # Fallback
        
    if not Path(test_file).exists():
        print(f"❌ No test files found")
        return None
    
    print(f"📄 Testing with: {Path(test_file).name}")
    
    # Test different worker configurations
    worker_configs = [1, 2, 4]
    results = {}
    
    for workers in worker_configs:
        print(f"\n⚙️  Testing with {workers} worker(s)...")
        
        optimizer = RAGPerformanceOptimizer(use_cache=False, max_workers=workers)  # Disable cache for pure parallel test
        
        exec_time, result = measure_processing_time(
            optimizer.optimize_document_processing,
            test_file
        )
        
        results[workers] = {
            'time': exec_time,
            'success': result.success,
            'workers_used': result.metrics.parallel_workers if result.success else 1,
            'items_processed': result.metrics.items_processed if result.success else 0
        }
        
        print(f"  - Time: {exec_time:.2f}s")
        if result.success:
            print(f"  - Workers used: {results[workers]['workers_used']}")
            print(f"  - Items processed: {results[workers]['items_processed']}")
    
    # Calculate speedups
    baseline_time = results.get(1, {}).get('time', 0)
    if baseline_time > 0:
        print(f"\n📈 Parallel Processing Analysis:")
        print(f"  - 1 worker (baseline): {baseline_time:.2f}s")
        
        for workers in worker_configs[1:]:
            if workers in results:
                speedup = baseline_time / max(0.001, results[workers]['time'])
                efficiency = speedup / workers * 100
                print(f"  - {workers} workers: {results[workers]['time']:.2f}s ({speedup:.1f}x speedup, {efficiency:.0f}% efficiency)")
    
    return results


def generate_performance_report(test_results: Dict):
    """Generate comprehensive performance report"""
    print("\n" + "="*80)
    print("COMPREHENSIVE PERFORMANCE REPORT")
    print("="*80)
    
    report = {
        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
        'test_results': test_results,
        'summary': {}
    }
    
    # Single document performance
    if 'single_document' in test_results:
        single_results = test_results['single_document']
        if single_results:
            baseline = single_results.get('baseline', {}).get('processing_time', 0)
            optimized = single_results.get('optimized_second', {}).get('processing_time', baseline)
            
            report['summary']['single_document'] = {
                'baseline_time': baseline,
                'optimized_time': optimized,
                'improvement': baseline / max(0.001, optimized),
                'cache_effectiveness': True if 'summary_cache_hit' in single_results.get('optimized_second', {}).get('optimizations_applied', []) else False
            }
    
    # Batch processing performance
    if 'batch_processing' in test_results:
        batch_results = test_results['batch_processing']
        if batch_results:
            report['summary']['batch_processing'] = {
                'sequential_time': batch_results.get('sequential_total', 0),
                'parallel_time': batch_results.get('batch_total', 0),
                'speedup': batch_results.get('speedup', 1),
                'files_processed': batch_results.get('files_processed', 0)
            }
    
    # Caching effectiveness
    if 'caching' in test_results:
        caching_results = test_results['caching']
        if caching_results:
            report['summary']['caching'] = {
                'cache_improvement': caching_results.get('cache_improvement', 1),
                'hit_rate': caching_results.get('cache_stats', {}).get('total_hit_rate', 0),
                'memory_usage_mb': caching_results.get('cache_stats', {}).get('memory_cache', {}).get('storage_mb', 0)
            }
    
    # Print summary
    print("\n🎯 KEY PERFORMANCE IMPROVEMENTS:")
    
    if 'single_document' in report['summary']:
        single = report['summary']['single_document']
        print(f"  • Single document processing: {single['improvement']:.1f}x faster")
        print(f"    - Baseline: {single['baseline_time']:.2f}s → Optimized: {single['optimized_time']:.2f}s")
        print(f"    - Cache effectiveness: {'Yes' if single['cache_effectiveness'] else 'No'}")
    
    if 'batch_processing' in report['summary']:
        batch = report['summary']['batch_processing']
        print(f"  • Batch processing: {batch['speedup']:.1f}x faster")
        print(f"    - Sequential: {batch['sequential_time']:.2f}s → Parallel: {batch['parallel_time']:.2f}s")
        print(f"    - Files processed: {batch['files_processed']}")
    
    if 'caching' in report['summary']:
        cache = report['summary']['caching']
        print(f"  • Caching system: {cache['cache_improvement']:.1f}x improvement")
        print(f"    - Hit rate: {cache['hit_rate']:.1%}")
        print(f"    - Memory usage: {cache['memory_usage_mb']:.1f}MB")
    
    # Save report
    report_path = Path("results/performance_optimization_report.json")
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📊 Full report saved to: {report_path}")
    return report


def main():
    """Run comprehensive performance optimization tests"""
    print("🚀 STARTING PERFORMANCE OPTIMIZATION TEST SUITE")
    print("="*80)
    
    test_results = {}
    
    # Test 1: Single document optimization
    try:
        single_results = test_single_document_optimization()
        test_results['single_document'] = single_results
    except Exception as e:
        print(f"❌ Single document test failed: {e}")
    
    # Test 2: Batch processing optimization
    try:
        batch_results = test_batch_processing_optimization()
        test_results['batch_processing'] = batch_results
    except Exception as e:
        print(f"❌ Batch processing test failed: {e}")
    
    # Test 3: Caching effectiveness
    try:
        caching_results = test_caching_effectiveness()
        test_results['caching'] = caching_results
    except Exception as e:
        print(f"❌ Caching test failed: {e}")
    
    # Test 4: Parallel processing
    try:
        parallel_results = test_parallel_processing()
        test_results['parallel_processing'] = parallel_results
    except Exception as e:
        print(f"❌ Parallel processing test failed: {e}")
    
    # Generate comprehensive report
    report = generate_performance_report(test_results)
    
    print("\n✅ PERFORMANCE OPTIMIZATION TEST SUITE COMPLETED")
    print("="*80)


if __name__ == "__main__":
    main()