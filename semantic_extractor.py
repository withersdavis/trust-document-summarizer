"""
Semantic Fact Extractor - Extract structured facts from trust documents
"""

import re
import json
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib

@dataclass
class Fact:
    """Structured fact extracted from document"""
    fact: str  # The actual fact statement
    page: int  # Page number where fact appears
    char_position: int  # Character position in full text
    fact_type: str  # Category of fact
    confidence: float  # Confidence score (0-1)
    entities: List[str]  # Named entities in the fact
    context: str  # Surrounding context (for verification)
    fact_id: str = ""  # Unique ID for the fact
    
    def __post_init__(self):
        if not self.fact_id:
            # Generate unique ID based on content
            content = f"{self.fact}_{self.page}_{self.char_position}"
            self.fact_id = hashlib.md5(content.encode()).hexdigest()[:8]
    
    def to_dict(self) -> Dict:
        return asdict(self)


class SemanticFactExtractor:
    """Extract semantic facts from trust documents"""
    
    def __init__(self):
        # Entity patterns for trust documents
        self.entity_patterns = {
            'PERSON': [
                r'\b[A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b',  # Full names
                r'\b(?:Grantor|Settlor|Trustor|Trustee|Beneficiary)\b',  # Roles
            ],
            'DATE': [
                r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # MM/DD/YYYY or MM-DD-YYYY
                r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
                r'\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b',
            ],
            'MONEY': [
                r'\$[\d,]+(?:\.\d{2})?',  # Dollar amounts
                r'\b\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:dollars?|USD)\b',
            ],
            'PERCENT': [
                r'\b\d+(?:\.\d+)?%\b',  # Percentages
                r'\b\d+(?:\.\d+)?\s*percent\b',
            ],
            'AGE': [
                r'\b\d+\s*years?\s*(?:of\s*)?age\b',
                r'\bage\s*\d+\b',
                r'\b(?:eighteen|twenty-one|twenty-five|thirty|thirty-five|forty|fifty|sixty|sixty-five|seventy)\s*\(\d+\)\s*years?\b',
            ]
        }
        
        # Relationship patterns
        self.relationship_patterns = [
            (r'(\w+)\s+(?:is|shall be|was)\s+(?:the\s+)?(?:trustee|successor trustee)', 'trustee_appointment'),
            (r'(\w+)\s+(?:is|are)\s+(?:the\s+)?(?:beneficiary|beneficiaries)', 'beneficiary_designation'),
            (r'(?:grantor|settlor)\s+(?:is|was)\s+(\w+)', 'grantor_identification'),
            (r'(\w+)\s+(?:shall|may|is authorized to)\s+(.+)', 'authority_grant'),
            (r'upon\s+the\s+death\s+of\s+(\w+)', 'death_trigger'),
            # Better patterns for extracting key parties
            (r'between[,\s]+I,\s+([^,]+)[,\s]+and\s+([^,]+)[,\s]+the\s+(?:initial\s+)?trustee', 'trust_parties'),
            (r'I,\s+([^,]+),\s+(?:as\s+)?(?:grantor|settlor|creator)', 'grantor_identification'),
            (r'([^,]+),\s+the\s+(?:initial\s+)?trustee', 'trustee_appointment'),
        ]
        
        # Condition patterns
        self.condition_patterns = [
            (r'(?:if|when|upon)\s+(.+?)[,\.]', 'condition'),
            (r'provided\s+(?:that|however)\s+(.+?)[,\.]', 'provision'),
            (r'(?:unless|except)\s+(.+?)[,\.]', 'exception'),
            (r'subject\s+to\s+(.+?)[,\.]', 'restriction'),
        ]
        
        # Trust-specific fact patterns
        self.trust_patterns = {
            'trust_creation': [
                r'(?:trust|agreement)\s+(?:dated|made|executed)\s+(?:on\s+)?(.+?)(?:\.|,)',
                r'(?:established|created)\s+(?:on\s+)?(.+?)(?:\.|,)',
                r'This\s+(.+?Trust)\s+Agreement\s+is\s+made',  # Captures "This [Trust Name] Agreement is made"
                r'(?:name|named|known as)\s+(?:this trust |the |this )?(.+?(?:Trust|TRUST))',  # Captures trust names
                r'The\s+(.+?(?:Trust|TRUST))\s+(?:Agreement|Document)',  # The [Trust Name] Agreement
            ],
            'distribution': [
                r'(?:distribute|pay)\s+(.+?)\s+to\s+(.+?)(?:\.|,)',
                r'(\w+)\s+(?:shall|may)\s+receive\s+(.+?)(?:\.|,)',
            ],
            'trustee_power': [
                r'trustee\s+(?:shall|may|is authorized to)\s+(.+?)(?:\.|,)',
                r'trustee\s+(?:has|have)\s+(?:the\s+)?(?:power|authority)\s+to\s+(.+?)(?:\.|,)',
            ],
            'tax_provision': [
                r'(?:GST|estate|income|gift)\s+tax\s+(.+?)(?:\.|,)',
                r'tax\s+(?:exemption|deduction|credit)\s+(.+?)(?:\.|,)',
            ],
            'termination': [
                r'trust\s+(?:shall|will)\s+terminate\s+(.+?)(?:\.|,)',
                r'upon\s+(?:termination|conclusion)\s+(.+?)(?:\.|,)',
            ]
        }
    
    def extract_facts(self, text: str, page_num: int = 1, 
                     start_position: int = 0) -> List[Fact]:
        """
        Extract all facts from a text segment
        
        Args:
            text: Text to extract facts from
            page_num: Page number for reference
            start_position: Starting character position in full document
        
        Returns:
            List of extracted facts
        """
        facts = []
        
        # Extract entities first
        entities = self._extract_entities(text)
        
        # Extract relationship facts
        for pattern, fact_type in self.relationship_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Get complete sentence instead of just the match
                fact_text = self._get_complete_sentence(text, match.start(), match.end())
                position = start_position + match.start()
                context = self._get_context(text, match.start(), match.end())
                
                fact = Fact(
                    fact=fact_text,
                    page=page_num,
                    char_position=position,
                    fact_type=fact_type,
                    confidence=0.8,
                    entities=self._find_entities_in_text(fact_text, entities),
                    context=context
                )
                facts.append(fact)
        
        # Extract condition facts
        for pattern, fact_type in self.condition_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Get complete sentence instead of just the match
                fact_text = self._get_complete_sentence(text, match.start(), match.end())
                position = start_position + match.start()
                context = self._get_context(text, match.start(), match.end())
                
                fact = Fact(
                    fact=fact_text,
                    page=page_num,
                    char_position=position,
                    fact_type=fact_type,
                    confidence=0.7,
                    entities=self._find_entities_in_text(fact_text, entities),
                    context=context
                )
                facts.append(fact)
        
        # Extract trust-specific facts
        for fact_type, patterns in self.trust_patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
                    # Get complete sentence instead of just the match
                    fact_text = self._get_complete_sentence(text, match.start(), match.end())
                    position = start_position + match.start()
                    context = self._get_context(text, match.start(), match.end())
                    
                    fact = Fact(
                        fact=fact_text,
                        page=page_num,
                        char_position=position,
                        fact_type=fact_type,
                        confidence=0.9,
                        entities=self._find_entities_in_text(fact_text, entities),
                        context=context
                    )
                    facts.append(fact)
        
        # Extract provision sentences (fallback for important content)
        provision_sentences = self._extract_provision_sentences(text)
        for sent_text, sent_start in provision_sentences:
            # Check if this sentence is already captured
            if not any(sent_start >= f.char_position - start_position and 
                      sent_start <= f.char_position - start_position + len(f.fact) 
                      for f in facts):
                position = start_position + sent_start
                
                fact = Fact(
                    fact=sent_text,
                    page=page_num,
                    char_position=position,
                    fact_type='provision',
                    confidence=0.6,
                    entities=self._find_entities_in_text(sent_text, entities),
                    context=sent_text  # Use full sentence as context
                )
                facts.append(fact)
        
        return facts
    
    def _extract_entities(self, text: str) -> Dict[str, List[Tuple[str, int, int]]]:
        """Extract named entities from text"""
        entities = {}
        
        for entity_type, patterns in self.entity_patterns.items():
            entities[entity_type] = []
            for pattern in patterns:
                for match in re.finditer(pattern, text):
                    entity_text = match.group(0)
                    start = match.start()
                    end = match.end()
                    entities[entity_type].append((entity_text, start, end))
        
        return entities
    
    def _find_entities_in_text(self, text: str, all_entities: Dict) -> List[str]:
        """Find which entities appear in a given text"""
        found = []
        for entity_type, entity_list in all_entities.items():
            for entity_text, _, _ in entity_list:
                if entity_text.lower() in text.lower():
                    found.append(f"{entity_type}:{entity_text}")
        return found
    
    def _get_context(self, text: str, start: int, end: int, 
                     context_chars: int = 100) -> str:
        """Get surrounding context for a match"""
        context_start = max(0, start - context_chars)
        context_end = min(len(text), end + context_chars)
        
        context = text[context_start:context_end]
        
        # Clean up context
        context = ' '.join(context.split())
        
        # Add ellipsis if truncated
        if context_start > 0:
            context = '...' + context
        if context_end < len(text):
            context = context + '...'
        
        return context
    
    def _get_complete_sentence(self, text: str, start: int, end: int) -> str:
        """Extract complete sentence containing the match"""
        # Find sentence start (look backwards for sentence ending)
        sentence_start = start
        for i in range(start - 1, max(0, start - 500), -1):
            if text[i] in '.!?;' and i + 1 < len(text) and text[i + 1] in ' \n\t':
                sentence_start = i + 2
                break
        else:
            # If no sentence ending found, look for paragraph start
            for i in range(start - 1, max(0, start - 200), -1):
                if text[i] == '\n':
                    sentence_start = i + 1
                    break
        
        # Find sentence end (look forward for sentence ending)
        sentence_end = end
        
        # More aggressive search for sentence completion
        for i in range(end, min(len(text), end + 800)):
            # Check for sentence endings
            if i < len(text) - 1:
                # Period followed by space or newline
                if text[i] == '.' and (text[i+1] in ' \n\t' or text[i+1].isupper()):
                    sentence_end = i + 1
                    break
                # Semicolon or other endings
                elif text[i] in ';!?' and text[i+1] in ' \n\t':
                    sentence_end = i + 1
                    break
                # Double newline (paragraph break)
                elif i < len(text) - 2 and text[i:i+2] == '\n\n':
                    sentence_end = i
                    break
        
        # Extract the complete sentence
        sentence = text[sentence_start:sentence_end].strip()
        
        # Clean up excessive whitespace but preserve some structure
        lines = sentence.split('\n')
        cleaned_lines = [' '.join(line.split()) for line in lines]
        sentence = ' '.join(cleaned_lines)
        
        # Final cleanup to remove multiple spaces
        sentence = ' '.join(sentence.split())
        
        return sentence
    
    def _extract_provision_sentences(self, text: str) -> List[Tuple[str, int]]:
        """Extract sentences that look like legal provisions"""
        provision_keywords = [
            'shall', 'may', 'must', 'trustee', 'beneficiary', 'distribute',
            'payment', 'income', 'principal', 'power', 'authority', 'discretion',
            'terminate', 'vest', 'estate', 'tax', 'exempt'
        ]
        
        sentences = []
        # Simple sentence splitting (can be improved with better NLP)
        sent_pattern = r'[A-Z][^.!?]*[.!?]'
        
        for match in re.finditer(sent_pattern, text, re.DOTALL):
            sent = match.group(0)
            sent_lower = sent.lower()
            
            # Check if sentence contains provision keywords
            if any(keyword in sent_lower for keyword in provision_keywords):
                sentences.append((sent.strip(), match.start()))
        
        return sentences
    
    def extract_from_pages(self, pages: List[Dict]) -> List[Fact]:
        """
        Extract facts from multiple pages
        
        Args:
            pages: List of page dictionaries with 'text' and 'page_number'
        
        Returns:
            List of all extracted facts
        """
        all_facts = []
        current_position = 0
        
        for page in pages:
            page_text = page.get('text', '')
            page_num = page.get('page_number', 1)
            
            facts = self.extract_facts(page_text, page_num, current_position)
            all_facts.extend(facts)
            
            current_position += len(page_text)
        
        return all_facts
    
    def deduplicate_facts(self, facts: List[Fact]) -> List[Fact]:
        """Remove duplicate or highly similar facts"""
        unique_facts = []
        seen_texts = set()
        
        for fact in facts:
            # Normalize fact text for comparison
            normalized = ' '.join(fact.fact.lower().split())
            
            if normalized not in seen_texts:
                seen_texts.add(normalized)
                unique_facts.append(fact)
        
        return unique_facts
    
    def rank_facts_by_importance(self, facts: List[Fact]) -> List[Fact]:
        """Rank facts by importance based on type and confidence"""
        importance_weights = {
            'trust_creation': 1.0,
            'trustee_appointment': 0.9,
            'beneficiary_designation': 0.9,
            'distribution': 0.85,
            'trustee_power': 0.8,
            'tax_provision': 0.75,
            'condition': 0.7,
            'provision': 0.6,
            'termination': 0.85,
            'authority_grant': 0.7,
            'death_trigger': 0.8,
        }
        
        for fact in facts:
            weight = importance_weights.get(fact.fact_type, 0.5)
            fact.confidence = fact.confidence * weight
        
        return sorted(facts, key=lambda f: f.confidence, reverse=True)


