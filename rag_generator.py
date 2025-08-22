"""
RAG Summary Generator - Generate summaries using retrieval-augmented generation
"""

import json
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from semantic_extractor import Fact, SemanticFactExtractor
from vector_store import DocumentVectorStore
from concept_categorizer import ConceptCategorizer
from smart_chunker import SmartChunker, DocumentChunk
from llm_client import LLMClient


class RAGSummaryGenerator:
    """Generate trust summaries using RAG approach"""
    
    def __init__(self, vector_store: DocumentVectorStore = None):
        """
        Initialize RAG generator
        
        Args:
            vector_store: Vector store with indexed facts
        """
        self.vector_store = vector_store or DocumentVectorStore()
        self.categorizer = ConceptCategorizer()
        self.llm_client = LLMClient()
        
        # Section queries for retrieval
        self.section_queries = {
            'essential_info': {
                'query': "trust name creation date grantor settlor trustee beneficiary established agreement",
                'categories': ['trust_creation', 'grantor_settlor', 'trustee_appointment', 'beneficiary_designation'],
                'top_k': 20
            },
            'how_it_works': {
                'query': "trustee powers authority administration management discretion operate provisions",
                'categories': ['trustee_powers', 'administrative_provisions', 'withdrawal_rights'],
                'top_k': 15
            },
            'important_provisions': {
                'query': "restrictions conditions spendthrift tax protection special provisions limitations",
                'categories': ['spendthrift_protection', 'tax_provisions', 'special_provisions', 'termination_conditions'],
                'top_k': 15
            },
            'distributions': {
                'query': "distribution beneficiary income principal payment receive age death mandatory discretionary",
                'categories': ['distribution_rules', 'distribution_timing', 'beneficiary_designation'],
                'top_k': 20
            }
        }
        
        # Load prompt templates
        self.prompts = self._load_prompts()
    
    def _load_prompts(self) -> Dict[str, str]:
        """Load prompt templates from files"""
        prompts = {}
        prompt_dir = Path("prompts")
        
        # Load main summary prompt
        summary_prompt_path = prompt_dir / "trust-summary-prompt.md"
        if summary_prompt_path.exists():
            with open(summary_prompt_path, 'r') as f:
                prompts['main'] = f.read()
        
        # Load section-specific prompts
        section_prompts = {
            'essential_info': """Generate the Essential Information section with:
- Trust name and date
- Grantor/Settlor identity
- Initial trustees
- Primary beneficiaries

Use ONLY the provided facts and citations.""",
            
            'how_it_works': """Generate the How the Trust Works section with:
- Administrative structure
- Trustee powers and limitations
- Management provisions

Use ONLY the provided facts and citations.""",
            
            'important_provisions': """Generate the Important Provisions section with:
- Key restrictions and conditions
- Special provisions
- Tax considerations
- Asset protection features

Use ONLY the provided facts and citations.""",
            
            'distributions': """Generate the Distribution Summary section with:
- Who receives distributions and when
- Distribution conditions and triggers
- Mandatory vs discretionary distributions

Use ONLY the provided facts and citations."""
        }
        
        prompts.update(section_prompts)
        return prompts
    
    def generate_summary(self, pdf_path: str, facts: List[Fact] = None) -> Dict:
        """
        Generate complete trust summary using RAG
        
        Args:
            pdf_path: Path to PDF document
            facts: Optional pre-extracted facts
        
        Returns:
            Complete summary with citations
        """
        # Extract facts if not provided
        if facts is None:
            extractor = SemanticFactExtractor()
            from pdf_processor import PDFProcessor
            processor = PDFProcessor()
            _, pages = processor.extract_text_from_pdf(pdf_path)
            facts = extractor.extract_from_pages(pages)
        
        # Index facts in vector store (clear first to avoid duplicates)
        doc_id = Path(pdf_path).stem
        try:
            # Clear existing facts for this document
            self.vector_store.clear_collection()
            self.vector_store = DocumentVectorStore()  # Reinitialize
        except:
            pass
        self.vector_store.index_facts(facts, doc_id)
        
        # Generate executive summary
        executive = self._generate_executive_summary(facts)
        
        # Generate each section
        sections = []
        citations = {}
        
        for section_type in ['essential_info', 'how_it_works', 'important_provisions', 'distributions']:
            section_data = self._generate_section(section_type, facts)
            sections.append(section_data['section'])
            citations.update(section_data['citations'])
        
        # Create final summary
        summary = {
            'meta': {
                'processing_method': 'rag',
                'total_facts': len(facts),
                'citations_created': len(citations),
                'document': Path(pdf_path).name
            },
            'summary': {
                'executive': executive,
                'sections': sections
            },
            'citations': citations
        }
        
        return summary
    
    def _generate_executive_summary(self, facts: List[Fact]) -> str:
        """Generate executive summary"""
        # Get most important facts
        important_facts = []
        for fact in facts:
            importance = self.categorizer.get_fact_importance(fact)
            if importance > 0.7:
                important_facts.append((fact, importance))
        
        # Sort by importance
        important_facts.sort(key=lambda x: x[1], reverse=True)
        top_facts = [f[0] for f in important_facts[:10]]
        
        # Create prompt
        fact_text = "\n".join([f"- Page {f.page}: {f.fact}" for f in top_facts])
        
        prompt = f"""Generate a 2-3 sentence executive summary of this trust document based on these key facts:

{fact_text}

Focus on: trust creation date, primary purpose, and key parties.
Keep it concise and factual."""
        
        # Use direct API call for text generation (not JSON)
        try:
            from anthropic import Anthropic
            client = Anthropic()
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                temperature=0.3,
                system="You are a trust document analyst creating an executive summary.",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except:
            # Fallback to simple response
            return "This trust document establishes provisions for the management and distribution of trust assets."
    
    def _generate_section(self, section_type: str, all_facts: List[Fact]) -> Dict:
        """Generate a specific section with citations"""
        # Retrieve relevant facts
        section_config = self.section_queries[section_type]
        
        # Search for relevant facts
        search_results = self.vector_store.semantic_search(
            section_config['query'],
            top_k=section_config['top_k']
        )
        
        # Filter by categories
        relevant_facts = []
        seen_facts = set()
        
        for result in search_results:
            fact_text = result['metadata'].get('fact_text', '')
            if fact_text and fact_text not in seen_facts:
                # Reconstruct fact from metadata
                fact = Fact(
                    fact=fact_text,
                    page=result['metadata'].get('page', 1),
                    char_position=result['metadata'].get('char_position', 0),
                    fact_type=result['metadata'].get('fact_type', ''),
                    confidence=result['metadata'].get('confidence', 0.5),
                    entities=json.loads(result['metadata'].get('entities', '[]')),
                    context=result.get('text', '')
                )
                relevant_facts.append(fact)
                seen_facts.add(fact_text)
        
        # Also get facts by category
        category_facts = self.categorizer.filter_facts_by_section(all_facts, section_type)
        for fact in category_facts[:10]:
            if fact.fact not in seen_facts:
                relevant_facts.append(fact)
                seen_facts.add(fact.fact)
        
        # Generate citations for facts
        citations = self._create_citations(relevant_facts[:15])  # Limit citations
        
        # Create section content
        section_content = self._generate_section_content(
            section_type, 
            relevant_facts, 
            citations
        )
        
        return {
            'section': {
                'id': section_type,
                'title': self._get_section_title(section_type),
                'content': section_content
            },
            'citations': citations
        }
    
    def _create_citations(self, facts: List[Fact]) -> Dict:
        """Create citations from facts - using complete fact text without truncation"""
        citations = {}
        
        for i, fact in enumerate(facts, 1):
            cite_id = f"{i:03d}"
            
            # Use the complete fact text without any truncation
            # Citations should be complete for proper reference
            citations[cite_id] = {
                'page': fact.page,
                'text': fact.fact,  # Full fact text, no truncation
                'type': fact.fact_type,
                'confidence': fact.confidence
            }
        
        return citations
    
    def _generate_section_content(self, section_type: str, 
                                 facts: List[Fact], 
                                 citations: Dict) -> str:
        """Generate content for a section"""
        # Create fact summary with citation references
        fact_lines = []
        for i, fact in enumerate(facts[:10], 1):  # Limit facts used
            cite_id = f"{i:03d}"
            if cite_id in citations:
                fact_lines.append(f"- {fact.fact} {{{{cite:{cite_id}}}}}")
        
        fact_text = "\n".join(fact_lines)
        
        # Get section prompt
        section_prompt = self.prompts.get(section_type, "Generate section content.")
        
        # Create full prompt
        prompt = f"""{section_prompt}

Available facts with citations:
{fact_text}

Format the response as structured content with headers and bullet points.
Include citation references in the format {{{{cite:XXX}}}} where appropriate.
"""
        
        # Use direct API call for text generation (not JSON)
        try:
            from anthropic import Anthropic
            client = Anthropic()
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=800,
                temperature=0.3,
                system="You are creating a section of a trust document summary.",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except:
            # Fallback with basic content
            return f"This section contains information about {section_type.replace('_', ' ')}."
    
    def _get_section_title(self, section_type: str) -> str:
        """Get title for section type"""
        titles = {
            'essential_info': 'Essential Information',
            'how_it_works': 'How the Trust Works',
            'important_provisions': 'Important Provisions',
            'distributions': 'Distribution Summary'
        }
        return titles.get(section_type, section_type.replace('_', ' ').title())
    
    def generate_from_chunks(self, chunks: List[DocumentChunk], 
                           pdf_path: str) -> Dict:
        """
        Generate summary from document chunks (for large documents)
        
        Args:
            chunks: Document chunks from smart chunker
            pdf_path: Path to original PDF
        
        Returns:
            Complete summary with citations
        """
        all_facts = []
        
        # Extract facts from each chunk
        extractor = SemanticFactExtractor()
        for chunk in chunks:
            chunk_facts = extractor.extract_facts(
                chunk.text, 
                chunk.start_page,
                chunk.start_char
            )
            all_facts.extend(chunk_facts)
        
        # Deduplicate facts
        all_facts = extractor.deduplicate_facts(all_facts)
        all_facts = extractor.rank_facts_by_importance(all_facts)
        
        # Generate summary using all facts
        return self.generate_summary(pdf_path, all_facts)


