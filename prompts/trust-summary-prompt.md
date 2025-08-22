# Trust Document Standardization Prompt

## Objective
Create a standardized summary of a trust document that:
1. Reduces the context size of the trust document
2. Maintains >99% of the material information in the document
3. Makes the trust document clearly understandable for an average person
4. Provides accurate citations to source material
5. Outputs in a structured JSON format with embedded markdown

## Core Structure

### **Executive Summary**
Write 2-3 paragraphs in plain English that capture:
- The essential story of this trust (who, what, when, why)
- How it works in practice
- Key protections or special features

Use conversational language. Include citations for all factual statements.

Example:
```json
{
  "executive": "The Homer J. Simpson Revocable Trust was created on {{cite:001}} by Homer Simpson {{cite:002}} to manage his assets during his lifetime and provide for Marge and their children after his death. During Homer's lifetime, he retains complete control {{cite:003}} and can revoke or amend the trust at any time {{cite:004}}. Upon Homer's death, the trust becomes irrevocable {{cite:005}} and divides into separate trusts for Marge and the children, with distributions for education, health, and support {{cite:006}}."
}
```

---

### **Essential Information**

#### **Trust Identity**
Include the fundamental identifying information with citations:
- Name(s) of the trust
- Date created and location
- Type and status
- Tax ID if available

#### **Key Parties**
List all important parties and their roles with citations:
- Who created the trust
- Who manages it (now and succession plan)
- Who benefits (primary and contingent)
- Any special roles (protectors, advisors, etc.)

---

### **How the Trust Works**

Organize this section by LOGICAL FLOW, not the document's written order. Choose the clearest organization pattern and cite all facts:

#### **Timeline Organization** (Most Common)
Best for trusts with clear life stages. Example structure:
```json
{
  "content": "## While Homer Is Alive\n\nHomer can revoke or amend the trust at any time {{cite:010}}. The trustee must distribute $5,000 monthly to Homer {{cite:011}}. Marge has no rights during this period {{cite:012}}.\n\n## When Homer Dies\n\nThe trust becomes irrevocable {{cite:013}}. The trustee divides assets: 40% to Marital Trust {{cite:014}}, 60% to Family Trust {{cite:015}}."
}
```

#### **Beneficiary Organization**
Best when different beneficiaries have very different terms:
```json
{
  "content": "## Provisions for Marge\n\nMarge receives all income for life {{cite:020}}. She can withdraw the greater of $50,000 or 5% annually {{cite:021}}.\n\n## Provisions for Bart\n\nBart's share is held in trust until age 35 {{cite:022}}. Distributions available for education before then {{cite:023}}."
}
```

#### **Event-Driven Organization**
Best for trusts with multiple triggering events:
```json
{
  "content": "## If Homer Becomes Disabled\n\nLisa, as successor trustee, takes over {{cite:030}}. Trust pays for Homer's care first {{cite:031}}, then family support {{cite:032}}."
}
```

Within each section, always specify:
- WHO has rights/powers (use actual names from the document) with citations
- WHAT they can do or receive with citations  
- WHEN it happens or changes with citations
- HOW it works (mechanism/process) with citations
- WHY (conditions or standards) with citations

---

### **Important Provisions**

Include sections as needed for:
- **Powers** - What trustees can do, beneficiary rights
- **Protections** - Creditor, divorce, spendthrift provisions
- **Tax Matters** - Elections, responsibilities, planning features
- **Administrative Rules** - Accounting, governing law, dispute resolution
- **Modification/Termination** - How and when the trust can change or end
- **Special Instructions** - Unique provisions specific to this trust

---

### **Distribution Summary**

Create a clear, visual summary of who gets what and when. Include citations for all distribution rules:

**Timeline Format:**
```json
{
  "content": "```\nAge 25: Bart receives 25% of his trust {{cite:040}}\nAge 30: Bart receives additional 25% (total 50%) {{cite:041}}\nAge 35: Bart receives remaining 50% (trust terminates) {{cite:042}}\n```"
}
```

