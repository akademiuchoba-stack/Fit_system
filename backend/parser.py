
"""
parser.py — Универсальный модуль загрузки и обогащения каталога для Fit_system.

Поддерживает источники:
1. Локальные файлы JSON / JSONL / CSV.
2. SQLite базы данных (.db), созданные парсером "IdealFit_Harvester".
3. Прямой парсинг URL (Lamoda-like) через aiohttp (для точечных запросов).

Архитектура:
- Данные приводятся к единому датаклассу ParsedItem.
- Биометрия модели извлекается либо из структурированных колонок БД,
  либо через NLP/Regex из текстового описания.
"""

from __future__ import annotations

import json
import re
import sqlite3
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import aiohttp

# -------------------------------------------------------------------------
# DATA STRUCTURES
# -------------------------------------------------------------------------

@dataclass
class ParsedItem:
    sku: str
    name: str
    brand: str = ""
    category: str = ""
    image_url: str = ""
    url: str = ""
    in_stock: bool = True
    size_label: str = ""
    fit_profile: str = "regular"  # slim/regular/oversize
    fabric: str = ""
    elastane_pct: Optional[float] = None

    # Данные для алгоритма "Идеальный припуск" (IEA)
    # Пример: {"height": 175, "chest": 84, "waist": 60, "hips": 90}
    model_metrics: Optional[Dict[str, Any]] = None
    model_size: Optional[str] = None

    # Промеры самого изделия (если доступны)
    metrics: Optional[Dict[str, Any]] = None


# -------------------------------------------------------------------------
# REGEX / NLP: Извлечение данных из текста
# -------------------------------------------------------------------------

RE_TRIPLE = re.compile(r"(\d{2,3})\s*[-—–]\s*(\d{2,3})\s*[-—–]\s*(\d{2,3})")
RE_CHEST = re.compile(r"(?:грудь|ог|bust)[\s:.-]*(\d{2,3})", re.I)
RE_WAIST = re.compile(r"(?:талия|от|waist)[\s:.-]*(\d{2,3})", re.I)
RE_HIPS  = re.compile(r"(?:б[её]дра|об|hips)[\s:.-]*(\d{2,3})", re.I)
RE_HEIGHT = re.compile(r"(?:рост|height)[\s:.-]*(\d{2,3})", re.I)
RE_SIZE_ON_MODEL = re.compile(r"(?:размер\s+на\s+модел[и|е]|size\s+on\s+model)[\s:.-]*([A-Za-zА-Яа-я0-9-]+)", re.I)
RE_ELASTANE = re.compile(r"(\d{1,2})\s*%?\s*(?:эластан|elastane|spandex|lycra)", re.I)

RE_HALF_CHEST = re.compile(r"(?:полуобхват\s+груди|ширина\s+под\s+проймой|pit\s+to\s+pit)[\s:.-]*(\d{2,3})", re.I)
RE_SHOULDERS = re.compile(r"(?:плечи|ширина\s+плеч|shoulders?)[\s:.-]*(\d{2,3})", re.I)
RE_SLEEVE = re.compile(r"(?:рукав|длина\s+рукава|sleeve)[\s:.-]*(\d{2,3})", re.I)
RE_LENGTH = re.compile(r"(?:длина\s+изделия|длина\s+по\s+спинке|length)[\s:.-]*(\d{2,3})", re.I)


