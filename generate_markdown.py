#!/usr/bin/env python3
"""Generate markdown from existing JSON summary"""

import json
import sys
from pathlib import Path
from markdown_generator import MarkdownGenerator

json_file = sys.argv[1] if len(sys.argv) > 1 else "results/2006_Eric_Russell_ILIT_summary.json"

# Load JSON
with open(json_file, 'r') as f:
    data = json.load(f)

# Generate markdown
generator = MarkdownGenerator()
base_path = Path(json_file).with_suffix('')

# Save both versions
with_citations, clean = generator.save_both_versions(data, str(base_path))

print(f"✓ Generated markdown files:")
print(f"  - With citations: {with_citations}")
print(f"  - Clean version: {clean}")