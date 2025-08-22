import pdfplumber
from pathlib import Path
import pypdfium2 as pdfium

pdf_path = "data/2006 Eric Russell ILIT.pdf"

print("Testing with pdfplumber:")
try:
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        
        # Check for images
        images = page.images
        print(f"Number of images on page 1: {len(images) if images else 0}")
        
        # Check for chars
        chars = page.chars
        print(f"Number of characters on page 1: {len(chars) if chars else 0}")
        
        # Try different extraction settings
        text = page.extract_text(x_tolerance=3, y_tolerance=3)
        if text:
            print(f"Text with tolerances: {text[:200]}")
        else:
            print("No text even with tolerances")
            
except Exception as e:
    print(f"Error: {e}")

print("\nTesting with pypdfium2:")
try:
    pdf = pdfium.PdfDocument(pdf_path)
    page = pdf[0]
    
    # Try to get text
    textpage = page.get_textpage()
    text = textpage.get_text_bounded()
    
    if text:
        print(f"PyPDFium2 extracted text (first 500 chars):\n{text[:500]}")
    else:
        print("No text extracted with pypdfium2")
        
    # Check if it's likely a scanned PDF
    print(f"\nPage dimensions: {page.get_width()} x {page.get_height()}")
    
except Exception as e:
    print(f"Error with pypdfium2: {e}")