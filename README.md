
# Fit_system — Идеальный Припуск (MVP)

Система интеллектуального подбора одежды для магазина O'stin (г. Ангарск, ТРЦ «Фестиваль»).

## Стек
- **Backend:** Python (FastAPI), SQLite (SQLAlchemy)
- **Frontend:** React (TypeScript), Tailwind CSS
- **Algorithm:** Proprietary "Ideal Ease" logic

## Установка и запуск

### 1. Бэкенд
```bash
cd backend
python -m venv venv
source venv/bin/activate # или venv\Scripts\activate на Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

### 2. Фронтенд
```bash
npm install
npm run dev
```

## Деплой
Проект настроен для работы с Timeweb Cloud через GitHub Actions или Webhooks. 
База данных `shop.db` инициализируется автоматически при первом запуске бэкенда.
