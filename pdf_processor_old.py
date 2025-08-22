import pdfplumber
from typing import List, Dict, Tuple

class PDFProcessor:
    def __init__(self):
        self.pages_content = []
        self.full_text = ""
        
    def extract_text_from_pdf(self, pdf_path: str) -> Tuple[str, List[Dict]]:
        """
        Extract text from PDF file with page tracking
        Returns: (full_text, pages_content)
        """
        pages_content = []
        full_text_parts = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text:
                        pages_content.append({
                            'page_number': i,
                            'text': text
                        })
                        full_text_parts.append(f"[Page {i}]\n{text}\n")
                
                self.pages_content = pages_content
                self.full_text = "\n".join(full_text_parts)
                
                return self.full_text, self.pages_content
                
        except Exception as e:
            raise Exception(f"Error processing PDF: {str(e)}")
    
    def get_page_count(self) -> int:
        """Get total number of pages"""
        return len(self.pages_content)
    
    def get_text_by_page(self, page_number: int) -> str:
        """Get text from specific page"""
        for page in self.pages_content:
            if page['page_number'] == page_number:
                return page['text']
        return ""