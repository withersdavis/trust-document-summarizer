"""
Concept Categorizer - Classify facts into semantic categories
"""

import re
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from semantic_extractor import Fact


@dataclass 
class ConceptCategory:
    """Represents a semantic concept category"""
    name: str
    description: str
    keywords: List[str]
    patterns: List[str]
    importance: float  # 0.0 to 1.0
    
    def matches(self, text: str) -> float:
        """Calculate match score for text against this category"""
        text_lower = text.lower()
        score = 0.0
        
        # Check keywords
        keyword_matches = sum(1 for kw in self.keywords if kw.lower() in text_lower)
        if self.keywords:
            score += (keyword_matches / len(self.keywords)) * 0.5
        
        # Check patterns
        pattern_matches = sum(1 for pattern in self.patterns 
                            if re.search(pattern, text, re.IGNORECASE))
        if self.patterns:
            score += (pattern_matches / len(self.patterns)) * 0.5
        
        return score * self.importance


class ConceptCategorizer:
    """Categorize facts and text into semantic concepts"""
    
    def __init__(self):
        # Define trust document concept categories
        self.categories = self._initialize_categories()
        
        # Cache for categorization results
        self.category_cache = {}
    
    def _initialize_categories(self) -> List[ConceptCategory]:
        """Initialize concept categories for trust documents"""
        return [
            ConceptCategory(
                name="trust_creation",
                description="Trust establishment and formation",
                keywords=["established", "created", "dated", "made", "executed", "agreement"],
                patterns=[
                    r"trust.*(?:dated|made|executed|created).*\d{4}",
                    r"(?:agreement|trust).*(?:is|was).*(?:made|created)",
                    r"(?:established|formation).*trust"
                ],
                importance=1.0
            ),
            ConceptCategory(
                name="grantor_settlor",
                description="Grantor/Settlor identity and provisions",
                keywords=["grantor", "settlor", "trustor", "creator", "establisher"],
                patterns=[
                    r"(?:grantor|settlor|trustor).*(?:is|was|named)",
                    r"I,?\s+[A-Z][a-z]+.*(?:grantor|settlor)",
                    r"(?:created|established)\s+by\s+[A-Z][a-z]+"
                ],
                importance=0.95
            ),
            ConceptCategory(
                name="trustee_appointment",
                description="Trustee designation and succession",
                keywords=["trustee", "successor", "co-trustee", "appointment", "resign"],
                patterns=[
                    r"(?:trustee|successor trustee).*(?:shall be|is|appointed)",
                    r"(?:appoint|designate).*trustee",
                    r"(?:removal|resignation).*trustee"
                ],
                importance=0.9
            ),
            ConceptCategory(
                name="trustee_powers",
                description="Powers and authorities granted to trustees",
                keywords=["power", "authority", "discretion", "may", "shall", "authorized"],
                patterns=[
                    r"trustee.*(?:may|shall|is authorized to)",
                    r"(?:power|authority).*trustee",
                    r"trustee.*discretion"
                ],
                importance=0.85
            ),
            ConceptCategory(
                name="beneficiary_designation",
                description="Beneficiary identification and classification",
                keywords=["beneficiary", "beneficiaries", "heir", "descendant", "children"],
                patterns=[
                    r"(?:primary|contingent).*beneficiar",
                    r"beneficiar.*(?:is|are|shall be)",
                    r"(?:children|descendants).*beneficiar"
                ],
                importance=0.95
            ),
            ConceptCategory(
                name="distribution_rules",
                description="Rules for distributions and payments",
                keywords=["distribute", "distribution", "payment", "income", "principal", "receive"],
                patterns=[
                    r"(?:distribute|pay).*(?:income|principal)",
                    r"(?:mandatory|discretionary).*distribution",
                    r"(?:upon|at).*(?:age|death).*(?:distribute|receive)"
                ],
                importance=0.9
            ),
            ConceptCategory(
                name="distribution_timing",
                description="When distributions occur",
                keywords=["age", "death", "upon", "when", "reaching", "attaining"],
                patterns=[
                    r"(?:upon|at).*age.*\d+",
                    r"(?:upon|after).*death",
                    r"when.*(?:reaches|attains).*age"
                ],
                importance=0.85
            ),
            ConceptCategory(
                name="tax_provisions",
                description="Tax-related provisions and planning",
                keywords=["tax", "GST", "estate", "gift", "exemption", "deduction", "marital"],
                patterns=[
                    r"(?:estate|gift|GST).*tax",
                    r"tax.*(?:exemption|deduction|credit)",
                    r"marital.*deduction"
                ],
                importance=0.8
            ),
            ConceptCategory(
                name="spendthrift_protection",
                description="Asset protection and spendthrift provisions",
                keywords=["spendthrift", "creditor", "protection", "attachment", "alienation"],
                patterns=[
                    r"spendthrift.*(?:provision|trust|protection)",
                    r"(?:creditor|attachment).*protection",
                    r"(?:cannot|may not).*(?:assign|alienate)"
                ],
                importance=0.75
            ),
            ConceptCategory(
                name="termination_conditions",
                description="Trust termination conditions",
                keywords=["terminate", "termination", "end", "conclusion", "final"],
                patterns=[
                    r"trust.*(?:shall|will).*terminate",
                    r"(?:upon|at).*termination",
                    r"final.*distribution"
                ],
                importance=0.8
            ),
            ConceptCategory(
                name="withdrawal_rights",
                description="Rights to withdraw assets",
                keywords=["withdrawal", "withdraw", "crummey", "annual exclusion"],
                patterns=[
                    r"(?:right|power).*withdraw",
                    r"annual.*(?:exclusion|withdrawal)",
                    r"crummey.*(?:power|withdrawal)"
                ],
                importance=0.75
            ),
            ConceptCategory(
                name="administrative_provisions",
                description="Trust administration and management",
                keywords=["administration", "accounting", "report", "manage", "invest"],
                patterns=[
                    r"(?:administration|management).*trust",
                    r"trustee.*(?:account|report)",
                    r"(?:invest|investment).*(?:power|authority)"
                ],
                importance=0.7
            ),
            ConceptCategory(
                name="amendment_modification",
                description="Amendment and modification provisions",
                keywords=["amend", "modify", "revoke", "irrevocable", "change"],
                patterns=[
                    r"(?:amend|modify).*(?:trust|agreement)",
                    r"(?:irrevocable|revocable).*trust",
                    r"(?:cannot|may not).*(?:amend|modify|revoke)"
                ],
                importance=0.75
            ),
            ConceptCategory(
                name="special_provisions",
                description="Special or unique provisions",
                keywords=["special", "specific", "particular", "unique", "exception"],
                patterns=[
                    r"(?:special|specific).*(?:provision|instruction)",
                    r"(?:exception|except).*(?:to|from)",
                    r"notwithstanding"
                ],
                importance=0.65
            ),
            ConceptCategory(
                name="definitions",
                description="Defined terms and definitions",
                keywords=["means", "definition", "defined", "shall mean", "includes"],
                patterns=[
                    r'"[^"]+".*means',
                    r'(?:defined|definition).*(?:as|means)',
                    r'for purposes of.*(?:means|shall mean)'
                ],
                importance=0.6
            )
        ]
    
    def categorize_fact(self, fact: Fact) -> List[Tuple[str, float]]:
        """
        Categorize a single fact into concepts
        
        Args:
            fact: Fact to categorize
        
        Returns:
            List of (category_name, confidence) tuples
        """
        # Check cache
        cache_key = fact.fact_id
        if cache_key in self.category_cache:
            return self.category_cache[cache_key]
        
        # Calculate scores for each category
        scores = []
        text_to_check = f"{fact.fact} {fact.context}"
        
        for category in self.categories:
            score = category.matches(text_to_check)
            
            # Boost score if fact_type matches category name
            if fact.fact_type and category.name in fact.fact_type:
                score = min(1.0, score + 0.3)
            
            if score > 0.1:  # Threshold for relevance
                scores.append((category.name, score))
        
        # Sort by score and take top categories
        scores.sort(key=lambda x: x[1], reverse=True)
        result = scores[:3]  # Return top 3 categories
        
        # Cache result
        self.category_cache[cache_key] = result
        
        return result
    
    def categorize_facts(self, facts: List[Fact]) -> Dict[str, List[Fact]]:
        """
        Categorize multiple facts into concept groups
        
        Args:
            facts: List of facts to categorize
        
        Returns:
            Dictionary mapping category names to lists of facts
        """
        categorized = {cat.name: [] for cat in self.categories}
        categorized['uncategorized'] = []
        
        for fact in facts:
            categories = self.categorize_fact(fact)
            
            if categories:
                # Add to primary category (highest score)
                primary_category = categories[0][0]
                categorized[primary_category].append(fact)
            else:
                categorized['uncategorized'].append(fact)
        
        # Remove empty categories
        return {k: v for k, v in categorized.items() if v}
    
    def get_category_importance(self, category_name: str) -> float:
        """Get importance score for a category"""
        for cat in self.categories:
            if cat.name == category_name:
                return cat.importance
        return 0.5  # Default importance
    
    def get_categories_for_section(self, section_type: str) -> List[str]:
        """
        Get relevant categories for a document section
        
        Args:
            section_type: Type of section (essential_info, distributions, etc.)
        
        Returns:
            List of relevant category names
        """
        section_categories = {
            'essential_info': [
                'trust_creation', 'grantor_settlor', 'trustee_appointment', 
                'beneficiary_designation'
            ],
            'how_it_works': [
                'trustee_powers', 'administrative_provisions', 
                'amendment_modification', 'withdrawal_rights'
            ],
            'important_provisions': [
                'spendthrift_protection', 'tax_provisions', 
                'special_provisions', 'termination_conditions'
            ],
            'distributions': [
                'distribution_rules', 'distribution_timing', 
                'beneficiary_designation', 'withdrawal_rights'
            ]
        }
        
        return section_categories.get(section_type, [])
    
    def filter_facts_by_section(self, facts: List[Fact], 
                               section_type: str) -> List[Fact]:
        """
        Filter facts relevant to a specific section
        
        Args:
            facts: List of all facts
            section_type: Type of section to filter for
        
        Returns:
            List of relevant facts
        """
        relevant_categories = set(self.get_categories_for_section(section_type))
        filtered = []
        
        for fact in facts:
            categories = self.categorize_fact(fact)
            if any(cat[0] in relevant_categories for cat in categories):
                filtered.append(fact)
        
        return filtered
    
    def get_fact_importance(self, fact: Fact) -> float:
        """
        Calculate overall importance score for a fact
        
        Args:
            fact: Fact to score
        
        Returns:
            Importance score (0.0 to 1.0)
        """
        categories = self.categorize_fact(fact)
        
        if not categories:
            return fact.confidence * 0.5
        
        # Use highest category score weighted by category importance
        max_score = 0.0
        for cat_name, cat_score in categories:
            cat_importance = self.get_category_importance(cat_name)
            weighted_score = cat_score * cat_importance
            max_score = max(max_score, weighted_score)
        
        # Combine with fact confidence
        return (max_score + fact.confidence) / 2
    
    def get_category_summary(self, facts: List[Fact]) -> Dict[str, Dict]:
        """
        Generate summary statistics for categorized facts
        
        Args:
            facts: List of facts
        
        Returns:
            Dictionary with category statistics
        """
        categorized = self.categorize_facts(facts)
        summary = {}
        
        for cat_name, cat_facts in categorized.items():
            if cat_facts:
                # Find category description
                cat_desc = "Other provisions"
                for cat in self.categories:
                    if cat.name == cat_name:
                        cat_desc = cat.description
                        break
                
                summary[cat_name] = {
                    'description': cat_desc,
                    'count': len(cat_facts),
                    'pages': sorted(set(f.page for f in cat_facts)),
                    'avg_confidence': sum(f.confidence for f in cat_facts) / len(cat_facts),
                    'importance': self.get_category_importance(cat_name)
                }
        
        return summary


