#!/usr/bin/env python3
"""
Trust Document Summarization Tool

Process trust documents and generate structured JSON summaries using LLM analysis.
"""

import argparse
import sys
import os
import json
from pathlib import Path
from datetime import datetime

from trust_processor import TrustDocumentProcessor
from markdown_generator import MarkdownGenerator

def main():
    parser = argparse.ArgumentParser(description='Process trust documents and generate structured summaries')
    parser.add_argument('pdf_file', nargs='?', help='Path to the PDF trust document')
    parser.add_argument('-o', '--output', help='Output JSON file path (default: results/<filename>_summary.json)')
    parser.add_argument('-p', '--provider', choices=['anthropic', 'openai'], 
                       help='LLM provider to use (default: from .env file)')
    parser.add_argument('--all', action='store_true', help='Process all PDFs in data folder')
    parser.add_argument('--markdown', action='store_true', help='Also generate markdown output')
    parser.add_argument('--no-citations', action='store_true', help='Generate markdown without citation markers')
    
    args = parser.parse_args()
    
    # Check if .env file exists
    if not Path('.env').exists() and not Path('.env.example').exists():
        print("Error: No .env file found. Please create one based on .env.example")
        print("Copy .env.example to .env and add your API key")
        sys.exit(1)
    
    # Initialize processor
    try:
        processor = TrustDocumentProcessor(llm_provider=args.provider)
    except Exception as e:
        print(f"Error initializing processor: {e}")
        print("\nPlease ensure:")
        print("1. You have created a .env file with your API key")
        print("2. The API key is valid")
        print("3. You have selected the correct provider (anthropic or openai)")
        sys.exit(1)
    
    # Process all PDFs if --all flag is set
    if args.all:
        data_folder = Path('data')
        pdf_files = list(data_folder.glob('*.pdf'))
        
        if not pdf_files:
            print("No PDF files found in data folder")
            sys.exit(1)
        
        print(f"Found {len(pdf_files)} PDF files to process")
        
        for pdf_file in pdf_files:
            output_name = pdf_file.stem.replace(' ', '_') + '_summary.json'
            output_path = Path('results') / output_name
            
            try:
                print(f"\n{'='*60}")
                print(f"Processing: {pdf_file.name}")
                print(f"{'='*60}")
                
                result = processor.process_trust_document(
                    str(pdf_file),
                    str(output_path)
                )
                
                if processor.validate_output(result):
                    print(f"✓ Successfully processed: {pdf_file.name}")
                    
                    # Generate markdown if requested
                    if args.markdown:
                        md_generator = MarkdownGenerator()
                        md_path = output_path.with_suffix('.md')
                        md_generator.save_markdown(result, str(md_path), 
                                                 include_citations=not args.no_citations)
                        print(f"✓ Markdown saved to: {md_path}")
                else:
                    print(f"⚠ Warning: Output validation failed for {pdf_file.name}")
                    
            except Exception as e:
                print(f"✗ Error processing {pdf_file.name}: {e}")
                continue
    
    # Process single file
    else:
        # Default to 2006 ILIT if no file specified
        if not args.pdf_file:
            pdf_path = 'data/2006 Eric Russell ILIT.pdf'
            print(f"No file specified. Processing default: {pdf_path}")
        else:
            pdf_path = args.pdf_file
        
        # Check if file exists
        if not Path(pdf_path).exists():
            print(f"Error: File not found: {pdf_path}")
            sys.exit(1)
        
        # Determine output path
        if args.output:
            output_path = args.output
        else:
            pdf_name = Path(pdf_path).stem.replace(' ', '_')
            output_path = f"results/{pdf_name}_summary.json"
        
        # Process the document
        try:
            print(f"{'='*60}")
            print(f"Trust Document Summarization")
            print(f"{'='*60}")
            print(f"Input: {pdf_path}")
            print(f"Output: {output_path}")
            print(f"LLM Provider: {processor.llm_client.provider}")
            print(f"{'='*60}\n")
            
            result = processor.process_trust_document(pdf_path, output_path)
            
            # Validate output
            if processor.validate_output(result):
                print(f"\n{'='*60}")
                print("✓ Processing complete!")
                print(f"Summary saved to: {output_path}")
                
                # Generate markdown if requested
                if args.markdown:
                    md_generator = MarkdownGenerator()
                    base_path = Path(output_path).with_suffix('')
                    
                    # Save both versions (with and without citations)
                    with_citations_path, clean_path = md_generator.save_both_versions(
                        result, str(base_path)
                    )
                    print(f"✓ Markdown saved to: {with_citations_path}")
                    print(f"✓ Clean markdown saved to: {clean_path}")
                
                # Print summary statistics
                if 'citations' in result:
                    print(f"Citations created: {len(result['citations'])}")
                if 'summary' in result and 'sections' in result['summary']:
                    print(f"Sections created: {len(result['summary']['sections'])}")
                print(f"{'='*60}")
            else:
                print("\n⚠ Warning: Output validation failed. Please review the output.")
                
        except Exception as e:
            print(f"\n✗ Error processing document: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()