"""
Smart Chunker - Intelligent document chunking with semantic boundaries
"""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import hashlib


@dataclass
class DocumentChunk:
    """Represents a chunk of document with metadata"""
    chunk_id: str
    text: str
    pages: List[int]
    start_page: int
    end_page: int
    start_char: int
    end_char: int
    chunk_type: str  # 'semantic', 'page', 'overflow'
    section_headers: List[str]
    context_before: str  # Previous chunk summary
    context_after: str   # Next chunk summary
    
    def to_dict(self) -> Dict:
        return {
            'chunk_id': self.chunk_id,
            'text': self.text,
            'pages': self.pages,
            'start_page': self.start_page,
            'end_page': self.end_page,
            'start_char': self.start_char,
            'end_char': self.end_char,
            'chunk_type': self.chunk_type,
            'section_headers': self.section_headers,
            'context_before': self.context_before,
            'context_after': self.context_after
        }


class SmartChunker:
    """Intelligent document chunker that respects semantic boundaries"""
    
    def __init__(self, 
                 max_chunk_size: int = 15000,
                 overlap_size: int = 500,
                 min_chunk_size: int = 1000):
        """
        Initialize smart chunker
        
        Args:
            max_chunk_size: Maximum characters per chunk
            overlap_size: Characters to overlap between chunks
            min_chunk_size: Minimum chunk size to avoid tiny chunks
        """
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
        self.min_chunk_size = min_chunk_size
        
        # Semantic boundary patterns for trust documents
        self.section_patterns = [
            # Articles and sections
            r'^ARTICLE\s+[IVX0-9]+[\.:]\s*.+',
            r'^Article\s+[IVX0-9]+[\.:]\s*.+',
            r'^SECTION\s+[0-9]+[\.:]\s*.+',
            r'^Section\s+[0-9]+[\.:]\s*.+',
            
            # Numbered sections
            r'^\d+\.\s+[A-Z][A-Z\s]+',  # "1. TRUST PROVISIONS"
            r'^\d+\.\d+\s+[A-Z][a-z]+',  # "1.1 Definitions"
            r'^[A-Z]\.\s+[A-Z][A-Z\s]+',  # "A. TRUSTEE POWERS"
            
            # Legal document markers
            r'^WHEREAS\b',
            r'^NOW,?\s+THEREFORE\b',
            r'^WITNESSETH\b',
            r'^RECITALS?\b',
            
            # Trust-specific sections
            r'^TRUST(?:EE)?\s+(?:POWERS?|PROVISIONS?|TERMS?)\b',
            r'^DISTRIBUTIONS?\b',
            r'^BENEFICIAR(?:Y|IES)\b',
            r'^(?:SUCCESSOR\s+)?TRUSTEE\b',
            r'^TERMINATION\b',
            r'^TAX\s+(?:PROVISIONS?|MATTERS?)\b',
            
            # Other structural markers
            r'^(?:SCHEDULE|EXHIBIT|APPENDIX)\s+[A-Z0-9]',
            r'^IN\s+WITNESS\s+WHEREOF\b',
        ]
        
        # Compile patterns for efficiency
        self.section_regex = re.compile(
            '|'.join(self.section_patterns), 
            re.IGNORECASE | re.MULTILINE
        )
        
        # Sub-section patterns (weaker boundaries)
        self.subsection_patterns = [
            r'^\([a-z]\)\s+',  # "(a) "
            r'^\(\d+\)\s+',    # "(1) "
            r'^[a-z]\.\s+',    # "a. "
            r'^[ivx]+\.\s+',   # "i. ", "ii. "
        ]
        
        self.subsection_regex = re.compile(
            '|'.join(self.subsection_patterns),
            re.IGNORECASE | re.MULTILINE
        )
        
        # Paragraph boundaries
        self.paragraph_pattern = re.compile(r'\n\n+')
        
        # Sentence boundaries
        self.sentence_pattern = re.compile(r'[.!?]\s+')
    
    def chunk_document(self, pages: List[Dict]) -> List[DocumentChunk]:
        """
        Chunk document intelligently using semantic boundaries
        
        Args:
            pages: List of page dictionaries with 'text' and 'page_number'
        
        Returns:
            List of document chunks
        """
        # First, identify document structure
        structure = self._analyze_structure(pages)
        
        # Create chunks based on structure
        if structure['has_sections']:
            chunks = self._chunk_by_sections(pages, structure)
        else:
            chunks = self._chunk_by_pages(pages)
        
        # Add context windows
        chunks = self._add_context_windows(chunks)
        
        # Validate and adjust chunks
        chunks = self._validate_chunks(chunks)
        
        return chunks
    
    def _analyze_structure(self, pages: List[Dict]) -> Dict:
        """Analyze document structure to determine chunking strategy"""
        structure = {
            'has_sections': False,
            'section_markers': [],
            'total_pages': len(pages),
            'total_chars': sum(len(p.get('text', '')) for p in pages),
            'avg_page_length': 0
        }
        
        if pages:
            structure['avg_page_length'] = structure['total_chars'] / len(pages)
        
        # Look for section markers
        full_text = '\n'.join(p.get('text', '') for p in pages[:10])  # Check first 10 pages
        section_matches = list(self.section_regex.finditer(full_text))
        
        if len(section_matches) >= 3:  # Need at least 3 sections to use section-based chunking
            structure['has_sections'] = True
            structure['section_markers'] = [m.group() for m in section_matches[:20]]
        
        return structure
    
    def _chunk_by_sections(self, pages: List[Dict], structure: Dict) -> List[DocumentChunk]:
        """Chunk document by semantic sections"""
        chunks = []
        current_chunk_text = ""
        current_pages = []
        current_headers = []
        current_start_page = 1
        current_start_char = 0
        total_chars = 0
        
        for page in pages:
            page_text = page.get('text', '')
            page_num = page.get('page_number', 1)
            
            # Find section boundaries in this page
            section_boundaries = list(self.section_regex.finditer(page_text))
            
            if not section_boundaries:
                # No section boundary, add to current chunk
                if len(current_chunk_text) + len(page_text) <= self.max_chunk_size:
                    current_chunk_text += f"\n[Page {page_num}]\n{page_text}\n"
                    current_pages.append(page_num)
                else:
                    # Chunk is too large, split at paragraph or sentence
                    if current_chunk_text:
                        chunks.append(self._create_chunk(
                            current_chunk_text, current_pages, 
                            current_start_page, current_start_char,
                            'semantic', current_headers
                        ))
                    
                    current_chunk_text = f"\n[Page {page_num}]\n{page_text}\n"
                    current_pages = [page_num]
                    current_start_page = page_num
                    current_start_char = total_chars
                    current_headers = []
            else:
                # Process text with section boundaries
                last_pos = 0
                for match in section_boundaries:
                    # Add text before section
                    before_text = page_text[last_pos:match.start()]
                    if before_text.strip():
                        if len(current_chunk_text) + len(before_text) <= self.max_chunk_size:
                            current_chunk_text += before_text
                        else:
                            # Save current chunk
                            if current_chunk_text:
                                chunks.append(self._create_chunk(
                                    current_chunk_text, current_pages,
                                    current_start_page, current_start_char,
                                    'semantic', current_headers
                                ))
                            current_chunk_text = before_text
                            current_pages = [page_num]
                            current_start_page = page_num
                            current_start_char = total_chars + last_pos
                            current_headers = []
                    
                    # Start new chunk with section header
                    if current_chunk_text and len(current_chunk_text) > self.min_chunk_size:
                        chunks.append(self._create_chunk(
                            current_chunk_text, current_pages,
                            current_start_page, current_start_char,
                            'semantic', current_headers
                        ))
                        current_chunk_text = ""
                        current_pages = []
                        current_headers = []
                    
                    # Add section header
                    section_header = match.group().strip()
                    current_headers.append(section_header)
                    current_chunk_text += f"\n[Page {page_num}]\n{page_text[match.start():]}"
                    current_pages = [page_num] if page_num not in current_pages else current_pages
                    current_start_page = page_num
                    current_start_char = total_chars + match.start()
                    last_pos = len(page_text)
                
                # Add remaining text
                if last_pos < len(page_text):
                    remaining = page_text[last_pos:]
                    if remaining.strip():
                        current_chunk_text += remaining
                        if page_num not in current_pages:
                            current_pages.append(page_num)
            
            total_chars += len(page_text)
        
        # Add final chunk
        if current_chunk_text:
            chunks.append(self._create_chunk(
                current_chunk_text, current_pages,
                current_start_page, current_start_char,
                'semantic', current_headers
            ))
        
        return chunks
    
    def _chunk_by_pages(self, pages: List[Dict]) -> List[DocumentChunk]:
        """Fallback: chunk by pages when no clear structure"""
        chunks = []
        current_chunk_text = ""
        current_pages = []
        current_start_page = 1
        current_start_char = 0
        total_chars = 0
        
        for page in pages:
            page_text = page.get('text', '')
            page_num = page.get('page_number', 1)
            
            # Check if adding this page exceeds max size
            if len(current_chunk_text) + len(page_text) <= self.max_chunk_size:
                current_chunk_text += f"\n[Page {page_num}]\n{page_text}\n"
                current_pages.append(page_num)
            else:
                # Save current chunk
                if current_chunk_text:
                    chunks.append(self._create_chunk(
                        current_chunk_text, current_pages,
                        current_start_page, current_start_char,
                        'page', []
                    ))
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk_text)
                current_chunk_text = overlap_text + f"\n[Page {page_num}]\n{page_text}\n"
                current_pages = [page_num]
                current_start_page = page_num
                current_start_char = total_chars
            
            total_chars += len(page_text)
        
        # Add final chunk
        if current_chunk_text:
            chunks.append(self._create_chunk(
                current_chunk_text, current_pages,
                current_start_page, current_start_char,
                'page', []
            ))
        
        return chunks
    
    def _create_chunk(self, text: str, pages: List[int], 
                     start_page: int, start_char: int,
                     chunk_type: str, headers: List[str]) -> DocumentChunk:
        """Create a DocumentChunk object"""
        chunk_id = hashlib.md5(f"{text[:100]}_{start_page}".encode()).hexdigest()[:8]
        
        return DocumentChunk(
            chunk_id=chunk_id,
            text=text.strip(),
            pages=pages,
            start_page=start_page,
            end_page=pages[-1] if pages else start_page,
            start_char=start_char,
            end_char=start_char + len(text),
            chunk_type=chunk_type,
            section_headers=headers,
            context_before="",  # Will be filled by _add_context_windows
            context_after=""    # Will be filled by _add_context_windows
        )
    
    def _get_overlap_text(self, text: str) -> str:
        """Get overlap text from the end of a chunk"""
        if len(text) <= self.overlap_size:
            return text
        
        # Try to find a sentence boundary
        overlap_start = len(text) - self.overlap_size
        sentences = list(self.sentence_pattern.finditer(text, overlap_start))
        
        if sentences:
            # Start from the beginning of a sentence
            return text[sentences[0].end():].strip() + "\n"
        
        # Fall back to paragraph boundary
        paragraphs = list(self.paragraph_pattern.finditer(text, overlap_start))
        if paragraphs:
            return text[paragraphs[0].end():].strip() + "\n"
        
        # Fall back to character boundary
        return text[-self.overlap_size:].strip() + "\n"
    
    def _add_context_windows(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Add context summaries from adjacent chunks"""
        for i, chunk in enumerate(chunks):
            # Add previous context
            if i > 0:
                prev_chunk = chunks[i-1]
                # Create a brief summary of previous chunk
                chunk.context_before = self._summarize_chunk(prev_chunk)
            
            # Add next context
            if i < len(chunks) - 1:
                next_chunk = chunks[i+1]
                # Create a brief summary of next chunk
                chunk.context_after = self._summarize_chunk(next_chunk)
        
        return chunks
    
    def _summarize_chunk(self, chunk: DocumentChunk) -> str:
        """Create a brief summary of a chunk for context"""
        # Extract key information
        summary_parts = []
        
        # Include section headers
        if chunk.section_headers:
            summary_parts.append(f"Sections: {', '.join(chunk.section_headers[:3])}")
        
        # Include page range
        summary_parts.append(f"Pages {chunk.start_page}-{chunk.end_page}")
        
        # Extract first meaningful sentence
        sentences = self.sentence_pattern.split(chunk.text)
        for sent in sentences[:5]:
            if len(sent) > 20 and not sent.startswith('[Page'):
                summary_parts.append(sent[:100])
                break
        
        return " | ".join(summary_parts)
    
    def _validate_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Validate and adjust chunks if needed"""
        validated = []
        
        for chunk in chunks:
            # Check minimum size
            if len(chunk.text) < self.min_chunk_size and validated:
                # Merge with previous chunk if too small
                prev_chunk = validated[-1]
                if len(prev_chunk.text) + len(chunk.text) <= self.max_chunk_size * 1.2:
                    # Merge chunks
                    prev_chunk.text += "\n" + chunk.text
                    prev_chunk.pages.extend(p for p in chunk.pages if p not in prev_chunk.pages)
                    prev_chunk.end_page = chunk.end_page
                    prev_chunk.end_char = chunk.end_char
                    prev_chunk.section_headers.extend(chunk.section_headers)
                    continue
            
            # Check maximum size
            if len(chunk.text) > self.max_chunk_size * 1.5:
                # Split oversized chunk
                sub_chunks = self._split_large_chunk(chunk)
                validated.extend(sub_chunks)
            else:
                validated.append(chunk)
        
        return validated
    
    def _split_large_chunk(self, chunk: DocumentChunk) -> List[DocumentChunk]:
        """Split a chunk that's too large"""
        sub_chunks = []
        text = chunk.text
        
        # Try to split at paragraph boundaries
        paragraphs = self.paragraph_pattern.split(text)
        
        current_text = ""
        for para in paragraphs:
            if len(current_text) + len(para) <= self.max_chunk_size:
                current_text += para + "\n\n"
            else:
                if current_text:
                    sub_chunk = self._create_chunk(
                        current_text,
                        chunk.pages,  # Keep same page references
                        chunk.start_page,
                        chunk.start_char + len(current_text),
                        'overflow',
                        chunk.section_headers
                    )
                    sub_chunks.append(sub_chunk)
                current_text = para + "\n\n"
        
        # Add remaining text
        if current_text:
            sub_chunk = self._create_chunk(
                current_text,
                chunk.pages,
                chunk.start_page,
                chunk.start_char + len(text) - len(current_text),
                'overflow',
                chunk.section_headers
            )
            sub_chunks.append(sub_chunk)
        
        return sub_chunks if sub_chunks else [chunk]


def chunk_document(pdf_path: str, max_chunk_size: int = 15000) -> List[DocumentChunk]:
    """
    Convenience function to chunk a PDF document
    
    Args:
        pdf_path: Path to PDF document
        max_chunk_size: Maximum chunk size
    
    Returns:
        List of document chunks
    """
    from pdf_processor import PDFProcessor
    
    # Extract text from PDF
    processor = PDFProcessor()
    full_text, pages = processor.extract_text_from_pdf(pdf_path)
    
    # Create chunks
    chunker = SmartChunker(max_chunk_size=max_chunk_size)
    chunks = chunker.chunk_document(pages)
    
    return chunks


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
    else:
        pdf_file = "data/2006 Eric Russell ILIT.pdf"
    
    print(f"Chunking document: {pdf_file}")
    chunks = chunk_document(pdf_file)
    
    print(f"\nCreated {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks, 1):
        print(f"\nChunk {i}:")
        print(f"  Type: {chunk.chunk_type}")
        print(f"  Pages: {chunk.start_page}-{chunk.end_page}")
        print(f"  Size: {len(chunk.text):,} chars")
        if chunk.section_headers:
            print(f"  Sections: {', '.join(chunk.section_headers[:3])}")
        print(f"  Preview: {chunk.text[:100]}...")