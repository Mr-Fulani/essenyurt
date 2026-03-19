"""
Excel export module for comparison results
Экспорт результатов сравнения в Excel
"""

from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Border, Side, Alignment, PatternFill
from openpyxl.utils import get_column_letter
from datetime import datetime
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResultsExporter:
    """Export comparison results to Excel"""
    
    # Color scheme
    COLORS = {
        'high': 'C6EFCE',      # Green (>80%)
        'medium': 'FFEB9C',    # Yellow (50-80%)
        'low': 'FFC7CE',       # Red (<50%)
        'header': '333333',    # Dark grey
        'subheader': '666666', # Medium grey
    }
    
    def __init__(self):
        self.wb = None
    
    def export_results(self, results: List[Dict], 
                       new_filename: str,
                       output_path: str):
        """
        Export comparison results to Excel file
        
        Args:
            results: List of match results from comparator
            new_filename: Name of the new file being compared
            output_path: Path for output Excel file
        """
        self.wb = Workbook()
        
        # Create summary sheet
        self._create_summary_sheet(results, new_filename)
        
        # Create detailed comparison sheets for top 3
        for i, result in enumerate(results[:3], 1):
            self._create_detail_sheet(result, i)
        
        # Save workbook
        self.wb.save(output_path)
        logger.info(f"Exported results to {output_path}")
    
    def _create_summary_sheet(self, results: List[Dict], new_filename: str):
        """Create summary sheet with ranking"""
        ws = self.wb.active
        ws.title = "Результаты сравнения"
        ws.sheet_view.showGridLines = False
        
        # Title
        ws.merge_cells('B2:L2')
        ws['B2'] = f"Результаты сравнения: {new_filename}"
        ws['B2'].font = Font(size=16, bold=True, color="FFFFFF")
        ws['B2'].fill = PatternFill(start_color=self.COLORS['header'], 
                                     end_color=self.COLORS['header'], fill_type="solid")
        ws['B2'].alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[2].height = 30
        
        # Date
        ws['B3'] = f"Дата сравнения: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        ws['B3'].font = Font(size=10, italic=True, color="666666")
        
        # Headers
        headers = [
            'Место', 'Имя файла архива', 'Дата добавления', 'Общий % схожести',
            '% Совпадения товаров', '% Совпадения производителей', 
            '% Совпадения веса', 'Кол-во позиций', 'Общий вес нетто (кг)',
            'Пересечение товаров', 'Уникальные в новом', 'Уникальные в архиве'
        ]
        
        header_row = 5
        for col, header in enumerate(headers, 2):  # Start from column B
            cell = ws.cell(row=header_row, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color=self.COLORS['subheader'],
                                   end_color=self.COLORS['subheader'], fill_type="solid")
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        
        ws.row_dimensions[header_row].height = 40
        
        # Data rows
        for idx, result in enumerate(results, 1):
            row = header_row + idx
            sim = result['similarity']
            
            # Determine color based on similarity
            total_sim = sim['total']
            if total_sim >= 80:
                fill_color = self.COLORS['high']
            elif total_sim >= 50:
                fill_color = self.COLORS['medium']
            else:
                fill_color = self.COLORS['low']
            
            # Data
            data = [
                idx,  # Место
                result['filename'],  # Имя файла
                result.get('upload_date', ''),  # Дата
                f"{sim['total']}%",  # Общий %
                f"{sim['names']}%",  # % товаров
                f"{sim['manufacturers']}%",  # % производителей
                f"{sim['weight']}%",  # % веса
                result.get('total_items', 0),  # Кол-во позиций
                round(result.get('total_weight', 0), 2),  # Вес нетто
                len(result.get('intersection', [])),  # Пересечение
                len(result.get('unique_new', [])),  # Уникальные новые
                len(result.get('unique_archive', [])),  # Уникальные в архиве
            ]
            
            for col, value in enumerate(data, 2):
                cell = ws.cell(row=row, column=col, value=value)
                cell.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")
                cell.alignment = Alignment(horizontal='center', vertical='center')
                
                # Bold for filename and total similarity
                if col in [3, 5]:  # Filename and total %
                    cell.font = Font(bold=True)
        
        # Adjust column widths
        column_widths = {
            'B': 8,   # Место
            'C': 35,  # Имя файла
            'D': 18,  # Дата
            'E': 15,  # Общий %
            'F': 18,  # % товаров
            'G': 22,  # % производителей
            'H': 15,  # % веса
            'I': 14,  # Кол-во позиций
            'J': 18,  # Вес нетто
            'K': 18,  # Пересечение
            'L': 18,  # Уникальные новые
            'M': 20,  # Уникальные архив
        }
        
        for col, width in column_widths.items():
            ws.column_dimensions[col].width = width
    
    def _create_detail_sheet(self, result: Dict, rank: int):
        """Create detailed comparison sheet for a match"""
        ws = self.wb.create_sheet(title=f"Детали #{rank}")
        ws.sheet_view.showGridLines = False
        
        filename = result['filename']
        sim = result['similarity']
        
        # Title
        ws.merge_cells('B2:H2')
        ws['B2'] = f"Детальное сравнение #{rank}: {filename}"
        ws['B2'].font = Font(size=14, bold=True, color="FFFFFF")
        ws['B2'].fill = PatternFill(start_color=self.COLORS['header'],
                                   end_color=self.COLORS['header'], fill_type="solid")
        ws['B2'].alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[2].height = 25
        
        # Similarity scores
        ws['B4'] = "Оценки схожести:"
        ws['B4'].font = Font(bold=True, size=11)
        
        scores = [
            f"Общая схожесть: {sim['total']}%",
            f"Схожесть наименований: {sim['names']}%",
            f"Схожесть производителей: {sim['manufacturers']}%",
            f"Схожесть веса: {sim['weight']}%",
            f"Схожесть позиций: {sim['items']}%",
            f"Схожесть артикулов: {sim['articles']}%",
        ]
        
        for i, score in enumerate(scores):
            ws.cell(row=5+i, column=2, value=score)
        
        # Intersection table
        row_start = 12
        ws[f'B{row_start}'] = "Совпадающие товары:"
        ws[f'B{row_start}'].font = Font(bold=True, size=11)
        
        headers = ['Наименование (новый)', 'Производитель (новый)', 
                   'Наименование (архив)', 'Производитель (архив)']
        
        for col, header in enumerate(headers, 2):
            cell = ws.cell(row=row_start+1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color=self.COLORS['subheader'],
                                   end_color=self.COLORS['subheader'], fill_type="solid")
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Intersection data
        intersection = result.get('intersection', [])
        for i, item in enumerate(intersection[:50], 2):  # Limit to 50 rows
            row = row_start + i
            new_prod = item.get('new_product', {})
            arch_prod = item.get('archive_product', {})
            
            ws.cell(row=row, column=2, value=new_prod.get('name', ''))
            ws.cell(row=row, column=3, value=new_prod.get('manufacturer', ''))
            ws.cell(row=row, column=4, value=arch_prod.get('name', ''))
            ws.cell(row=row, column=5, value=arch_prod.get('manufacturer', ''))
            
            # Green background for matches
            for col in range(2, 6):
                ws.cell(row=row, column=col).fill = PatternFill(
                    start_color=self.COLORS['high'],
                    end_color=self.COLORS['high'],
                    fill_type="solid"
                )
        
        # Unique to new file
        row_start = row_start + len(intersection) + 4
        if row_start < 60:  # Only if space permits
            ws[f'B{row_start}'] = "Уникальные товары в новом файле:"
            ws[f'B{row_start}'].font = Font(bold=True, size=11)
            
            headers = ['Наименование', 'Производитель', 'Артикул', 'Вес нетто']
            for col, header in enumerate(headers, 2):
                cell = ws.cell(row=row_start+1, column=col, value=header)
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(start_color=self.COLORS['subheader'],
                                       end_color=self.COLORS['subheader'], fill_type="solid")
            
            unique_new = result.get('unique_new', [])
            for i, prod in enumerate(unique_new[:20], 2):
                row = row_start + i
                ws.cell(row=row, column=2, value=prod.get('name', ''))
                ws.cell(row=row, column=3, value=prod.get('manufacturer', ''))
                ws.cell(row=row, column=4, value=prod.get('article', ''))
                ws.cell(row=row, column=5, value=prod.get('weight_net', 0))
                
                # Red background for unique
                for col in range(2, 6):
                    ws.cell(row=row, column=col).fill = PatternFill(
                        start_color=self.COLORS['low'],
                        end_color=self.COLORS['low'],
                        fill_type="solid"
                    )
        
        # Adjust column widths
        ws.column_dimensions['B'].width = 35
        ws.column_dimensions['C'].width = 25
        ws.column_dimensions['D'].width = 35
        ws.column_dimensions['E'].width = 25
    
    def export_single_comparison(self, new_products: List[Dict],
                                  archive_products: List[Dict],
                                  new_filename: str,
                                  archive_filename: str,
                                  output_path: str):
        """
        Export single file-to-file comparison
        
        Args:
            new_products: Products from new file
            archive_products: Products from archive file
            new_filename: New file name
            archive_filename: Archive file name
            output_path: Output path
        """
        self.wb = Workbook()
        ws = self.wb.active
        ws.title = "Сравнение"
        ws.sheet_view.showGridLines = False
        
        # Title
        ws.merge_cells('B2:E2')
        ws['B2'] = f"Сравнение: {new_filename} vs {archive_filename}"
        ws['B2'].font = Font(size=14, bold=True)
        ws['B2'].alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[2].height = 25
        
        # Side-by-side comparison
        headers = ['Новый файл', '', '', 'Архив', '', '']
        subheaders = ['Наименование', 'Производитель', 'Вес', 
                      'Наименование', 'Производитель', 'Вес']
        
        for col, header in enumerate(headers, 2):
            cell = ws.cell(row=4, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color=self.COLORS['header'],
                                   end_color=self.COLORS['header'], fill_type="solid")
            cell.alignment = Alignment(horizontal='center')
        
        ws.merge_cells('B4:D4')
        ws.merge_cells('E4:G4')
        
        for col, subheader in enumerate(subheaders, 2):
            cell = ws.cell(row=5, column=col, value=subheader)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color=self.COLORS['subheader'],
                                   end_color=self.COLORS['subheader'], fill_type="solid")
            cell.alignment = Alignment(horizontal='center')
        
        # Match products and display
        max_rows = max(len(new_products), len(archive_products))
        
        for i in range(max_rows):
            row = 6 + i
            
            if i < len(new_products):
                p = new_products[i]
                ws.cell(row=row, column=2, value=p.get('name', ''))
                ws.cell(row=row, column=3, value=p.get('manufacturer', ''))
                ws.cell(row=row, column=4, value=p.get('weight_net', 0))
            
            if i < len(archive_products):
                p = archive_products[i]
                ws.cell(row=row, column=5, value=p.get('name', ''))
                ws.cell(row=row, column=6, value=p.get('manufacturer', ''))
                ws.cell(row=row, column=7, value=p.get('weight_net', 0))
        
        # Adjust column widths
        ws.column_dimensions['B'].width = 30
        ws.column_dimensions['C'].width = 20
        ws.column_dimensions['D'].width = 12
        ws.column_dimensions['E'].width = 30
        ws.column_dimensions['F'].width = 20
        ws.column_dimensions['G'].width = 12
        
        self.wb.save(output_path)
