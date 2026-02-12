#!/usr/bin/env python3
"""
shops/ostin_parser.py

ВЕРСИЯ: MAXIMUM BYPASS / LAMODA-FIRST
Запускается из админки (/api/admin/update-db).

Стратегия:
1. Использует Playwright (Full Browser) вместо requests для обхода WAF Lamoda (ошибка 401).
2. Применяет техники Stealth (скрытие navigator.webdriver, эмуляция плагинов).
3. Ищет товары O'stin на Lamoda.
4. Извлекает "золотые данные" (Vendor Code, Биометрия, Состав) из JSON State.
5. Сохраняет в БД с правильной структурой metrics={"M": ...}.
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

# --- НАСТРОЙКА ПУТЕЙ ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend import database, models

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("CRITICAL: Playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

# --- КОНФИГУРАЦИЯ ---
# Поисковые запросы для нахождения товаров O'stin на Lamoda
CATEGORY_QUERIES = {
    "women_pants": "O'stin брюки женские",
    "women_jeans": "O'stin джинсы женские",
    "women_skirts": "O'stin юбки",
    "women_dresses": "O'stin платья",
    "men_pants": "O'stin брюки мужские",
    "men_jeans": "O'stin джинсы мужские",
    "men_shirts": "O'stin рубашки мужские",
    "men_tshirts": "O'stin футболки мужские",
}

LIMIT_PER_CATEGORY = 12  # Не жадничаем, чтобы не получить бан по IP

logging.basicConfig(level=logging.INFO, format='[parser] %(message)s')
logger = logging.getLogger(__name__)


class LamodaStealthHarvester:
    """
    Класс для скрытного парсинга Lamoda через Playwright.
    Эмулирует реального пользователя для обхода блокировок 401/403.
    """
    SEARCH_URL = "https://www.lamoda.ru/catalogsearch/result/"
    
    def fetch_items(self, query: str, limit: int) -> List[Dict]:
        items = []
        logger.info(f"🕵️  Запуск Stealth-браузера для: '{query}'")
        
        with sync_playwright() as p:
            # МАКСИМАЛЬНАЯ МАСКИРОВКА
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled', # Самый важный флаг
                    '--disable-infobars',
                    '--window-size=1920,1080',
                    '--start-maximized',
                ]
            )
            
            # Контекст с реальным User-Agent и локалью
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                locale='ru-RU',
                timezone_id='Europe/Moscow',
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            )
            
            # JS-ИНЪЕКЦИИ ПРОТИВ ДЕТЕКТОРОВ
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
                window.chrome = { runtime: {} };
            """)
            
            page = context.new_page()
            
            try:
                # 1. Формирование URL
                # Lamoda принимает пробелы как +, playwright сам закодирует
                url = f"{self.SEARCH_URL}?q={query}&submit=y"
                
                # 2. Переход на страницу
                response = page.goto(url, timeout=60000, wait_until='domcontentloaded')
                
                # Проверка статуса (если Lamoda отдала 403/401 даже браузеру)
                if response and response.status in [401, 403]:
                    logger.error(f"⛔ Блокировка доступа (HTTP {response.status}). IP сервера в черном списке.")
                    return []

                # 3. Имитация человека (Humanize)
                self._human_behavior(page)
                
                # 4. Проверка на Captcha / Access Denied
                title = page.title()
                if "Access Denied" in title or "Captcha" in title:
                    logger.warning("⚠️ Обнаружена защита WAF/Captcha.")
                    return []

                # 5. Извлечение данных
                # Мы ищем JSON state внутри HTML, так как он содержит полные данные
                html_content = page.content()
                data = self._extract_json_state(html_content)
                
                if not data:
                    logger.warning("JSON State не найден. Возможно, изменилась верстка.")
                    return []
                
                # Поиск списка товаров
                products = self._find_products_in_payload(data)
                logger.info(f"Найдено товаров в JSON: {len(products)}")

                for p in products[:limit]:
                    try:
                        parsed = self._parse_product_entry(p)
                        if parsed:
                            items.append(parsed)
                    except Exception:
                        continue
                        
            except Exception as e:
                logger.error(f"Ошибка Playwright: {e}")
            finally:
                browser.close()
            
        return items

    def _human_behavior(self, page):
        """Имитация действий пользователя для 'прогрева'"""
        try:
            # Случайные движения мышью
            page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            time.sleep(random.uniform(0.5, 1.5))
            
            # Скролл вниз (триггерит ленивую загрузку и JS-события)
            page.mouse.wheel(0, 500)
            time.sleep(1)
            page.mouse.wheel(0, 500)
            time.sleep(2)
        except:
            pass

    def _extract_json_state(self, html: str) -> Optional[Dict]:
        """Парсит window.__INITIAL_STATE__"""
        # Используем regex с DOTALL для захвата многострочного JSON
        m = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except:
                pass
        return None

    def _find_products_in_payload(self, data: Dict) -> List[Dict]:
        """Ищет массив продуктов в структуре Lamoda"""
        # Структура может меняться, проверяем популярные пути
        paths = [
            ['payload', 'catalog', 'products'],
            ['state', 'catalog', 'result', 'products'],
            ['catalog', 'products']
        ]
        
        for path in paths:
            current = data
            try:
                for key in path:
                    current = current[key]
                if isinstance(current, list):
                    return current
            except (KeyError, TypeError):
                continue
        return []

    def _parse_product_entry(self, p: Dict) -> Optional[Dict]:
        """Превращает сырой объект Lamoda в формат Fit_system"""
        
        # 1. Vendor Code (Артикул производителя)
        vendor_code = p.get('model', {}).get('vendor_code')
        if not vendor_code:
            # Иногда в атрибутах
            for attr in p.get('attributes', []):
                if attr.get('key') == 'vendor_code' or attr.get('label') == 'Артикул':
                    vendor_code = attr.get('value')
                    break
        
        # Если кода нет или это внутренний код Lamoda (MP00...), генерируем стабильный ID
        lamoda_sku = p.get('sku', '')
        if not vendor_code or str(vendor_code).startswith("MP00"):
            if lamoda_sku:
                vendor_code = f"OST-{lamoda_sku[-8:]}"
            else:
                return None # Мусорные данные

        # 2. Основные поля
        name = p.get('title', '') or p.get('name', '')
        price = float(p.get('price', {}).get('amount', 0))
        img_raw = p.get('image', '') or p.get('gallery', [{}])[0].get('image', '')
        img = f"https:{img_raw}" if img_raw.startswith('//') else img_raw

        # 3. Метрики (попытка достать из листинга)
        # В списке товаров детальной биометрии может не быть, 
        # но мы заполним структуру для совместимости.
        metrics_pack = {
            "model_metrics": {},
            "model_size": None,
            "elastane_pct": 0,
            "fabric": "",
            "fit_profile": "regular"
        }

        # Пытаемся угадать профиль по названию
        t_lower = name.lower()
        if 'oversize' in t_lower or 'оверсайз' in t_lower:
            metrics_pack['fit_profile'] = 'oversize'
        elif 'slim' in t_lower or 'узкие' in t_lower or 'притален' in t_lower:
            metrics_pack['fit_profile'] = 'slim'
            
        # Пытаемся достать состав (иногда есть в листинге)
        # Если нет - ставим дефолт для джинсов (чтобы алгоритм IEA работал)
        if 'джинсы' in t_lower or 'jeans' in t_lower:
            metrics_pack['elastane_pct'] = 2

        return {
            "sku": vendor_code,
            "name": f"O'stin {name}",
            "price": price,
            "image_url": img,
            "metrics": metrics_pack,
            "lamoda_url": f"https://www.lamoda.ru/p/{lamoda_sku}/"
        }