**Flowchart Format:**
```json
{
  "content": "```\nAt Homer's Death:\n├── If Marge survives → 100% to Marital Trust {{cite:050}}\n│   └── At Marge's death → Divided equally among children {{cite:051}}\n└── If Marge predeceased → Divided equally among children {{cite:052}}\n    └── If any child predeceased → That share to their children {{cite:053}}\n```"
}
```

**Table Format:**
```json
{
  "content": "| Beneficiary | During Homer's Life | At Homer's Death | At Age 35 |\n|------------|-------------------|-----------------|----------|\n| Marge | No rights {{cite:060}} | All income {{cite:061}} | N/A |\n| Bart | $5,000/year {{cite:062}} | Trust share {{cite:063}} | 100% outright {{cite:064}} |"
}
```

Choose the format that makes the distribution scheme clearest for this specific trust.

---

## Citation Guidelines

### Creating Citations

Every factual statement must have a citation. Create citations as follows:

```json
{
  "citations": {
    "001": {
      "fact_type": "trust_creation",  // Categories: trust_creation, grantor_identity, trustee_identity, trustee_power, beneficiary_right, distribution_rule, tax_provision, etc.
      "scope": "phrase",  // word|phrase|sentence|paragraph|section|table
      "confidence": 1.0,  // 1.0 for explicit text, 0.8-0.9 for interpreted
      "sources": [
        {
          "type": "text",
          "page": 1,  // Can be number, array [1,2,3], or range {"start": 1, "end": 3}
          "location": {
            "section": "Opening Paragraph",
            "paragraph": 1
          },
          "exact_text": "THIS TRUST AGREEMENT made this 15th day of March, 2024",
          "context": "Full paragraph if needed for understanding..."
        }
      ]
    }
  }
}
```

### Citation Scope Examples

**Word-level citation:**
```json
{
  "content": "The trustee {{cite:001}} has complete discretion {{cite:002}}",
  "citation_ranges": [
    {"cite_id": "001", "start_char": 4, "end_char": 11, "text": "trustee"},
    {"cite_id": "002", "start_char": 16, "end_char": 34, "text": "complete discretion"}
  ]
}
```

**Section-level citation:**
```json
{
  "content": "## Trustee Powers\n\n{{cite:010}}",
  "citations": {
    "010": {
      "scope": "section",
      "sources": [{
        "type": "section",
        "page": [5, 6, 7],
        "location": {"section": "Article 6"},
        "exact_text": "[TRUNCATED - Full section text]",
        "summary": "Complete enumeration of trustee powers"
      }]
    }
  }
}
```

**Multiple sources for one fact:**
```json
{
  "citations": {
    "015": {
      "fact_type": "trustee_discretion",
      "sources": [
        {
          "page": 3,
          "exact_text": "sole and absolute discretion"
        },
        {
          "page": 7,
          "exact_text": "as the Trustee deems advisable"
        }
      ]
    }
  }
}
```

## Guidelines for Creating Summary

