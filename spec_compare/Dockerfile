# Dockerfile for Specification Comparison Tool
# Сборка: docker build -t spec-compare .
# Запуск: docker run -v $(pwd)/data:/app/data -v /tmp/.X11-unix:/tmp/.X11-unix -e DISPLAY=$DISPLAY spec-compare

FROM python:3.11-slim

# Установка системных зависимостей для GUI и Excel
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libqt6widgets6 \
    libqt6gui6 \
    libqt6core6 \
    qt6-base-dev \
    x11-apps \
    && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /app

# Копирование requirements и установка Python-зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY src/ ./src/
COPY test_files/ ./test_files/

# Переменные окружения для Qt
ENV QT_QPA_PLATFORM=xcb
ENV PYTHONPATH=/app

# Точка входа
CMD ["python", "src/main.py"]