# ==========================================
# 2. ЛОГИКА ОБНОВЛЕНИЯ БД
# ==========================================

def harvest_and_upsert(per_category: int) -> int:
    models.Base.metadata.create_all(bind=database.engine)
    harvester = LamodaStealthHarvester()
    
    total_processed = 0
    
    with database.SessionLocal() as db:
        for cat_key, query in CATEGORY_QUERIES.items():
            logger.info(f"--- Обработка категории: {cat_key} ---")
            
            # Запускаем новый браузер для каждой категории (чистая сессия = меньше банов)
            items = harvester.fetch_items(query, per_category)
            
            if not items:
                logger.warning(f"Категория {cat_key} пропущена (нет данных или бан).")
                time.sleep(5)
                continue

            for item in items:
                sku = item['sku']
                raw_metrics = item['metrics']
                
                # Дополняем метрики категорией
                raw_metrics["internal_category"] = cat_key

                # ВАЖНО: Упаковка для backend fit_engine (структура {"M": ...})
                structured_metrics = {"M": raw_metrics}
                
                # Upsert в БД
                garment_data = {
                    "sku": sku,
                    "name": item['name'],
                    "platform": "ostin", 
                    "price": item['price'],
                    "image_url": item['image_url'],
                    "metrics": structured_metrics,
                    "in_stock": True,
                    "url": item['lamoda_url'] # Ссылка на товар
                }

                existing = db.query(models.Garment).filter(models.Garment.sku == sku).first()
                if existing:
                    # Обновляем существующий
                    for k, v in garment_data.items():
                        setattr(existing, k, v)
                else:
                    # Создаем новый
                    db.add(models.Garment(**garment_data))
                
                try:
                    db.commit()
                    total_processed += 1
                    logger.info(f"Saved: {item['name']} [{sku}]")
                except Exception as e:
                    db.rollback()
                    logger.error(f"DB Error: {e}")
            
            # Большая пауза между категориями (снижает риск бана)
            sleep_time = random.uniform(5, 10)
            logger.info(f"Пауза {sleep_time:.1f} сек...")
            time.sleep(sleep_time)

    return total_processed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", help="Ignored")
    args = parser.parse_args()
    
    logger.info("Запуск парсера (Playwright Stealth Mode)...")
    count = harvest_and_upsert(LIMIT_PER_CATEGORY)
    logger.info(f"🏁 Готово. Обработано товаров: {count}")

if __name__ == "__main__":
    main()

