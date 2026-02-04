
#!/bin/bash

# Fit_system Deployment Script for Ubuntu 24.04
echo "🚀 Starting Fit_system deployment..."

# 1. Установка зависимостей системы
sudo apt update && sudo apt install -y python3-venv python3-pip

# 2. Виртуальное окружение
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# 3. Установка библиотек
source venv/bin/activate
echo "🛠 Installing Python dependencies..."
pip install -r requirements.txt

# 4. Создание базы данных и папки shops
# Мы запускаем seed_db.py всегда, так как внутри есть проверка на существование данных
echo "🗄 Checking Database status..."
python3 backend/seed_db.py

# 5. Запуск сервера
echo "✅ Readiness check complete."
echo "🌐 Application will be available at http://109.73.193.225:8000"
uvicorn backend.main:app --host 0.0.0.0 --port 8000
