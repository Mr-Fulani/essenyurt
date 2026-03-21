"""
Excel parser module for specification files
Парсинг Excel файлов спецификаций - Универсальная версия
"""

import pandas as pd
import re
from pathlib import Path
from typing import List, Dict, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SpecificationParser:
    """Parser for generic specification files"""
    
    def __init__(self):
        self.errors = []
    
    def parse_file(self, file_path: str) -> List[Dict]:
        """
        Parse Excel specification file and extract all columns
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            List of dictionaries, where keys are column headers
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Read Excel file
        try:
            try:
                df = pd.read_excel(file_path, sheet_name='Спецификация', header=None)
                logger.info(f"Read sheet 'Спецификация' from {path.name}")
            except ValueError:
                df = pd.read_excel(file_path, sheet_name=0, header=None)
                logger.info(f"Read first sheet from {path.name}")
        except Exception as e:
            raise ValueError(f"Failed to read Excel file: {e}")
        
        self._validate_structure(df)
        products = self._parse_products(df)
        
        logger.info(f"Parsed {len(products)} products from {path.name}")
        return products
    
    def _validate_structure(self, df: pd.DataFrame):
        """Basic validation to ensure file is not empty"""
        if df.empty:
            raise ValueError("Excel file is empty")
        if len(df) < 2:
            raise ValueError("Excel file has insufficient rows")
    
    def _find_header_row(self, df: pd.DataFrame) -> Tuple[int, List[str]]:
        """Find the row that looks most like a header (most string values)"""
        best_row_idx = 0
        max_strings = 0
        headers = []
        
        # Check first 10 rows to find header
        for idx in range(min(10, len(df))):
            row = df.iloc[idx].dropna().astype(str)
            strings_count = len([x for x in row if len(x.strip()) > 1])
            if strings_count > max_strings:
                max_strings = strings_count
                best_row_idx = idx
        
        # Build clean headers list
        row = df.iloc[best_row_idx]
        for col_idx, val in enumerate(row):
            if pd.isna(val) or str(val).strip() == '' or str(val).strip() == 'nan':
                headers.append(f"Column_{col_idx+1}")
            else:
                # Clean header name
                clean_name = str(val).strip()
                # Ensure uniqueness
                base_name = clean_name
                counter = 1
                while clean_name in headers:
                    clean_name = f"{base_name} ({counter})"
                    counter += 1
                headers.append(clean_name)
                
        return best_row_idx, headers

    def _parse_products(self, df: pd.DataFrame) -> List[Dict]:
        """Parse rows into dictionaries based on found headers"""
        header_row_idx, headers = self._find_header_row(df)
        products = []
        
        for idx in range(header_row_idx + 1, len(df)):
            row = df.iloc[idx]
            
            # Check for end marker or empty row in first column
            first_col_val = str(row.iloc[0]).strip() if len(row) > 0 else ''
            if '|||||||' in first_col_val or 'ИТОГО' in first_col_val.upper():
                break
                
            # Check if completely empty
            if row.isna().all():
                continue
                
            product = { 'row_number': idx + 1 }
            
            has_data = False
            for col_idx, header in enumerate(headers):
                if col_idx < len(row):
                    val = row.iloc[col_idx]
                    if pd.isna(val):
                        val = ''
                    # Try to parse to int/float if possible, otherwise string
                    if isinstance(val, str):
                        val = val.strip()
                        if val.replace('.','',1).replace(',','',1).isdigit():
                            try:
                                num = float(val.replace(',', '.'))
                                val = int(num) if num.is_integer() else num
                            except ValueError:
                                pass
                    if val != '' and str(val) != 'nan':
                        has_data = True
                    product[header] = val
                    
            if has_data:
                products.append(product)
                
        return products
