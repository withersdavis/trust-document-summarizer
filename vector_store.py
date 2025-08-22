"""
Vector Store - Semantic search and retrieval for document facts
"""

import os
import json
import hashlib
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import chromadb
from chromadb.config import Settings
from semantic_extractor import Fact
import numpy as np


class DocumentVectorStore:
    """Vector database for semantic search of document facts"""
    
    def __init__(self, collection_name: str = "trust_facts", 
                 persist_directory: str = "vector_db"):
        """
        Initialize vector store
        
        Args:
            collection_name: Name of the collection
            persist_directory: Directory to persist the database
        """
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(exist_ok=True)
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(collection_name)
            print(f"✓ Loaded existing collection: {collection_name}")
        except:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "Trust document facts"}
            )
            print(f"✓ Created new collection: {collection_name}")
    
    def index_facts(self, facts: List[Fact], document_id: str = None) -> int:
        """
        Index facts into the vector store
        
        Args:
            facts: List of facts to index
            document_id: Optional document identifier
        
        Returns:
            Number of facts indexed
        """
        if not facts:
            return 0
        
        # Prepare data for indexing
        documents = []
        metadatas = []
        ids = []
        
        for fact in facts:
            # Create searchable document text
            doc_text = f"{fact.fact}\n\nContext: {fact.context}"
            documents.append(doc_text)
            
            # Prepare metadata
            metadata = {
                "fact_type": fact.fact_type,
                "page": fact.page,
                "char_position": fact.char_position,
                "confidence": fact.confidence,
                "entities": json.dumps(fact.entities),
                "fact_text": fact.fact[:500],  # Store first 500 chars
            }
            
            if document_id:
                metadata["document_id"] = document_id
            
            metadatas.append(metadata)
            
            # Use fact_id or generate one
            fact_id = fact.fact_id or hashlib.md5(
                f"{fact.fact}_{fact.page}".encode()
            ).hexdigest()[:16]
            ids.append(fact_id)
        
        # Add to collection
        try:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"✓ Indexed {len(facts)} facts")
            return len(facts)
        except Exception as e:
            print(f"⚠️ Error indexing facts: {e}")
            return 0
    
    def semantic_search(self, query: str, top_k: int = 10, 
                       filters: Dict = None) -> List[Dict]:
        """
        Perform semantic search for relevant facts
        
        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional metadata filters
        
        Returns:
            List of relevant facts with scores
        """
        try:
            # Build where clause from filters
            where = None
            if filters:
                where = {}
                for key, value in filters.items():
                    if isinstance(value, list):
                        where[key] = {"$in": value}
                    else:
                        where[key] = value
            
            # Perform search
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where,
                include=["metadatas", "documents", "distances"]
            )
            
            # Format results
            formatted_results = []
            if results and results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    result = {
                        'id': results['ids'][0][i],
                        'text': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'score': 1 - results['distances'][0][i]  # Convert distance to similarity
                    }
                    formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            print(f"⚠️ Search error: {e}")
            return []
    
    def search_by_section(self, section_type: str) -> List[Dict]:
        """
        Search for facts relevant to a specific section type
        
        Args:
            section_type: Type of section (essential_info, distributions, etc.)
        
        Returns:
            List of relevant facts
        """
        # Define queries for each section type
        section_queries = {
            'essential_info': "trust name grantor settlor trustee date created established agreement",
            'how_it_works': "administration management trustee powers authority discretion operate function",
            'important_provisions': "restrictions conditions special terms limitations requirements prohibitions",
            'distributions': "beneficiary distribution income principal payment receive inherit allocation"
        }
        
        query = section_queries.get(section_type, section_type)
        
        # Define relevant fact types for each section
        section_fact_types = {
            'essential_info': ['trust_creation', 'trustee_appointment', 'grantor_identification'],
            'how_it_works': ['trustee_power', 'authority_grant', 'provision'],
            'important_provisions': ['condition', 'restriction', 'exception', 'tax_provision'],
            'distributions': ['distribution', 'beneficiary_designation', 'death_trigger', 'termination']
        }
        
        filters = None
        if section_type in section_fact_types:
            filters = {"fact_type": section_fact_types[section_type]}
        
        return self.semantic_search(query, top_k=20, filters=filters)
    
    def find_similar_facts(self, fact_text: str, top_k: int = 5) -> List[Dict]:
        """
        Find facts similar to a given fact
        
        Args:
            fact_text: Text of the fact to find similar ones for
            top_k: Number of similar facts to return
        
        Returns:
            List of similar facts
        """
        return self.semantic_search(fact_text, top_k=top_k)
    
    def get_facts_by_page(self, page_num: int) -> List[Dict]:
        """
        Get all facts from a specific page
        
        Args:
            page_num: Page number
        
        Returns:
            List of facts from that page
        """
        return self.semantic_search(
            "",  # Empty query to get all
            top_k=100,
            filters={"page": page_num}
        )
    
    def get_facts_by_type(self, fact_type: str) -> List[Dict]:
        """
        Get all facts of a specific type
        
        Args:
            fact_type: Type of fact
        
        Returns:
            List of facts of that type
        """
        return self.semantic_search(
            "",  # Empty query to get all
            top_k=100,
            filters={"fact_type": fact_type}
        )
    
    def expand_context(self, facts: List[Dict], expansion_factor: int = 2) -> List[Dict]:
        """
        Expand context by finding related facts
        
        Args:
            facts: Initial facts
            expansion_factor: How many related facts to find per initial fact
        
        Returns:
            Expanded list of facts including related ones
        """
        expanded = list(facts)  # Start with original facts
        seen_ids = {f.get('id') for f in facts}
        
        for fact in facts[:5]:  # Limit to first 5 to avoid explosion
            # Find similar facts
            similar = self.find_similar_facts(
                fact.get('text', ''), 
                top_k=expansion_factor
            )
            
            for sim_fact in similar:
                if sim_fact['id'] not in seen_ids:
                    expanded.append(sim_fact)
                    seen_ids.add(sim_fact['id'])
        
        return expanded
    
    def clear_collection(self):
        """Clear all facts from the collection"""
        try:
            self.client.delete_collection(self.collection.name)
            self.collection = self.client.create_collection(
                name=self.collection.name,
                metadata={"description": "Trust document facts"}
            )
            print("✓ Collection cleared")
        except Exception as e:
            print(f"⚠️ Error clearing collection: {e}")
    
    def get_stats(self) -> Dict:
        """Get statistics about the vector store"""
        try:
            count = self.collection.count()
            
            # Get sample of fact types
            sample = self.collection.get(limit=100, include=["metadatas"])
            fact_types = {}
            if sample and sample['metadatas']:
                for metadata in sample['metadatas']:
                    ft = metadata.get('fact_type', 'unknown')
                    fact_types[ft] = fact_types.get(ft, 0) + 1
            
            return {
                'total_facts': count,
                'fact_types': fact_types,
                'collection_name': self.collection.name,
                'persist_directory': str(self.persist_directory)
            }
        except Exception as e:
            print(f"⚠️ Error getting stats: {e}")
            return {}


