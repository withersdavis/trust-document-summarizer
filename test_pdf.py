import pdfplumber
from pathlib import Path

pdf_path = "data/2006 Eric Russell ILIT.pdf"

# Check if file exists
if Path(pdf_path).exists():
    print(f"File exists: {pdf_path}")
    print(f"File size: {Path(pdf_path).stat().st_size} bytes")
else:
    print(f"File not found: {pdf_path}")
    
# Try to open and read the PDF
try:
    with pdfplumber.open(pdf_path) as pdf:
        print(f"Number of pages: {len(pdf.pages)}")
        
        # Try to extract text from first page
        if pdf.pages:
            page1 = pdf.pages[0]
            text = page1.extract_text()
            if text:
                print(f"First page text (first 500 chars):\n{text[:500]}")
            else:
                print("No text extracted from first page")
                
                # Try alternative extraction methods
                print("\nTrying extract_text_simple:")
                text_simple = page1.extract_text_simple()
                if text_simple:
                    print(f"Simple text (first 500 chars):\n{text_simple[:500]}")
                else:
                    print("No text from simple extraction either")
        else:
            print("No pages found in PDF")
            
except Exception as e:
    print(f"Error opening PDF: {e}")