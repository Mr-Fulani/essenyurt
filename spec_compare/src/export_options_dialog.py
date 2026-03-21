"""
Диалоговое окно выбора опций для экспорта оригинального файла из базы данных.
"""

import os
import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, 
    QPushButton, QLabel, QGroupBox, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from openpyxl import Workbook
from database import Database
from typing import List, Dict

class ExportOptionsDialog(QDialog):
    """Окно выбора параметров пост-обработки перед скачиванием файла"""
    
    def __init__(self, file_id: int, db: Database, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Параметры экспорта оригинала")
        self.setMinimumWidth(450)
        self.file_id = file_id
        self.db = db
        
        # Получаем данные файла
        self.file_info = self.db.get_file(file_id)
        if not self.file_info:
            QMessageBox.critical(self, "Ошибка", "Файл не найден в базе данных")
            self.reject()
            return
            
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        info_label = QLabel(f"<b>Файл:</b> {self.file_info['filename']}<br>"
                           f"<b>Дата загрузки:</b> {self.file_info['upload_date']}")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)
        
        options_group = QGroupBox("Выберите действия по обработке:")
        options_layout = QVBoxLayout(options_group)
        
        self.check_as_is = QCheckBox("Скачать «Как есть» (оригинальный файл из БД)")
        self.check_as_is.setChecked(True)
        self.check_as_is.stateChanged.connect(self.on_as_is_changed)
        options_layout.addWidget(self.check_as_is)
        
        self.check_recalc = QCheckBox("Пересчитать итоги (Сумма и Вес по позициям)")
        self.check_recalc.setEnabled(False)
        options_layout.addWidget(self.check_recalc)
        
        self.check_normalize = QCheckBox("Нормализовать текст (Удалить лишние пробелы)")
        self.check_normalize.setEnabled(False)
        options_layout.addWidget(self.check_normalize)
        
        self.check_cleanup = QCheckBox("Очистка (Удалить пустые строки и дубликаты)")
        self.check_cleanup.setEnabled(False)
        options_layout.addWidget(self.check_cleanup)
        
        layout.addWidget(options_group)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        export_btn = QPushButton("🚀 Экспортировать в Excel")
        export_btn.clicked.connect(self.run_export)
        export_btn.setStyleSheet("background-color: #0066cc; color: white; padding: 10px; font-weight: bold;")
        btn_layout.addWidget(export_btn)
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)

    def on_as_is_changed(self, state):
        """Активация опций обработки только если не 'Как есть'"""
        is_as_is = (state == Qt.CheckState.Checked.value)
        self.check_recalc.setEnabled(not is_as_is)
        self.check_normalize.setEnabled(not is_as_is)
        self.check_cleanup.setEnabled(not is_as_is)
        if is_as_is:
            self.check_recalc.setChecked(False)
            self.check_normalize.setChecked(False)
            self.check_cleanup.setChecked(False)

    def run_export(self):
        """Выполнение экспорта с учетом выбранных фильтров"""
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить файл", self.file_info['filename'], 
            "Excel Files (*.xlsx)"
        )
        
        if not save_path:
            return
            
        try:
            if self.check_as_is.isChecked():
                # Просто выгружаем BLOB
                data = self.db.get_file_content(self.file_id)
                if data and data[1]:
                    with open(save_path, 'wb') as f:
                        f.write(data[1])
                else:
                    raise ValueError("Контент файла отсутствует в БД (старая запись)")
            else:
                # Генерируем новый Excel на основе json_snapshot с обработкой
                self._generate_modified_excel(save_path)
                
            QMessageBox.information(self, "Успех", f"Файл успешно сохранен:\n{save_path}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", str(e))

    def _generate_modified_excel(self, path: str):
        """Генерация Excel из JSON данных с применением фильтров"""
        products = json.loads(self.file_info['json_snapshot'])
        
        def find_key(p, hints):
            for k in p.keys():
                if isinstance(k, str) and any(h in k.lower() for h in hints): return k
            return None
            
        def to_float(val):
            try: return float(str(val).replace(',', '.').replace(' ', ''))
            except: return 0.0

        # 1. Очистка
        if self.check_cleanup.isChecked():
            # Удаляем полностью пустые строки
            products = [p for p in products if any(str(v).strip() for k,v in p.items() if k != 'row_number')]
            # Удаление дубликатов по всем полям
            seen = set()
            unique_products = []
            for p in products:
                sig = "|".join(str(v).strip().lower() for k,v in sorted(p.items()) if k != 'row_number')
                if sig not in seen and sig:
                    unique_products.append(p)
                    seen.add(sig)
            products = unique_products

        # 2. Нормализация (все строковые поля)
        if self.check_normalize.isChecked():
            for p in products:
                for k, v in p.items():
                    if isinstance(v, str) and k != 'row_number':
                        p[k] = ' '.join(v.split()).strip()

        # 3. Пересчет итогов
        if self.check_recalc.isChecked():
            for p in products:
                k_qty = find_key(p, ['кол', 'qty'])
                k_price = find_key(p, ['цена за', 'ед', 'unit_p'])
                k_total = find_key(p, ['стоимо', 'сумма', 'итог', 'цена'])
                
                if k_qty and k_price and k_total:
                    qty = to_float(p.get(k_qty))
                    price = to_float(p.get(k_price))
                    if qty > 0 and price > 0:
                        p[k_total] = qty * price

        # Создаем Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "Спецификация"
        
        if not products:
            ws.append(["Данные отсутствуют"])
            wb.save(path)
            return

        # Заголовки
        headers = list(products[0].keys())
        if 'similarity_vector' in headers: headers.remove('similarity_vector')
        ws.append(headers)
        
        for p in products:
            row = [p.get(h, "") for h in headers]
            ws.append(row)
            
        wb.save(path)