def generate_rag_summary(pdf_path: str, output_path: str = None) -> Dict:
    """
    Convenience function to generate RAG summary
    
    Args:
        pdf_path: Path to PDF document
        output_path: Optional output path for JSON
    
    Returns:
        Summary dictionary
    """
    generator = RAGSummaryGenerator()
    summary = generator.generate_summary(pdf_path)
    
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"✓ Summary saved to: {output_path}")
    
    return summary


if __name__ == "__main__":
    import sys
    
    # Test 1: Small document (2006 Eric Russell ILIT)
    print("="*60)
    print("Test 1: Small Document (2006 Eric Russell ILIT)")
    print("="*60)
    
    test1_path = "data/2006 Eric Russell ILIT.pdf"
    test1_output = "results/test_rag_2006_eric.json"
    
    summary1 = generate_rag_summary(test1_path, test1_output)
    
    print(f"\n✓ Generated summary with {len(summary1['citations'])} citations")
    print(f"✓ Executive summary: {summary1['summary']['executive'][:100]}...")
    print(f"✓ Sections: {len(summary1['summary']['sections'])}")
    
    # Test 2: Different document (1998 Eric Russell Family Trust)
    print("\n" + "="*60)
    print("Test 2: Different Document (1998 Eric Russell Family Trust)")
    print("="*60)
    
    test2_path = "data/1998 Eric Russell Family Trust Agreement.pdf"
    test2_output = "results/test_rag_1998_eric.json"
    
    summary2 = generate_rag_summary(test2_path, test2_output)
    
    print(f"\n✓ Generated summary with {len(summary2['citations'])} citations")
    print(f"✓ Executive summary: {summary2['summary']['executive'][:100]}...")
    print(f"✓ Sections: {len(summary2['summary']['sections'])}")
    
    # Validate citations are referenced
    for section in summary1['summary']['sections']:
        content = section.get('content', '')
        cite_refs = content.count('{{cite:')
        print(f"  - {section['title']}: {cite_refs} citation references")