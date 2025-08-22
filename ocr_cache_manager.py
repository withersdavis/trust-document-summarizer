"""
OCR Cache Manager - Stores OCR results to avoid re-processing
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

class OCRCacheManager:
    def __init__(self, cache_dir: str = "ocr_cache"):
        """Initialize OCR cache manager with cache directory"""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.index_file = self.cache_dir / "index.json"
        self.index = self._load_index()
    
    def _load_index(self) -> Dict:
        """Load the cache index"""
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_index(self):
        """Save the cache index"""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)
    
    def _get_file_hash(self, file_path: str) -> str:
        """Generate hash of file for cache key"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _get_cache_path(self, file_hash: str) -> Path:
        """Get cache file path for given hash"""
        return self.cache_dir / f"{file_hash}.json"
    
    def has_cached_ocr(self, pdf_path: str) -> bool:
        """Check if OCR results exist for this PDF"""
        try:
            file_hash = self._get_file_hash(pdf_path)
            cache_path = self._get_cache_path(file_hash)
            
            # Check if cache file exists and is in index
            if cache_path.exists() and file_hash in self.index:
                # Verify file hasn't changed
                stored_info = self.index[file_hash]
                file_stats = os.stat(pdf_path)
                
                # Check if file size matches
                if stored_info.get('file_size') == file_stats.st_size:
                    print(f"✓ Found cached OCR for: {Path(pdf_path).name}")
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error checking cache: {e}")
            return False
    
    def get_cached_ocr(self, pdf_path: str) -> Optional[Tuple[str, List[Dict]]]:
        """Retrieve cached OCR results"""
        try:
            file_hash = self._get_file_hash(pdf_path)
            cache_path = self._get_cache_path(file_hash)
            
            if cache_path.exists():
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                
                print(f"✓ Loaded cached OCR: {len(data['pages'])} pages, {len(data['full_text'])} chars")
                return data['full_text'], data['pages']
            
            return None
            
        except Exception as e:
            print(f"Error loading cache: {e}")
            return None
    
    def save_ocr_results(self, pdf_path: str, full_text: str, pages: List[Dict]):
        """Save OCR results to cache"""
        try:
            file_hash = self._get_file_hash(pdf_path)
            cache_path = self._get_cache_path(file_hash)
            file_stats = os.stat(pdf_path)
            
            # Save OCR data
            cache_data = {
                'pdf_path': str(Path(pdf_path).absolute()),
                'pdf_name': Path(pdf_path).name,
                'processed_date': datetime.now().isoformat(),
                'page_count': len(pages),
                'total_chars': len(full_text),
                'full_text': full_text,
                'pages': pages
            }
            
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            # Update index
            self.index[file_hash] = {
                'pdf_path': str(Path(pdf_path).absolute()),
                'pdf_name': Path(pdf_path).name,
                'file_size': file_stats.st_size,
                'file_modified': datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                'processed_date': cache_data['processed_date'],
                'page_count': len(pages),
                'total_chars': len(full_text),
                'cache_file': str(cache_path.name)
            }
            
            self._save_index()
            print(f"✓ Cached OCR results: {Path(pdf_path).name} ({len(pages)} pages)")
            
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def get_cache_stats(self) -> Dict:
        """Get statistics about the cache"""
        stats = {
            'total_documents': len(self.index),
            'total_pages': sum(info['page_count'] for info in self.index.values()),
            'total_chars': sum(info['total_chars'] for info in self.index.values()),
            'cache_size_mb': sum(
                (self.cache_dir / info['cache_file']).stat().st_size 
                for info in self.index.values() 
                if (self.cache_dir / info['cache_file']).exists()
            ) / (1024 * 1024),
            'documents': [
                {
                    'name': info['pdf_name'],
                    'pages': info['page_count'],
                    'processed': info['processed_date']
                }
                for info in self.index.values()
            ]
        }
        return stats
    
    def clear_cache(self):
        """Clear all cached OCR results"""
        for file_hash in self.index:
            cache_path = self._get_cache_path(file_hash)
            if cache_path.exists():
                cache_path.unlink()
        
        self.index = {}
        self._save_index()
        print("✓ OCR cache cleared")