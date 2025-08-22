#!/usr/bin/env python3
"""
Multi-Pass Trust Document Processor
Combines prompt engineering with intelligent processing
"""

import json
import re
from typing import Dict, List, Tuple
from pathlib import Path
from pdf_processor import PDFProcessor
from llm_client import LLMClient

class MultiPassTrustProcessor:
    """
    Agent that makes multiple passes through a document for accurate citation extraction
    """
    
    def __init__(self, llm_provider=None):
        self.pdf_processor = PDFProcessor()
        self.llm_client = LLMClient(provider=llm_provider)
        self.facts_db = {}
        self.citations_db = {}
        # Load prompts from files
        self.prompts = self._load_prompts()
        
    def process_document(self, pdf_path: str) -> Dict:
        """
        Multi-pass processing for accurate citations
        """
        print("="*60)
        print("MULTI-PASS TRUST DOCUMENT PROCESSOR")
        print("="*60)
        
        # Extract text
        print("\n📄 PASS 0: Extracting text from PDF...")
        full_text, pages = self.pdf_processor.extract_text_from_pdf(pdf_path)
        total_pages = len(pages)
        print(f"✓ Extracted {total_pages} pages")
        
        # PASS 1: Extract key facts with locations
        print("\n🔍 PASS 1: Extracting key facts and locations...")
        facts = self._pass1_extract_facts(full_text, pages)
        print(f"✓ Found {len(facts)} key facts")
        
        # PASS 2: Generate citations for all facts
        print("\n📝 PASS 2: Generating citations for all facts...")
        citations = self._pass2_generate_citations(facts, pages)
        print(f"✓ Created {len(citations)} citations")
        
        # PASS 3: Generate summary using only existing citations
        print("\n📋 PASS 3: Generating summary with verified citations...")
        summary = self._pass3_generate_summary(facts, citations, full_text)
        print(f"✓ Summary complete")
        
        # PASS 4: Validate and cleanup
        print("\n✅ PASS 4: Validation and cleanup...")
        result = self._pass4_validate_and_cleanup(summary, citations)
        print(f"✓ Final validation complete")
        
        return result
    
    def _load_prompts(self) -> Dict:
        """Load prompts from the prompts folder"""
        prompts = {}
        prompt_files = {
            'pass1': 'prompts/pass1-fact-extraction.md',
            'pass3': 'prompts/pass3-summary-generation.md',
            'main': 'prompts/trust-summary-prompt.md'
        }
        
        for key, path in prompt_files.items():
            if Path(path).exists():
                with open(path, 'r') as f:
                    prompts[key] = f.read()
            else:
                print(f"Warning: Prompt file not found: {path}")
                prompts[key] = ""
        
        return prompts
    
    def _pass1_extract_facts(self, full_text: str, pages: List) -> List[Dict]:
        """
        PASS 1: Extract facts with their locations
        This can be both prompt-based (LLM) and rule-based (regex)
        """
        facts = []
        
        # Hybrid approach: Use LLM for complex extraction, regex for standard patterns
        
        # 1. Quick regex extraction for standard trust elements
        print("  - Extracting standard trust elements...")
        regex_facts = self._extract_standard_facts(full_text, pages)
        facts.extend(regex_facts)
        
        # 2. LLM extraction for complex facts
        print("  - Using LLM to extract complex provisions...")
        
        # Use the prompt from the prompts folder
        fact_prompt = self.prompts.get('pass1', '')
        if not fact_prompt:
            print("    Warning: Using fallback prompt for fact extraction")
            fact_prompt = "Extract all key facts from this trust document with page numbers."
        
        # Process in chunks for better accuracy
        if len(pages) > 20:
            # Process in chunks
            for i in range(0, len(pages), 20):
                chunk_pages = pages[i:i+20]
                chunk_text = "\n".join([f"[Page {p['page_number']}]\n{p['text']}" for p in chunk_pages])
                chunk_facts = self._extract_facts_with_llm(fact_prompt, chunk_text, page_offset=i)
                facts.extend(chunk_facts)
        else:
            # Process all at once
            llm_facts = self._extract_facts_with_llm(fact_prompt, full_text, page_offset=0)
            facts.extend(llm_facts)
        
        # Deduplicate facts
        facts = self._deduplicate_facts(facts)
        
        return facts
    
    def _pass2_generate_citations(self, facts: List[Dict], pages: List) -> Dict:
        """
        PASS 2: Generate citations for all extracted facts
        """
        citations = {}
        
        for i, fact in enumerate(facts, 1):
            cite_id = f"{i:03d}"
            
            # Find the exact text on the page if not already provided
            if 'exact_text' not in fact and 'statement' in fact:
                page_num = fact.get('page', 1)
                if page_num <= len(pages):
                    page_text = pages[page_num - 1]['text']
                    # Try to find relevant text
                    fact['exact_text'] = self._find_text_for_fact(fact['statement'], page_text)
            
            citations[cite_id] = {
                'page': fact.get('page', 1),
                'text': fact.get('exact_text', fact.get('statement', 'No statement provided')),
                'type': fact.get('type', 'general'),
                'confidence': fact.get('confidence', 1.0)
            }
            
            # Store the citation ID with the fact for Pass 3
            fact['cite_id'] = cite_id
        
        return citations
    
    def _pass3_generate_summary(self, facts: List[Dict], citations: Dict, full_text: str) -> Dict:
        """
        PASS 3: Generate summary using ONLY pre-created citations
        """
        # Create a fact reference list for the LLM
        fact_list = "\n".join([
            f"- {fact.get('statement', fact.get('exact_text', 'Fact')[:100])} [use {{{{cite:{fact['cite_id']}}}}}]"
            for fact in facts if 'cite_id' in fact
        ])
        
        # Use the Pass 3 prompt from the prompts folder
        base_prompt = self.prompts.get('pass3', '')
        if not base_prompt:
            print("    Warning: Pass 3 prompt not found, using simplified version")
            base_prompt = "Create a trust summary using only the provided citations."
        
        # Combine with the fact list
        summary_prompt = f"""
        {base_prompt}
        
        ## AVAILABLE FACTS WITH ASSIGNED CITATIONS:
        {fact_list}
        
        ## REMINDER:
        - You may ONLY use the citation numbers listed above
        - Every factual statement MUST include its citation
        - Use the exact format: {{{{cite:001}}}}, {{{{cite:002}}}}, etc.
        - Output ONLY valid JSON following the structure specified
        """
        
        # Get summary from LLM
        summary_response = self.llm_client.process_document(
            system_prompt="You are a trust document summarizer. You must output ONLY valid JSON. Do not include any text before or after the JSON.",
            user_content=summary_prompt
        )
        
        return summary_response
    
    def _pass4_validate_and_cleanup(self, summary: Dict, citations: Dict) -> Dict:
        """
        PASS 4: Validate all citations are properly linked
        """
        # Ensure all referenced citations exist
        summary_str = json.dumps(summary)
        referenced = set(re.findall(r'\{\{cite:(\d+)\}\}', summary_str))
        
        # Remove any citations not referenced
        used_citations = {
            cite_id: cite_data 
            for cite_id, cite_data in citations.items() 
            if cite_id in referenced
        }
        
        # Check for any missing (shouldn't happen with our approach)
        missing = referenced - set(used_citations.keys())
        if missing:
            print(f"  ⚠️ Warning: {len(missing)} citations referenced but not defined")
            # These shouldn't exist with our approach, but add safety placeholders
            for cite_id in missing:
                used_citations[cite_id] = {
                    'page': 1,
                    'text': '[Error: Citation not found]',
                    'type': 'error'
                }
        
        # Combine summary and citations
        result = summary.copy() if isinstance(summary, dict) else {'summary': summary}
        result['citations'] = used_citations
        
        # Add metadata
        result['meta'] = {
            'total_facts_extracted': len(self.facts_db),
            'citations_created': len(used_citations),
            'processing_method': 'multi_pass',
            'passes_completed': 4
        }
        
        return result
    
    # Helper methods
    def _extract_standard_facts(self, text: str, pages: List) -> List[Dict]:
        """Extract standard trust facts using regex patterns"""
        facts = []
        
        patterns = {
            'trust_creation': [
                r'(?i)(agreement|trust).{0,50}made.{0,50}(\w+\s+\d+,?\s+\d{4})',
                r'(?i)dated?.{0,20}(\w+\s+\d+,?\s+\d{4})',
            ],
            'grantor': [
                r'(?i)(grantor|settlor|trustor)[\s:]+([A-Z][A-Za-z\s\.]+?)(?:,|\s+of)',
            ],
            'trustee': [
                r'(?i)(trustee)[\s:]+([A-Z][A-Za-z\s\.]+?)(?:,|\s+of)',
            ],
        }
        
        for fact_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.finditer(pattern, text[:10000])  # Focus on first pages
                for match in matches:
                    # Find which page this is on
                    page_num = self._find_page_for_position(match.start(), text, pages)
                    
                    facts.append({
                        'statement': self._clean_match_text(match.group(0)),
                        'type': fact_type,
                        'page': page_num,
                        'exact_text': match.group(0),
                        'confidence': 0.9
                    })
                    break  # Take first match for each type
        
        return facts
    
    def _extract_facts_with_llm(self, prompt: str, text: str, page_offset: int) -> List[Dict]:
        """Extract facts using LLM"""
        try:
            response = self.llm_client.process_document(
                system_prompt=prompt,
                user_content=text
            )
            
            if isinstance(response, dict) and 'facts' in response:
                facts = response['facts']
            elif isinstance(response, list):
                facts = response
            else:
                facts = []
            
            # Adjust page numbers by offset
            for fact in facts:
                if 'page' in fact:
                    fact['page'] += page_offset
            
            return facts
            
        except Exception as e:
            print(f"    Warning: LLM extraction failed: {e}")
            return []
    
    def _deduplicate_facts(self, facts: List[Dict]) -> List[Dict]:
        """Remove duplicate facts"""
        seen = set()
        unique_facts = []
        
        for fact in facts:
            # Create a simple hash of the fact
            fact_key = f"{fact.get('type', '')}:{fact.get('statement', '')[:50]}"
            if fact_key not in seen:
                seen.add(fact_key)
                unique_facts.append(fact)
        
        return unique_facts
    
    def _find_text_for_fact(self, fact_statement: str, page_text: str) -> str:
        """Find supporting text for a fact on a page"""
        # Simple approach - find a sentence containing key words from fact
        words = fact_statement.lower().split()
        keywords = [w for w in words if len(w) > 4][:3]  # Top 3 long words
        
        sentences = page_text.split('.')
        for sentence in sentences:
            if all(kw in sentence.lower() for kw in keywords):
                return sentence.strip()
        
        return fact_statement  # Fallback
    
    def _find_page_for_position(self, position: int, full_text: str, pages: List) -> int:
        """Find which page a character position falls on"""
        current_pos = 0
        for page in pages:
            page_length = len(page['text'])
            if position <= current_pos + page_length:
                return page['page_number']
            current_pos += page_length
        return len(pages)  # Last page
    
    def _clean_match_text(self, text: str) -> str:
        """Clean up matched text"""
        return ' '.join(text.split())  # Normalize whitespace


# Easy-to-use wrapper
def process_trust_multipass(pdf_path: str, output_path: str = None):
    """
    Process a trust document using multi-pass approach
    """
    processor = MultiPassTrustProcessor()
    result = processor.process_document(pdf_path)
    
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n📁 Results saved to: {output_path}")
    
    return result


if __name__ == "__main__":
    import sys
    pdf_file = sys.argv[1] if len(sys.argv) > 1 else "data/2006 Eric Russell ILIT.pdf"
    output_file = pdf_file.replace('.pdf', '_multipass.json').replace('data/', 'results/')
    
    print(f"Processing: {pdf_file}")
    result = process_trust_multipass(pdf_file, output_file)
    
    print(f"\n📊 Results:")
    print(f"  - Citations created: {len(result.get('citations', {}))}")
    print(f"  - Processing method: {result.get('meta', {}).get('processing_method')}")
    print(f"  - Passes completed: {result.get('meta', {}).get('passes_completed')}")