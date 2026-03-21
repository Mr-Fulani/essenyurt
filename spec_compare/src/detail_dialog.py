"""
Detail dialog for viewing comparison results - Универсальная версия
Диалог детального просмотра результатов сравнения
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QHeaderView, QPushButton, QTabWidget,
    QWidget, QGroupBox, QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
import json
from rapidfuzz import fuzz

class DetailDialog(QDialog):
    """Dialog for detailed comparison view"""
    
    def __init__(self, result: dict, parent=None):
        super().__init__(parent)
        self.result = result
        self.setWindowTitle(f"Детальное сравнение: {result['filename']}")
        self.setMinimumSize(1000, 700)
        
        # Получаем данные товаров
        self.new_products = parent.current_new_products if parent and hasattr(parent, 'current_new_products') else []
        self.archive_products = result.get('products', [])
        
        # Determine all unique columns across both files
        all_keys = set()
        for p in self.new_products + self.archive_products:
            for k in p.keys():
                if k != 'row_number':
                    all_keys.add(k)
        self.columns = sorted(list(all_keys))

        self._compute_generic_intersections()
        self.setup_ui()
        
    def _compute_generic_intersections(self):
        def get_sig(p):
            parts = []
            for k in self.columns:
                val = p.get(k, '')
                if isinstance(val, float):
                    val = f"{val:.2f}" if val != int(val) else str(int(val))
                else:
                    val = str(val)
                val = val.strip().lower()
                if val and val != 'nan':
                    parts.append(val)
            return " ".join(parts)
            
        new_sigs = [get_sig(p) for p in self.new_products]
        arch_sigs = [get_sig(p) for p in self.archive_products]
        
        self.intersection = []
        self.partial_matches = []
        self.unique_new = []
        self.unique_archive = []
        
        # Track used archive indices to handle duplicates properly
        used_archive_indices = set()
        
        # Determine matches for new products
        for i, (p_new, sig_new) in enumerate(zip(self.new_products, new_sigs)):
            if not sig_new:
                self.unique_new.append(p_new)
                continue
                
            best_score = 0
            best_arch_idx = -1
            
            for j, (p_arch, sig_arch) in enumerate(zip(self.archive_products, arch_sigs)):
                if not sig_arch or j in used_archive_indices:
                    continue
                    
                if sig_new == sig_arch:
                    best_score = 100
                    best_arch_idx = j
                    break
                    
                score = fuzz.token_set_ratio(sig_new, sig_arch)
                if score > best_score:
                    best_score = score
                    best_arch_idx = j
                    
            if best_score == 100:
                self.intersection.append({'new_product': p_new, 'archive_product': self.archive_products[best_arch_idx]})
                used_archive_indices.add(best_arch_idx)
            elif best_score >= 60:
                self.partial_matches.append({'new_product': p_new, 'archive_product': self.archive_products[best_arch_idx], 'score': best_score})
                used_archive_indices.add(best_arch_idx)
            else:
                self.unique_new.append(p_new)
                
        # Any archive product not used in a 100% match is considered unique to archive
        for j, p_arch in enumerate(self.archive_products):
            if j not in used_archive_indices:
                self.unique_archive.append(p_arch)
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header with similarity scores
        header = QGroupBox("Оценки схожести")
        header_layout = QGridLayout(header)
        
        sim = self.result.get('similarity', {})
        scores = [
            ("Общая схожесть", sim.get('total', 0), True),
            ("Содержимое строк", sim.get('content', 0), False),
            ("Структура колонок", sim.get('columns', 0), False),
        ]
        
        for i, (name, value, is_main) in enumerate(scores):
            label = QLabel(f"{name}:")
            value_label = QLabel(f"{value}%")
            value_label.setFont(QFont("Arial", 12 if is_main else 10, 
                                     QFont.Weight.Bold if is_main else QFont.Weight.Normal))
            
            if value >= 80: value_label.setStyleSheet("color: #2E7D32;")
            elif value >= 50: value_label.setStyleSheet("color: #F57C00;")
            else: value_label.setStyleSheet("color: #C62828;")
            
            header_layout.addWidget(label, i // 3, (i % 3) * 2)
            header_layout.addWidget(value_label, i // 3, (i % 3) * 2 + 1)
        
        layout.addWidget(header)
        
        # Tabs for different views
        tabs = QTabWidget()
        tabs.addTab(self._create_matching_tab(), "Совпадающие товары")
        tabs.addTab(self._create_partial_tab(), "Частично похожие")
        tabs.addTab(self._create_unique_tab(self.unique_new, "Уникальных товаров", QColor(255, 200, 200)), "Уникальные (новый)")
        tabs.addTab(self._create_unique_tab(self.unique_archive, "Отсутствующих товаров", QColor(220, 220, 220)), "Уникальные (архив)")
        layout.addWidget(tabs)
        
        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("background-color: #666; color: white; padding: 8px 20px; border-radius: 4px;")
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
    
    def _create_matching_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        table = QTableWidget()
        headers = [f"{c} (Сверяется)" for c in self.columns]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        if headers:
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.setAlternatingRowColors(True)
        
        table.setRowCount(len(self.intersection))
        for i, item in enumerate(self.intersection):
            new_prod = item.get('new_product', {})
            for col_idx, k in enumerate(self.columns):
                val = new_prod.get(k, '')
                if isinstance(val, float): val = f"{val:.2f}"
                table_item = QTableWidgetItem(str(val))
                table_item.setBackground(QColor(200, 255, 200)) # Pastel Green
                table_item.setForeground(QColor(0, 0, 0))       # Black text
                table.setItem(i, col_idx, table_item)
        
        count_label = QLabel(f"Найдено полных совпадений строк: {len(self.intersection)}")
        count_label.setStyleSheet("color: #2E7D32; font-weight: bold;")
        layout.addWidget(count_label)
        layout.addWidget(table)
        return widget
        
    def _create_partial_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        table = QTableWidget()
        headers = [f"{c} (Новый файл)" for c in self.columns]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        if headers:
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.setAlternatingRowColors(True)
        
        table.setRowCount(len(self.partial_matches))
        for i, item in enumerate(self.partial_matches):
            new_prod = item.get('new_product', {})
            score = item.get('score', 0)
            for col_idx, k in enumerate(self.columns):
                val = new_prod.get(k, '')
                if isinstance(val, float): val = f"{val:.2f}"
                table_item = QTableWidgetItem(str(val))
                table_item.setBackground(QColor(255, 255, 200)) # Yellow
                table_item.setForeground(QColor(0, 0, 0))
                table_item.setToolTip(f"Схожесть с архивом: {score:.1f}%")
                table.setItem(i, col_idx, table_item)
        
        count_label = QLabel(f"Найдено частично похожих строк (>60%): {len(self.partial_matches)}")
        count_label.setStyleSheet("color: #F57C00; font-weight: bold;")
        layout.addWidget(count_label)
        layout.addWidget(table)
        return widget
    
    def _create_unique_tab(self, array: list, prefix: str, color) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        table = QTableWidget()
        table.setColumnCount(len(self.columns))
        table.setHorizontalHeaderLabels(self.columns)
        if self.columns:
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.setAlternatingRowColors(True)
        
        table.setRowCount(len(array))
        for i, prod in enumerate(array):
            for col_idx, k in enumerate(self.columns):
                val = prod.get(k, '')
                if isinstance(val, float): val = f"{val:.2f}"
                table_item = QTableWidgetItem(str(val))
                table_item.setBackground(color)
                table_item.setForeground(QColor(0, 0, 0))
                table.setItem(i, col_idx, table_item)
                
        count_label = QLabel(f"{prefix}: {len(array)}")
        count_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(count_label)
        layout.addWidget(table)
        return widget
