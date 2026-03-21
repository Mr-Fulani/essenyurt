@echo off
chcp 65001 >nul
echo ============================================
echo SpecCompare: Запуск программы на Windows
echo ============================================

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ОШИБКА] Python не установлен или не добавлен в PATH.
    echo Пожалуйста, установите Python с сайта python.org и отметьте галочку "Add Python to PATH" во время установки.
    pause
    exit /b
)

if not exist ".venv" (
    echo [ИНФО] Инициализация первого запуска... (создаю виртуальное окружение)
    python -m venv .venv
)

echo [ИНФО] Активация и установка зависимостей...
call .venv\Scripts\activate.bat
pip install -r requirements.txt >nul

echo [ИНФО] Запускаю приложение...
python src\main.py

pause
