"""
Comprehensive RAG Testing - Test with various document structures
"""

import json
import time
from pathlib import Path
from typing import Dict, List
from rag_processor import RAGTrustProcessor


def run_comprehensive_tests():
    """Run comprehensive tests on all available documents"""
    
    # Initialize processor
    processor = RAGTrustProcessor()
    
    # Find all PDFs in data folder
    data_dir = Path("data")
    pdf_files = list(data_dir.glob("*.pdf"))
    
    print(f"\n{'='*60}")
    print(f"COMPREHENSIVE RAG TESTING")
    print(f"{'='*60}")
    print(f"Found {len(pdf_files)} documents to test\n")
    
    # Test results storage
    test_results = []
    
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n[Test {i}/{len(pdf_files)}] {pdf_path.name}")
        print("-" * 40)
        
        try:
            # Process document
            result = processor.process_document(str(pdf_path))
            
            # Collect test metrics
            test_data = {
                'document': pdf_path.name,
                'success': result.success,
                'pages': result.document_stats.get('pages', 0),
                'characters': result.document_stats.get('characters', 0),
                'facts_extracted': len(result.summary.get('meta', {}).get('facts', [])),
                'citations_created': result.document_stats.get('citations_created', 0),
                'valid_citations': result.validation_report.get('valid_citations', 0),
                'total_citations': result.validation_report.get('total_citations', 0),
                'processing_method': result.summary.get('meta', {}).get('processing_method', 'unknown'),
                'chunks': result.summary.get('meta', {}).get('chunks', 0),
                'processing_time': result.processing_time,
                'error': result.error_message if not result.success else ""
            }
            
            test_results.append(test_data)
            
            # Print summary
            if result.success:
                print(f"✅ Success!")
                print(f"  - Method: {test_data['processing_method']}")
                print(f"  - Pages: {test_data['pages']}")
                print(f"  - Characters: {test_data['characters']:,}")
                print(f"  - Citations: {test_data['valid_citations']}/{test_data['total_citations']} valid")
                print(f"  - Time: {test_data['processing_time']:.2f}s")
            else:
                print(f"❌ Failed: {test_data['error']}")
                
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
            test_results.append({
                'document': pdf_path.name,
                'success': False,
                'error': str(e)
            })
    
    # Generate test report
    generate_test_report(test_results)
    
    return test_results


def generate_test_report(test_results: List[Dict]):
    """Generate comprehensive test report"""
    
    print(f"\n{'='*60}")
    print(f"TEST REPORT")
    print(f"{'='*60}")
    
    # Overall statistics
    total = len(test_results)
    successful = sum(1 for r in test_results if r.get('success', False))
    
    print(f"\n📊 Overall Results:")
    print(f"  - Total tests: {total}")
    print(f"  - Successful: {successful}")
    print(f"  - Failed: {total - successful}")
    print(f"  - Success rate: {(successful/total)*100:.1f}%")
    
    # Processing method breakdown
    print(f"\n📈 Processing Methods Used:")
    standard_count = sum(1 for r in test_results 
                        if r.get('processing_method') == 'rag' and r.get('chunks', 0) == 0)
    chunked_count = sum(1 for r in test_results 
                       if r.get('chunks', 0) > 0)
    print(f"  - Standard RAG: {standard_count}")
    print(f"  - Chunked RAG: {chunked_count}")
    
    # Document size analysis
    if successful > 0:
        successful_results = [r for r in test_results if r.get('success', False)]
        
        avg_pages = sum(r.get('pages', 0) for r in successful_results) / len(successful_results)
        avg_chars = sum(r.get('characters', 0) for r in successful_results) / len(successful_results)
        avg_time = sum(r.get('processing_time', 0) for r in successful_results) / len(successful_results)
        
        print(f"\n📏 Document Statistics (successful):")
        print(f"  - Average pages: {avg_pages:.1f}")
        print(f"  - Average characters: {avg_chars:,.0f}")
        print(f"  - Average processing time: {avg_time:.2f}s")
        
        # Find largest/smallest
        largest = max(successful_results, key=lambda x: x.get('characters', 0))
        smallest = min(successful_results, key=lambda x: x.get('characters', 0))
        
        print(f"\n  - Largest document: {largest['document']} ({largest['characters']:,} chars)")
        print(f"  - Smallest document: {smallest['document']} ({smallest['characters']:,} chars)")
    
    # Citation quality
    if successful > 0:
        total_citations = sum(r.get('total_citations', 0) for r in successful_results)
        valid_citations = sum(r.get('valid_citations', 0) for r in successful_results)
        
        print(f"\n✓ Citation Quality:")
        print(f"  - Total citations: {total_citations}")
        print(f"  - Valid citations: {valid_citations}")
        print(f"  - Validation rate: {(valid_citations/max(1, total_citations))*100:.1f}%")
    
    # Failed tests details
    failed_results = [r for r in test_results if not r.get('success', False)]
    if failed_results:
        print(f"\n❌ Failed Tests:")
        for r in failed_results:
            print(f"  - {r['document']}: {r.get('error', 'Unknown error')}")
    
    # Save report to file
    report_path = Path("results/rag_test_report.json")
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, 'w') as f:
        json.dump({
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
            'summary': {
                'total_tests': total,
                'successful': successful,
                'failed': total - successful,
                'success_rate': (successful/total)*100 if total > 0 else 0
            },
            'results': test_results
        }, f, indent=2)
    
    print(f"\n📁 Detailed report saved to: {report_path}")


def test_edge_cases():
    """Test specific edge cases"""
    
    print(f"\n{'='*60}")
    print(f"EDGE CASE TESTING")
    print(f"{'='*60}")
    
    processor = RAGTrustProcessor()
    
    # Test 1: Empty collection handling
    print("\n1. Testing with cleared vector store...")
    processor.vector_store.clear_collection()
    
    # Test 2: Small document
    smallest_doc = "data/2006 Eric Russell ILIT.pdf"
    if Path(smallest_doc).exists():
        print(f"\n2. Testing smallest document: {Path(smallest_doc).name}")
        result = processor.process_document(smallest_doc)
        print(f"   Result: {'✅ Success' if result.success else '❌ Failed'}")
    
    # Test 3: Document with poor OCR (if available)
    # This would test error handling for low-quality scans
    
    print("\n✓ Edge case testing complete")


if __name__ == "__main__":
    # Run comprehensive tests
    test_results = run_comprehensive_tests()
    
    # Run edge case tests
    test_edge_cases()
    
    print(f"\n{'='*60}")
    print(f"ALL TESTS COMPLETE")
    print(f"{'='*60}")