def extract_facts_from_document(pdf_path: str) -> List[Fact]:
    """
    Convenience function to extract facts from a PDF document
    
    Args:
        pdf_path: Path to PDF document
    
    Returns:
        List of extracted facts
    """
    from pdf_processor import PDFProcessor
    
    # Extract text from PDF
    processor = PDFProcessor()
    full_text, pages = processor.extract_text_from_pdf(pdf_path)
    
    # Extract facts
    extractor = SemanticFactExtractor()
    facts = extractor.extract_from_pages(pages)
    
    # Deduplicate and rank
    facts = extractor.deduplicate_facts(facts)
    facts = extractor.rank_facts_by_importance(facts)
    
    return facts


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
    else:
        pdf_file = "data/2006 Eric Russell ILIT.pdf"
    
    print(f"Extracting facts from: {pdf_file}")
    facts = extract_facts_from_document(pdf_file)
    
    print(f"\nExtracted {len(facts)} facts")
    print("\nTop 10 facts by importance:")
    for i, fact in enumerate(facts[:10], 1):
        print(f"\n{i}. [{fact.fact_type}] (confidence: {fact.confidence:.2f})")
        print(f"   Page {fact.page}: {fact.fact[:100]}...")
        if fact.entities:
            print(f"   Entities: {', '.join(fact.entities[:5])}")