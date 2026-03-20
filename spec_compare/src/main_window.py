"""
Main GUI window for Specification Comparison Tool
Главное окно приложения сравнения спецификаций
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QGroupBox, QComboBox, QDateEdit,
    QCheckBox, QProgressBar, QSplitter, QTextEdit, QFrame,
    QAbstractItemView, QMenu, QSystemTrayIcon, QStyle
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDate, QMimeData, QSettings
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QAction, QFont

from database import Database
from excel_parser import SpecificationParser
from comparator import SpecificationComparator
from excel_exporter import ResultsExporter


class ComparisonWorker(QThread):
    """Background worker for file comparison"""
    
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished_signal = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, file_path: str, db: Database, 
                 date_from: Optional[str] = None,
                 date_to: Optional[str] = None,
                 limit: Optional[int] = None):
        super().__init__()
        self.file_path = file_path
        self.db = db
        self.date_from = date_from
        self.date_to = date_to
        self.limit = limit
        self.parser = SpecificationParser()
        self.comparator = SpecificationComparator()
    
    def run(self):
        try:
            self.status.emit("Парсинг файла...")
            self.progress.emit(10)
            
            # Parse new file
            new_products = self.parser.parse_file(self.file_path)
            
            if not new_products:
                self.error.emit("Файл не содержит товаров")
                return
            
            self.status.emit(f"Загружено {len(new_products)} товаров")
            self.progress.emit(30)
            
            # Get candidate files from database
            self.status.emit("Поиск кандидатов в базе...")
            
            # Pre-filter by weight range (±30%)
            total_weight = sum(p.get('weight_net', 0) or 0 for p in new_products)
            min_weight = total_weight * 0.7
            max_weight = total_weight * 1.3
            
            weight_candidates = self.db.get_files_by_weight_range(min_weight, max_weight)
            
            # If weight filter returns too few, get all files
            if len(weight_candidates) < 10:
                weight_candidates = self.db.get_all_files(
                    date_from=self.date_from,
                    date_to=self.date_to,
                    limit=self.limit or 1000
                )
            
            self.status.emit(f"Найдено {len(weight_candidates)} кандидатов")
            self.progress.emit(50)
            
            # Load products for each candidate
            self.status.emit("Загрузка данных кандидатов...")
            candidate_files = []
            total_candidates = len(weight_candidates)
            for i, file_info in enumerate(weight_candidates):
                self.status.emit(f"Загрузка кандидата {i+1} из {total_candidates}: {file_info['filename']}")
                products = self.db.get_file_products(file_info['id'])
                file_info['products'] = products
                candidate_files.append(file_info)
                
                progress = 50 + int((i / total_candidates) * 30)
                self.progress_bar_signal = progress # (Hypothetical, wait... using progress.emit below)
                self.progress.emit(progress)
            
            # Compare
            self.status.emit(f"Сравнение с {total_candidates} файлами...")
            results = self.comparator.find_matches(
                new_products, candidate_files, top_n=10
            )
            
            self.progress.emit(100)
            self.status.emit("Готово!")
            self.finished_signal.emit(results)
            
        except Exception as e:
            self.error.emit(str(e))


class DropArea(QFrame):
    """Custom drop area for file drag & drop"""
    
    file_dropped = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        self.setMinimumHeight(120)
        self.setStyleSheet("""
            DropArea {
                background-color: #f0f0f0;
                border: 3px dashed #999;
                border-radius: 10px;
            }
            DropArea[active="true"] {
                background-color: #e6f3ff;
                border-color: #0066cc;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.icon_label = QLabel("📁")
        self.icon_label.setFont(QFont("Arial", 32))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label)
        
        self.text_label = QLabel("Перетащите файл сюда или нажмите для выбора")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setStyleSheet("font-size: 14px; color: #666;")
        layout.addWidget(self.text_label)
        
        self.file_label = QLabel("")
        self.file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_label.setStyleSheet("font-size: 12px; color: #0066cc; font-weight: bold;")
        layout.addWidget(self.file_label)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1:
                file_path = urls[0].toLocalFile()
                if file_path.endswith(('.xlsx', '.xls')):
                    self.setProperty("active", "true")
                    self.style().unpolish(self)
                    self.style().polish(self)
                    event.acceptProposedAction()
    
    def dragLeaveEvent(self, event):
        self.setProperty("active", "false")
        self.style().unpolish(self)
        self.style().polish(self)
    
    def dropEvent(self, event: QDropEvent):
        self.setProperty("active", "false")
        self.style().unpolish(self)
        self.style().polish(self)
        
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.file_label.setText(Path(file_path).name)
            self.file_dropped.emit(file_path)
    
    def mousePressEvent(self, event):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл спецификации", "",
            "Excel Files (*.xlsx *.xls)"
        )
        if file_path:
            self.file_label.setText(Path(file_path).name)
            self.file_dropped.emit(file_path)


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Сравнение спецификаций (таможенные декларации)")
        self.setMinimumSize(1200, 800)
        
        # Initialize components
        self.db = Database()
        self.parser = SpecificationParser()
        self.comparator = SpecificationComparator()
        self.exporter = ResultsExporter()
        self.current_file_path: Optional[str] = None
        self.comparison_results: List = []
        
        self.setup_ui()
        self.load_stats()
    
    def setup_ui(self):
        """Setup user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # === Header ===
        header = QLabel("📊 Сравнение спецификаций")
        header.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)
        
        # === Drop Area ===
        self.drop_area = DropArea()
        self.drop_area.file_dropped.connect(self.on_file_dropped)
        main_layout.addWidget(self.drop_area)
        
        # === Filters ===
        filters_group = QGroupBox("Фильтры")
        filters_layout = QHBoxLayout(filters_group)
        
        # Date range
        filters_layout.addWidget(QLabel("Период с:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addYears(-1))
        filters_layout.addWidget(self.date_from)
        
        filters_layout.addWidget(QLabel("по:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        filters_layout.addWidget(self.date_to)
        
        # Limit
        filters_layout.addWidget(QLabel("Лимит:"))
        self.limit_combo = QComboBox()
        self.limit_combo.addItems(["Все", "Последние 10", "Последние 50", 
                                   "Последние 100", "Последние 500"])
        self.limit_combo.setCurrentIndex(3)  # Default: 100
        filters_layout.addWidget(self.limit_combo)
        
        # All files checkbox
        self.all_files_check = QCheckBox("Все файлы (игнорировать даты)")
        filters_layout.addWidget(self.all_files_check)
        
        filters_layout.addStretch()
        main_layout.addWidget(filters_group)
        
        # === Progress ===
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Готов к работе")
        self.status_label.setStyleSheet("font-style: italic;")
        progress_layout.addWidget(self.status_label)
        
        main_layout.addLayout(progress_layout)
        
        # === Summary Area ===
        self.summary_group = QGroupBox("Итоги сравнения")
        self.summary_group.setVisible(False)
        summary_layout = QVBoxLayout(self.summary_group)
        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("font-size: 14px; font-weight: 500; line-height: 1.5; padding: 5px;")
        summary_layout.addWidget(self.summary_label)
        main_layout.addWidget(self.summary_group)
        
        # === Results Table ===
        results_group = QGroupBox("Результаты сравнения")
        results_layout = QVBoxLayout(results_group)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(9)
        self.results_table.setHorizontalHeaderLabels([
            "Место", "Файл", "Дата", "Схожесть", "Товары", 
            "Производители", "Вес", "Позиций", "Вес нетто"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(self.show_context_menu)
        results_layout.addWidget(self.results_table)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        self.export_btn = QPushButton("📥 Экспорт в Excel")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_results)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #ccc; }
        """)
        btn_layout.addWidget(self.export_btn)
        
        self.detail_btn = QPushButton("📋 Детальное сравнение")
        self.detail_btn.setEnabled(False)
        self.detail_btn.clicked.connect(self.show_details)
        btn_layout.addWidget(self.detail_btn)
        
        btn_layout.addStretch()
        
        self.compare_btn = QPushButton("🔍 Сравнить")
        self.compare_btn.setEnabled(False)
        self.compare_btn.clicked.connect(self.start_comparison)
        self.compare_btn.setStyleSheet("""
            QPushButton {
                background-color: #0066cc;
                color: white;
                padding: 10px 30px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #0052a3; }
        """)
        btn_layout.addWidget(self.compare_btn)
        
        results_layout.addLayout(btn_layout)
        main_layout.addWidget(results_group)
        
        # === Stats Bar ===
        self.db_stats_label = QLabel("База данных: 0 файлов | 0 товаров")
        self.db_stats_label.setStyleSheet("font-size: 11px;")
        self.db_stats_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        main_layout.addWidget(self.db_stats_label)
        
        # === Menu Bar ===
        self.setup_menu()
    
    def setup_menu(self):
        """Setup menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("Файл")
        
        open_action = QAction("Открыть файл...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        export_action = QAction("Экспорт результатов...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_results)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Выход", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Database menu
        db_menu = menubar.addMenu("База данных")
        
        import_action = QAction("Импорт файла в базу...", self)
        import_action.triggered.connect(self.import_file)
        db_menu.addAction(import_action)
        
        stats_action = QAction("Статистика", self)
        stats_action.triggered.connect(self.show_stats)
        db_menu.addAction(stats_action)
        
        # Help menu
        help_menu = menubar.addMenu("Справка")
        
        about_action = QAction("О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def load_stats(self):
        """Load and display database statistics"""
        stats = self.db.get_stats()
        self.db_stats_label.setText(
            f"📁 База данных: {stats['file_count']:,} файлов | "
            f"{stats['product_count']:,} товаров | "
            f"Общий вес: {stats['total_weight']:,.2f} кг"
        )
    
    def on_file_dropped(self, file_path: str):
        """Handle file drop"""
        self.current_file_path = file_path
        self.compare_btn.setEnabled(True)
        self.status_label.setText(f"Выбран файл: {Path(file_path).name}")
    
    def open_file_dialog(self):
        """Open file dialog"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл спецификации", "",
            "Excel Files (*.xlsx *.xls)"
        )
        if file_path:
            self.on_file_dropped(file_path)
    
    def start_comparison(self):
        """Start comparison in background thread"""
        if not self.current_file_path:
            return
        
        # Get filter values
        date_from = None
        date_to = None
        limit = None
        
        if not self.all_files_check.isChecked():
            date_from = self.date_from.date().toString("yyyy-MM-dd")
            date_to = self.date_to.date().toString("yyyy-MM-dd")
        
        limit_text = self.limit_combo.currentText()
        if "10" in limit_text:
            limit = 10
        elif "50" in limit_text:
            limit = 50
        elif "100" in limit_text:
            limit = 100
        elif "500" in limit_text:
            limit = 500
        
        # Start worker thread
        self.worker = ComparisonWorker(
            self.current_file_path, self.db,
            date_from, date_to, limit
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.status.connect(self.update_status)
        self.worker.finished_signal.connect(self.on_comparison_finished)
        self.worker.error.connect(self.on_comparison_error)
        
        self.progress_bar.setVisible(True)
        self.compare_btn.setEnabled(False)
        self.worker.start()
    
    def update_progress(self, value: int):
        """Update progress bar"""
        self.progress_bar.setValue(value)
    
    def update_status(self, message: str):
        """Update status label"""
        self.status_label.setText(message)
    
    def on_comparison_finished(self, results: List):
        """Handle comparison completion"""
        self.comparison_results = results
        self.display_results(results)
        self.export_btn.setEnabled(True)
        self.detail_btn.setEnabled(True)
        self.compare_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # Build summary text
        filename = Path(self.current_file_path).name
        best_match = results[0]['similarity']['total'] if results else 0
        candidates_count = self.worker.limit or "все" if not self.worker.date_from else "отфильтрованные"
        # We can actually pass the number of candidates from the worker, but for now:
        db_stats = self.db.get_stats()
        
        summary_text = (
            f"✅ <b>Файл проанализирован:</b> {filename}<br>"
            f"📊 <b>Результат:</b> Поиск выполнен по {db_stats['file_count']} файлам в базе данных.<br>"
        )
        
        if results:
            summary_text += f"🔍 <b>Найдено совпадений:</b> {len(results)}. Максимальное сходство: <b>{best_match}%</b>."
        else:
            summary_text += "🔍 <b>Совпадений не найдено.</b> Текущий файл добавлен в базу для будущих сравнений."
            
        self.summary_label.setText(summary_text)
        self.summary_group.setVisible(True)
        
        # Add file to database
        try:
            products = self.parser.parse_file(self.current_file_path)
            self.db.add_file(filename, self.current_file_path, products)
            self.load_stats()
        except ValueError as e:
            # File already exists, ignore
            pass
        except Exception as e:
            print(f"Error adding file to DB: {e}")
    
    def on_comparison_error(self, error: str):
        """Handle comparison error"""
        QMessageBox.critical(self, "Ошибка", f"Ошибка при сравнении:\n{error}")
        self.compare_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("")
    
    def display_results(self, results: List):
        """Display results in table"""
        self.results_table.setRowCount(len(results))
        
        for i, result in enumerate(results):
            sim = result['similarity']
            
            # Color based on similarity
            total_sim = sim['total']
            if total_sim >= 80:
                color = "#C6EFCE"  # Green
            elif total_sim >= 50:
                color = "#FFEB9C"  # Yellow
            else:
                color = "#FFC7CE"  # Red
            
            items = [
                (i + 1, None),  # Место
                (result['filename'], None),  # Файл
                (result.get('upload_date', ''), None),  # Дата
                (f"{sim['total']}%", color),  # Схожесть
                (f"{sim['names']}%", None),  # Товары
                (f"{sim['manufacturers']}%", None),  # Производители
                (f"{sim['weight']}%", None),  # Вес
                (result.get('total_items', 0), None),  # Позиций
                (f"{result.get('total_weight', 0):.2f}", None),  # Вес нетто
            ]
            
            for col, (value, bg_color) in enumerate(items):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if bg_color:
                    item.setBackground(Qt.GlobalColor.green if total_sim >= 80 
                                      else Qt.GlobalColor.yellow if total_sim >= 50 
                                      else Qt.GlobalColor.red)
                self.results_table.setItem(i, col, item)
        
        self.results_table.resizeColumnsToContents()
    
    def export_results(self):
        """Export results to Excel"""
        if not self.comparison_results:
            return
        
        output_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить результаты", 
            f"comparison_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if output_path:
            try:
                filename = Path(self.current_file_path).name
                self.exporter.export_results(
                    self.comparison_results, filename, output_path
                )
                QMessageBox.information(
                    self, "Успех", 
                    f"Результаты сохранены:\n{output_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Ошибка", 
                    f"Ошибка при экспорте:\n{str(e)}"
                )
    
    def show_details(self):
        """Show detailed comparison for selected row"""
        current_row = self.results_table.currentRow()
        if current_row < 0 or current_row >= len(self.comparison_results):
            QMessageBox.information(self, "Информация", "Выберите строку для просмотра деталей")
            return
        
        result = self.comparison_results[current_row]
        
        # Create detail dialog
        from detail_dialog import DetailDialog
        dialog = DetailDialog(result, self)
        dialog.exec()
    
    def show_context_menu(self, position):
        """Show context menu for table"""
        menu = QMenu()
        
        view_action = menu.addAction("Просмотреть детали")
        export_action = menu.addAction("Экспортировать эту запись")
        
        action = menu.exec(self.results_table.viewport().mapToGlobal(position))
        
        if action == view_action:
            self.show_details()
        elif action == export_action:
            self.export_single_result()
    
    def export_single_result(self):
        """Export single result"""
        current_row = self.results_table.currentRow()
        if current_row < 0:
            return
        
        result = self.comparison_results[current_row]
        output_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить сравнение",
            f"comparison_{result['filename']}.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if output_path:
            try:
                self.exporter.export_results([result], 
                    Path(self.current_file_path).name, output_path)
                QMessageBox.information(self, "Успех", "Сохранено!")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))
    
    def import_file(self):
        """Import file to database without comparison"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл для импорта", "",
            "Excel Files (*.xlsx *.xls)"
        )
        
        if file_path:
            try:
                filename = Path(file_path).name
                products = self.parser.parse_file(file_path)
                file_id = self.db.add_file(filename, file_path, products)
                self.load_stats()
                QMessageBox.information(
                    self, "Успех", 
                    f"Файл '{filename}' импортирован\n"
                    f"Товаров: {len(products)}"
                )
            except ValueError as e:
                QMessageBox.warning(self, "Внимание", str(e))
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))
    
    def show_stats(self):
        """Show database statistics"""
        stats = self.db.get_stats()
        
        # Get recent files
        recent = self.db.get_all_files(limit=10)
        recent_text = "\n".join([
            f"  • {f['filename']} ({f['upload_date']})" 
            for f in recent
        ])
        
        QMessageBox.information(
            self, "Статистика базы данных",
            f"📊 Общая статистика:\n"
            f"  Файлов: {stats['file_count']:,}\n"
            f"  Товаров: {stats['product_count']:,}\n"
            f"  Общий вес: {stats['total_weight']:,.2f} кг\n\n"
            f"📁 Последние 10 файлов:\n{recent_text}"
        )
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self, "О программе",
            "<h2>Сравнение спецификаций</h2>"
            "<p>Версия: 1.0.0</p>"
            "<p>Программа для сравнения спецификаций товаров "
            "в таможенных декларациях.</p>"
            "<p>Алгоритм сравнения:</p>"
            "<ul>"
            "<li>35% - Схожесть наименований</li>"
            "<li>25% - Схожесть производителей</li>"
            "<li>20% - Схожесть веса</li>"
            "<li>15% - Схожесть позиций</li>"
            "<li>5% - Схожесть артикулов</li>"
            "</ul>"
        )
    
    def closeEvent(self, event):
        """Handle window close"""
        self.db.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Set application font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
