"""
Simple UI for Trust Document Summarizer
Two tabs: Document List and Results List
"""

import streamlit as st
import os
from pathlib import Path
from datetime import datetime
import json
from document_database import DocumentDatabase
from pdf_processor import PDFProcessor
from multi_pass_processor import MultiPassTrustProcessor, process_trust_multipass
from chunked_processor import ChunkedDocumentProcessor, process_large_document
from rag_processor import RAGTrustProcessor, process_trust_rag
from ocr_cache_manager import OCRCacheManager

# Page config
st.set_page_config(
    page_title="Trust Document Summarizer",
    page_icon="📄",
    layout="wide"
)

# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = DocumentDatabase()

if 'cache_manager' not in st.session_state:
    st.session_state.cache_manager = OCRCacheManager()

# Title
st.title("📄 Trust Document Summarizer")

# Create tabs
tab1, tab2 = st.tabs(["📁 Document List", "📊 Results List"])

# Tab 1: Document List
with tab1:
    st.header("Document Management")
    
    # File upload section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Upload a trust document (PDF)",
            type=['pdf'],
            help="Upload a PDF trust document for processing"
        )
        
        if uploaded_file is not None:
            # Save uploaded file temporarily
            temp_dir = Path("temp_uploads")
            temp_dir.mkdir(exist_ok=True)
            temp_path = temp_dir / uploaded_file.name
            
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            if st.button("Add to Database", type="primary"):
                doc_id = st.session_state.db.add_document(str(temp_path))
                st.success(f"✅ Document added to database (ID: {doc_id})")
                st.rerun()
    
    with col2:
        # OCR Cache Stats
        cache_stats = st.session_state.cache_manager.get_cache_stats()
        st.metric("Cached Documents", cache_stats['total_documents'])
        st.metric("Total Pages Cached", cache_stats['total_pages'])
        st.metric("Cache Size", f"{cache_stats['cache_size_mb']:.1f} MB")
    
    st.divider()
    
    # Document list
    st.subheader("📚 Documents in Database")
    
    documents = st.session_state.db.get_all_documents()
    
    if documents:
        for doc in documents:
            with st.expander(f"📄 {doc['file_name']}", expanded=False):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**ID:** {doc['id']}")
                    st.write(f"**Path:** {doc['file_path']}")
                    st.write(f"**Size:** {doc['file_size']:,} bytes")
                
                with col2:
                    st.write(f"**Pages:** {doc['page_count'] or 'Unknown'}")
                    st.write(f"**Added:** {doc['added_date'][:10] if doc['added_date'] else 'Unknown'}")
                    st.write(f"**OCR Runs:** {doc['ocr_count']}")
                
                with col3:
                    st.write(f"**Results:** {doc['result_count']}")
                    
                    # Recommend processing method based on size
                    file_size_mb = doc['file_size'] / (1024 * 1024) if doc['file_size'] else 0
                    if file_size_mb > 5 or (doc['page_count'] and doc['page_count'] > 50):
                        recommended = "RAG (Semantic)"
                        st.info("💡 Large document - RAG recommended")
                    else:
                        recommended = "RAG (Semantic)"
                        st.info("💡 RAG provides best quality")
                    
                    # Processing options
                    processing_method = st.selectbox(
                        "Processing method",
                        ["RAG (Semantic)", "Multi-pass (Standard)", "Chunked (Large Docs)"],
                        index=0,  # Default to RAG
                        key=f"method_{doc['id']}",
                        help="RAG: Best quality with semantic understanding | Multi-pass: Traditional approach | Chunked: For very large documents"
                    )
                    
                    # Process button
                    if st.button(f"Process Document", key=f"process_{doc['id']}"):
                        with st.spinner("Processing document..."):
                            try:
                                # Check if file exists
                                if not Path(doc['file_path']).exists():
                                    st.error(f"File not found: {doc['file_path']}")
                                else:
                                    # Process the document
                                    output_dir = Path("results")
                                    output_dir.mkdir(exist_ok=True)
                                    
                                    # Generate output path based on method
                                    if "RAG" in processing_method:
                                        # Process using RAG method
                                        result = process_trust_rag(
                                            doc['file_path'], 
                                            str(output_dir)
                                        )
                                        
                                        if result.success:
                                            result_data = result.summary
                                            # Find the generated file (RAG adds timestamp)
                                            pattern = Path(doc['file_path']).stem + "_rag_*.json"
                                            result_files = list(output_dir.glob(pattern))
                                            if result_files:
                                                result_path = result_files[-1]  # Get most recent
                                            else:
                                                result_path = output_dir / (Path(doc['file_path']).stem + "_rag.json")
                                        else:
                                            raise Exception(f"RAG processing failed: {result.error_message}")
                                    elif "Chunked" in processing_method:
                                        result_filename = Path(doc['file_path']).stem + "_chunked.json"
                                        result_path = output_dir / result_filename
                                        
                                        # Process using chunked method
                                        result_data = process_large_document(
                                            doc['file_path'], 
                                            str(result_path)
                                        )
                                    else:
                                        result_filename = Path(doc['file_path']).stem + "_multipass.json"
                                        result_path = output_dir / result_filename
                                        
                                        # Process using multi-pass method
                                        result_data = process_trust_multipass(
                                            doc['file_path'], 
                                            str(result_path)
                                        )
                                    
                                    # Add to database
                                    metadata = {
                                        'citations_count': len(result_data.get('citations', {})),
                                        'placeholders_count': 0,  # RAG and Multi-pass should have 0
                                        'sections_count': len(result_data.get('summary', {}).get('sections', [])),
                                        'status': 'completed',
                                        'processing_method': result_data.get('meta', {}).get('processing_method', 'unknown'),
                                        'facts_extracted': result_data.get('meta', {}).get('total_facts', 0),
                                        'chunks_created': result_data.get('meta', {}).get('chunks', 0)
                                    }
                                    
                                    st.session_state.db.add_processing_result(
                                        doc['id'],
                                        'trust_summary',
                                        str(result_path),
                                        metadata
                                    )
                                    
                                    st.success(f"✅ Processing complete! Results saved to: {result_path}")
                                    st.rerun()
                                    
                            except Exception as e:
                                st.error(f"❌ Processing failed: {str(e)}")
    else:
        st.info("No documents in database. Upload a PDF to get started.")
    
    # Data folder scan
    st.divider()
    st.subheader("📂 Scan Data Folder")
    
    data_folder = Path("/Users/w/Downloads/apps/summarizer/data")
    if data_folder.exists():
        pdf_files = list(data_folder.glob("*.pdf"))
        
        if pdf_files:
            st.write(f"Found {len(pdf_files)} PDF files in data folder:")
            
            for pdf_file in pdf_files:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"• {pdf_file.name}")
                with col2:
                    if st.button(f"Add", key=f"add_{pdf_file.name}"):
                        doc_id = st.session_state.db.add_document(str(pdf_file))
                        st.success(f"Added {pdf_file.name}")
                        st.rerun()
        else:
            st.write("No PDF files found in data folder")
    else:
        st.write("Data folder not found")

