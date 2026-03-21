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
                total_amount REAL DEFAULT 0, -- New column
                manufacturers TEXT,  -- JSON array
                brands TEXT,  -- JSON array
                json_snapshot TEXT,  -- Full data as JSON
                file_content BLOB    -- Original file content
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
                unit_price REAL DEFAULT 0, -- New column
                total_price REAL DEFAULT 0, -- New column
                similarity_vector BLOB,  -- Changed from TEXT to BLOB
                FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
            )
        ''')
        
        # Migration: Add price columns if they don't exist
        try:
            cursor.execute("ALTER TABLE files ADD COLUMN total_amount REAL DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Already exists
            
        try:
            cursor.execute("ALTER TABLE products ADD COLUMN unit_price REAL DEFAULT 0")
            cursor.execute("ALTER TABLE products ADD COLUMN total_price REAL DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Already exists

        try:
            cursor.execute("ALTER TABLE files ADD COLUMN file_content BLOB")
        except sqlite3.OperationalError:
            pass  # Already exists

        # Migration: Change similarity_vector to BLOB if it's TEXT
        # This is more complex as SQLite doesn't allow direct column type alteration if data exists.
        # For simplicity, we'll assume new databases will have BLOB and existing ones might need manual migration
        # or a more robust ALTER TABLE approach (e.g., rename, create new, copy, drop old).
        # For now, we'll just ensure the CREATE TABLE uses BLOB.
        # If an existing DB has TEXT, it will continue to use TEXT unless manually migrated.
        # A proper migration would involve:
        # ALTER TABLE products RENAME TO products_old;
        # CREATE TABLE products (... similarity_vector BLOB ...);
        # INSERT INTO products SELECT ... CAST(similarity_vector AS BLOB) ... FROM products_old;
        # DROP TABLE products_old;
        # For this change, we'll rely on the CREATE TABLE IF NOT EXISTS to define BLOB for new DBs.
        # Existing DBs will keep TEXT for similarity_vector unless manually handled.
        
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
    
    def _guess_column(self, product: Dict, names_to_check: List[str]) -> any:
        """Попытка найти значение по примерным названиям колонок"""
        for k, v in product.items():
            if isinstance(k, str) and k != 'row_number':
                k_lower = k.lower()
                if any(name in k_lower for name in names_to_check):
                    return v
        return ''

    def file_exists(self, file_hash: str) -> bool:
        """Check if file already exists in database"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM files WHERE file_hash = ?", (file_hash,))
        return cursor.fetchone() is not None
    
    def add_file(self, filename: str, file_path: str, products_data: List[Dict]) -> int:
        """Add new file with its generic products to database"""
        original_hash = self.compute_file_hash(file_path)
        file_hash = original_hash
        
        counter = 1
        while self.file_exists(file_hash):
            file_hash = f"{original_hash}_{counter}"
            counter += 1
        
        # Read file content for storage
        with open(file_path, 'rb') as f:
            file_content = f.read()
            
        # Улучшенный сбор итогов через эвристику
        def to_float(val):
            try: return float(str(val).replace(',', '.').replace(' ', ''))
            except: return 0.0

        total_weight = sum(to_float(self._guess_column(p, ['вес', 'weight', 'нетто'])) for p in products_data)
        total_items = len(products_data)
        total_amount = sum(to_float(self._guess_column(p, ['стоимо', 'сумма', 'итог', 'total', 'цена'])) for p in products_data)
        
        manufacturers = list(set(str(self._guess_column(p, ['производит', 'изготовит', 'manufacturer'])) for p in products_data if self._guess_column(p, ['производит', 'изготовит', 'manufacturer'])))
        brands = list(set(str(self._guess_column(p, ['бренд', 'марка', 'brand'])) for p in products_data if self._guess_column(p, ['бренд', 'марка', 'brand'])))
        
        # Insert file record
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO files (filename, file_hash, total_weight, total_items, total_amount, manufacturers, brands, json_snapshot, file_content)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            filename, file_hash, total_weight, total_items, total_amount,
            json.dumps(manufacturers, ensure_ascii=False),
            json.dumps(brands, ensure_ascii=False),
            json.dumps(products_data, ensure_ascii=False, default=str),
            file_content
        ))
        
        file_id = cursor.lastrowid
        if file_id is None:
            raise ValueError("Failed to get lastrowid after inserting file")
        
        file_id = int(file_id)
        
        # Insert heuristic products for search index
        for product in products_data:
            name = str(self._guess_column(product, ['наименов', 'название', 'описание', 'name', 'товар']))
            mfr = str(self._guess_column(product, ['производит', 'изготовит']))
            brand = str(self._guess_column(product, ['бренд', 'марка']))
            weight = to_float(self._guess_column(product, ['вес', 'weight']))
            qty = to_float(self._guess_column(product, ['кол', 'qty']))
            u_price = to_float(self._guess_column(product, ['цена за', 'ед']))
            t_price = to_float(self._guess_column(product, ['стоимо', 'сумма']))
            article = str(self._guess_column(product, ['артикул', 'код', 'part']))
            
            cursor.execute('''
                INSERT INTO products (file_id, name_clean, name_original, manufacturer, brand, weight_net, quantity, article, unit_price, total_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                file_id, self._clean_name(name), name, mfr, brand, weight, qty, article, u_price, t_price
            ))
        
        self.conn.commit()
        return file_id
    
    def _clean_name(self, name: str) -> str:
        """Clean product name for better matching"""
        if not name:
            return ''
        name = ' '.join(name.upper().split())
        fillers = ['THE', 'AND', 'OR', 'WITH', 'FOR', 'OF', 'IN', 'ON', 'AT', 'TO']
        words = [w for w in name.split() if w not in fillers]
        return ' '.join(words)
    
    def get_file(self, file_id: int) -> Optional[Dict]:
        """Get file by ID (excluding BLOB content for performance)"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, filename, file_hash, upload_date, total_weight, total_items, total_amount, manufacturers, brands, json_snapshot FROM files WHERE id = ?", (file_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def delete_file(self, file_id: int) -> bool:
        """Delete file and its associated products from the database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM products WHERE file_id = ?", (file_id,))
            cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
            self.conn.commit()
            return True
        except Exception as e:
            import logging
            logging.error(f"Error deleting file {file_id}: {e}")
            self.conn.rollback()
            return False

    def get_file_content(self, file_id: int) -> Optional[Tuple[str, bytes]]:
        """Get filename and raw content for download"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT filename, file_content FROM files WHERE id = ?", (file_id,))
        row = cursor.fetchone()
        if row:
            return row['filename'], row['file_content']
        return None
    
    def get_file_products(self, file_id: int) -> List[Dict]:
        """Get all products generic data for a file"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT json_snapshot FROM files WHERE id = ?", (file_id,))
        row = cursor.fetchone()
        if row and row['json_snapshot']:
            return json.loads(row['json_snapshot'])
        return []
    
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
    
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
