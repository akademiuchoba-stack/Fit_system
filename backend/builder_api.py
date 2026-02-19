from __future__ import annotations

import json
import os
import re
import sqlite3
from typing import Any, Dict, List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOP_DB_PATH = os.path.join(PROJECT_ROOT, "shops", "shop.db")


def _ensure_db():
    os.makedirs(os.path.dirname(SHOP_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(SHOP_DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS garments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE,
            name TEXT,
            platform TEXT,
            image_url TEXT,
            price REAL,
            in_stock BOOLEAN,
            metrics JSON
        )
    """)
    conn.commit()
    conn.close()


def parse_text_data(text: str) -> Dict[str, Any]:
    metrics = {
        "model_metrics": {},
        "model_size": None,
        "elastane_pct": 0,
        "fabric": "Unknown",
        "fit_profile": "regular"
    }

    if not text:
        return metrics

    clean = re.sub(r"\s+", " ", text.lower())

    m = re.search(r"(\d{2,3})\s*-\s*(\d{2,3})\s*-\s*(\d{2,3})", clean)
    if m:
        metrics["model_metrics"] = {
            "chest": int(m.group(1)),
            "waist": int(m.group(2)),
            "hips": int(m.group(3))
        }

    size = re.search(r"размер.*?([a-z0-9]+)", clean)
    if size:
        metrics["model_size"] = size.group(1).upper()

    elastane = re.search(r"(\d+)\s*%\s*(эластан|spandex|lycra)", clean)
    if elastane:
        metrics["elastane_pct"] = int(elastane.group(1))

    return metrics


def upsert_garment(payload: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_db()

    sku = payload.get("sku")
    if not sku:
        raise ValueError("SKU required")

    name = payload.get("name") or "O'stin item"
    price = float(payload.get("price") or 0)

    text = payload.get("text") or ""
    parsed = parse_text_data(text)

    model_size = payload.get("model_size") or parsed.get("model_size") or "M"

    metrics = {
        model_size: {
            "model_metrics": parsed.get("model_metrics"),
            "elastane_pct": parsed.get("elastane_pct"),
            "fabric": parsed.get("fabric"),
            "fit_profile": payload.get("fit_profile") or parsed.get("fit_profile"),
            "real_measurements": payload.get("real_measurements") or {},
            "try_on": payload.get("try_on") or {}
        }
    }

    conn = sqlite3.connect(SHOP_DB_PATH)
    c = conn.cursor()

    c.execute("SELECT id FROM garments WHERE sku=?", (sku,))
    exists = c.fetchone()

    if exists:
        c.execute("""
            UPDATE garments
            SET name=?, price=?, metrics=?, in_stock=1
            WHERE sku=?
        """, (name, price, json.dumps(metrics, ensure_ascii=False), sku))
        action = "updated"
    else:
        c.execute("""
            INSERT INTO garments (sku, name, platform, price, image_url, in_stock, metrics)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (sku, name, "ostin", price, "", 1, json.dumps(metrics, ensure_ascii=False)))
        action = "created"

    conn.commit()
    conn.close()

    return {"ok": True, "action": action, "sku": sku}


def list_garments(limit: int = 50):
    _ensure_db()
    conn = sqlite3.connect(SHOP_DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM garments ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows
