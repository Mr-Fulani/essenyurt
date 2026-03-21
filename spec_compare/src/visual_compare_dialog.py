"""
Диалоговое окно для визуального сравнения двух спецификаций бок о бок.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QLabel, QSplitter, QHeaderView, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from typing import List, Dict
from rapidfuzz import fuzz

class VisualCompareDialog(QDialog):
    """Окно для визуального сравнения товаров 'Новый' vs 'Архив'"""
    
    def __init__(self, new_products: List[Dict], archive_products: List[Dict], 
                 archive_filename: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Визуальное сравнение: {archive_filename}")
        self.setMinimumSize(1200, 700)
        
        self.new_products = new_products
        self.archive_products = archive_products
        
        # Determine columns for each table separately to prevent empty blanks when column names differ
        new_keys = set()
        for p in self.new_products:
            for k in p.keys():
                if k != 'row_number': new_keys.add(k)
        self.new_columns = sorted(list(new_keys))
        
        arch_keys = set()
        for p in self.archive_products:
            for k in p.keys():
                if k != 'row_number': arch_keys.add(k)
        self.archive_columns = sorted(list(arch_keys))
        
        self.setup_ui()
        self.populate_tables()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Заголовок
        header = QLabel("🔍 Сравнение спецификаций (бок о бок)")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(header)
        
        # Сплиттер для двух таблиц
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Левая панель (Новый файл)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        self.left_label = QLabel("<b>ТЕКУЩИЙ (НОВЫЙ) ФАЙЛ</b>")
        left_layout.addWidget(self.left_label)
        self.new_table = self._create_table(self.new_columns)
        left_layout.addWidget(self.new_table)
        splitter.addWidget(left_widget)
        
        # Правая панель (Архивный файл)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        self.right_label = QLabel(f"<b>АРХИВ: {self.windowTitle().split(': ')[-1]}</b>")
        right_layout.addWidget(self.right_label)
        self.archive_table = self._create_table(self.archive_columns)
        right_layout.addWidget(self.archive_table)
        splitter.addWidget(right_widget)
        
        layout.addWidget(splitter)
        
        # Легенда
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel("🟢 Точное совпадение (100%)"))
        legend_layout.addWidget(QLabel("🟡 Частичное совпадение (>60%)"))
        legend_layout.addWidget(QLabel("⚪️ Уникальная позиция"))
        legend_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # Add legend widget to layout
        legend_widget = QWidget()
        legend_widget.setLayout(legend_layout)
        layout.addWidget(legend_widget)

    def _create_table(self, columns: List[str]) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        if len(columns) > 0:
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.setAlternatingRowColors(True)
        return table

    def populate_tables(self):
        """Заполнение таблиц и выравнивание совпадений по строкам"""
        def get_sig(p):
            parts = []
            # Gather all non-empty values sorted by key to make signature robust
            for k in sorted(p.keys()):
                if k == 'row_number': continue
                val = str(p.get(k, '')).strip().lower()
                if val and val != 'nan':
                    parts.append(val)
            return " ".join(parts)
            
        new_sigs = [get_sig(p) for p in self.new_products]
        arch_sigs = [get_sig(p) for p in self.archive_products]
        
        # 1. Сначала находим все пары
        used_arch = set()
        exact_pairs = []
        partial_pairs = []
        unique_new = []
        
        for p_new, sig_new in zip(self.new_products, new_sigs):
            if not sig_new:
                unique_new.append(p_new)
                continue
                
            best_score = 0
            best_idx = -1
            
            for j, (p_arch, sig_arch) in enumerate(zip(self.archive_products, arch_sigs)):
                if not sig_arch or j in used_arch: continue
                
                if sig_new == sig_arch:
                    best_score = 100
                    best_idx = j
                    break
                    
                score = fuzz.token_set_ratio(sig_new, sig_arch)
                if score > best_score:
                    best_score = score
                    best_idx = j
            
            if best_score == 100:
                exact_pairs.append((p_new, self.archive_products[best_idx], best_score))
                used_arch.add(best_idx)
            elif best_score >= 60:
                partial_pairs.append((p_new, self.archive_products[best_idx], best_score))
                used_arch.add(best_idx)
            else:
                unique_new.append(p_new)
                
        unique_arch = [p for j, p in enumerate(self.archive_products) if j not in used_arch]
        
        # 2. Выстраиваем финальный порядок строк (Точные -> Частичные -> Уникальные Новый -> Уникальные Архив)
        total_rows = len(exact_pairs) + len(partial_pairs) + len(unique_new) + len(unique_arch)
        self.new_table.setRowCount(total_rows)
        self.archive_table.setRowCount(total_rows)
        
        current_row = 0
        
        # Точные совпадения (Зеленые)
        for p_n, p_a, score in exact_pairs:
            self._fill_row(self.new_table, current_row, p_n, self.new_columns, True, False, score)
            self._fill_row(self.archive_table, current_row, p_a, self.archive_columns, True, False, score)
            current_row += 1
            
        # Частичные совпадения (Желтые)
        for p_n, p_a, score in partial_pairs:
            self._fill_row(self.new_table, current_row, p_n, self.new_columns, False, True, score)
            self._fill_row(self.archive_table, current_row, p_a, self.archive_columns, False, True, score)
            current_row += 1
            
        # Уникальные из нового файла (Слева текст, справа пусто)
        for p_n in unique_new:
            self._fill_row(self.new_table, current_row, p_n, self.new_columns, False, False, 0)
            self._fill_empty_row(self.archive_table, current_row, self.archive_columns)
            current_row += 1
            
        # Уникальные из архива (Слева пусто, справа текст)
        for p_a in unique_arch:
            self._fill_empty_row(self.new_table, current_row, self.new_columns)
            self._fill_row(self.archive_table, current_row, p_a, self.archive_columns, False, False, 0)
            current_row += 1

        matches_count = len(exact_pairs)
        partial_count = len(partial_pairs)
        
        # Обновляем заголовки с информацией о количестве
        self.left_label.setText(f"<b>НОВЫЙ ФАЙЛ</b> ({len(self.new_products)} поз., {matches_count} точн., {partial_count} част.)")
        self.right_label.setText(f"<b>АРХИВ</b> ({len(self.archive_products)} поз.)")

    def _fill_empty_row(self, table: QTableWidget, row: int, columns: List[str]):
        for col_idx in range(len(columns)):
            item = QTableWidgetItem("")
            item.setBackground(QColor(40, 40, 40)) # Темный фон для пустых ячеек в Dark Mode
            table.setItem(row, col_idx, item)

    def _fill_row(self, table: QTableWidget, row: int, p: Dict, columns: List[str], exact_match: bool, partial_match: bool, score: float):
        color = None
        if exact_match:
            color = QColor(200, 255, 200) # Green
        elif partial_match:
            color = QColor(255, 255, 200) # Yellow
            
        for col_idx, col_name in enumerate(columns):
            val = p.get(col_name, '')
            if str(val) == 'nan': val = ''
            
            if isinstance(val, float):
                item_text = f"{val:.2f}" if val != int(val) else str(int(val))
            else:
                item_text = str(val)
                
            item = QTableWidgetItem(item_text)
            
            if color:
                item.setBackground(color)
                item.setForeground(QColor(0, 0, 0))
                if score > 0:
                    item.setToolTip(f"Схожесть строк: {score:.1f}%")
            table.setItem(row, col_idx, item)
