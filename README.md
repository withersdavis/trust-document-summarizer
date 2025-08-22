# Trust Document Summarizer

An AI-powered system for analyzing and summarizing trust documents with accurate citation tracking.

## Features

- **PDF Processing**: Handles both text-based and scanned PDFs using OCR
- **Multi-pass Processing**: Ensures all citations are created before being referenced
- **Chunked Processing**: Handles large documents (50+ pages) reliably
- **OCR Caching**: Avoids re-processing documents with intelligent caching
- **Database Tracking**: SQLite database tracks all documents and processing results
- **Web UI**: Streamlit interface for easy document management
- **Citation Validation**: Every citation is verified and linked to source text

## Installation

### Prerequisites

- Python 3.9+
- Tesseract OCR (for scanned documents)

#### Install Tesseract

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

**Windows:**
Download installer from: https://github.com/UB-Mannheim/tesseract/wiki

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd trust-document-summarizer
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Set up API keys:
```bash
# Create .env file
cp .env.example .env

# Edit .env and add your API keys:
# ANTHROPIC_API_KEY=your_key_here
# OPENAI_API_KEY=your_key_here
```

## Usage

### Web Interface

Run the Streamlit UI:
```bash
streamlit run app_ui.py
```

Open http://localhost:8501 in your browser.

### Command Line

#### Process with Multi-pass (Standard documents):
```bash
python multi_pass_processor.py "data/document.pdf"
```

#### Process with Chunked method (Large documents):
```bash
python chunked_processor.py "data/large_document.pdf"
```

#### Process all documents:
```bash
python process_trust.py --all --markdown
```

## Project Structure

```
trust-document-summarizer/
├── app_ui.py                 # Streamlit web interface
├── multi_pass_processor.py   # Multi-pass processing for standard documents
├── chunked_processor.py      # Chunked processing for large documents
├── pdf_processor.py          # PDF text extraction and OCR
├── ocr_cache_manager.py      # OCR result caching
├── document_database.py      # SQLite database management
├── llm_client.py            # LLM API client (Anthropic/OpenAI)
├── trust_processor.py       # Original single-pass processor
├── markdown_generator.py     # Convert JSON to readable markdown
├── process_trust.py         # CLI script
├── prompts/                 # LLM prompts
│   ├── trust-summary-prompt.md
│   ├── pass1-fact-extraction.md
│   └── pass3-summary-generation.md
├── data/                    # Input PDF documents (gitignored)
├── results/                 # Processing results (gitignored)
└── ocr_cache/              # Cached OCR results (gitignored)
```

## Processing Methods

### Multi-pass Processing (Standard)
Best for documents under 50 pages:
1. **Pass 1**: Extract facts with page locations
2. **Pass 2**: Generate citations from facts
3. **Pass 3**: Create summary using only existing citations
4. **Pass 4**: Validate and cleanup

### Chunked Processing (Large Documents)
For documents over 50 pages or when standard processing fails:
1. Split document into ~20K character chunks
2. Process each chunk independently
3. Merge results and generate unified summary
4. Validate all citations

## Output Format

The system generates structured JSON with:
- **Executive Summary**: High-level overview with citations
- **Essential Information**: Trust name, parties, dates
- **How the Trust Works**: Administrative structure
- **Important Provisions**: Key terms and restrictions
- **Distribution Summary**: Who receives what and when
- **Citations**: Every fact linked to source text and page number

Example output structure:
```json
{
  "meta": {
    "total_facts_extracted": 25,
    "citations_created": 15,
    "processing_method": "multi_pass",
    "passes_completed": 4
  },
  "summary": {
    "executive": "Trust overview with {{cite:001}} references",
    "sections": [...]
  },
  "citations": {
    "001": {
      "page": 5,
      "text": "Exact quote from document",
      "type": "trust_creation"
    }
  }
}
```

## Database Schema

### Documents Table
- File information, hash, dates
- Page count and document type

### OCR Cache Table
- Links to cached OCR results
- Processing time and character count

### Processing Results Table
- All processing attempts with metadata
- Citation and section counts
- Processing method used

## API Configuration

The system supports:
- **Anthropic Claude** (recommended): Better at structured output
- **OpenAI GPT-4**: Alternative LLM option

Set your preferred provider in `.env`:
```
LLM_PROVIDER=anthropic  # or openai
ANTHROPIC_API_KEY=your_key
OPENAI_API_KEY=your_key
```

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Processing a New Document Type
1. Place PDF in `data/` folder
2. Run through UI or CLI
3. Check results in `results/` folder
4. Verify citations in generated JSON

## Troubleshooting

### OCR Issues
- Ensure Tesseract is installed: `tesseract --version`
- Check OCR cache: `ls ocr_cache/`
- Clear cache if needed: Delete `ocr_cache/*.json`

### Processing Errors
- Check API keys in `.env`
- For large documents, use chunked processing
- Review error logs in UI or console output

## Future Enhancements (Planned)

- **RAG Implementation**: Semantic search across documents
- **Vector Database**: Better handling of large document sets
- **Entity Recognition**: Automatic identification of parties
- **Document Comparison**: Compare multiple trust versions
- **Batch Processing**: Process multiple documents in parallel

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request