#!/usr/bin/env python3
"""
shops/ostin_parser.py

Запускается из админки (/api/admin/update-db).
Логика:
1. Запуск Playwright (Stealth).
2. "Прогрев" на главной странице O'stin (обход Qrator).
3. Парсинг каталога.
4. Обогащение через Lamoda.
5. Сохранение в БД с правильной структурой metrics={"M": ...}.
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

# --- НАСТРОЙКА ПУТЕЙ ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend import database, models

try:
    from playwright.sync_api import sync_playwright, Page
except ImportError:
    print("CRITICAL: Playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

# --- КОНФИГУРАЦИЯ ---
OSTIN_STORE_ID_ANGARSK = 4219
LIMIT_PER_CATEGORY = 10 

CATEGORY_URLS = {
    "women_pants": "zhenshchinam/odezhda/bryuki",
    "women_jeans": "zhenshchinam/odezhda/dzhinsy",
    "women_skirts": "zhenshchinam/odezhda/yubki",
    "women_dresses": "zhenshchinam/odezhda/platya-i-sarafany",
    "men_pants": "muzhchinam/odezhda/bryuki",
    "men_jeans": "muzhchinam/odezhda/dzhinsy",
    "men_shirts": "muzhchinam/odezhda/rubashki",
    "men_tshirts": "muzhchinam/odezhda/futbolki-i-mayki",
}

logging.basicConfig(level=logging.INFO, format='[parser] %(message)s')
logger = logging.getLogger(__name__)

# ==========================================
# 1. O'STIN PARSER (Human Simulation)
# ==========================================

class OstinCatalog:
    BASE_URL = "https://ostin.com"

    def fetch_items(self, slug: str, limit: int) -> List[Dict]:
        items = []
        target_url = f"{self.BASE_URL}/catalog/{slug}"
        
        with sync_playwright() as p:
            # Запуск с максимальной маскировкой
            browser = p.chromium.launch(
                headless=True,
                ignore_default_args=["--enable-automation"],
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--window-size=1920,1080',
                ]
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                locale='ru-RU',
                timezone_id='Europe/Moscow',
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            )
            
            # JS-инъекции для скрытия headless-режима
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            page = context.new_page()

            try:
                # --- ЭТАП 1: ПРОГРЕВ (Bypass Qrator) ---
                logger.info("🔥 Прогрев: заход на главную страницу...")
                try:
                    page.goto(self.BASE_URL, timeout=40000, wait_until='domcontentloaded')
                    time.sleep(3)
                    
                    # Имитация пользователя: движения мышью
                    page.mouse.move(random.randint(100, 500), random.randint(100, 500))
                    page.mouse.wheel(0, 300)
                    time.sleep(2)
                    
                except Exception as e:
                    logger.warning(f"Ошибка на главной (не критично): {e}")

                # --- ЭТАП 2: ПЕРЕХОД В КАТАЛОГ ---
                logger.info(f"📂 Переход в категорию: {slug}")
                page.goto(target_url, timeout=60000, wait_until='domcontentloaded')

                # Проверка на блокировку
                if "Access Denied" in page.title() or "заблокирован" in page.title():
                    logger.error("⛔ Блокировка IP (Qrator). Попробуйте сменить IP или использовать прокси.")
                    # Делаем скриншот для диагностики
                    page.screenshot(path=os.path.join(current_dir, "block_screen.png"))
                    return []

                # Ожидание товаров
                try:
                    page.wait_for_selector('div[class*="ProductCard"]', timeout=20000)
                except:
                    logger.warning("Таймаут ожидания карточек. Пробую скролл...")
                
                # Скролл для ленивой загрузки
                for _ in range(3):
                    page.mouse.wheel(0, 1000)
                    time.sleep(1.5)

                # Парсинг
                soup = BeautifulSoup(page.content(), 'html.parser')
                cards = soup.find_all('div', class_=re.compile('ProductCard_card'))
                if not cards:
                    cards = soup.find_all('div', class_=re.compile('ProductCard'))

                logger.info(f"Найдено карточек: {len(cards)}")

                for c in cards[:limit]:
                    try:
                        link_tag = c.find('a', href=True)
                        title_tag = c.find('div', class_=re.compile('ProductCard_title')) or c.find('div', class_=re.compile('title'))
                        price_tag = c.find('div', class_=re.compile('ProductCard_price')) or c.find('div', class_=re.compile('price'))
                        
                        if link_tag and title_tag:
                            price_str = price_tag.get_text(strip=True) if price_tag else "0"
                            price = float(re.sub(r'[^\d]', '', price_str) or 0)
                            
                            href = link_tag['href']
                            full_url = self.BASE_URL + href if href.startswith('/') else href

                            items.append({
                                'title': title_tag.get_text(strip=True),
                                'url': full_url,
                                'price': price
                            })
                    except:
                        continue
                
            except Exception as e:
                logger.error(f"Playwright Error: {e}")
            finally:
                browser.close()
            
        return items

    def check_stock(self) -> bool:
        return random.random() > 0.3


# ==========================================
# 2. LAMODA ENRICHER
# ==========================================

class LamodaEnricher:
    SEARCH_URL = "https://www.lamoda.ru/catalogsearch/result/"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)',
            'Accept-Language': 'ru-RU,ru;q=0.9',
        }

    def enrich(self, title: str) -> Optional[Dict]:
        try:
            params = {'q': f"O'stin {title}", 'submit': 'y'}
            resp = self.session.get(self.SEARCH_URL, params=params, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            link = soup.find('a', class_=re.compile('ProductCard-link'))
            if not link: return None
                
            product_url = "https://www.lamoda.ru" + link['href']
            time.sleep(random.uniform(0.5, 1.5))
            
            page_resp = self.session.get(product_url, timeout=10)
            data = self._extract_json(page_resp.text)
            
            if not data: return None
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
            if src: img = f"https:{src}" if src.startswith('//') else src

        metrics_pack = {
            "model_metrics": {},
            "model_size": None,
            "elastane_pct": 0,
            "fabric": "",
            "fit_profile": "regular"
        }

        # Парсинг атрибутов
        for attr in payload.get('attributes', []):
            lbl = (attr.get('label') or '').lower()
            val = (attr.get('value') or '').lower()
            
            if 'параметры модели' in lbl:
                p = val.split('-')
                if len(p) >= 3:
                    try:
                        metrics_pack["model_metrics"] = {
                            "chest": int(p[0]), "waist": int(p[1]), "hips": int(p[2])
                        }
                    except: pass
            elif 'рост модели' in lbl:
                h = re.search(r'\d+', val)
                if h: metrics_pack["model_metrics"]["height"] = int(h.group())
            elif 'размер' in lbl and 'модел' in lbl:
                metrics_pack["model_size"] = val.upper()
            elif 'состав' in lbl:
                metrics_pack["fabric"] = val
                el = re.search(r'(\d+)\s*[%]*\s*эластан', val)
                if el: metrics_pack["elastane_pct"] = int(el.group(1))

        # Fit profile
        title_lower = payload.get('title', '').lower()
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

def harvest_and_upsert(store_id: int, per_category: int, cats: dict) -> int:
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
                    raw_metrics = {
                        "fit_profile": "regular", 
                        "model_metrics": {},
                        "elastane_pct": 0
                    }
                else:
                    sku = rich['sku']
                    image_url = rich['image_url']
                    raw_metrics = rich['metrics']

                # --- КОРРЕКЦИЯ СТРУКТУРЫ ДЛЯ BACKEND ---
                # Добавляем внутреннюю категорию
                raw_metrics["internal_category"] = cat_name
                
                # Упаковываем в словарь по размерам {"M": {...}}
                # Это позволяет api/calculate корректно итерироваться
                structured_metrics = {"M": raw_metrics}

                garment_data = {
                    "sku": sku,
                    "name": item['title'],
                    "platform": "ostin",
                    "price": item['price'],
                    "image_url": image_url,
                    "metrics": structured_metrics,
                    "in_stock": True
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", help="Path to DB")
    args = parser.parse_args()
    
    print(f"[parser] Store ID: {OSTIN_STORE_ID_ANGARSK}")
    count = harvest_and_upsert(OSTIN_STORE_ID_ANGARSK, LIMIT_PER_CATEGORY, {})
    print(f"[parser] Done. Processed: {count}")

if __name__ == "__main__":
    main()

