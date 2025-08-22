import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from pdf_processor import PDFProcessor
from llm_client import LLMClient

class TrustDocumentProcessor:
    def __init__(self, llm_provider: Optional[str] = None):
        self.pdf_processor = PDFProcessor()
        self.llm_client = LLMClient(provider=llm_provider)
        self.prompt_template = self._load_prompt_template()
        
    def _load_prompt_template(self) -> str:
        """Load the trust summary prompt template"""
        prompt_path = Path("prompts/trust-summary-prompt.md")
        if prompt_path.exists():
            with open(prompt_path, 'r') as f:
                return f.read()
        else:
            raise FileNotFoundError(f"Prompt template not found at {prompt_path}")
    
    def process_trust_document(self, pdf_path: str, output_path: Optional[str] = None) -> Dict:
        """
        Process a trust document PDF and generate structured summary
        
        Args:
            pdf_path: Path to the PDF trust document
            output_path: Optional path to save the JSON output
        
        Returns:
            Dictionary containing the structured trust summary
        """
        print(f"Processing: {pdf_path}")
        
        # Extract text from PDF
        print("Extracting text from PDF...")
        full_text, pages_content = self.pdf_processor.extract_text_from_pdf(pdf_path)
        
        if not full_text:
            raise ValueError("No text content extracted from PDF")
        
        page_count = self.pdf_processor.get_page_count()
        print(f"Extracted {page_count} pages of text")
        
        # Prepare system prompt
        system_prompt = f"""You are a legal document analysis expert specializing in trust documents.
Your task is to create a comprehensive, structured summary of the trust document following the exact format and guidelines provided.
You must output valid JSON that matches the structure shown in the examples.

{self.prompt_template}

IMPORTANT: 
- Your response must be valid JSON only
- Follow the exact structure shown in the examples
- Include accurate citations with page numbers
- Use the actual names and terms from the document
- CRITICAL: You MUST create a citation entry in the "citations" section for EVERY {{cite:XXX}} reference you use
- Before returning your response, verify that every {{cite:XXX}} in your text has a corresponding entry in the citations dictionary
- The citations dictionary must have an entry for each unique citation number you reference"""
        
        # Prepare user content
        user_content = f"""Please analyze the following trust document and create a structured summary according to the guidelines provided.

DOCUMENT CONTENT:
{full_text}

Create a comprehensive JSON summary with:
1. Executive summary
2. Essential information (trust identity, key parties)
3. How the trust works (organized logically)
4. Important provisions
5. Distribution summary
6. Complete citations with page numbers

Remember to:
- Use actual names from the document
- Preserve specific numbers and dates
- Translate legal jargon to plain English
- Include citations for every factual statement
- Output valid JSON only

CITATION REQUIREMENTS:
- Every {{cite:001}}, {{cite:002}}, etc. that you reference MUST have a corresponding entry in the "citations" dictionary
- Each citation entry must include: page number, the exact text from the document, and the citation type
- Do NOT reference a citation number without creating its entry in the citations section
- Example: If you write {{cite:013}}, you MUST include citation "013" in the citations dictionary"""
        
        # Process with LLM
        print(f"Processing with {self.llm_client.provider.upper()} LLM...")
        try:
            result = self.llm_client.process_document(system_prompt, user_content)
        except Exception as e:
            print(f"Error during LLM processing: {e}")
            raise
        
        # Validate citations are complete
        result = self._validate_and_fix_citations(result)
        
        # Add metadata
        result['meta'] = result.get('meta', {})
        result['meta'].update({
            'source_document': os.path.basename(pdf_path),
            'page_count': page_count,
            'processed_date': datetime.now().isoformat(),
            'llm_provider': self.llm_client.provider,
            'llm_model': self.llm_client.model
        })
        
        # Save output if path provided
        if output_path:
            self._save_output(result, output_path)
            print(f"Summary saved to: {output_path}")
        
        return result
    
    def _save_output(self, data: Dict, output_path: str):
        """Save the processed output to a JSON file"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _validate_and_fix_citations(self, result: Dict) -> Dict:
        """Validate that all referenced citations exist and add placeholders for missing ones"""
        import re
        
        # Find all citation references in the result
        json_str = json.dumps(result)
        referenced_citations = set(re.findall(r'\{\{cite:(\d+)\}\}', json_str))
        
        # Get existing citations
        existing_citations = set(result.get('citations', {}).keys())
        
        # Find missing citations
        missing_citations = referenced_citations - existing_citations
        
        if missing_citations:
            print(f"Warning: Found {len(missing_citations)} missing citations: {sorted(missing_citations)}")
            print("Adding placeholder citations for missing references...")
            
            # Ensure citations dict exists
            if 'citations' not in result:
                result['citations'] = {}
            
            # Add placeholders for missing citations
            for cite_id in missing_citations:
                result['citations'][cite_id] = {
                    "page": 1,
                    "text": f"[Citation {cite_id} - not provided by LLM, please verify in source document]",
                    "type": "placeholder"
                }
            
            print(f"Added {len(missing_citations)} placeholder citations")
        
        return result
    
    def validate_output(self, result: Dict) -> bool:
        """Basic validation of the output structure"""
        # More flexible validation - check for either structure
        if 'summary' in result:
            # Original expected structure
            required_keys = ['summary', 'citations']
            summary_keys = ['executive', 'sections']
            
            for key in required_keys:
                if key not in result:
                    print(f"Missing required key: {key}")
                    return False
            
            if 'summary' in result:
                for key in summary_keys:
                    if key not in result['summary']:
                        print(f"Missing summary key: {key}")
                        return False
        else:
            # Alternative structure (direct keys)
            if 'executive' in result or 'essential_info' in result:
                return True  # Accept alternative structure
            else:
                print(f"Missing required key: summary")
                return False
        
        return True