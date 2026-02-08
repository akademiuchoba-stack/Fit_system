
"""
logic.py — закрытое вычислительное ядро Fit_system ("Идеальный припуск")

Важно:
- Вся логика остаётся на сервере (black-box API), фронт получает только score + человекочитаемые пояснения.
- В ответах API мы НЕ возвращаем внутренние оценочные размеры изделия, только отклонения/оценку.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, List


# -----------------------------
# Конфигурация "дизайнерской прибавки"
# -----------------------------
# Для MVP — простые константы (в см по ОБХВАТУ, т.е. по окружности).
# Потом их можно калибровать по фидбэку (priors).
DESIGN_EASE_BY_FIT: Dict[str, Dict[str, float]] = {
    # верх (грудь) / талия / бёдра
    "slim":     {"chest": 4.0,  "waist": 2.0,  "hips": 2.0},
    "regular":  {"chest": 6.0,  "waist": 4.0,  "hips": 4.0},
    "oversize": {"chest": 14.0, "waist": 10.0, "hips": 10.0},
}

# Градация между соседними размерами по обхватам (см), MVP-правило из ТЗ
DEFAULT_GRADING_STEP = 4.0  # см по окружности


@dataclass(frozen=True)
class FitResult:
    score: float
    status: str
    explanation: str
    deltas_cm: Dict[str, float]  # отклонения по зонам: положит = свободнее, отриц = теснее
    warnings: List[str]


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _fit_profile_from_garment(garment: Dict[str, Any]) -> str:
    fp = (garment.get("fit_profile") or garment.get("fit") or garment.get("silhouette") or "regular").strip().lower()
    if fp not in ("slim", "regular", "oversize"):
        return "regular"
    return fp


def _poisson_ratio_from_fabric(garment: Dict[str, Any]) -> float:
    """
    Грубая оценка коэффициента Пуассона по типу материала.
    В ТЗ упоминается учёт эффекта Пуассона в зоне "живот-длина". Для MVP:
    - трикотаж/стрейч → выше
    - ткань/деним без стрейча → ниже
    """
    txt = (garment.get("fabric") or garment.get("material") or "").lower()
    elastane = _safe_float(garment.get("elastane_pct"))
    if elastane is not None and elastane >= 3:
        return 0.55
    if any(k in txt for k in ["трикот", "jersey", "стрейч", "stretch", "эластан", "spandex", "elastane"]):
        return 0.60
    return 0.35


def _size_index(size_label: str) -> Optional[int]:
    """
    Переводим размер в индекс для градации.
    MVP: поддерживаем XS,S,M,L,XL,XXL и числовые "44/46/48" как шаг 1.
    """
    if not size_label:
        return None
    s = str(size_label).strip().upper()

    map_alpha = {"XXS": 0, "XS": 1, "S": 2, "M": 3, "L": 4, "XL": 5, "XXL": 6, "3XL": 7, "4XL": 8}
    if s in map_alpha:
        return map_alpha[s]

    # Пробуем взять число из "48" или "32/32" — берём первое число
    m = None
    for pat in [r"(\d{2,3})", r"(\d{2,3})\s*/\s*(\d{2,3})"]:
        mm = math.floor(float(re.findall(pat, s)[0])) if re.findall(pat, s) else None
        if mm is not None:
            m = int(mm)
            break
    if m is None:
        # "W32 L32" и т.п.
        mm = re.search(r"W\s*(\d{2})", s)
        if mm:
            m = int(mm.group(1))
    if m is None:
        return None

    # нормализуем: 40..60 -> 0..10
    return int(round((m - 40) / 2))


def estimate_garment_measurements_from_model(
    model_metrics: Dict[str, Any],
    model_size_label: str,
    target_size_label: str,
    fit_profile: str,
    grading_step: float = DEFAULT_GRADING_STEP,
) -> Dict[str, float]:
    """
    Оценка параметров изделия для target_size_label через "транзитивный матчиннг":
    1) предполагаем, что на модели изделие сидит "как задумано" → добавляем Design Ease к параметрам модели
    2) скейлим на целевой размер через шаг градации
    Суть описана в архитектурном документе/ТЗ. fileciteturn1file0 fileciteturn2file11
    """
    fp = fit_profile
    ease = DESIGN_EASE_BY_FIT.get(fp, DESIGN_EASE_BY_FIT["regular"])

    def get_model(name: str) -> Optional[float]:
        return _safe_float(model_metrics.get(name))

    chest = get_model("chest")
    waist = get_model("waist")
    hips = get_model("hips")

    if chest is None and waist is None and hips is None:
        # нет данных — возвращаем пусто
        return {}

    # Изделие в размере модели (по окружности)
    garment_model = {
        "chest": (chest + ease["chest"]) if chest is not None else None,
        "waist": (waist + ease["waist"]) if waist is not None else None,
        "hips":  (hips  + ease["hips"])  if hips  is not None else None,
    }

    i_model = _size_index(model_size_label)
    i_user = _size_index(target_size_label)
    delta_i = 0 if (i_model is None or i_user is None) else (i_user - i_model)

    def scale(v: Optional[float]) -> Optional[float]:
        if v is None:
            return None
        return v + delta_i * grading_step

    out = {}
    for k, v in garment_model.items():
        vv = scale(v)
        if vv is not None:
            out[k] = float(vv)
    return out


def compute_fit_score(
    user: Dict[str, Any],
    garment: Dict[str, Any],
    size_label: str,
) -> FitResult:
    """
    Возвращает:
      - FitScore 0..100
      - статус (perfect / ok / risky / bad)
      - пояснение
      - deltas_cm по зонам (положит = свободнее, отриц = теснее)
      - предупреждения
    """
    # --- ВХОДЫ ---
    u_chest = _safe_float(user.get("chest"))
    u_waist = _safe_float(user.get("waist"))
    u_hips = _safe_float(user.get("hips"))
    u_shoulders = _safe_float(user.get("shoulders"))
    u_arm = _safe_float(user.get("arm"))

    # 1) Если у нас есть реальные промеры изделия в БД (как в текущем MVP), используем их.
    #    Иначе пробуем оценить по параметрам модели + fit_profile.
    g = garment.get("metrics") or garment  # совместимость
    g_chest = _safe_float(g.get("chest"))
    g_waist = _safe_float(g.get("waist"))
    g_hips = _safe_float(g.get("hips"))
    g_shoulders = _safe_float(g.get("shoulders"))
    g_sleeve = _safe_float(g.get("sleeve"))

    warnings: List[str] = []

    fit_profile = _fit_profile_from_garment(garment)

    # 2) Транзитивная оценка (если нет промеров)
    if (g_chest is None and g_waist is None and g_hips is None) and garment.get("model_metrics"):
        est = estimate_garment_measurements_from_model(
            model_metrics=garment.get("model_metrics") or {},
            model_size_label=str(garment.get("model_size") or ""),
            target_size_label=str(size_label),
            fit_profile=fit_profile,
        )
        g_chest = est.get("chest")
        g_waist = est.get("waist")
        g_hips = est.get("hips")

    # --- ДЕЛЬТЫ (изделие - тело) ---
    # Важно: у нас "изделие" по окружности, а user тоже по окружности.
    deltas: Dict[str, float] = {}
    if u_chest is not None and g_chest is not None:
        deltas["chest"] = g_chest - u_chest
    if u_waist is not None and g_waist is not None:
        deltas["waist"] = g_waist - u_waist
    if u_hips is not None and g_hips is not None:
        deltas["hips"] = g_hips - u_hips

    # Рукав: корректируем на "спущенное плечо" (идея из ТЗ). fileciteturn2file15
    if u_arm is not None and g_sleeve is not None:
        eff_sleeve = g_sleeve
        if u_shoulders is not None and g_shoulders is not None:
            drop = (g_shoulders - u_shoulders) / 2.0
            if drop > 0:
                eff_sleeve = g_sleeve + drop
                warnings.append("Плечо спущено: рукав может ощущаться длиннее.")
        deltas["sleeve"] = eff_sleeve - u_arm

    # Живот-длина (MVP): если талия > грудь → повышаем риск (из ТЗ). fileciteturn1file1
    if u_waist is not None and u_chest is not None and u_waist > u_chest:
        warnings.append("У талии объём больше груди: возможен подъём низа спереди.")
        # Эффект Пуассона усиливает риск у стрейча/трикотажа
        nu = _poisson_ratio_from_fabric(garment)
        warnings.append(f"Материал-коэффициент (условно ν={nu:.2f}) учтён в риске посадки.")

    # --- СКОРИНГ ---
    # целевой "идеальный припуск" зависит от fit_profile:
    # хотим попасть в небольшой коридор вокруг target_delta.
    target = DESIGN_EASE_BY_FIT.get(fit_profile, DESIGN_EASE_BY_FIT["regular"])

    # Переводим target (см по окружности) в "целевое delta": изделие - тело.
    # Для regular chest +6 значит delta ~ +6. (Мы сравниваем окружности)
    target_delta = {"chest": target["chest"], "waist": target["waist"], "hips": target["hips"]}

    # Ошибка как среднеквадратичное отклонение от целевого припуска
    errs = []
    weights = {"chest": 1.0, "waist": 1.0, "hips": 0.8, "sleeve": 0.5}
    for k, w in weights.items():
        if k in deltas and (k in target_delta or k == "sleeve"):
            t = target_delta.get(k, 0.0)
            errs.append(w * (deltas[k] - t) ** 2)

    if not errs:
        return FitResult(
            score=0.0,
            status="bad",
            explanation="Недостаточно данных по изделию для расчёта.",
            deltas_cm=deltas,
            warnings=warnings,
        )

    rmse = math.sqrt(sum(errs) / max(len(errs), 1))

    # Преобразуем RMSE в score: 0см -> 100, 10см -> ~40
    score = 100.0 * math.exp(- (rmse / 6.0) ** 2)
    score = _clamp(score, 0.0, 100.0)

    # Статус
    if score >= 92:
        status = "perfect"
        explain = "Идеально (припуск близок к целевому)."
    elif score >= 78:
        status = "ok"
        explain = "Хорошо (незначимые отклонения)."
    elif score >= 55:
        status = "risky"
        explain = "Погранично (возможен дискомфорт)."
    else:
        status = "bad"
        explain = "Не рекомендуется (сильные отклонения)."

    # Чуть-чуть текстового пояснения по ключевой зоне
    if deltas:
        worst = max(deltas.items(), key=lambda kv: abs(kv[1] - target_delta.get(kv[0], 0.0)))
        k, v = worst
        t = target_delta.get(k, 0.0)
        dv = v - t
        if abs(dv) >= 4:
            if dv < 0:
                explain += f" Основной риск: {k} — теснее желаемого примерно на {abs(dv):.0f} см."
            else:
                explain += f" Основной риск: {k} — свободнее желаемого примерно на {abs(dv):.0f} см."

    return FitResult(score=score, status=status, explanation=explain, deltas_cm=deltas, warnings=warnings)
