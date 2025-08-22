# Pass 3: Summary Generation with Citations

You are creating a comprehensive trust document summary. You MUST use ONLY the citations provided to you.

## Available Citations

You will be given a list of facts with their assigned citation IDs. You may ONLY use these citations.

## Required Output Structure

Generate a JSON summary following this EXACT structure:

```json
{
  "meta": {
    "trust_name": "Official trust name {{cite:XXX}}",
    "document_type": "trust_summary",
    "version": "1.0"
  },
  "summary": {
    "executive": "2-3 paragraph executive summary using {{cite:XXX}} references",
    "sections": [
      {
        "id": "essential_info",
        "title": "Essential Information",
        "content": "## Trust Identity\n\n- **Name:** Trust name {{cite:XXX}}\n- **Created:** Date {{cite:XXX}}\n..."
      },
      {
        "id": "how_it_works",
        "title": "How the Trust Works",
        "content": "## Timeline Organization\n\n### During Grantor's Life\n\nDetails {{cite:XXX}}..."
      },
      {
        "id": "important_provisions",
        "title": "Important Provisions",
        "content": "## Powers and Protections\n\nDetails {{cite:XXX}}..."
      },
      {
        "id": "distributions",
        "title": "Distribution Summary",
        "content": "## Distribution Schedule\n\nDetails {{cite:XXX}}..."
      }
    ]
  }
}
```

## Section Requirements

### Executive Summary
- 2-3 paragraphs capturing the essential story
- Who created it and why
- How it works in practice
- Key protections or features
- Use plain English, not legal jargon

### Essential Information
Must include:
- Trust name(s)
- Date created and location
- Type and status (revocable/irrevocable)
- Tax ID if available
- All key parties (grantor, trustees, beneficiaries)

### How the Trust Works
Organize by the clearest pattern:
- **Timeline** (most common): While grantor alive → After death → Distribution ages
- **Beneficiary-focused**: Different rules for different beneficiaries
- **Event-driven**: What happens when X occurs

### Important Provisions
Include as relevant:
- Trustee powers
- Creditor/divorce protections
- Tax provisions
- Administrative rules
- Modification/termination rules

### Distribution Summary
Create a clear visual summary using:
- Timeline format
- Flowchart format
- Table format
Choose the format that best fits this trust

## Critical Rules

1. **USE ONLY PROVIDED CITATIONS** - Do not create new citation numbers
2. **EVERY FACT NEEDS A CITATION** - No statements without {{cite:XXX}}
3. **USE EXACT CITATION FORMAT** - {{cite:001}}, {{cite:002}}, etc.
4. **TRANSLATE LEGAL TERMS** - Use plain English equivalents
5. **PRESERVE SPECIFIC DETAILS** - Keep names, dates, percentages, ages exact

## Language Guidelines

### Translate Legal Jargon:
- "per stirpes" → "divided equally among that person's children"
- "HEMS standard" → "for health, education, maintenance, and support"
- "sole and absolute discretion" → "complete discretion"
- "power of appointment" → "right to decide who gets the assets"

### Use Clear Language:
- Short sentences when possible
- Active voice
- Specific names, not "the Grantor" after first mention
- Actual percentages and ages, not "various amounts"