# Инструкция по установке и развёртыванию

## Содержание

1. [Быстрый старт (рекомендуется)](#быстрый-старт)
2. [Установка на Windows](#установка-на-windows)
3. [Установка на macOS](#установка-на-macos)
4. [Установка через Docker](#установка-через-docker)
5. [Сборка исполняемого файла](#сборка-исполняемого-файла)
6. [Устранение неполадок](#устранение-неполадок)

---

## Быстрый старт

### Для Windows:
```powershell
# 1. Скачайте и установите Python 3.11+ с https://python.org
# 2. Откройте PowerShell или CMD

git clone <URL_репозитория>
cd spec_compare
pip install -r requirements.txt
cd src
python main.py
```

### Для macOS:
```bash
# 1. Установите Homebrew (если нет): /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
# 2. Установите Python

brew install python@3.11

git clone <URL_репозитория>
cd spec_compare
pip3 install -r requirements.txt
cd src
python3 main.py
```

---

## Установка на Windows

### Шаг 1: Установка Python

1. Перейдите на [python.org](https://www.python.org/downloads/)
2. Скачайте Python 3.11 или новее
3. **Важно!** При установке отметьте галочку:
   - ☑️ "Add Python to PATH"
   - ☑️ "Install pip"

4. Проверьте установку:
```powershell
python --version
pip --version
```

### Шаг 2: Установка Git (опционально)

1. Скачайте Git с [git-scm.com](https://git-scm.com/download/win)
2. Установите с настройками по умолчанию
3. Проверьте:
```powershell
git --version
```

### Шаг 3: Скачивание проекта

**Вариант A: Через Git (рекомендуется)**
```powershell
git clone <URL_репозитория>
cd spec_compare
```

**Вариант B: ZIP-архив**
1. Скачайте архив проекта
2. Распакуйте в удобное место
3. Откройте PowerShell в папке проекта

### Шаг 4: Установка зависимостей

```powershell
# Создание виртуального окружения (рекомендуется)
python -m venv venv

# Активация окружения
venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt
```

### Шаг 5: Запуск

```powershell
cd src
python main.py
```

---

## Установка на macOS

### Шаг 1: Установка Homebrew (если не установлен)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Шаг 2: Установка Python

```bash
brew install python@3.11
```

Проверка:
```bash
python3 --version
pip3 --version
```

### Шаг 3: Установка Qt6 (для GUI)

```bash
brew install qt@6
```

### Шаг 4: Скачивание проекта

**Вариант A: Через Git**
```bash
git clone <URL_репозитория>
cd spec_compare
```

**Вариант B: ZIP-архив**
1. Скачайте и распакуйте архив
2. Откройте Terminal в папке проекта

### Шаг 5: Установка зависимостей

```bash
# Создание виртуального окружения
python3 -m venv venv

# Активация окружения
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
```

### Шаг 6: Запуск

```bash
cd src
python3 main.py
```

---

## Установка через Docker

Docker позволяет изолировать все зависимости и не устанавливать Python на хост-систему.

### Предварительные требования

- Установите [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### Шаг 1: Сборка образа

```bash
cd spec_compare
docker build -t spec-compare .
```

### Шаг 2: Запуск (Windows PowerShell)

```powershell
# Разрешить доступ к X11 (для GUI)
# Установите VcXsrv или Xming X Server

# Запуск контейнера
docker run -it `
  -v ${PWD}/data:/app/data `
  -e DISPLAY=host.docker.internal:0.0 `
  spec-compare
```

### Шаг 2: Запуск (macOS)

```bash
# Установите XQuartz
brew install --cask xquartz

# Запустите XQuartz и разрешите доступ
open -a XQuartz
# В настройках XQuartz: Security → Allow connections from network clients

# Получите IP-адрес
IP=$(ifconfig en0 | grep inet | awk '$1=="inet" {print $2}')
xhost + $IP

# Запуск контейнера
docker run -it \
  -v $(pwd)/data:/app/data \
  -e DISPLAY=$IP:0 \
  spec-compare
```

### Альтернатива: Docker Compose

```bash
# Запуск через docker-compose
docker-compose up
```

---

## Сборка исполняемого файла

### Для распространения среди пользователей без Python

### Windows (.exe)

```powershell
# Установка pyinstaller
pip install pyinstaller

# Сборка
cd spec_compare
python build.py --all --package

# Или вручную:
cd src
pyinstaller --onefile --windowed --name "SpecCompare" main.py

# Результат: dist/SpecCompare.exe
```

### macOS (.app)

```bash
# Установка pyinstaller
pip install pyinstaller

# Сборка
cd spec_compare
python build.py --all --package

# Или вручную:
cd src
pyinstaller --onefile --windowed --name "SpecCompare" main.py

# Результат: dist/SpecCompare
```

### Подпись приложения (macOS)

Если macOS блокирует запуск:
```bash
# Разрешить запуск
xattr -cr dist/SpecCompare

# Или через Системные настройки → Безопасность
```

---

## Устранение неполадок

### Ошибка: "pip не найден"

**Windows:**
```powershell
python -m ensurepip --upgrade
```

**macOS:**
```bash
python3 -m ensurepip --upgrade
```

### Ошибка: "No module named 'PyQt6'"

```bash
pip install PyQt6
```

### Ошибка: "No module named 'sklearn'"

```bash
pip install scikit-learn
```

### Ошибка на macOS: "App can't be opened"

```bash
# Разрешить запуск из неизвестных источников
sudo spctl --master-disable

# Или для конкретного файла
xattr -cr /path/to/SpecCompare
```

### Ошибка: "Failed to load platform plugin"

**Windows:**
```powershell
pip install PyQt6 --upgrade
```

**macOS:**
```bash
brew reinstall qt@6
pip install PyQt6 --upgrade
```

### Ошибка с Excel файлами

```bash
pip install openpyxl xlrd --upgrade
```

### Очистка и переустановка

```bash
# Удалить виртуальное окружение
rm -rf venv  # macOS
rmdir /s venv  # Windows

# Создать заново
python -m venv venv
source venv/bin/activate  # macOS
venv\Scripts\activate  # Windows

# Переустановить зависимости
pip install -r requirements.txt --force-reinstall
```

---

## Проверка установки

После установки проверьте работу:

```bash
cd src
python main.py
```

Должно открыться окно приложения. Попробуйте:
1. Перетащить тестовый файл из `test_files/BVB135.xlsx`
2. Нажать "Сравнить"
3. Проверить результаты

---

## Обновление приложения

### Через Git:
```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

### Вручную:
1. Скачайте новую версию
2. Распакуйте поверх старой
3. Обновите зависимости: `pip install -r requirements.txt --upgrade`

---

## Поддержка

При возникновении проблем:
1. Проверьте версию Python: `python --version` (должна быть 3.11+)
2. Проверьте установленные пакеты: `pip list`
3. Создайте issue с описанием ошибки
