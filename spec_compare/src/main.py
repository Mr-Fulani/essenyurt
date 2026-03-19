"""
Specification Comparison Tool - Entry Point
Точка входа в приложение сравнения спецификаций
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main_window import main

if __name__ == "__main__":
    main()
