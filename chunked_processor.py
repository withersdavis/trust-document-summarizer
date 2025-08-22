"""
Chunked Document Processor - Handles large OCR documents by processing in chunks
"""

import json
from typing import Dict, List, Tuple
from pathlib import Path
import re
from pdf_processor import PDFProcessor
from llm_client import LLMClient

class ChunkedDocumentProcessor:
    def __init__(self, chunk_size: int = 20000, overlap: int = 500):
        """
        Initialize chunked processor
        
        Args:
            chunk_size: Maximum characters per chunk
            overlap: Number of characters to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.llm_client = LLMClient()
        
    def process_large_document(self, pdf_path: str) -> Dict:
        """
        Process a large document by chunking it intelligently
        """
        print("="*60)
        print("CHUNKED DOCUMENT PROCESSOR")
        print("="*60)
        
        # Extract text from PDF
        pdf_processor = PDFProcessor()
        full_text, pages = pdf_processor.extract_text_from_pdf(pdf_path)
        
        total_chars = len(full_text)
        print(f"📄 Document: {Path(pdf_path).name}")
        print(f"📊 Total characters: {total_chars:,}")
        print(f"📄 Total pages: {len(pages)}")
        
        # Check if chunking is needed
        if total_chars <= self.chunk_size:
            print("✅ Document fits in single chunk - using standard processing")
            return self._process_single_chunk(full_text, pages, pdf_path)
        
        # Create intelligent chunks
        chunks = self._create_smart_chunks(pages)
        print(f"📦 Created {len(chunks)} chunks for processing")
        
        # Process each chunk
        all_facts = []
        all_citations = {}
        
        for i, chunk in enumerate(chunks, 1):
            print(f"\n🔄 Processing chunk {i}/{len(chunks)} ({len(chunk['text']):,} chars)")
            chunk_result = self._process_chunk(chunk, i, len(chunks))
            
            # Merge results
            if chunk_result.get('facts'):
                all_facts.extend(chunk_result['facts'])
            
            if chunk_result.get('citations'):
                # Renumber citations to avoid conflicts
                for cite_id, cite_data in chunk_result['citations'].items():
                    new_id = f"{i:03d}_{cite_id}"
                    all_citations[new_id] = cite_data
        
        # Generate final summary using all facts and citations
        final_summary = self._generate_final_summary(all_facts, all_citations, pdf_path)
        
        return final_summary
    
    def _create_smart_chunks(self, pages: List[Dict]) -> List[Dict]:
        """
        Create intelligent chunks that respect page boundaries
        """
        chunks = []
        current_chunk = {
            'text': '',
            'pages': [],
            'start_page': None,
            'end_page': None
        }
        
        for page in pages:
            page_text = page.get('text', '')
            page_num = page.get('page_number', 0)
            
            # Check if adding this page would exceed chunk size
            if len(current_chunk['text']) + len(page_text) > self.chunk_size and current_chunk['text']:
                # Save current chunk
                chunks.append(current_chunk)
                
                # Start new chunk with overlap from previous page
                overlap_text = self._get_overlap_text(current_chunk['text'])
                current_chunk = {
                    'text': overlap_text + page_text,
                    'pages': [page_num],
                    'start_page': page_num,
                    'end_page': page_num
                }
            else:
                # Add to current chunk
                current_chunk['text'] += f"\n[Page {page_num}]\n{page_text}\n"
                current_chunk['pages'].append(page_num)
                if current_chunk['start_page'] is None:
                    current_chunk['start_page'] = page_num
                current_chunk['end_page'] = page_num
        
        # Add final chunk
        if current_chunk['text']:
            chunks.append(current_chunk)
        
        return chunks
    
    def _get_overlap_text(self, text: str) -> str:
        """Get overlap text from the end of a chunk"""
        if len(text) <= self.overlap:
            return text
        
        # Try to find a sentence boundary
        overlap_start = len(text) - self.overlap
        sentence_end = text.rfind('.', overlap_start)
        
        if sentence_end > overlap_start - 200:  # Within reasonable distance
            return text[sentence_end + 1:].strip() + "\n"
        
        return text[-self.overlap:].strip() + "\n"
    
    def _process_chunk(self, chunk: Dict, chunk_num: int, total_chunks: int) -> Dict:
        """Process a single chunk"""
        
        prompt = f"""
You are processing chunk {chunk_num} of {total_chunks} from a trust document.
This chunk covers pages {chunk['start_page']} to {chunk['end_page']}.

Extract key facts and create citations from this chunk.

IMPORTANT RULES:
1. Only extract FACTS with specific details (names, dates, amounts, provisions)
2. Each fact MUST have a page number
3. Create citations for important facts
4. Return valid JSON only

Return JSON in this format:
{{
    "facts": [
        {{
            "fact": "Clear statement of fact",
            "page": <page_number>,
            "type": "category"
        }}
    ],
    "citations": {{
        "001": {{
            "page": <page_number>,
            "text": "Exact quote from document",
            "type": "category"
        }}
    }}
}}

