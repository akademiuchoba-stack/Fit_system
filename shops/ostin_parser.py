#!/usr/bin/env python3
"""
shops/ostin_parser.py

Запускается из админки.
1) Парсит каталог O'stin (цены, названия).
2) Обогащает данные через Lamoda (Vendor Code, биометрия модели, состав).
3) Сохраняет в БД (таблица garments), упаковывая данные для Fit-алгоритма в поле metrics.

ВАЖНО для совместимости с backend:
- Garment.metrics ДОЛЖНО быть словарём по размерам: {"S": {...}, "M": {...}}
- Даже если реальных промеров нет, мы сохраняем 1 "виртуальный" размер (например "M"),
  чтобы /api/calculate не ломался и logic.py мог оценить промеры по model_metrics+model_size.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import random
import json
import re
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Any

# --- НАСТРОЙКА ОКРУЖЕНИЯ ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend import database, models  # noqa: E402

# --- КОНФИГУРАЦИЯ ---
OSTIN_STORE_ID_ANGARSK = 4219
LIMIT_PER_CATEGORY = 10  # как ты просил

# Маппинг: внутренняя категория -> slug на сайте O'stin
CATEGORY_URLS = {
    # women
    "women_pants": "zhenshchinam/odezhda/bryuki",
    "women_jeans": "zhenshchinam/odezhda/dzhinsy",
    "women_skirts": "zhenshchinam/odezhda/yubki",
    "women_dresses": "zhenshchinam/odezhda/platya-i-sarafany",
    "women_shirts": "zhenshchinam/odezhda/rubashki",
    "women_tshirts": "zhenshchinam/odezhda/futbolki-i-maiki",
    "women_blouses": "zhenshchinam/odezhda/bluzki-i-rubashki",
    "women_jackets": "zhenshchinam/odezhda/verkhnyaya-odezhda",

    # men
    "men_pants": "muzhchinam/odezhda/bryuki",
    "men_jeans": "muzhchinam/odezhda/dzhinsy",
    "men_shirts": "muzhchinam/odezhda/rubashki",
    "men_tshirts": "muzhchinam/odezhda/futbolki-i-mayki",
    "men_jackets": "muzhchinam/odezhda/verkhnyaya-odezhda",
}

logging.basicConfig(level=logging.INFO, format='[parser] %(message)s')
logger = logging.getLogger(__name__)


# ==========================================
# 1. КЛАССЫ ПАРСЕРА
# ==========================================

class OstinCatalog:
    """Сбор базовой инфо с сайта O'stin"""
    BASE_URL = "https://ostin.com"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }

    def fetch_items(self, slug: str, limit: int) -> List[Dict]:
        items: List[Dict] = []
        url = f"{self.BASE_URL}/catalog/{slug}"
        logger.info(f"O'stin scan: {url}")

        try:
            resp = self.session.get(url, timeout=20)
            if resp.status_code != 200:
                return []

            soup = BeautifulSoup(resp.text, 'html.parser')
            cards = soup.find_all('div', class_=re.compile('ProductCard_card'))

            for c in cards[:limit]:
                try:
                    link_tag = c.find('a', href=True)
                    title_tag = c.find('div', class_=re.compile('ProductCard_title'))
                    price_tag = c.find('div', class_=re.compile('ProductCard_price'))

                    if link_tag and title_tag:
                        price_str = price_tag.get_text(strip=True) if price_tag else "0"
                        price = float(re.sub(r'[^\d]', '', price_str) or 0)

                        items.append({
                            'title': title_tag.get_text(strip=True),
                            'url': self.BASE_URL + link_tag['href'],
                            'price': price
                        })
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Error fetching O'stin: {e}")

        return items

    def check_stock(self) -> bool:
        # Эмуляция проверки стока в Ангарске (API закрыт)
        return random.random() > 0.2


