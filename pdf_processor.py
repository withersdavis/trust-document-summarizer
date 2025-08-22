import pdfplumber
from typing import List, Dict, Tuple
from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image
import pytesseract
import io

from ocr_cache_manager import OCRCacheManager

class PDFProcessor:
    def __init__(self, use_cache: bool = True):
        self.pages_content = []
        self.full_text = ""
        self.use_cache = use_cache
        self.cache_manager = OCRCacheManager() if use_cache else None
        
    def extract_text_from_pdf(self, pdf_path: str) -> Tuple[str, List[Dict]]:
        """
        Extract text from PDF file with page tracking.
        Handles both text-based and scanned (image-based) PDFs using OCR.
        Returns: (full_text, pages_content)
        """
        # Check cache first
        if self.use_cache and self.cache_manager:
            if self.cache_manager.has_cached_ocr(pdf_path):
                cached_result = self.cache_manager.get_cached_ocr(pdf_path)
                if cached_result:
                    self.full_text, self.pages_content = cached_result
                    return self.full_text, self.pages_content
        
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
                    # Cache the results
                    if self.use_cache and self.cache_manager:
                        self.cache_manager.save_ocr_results(pdf_path, self.full_text, self.pages_content)
                    return self.full_text, self.pages_content
                
        except Exception as e:
            print(f"Error with pdfplumber: {e}")
        
        # If no text found, use OCR
        print("No text found in PDF. Using OCR to extract text from images...")
        return self._extract_text_with_ocr(pdf_path)
    
    def _extract_text_with_ocr(self, pdf_path: str) -> Tuple[str, List[Dict]]:
        """
        Extract text from PDF using OCR (Tesseract).
        This handles scanned PDFs by converting pages to images and running OCR.
        """
        pages_content = []
        full_text_parts = []
        
        try:
            # Use pypdfium2 to render pages as images
            pdf = pdfium.PdfDocument(pdf_path)
            total_pages = len(pdf)
            
            for i, page in enumerate(pdf, 1):
                print(f"Processing page {i}/{total_pages} with OCR...")
                
                # Render page as high-resolution image for better OCR accuracy
                # Using scale=3.0 for 300 DPI equivalent
                bitmap = page.render(scale=3.0)
                pil_image = bitmap.to_pil()
                
                # Run OCR using Tesseract
                try:
                    # Configure Tesseract for better accuracy
                    custom_config = r'--oem 3 --psm 6'
                    text = pytesseract.image_to_string(pil_image, config=custom_config)
                    
                    if text and text.strip():
                        pages_content.append({
                            'page_number': i,
                            'text': text,
                            'extraction_method': 'OCR'
                        })
                        full_text_parts.append(f"[Page {i}]\n{text}\n")
                    else:
                        # If OCR returns nothing, add a placeholder
                        placeholder = f"[Page {i} - No text could be extracted]"
                        pages_content.append({
                            'page_number': i,
                            'text': placeholder,
                            'extraction_method': 'OCR_FAILED'
                        })
                        full_text_parts.append(f"[Page {i}]\n{placeholder}\n")
                        
                except Exception as ocr_error:
                    print(f"OCR error on page {i}: {ocr_error}")
                    error_text = f"[Page {i} - OCR failed: {str(ocr_error)}]"
                    pages_content.append({
                        'page_number': i,
                        'text': error_text,
                        'extraction_method': 'OCR_ERROR'
                    })
                    full_text_parts.append(f"[Page {i}]\n{error_text}\n")
            
            self.pages_content = pages_content
            self.full_text = "\n".join(full_text_parts)
            
            # Cache the OCR results
            if self.use_cache and self.cache_manager and self.full_text:
                self.cache_manager.save_ocr_results(pdf_path, self.full_text, self.pages_content)
            
            # Check if we got any meaningful text
            total_text_length = sum(len(p.get('text', '')) for p in pages_content 
                                   if p.get('extraction_method') == 'OCR')
            
            if total_text_length > 100:  # Arbitrary threshold for "meaningful" text
                print(f"Successfully extracted {total_text_length} characters from {total_pages} pages using OCR")
            else:
                print(f"Warning: Very little text extracted ({total_text_length} characters). The document may be empty or the scan quality may be poor.")
            
            return self.full_text, self.pages_content
                
        except Exception as e:
            raise Exception(f"Error processing PDF with OCR: {str(e)}")
    
    def get_page_count(self) -> int:
        """Get total number of pages"""
        return len(self.pages_content)
    
    def get_text_by_page(self, page_number: int) -> str:
        """Get text from specific page"""
        for page in self.pages_content:
            if page['page_number'] == page_number:
                return page['text']
        return ""
    
    def get_extraction_summary(self) -> Dict:
        """Get summary of extraction methods used"""
        summary = {
            'total_pages': len(self.pages_content),
            'text_pages': 0,
            'ocr_pages': 0,
            'failed_pages': 0,
            'total_characters': 0
        }
        
        for page in self.pages_content:
            method = page.get('extraction_method', 'text')
            text_length = len(page.get('text', ''))
            
            if method == 'OCR':
                summary['ocr_pages'] += 1
                summary['total_characters'] += text_length
            elif method in ['OCR_FAILED', 'OCR_ERROR']:
                summary['failed_pages'] += 1
            else:
                summary['text_pages'] += 1
                summary['total_characters'] += text_length
        
        return summary