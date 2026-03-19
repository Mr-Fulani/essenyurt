"""
Excel parser module for specification files
Парсинг Excel файлов спецификаций
"""

import pandas as pd
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SpecificationParser:
    """Parser for customs declaration specification files"""
    
    # Column mapping (column letter -> field name)
    COLUMN_MAP = {
        'B': 'name',           # Наименование товара
        'C': 'description',    # Описание
        'D': 'article',        # Артикул
        'F': 'manufacturer',   # Производитель
        'G': 'brand',          # Бренд
        'K': 'quantity',       # Количество
        'N': 'weight_net',     # Вес нетто
        'I': 'country',        # Страна происхождения
    }
    
    # Required columns for validation
    REQUIRED_COLUMNS = ['B', 'D', 'F', 'G', 'K', 'N']
    
    def __init__(self):
        self.errors = []
    
    def parse_file(self, file_path: str) -> List[Dict]:
        """
        Parse Excel specification file
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            List of product dictionaries
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Read Excel file
        try:
            # Try to read "Спецификация" sheet first
            try:
                df = pd.read_excel(file_path, sheet_name='Спецификация', header=None)
                logger.info(f"Read sheet 'Спецификация' from {path.name}")
            except ValueError:
                # Fall back to first sheet
                df = pd.read_excel(file_path, sheet_name=0, header=None)
                logger.info(f"Read first sheet from {path.name}")
        except Exception as e:
            raise ValueError(f"Failed to read Excel file: {e}")
        
        # Validate structure
        self._validate_structure(df)
        
        # Parse products
        products = self._parse_products(df)
        
        logger.info(f"Parsed {len(products)} products from {path.name}")
        return products
    
    def _validate_structure(self, df: pd.DataFrame):
        """Validate Excel file structure"""
        if df.empty:
            raise ValueError("Excel file is empty")
        
        # Check minimum rows (header + at least one data row)
        if len(df) < 3:
            raise ValueError("Excel file has insufficient rows (minimum 3 required)")
        
        # Check required columns exist
        max_col = len(df.columns)
        col_indices = {col: ord(col) - ord('A') for col in self.REQUIRED_COLUMNS}
        
        missing_cols = []
        for col, idx in col_indices.items():
            if idx >= max_col:
                missing_cols.append(col)
        
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
    
    def _parse_products(self, df: pd.DataFrame) -> List[Dict]:
        """Parse product data from DataFrame"""
        products = []
        
        # Data starts from row 3 (index 2, 0-based)
        # Skip header rows
        data_start = 2
        
        for idx in range(data_start, len(df)):
            row = df.iloc[idx]
            
            # Check for end marker (итоговые строки содержат "|||||||")
            first_col_value = str(row.iloc[0]) if len(row) > 0 else ''
            if '|||||||' in first_col_value or 'ИТОГО' in first_col_value.upper():
                break
            
            # Parse product
            product = self._parse_row(row, idx)
            
            # Skip empty rows
            if product.get('name'):
                products.append(product)
        
        return products
    
    def _parse_row(self, row: pd.Series, row_idx: int) -> Dict:
        """Parse single row into product dictionary"""
        product = {
            'row_number': row_idx + 1,  # 1-based row number
            'name': '',
            'description': '',
            'article': '',
            'manufacturer': '',
            'brand': '',
            'quantity': 0,
            'weight_net': 0.0,
            'country': ''
        }
        
        # Column indices (0-based)
        col_indices = {
            'B': 1,   # Наименование
            'C': 2,   # Описание
            'D': 3,   # Артикул
            'F': 5,   # Производитель
            'G': 6,   # Бренд
            'K': 10,  # Количество
            'N': 13,  # Вес нетто
            'I': 8,   # Страна
        }
        
        # Extract values
        try:
            # Наименование (column B)
            if len(row) > col_indices['B']:
                val = row.iloc[col_indices['B']]
                product['name'] = self._clean_string(val)
            
            # Описание (column C)
            if len(row) > col_indices['C']:
                val = row.iloc[col_indices['C']]
                product['description'] = self._clean_string(val)
            
            # Артикул (column D)
            if len(row) > col_indices['D']:
                val = row.iloc[col_indices['D']]
                product['article'] = self._clean_string(val)
            
            # Производитель (column F)
            if len(row) > col_indices['F']:
                val = row.iloc[col_indices['F']]
                product['manufacturer'] = self._clean_string(val)
            
            # Бренд (column G)
            if len(row) > col_indices['G']:
                val = row.iloc[col_indices['G']]
                product['brand'] = self._clean_string(val)
            
            # Количество (column K)
            if len(row) > col_indices['K']:
                val = row.iloc[col_indices['K']]
                product['quantity'] = self._parse_number(val, int)
            
            # Вес нетто (column N)
            if len(row) > col_indices['N']:
                val = row.iloc[col_indices['N']]
                product['weight_net'] = self._parse_number(val, float)
            
            # Страна (column I)
            if len(row) > col_indices['I']:
                val = row.iloc[col_indices['I']]
                product['country'] = self._clean_string(val)
        
        except Exception as e:
            logger.warning(f"Error parsing row {row_idx + 1}: {e}")
        
        return product
    
    def _clean_string(self, value) -> str:
        """Clean string value"""
        if pd.isna(value) or value is None:
            return ''
        s = str(value).strip()
        # Remove extra whitespace
        s = ' '.join(s.split())
        return s
    
    def _parse_number(self, value, num_type):
        """Parse numeric value"""
        if pd.isna(value) or value is None:
            return num_type(0)
        
        try:
            # Handle string values with commas
            if isinstance(value, str):
                value = value.replace(',', '.').replace(' ', '')
                # Extract first number from string
                match = re.search(r'[-+]?[\d.]+', value)
                if match:
                    value = match.group()
                else:
                    return num_type(0)
            
            return num_type(float(value))
        except (ValueError, TypeError):
            return num_type(0)
    
    def get_file_info(self, file_path: str) -> Dict:
        """Get summary info about specification file"""
        products = self.parse_file(file_path)
        
        total_weight = sum(p['weight_net'] for p in products)
        manufacturers = list(set(p['manufacturer'] for p in products if p['manufacturer']))
        brands = list(set(p['brand'] for p in products if p['brand']))
        
        return {
            'filename': Path(file_path).name,
            'product_count': len(products),
            'total_weight': total_weight,
            'manufacturers': manufacturers,
            'brands': brands,
            'products': products
        }


def test_parser():
    """Test parser with sample file"""
    parser = SpecificationParser()
    # Test with a sample file path
    # info = parser.get_file_info("test.xlsx")
    # print(info)


if __name__ == "__main__":
    test_parser()
