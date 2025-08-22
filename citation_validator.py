"""
Citation Validator - Validate and correct citations with fuzzy matching
"""

import re
import json
from typing import Dict, List, Tuple, Optional
from rapidfuzz import fuzz, process
from pathlib import Path


class CitationValidator:
    """Validate citations against source document"""
    
    def __init__(self, original_document: str = None, pages: List[Dict] = None):
        """
        Initialize validator
        
        Args:
            original_document: Full text of original document
            pages: List of page dictionaries with text
        """
        self.original_document = original_document
        self.pages = pages or []
        
        # Build page index for quick lookup
        self.page_index = {}
        if pages:
            for page in pages:
                page_num = page.get('page_number', 1)
                self.page_index[page_num] = page.get('text', '')
        
        # Citation pattern
        self.citation_pattern = re.compile(r'\{\{cite:(\w+)\}\}')
    
    def validate_summary(self, summary: Dict) -> Dict:
        """
        Validate all citations in a summary
        
        Args:
            summary: Summary dictionary with citations
        
        Returns:
            Validation report
        """
        report = {
            'total_citations': 0,
            'valid_citations': 0,
            'invalid_citations': 0,
            'orphaned_citations': [],
            'missing_citations': [],
            'corrected_citations': [],
            'validation_details': {}
        }
        
        # Extract all citation references from content
        all_references = self._extract_citation_references(summary)
        citations = summary.get('citations', {})
        
        report['total_citations'] = len(citations)
        
        # Check each citation
        for cite_id, cite_data in citations.items():
            validation = self._validate_citation(cite_id, cite_data)
            report['validation_details'][cite_id] = validation
            
            if validation['is_valid']:
                report['valid_citations'] += 1
            else:
                report['invalid_citations'] += 1
                
                # Try to correct the citation
                corrected = self._correct_citation(cite_data)
                if corrected:
                    report['corrected_citations'].append({
                        'id': cite_id,
                        'original': cite_data,
                        'corrected': corrected
                    })
        
        # Check for orphaned citations (defined but not referenced)
        for cite_id in citations:
            if cite_id not in all_references:
                report['orphaned_citations'].append(cite_id)
        
        # Check for missing citations (referenced but not defined)
        for ref_id in all_references:
            if ref_id not in citations:
                report['missing_citations'].append(ref_id)
        
        return report
    
    def _extract_citation_references(self, summary: Dict) -> set:
        """Extract all citation references from summary content"""
        references = set()
        
        # Check executive summary
        executive = summary.get('summary', {}).get('executive', '')
        references.update(self.citation_pattern.findall(executive))
        
        # Check all sections
        sections = summary.get('summary', {}).get('sections', [])
        for section in sections:
            content = section.get('content', '')
            references.update(self.citation_pattern.findall(content))
        
        return references
    
    def _validate_citation(self, cite_id: str, cite_data: Dict) -> Dict:
        """Validate a single citation"""
        validation = {
            'id': cite_id,
            'is_valid': False,
            'exact_match': False,
            'fuzzy_score': 0,
            'page_verified': False,
            'issues': []
        }
        
        cite_text = cite_data.get('text', '')
        cite_page = cite_data.get('page', 0)
        
        if not cite_text:
            validation['issues'].append('Empty citation text')
            return validation
        
        # Check if page exists
        if cite_page in self.page_index:
            validation['page_verified'] = True
            page_text = self.page_index[cite_page]
            
            # Check for exact match
            if cite_text in page_text:
                validation['exact_match'] = True
                validation['is_valid'] = True
                validation['fuzzy_score'] = 100
            else:
                # Try fuzzy matching
                score = self._fuzzy_match_in_text(cite_text, page_text)
                validation['fuzzy_score'] = score
                
                if score > 80:  # 80% similarity threshold
                    validation['is_valid'] = True
                else:
                    validation['issues'].append(f'Text not found on page {cite_page}')
        else:
            validation['issues'].append(f'Page {cite_page} not found')
            
            # Try to find the text on any page
            found_page = self._find_text_in_document(cite_text)
            if found_page:
                validation['issues'].append(f'Text actually on page {found_page}')
                validation['suggested_page'] = found_page
        
        return validation
    
    def _fuzzy_match_in_text(self, needle: str, haystack: str, 
                            threshold: int = 80) -> float:
        """Find fuzzy match of text within larger text"""
        if not needle or not haystack:
            return 0
        
        # Clean texts
        needle_clean = ' '.join(needle.split()).lower()
        haystack_clean = ' '.join(haystack.split()).lower()
        
        # If needle is short, look for exact substring
        if len(needle_clean) < 20:
            if needle_clean in haystack_clean:
                return 100
        
        # Try sliding window for longer texts
        needle_len = len(needle_clean)
        best_score = 0
        
        # Slide through haystack with window size of needle
        for i in range(0, len(haystack_clean) - needle_len + 1, 10):
            window = haystack_clean[i:i + needle_len + 20]
            score = fuzz.partial_ratio(needle_clean, window)
            best_score = max(best_score, score)
            
            if best_score > 95:  # Early exit for very good matches
                break
        
        return best_score
    
    def _find_text_in_document(self, text: str) -> Optional[int]:
        """Find which page contains the text"""
        best_score = 0
        best_page = None
        
        for page_num, page_text in self.page_index.items():
            score = self._fuzzy_match_in_text(text, page_text)
            if score > best_score:
                best_score = score
                best_page = page_num
                
                if score > 95:  # Very good match, stop searching
                    break
        
        return best_page if best_score > 80 else None
    
    def _correct_citation(self, cite_data: Dict) -> Optional[Dict]:
        """Try to correct an invalid citation"""
        cite_text = cite_data.get('text', '')
        cite_page = cite_data.get('page', 0)
        
        if not cite_text:
            return None
        
        # Try to find the correct page
        correct_page = self._find_text_in_document(cite_text)
        if correct_page and correct_page != cite_page:
            corrected = cite_data.copy()
            corrected['page'] = correct_page
            corrected['corrected'] = True
            return corrected
        
        # Try to find similar text on the stated page
        if cite_page in self.page_index:
            page_text = self.page_index[cite_page]
            
            # Extract sentences from page
            sentences = re.split(r'[.!?]\s+', page_text)
            
            # Find best matching sentence
            best_match = process.extractOne(
                cite_text, 
                sentences,
                scorer=fuzz.partial_ratio
            )
            
            if best_match and best_match[1] > 70:
                corrected = cite_data.copy()
                corrected['text'] = best_match[0]
                corrected['corrected'] = True
                corrected['similarity'] = best_match[1]
                return corrected
        
        return None
    
    def auto_correct_summary(self, summary: Dict) -> Dict:
        """Automatically correct citations in summary"""
        corrected_summary = json.loads(json.dumps(summary))  # Deep copy
        report = self.validate_summary(summary)
        
        # Apply corrections
        for correction in report['corrected_citations']:
            cite_id = correction['id']
            corrected_data = correction['corrected']
            corrected_summary['citations'][cite_id] = corrected_data
        
        # Remove orphaned citations
        for orphan_id in report['orphaned_citations']:
            if orphan_id in corrected_summary['citations']:
                del corrected_summary['citations'][orphan_id]
        
        # Add metadata about corrections
        corrected_summary['meta'] = corrected_summary.get('meta', {})
        corrected_summary['meta']['citation_validation'] = {
            'valid': report['valid_citations'],
            'corrected': len(report['corrected_citations']),
            'removed': len(report['orphaned_citations'])
        }
        
        return corrected_summary


