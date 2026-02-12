"""
parser.py — Универсальный модуль загрузки.
Совместим с ORM-схемой (таблица garments, metrics JSON).

Поддерживает 2 формата metrics:
1) По размерам: {"S": {...}, "M": {...}}
2) Плоский: {"model_metrics": {...}, "fit_profile": "...", ...}
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
    fit_profile: str = "regular"
    fabric: str = ""
    elastane_pct: Optional[float] = None

    model_metrics: Optional[Dict[str, Any]] = None
    model_size: Optional[str] = None

    metrics: Optional[Dict[str, Any]] = None


# -------------------------------------------------------------------------
# REGEX / NLP UTILS
# -------------------------------------------------------------------------
RE_TRIPLE = re.compile(r"(\d{2,3})\s*[-—–]\s*(\d{2,3})\s*[-—–]\s*(\d{2,3})")
RE_CHEST = re.compile(r"(?:грудь|ог|bust)[\s:.-]*(\d{2,3})", re.I)
RE_WAIST = re.compile(r"(?:талия|от|waist)[\s:.-]*(\d{2,3})", re.I)
RE_HIPS  = re.compile(r"(?:б[её]дра|об|hips)[\s:.-]*(\d{2,3})", re.I)
RE_HEIGHT = re.compile(r"(?:рост|height)[\s:.-]*(\d{2,3})", re.I)
RE_SIZE_ON_MODEL = re.compile(r"(?:размер\s+на\s+модел[и|е]|size\s+on\s+model)[\s:.-]*([A-Za-zА-Яа-я0-9-]+)", re.I)
RE_ELASTANE = re.compile(r"(\d{1,2})\s*%?\s*(?:эластан|elastane|spandex|lycra)", re.I)

def _extract_model_metrics(text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not text:
        return None, None
    t = " ".join(str(text).split())
    mm: Dict[str, Any] = {}

    m = RE_TRIPLE.search(t)
    if m:
        mm["chest"], mm["waist"], mm["hips"] = int(m.group(1)), int(m.group(2)), int(m.group(3))

    mh = RE_HEIGHT.search(t)
    if mh:
        mm["height"] = int(mh.group(1))

    if "chest" not in mm:
        mc = RE_CHEST.search(t)
        if mc:
            mm["chest"] = int(mc.group(1))

    ms = None
    sm = RE_SIZE_ON_MODEL.search(t)
    if sm:
        ms = sm.group(1).strip()

    return (mm or None), ms

def _extract_elastane_pct(text: str) -> Optional[float]:
    if not text:
        return None
    m = RE_ELASTANE.search(str(text))
    return float(m.group(1)) if m else None

def _guess_fit_profile(text: str) -> str:
    t = str(text).lower()
    if "oversize" in t or "оверсайз" in t:
        return "oversize"
    if "slim" in t or "притален" in t:
        return "slim"
    return "regular"

# -------------------------------------------------------------------------
# WEB PARSING (Async Lamoda-like)
# -------------------------------------------------------------------------
async def fetch_html(url: str, session: aiohttp.ClientSession) -> str:
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
        return await resp.text()

async def parse_lamoda_like(url: str) -> Optional[ParsedItem]:
    return None

# -------------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------------
def _normalize_metrics_blob(metrics_blob: Any) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Возвращает:
      - metrics_dict: исходный JSON (dict)
      - chosen_size: если это формат по размерам, вернёт выбранный ключ размера
    """
    if not isinstance(metrics_blob, dict):
        return {}, None

    # формат по размерам: {"S": {...}, "M": {...}}
    # эвристика: если значения — dict и ключи похожи на размеры
    if metrics_blob and all(isinstance(v, dict) for v in metrics_blob.values()):
        keys = list(metrics_blob.keys())
        # выберем "M" если есть, иначе первый ключ
        chosen = "M" if "M" in metrics_blob else keys[0]
        return metrics_blob, chosen

    # плоский формат
    return metrics_blob, None

# -------------------------------------------------------------------------
# FILE LOADING (DB / JSON)
# -------------------------------------------------------------------------
def load_rows_from_idealfit_sqlite(sqlite_path: str) -> List[Dict[str, Any]]:
    """
    Читает SQLite БД (shop.db).
    Адаптировано под схему ORM (таблица garments, поле metrics JSON).
    Поддерживает metrics: по размерам ИЛИ плоский.
    """
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row

    out: List[Dict[str, Any]] = []
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='garments'")
        if not cur.fetchone():
            return []

        cur.execute("SELECT * FROM garments")
        rows = cur.fetchall()

        for r in rows:
            metrics_json: Dict[str, Any] = {}
            raw_metrics = r["metrics"]
            if raw_metrics:
                try:
                    if isinstance(raw_metrics, str):
                        metrics_json = json.loads(raw_metrics)
                    elif isinstance(raw_metrics, dict):
                        metrics_json = raw_metrics
                except Exception:
                    metrics_json = {}

            metrics_dict, chosen_size = _normalize_metrics_blob(metrics_json)

            # если формат по размерам — берём выбранный size-пакет
            if chosen_size:
                pack = metrics_dict.get(chosen_size, {}) if isinstance(metrics_dict, dict) else {}
            else:
                pack = metrics_dict

            model_metrics = pack.get("model_metrics")
            model_size = pack.get("model_size")
            elastane = pack.get("elastane_pct")
            fit_profile = pack.get("fit_profile") or _guess_fit_profile(r["name"])

            if elastane is None and "description" in r.keys():
                elastane = _extract_elastane_pct(r["description"])

            internal_cat = pack.get("internal_category", "")

            out.append({
                "sku": r["sku"],
                "name": r["name"],
                "category": (r.get("platform", "") or "") + "_" + str(internal_cat),
                "image_url": r["image_url"],
                "url": r.get("url", ""),
                "in_stock": bool(r["in_stock"]),
                "fit_profile": fit_profile,
                "elastane_pct": elastane,
                "model_metrics": model_metrics,
                "model_size": model_size,
                "metrics": metrics_json,  # сохраняем как есть (по размерам или плоский)
                "price": r["price"],
            })

        return out
    except Exception as e:
        print(f"[Parser Error] Чтение SQLite: {e}")
        return []
    finally:
        conn.close()

def load_items_from_local_file(path: str) -> List[ParsedItem]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")

    raw_items: List[Dict[str, Any]] = []
    if p.suffix.lower() in (".db", ".sqlite", ".sqlite3"):
        raw_items = load_rows_from_idealfit_sqlite(str(p))
    elif p.suffix.lower() == ".json":
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            raw_items = data if isinstance(data, list) else data.get("items", [])
        except Exception:
            raw_items = []

    parsed_result: List[ParsedItem] = []
    for r in raw_items:
        if not r.get("sku"):
            continue

        item = ParsedItem(
            sku=str(r["sku"]),
            name=str(r.get("name", "Unknown")),
            image_url=str(r.get("image_url", "")),
            url=str(r.get("url", "")),
            in_stock=bool(r.get("in_stock", True)),
            fit_profile=str(r.get("fit_profile", "regular")),
            elastane_pct=r.get("elastane_pct"),
            model_metrics=r.get("model_metrics"),
            model_size=r.get("model_size"),
            metrics=r.get("metrics"),
        )
        parsed_result.append(item)

    return parsed_result

