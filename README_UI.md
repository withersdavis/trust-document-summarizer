# Trust Document Summarizer UI

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the Streamlit app:
```bash
streamlit run app_ui.py
```

## Features

### Document List Tab
- Upload new PDF documents
- View all documents in database
- Process documents with multi-pass summarization
- Scan and add documents from data folder
- View OCR cache statistics

### Results List Tab
- View all processing results
- Filter by processing type
- View detailed summaries and citations
- Track processing statistics

## Database

The app uses SQLite to track:
- Documents (file info, hash, dates)
- OCR cache entries
- Processing results with metadata

## OCR Caching

OCR results are automatically cached to avoid re-processing:
- Cache stored in `ocr_cache/` folder
- Uses SHA256 file hashing
- Automatically detects file changes

## API Keys

Set environment variables:
- `ANTHROPIC_API_KEY` for Claude
- `OPENAI_API_KEY` for GPT-4