class LamodaEnricher:
    """Извлечение Vendor Code и параметров модели через Lamoda"""
    SEARCH_URL = "https://www.lamoda.ru/catalogsearch/result/"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9',
        }

    def enrich(self, title: str) -> Optional[Dict]:
        try:
            params = {'q': f"O'stin {title}", 'submit': 'y'}
            resp = self.session.get(self.SEARCH_URL, params=params, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')

            link = soup.find('a', class_=re.compile('ProductCard-link'))
            if not link:
                return None

            product_url = "https://www.lamoda.ru" + link['href']

            time.sleep(random.uniform(1.5, 3.0))
            page_resp = self.session.get(product_url, timeout=10)

            data = self._extract_json(page_resp.text)
            if not data:
                return None

            return self._parse_json(data, product_url)

        except Exception as e:
            logger.warning(f"Lamoda enrich failed: {e}")
            return None

    def _extract_json(self, html: str) -> Optional[Dict]:
        m = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html, re.DOTALL)
        return json.loads(m.group(1)) if m else None

    def _parse_json(self, data: Dict, url: str) -> Dict:
        payload = data.get('payload', {}).get('product', {})
        if not payload:
            payload = data.get('state', {}).get('product', {}).get('result', {})

        vendor_code = payload.get('model', {}).get('vendor_code')
        if not vendor_code or str(vendor_code).startswith("MP00"):
            vendor_code = f"OST-{abs(hash(url))}"

        img = ""
        gallery = payload.get('gallery', [])
        if gallery:
            src = gallery[0].get('image') or gallery[0].get('src')
            if src:
                img = f"https:{src}" if src.startswith('//') else src

        # Пакет для Fit-алгоритма (будет вложен в metrics["M"])
        metrics_pack = {
            "model_metrics": {},
            "model_size": None,
            "elastane_pct": 0,
            "fabric": "",
            "fit_profile": "regular"
        }

        for attr in payload.get('attributes', []):
            lbl = (attr.get('label', '') or '').lower()
            val = (attr.get('value', '') or '').lower()

            if 'параметры модели' in lbl:
                p = val.split('-')
                if len(p) >= 3:
                    try:
                        metrics_pack["model_metrics"] = {
                            "chest": int(p[0]),
                            "waist": int(p[1]),
                            "hips": int(p[2])
                        }
                    except Exception:
                        pass
            elif 'рост модели' in lbl:
                h = re.search(r'\d+', val)
                if h:
                    metrics_pack["model_metrics"]["height"] = int(h.group())
            elif 'размер' in lbl and 'модел' in lbl:
                metrics_pack["model_size"] = val.upper()
            elif 'состав' in lbl:
                metrics_pack["fabric"] = val
                el = re.search(r'(\d+)\s*[%]*\s*эластан', val)
                if el:
                    metrics_pack["elastane_pct"] = int(el.group(1))

        title_lower = (payload.get('title', '') or '').lower()
        if 'oversize' in title_lower or 'оверсайз' in title_lower:
            metrics_pack["fit_profile"] = "oversize"
        elif 'slim' in title_lower or 'притален' in title_lower:
            metrics_pack["fit_profile"] = "slim"

        return {
            "sku": vendor_code,
            "image_url": img,
            "metrics": metrics_pack
        }


# ==========================================
# 2. ЛОГИКА ОБНОВЛЕНИЯ БД
# ==========================================

def harvest_and_upsert(store_id: int, per_category: int, cats: dict) -> int:
    """
    Основной процесс обновления.
    Использует ORM backend.models для записи.
    """

    models.Base.metadata.create_all(bind=database.engine)

    ostin = OstinCatalog()
    lamoda = LamodaEnricher()

    total_processed = 0

    with database.SessionLocal() as db:
        for cat_name, ostin_slug in CATEGORY_URLS.items():
            logger.info(f"--- Категория: {cat_name} ---")

            candidates = ostin.fetch_items(ostin_slug, per_category)

            for item in candidates:
                rich = lamoda.enrich(item['title'])

                if not rich:
                    sku = f"OST-{abs(hash(item['title']))}"
                    image_url = ""
                    metrics_pack = {
                        "fit_profile": "regular",
                        "model_metrics": {},
                        "model_size": None,
                        "fabric": "",
                        "elastane_pct": 0,
                    }
                    logger.info(f"Skipped enrichment: {item['title']}")
                else:
                    sku = rich['sku']
                    image_url = rich['image_url']
                    metrics_pack = rich['metrics'] or {}

                # ВАЖНО: сохраняем как словарь по размерам (хотя бы один "виртуальный" размер),
                # иначе /api/calculate будет ломаться
                metrics_by_size = {
                    "M": {
                        **metrics_pack,
                        "internal_category": cat_name,
                    }
                }

                in_stock = ostin.check_stock()

                garment_data = {
                    "sku": sku,
                    "name": item['title'],
                    "platform": "ostin",
                    "price": item['price'],
                    "image_url": image_url,
                    "metrics": metrics_by_size,
                    "in_stock": in_stock
                }

                existing = db.query(models.Garment).filter(models.Garment.sku == sku).first()
                if existing:
                    for k, v in garment_data.items():
                        setattr(existing, k, v)
                else:
                    db.add(models.Garment(**garment_data))

                try:
                    db.commit()
                    total_processed += 1
                    logger.info(f"Saved: {item['title']} [{sku}]")
                except Exception as e:
                    logger.error(f"DB Error: {e}")
                    db.rollback()

    return total_processed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", help="Path to DB (ignored, using backend config)")
    _ = parser.parse_args()

    print("[parser] Starting update cycle...")

    count = harvest_and_upsert(
        store_id=OSTIN_STORE_ID_ANGARSK,
        per_category=LIMIT_PER_CATEGORY,
        cats={}
    )

    print(f"[parser] Done. Processed: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

