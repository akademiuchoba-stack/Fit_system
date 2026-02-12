#!/usr/bin/env python3
"""
shops/ostin_parser.py

Запускается из админки.
Использует Playwright (как браузер) для загрузки каталога O'stin,
дальше парсит HTML через BeautifulSoup.
Потом обогащает данные через Lamoda (requests) и пишет в SQLite через ORM Fit_system.

ВАЖНО для совместимости с backend:
- Garment.metrics ДОЛЖНО быть словарём по размерам, т.к. /api/calculate делает:
  for size_label, raw_metrics in item.metrics.items()
Поэтому мы сохраняем данные в виртуальный размер "M": metrics={"M": {...}}
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
from typing import Dict, List, Optional, Any

import requests
from bs4 import BeautifulSoup

# --- НАСТРОЙКА ОКРУЖЕНИЯ ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend import database, models  # noqa: E402

# Playwright
try:
    from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
except ImportError:
    print("CRITICAL: Playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

# --- КОНФИГУРАЦИЯ ---
OSTIN_STORE_ID_ANGARSK = 4219
LIMIT_PER_CATEGORY = 10  # как ты просил

CATEGORY_URLS = {
    "women_pants": "zhenshchinam/odezhda/bryuki",
    "women_jeans": "zhenshchinam/odezhda/dzhinsy",
    "women_skirts": "zhenshchinam/odezhda/yubki",
    "women_dresses": "zhenshchinam/odezhda/platya-i-sarafany",
    "women_shirts": "zhenshchinam/odezhda/rubashki",
    "women_tshirts": "zhenshchinam/odezhda/futbolki-i-maiki",
    "women_blouses": "zhenshchinam/odezhda/bluzki-i-rubashki",
    "women_jackets": "zhenshchinam/odezhda/verkhnyaya-odezhda",

    "men_pants": "muzhchinam/odezhda/bryuki",
    "men_jeans": "muzhchinam/odezhda/dzhinsy",
    "men_shirts": "muzhchinam/odezhda/rubashki",
    "men_tshirts": "muzhchinam/odezhda/futbolki-i-mayki",
    "men_jackets": "muzhchinam/odezhda/verkhnyaya-odezhda",
}

logging.basicConfig(level=logging.INFO, format='[parser] %(message)s')
logger = logging.getLogger(__name__)


# ==========================================
# 1. O'STIN PARSER (Playwright -> HTML -> BS4)
# ==========================================

class OstinCatalog:
    BASE_URL = "https://ostin.com"

    def __init__(self, page: Page):
        self.page = page

    def fetch_items(self, slug: str, limit: int) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        url = f"{self.BASE_URL}/catalog/{slug}"
        logger.info(f"O'stin (Playwright): открываю {url}")

        try:
            self.page.goto(url, timeout=60000)

            # Ждём появления чего-то, похожего на карточки (если не появится — просто вернём пусто)
            logger.info("Жду появления карточек товаров...")
            try:
                self.page.wait_for_selector('div[class*="ProductCard"]', timeout=30000)
            except Exception:
                logger.warning("Таймаут ожидания карточек. Каталог не загрузился.")
                return []

            # Небольшой скролл для lazy-load
            self.page.evaluate("window.scrollTo(0, 800)")
            time.sleep(1)

            html_content = self.page.content()
            soup = BeautifulSoup(html_content, 'html.parser')

            # Пытаемся найти карточки (как у тебя было)
            cards = soup.find_all('div', class_=re.compile('ProductCard_card'))
            if not cards:
                # запасной вариант — иногда классы меняются
                cards = soup.find_all('div', class_=re.compile('ProductCard'))

            for c in cards[:limit]:
                try:
                    link_tag = c.find('a', href=True)
                    title_tag = c.find('div', class_=re.compile('ProductCard_title')) or c.find('div', class_=re.compile('title'))
                    price_tag = c.find('div', class_=re.compile('ProductCard_price')) or c.find('div', class_=re.compile('price'))

                    if not (link_tag and title_tag):
                        continue

                    price_str = price_tag.get_text(strip=True) if price_tag else "0"
                    price = float(re.sub(r'[^\d]', '', price_str) or 0)

                    href = link_tag['href']
                    if href.startswith("/"):
                        href = self.BASE_URL + href

                    items.append({
                        'title': title_tag.get_text(strip=True),
                        'url': href,
                        'price': price
                    })
                except Exception:
                    continue

            logger.info(f"Получено товаров: {len(items)}")
            return items

        except Exception as e:
            logger.error(f"Playwright Error: {e}")
            return []

    def check_stock(self) -> bool:
        # как у тебя: имитация
        return random.random() > 0.2


# ==========================================
# 2. LAMODA ENRICHER (requests)
# ==========================================

class LamodaEnricher:
    SEARCH_URL = "https://www.lamoda.ru/catalogsearch/result/"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9',
        }

    def enrich(self, title: str) -> Optional[Dict[str, Any]]:
        try:
            params = {'q': f"O'stin {title}", 'submit': 'y'}
            resp = self.session.get(self.SEARCH_URL, params=params, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')

            link = soup.find('a', class_=re.compile('ProductCard-link'))
            if not link:
                return None

            product_url = "https://www.lamoda.ru" + link['href']
            time.sleep(random.uniform(1.0, 2.0))

            page_resp = self.session.get(product_url, timeout=15)
            data = self._extract_json(page_resp.text)
            if not data:
                return None

            return self._parse_json(data, product_url)

        except Exception as e:
            logger.warning(f"Lamoda enrich failed: {e}")
            return None

    def _extract_json(self, html: str) -> Optional[Dict[str, Any]]:
        m = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html, re.DOTALL)
        return json.loads(m.group(1)) if m else None

    def _parse_json(self, data: Dict[str, Any], url: str) -> Dict[str, Any]:
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

        metrics_pack: Dict[str, Any] = {
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
        elif 'slim' in title_lower:
            metrics_pack["fit_profile"] = "slim"

        return {
            "sku": vendor_code,
            "image_url": img,
            "metrics": metrics_pack
        }


# ==========================================
# 3. UPSERT LOGIC
# ==========================================

def harvest_and_upsert(ostin: OstinCatalog, lamoda: LamodaEnricher, per_category: int) -> int:
    models.Base.metadata.create_all(bind=database.engine)

    total_processed = 0

    with database.SessionLocal() as db:
        for cat_name, ostin_slug in CATEGORY_URLS.items():
            logger.info(f"--- Категория: {cat_name} ---")

            candidates = ostin.fetch_items(ostin_slug, per_category)

            for item in candidates:
                rich = lamoda.enrich(item['title'])

                if not rich:
                    sku = f"OST-{abs(hash(item['title']))}"
                    metrics_pack = {
                        "fit_profile": "regular",
                        "model_metrics": {},
                        "model_size": None,
                        "elastane_pct": 0,
                        "fabric": "",
                    }
                    image_url = ""
                else:
                    sku = rich['sku']
                    metrics_pack = rich['metrics']
                    image_url = rich['image_url']

                # ВАЖНО: формат по размерам для backend
                metrics_by_size = {
                    "M": {
                        **(metrics_pack or {}),
                        "internal_category": cat_name,
                    }
                }

                garment_data = {
                    "sku": sku,
                    "name": item['title'],
                    "platform": "ostin",
                    "price": item.get('price', 0),
                    "image_url": image_url,
                    "metrics": metrics_by_size,
                    "in_stock": bool(ostin.check_stock()),
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
                    db.rollback()
                    logger.error(f"DB Error: {e}")

    return total_processed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", help="Path to DB (backend uses its own path; arg kept for compatibility)")
    _ = ap.parse_args()

    logger.info(f"Store ID (fixed): {OSTIN_STORE_ID_ANGARSK}")

    lamoda = LamodaEnricher()

    # Один браузер на весь запуск (оптимизация без изменения логики)
    with sync_playwright() as p:
        browser: Browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context: BrowserContext = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page: Page = context.new_page()

        try:
            ostin = OstinCatalog(page)
            count = harvest_and_upsert(ostin, lamoda, LIMIT_PER_CATEGORY)
        finally:
            context.close()
            browser.close()

    logger.info(f"Done. Processed: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

