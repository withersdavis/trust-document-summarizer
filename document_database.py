"""
Document Database - Track source documents, OCR versions, and processing results
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

class DocumentDatabase:
    def __init__(self, db_path: str = "documents.db"):
        """Initialize document database"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        cursor = self.conn.cursor()
        
        # Documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_name TEXT NOT NULL,
                file_size INTEGER,
                file_hash TEXT,
                page_count INTEGER,
                document_type TEXT,
                added_date TEXT,
                last_modified TEXT
            )
        """)
        
        # OCR cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ocr_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                cache_file TEXT,
                ocr_date TEXT,
                total_chars INTEGER,
                page_count INTEGER,
                processing_time REAL,
                FOREIGN KEY (document_id) REFERENCES documents (id)
            )
        """)
        
        # Processing results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processing_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                processing_type TEXT NOT NULL,
                result_file TEXT,
                processing_date TEXT,
                processing_time REAL,
                citations_count INTEGER,
                placeholders_count INTEGER,
                sections_count INTEGER,
                status TEXT,
                error_message TEXT,
                metadata TEXT,
                FOREIGN KEY (document_id) REFERENCES documents (id)
            )
        """)
        
        self.conn.commit()
    
    def add_document(self, file_path: str, file_hash: str = None) -> int:
        """Add a document to the database"""
        cursor = self.conn.cursor()
        file_path = str(Path(file_path).absolute())
        file_name = Path(file_path).name
        
        try:
            file_stats = Path(file_path).stat()
            file_size = file_stats.st_size
            last_modified = datetime.fromtimestamp(file_stats.st_mtime).isoformat()
        except:
            file_size = 0
            last_modified = None
        
        # Check if document exists
        cursor.execute("SELECT id FROM documents WHERE file_path = ?", (file_path,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing document
            cursor.execute("""
                UPDATE documents 
                SET file_size = ?, last_modified = ?, file_hash = ?
                WHERE file_path = ?
            """, (file_size, last_modified, file_hash, file_path))
            doc_id = existing['id']
        else:
            # Insert new document
            cursor.execute("""
                INSERT INTO documents (file_path, file_name, file_size, file_hash, 
                                     added_date, last_modified, document_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (file_path, file_name, file_size, file_hash, 
                  datetime.now().isoformat(), last_modified, 'trust'))
            doc_id = cursor.lastrowid
        
        self.conn.commit()
        return doc_id
    
    def add_ocr_cache(self, document_id: int, cache_file: str, total_chars: int, 
                      page_count: int, processing_time: float = None):
        """Record OCR cache information"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO ocr_cache (document_id, cache_file, ocr_date, total_chars, 
                                  page_count, processing_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (document_id, cache_file, datetime.now().isoformat(), 
              total_chars, page_count, processing_time))
        
        # Update document page count
        cursor.execute("""
            UPDATE documents SET page_count = ? WHERE id = ?
        """, (page_count, document_id))
        
        self.conn.commit()
    
    def add_processing_result(self, document_id: int, processing_type: str, 
                            result_file: str, metadata: Dict):
        """Record a processing result"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO processing_results 
            (document_id, processing_type, result_file, processing_date,
             citations_count, placeholders_count, sections_count, status, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (document_id, processing_type, result_file, datetime.now().isoformat(),
              metadata.get('citations_count', 0),
              metadata.get('placeholders_count', 0),
              metadata.get('sections_count', 0),
              metadata.get('status', 'completed'),
              json.dumps(metadata)))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_document_by_path(self, file_path: str) -> Optional[Dict]:
        """Get document info by file path"""
        cursor = self.conn.cursor()
        file_path = str(Path(file_path).absolute())
        
        cursor.execute("SELECT * FROM documents WHERE file_path = ?", (file_path,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def get_all_documents(self) -> List[Dict]:
        """Get all documents in the database"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT d.*, 
                   COUNT(DISTINCT o.id) as ocr_count,
                   COUNT(DISTINCT p.id) as result_count
            FROM documents d
            LEFT JOIN ocr_cache o ON d.id = o.document_id
            LEFT JOIN processing_results p ON d.id = p.document_id
            GROUP BY d.id
            ORDER BY d.added_date DESC
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_processing_results(self, document_id: int = None) -> List[Dict]:
        """Get processing results, optionally filtered by document"""
        cursor = self.conn.cursor()
        
        if document_id:
            cursor.execute("""
                SELECT p.*, d.file_name 
                FROM processing_results p
                JOIN documents d ON p.document_id = d.id
                WHERE p.document_id = ?
                ORDER BY p.processing_date DESC
            """, (document_id,))
        else:
            cursor.execute("""
                SELECT p.*, d.file_name 
                FROM processing_results p
                JOIN documents d ON p.document_id = d.id
                ORDER BY p.processing_date DESC
            """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        cursor = self.conn.cursor()
        
        stats = {}
        
        # Document stats
        cursor.execute("SELECT COUNT(*) as count FROM documents")
        stats['total_documents'] = cursor.fetchone()['count']
        
        # OCR stats
        cursor.execute("""
            SELECT COUNT(*) as count, SUM(total_chars) as chars, SUM(page_count) as pages
            FROM ocr_cache
        """)
        row = cursor.fetchone()
        stats['total_ocr_cached'] = row['count'] or 0
        stats['total_chars_extracted'] = row['chars'] or 0
        stats['total_pages_processed'] = row['pages'] or 0
        
        # Processing stats
        cursor.execute("""
            SELECT processing_type, COUNT(*) as count, 
                   AVG(citations_count) as avg_citations,
                   AVG(placeholders_count) as avg_placeholders
            FROM processing_results
            GROUP BY processing_type
        """)
        stats['processing_types'] = [dict(row) for row in cursor.fetchall()]
        
        return stats
    
    def close(self):
        """Close database connection"""
        self.conn.close()