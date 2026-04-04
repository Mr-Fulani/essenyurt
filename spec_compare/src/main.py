import sys
import os

# Добавляем папку src в пути поиска модулей, чтобы программа видела свои части
src_dir = os.path.dirname(os.path.abspath(__file__))
if src_dir not in sys.path:
    sys.path.append(src_dir)

# Фикс для PyInstaller (пути внутри временной папки EXE)
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
    if bundle_dir not in sys.path:
        sys.path.append(bundle_dir)
    os.chdir(bundle_dir)

from PyQt6.QtWidgets import QApplication
# Теперь импорт точно сработает:
from main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
