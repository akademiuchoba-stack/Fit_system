
"""
parser.py — модуль загрузки/обогащения каталога для Fit_system.

⚠️ Важно про законность/ToS:
- Этот модуль рассчитан на работу с ОТКРЫТЫМИ страницами и разрешёнными источниками.
- В нём НЕТ обхода SSL pinning, взлома мобильных API, ротации прокси и т.п.
- Если у магазина есть официальный API/экспорт — лучше подключаться к нему.

Архитектурные идеи:
- Lamoda: извлечение JSON из window.__INITIAL_STATE__ как наиболее стабильного источника. fileciteturn2file0
- NLP-извлечение биометрии из текста через regex-паттерны (ОГ-ОТ-ОБ, рост, "параметры модели"). fileciteturn2file8
- Возможность "подмешать" промеры из магазина вручную (в твоём UI) и сохранить в БД.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from bs4 import BeautifulSoup
from thefuzz import fuzz


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

    # то, что помогает алгоритму "Идеальный припуск"
    model_metrics: Optional[Dict[str, Any]] = None   # {"height":189,"chest":102,"waist":85,"hips":98}
    model_size: Optional[str] = None

    # промеры изделия (если источник их даёт напрямую)
    metrics: Optional[Dict[str, Any]] = None         # {"chest":..., "waist":..., "hips":..., "shoulders":..., "sleeve":...}


# -----------------------------
# Regex / NLP: извлечение биометрии модели из описаний
# -----------------------------
RE_TRIPLE = re.compile(r"(\d{2,3})\s*[-—–]\s*(\d{2,3})\s*[-—–]\s*(\d{2,3})")
RE_CHEST = re.compile(r"(?:грудь|ог|bust)[\s:.-]*(\d{2,3})", re.I)
RE_WAIST = re.compile(r"(?:талия|от|waist)[\s:.-]*(\d{2,3})", re.I)
RE_HIPS  = re.compile(r"(?:б[её]дра|об|hips)[\s:.-]*(\d{2,3})", re.I)
RE_HEIGHT = re.compile(r"(?:рост|height)[\s:.-]*(\d{3})", re.I)
RE_MODEL_SIZE = re.compile(r"(?:размер|size)[\s\w]*?([XSML]{1,3}|\d{2,3}\s*/\s*\d{2,3}|\d{2,3})", re.I)


def extract_model_metrics_from_text(text: str) -> Dict[str, Any]:
    """
    Вытаскиваем из текста:
    - рост
    - ОГ/ОТ/ОБ (в двух форматах: "89-60-84" или "грудь 102, талия 85, бёдра 98")
    - размер на модели
    """
    t = " ".join((text or "").split()).lower()

    out: Dict[str, Any] = {}

    # 1) тройка "83-63-92"
    m = RE_TRIPLE.search(t)
    if m:
        out["chest"] = int(m.group(1))
        out["waist"] = int(m.group(2))
        out["hips"] = int(m.group(3))

    # 2) именованные
    for key, rx in [("chest", RE_CHEST), ("waist", RE_WAIST), ("hips", RE_HIPS)]:
        mm = rx.search(t)
        if mm and key not in out:
            out[key] = int(mm.group(1))

    # 3) рост
    mh = RE_HEIGHT.search(t)
    if mh:
        out["height"] = int(mh.group(1))

    # 4) размер на модели
    ms = RE_MODEL_SIZE.search(t)
    if ms:
        out["model_size"] = ms.group(1).strip().upper().replace(" ", "")

    # sanity check (простые правила из ТЗ)
    if "waist" in out and out["waist"] < 50:
        out.pop("waist", None)
    if "chest" in out and "waist" in out and out["waist"] > out["chest"] + 40:
        # подозрительно
        pass

    return out


def guess_fit_profile(text: str) -> str:
    t = (text or "").lower()
    if "oversize" in t or "оверсайз" in t:
        return "oversize"
    if "slim" in t or "узк" in t:
        return "slim"
    return "regular"


def try_extract_elastane_pct(text: str) -> Optional[float]:
    t = (text or "").lower()
    #  "5% эластан" / "elastane 3%"
    m = re.search(r"(\d+(?:\.\d+)?)\s*%?\s*(эластан|elastane|spandex|лайкра)", t)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            return None
    return None


# -----------------------------
# Lamoda: __INITIAL_STATE__
# -----------------------------
async def parse_lamoda_product(url: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
    """
    Извлекаем окно initial state.
    (Если структура изменится — добавим fallback на CSS/DL позже.)
    """
    async with session.get(url) as resp:
        html = await resp.text()

    # Обычно выглядит как window.__INITIAL_STATE__ = {...};
    m = re.search(r"window\.__INITIAL_STATE__\s*=\s*({.*?})\s*;\s*</script>", html, re.S)
    if not m:
        # fallback: ищем любой script с этой переменной
        m = re.search(r"window\.__INITIAL_STATE__\s*=\s*({.*?});", html, re.S)
    if not m:
        return {"ok": False, "error": "INITIAL_STATE not found"}

    raw = m.group(1)

    # Иногда там экранирование. Пробуем аккуратно распарсить.
    try:
        data = json.loads(raw)
    except Exception:
        # попытка очистки "undefined" и хвостов
        cleaned = raw.replace("undefined", "null")
        data = json.loads(cleaned)

    return {"ok": True, "state": data}


# -----------------------------
# Импорт каталога из файла (самый надёжный способ для MVP)
# -----------------------------
def load_items_from_local_file(path: str) -> List[ParsedItem]:
    """
    Поддержка JSON/JSONL/CSV (CSV — с минимальным набором колонок).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")

    if p.suffix.lower() in (".json",):
        obj = json.loads(p.read_text(encoding="utf-8"))
        rows = obj if isinstance(obj, list) else obj.get("items", [])
    elif p.suffix.lower() in (".jsonl", ".ndjson"):
        rows = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    elif p.suffix.lower() in (".csv",):
        import csv
        rows = []
        with p.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)
    else:
        raise ValueError("Поддерживаются .json, .jsonl, .csv")

    out: List[ParsedItem] = []
    for r in rows:
        sku = str(r.get("sku") or r.get("article") or r.get("id") or "").strip()
        if not sku:
            continue
        name = str(r.get("name") or r.get("title") or "").strip() or sku

        desc = str(r.get("description") or "")
        fit_profile = str(r.get("fit_profile") or guess_fit_profile(desc))
        elastane = r.get("elastane_pct")
        try:
            elastane = float(elastane) if elastane is not None and str(elastane).strip() != "" else try_extract_elastane_pct(desc)
        except Exception:
            elastane = try_extract_elastane_pct(desc)

        model_metrics = None
        model_size = None
        mm = extract_model_metrics_from_text(desc)
        if mm:
            model_metrics = {k: v for k, v in mm.items() if k in ("height", "chest", "waist", "hips")}
            model_size = mm.get("model_size")

        metrics = r.get("metrics")
        if isinstance(metrics, str) and metrics.strip().startswith("{"):
            try:
                metrics = json.loads(metrics)
            except Exception:
                metrics = None

        out.append(ParsedItem(
            sku=sku,
            name=name,
            brand=str(r.get("brand") or ""),
            category=str(r.get("category") or ""),
            image_url=str(r.get("image_url") or r.get("image") or ""),
            url=str(r.get("url") or ""),
            in_stock=bool(r.get("in_stock") if r.get("in_stock") is not None else True),
            size_label=str(r.get("size_label") or r.get("size") or ""),
            fit_profile=fit_profile if fit_profile in ("slim", "regular", "oversize") else "regular",
            fabric=str(r.get("fabric") or r.get("material") or ""),
            elastane_pct=elastane,
            model_metrics=model_metrics,
            model_size=model_size,
            metrics=metrics if isinstance(metrics, dict) else None,
        ))

    return out


# -----------------------------
# Fuzzy matching (если тебе нужно сшивать источники)
# -----------------------------
def fuzzy_match_name(a: str, b: str) -> int:
    return fuzz.token_set_ratio(a or "", b or "")