def index_document_facts(pdf_path: str, vector_store: DocumentVectorStore = None) -> int:
    """
    Index facts from a document into the vector store
    
    Args:
        pdf_path: Path to PDF document
        vector_store: Optional existing vector store
    
    Returns:
        Number of facts indexed
    """
    from semantic_extractor import extract_facts_from_document
    
    # Extract facts
    facts = extract_facts_from_document(pdf_path)
    
    # Create vector store if not provided
    if vector_store is None:
        vector_store = DocumentVectorStore()
    
    # Generate document ID
    doc_id = Path(pdf_path).stem
    
    # Index facts
    count = vector_store.index_facts(facts, document_id=doc_id)
    
    return count


if __name__ == "__main__":
    import sys
    
    # Test with a document
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
    else:
        pdf_file = "data/2006 Eric Russell ILIT.pdf"
    
    print(f"Indexing facts from: {pdf_file}")
    
    # Create vector store
    vector_store = DocumentVectorStore()
    
    # Index document
    count = index_document_facts(pdf_file, vector_store)
    
    # Test search
    print("\n" + "="*60)
    print("Testing semantic search...")
    print("="*60)
    
    # Search for trust creation
    print("\n1. Searching for 'trust creation date':")
    results = vector_store.semantic_search("trust creation date", top_k=3)
    for i, result in enumerate(results, 1):
        print(f"\n   Result {i} (score: {result['score']:.3f}):")
        print(f"   Type: {result['metadata']['fact_type']}")
        print(f"   Page: {result['metadata']['page']}")
        print(f"   Text: {result['metadata']['fact_text'][:100]}...")
    
    # Search for beneficiaries
    print("\n2. Searching for 'beneficiary distributions':")
    results = vector_store.semantic_search("beneficiary distributions", top_k=3)
    for i, result in enumerate(results, 1):
        print(f"\n   Result {i} (score: {result['score']:.3f}):")
        print(f"   Type: {result['metadata']['fact_type']}")
        print(f"   Page: {result['metadata']['page']}")
        print(f"   Text: {result['metadata']['fact_text'][:100]}...")
    
    # Get stats
    print("\n" + "="*60)
    print("Vector Store Statistics:")
    print("="*60)
    stats = vector_store.get_stats()
    print(f"Total facts indexed: {stats['total_facts']}")
    print(f"Fact types distribution:")
    for ft, count in stats.get('fact_types', {}).items():
        print(f"  - {ft}: {count}")