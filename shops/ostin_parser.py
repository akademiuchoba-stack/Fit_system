#!/usr/bin/env python3
"""
shops/ostin_parser.py

Запускается кнопкой "Обновить базу" из /admin.
Обновляет shops/shop.db (таблица garments Fit_system).
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Dict, List

# --- НАСТРОЙКИ ---
OSTIN_STORE_ID_ANGARSK = 4219
TARGET_ITEMS_PER_CATEGORY = 10

categories: Dict[str, Dict[str, List[str]]] = {
    "women": {
        "pants": ["брюки"],
        "jeans": ["джинсы"],
        "skirts": ["юбки"],
        "shirts": ["рубашки"],
        "tshirts": ["футболки"],
        "blouses": ["блузки"],
        "dresses": ["платья"],
        "jackets": ["куртки", "пуховики", "пальто"],
        "sweaters": ["свитеры", "джемперы", "кардиганы"],
        "hoodies": ["худи", "свитшоты"],
        "shorts": ["шорты"],
    },
    "men": {
        "pants": ["брюки"],
        "jeans": ["джинсы"],
        "shirts": ["рубашки"],
        "tshirts": ["футболки", "поло"],
        "jackets": ["куртки", "пуховики", "пальто"],
        "sweaters": ["свитеры", "джемперы", "кардиганы"],
        "hoodies": ["худи", "свитшоты"],
        "shorts": ["шорты"],
    },
}


def harvest_and_upsert(store_id: int, per_category: int, cats: dict) -> int:
    """
    Сюда ты вставишь свой реальный парсер.
    Пока — просто проверка подключения к БД.
    """

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from backend import database, models

    models.Base.metadata.create_all(bind=database.engine)

    with database.SessionLocal() as db:
        count = db.query(models.Garment).count()

    print(f"[parser] DB accessible. Current garments: {count}")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    args = parser.parse_args()

    print(f"[parser] Using DB: {args.db}")
    print(f"[parser] Store ID: {OSTIN_STORE_ID_ANGARSK}")
    print(f"[parser] Limit per category: {TARGET_ITEMS_PER_CATEGORY}")

    updated = harvest_and_upsert(
        store_id=OSTIN_STORE_ID_ANGARSK,
        per_category=TARGET_ITEMS_PER_CATEGORY,
        cats=categories,
    )

    print(f"[parser] Done. Updated: {updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