DOCUMENT CHUNK:
{chunk['text'][:15000]}  # Limit chunk size sent to LLM
"""
        
        try:
            result = self.llm_client.process_document("You are a trust document analyzer.", prompt)
            
            # The response is already a dictionary if successful
            if isinstance(result, dict):
                return result
            
            # If it's a string, try to parse it
            json_str = self._extract_json(str(result))
            return json.loads(json_str)
            
        except Exception as e:
            print(f"⚠️ Error processing chunk {chunk_num}: {e}")
            return {"facts": [], "citations": {}}
    
    def _process_single_chunk(self, full_text: str, pages: List, pdf_path: str) -> Dict:
        """Process document as single chunk (fallback to standard processing)"""
        from multi_pass_processor import process_trust_multipass
        
        # Use the existing multi-pass processor for smaller documents
        return process_trust_multipass(pdf_path)
    
    def _generate_final_summary(self, all_facts: List, all_citations: Dict, pdf_path: str) -> Dict:
        """Generate final summary from all chunks"""
        
        # Group facts by type
        fact_groups = {}
        for fact in all_facts:
            fact_type = fact.get('type', 'general')
            if fact_type not in fact_groups:
                fact_groups[fact_type] = []
            fact_groups[fact_type].append(fact)
        
        # Create fact summary for LLM
        fact_summary = "EXTRACTED FACTS BY CATEGORY:\n\n"
        for fact_type, facts in fact_groups.items():
            fact_summary += f"{fact_type.upper()}:\n"
            for fact in facts[:10]:  # Limit facts per category
                fact_summary += f"- {fact['fact']} (Page {fact.get('page', '?')})\n"
            fact_summary += "\n"
        
        # Load summary generation prompt
        prompt_path = Path("prompts/pass3-summary-generation.md")
        if prompt_path.exists():
            with open(prompt_path, 'r') as f:
                summary_prompt = f.read()
        else:
            summary_prompt = "Generate a trust document summary using the provided facts and citations."
        
        # Create citation reference
        citation_ref = "\nAVAILABLE CITATIONS:\n"
        for cite_id, cite_data in list(all_citations.items())[:50]:  # Limit citations
            citation_ref += f"{{{{cite:{cite_id}}}}} - Page {cite_data['page']}: {cite_data['text'][:100]}...\n"
        
        final_prompt = f"""
{summary_prompt}

{fact_summary}

{citation_ref}

Generate a comprehensive summary using ONLY the citations provided above.
Use the exact citation format: {{{{cite:XXX}}}} where XXX is the citation ID.

Return the complete JSON structure as specified in the prompt.
"""
        
        try:
            result = self.llm_client.process_document("You are a trust document analyzer.", final_prompt)
            
            # Check if response is already a dict
            if not isinstance(result, dict):
                json_str = self._extract_json(str(result))
                result = json.loads(json_str)
            
            # Add metadata
            result['meta'] = {
                'total_facts_extracted': len(all_facts),
                'citations_created': len(all_citations),
                'processing_method': 'chunked',
                'chunks_processed': len(fact_groups),
                'document': Path(pdf_path).name
            }
            
            # Add all citations
            result['citations'] = all_citations
            
            return result
            
        except Exception as e:
            print(f"⚠️ Error generating final summary: {e}")
            
            # Return basic structure with extracted data
            return {
                'meta': {
                    'total_facts_extracted': len(all_facts),
                    'citations_created': len(all_citations),
                    'processing_method': 'chunked_with_errors',
                    'error': str(e)
                },
                'facts': all_facts,
                'citations': all_citations,
                'summary': {
                    'executive': 'Error generating summary. See facts and citations.',
                    'sections': []
                }
            }
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from LLM response"""
        # Try to find JSON boundaries
        json_start = text.find('{')
        json_end = text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = text[json_start:json_end]
            
            # Clean up common issues
            json_str = re.sub(r',\s*}', '}', json_str)  # Remove trailing commas
            json_str = re.sub(r',\s*]', ']', json_str)  # Remove trailing commas in arrays
            
            return json_str
        
        return text


def process_large_document(pdf_path: str, output_path: str = None):
    """
    Process a large document with intelligent chunking
    """
    processor = ChunkedDocumentProcessor()
    result = processor.process_large_document(pdf_path)
    
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n📁 Results saved to: {output_path}")
    
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
    else:
        pdf_file = "data/Jerry Simons Trust.pdf"  # Large document
    
    output_file = pdf_file.replace('.pdf', '_chunked.json').replace('data/', 'results/')
    
    print(f"Processing large document: {pdf_file}")
    result = process_large_document(pdf_file, output_file)
    
    print(f"\n📊 Results:")
    print(f"  - Facts extracted: {result.get('meta', {}).get('total_facts_extracted', 0)}")
    print(f"  - Citations created: {result.get('meta', {}).get('citations_created', 0)}")
    print(f"  - Processing method: {result.get('meta', {}).get('processing_method')}")