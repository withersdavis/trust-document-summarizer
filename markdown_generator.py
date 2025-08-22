import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

class MarkdownGenerator:
    def __init__(self):
        self.citations_map = {}
        
    def json_to_markdown(self, json_data: Dict, include_citations: bool = True) -> str:
        """
        Convert JSON trust summary to readable markdown format
        
        Args:
            json_data: The JSON summary dictionary
            include_citations: Whether to include citation references in the text
        
        Returns:
            Formatted markdown string
        """
        self.citations_map = json_data.get('citations', {})
        md_lines = []
        
        # Add title and metadata
        md_lines.extend(self._generate_header(json_data))
        
        # Add executive summary (handle both structures)
        if 'summary' in json_data and 'executive' in json_data['summary']:
            md_lines.extend(self._generate_executive_summary(json_data['summary']['executive'], include_citations))
        elif 'executive' in json_data:
            md_lines.extend(self._generate_executive_summary(json_data['executive'], include_citations))
        
        # Add main sections (handle both structures)
        if 'summary' in json_data and 'sections' in json_data['summary']:
            for section in json_data['summary']['sections']:
                md_lines.extend(self._generate_section(section, include_citations))
        else:
            # Handle alternative structure - convert other keys to sections
            for key in ['essential_info', 'how_it_works', 'important_provisions', 'distributions']:
                if key in json_data:
                    section = {
                        'title': key.replace('_', ' ').title(),
                        'content': self._format_json_as_markdown(json_data[key])
                    }
                    md_lines.extend(self._generate_section(section, include_citations))
        
        # Add citations appendix if requested
        if include_citations and self.citations_map:
            md_lines.extend(self._generate_citations_appendix())
        
        # Add document metadata footer
        md_lines.extend(self._generate_footer(json_data))
        
        return '\n'.join(md_lines)
    
    def _generate_header(self, json_data: Dict) -> List[str]:
        """Generate document header with metadata"""
        lines = []
        meta = json_data.get('meta', {})
        
        # Main title
        trust_name = meta.get('trust_name', 'Trust Document Summary')
        lines.append(f"# {trust_name}")
        lines.append("")
        
        # Document info box
        lines.append("## Document Information")
        lines.append("")
        lines.append("| Field | Value |")
        lines.append("|-------|-------|")
        
        if meta.get('source_document'):
            lines.append(f"| **Source Document** | {meta['source_document']} |")
        if meta.get('page_count'):
            lines.append(f"| **Total Pages** | {meta['page_count']} |")
        if meta.get('created_date'):
            lines.append(f"| **Summary Created** | {meta['created_date']} |")
        if meta.get('processed_date'):
            date_str = meta['processed_date']
            try:
                dt = datetime.fromisoformat(date_str)
                formatted_date = dt.strftime("%B %d, %Y at %I:%M %p")
                lines.append(f"| **Processed** | {formatted_date} |")
            except:
                lines.append(f"| **Processed** | {date_str} |")
        
        lines.append("")
        lines.append("---")
        lines.append("")
        
        return lines
    
    def _generate_executive_summary(self, executive_text: str, include_citations: bool) -> List[str]:
        """Generate executive summary section"""
        lines = []
        lines.append("## Executive Summary")
        lines.append("")
        
        # Process the text to handle citations
        processed_text = self._process_citations_in_text(executive_text, include_citations)
        
        # Split into paragraphs and add
        paragraphs = processed_text.split('\n\n')
        for para in paragraphs:
            if para.strip():
                lines.append(para.strip())
                lines.append("")
        
        lines.append("---")
        lines.append("")
        
        return lines
    
    def _generate_section(self, section: Dict, include_citations: bool) -> List[str]:
        """Generate a content section"""
        lines = []
        
        # Section title
        title = section.get('title', 'Section')
        
        # Don't duplicate "Essential Information" or other headers if they're in the content
        content = section.get('content', '')
        
        # Check if content already has markdown headers
        if not content.strip().startswith('#'):
            lines.append(f"## {title}")
            lines.append("")
        
        # Process the content
        processed_content = self._process_citations_in_text(content, include_citations)
        
        # Handle markdown content (tables, lists, code blocks)
        lines.extend(self._format_markdown_content(processed_content))
        lines.append("")
        lines.append("---")
        lines.append("")
        
        return lines
    
    def _format_json_as_markdown(self, data) -> str:
        """Convert JSON data to markdown format"""
        if isinstance(data, dict):
            lines = []
            for key, value in data.items():
                formatted_key = key.replace('_', ' ').title()
                if isinstance(value, (list, dict)):
                    lines.append(f"**{formatted_key}:**")
                    lines.append(self._format_json_as_markdown(value))
                else:
                    lines.append(f"**{formatted_key}:** {value}")
            return '\n'.join(lines)
        elif isinstance(data, list):
            return '\n'.join([f"- {item}" for item in data])
        else:
            return str(data)
    
    def _format_markdown_content(self, content: str) -> List[str]:
        """Format markdown content preserving structure"""
        lines = []
        
        # Split by lines to preserve formatting
        content_lines = content.split('\n')
        
        in_code_block = False
        in_table = False
        
        for line in content_lines:
            # Detect code blocks
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                lines.append(line)
            # Detect tables
            elif '|' in line and not in_code_block:
                in_table = True
                lines.append(line)
            # Regular content
            else:
                if in_table and '|' not in line and line.strip():
                    in_table = False
                lines.append(line)
        
        return lines
    
    def _process_citations_in_text(self, text: str, include_citations: bool) -> str:
        """Process citation markers in text"""
        if not include_citations:
            # Remove all citation markers
            return re.sub(r'\{\{cite:\d+\}\}', '', text).strip()
        
        # Replace citation markers with superscript numbers
        def replace_citation(match):
            cite_id = match.group(1)
            return f"[^{cite_id}]"
        
        return re.sub(r'\{\{cite:(\d+)\}\}', replace_citation, text)
    
    def _generate_citations_appendix(self) -> List[str]:
        """Generate citations appendix"""
        lines = []
        lines.append("## Citations")
        lines.append("")
        lines.append("*All citations reference specific locations in the source document.*")
        lines.append("")
        
        # Sort citations by ID
        sorted_citations = sorted(self.citations_map.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0)
        
        for cite_id, citation in sorted_citations:
            # Handle both nested and direct citation formats
            if 'sources' in citation:
                # Original nested format
                sources = citation.get('sources', [])
                if sources:
                    source = sources[0]
                    page_ref = self._format_page_reference(source.get('page'))
                    exact_text = source.get('exact_text', '')
            else:
                # Direct format (from simplified LLM response)
                page_ref = self._format_page_reference(citation.get('page'))
                exact_text = citation.get('text', '')
            
            # Build citation entry
            cite_parts = []
            if page_ref:
                cite_parts.append(f"Page {page_ref}")
            
            # Add the citation type if available
            if 'type' in citation:
                cite_type = citation['type'].replace('_', ' ').title()
                cite_parts.append(f"({cite_type})")
            
            # Add exact text
            if exact_text:
                # Clean up the text and limit length
                clean_text = exact_text.strip().replace('\n', ' ')
                if len(clean_text) > 150:
                    clean_text = clean_text[:150] + "..."
                cite_parts.append(f'"{clean_text}"')
            
            # Format the citation line
            lines.append(f"[^{cite_id}]: " + ' - '.join(cite_parts))
            lines.append("")
        
        lines.append("---")
        lines.append("")
        
        return lines
    
    def _format_page_reference(self, page_data) -> str:
        """Format page reference from various formats"""
        if isinstance(page_data, int):
            return str(page_data)
        elif isinstance(page_data, list):
            if len(page_data) == 1:
                return str(page_data[0])
            elif len(page_data) == 2:
                return f"{page_data[0]}-{page_data[1]}"
            else:
                return f"{page_data[0]}-{page_data[-1]}"
        elif isinstance(page_data, dict):
            start = page_data.get('start', '')
            end = page_data.get('end', '')
            if start and end:
                return f"{start}-{end}"
            return str(start or end)
        return ""
    
    def _generate_footer(self, json_data: Dict) -> List[str]:
        """Generate document footer"""
        lines = []
        lines.append("---")
        lines.append("")
        lines.append("*This summary was generated automatically from the source trust document. ")
        lines.append("Please consult the original document and legal counsel for authoritative information.*")
        lines.append("")
        
        return lines
    
    def save_markdown(self, json_data: Dict, output_path: str, include_citations: bool = True):
        """
        Convert JSON to markdown and save to file
        
        Args:
            json_data: The JSON summary dictionary
            output_path: Path to save the markdown file
            include_citations: Whether to include citations
        """
        markdown_content = self.json_to_markdown(json_data, include_citations)
        
        # Ensure directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
    
    def save_both_versions(self, json_data: Dict, base_output_path: str):
        """
        Save both citation and no-citation versions
        
        Args:
            json_data: The JSON summary dictionary
            base_output_path: Base path for output (e.g., 'results/trust_summary')
        """
        base_path = Path(base_output_path)
        
        # Save version with citations
        with_citations_path = base_path.with_suffix('.md')
        self.save_markdown(json_data, str(with_citations_path), include_citations=True)
        
        # Save clean version without citations
        clean_path = base_path.parent / f"{base_path.stem}_clean.md"
        self.save_markdown(json_data, str(clean_path), include_citations=False)
        
        return str(with_citations_path), str(clean_path)