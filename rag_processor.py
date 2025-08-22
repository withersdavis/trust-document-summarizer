"""
RAG Trust Processor - Unified processor combining all RAG components
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

from pdf_processor import PDFProcessor
from semantic_extractor import SemanticFactExtractor, Fact
from vector_store import DocumentVectorStore
from smart_chunker import SmartChunker, DocumentChunk
from concept_categorizer import ConceptCategorizer
from rag_generator import RAGSummaryGenerator
from citation_validator import CitationValidator
from document_database import DocumentDatabase
from ocr_cache_manager import OCRCacheManager


@dataclass
class ProcessingResult:
    """Result of RAG processing"""
    success: bool
    summary: Dict
    validation_report: Dict
    processing_time: float
    document_stats: Dict
    error_message: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)


class RAGTrustProcessor:
    """Unified RAG processor for trust documents"""
    
    def __init__(self, use_cache: bool = True, use_database: bool = True):
        """
        Initialize RAG processor
        
        Args:
            use_cache: Whether to use OCR caching
            use_database: Whether to track in database
        """
        self.use_cache = use_cache
        self.use_database = use_database
        
        # Initialize components
        self.pdf_processor = PDFProcessor(use_cache=use_cache)
        self.fact_extractor = SemanticFactExtractor()
        self.vector_store = DocumentVectorStore()
        self.chunker = SmartChunker()
        self.categorizer = ConceptCategorizer()
        self.generator = RAGSummaryGenerator(self.vector_store)
        
        # Optional components
        self.database = DocumentDatabase() if use_database else None
        self.cache_manager = OCRCacheManager() if use_cache else None
        
        # Processing options
        self.options = {
            'max_chunk_size': 15000,
            'min_facts_required': 10,
            'citation_threshold': 0.8,
            'use_chunking_threshold': 50000  # Use chunking for docs > 50K chars
        }
    
    def process_document(self, pdf_path: str, output_dir: str = "results") -> ProcessingResult:
        """
        Process a trust document using full RAG pipeline
        
        Args:
            pdf_path: Path to PDF document
            output_dir: Directory for output files
        
        Returns:
            ProcessingResult with summary and validation
        """
        start_time = time.time()
        
        try:
            # Step 1: Extract text from PDF
            print(f"\n{'='*60}")
            print(f"RAG TRUST PROCESSOR")
            print(f"{'='*60}")
            print(f"📄 Document: {Path(pdf_path).name}")
            
            full_text, pages = self.pdf_processor.extract_text_from_pdf(pdf_path)
            total_chars = len(full_text)
            total_pages = len(pages)
            
            print(f"📊 Statistics:")
            print(f"  - Pages: {total_pages}")
            print(f"  - Characters: {total_chars:,}")
            
            # Add to database if enabled
            doc_id = None
            if self.database:
                doc_id = self.database.add_document(pdf_path)
                print(f"  - Database ID: {doc_id}")
            
            # Step 2: Determine processing strategy
            if total_chars > self.options['use_chunking_threshold']:
                print(f"\n🔄 Using CHUNKED processing (document > {self.options['use_chunking_threshold']:,} chars)")
                summary = self._process_with_chunking(pages, pdf_path)
            else:
                print(f"\n🔄 Using STANDARD processing")
                summary = self._process_standard(pages, pdf_path)
            
            # Step 3: Validate citations
            print(f"\n✓ Validating citations...")
            validator = CitationValidator(full_text, pages)
            validation_report = validator.validate_summary(summary)
            
            # Step 4: Auto-correct if needed
            if validation_report['invalid_citations'] > 0:
                print(f"  - Correcting {validation_report['invalid_citations']} invalid citations")
                summary = validator.auto_correct_summary(summary)
                # Re-validate
                validation_report = validator.validate_summary(summary)
            
            print(f"  - Valid: {validation_report['valid_citations']}/{validation_report['total_citations']}")
            
            # Step 5: Save results
            output_path = self._save_results(summary, pdf_path, output_dir)
            print(f"\n📁 Results saved to: {output_path}")
            
            # Step 6: Update database
            if self.database and doc_id:
                metadata = {
                    'citations_count': len(summary.get('citations', {})),
                    'sections_count': len(summary.get('summary', {}).get('sections', [])),
                    'processing_method': summary.get('meta', {}).get('processing_method', 'rag'),
                    'status': 'completed',
                    'validation_score': validation_report['valid_citations'] / max(1, validation_report['total_citations'])
                }
                self.database.add_processing_result(
                    doc_id, 'rag_summary', str(output_path), metadata
                )
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Create result
            return ProcessingResult(
                success=True,
                summary=summary,
                validation_report=validation_report,
                processing_time=processing_time,
                document_stats={
                    'pages': total_pages,
                    'characters': total_chars,
                    'facts_extracted': len(summary.get('meta', {}).get('facts', [])),
                    'citations_created': len(summary.get('citations', {}))
                }
            )
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            return ProcessingResult(
                success=False,
                summary={},
                validation_report={},
                processing_time=time.time() - start_time,
                document_stats={},
                error_message=str(e)
            )
    
    def _process_standard(self, pages: List[Dict], pdf_path: str) -> Dict:
        """Process document using standard RAG approach"""
        # Extract facts
        print("  - Extracting semantic facts...")
        facts = self.fact_extractor.extract_from_pages(pages)
        facts = self.fact_extractor.deduplicate_facts(facts)
        facts = self.fact_extractor.rank_facts_by_importance(facts)
        print(f"    Found {len(facts)} unique facts")
        
        # Categorize facts
        print("  - Categorizing facts...")
        categorized = self.categorizer.categorize_facts(facts)
        category_summary = self.categorizer.get_category_summary(facts)
        print(f"    Organized into {len(categorized)} categories")
        
        # Generate summary
        print("  - Generating RAG summary...")
        summary = self.generator.generate_summary(pdf_path, facts)
        
        # Add category metadata
        summary['meta']['categories'] = {
            cat: {'count': stats['count'], 'importance': stats['importance']}
            for cat, stats in category_summary.items()
        }
        
        return summary
    
    def _process_with_chunking(self, pages: List[Dict], pdf_path: str) -> Dict:
        """Process large document using chunking"""
        # Create chunks
        print("  - Creating semantic chunks...")
        chunks = self.chunker.chunk_document(pages)
        print(f"    Created {len(chunks)} chunks")
        
        # Process each chunk
        all_facts = []
        chunk_summaries = []
        
        for i, chunk in enumerate(chunks, 1):
            if i % 10 == 0 or i == len(chunks):
                print(f"    Processing chunk {i}/{len(chunks)}...")
            
            # Extract facts from chunk
            chunk_facts = self.fact_extractor.extract_facts(
                chunk.text,
                chunk.start_page,
                chunk.start_char
            )
            all_facts.extend(chunk_facts)
            
            # Store chunk summary for context
            if chunk.section_headers:
                chunk_summaries.append({
                    'chunk_id': chunk.chunk_id,
                    'pages': f"{chunk.start_page}-{chunk.end_page}",
                    'headers': chunk.section_headers[:3],
                    'facts': len(chunk_facts)
                })
        
        # Deduplicate and rank facts
        print("  - Deduplicating and ranking facts...")
        all_facts = self.fact_extractor.deduplicate_facts(all_facts)
        all_facts = self.fact_extractor.rank_facts_by_importance(all_facts)
        print(f"    Total unique facts: {len(all_facts)}")
        
        # Categorize all facts
        print("  - Categorizing facts...")
        categorized = self.categorizer.categorize_facts(all_facts)
        
        # Generate summary from chunks
        print("  - Generating RAG summary from chunks...")
        summary = self.generator.generate_from_chunks(chunks, pdf_path)
        
        # Add chunk metadata
        summary['meta']['chunks'] = len(chunks)
        summary['meta']['chunk_summaries'] = chunk_summaries[:10]  # Include first 10
        
        return summary
    
    def _save_results(self, summary: Dict, pdf_path: str, output_dir: str) -> Path:
        """Save processing results"""
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        # Generate filename
        doc_name = Path(pdf_path).stem
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"{doc_name}_rag_{timestamp}.json"
        
        # Save JSON
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        return output_file
    
    def process_batch(self, pdf_paths: List[str], output_dir: str = "results") -> List[ProcessingResult]:
        """
        Process multiple documents
        
        Args:
            pdf_paths: List of PDF paths
            output_dir: Output directory
        
        Returns:
            List of processing results
        """
        results = []
        
        print(f"\n📚 Processing {len(pdf_paths)} documents...")
        
        for i, pdf_path in enumerate(pdf_paths, 1):
            print(f"\n[{i}/{len(pdf_paths)}] Processing: {Path(pdf_path).name}")
            result = self.process_document(pdf_path, output_dir)
            results.append(result)
            
            if result.success:
                print(f"✅ Success ({result.processing_time:.1f}s)")
            else:
                print(f"❌ Failed: {result.error_message}")
        
        # Summary statistics
        successful = sum(1 for r in results if r.success)
        total_time = sum(r.processing_time for r in results)
        
        print(f"\n{'='*60}")
        print(f"BATCH PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"✓ Successful: {successful}/{len(pdf_paths)}")
        print(f"✓ Total time: {total_time:.1f}s")
        print(f"✓ Average time: {total_time/len(pdf_paths):.1f}s per document")
        
        return results


def process_trust_rag(pdf_path: str, output_dir: str = "results") -> ProcessingResult:
    """
    Convenience function to process a trust document with RAG
    
    Args:
        pdf_path: Path to PDF
        output_dir: Output directory
    
    Returns:
        ProcessingResult
    """
    processor = RAGTrustProcessor()
    return processor.process_document(pdf_path, output_dir)


if __name__ == "__main__":
    import sys
    
    # Test 1: Process single document (small)
    print("\n" + "="*60)
    print("Test 1: Single Document Processing (2006 Eric Russell ILIT)")
    print("="*60)
    
    test1_path = "data/2006 Eric Russell ILIT.pdf"
    result1 = process_trust_rag(test1_path)
    
    if result1.success:
        print(f"\n✅ Test 1 Passed!")
        print(f"  - Processing time: {result1.processing_time:.2f}s")
        print(f"  - Citations: {result1.document_stats['citations_created']}")
        print(f"  - Validation: {result1.validation_report['valid_citations']}/{result1.validation_report['total_citations']} valid")
    else:
        print(f"\n❌ Test 1 Failed: {result1.error_message}")
    
    # Test 2: Process large document with chunking
    print("\n" + "="*60)
    print("Test 2: Large Document with Chunking (Jerry Simons Trust)")
    print("="*60)
    
    test2_path = "data/Jerry Simons Trust.pdf"
    if Path(test2_path).exists():
        result2 = process_trust_rag(test2_path)
        
        if result2.success:
            print(f"\n✅ Test 2 Passed!")
            print(f"  - Processing time: {result2.processing_time:.2f}s")
            print(f"  - Method: {result2.summary['meta'].get('processing_method', 'unknown')}")
            print(f"  - Chunks: {result2.summary['meta'].get('chunks', 0)}")
            print(f"  - Citations: {result2.document_stats['citations_created']}")
        else:
            print(f"\n❌ Test 2 Failed: {result2.error_message}")
    else:
        print(f"⚠️ Test file not found: {test2_path}")