def validate_citations(summary_path: str, pdf_path: str) -> Dict:
    """
    Validate citations in a summary file
    
    Args:
        summary_path: Path to summary JSON
        pdf_path: Path to original PDF
    
    Returns:
        Validation report
    """
    # Load summary
    with open(summary_path, 'r') as f:
        summary = json.load(f)
    
    # Extract text from PDF
    from pdf_processor import PDFProcessor
    processor = PDFProcessor()
    full_text, pages = processor.extract_text_from_pdf(pdf_path)
    
    # Validate
    validator = CitationValidator(full_text, pages)
    report = validator.validate_summary(summary)
    
    return report


if __name__ == "__main__":
    import sys
    
    # Test 1: Validate RAG-generated summary
    print("="*60)
    print("Test 1: Validate RAG Summary (2006 Eric Russell ILIT)")
    print("="*60)
    
    test1_summary = "results/test_rag_2006_eric.json"
    test1_pdf = "data/2006 Eric Russell ILIT.pdf"
    
    if Path(test1_summary).exists():
        report1 = validate_citations(test1_summary, test1_pdf)
        
        print(f"\nValidation Results:")
        print(f"  Total citations: {report1['total_citations']}")
        print(f"  Valid citations: {report1['valid_citations']}")
        print(f"  Invalid citations: {report1['invalid_citations']}")
        print(f"  Orphaned citations: {len(report1['orphaned_citations'])}")
        print(f"  Missing citations: {len(report1['missing_citations'])}")
        
        if report1['corrected_citations']:
            print(f"\nCorrected {len(report1['corrected_citations'])} citations:")
            for corr in report1['corrected_citations'][:3]:
                print(f"  - Citation {corr['id']}: Page {corr['original']['page']} → {corr['corrected']['page']}")
    else:
        print(f"Summary file not found: {test1_summary}")
    
    # Test 2: Validate and auto-correct
    print("\n" + "="*60)
    print("Test 2: Auto-correct Citations (1998 Eric Russell)")
    print("="*60)
    
    test2_summary = "results/test_rag_1998_eric.json"
    test2_pdf = "data/1998 Eric Russell Family Trust Agreement.pdf"
    
    if Path(test2_summary).exists():
        # Load and validate
        with open(test2_summary, 'r') as f:
            summary2 = json.load(f)
        
        from pdf_processor import PDFProcessor
        processor = PDFProcessor()
        _, pages2 = processor.extract_text_from_pdf(test2_pdf)
        
        validator2 = CitationValidator(pages=pages2)
        corrected2 = validator2.auto_correct_summary(summary2)
        
        # Save corrected version
        corrected_path = "results/test_rag_1998_eric_corrected.json"
        with open(corrected_path, 'w') as f:
            json.dump(corrected2, f, indent=2)
        
        print(f"\n✓ Corrected summary saved to: {corrected_path}")
        print(f"Validation metadata: {corrected2['meta'].get('citation_validation', {})}")
    else:
        print(f"Summary file not found: {test2_summary}")