### PRESERVE the trust's:
- Actual names and terms (don't genericize)
  - ✓ "The 2006 Homer J. Simpson Irrevocable Trust" {{cite:001}}
  - ✗ "The Family Trust"
- Specific numbers (ages, percentages, amounts)
  - ✓ "25% at age 30 {{cite:002}}, 75% at age 35 {{cite:003}}"
  - ✗ "portions at various ages"
- Important conditions and contingencies
  - ✓ "If Lisa dies before age 35 {{cite:004}}, her share goes to her children {{cite:005}}"
  - ✗ "subject to various conditions"

### TRANSLATE into plain English:
- Legal jargon → everyday language
  - "sole and absolute discretion" → "complete discretion"
  - "per stirpes" → "divided equally among that person's children"
  - "HEMS standard" → "for health, education, maintenance, and support"
- Complex sentences → clear, simple statements
  - Original: "Notwithstanding the foregoing, in the event that..."
  - Translation: "However, if..."
- Technical terms → practical meanings
  - "power of appointment" → "right to decide who gets the assets"
  - "spendthrift provision" → "protection from creditors"

### ORGANIZE for clarity:
- Group related information logically, not by article number
  - Put all successor trustee info together, even if scattered in original
- Fix illogical document order
  - If Article 7 defines terms used in Article 2, explain terms first
- Repeat key information when helpful
  - If distribution rules apply in multiple scenarios, repeat them with same citations
- Create clear hierarchies
  - Main rule → Exception → Exception to exception

### CITE everything:
- Every factual statement needs a citation
- Use exact quotes from the source document
- If multiple sources support one fact, include all
- For interpreted facts (not explicit in text), set confidence < 1.0
- Preserve entire relevant text in exact_text field

### COMPLETENESS CHECK:
The summary should answer:
- Who created this trust and why?
- Who's in charge and who takes over?
- Who benefits and how?
- When do distributions happen?
- What happens in various scenarios (death, disability, etc.)?
- How are taxes and administration handled?
- When and how does it end?
- What protections exist?

### NOTE ON FLEXIBILITY:
- Not every trust needs every section
- Add sections unique to the specific trust
- Combine or split sections as makes sense
- The goal is clarity and completeness, not rigid conformity

### DOCUMENTATION:
Always conclude with:
- What documents were reviewed
- Any information that appears incomplete or missing
- Assumptions made or clarifications needed

---

## Complete Example Output

```json
{
  "meta": {
    "trust_name": "The Homer J. Simpson Revocable Trust",
    "document_type": "trust_summary",
    "version": "1.0",
    "created_date": "2024-01-15",
    "source_document": "homer-simpson-trust.pdf",
    "page_count": 12,
    "summary_method": "manual",
    "confidence_score": 0.95
  },
  "summary": {
    "executive": "The Homer J. Simpson Revocable Trust was created on March 15, 2024 {{cite:001}} by Homer Simpson of Springfield {{cite:002}} to manage his assets during his lifetime and provide for his family after death. Homer retains complete control during his lifetime {{cite:003}}, including the right to revoke or amend {{cite:004}}. Upon his death, the trust becomes irrevocable {{cite:005}} and divides into separate trusts for Marge and each child {{cite:006}}.",
    "sections": [
      {
        "id": "essential_info",
        "title": "Essential Information",
        "content": "## Trust Identity\n\n- **Name:** The Homer J. Simpson Revocable Trust {{cite:001}}\n- **Created:** March 15, 2024 {{cite:001}}\n- **Grantor:** Homer Simpson {{cite:002}}\n- **Initial Trustee:** Homer Simpson {{cite:007}}\n- **Successor Trustee:** Marge Simpson {{cite:008}}, then Lisa Simpson {{cite:009}}"
      },
      {
        "id": "distributions",
        "title": "How the Trust Works",
        "content": "## While Homer Is Alive\n\nHomer can revoke or amend the trust at any time {{cite:003}}. All income and principal available to Homer {{cite:010}}.\n\n## When Homer Dies\n\nTrust becomes irrevocable {{cite:005}}. Assets divide:\n- 50% to Marital Trust for Marge {{cite:011}}\n- 50% divided equally among children {{cite:012}}"
      }
    ]
  },
  "citations": {
    "001": {
      "fact_type": "trust_creation",
      "scope": "sentence",
      "confidence": 1.0,
      "sources": [
        {
          "type": "text",
          "page": 1,
          "location": {
            "section": "Opening",
            "paragraph": 1
          },
          "exact_text": "THIS REVOCABLE TRUST AGREEMENT is made this 15th day of March, 2024, by HOMER J. SIMPSON",
          "context": null
        }
      ]
    },
    "002": {
      "fact_type": "grantor_identity",
      "scope": "phrase",
      "confidence": 1.0,
      "sources": [
        {
          "type": "text",
          "page": 1,
          "location": {
            "section": "Opening",
            "paragraph": 1
          },
          "exact_text": "HOMER J. SIMPSON, of Springfield",
          "context": null
        }
      ]
    },
    "008": {
      "fact_type": "successor_trustee",
      "scope": "phrase",
      "confidence": 1.0,
      "sources": [
        {
          "type": "text",
          "page": 4,
          "location": {
            "section": "Article 5",
            "paragraph": 2
          },
          "exact_text": "Upon Homer's death or incapacity, MARGE SIMPSON shall serve as Successor Trustee",
          "context": null
        }
      ]
    }
  },
  "citation_ranges": []
}
```