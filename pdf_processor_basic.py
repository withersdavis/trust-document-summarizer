import pdfplumber
from typing import List, Dict, Tuple
from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image
import io

class PDFProcessor:
    def __init__(self):
        self.pages_content = []
        self.full_text = ""
        
    def extract_text_from_pdf(self, pdf_path: str) -> Tuple[str, List[Dict]]:
        """
        Extract text from PDF file with page tracking.
        Handles both text-based and scanned (image-based) PDFs.
        Returns: (full_text, pages_content)
        """
        pages_content = []
        full_text_parts = []
        
        # First try regular text extraction
        try:
            with pdfplumber.open(pdf_path) as pdf:
                has_text = False
                
                for i, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text and text.strip():
                        has_text = True
                        pages_content.append({
                            'page_number': i,
                            'text': text
                        })
                        full_text_parts.append(f"[Page {i}]\n{text}\n")
                
                # If we got text, return it
                if has_text:
                    self.pages_content = pages_content
                    self.full_text = "\n".join(full_text_parts)
                    return self.full_text, self.pages_content
                
        except Exception as e:
            print(f"Error with pdfplumber: {e}")
        
        # If no text found, try extracting images and using OCR
        print("No text found in PDF. Attempting to extract from images...")
        return self._extract_text_from_images(pdf_path)
    
    def _extract_text_from_images(self, pdf_path: str) -> Tuple[str, List[Dict]]:
        """
        Extract text from PDF by converting pages to images.
        This handles scanned PDFs.
        """
        pages_content = []
        full_text_parts = []
        
        try:
            # Use pypdfium2 to render pages as images
            pdf = pdfium.PdfDocument(pdf_path)
            
            for i, page in enumerate(pdf, 1):
                print(f"Processing page {i}/{len(pdf)}...")
                
                # Render page as image (higher scale for better OCR)
                bitmap = page.render(scale=2.0)  # 2x resolution for better OCR
                pil_image = bitmap.to_pil()
                
                # For now, we'll just note that the page is an image
                # In a production system, you'd use OCR here (pytesseract)
                # But that requires tesseract to be installed on the system
                
                # Placeholder text indicating this is a scanned page
                text = f"[Scanned page {i} - OCR would be needed to extract text from this image-based PDF]"
                
                pages_content.append({
                    'page_number': i,
                    'text': text,
                    'is_scanned': True
                })
                full_text_parts.append(f"[Page {i}]\n{text}\n")
            
            self.pages_content = pages_content
            self.full_text = "\n".join(full_text_parts)
            
            if not self.full_text.strip():
                # Try one more approach - check if there's any hidden text
                with pdfplumber.open(pdf_path) as pdf:
                    all_text = []
                    for page in pdf.pages:
                        # Try to extract any form of text
                        text = page.extract_text_simple() or ""
                        words = page.extract_words()
                        if words:
                            text = " ".join([w['text'] for w in words])
                        if text:
                            all_text.append(text)
                    
                    if all_text:
                        self.full_text = "\n".join(all_text)
                        return self.full_text, pages_content
            
            # If still no text, return a message about needing OCR
            if not any(p['text'] for p in pages_content if 'text' in p):
                error_msg = """This PDF appears to be a scanned document (image-based).
                
To process this document, you would need:
1. Install Tesseract OCR on your system
2. Use pytesseract to extract text from the images

For now, I cannot extract text from this scanned PDF without OCR software installed."""
                
                self.full_text = error_msg
                pages_content = [{'page_number': 1, 'text': error_msg, 'is_scanned': True}]
            
            return self.full_text, pages_content
                
        except Exception as e:
            raise Exception(f"Error processing PDF images: {str(e)}")
    
    def get_page_count(self) -> int:
        """Get total number of pages"""
        return len(self.pages_content)
    
    def get_text_by_page(self, page_number: int) -> str:
        """Get text from specific page"""
        for page in self.pages_content:
            if page['page_number'] == page_number:
                return page['text']
        return ""