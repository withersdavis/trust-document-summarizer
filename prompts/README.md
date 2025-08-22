# Trust Document Processing Prompts

This folder contains all prompts used for trust document processing.

## Prompt Files

### Core Prompts

- **`trust-summary-prompt.md`** - Main comprehensive prompt for trust document summarization (used in single-pass mode)

### Multi-Pass Prompts

- **`pass1-fact-extraction.md`** - Extract facts with locations from trust documents
- **`pass3-summary-generation.md`** - Generate summary using pre-created citations

## Processing Modes

### Single-Pass Mode
Uses `trust-summary-prompt.md` to do everything in one LLM call:
- Extract facts
- Create citations
- Generate summary

### Multi-Pass Mode
Breaks processing into multiple focused passes:
1. **Pass 1**: Extract facts using `pass1-fact-extraction.md`
2. **Pass 2**: Generate citations programmatically
3. **Pass 3**: Create summary using `pass3-summary-generation.md`
4. **Pass 4**: Validate and cleanup

## Why Multiple Prompts?

- **Focused Tasks**: Each pass has one clear objective
- **Better Accuracy**: Reduces cognitive load on the LLM
- **No Missing Citations**: Citations are created before being referenced
- **Scalability**: Handles large documents better

## Adding New Prompts

When adding new prompts:
1. Use markdown format
2. Include clear instructions
3. Specify expected output format
4. Add examples where helpful
5. Document the prompt's purpose in this README