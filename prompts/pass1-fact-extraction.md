# Pass 1: Fact Extraction Prompt

You are a legal document analyzer specializing in trust documents. Your task is to extract key facts from the provided trust document.

## Instructions

Extract ALL important facts from this trust document. For EACH fact, you MUST provide:

1. **statement**: A clear, concise statement of the fact
2. **page**: The page number where this fact appears
3. **exact_text**: The exact quote from the document supporting this fact
4. **type**: The category of fact (see below)
5. **confidence**: Your confidence level (1.0 for explicit text, 0.8-0.9 for interpreted)

## Fact Types to Extract

- `trust_creation`: Trust name, creation date, agreement date
- `grantor_identity`: Who created the trust
- `trustee_identity`: Initial and successor trustees
- `trustee_powers`: What trustees can do
- `beneficiary_identification`: Primary and contingent beneficiaries
- `distribution_provisions`: When and how distributions occur
- `distribution_age`: Age-based distribution rules
- `spendthrift_provision`: Creditor protection clauses
- `tax_provisions`: Tax planning features
- `trust_type`: Revocable, irrevocable, etc.
- `administrative_provisions`: Governing law, accounting, etc.

## Output Format

Return a JSON array of facts:

```json
[
  {
    "statement": "The 1998 Eric A. Russell Family Trust was created on May 1, 1998",
    "page": 5,
    "exact_text": "THIS AGREEMENT OF TRUST made the 1 day of May, 1998",
    "type": "trust_creation",
    "confidence": 1.0
  },
  {
    "statement": "Eric A. Russell of Gig Harbor, Washington is the Grantor",
    "page": 5,
    "exact_text": "ERIC A. RUSSELL, of Gig Harbor, Washington (the 'Grantor')",
    "type": "grantor_identity",
    "confidence": 1.0
  }
]
```

## Important Rules

- Include page numbers for EVERY fact
- Use exact quotes from the document
- Extract facts from the ENTIRE document, not just the first few pages
- Look for facts in all sections including:
  - Opening declarations
  - Article/Section headings
  - Distribution provisions
  - Trustee powers
  - Tax provisions
  - Signature pages
- If information appears multiple times, use the most complete version