def _extract_model_metrics(text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Достаёт рост + ОГ-ОТ-ОБ и размер модели из текста."""
    if not text:
        return None, None

    t = " ".join(str(text).split())
    mm: Dict[str, Any] = {}

    # Поиск тройки параметров (90-60-90)
    m = RE_TRIPLE.search(t)
    if m:
        mm["chest"] = int(m.group(1))
        mm["waist"] = int(m.group(2))
        mm["hips"] = int(m.group(3))

    mh = RE_HEIGHT.search(t)
    if mh:
        mm["height"] = int(mh.group(1))

    # Fallback по отдельным ключевым словам
    if "chest" not in mm:
        mc = RE_CHEST.search(t)
        if mc: mm["chest"] = int(mc.group(1))
    if "waist" not in mm:
        mw = RE_WAIST.search(t)
        if mw: mm["waist"] = int(mw.group(1))
    if "hips" not in mm:
        mhp = RE_HIPS.search(t)
        if mhp: mm["hips"] = int(mhp.group(1))

    ms = None
    sm = RE_SIZE_ON_MODEL.search(t)
    if sm:
        ms = sm.group(1).strip()

    return (mm or None), ms


def _extract_elastane_pct(text: str) -> Optional[float]:
    """Извлекает процент эластана для расчета Negative Ease."""
    if not text:
        return None
    t = " ".join(str(text).split())
    m = RE_ELASTANE.search(t)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


def _extract_garment_metrics(text: str) -> Optional[Dict[str, Any]]:
    """Извлекает прямые промеры изделия (длина, рукав) из текста."""
    if not text:
        return None
    t = " ".join(str(text).split())
    metrics: Dict[str, Any] = {}

    mhc = RE_HALF_CHEST.search(t)
    if mhc: metrics["chest"] = int(mhc.group(1)) * 2  # полуобхват -> обхват

    ms = RE_SLEEVE.search(t)
    if ms: metrics["sleeve"] = int(ms.group(1))

    ml = RE_LENGTH.search(t)
    if ml: metrics["length"] = int(ml.group(1))

    msh = RE_SHOULDERS.search(t)
    if msh: metrics["shoulders"] = int(msh.group(1))

    return metrics or None


def _guess_fit_profile(text: str) -> str:
    t = str(text).lower() if text else ""
    if "oversize" in t or "оверсайз" in t or "loose" in t:
        return "oversize"
    if "slim" in t or "облег" in t or "skinny" in t:
        return "slim"
    return "regular"


# -------------------------------------------------------------------------
# WEB PARSING UTILS (Async)
# -------------------------------------------------------------------------

async def fetch_html(url: str, session: aiohttp.ClientSession) -> str:
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
        resp.raise_for_status()
        return await resp.text()


def extract_initial_state(html: str) -> Optional[Dict[str, Any]]:
    """Извлекает window.__INITIAL_STATE__ JSON из HTML Lamoda."""
    if not html: return None
    m = re.search(r"window\.__INITIAL_STATE__\s*=\s*({.*?});", html, flags=re.DOTALL)
    if not m: return None
    try:
        return json.loads(m.group(1))
    except Exception:
        return None


def deep_find_first(obj: Any, key_predicate) -> Optional[Any]:
    """Рекурсивный поиск значения в JSON."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if key_predicate(k): return v
            res = deep_find_first(v, key_predicate)
            if res is not None: return res
    elif isinstance(obj, list):
        for it in obj:
            res = deep_find_first(it, key_predicate)
            if res is not None: return res
    return None


async def parse_lamoda_like(url: str) -> Optional[ParsedItem]:
    """
    Парсит страницу Lamoda-типа по URL.
    Используется для добавления товара "на лету".
    """
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        try:
            html = await fetch_html(url, session)
        except Exception:
            return None
        
        state = extract_initial_state(html)
        if not state: return None

        # Хелперы для извлечения из state
        def _get_val(keys: List[str]) -> str:
            val = deep_find_first(state, lambda k: k.lower() in keys)
            return str(val) if val else ""

        sku = _get_val(["vendor_code", "manufacturer_sku", "mnfr", "sku"])
        if str(sku).startswith("MP00"): sku = "" # Игнорируем внутренние ID если нашли их вместо вендора
        
        # Если не нашли вендор код, генерируем хеш из URL
        if not sku or len(sku) < 4:
            sku = re.sub(r"\W+", "_", url)[-32:]

        title = _get_val(["title", "name"]) or sku
        
        # Картинка
        img = ""
        gal_item = deep_find_first(state, lambda k: "gallery" in k.lower())
        if isinstance(gal_item, list) and gal_item:
             i = gal_item[0]
             if isinstance(i, dict):
                 raw_img = i.get("image") or i.get("src")
                 if raw_img: img = f"https:{raw_img}" if raw_img.startswith("//") else raw_img

        # Сбор текста для NLP анализа
        text_parts = []
        attrs = deep_find_first(state, lambda k: k.lower() == "attributes")
        if isinstance(attrs, list):
            for a in attrs:
                if isinstance(a, dict):
                    text_parts.append(f"{a.get('label', '')}: {a.get('value', '')}")
        
        desc = deep_find_first(state, lambda k: k.lower() in ("description", "desc"))
        if desc: text_parts.append(str(desc))
        
        full_text = " | ".join(text_parts)

        # NLP извлечение
        model_metrics, model_size = _extract_model_metrics(full_text)
        elastane_pct = _extract_elastane_pct(full_text)
        garment_metrics = _extract_garment_metrics(full_text)
        fit_profile = _guess_fit_profile(full_text)

        return ParsedItem(
            sku=sku,
            name=title,
            image_url=img,
            url=url,
            fit_profile=fit_profile,
            elastane_pct=elastane_pct,
            model_metrics=model_metrics,
            model_size=model_size,
            metrics=garment_metrics
        )


# -------------------------------------------------------------------------
# FILE LOADING (Local: DB / JSON / CSV)
# -------------------------------------------------------------------------

def load_rows_from_idealfit_sqlite(sqlite_path: str) -> List[Dict[str, Any]]:
    """
    Читает SQLite, созданную парсером IdealFit_Harvester.
    Схема: garments (ostin_sku, title, price, model_height, stock_angarsk...)
    """
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    
    # Маппинг полей SQLite -> ParsedItem (промежуточный словарь)
    # Поля IdealFit_Harvester: 
    # ostin_sku, lamoda_sku, category, title, price, model_height, 
    # model_chest, model_waist, model_hips, size_on_model, elastane_percent, 
    # image_url, product_url, stock_angarsk
    
    try:
        cur = conn.cursor()
        # Проверяем наличие таблицы
        try:
            cur.execute("SELECT 1 FROM garments LIMIT 1")
        except sqlite3.OperationalError:
            return []

        rows = cur.execute("SELECT * FROM garments").fetchall()
        out = []
        
        for r in rows:
            # Сборка метрик модели
            mm = {}
            if r["model_height"]: mm["height"] = r["model_height"]
            if r["model_chest"]: mm["chest"] = r["model_chest"]
            if r["model_waist"]: mm["waist"] = r["model_waist"]
            if r["model_hips"]: mm["hips"] = r["model_hips"]
            
            # Конвертация эластана
            elastane = None
            if r["elastane_percent"] is not None:
                try: elastane = float(r["elastane_percent"])
                except: pass

            # Конвертация стока (Integer -> Bool)
            stock_val = r["stock_angarsk"] if "stock_angarsk" in r.keys() else 1
            in_stock = bool(stock_val and int(stock_val) > 0)

            out.append({
                "sku": r["ostin_sku"], # Используем Vendor Code как основной
                "name": r["title"],
                "category": r["category"],
                "image_url": r["image_url"],
                "url": r["product_url"],
                "in_stock": in_stock,
                "elastane_pct": elastane,
                "model_metrics": mm if mm else None,
                "model_size": r["size_on_model"],
                "fit_profile": _guess_fit_profile(r["title"]), # В БД нет профиля, угадываем
                "source_lamoda_sku": r["lamoda_sku"]
            })
        return out
    
    except Exception as e:
        print(f"Ошибка чтения SQLite {sqlite_path}: {e}")
        return []
    finally:
        conn.close()


def load_items_from_local_file(path: str) -> List[ParsedItem]:
    """
    Главная точка входа для загрузки файлов.
    Определяет тип файла (.db, .json, .csv) и возвращает список ParsedItem.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")

    raw_items = []

    # 1. SQLite (IdealFit DB)
    if p.suffix.lower() in (".db", ".sqlite", ".sqlite3"):
        raw_items = load_rows_from_idealfit_sqlite(str(p))

    # 2. JSON
    elif p.suffix.lower() == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        raw_items = data if isinstance(data, list) else data.get("items", [])

    # 3. CSV
    elif p.suffix.lower() == ".csv":
        with p.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            raw_items = list(reader)

    # Преобразование в ParsedItem
    parsed_result = []
    for r in raw_items:
        # Пропускаем, если нет SKU
        sku = str(r.get("sku") or r.get("ostin_sku") or "").strip()
        if not sku: continue
        
        # Эластан
        el_pct = r.get("elastane_pct")
        if el_pct is None: 
            el_pct = _extract_elastane_pct(r.get("description", ""))

        # Биометрия
        m_metrics = r.get("model_metrics")
        m_size = r.get("model_size")
        
        # Если в JSON не было словаря метрик, пробуем распарсить текст
        if not m_metrics and r.get("description"):
            m_metrics, temp_size = _extract_model_metrics(r["description"])
            if not m_size: m_size = temp_size

        item = ParsedItem(
            sku=sku,
            name=str(r.get("name") or r.get("title") or "Unknown"),
            brand=str(r.get("brand", "")),
            category=str(r.get("category", "")),
            image_url=str(r.get("image_url", "")),
            url=str(r.get("url", "")),
            in_stock=bool(r.get("in_stock", True)),
            fit_profile=str(r.get("fit_profile", "regular")),
            fabric=str(r.get("fabric", "")),
            elastane_pct=el_pct,
            model_metrics=m_metrics,
            model_size=str(m_size) if m_size else None,
            metrics=r.get("metrics") # Промеры изделия
        )
        parsed_result.append(item)

    return parsed_result


# -------------------------------------------------------------------------
# R&D HOOKS: shop.db init + optional refresh
# -------------------------------------------------------------------------


def ensure_shop_db(sqlite_path: str) -> None:
    """Гарантирует, что файл shop.db существует и в нём есть таблица `garments`.

    Пользовательский сценарий:
    - shop.db создаётся заранее (как ты просишь), но если файла нет — мы создадим.
    - Схема создаётся "мягко": только нужные поля, совместимые с load_rows_from_idealfit_sqlite().

    Важно: мы не навязываем жёсткую схему — внешний парсер может добавлять свои колонки.
    """
    p = Path(sqlite_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(p))
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS garments (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              ostin_sku TEXT,
              lamoda_sku TEXT,
              category TEXT,
              title TEXT,
              price REAL,
              model_height INTEGER,
              model_chest INTEGER,
              model_waist INTEGER,
              model_hips INTEGER,
              size_on_model TEXT,
              elastane_percent REAL,
              image_url TEXT,
              product_url TEXT,
              stock_angarsk INTEGER
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def refresh_shop_db(sqlite_path: str) -> None:
    """Запускает внешний парсер, который обновляет shop.db.

    Управляется окружением:
    - FIT_PARSER_CMD: команда запуска (например: `python3 /path/parser.py --db {db}`)
      Где {db} будет заменено на sqlite_path.

    Если переменная не задана — функция ничего не делает.
    """
    import os
    import shlex
    import subprocess

    cmd_tpl = (os.getenv("FIT_PARSER_CMD") or "").strip()
    if not cmd_tpl:
        return

    cmd = cmd_tpl.format(db=sqlite_path)
    args = shlex.split(cmd)

    # Таймаут можно переопределить через env
    timeout_s = int(os.getenv("FIT_PARSER_TIMEOUT", "300"))

    proc = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout_s,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "Парсер завершился с ошибкой. "
            f"code={proc.returncode}; stderr={proc.stderr[-2000:]}"
        )
