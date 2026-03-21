"""
Database viewer dialog for managing stored specifications
"""
import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QHeaderView, QPushButton, QMessageBox,
    QWidget
)
from PyQt6.QtCore import Qt

class ContentViewerDialog(QDialog):
    """Dialog to just view raw content of a stored file"""
    def __init__(self, filename: str, products: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Содержимое: {filename}")
        self.setMinimumSize(1000, 700)
        self.products = products
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        info_label = QLabel(f"Всего строк в файле: {len(self.products)}")
        info_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(info_label)
        
        table = QTableWidget()
        
        # Определяем все колонки
        all_keys = set()
        for p in self.products:
            for k in p.keys():
                if isinstance(k, str) and k.lower() != 'row_number':
                    all_keys.add(k)
        columns = sorted(list(all_keys))
        
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setRowCount(len(self.products))
        
        for i, prod in enumerate(self.products):
            for col_idx, k in enumerate(columns):
                val = prod.get(k, '')
                if isinstance(val, float): val = f"{val:.2f}"
                table_item = QTableWidgetItem(str(val))
                table.setItem(i, col_idx, table_item)
                
        table.setAlternatingRowColors(True)
        if columns:
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(table)
        
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        close_btn.setFixedWidth(100)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)


class DatabaseViewerDialog(QDialog):
    """Dialog for viewing and managing all files in database"""
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.main_window = parent
        self.setWindowTitle("Управление базой данных")
        self.setMinimumSize(1100, 700)
        self.files = []
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        header = QLabel("🗄 Обзор базы данных")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header)
        
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Дата загрузки", "Имя файла", "Товаров", "Общий вес (кг)", "Сумма", "Бренды/Производители"
        ])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.itemDoubleClicked.connect(self.view_file)
        layout.addWidget(self.table)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 Обновить")
        self.refresh_btn.clicked.connect(self.load_data)
        btn_layout.addWidget(self.refresh_btn)
        
        self.view_btn = QPushButton("👀 Посмотреть содержимое")
        self.view_btn.clicked.connect(self.view_file)
        self.view_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; border-radius: 4px; padding: 6px 15px;")
        btn_layout.addWidget(self.view_btn)
        
        self.download_btn = QPushButton("💾 Скачать оригинал")
        self.download_btn.clicked.connect(self.download_file)
        self.download_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; border-radius: 4px; padding: 6px 15px;")
        btn_layout.addWidget(self.download_btn)
        
        btn_layout.addStretch()
        
        self.delete_btn = QPushButton("🗑 Удалить файл")
        self.delete_btn.clicked.connect(self.delete_file)
        self.delete_btn.setStyleSheet("background-color: #F44336; color: white; font-weight: bold; border-radius: 4px; padding: 6px 15px;")
        btn_layout.addWidget(self.delete_btn)
        
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
    def load_data(self):
        self.files = self.db.get_all_files()
        self.table.setRowCount(len(self.files))
        
        for i, f in enumerate(self.files):
            id_item = QTableWidgetItem(str(f.get('id', '')))
            
            date_val = f.get('upload_date', '')
            if isinstance(date_val, str) and ' ' in date_val:
                date_val = date_val.split(' ')[0]
            date_item = QTableWidgetItem(str(date_val))
            
            file_item = QTableWidgetItem(f.get('filename', ''))
            
            items_item = QTableWidgetItem(str(f.get('total_items', 0)))
            
            weight = f.get('total_weight', 0)
            weight_item = QTableWidgetItem(f"{weight:,.2f}")
            
            amount = f.get('total_amount', 0)
            amount_item = QTableWidgetItem(f"{amount:,.2f}")
            
            mfrs = ""
            try:
                m1 = json.loads(f.get('manufacturers', '[]'))
                m2 = json.loads(f.get('brands', '[]'))
                combined = [str(x) for x in list(set(m1 + m2)) if x and str(x).lower() != 'nan']
                mfrs = ", ".join(combined[:3])
                if len(combined) > 3: mfrs += "..."
            except:
                pass
            info_item = QTableWidgetItem(mfrs)
            
            self.table.setItem(i, 0, id_item)
            self.table.setItem(i, 1, date_item)
            self.table.setItem(i, 2, file_item)
            self.table.setItem(i, 3, items_item)
            self.table.setItem(i, 4, weight_item)
            self.table.setItem(i, 5, amount_item)
            self.table.setItem(i, 6, info_item)
            
    def _get_selected_file_id(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Внимание", "Выберите файл в таблице")
            return None, None
        return self.files[row]['id'], self.files[row]['filename']

    def view_file(self):
        file_id, filename = self._get_selected_file_id()
        if not file_id: return
        
        products = self.db.get_file_products(file_id)
        if not products:
            QMessageBox.warning(self, "Ошибка", "Не удалось загрузить данные файла или файл пуст.")
            return
            
        dialog = ContentViewerDialog(filename, products, self)
        dialog.exec()
        
    def download_file(self):
        file_id, filename = self._get_selected_file_id()
        if not file_id: return
        
        if self.main_window:
            from export_options_dialog import ExportOptionsDialog
            dialog = ExportOptionsDialog(file_id, self.db, self.main_window)
            dialog.exec()
            
    def delete_file(self):
        file_id, filename = self._get_selected_file_id()
        if not file_id: return
        
        reply = QMessageBox.question(
            self, "Удаление файла",
            f"Вы уверены, что хотите безвозвратно удалить файл:\n{filename}?\n\nЭто действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success = self.db.delete_file(file_id)
            if success:
                QMessageBox.information(self, "Успех", "Файл успешно удален из базы данных.")
                self.load_data()
                if self.main_window:
                    self.main_window.load_stats()
            else:
                QMessageBox.critical(self, "Ошибка", "Произошла ошибка при удалении файла.")
