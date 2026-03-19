"""
Detail dialog for viewing comparison results
Диалог детального просмотра результатов сравнения
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QHeaderView, QPushButton, QTabWidget,
    QWidget, QGroupBox, QGridLayout, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class DetailDialog(QDialog):
    """Dialog for detailed comparison view"""
    
    def __init__(self, result: dict, parent=None):
        super().__init__(parent)
        self.result = result
        self.setWindowTitle(f"Детальное сравнение: {result['filename']}")
        self.setMinimumSize(1000, 700)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header with similarity scores
        header = QGroupBox("Оценки схожести")
        header_layout = QGridLayout(header)
        
        sim = self.result['similarity']
        scores = [
            ("Общая схожесть", sim['total'], True),
            ("Наименования", sim['names'], False),
            ("Производители", sim['manufacturers'], False),
            ("Вес", sim['weight'], False),
            ("Позиции", sim['items'], False),
            ("Артикулы", sim['articles'], False),
        ]
        
        for i, (name, value, is_main) in enumerate(scores):
            label = QLabel(f"{name}:")
            value_label = QLabel(f"{value}%")
            value_label.setFont(QFont("Arial", 12 if is_main else 10, 
                                     QFont.Weight.Bold if is_main else QFont.Weight.Normal))
            
            # Color based on value
            if value >= 80:
                value_label.setStyleSheet("color: #2E7D32;")
            elif value >= 50:
                value_label.setStyleSheet("color: #F57C00;")
            else:
                value_label.setStyleSheet("color: #C62828;")
            
            header_layout.addWidget(label, i // 3, (i % 3) * 2)
            header_layout.addWidget(value_label, i // 3, (i % 3) * 2 + 1)
        
        layout.addWidget(header)
        
        # Tabs for different views
        tabs = QTabWidget()
        
        # Tab 1: Matching products
        tabs.addTab(self._create_matching_tab(), "Совпадающие товары")
        
        # Tab 2: Unique to new file
        tabs.addTab(self._create_unique_new_tab(), "Уникальные (новый)")
        
        # Tab 3: Unique to archive
        tabs.addTab(self._create_unique_archive_tab(), "Уникальные (архив)")
        
        layout.addWidget(tabs)
        
        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #555; }
        """)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
    
    def _create_matching_tab(self) -> QWidget:
        """Create tab for matching products"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "Наименование (новый)", "Производитель (новый)", "Вес (новый)",
            "Наименование (архив)", "Производитель (архив)", "Вес (архив)"
        ])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        table.setAlternatingRowColors(True)
        
        intersection = self.result.get('intersection', [])
        table.setRowCount(len(intersection))
        
        for i, item in enumerate(intersection):
            new_prod = item.get('new_product', {})
            arch_prod = item.get('archive_product', {})
            
            items = [
                new_prod.get('name', ''),
                new_prod.get('manufacturer', ''),
                f"{new_prod.get('weight_net', 0):.2f}",
                arch_prod.get('name', ''),
                arch_prod.get('manufacturer', ''),
                f"{arch_prod.get('weight_net', 0):.2f}",
            ]
            
            for col, value in enumerate(items):
                table_item = QTableWidgetItem(str(value))
                table_item.setBackground(Qt.GlobalColor.green)
                table.setItem(i, col, table_item)
        
        count_label = QLabel(f"Найдено совпадений: {len(intersection)}")
        count_label.setStyleSheet("color: #2E7D32; font-weight: bold;")
        layout.addWidget(count_label)
        layout.addWidget(table)
        
        return widget
    
    def _create_unique_new_tab(self) -> QWidget:
        """Create tab for products unique to new file"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels([
            "Наименование", "Производитель", "Артикул", "Количество", "Вес нетто"
        ])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.setAlternatingRowColors(True)
        
        unique_new = self.result.get('unique_new', [])
        table.setRowCount(len(unique_new))
        
        for i, prod in enumerate(unique_new):
            items = [
                prod.get('name', ''),
                prod.get('manufacturer', ''),
                prod.get('article', ''),
                str(prod.get('quantity', 0)),
                f"{prod.get('weight_net', 0):.2f}",
            ]
            
            for col, value in enumerate(items):
                table_item = QTableWidgetItem(str(value))
                table_item.setBackground(Qt.GlobalColor.red)
                table.setItem(i, col, table_item)
        
        count_label = QLabel(f"Уникальных товаров: {len(unique_new)}")
        count_label.setStyleSheet("color: #C62828; font-weight: bold;")
        layout.addWidget(count_label)
        layout.addWidget(table)
        
        return widget
    
    def _create_unique_archive_tab(self) -> QWidget:
        """Create tab for products unique to archive"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels([
            "Наименование", "Производитель", "Артикул", "Количество", "Вес нетто"
        ])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.setAlternatingRowColors(True)
        
        unique_archive = self.result.get('unique_archive', [])
        table.setRowCount(len(unique_archive))
        
        for i, prod in enumerate(unique_archive):
            items = [
                prod.get('name', ''),
                prod.get('manufacturer', ''),
                prod.get('article', ''),
                str(prod.get('quantity', 0)),
                f"{prod.get('weight_net', 0):.2f}",
            ]
            
            for col, value in enumerate(items):
                table_item = QTableWidgetItem(str(value))
                table_item.setBackground(Qt.GlobalColor.yellow)
                table.setItem(i, col, table_item)
        
        count_label = QLabel(f"Уникальных товаров в архиве: {len(unique_archive)}")
        count_label.setStyleSheet("color: #F57C00; font-weight: bold;")
        layout.addWidget(count_label)
        layout.addWidget(table)
        
        return widget