def categorize_document_facts(pdf_path: str) -> Dict[str, List[Fact]]:
    """
    Convenience function to categorize facts from a document
    
    Args:
        pdf_path: Path to PDF document
    
    Returns:
        Dictionary of categorized facts
    """
    from semantic_extractor import extract_facts_from_document
    
    # Extract facts
    facts = extract_facts_from_document(pdf_path)
    
    # Categorize
    categorizer = ConceptCategorizer()
    categorized = categorizer.categorize_facts(facts)
    
    return categorized


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
    else:
        pdf_file = "data/2006 Eric Russell ILIT.pdf"
    
    print(f"Categorizing facts from: {pdf_file}")
    categorized = categorize_document_facts(pdf_file)
    
    print(f"\nCategory Distribution:")
    print("="*60)
    
    for category, facts in categorized.items():
        if facts:
            print(f"\n{category}: {len(facts)} facts")
            # Show top 3 facts
            for fact in facts[:3]:
                print(f"  - Page {fact.page}: {fact.fact[:60]}...")
    
    # Get summary
    from semantic_extractor import extract_facts_from_document
    facts = extract_facts_from_document(pdf_file)
    categorizer = ConceptCategorizer()
    summary = categorizer.get_category_summary(facts)
    
    print(f"\n\nCategory Summary Statistics:")
    print("="*60)
    for cat_name, stats in summary.items():
        print(f"\n{cat_name}:")
        print(f"  Description: {stats['description']}")
        print(f"  Count: {stats['count']} facts")
        print(f"  Pages: {stats['pages'][:5]}..." if len(stats['pages']) > 5 else f"  Pages: {stats['pages']}")
        print(f"  Avg Confidence: {stats['avg_confidence']:.2f}")
        print(f"  Importance: {stats['importance']:.2f}")