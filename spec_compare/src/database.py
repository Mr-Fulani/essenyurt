"""
Database module for Specification Comparison Tool
SQLite database with FTS5 for full-text search
"""

import sqlite3
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np


class Database:
    """SQLite database manager for specification files"""
    
    def __init__(self, db_path: str = "specifications.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(
            self.db_path, 
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        self.conn.row_factory = sqlite3.Row
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables and indexes"""
        cursor = self.conn.cursor()
        
        # Enable FTS5
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='files'")
        
        # Create files table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_hash TEXT UNIQUE NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_weight REAL DEFAULT 0,
                total_items INTEGER DEFAULT 0,
                manufacturers TEXT,  -- JSON array
                brands TEXT,  -- JSON array
                json_snapshot TEXT  -- Full data as JSON
            )
        ''')
        
        # Create products table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                name_clean TEXT NOT NULL,
                name_original TEXT,
                manufacturer TEXT,
                brand TEXT,
                weight_net REAL DEFAULT 0,
                quantity INTEGER DEFAULT 0,
                article TEXT,
                similarity_vector TEXT,  -- Precomputed vector for fast comparison
                FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
            )
        ''')
        
        # Create indexes for fast search
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_weight ON files(total_weight)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_date ON files(upload_date)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_file_id ON products(file_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_manufacturer ON products(manufacturer)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_name ON products(name_clean)
        ''')
        
        # Create FTS5 virtual table for full-text search
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS products_fts USING fts5(
                name_clean,
                manufacturer,
                brand,
                content='products',
                content_rowid='id'
            )
        ''')
        
        # Triggers to keep FTS index in sync
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS products_ai AFTER INSERT ON products BEGIN
                INSERT INTO products_fts(rowid, name_clean, manufacturer, brand)
                VALUES (new.id, new.name_clean, new.manufacturer, new.brand);
            END
        ''')
        
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS products_ad AFTER DELETE ON products BEGIN
                INSERT INTO products_fts(products_fts, rowid, name_clean, manufacturer, brand)
                VALUES ('delete', old.id, old.name_clean, old.manufacturer, old.brand);
            END
        ''')
        
        self.conn.commit()
    
    def compute_file_hash(self, file_path: str) -> str:
        """Compute MD5 hash of file for deduplication"""
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def file_exists(self, file_hash: str) -> bool:
        """Check if file already exists in database"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM files WHERE file_hash = ?", (file_hash,))
        return cursor.fetchone() is not None
    
    def add_file(self, filename: str, file_path: str, products_data: List[Dict]) -> int:
        """Add new file with its products to database"""
        file_hash = self.compute_file_hash(file_path)
        
        if self.file_exists(file_hash):
            raise ValueError(f"File '{filename}' already exists in database (duplicate)")
        
        # Calculate totals
        total_weight = sum(p.get('weight_net', 0) or 0 for p in products_data)
        total_items = len(products_data)
        manufacturers = list(set(p.get('manufacturer', '') for p in products_data if p.get('manufacturer')))
        brands = list(set(p.get('brand', '') for p in products_data if p.get('brand')))
        
        # Insert file record
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO files (filename, file_hash, total_weight, total_items, manufacturers, brands, json_snapshot)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            filename,
            file_hash,
            total_weight,
            total_items,
            json.dumps(manufacturers, ensure_ascii=False),
            json.dumps(brands, ensure_ascii=False),
            json.dumps(products_data, ensure_ascii=False)
        ))
        
        file_id = cursor.lastrowid
        if file_id is None:
            raise ValueError("Failed to get lastrowid after inserting file")
        
        file_id = int(file_id)
        
        # Insert products
        for product in products_data:
            cursor.execute('''
                INSERT INTO products (file_id, name_clean, name_original, manufacturer, brand, weight_net, quantity, article)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                file_id,
                self._clean_name(product.get('name', '')),
                product.get('name', ''),
                product.get('manufacturer', ''),
                product.get('brand', ''),
                product.get('weight_net', 0) or 0,
                product.get('quantity', 0) or 0,
                product.get('article', '')
            ))
        
        self.conn.commit()
        return file_id
    
    def _clean_name(self, name: str) -> str:
        """Clean product name for better matching"""
        if not name:
            return ''
        # Uppercase and remove extra spaces
        name = ' '.join(name.upper().split())
        # Remove common filler words
        fillers = ['THE', 'AND', 'OR', 'WITH', 'FOR', 'OF', 'IN', 'ON', 'AT', 'TO']
        words = [w for w in name.split() if w not in fillers]
        return ' '.join(words)
    
    def get_file(self, file_id: int) -> Optional[Dict]:
        """Get file by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM files WHERE id = ?", (file_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def get_file_products(self, file_id: int) -> List[Dict]:
        """Get all products for a file"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT *, name_original as name FROM products WHERE file_id = ?", (file_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_all_files(self, date_from: Optional[str] = None, 
                      date_to: Optional[str] = None,
                      limit: Optional[int] = None) -> List[Dict]:
        """Get all files with optional filtering"""
        query = "SELECT * FROM files WHERE 1=1"
        params = []
        
        if date_from:
            query += " AND date(upload_date) >= ?"
            params.append(date_from)
        if date_to:
            query += " AND date(upload_date) <= ?"
            params.append(date_to)
        
        query += " ORDER BY upload_date DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_files_by_weight_range(self, min_weight: float, max_weight: float) -> List[Dict]:
        """Get files within weight range (for pre-filtering)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM files 
            WHERE total_weight BETWEEN ? AND ?
        ''', (min_weight, max_weight))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_files_by_manufacturers(self, manufacturers: List[str]) -> List[Dict]:
        """Get files containing specific manufacturers"""
        if not manufacturers:
            return []
        
        # Use FTS to find files with matching manufacturers
        placeholders = ','.join('?' * len(manufacturers))
        cursor = self.conn.cursor()
        cursor.execute(f'''
            SELECT DISTINCT f.* FROM files f
            JOIN products p ON f.id = p.file_id
            WHERE p.manufacturer IN ({placeholders})
        ''', manufacturers)
        return [dict(row) for row in cursor.fetchall()]
    
    def search_similar_products(self, query: str, limit: int = 100) -> List[Dict]:
        """Search products using FTS5"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT p.*, name_original as name, rank FROM products_fts
            JOIN products p ON products_fts.rowid = p.id
            WHERE products_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        ''', (query, limit))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM files")
        file_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM products")
        product_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT SUM(total_weight) as total FROM files")
        total_weight = cursor.fetchone()['total'] or 0
        
        return {
            'file_count': file_count,
            'product_count': product_count,
            'total_weight': total_weight
        }
    
    def delete_file(self, file_id: int):
        """Delete file and its products"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
        self.conn.commit()
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
