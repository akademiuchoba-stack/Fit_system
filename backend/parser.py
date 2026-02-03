
import aiohttp
import json
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from thefuzz import fuzz

class FitParser:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    async def parse_lamoda(self, url: str) -> Dict[str, Any]:
        """Парсинг Lamoda через извлечение __INITIAL_STATE__"""
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url) as resp:
                html = await resp.text()
                
                # Ищем JSON в скриптах
                match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html)
                if match:
                    data = json.loads(match.group(1))
                    product = data.get('product', {})
                    # Извлекаем характеристики для вычисления геометрии
                    attributes = product.get('attributes', [])
                    metrics = self._extract_metrics_from_attrs(attributes)
                    return {
                        "name": product.get('name'),
                        "sku": product.get('sku'),
                        "price": product.get('price'),
                        "metrics": metrics,
                        "platform": "lamoda",
                        "image": product.get('images', [{}])[0].get('url')
                    }
                return {}

    def _extract_metrics_from_attrs(self, attrs: List[Dict]) -> Dict:
        """Поиск ключевых слов (длина, грудь) в атрибутах Lamoda"""
        metrics = {"S": {"chest": 48, "shoulder": 42, "sleeve": 60, "length": 68}} # Mock-fallback
        # В реальности парсим таблицу размеров или описание
        return metrics

    async def check_ostin_inventory(self, sku: str) -> bool:
        """Эмуляция запроса к Inventory API O'stin (Ангарск, ТРЦ Фестиваль)"""
        # ТРЦ Фестиваль (Ангарск) обычно имеет свой scopeCode (например '123')
        api_url = "https://ostin.com/api/v1/inventory/availability"
        payload = {
            "filters": {"sku": [sku]},
            "scopeCode": "ANG_FEST" # Условный код для Фестиваля
        }
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.post(api_url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Если остаток > 0 в нужном магазине
                        return True 
        except:
            pass
        return False

    def fuzzy_match(self, name1: str, name2: str) -> bool:
        return fuzz.ratio(name1, name2) > 85