# Tab 2: Results List
with tab2:
    st.header("Processing Results")
    
    # Statistics
    stats = st.session_state.db.get_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Documents", stats['total_documents'])
    with col2:
        st.metric("OCR Cached", stats['total_ocr_cached'])
    with col3:
        st.metric("Total Pages", stats['total_pages_processed'])
    with col4:
        st.metric("Characters Extracted", f"{stats['total_chars_extracted']:,}")
    
    st.divider()
    
    # Results list
    st.subheader("📊 All Processing Results")
    
    results = st.session_state.db.get_processing_results()
    
    if results:
        # Filter options
        col1, col2 = st.columns([1, 3])
        with col1:
            filter_type = st.selectbox(
                "Filter by type",
                ["All"] + list(set(r['processing_type'] for r in results))
            )
        
        # Display results
        for result in results:
            if filter_type == "All" or result['processing_type'] == filter_type:
                with st.expander(f"📋 {result['file_name']} - {result['processing_date'][:16]}", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Type:** {result['processing_type']}")
                        st.write(f"**Status:** {result['status']}")
                        st.write(f"**Date:** {result['processing_date']}")
                    
                    with col2:
                        metadata = json.loads(result['metadata']) if result['metadata'] else {}
                        st.write(f"**Citations:** {result['citations_count']}")
                        if metadata.get('facts_extracted'):
                            st.write(f"**Facts Extracted:** {metadata.get('facts_extracted', 0)}")
                        if metadata.get('chunks_created'):
                            st.write(f"**Chunks:** {metadata.get('chunks_created', 0)}")
                        st.write(f"**Sections:** {result['sections_count']}")
                    
                    # View result button
                    if result['result_file'] and Path(result['result_file']).exists():
                        if st.button(f"View Result", key=f"view_{result['id']}"):
                            with open(result['result_file'], 'r') as f:
                                result_data = json.load(f)
                            
                            # Display summary
                            st.markdown("### Executive Summary")
                            st.write(result_data.get('summary', {}).get('executive', 'No summary available'))
                            
                            # Display sections
                            sections = result_data.get('summary', {}).get('sections', [])
                            if sections:
                                st.markdown("### Sections")
                                for section in sections:
                                    st.markdown(f"**{section.get('title', 'Untitled')}**")
                                    st.markdown(section.get('content', ''))
                            
                            # Display citations
                            citations = result_data.get('citations', {})
                            if citations:
                                st.markdown("### Citations")
                                for cite_id, cite_data in citations.items():
                                    st.write(f"**[{cite_id}]** Page {cite_data.get('page', '?')}: {cite_data.get('text', '')}")
                    else:
                        st.warning("Result file not found")
                    
                    # Error message if any
                    if result.get('error_message'):
                        st.error(f"Error: {result['error_message']}")
    else:
        st.info("No processing results yet. Process a document from the Document List tab.")
    
    # Processing type breakdown
    if stats.get('processing_types'):
        st.divider()
        st.subheader("📈 Processing Statistics")
        
        for ptype in stats['processing_types']:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(f"{ptype['processing_type']} Runs", ptype['count'])
            with col2:
                st.metric("Avg Citations", f"{ptype['avg_citations']:.1f}" if ptype['avg_citations'] else "0")
            with col3:
                st.metric("Avg Placeholders", f"{ptype['avg_placeholders']:.1f}" if ptype['avg_placeholders'] else "0")

# Sidebar
with st.sidebar:
    st.header("🔧 Tools")
    
    if st.button("Clear OCR Cache", type="secondary"):
        st.session_state.cache_manager.clear_cache()
        st.success("OCR cache cleared")
    
    if st.button("Refresh Database", type="secondary"):
        st.session_state.db = DocumentDatabase()
        st.success("Database refreshed")
        st.rerun()
    
    st.divider()
    
    # Display API key status
    st.subheader("API Configuration")
    
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if anthropic_key:
        st.success("✅ Anthropic API Key Set")
    else:
        st.warning("⚠️ No Anthropic API Key")
    
    if openai_key:
        st.success("✅ OpenAI API Key Set")
    else:
        st.warning("⚠️ No OpenAI API Key")
    
    st.divider()
    st.caption("Trust Document Summarizer v1.0")