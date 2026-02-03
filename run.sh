
#!/bin/bash

# Fit_system Deployment Script for Ubuntu 24.04
echo "🚀 Starting Fit_system deployment..."

# 1. Update system and install python if missing
sudo apt update && sudo apt install -y python3-venv python3-pip

# 2. Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# 3. Install dependencies
echo "🛠 Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Final checks
echo "✅ Deployment prepared."
echo "🌐 Starting server on http://109.73.193.225:8000"

# 5. Run server (using nohup or screen is recommended for persistence)
# python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
uvicorn backend.main:app --host 0.0.0.0 --port 8000
