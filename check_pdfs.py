import pdfplumber
from pathlib import Path

data_dir = Path("data")
pdf_files = list(data_dir.glob("*.pdf"))

print("Checking all PDF files for text content:\n")

for pdf_file in pdf_files:
    try:
        with pdfplumber.open(pdf_file) as pdf:
            has_text = False
            total_chars = 0
            
            for page in pdf.pages[:3]:  # Check first 3 pages
                text = page.extract_text()
                if text and text.strip():
                    has_text = True
                    total_chars += len(text)
            
            print(f"📄 {pdf_file.name}")
            if has_text:
                print(f"   ✅ Contains text ({total_chars} characters in first 3 pages)")
            else:
                print(f"   ❌ No text found (likely scanned/image-based)")
            print()
            
    except Exception as e:
        print(f"📄 {pdf_file.name}")
        print(f"   ⚠️ Error: {e}")
        print()