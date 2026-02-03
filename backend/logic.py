
import math
from typing import Dict, Any

def calculate_fit(user: Dict[str, Any], garment: Dict[str, Any], fabric_stretch: float = 1.0):
    """
    Математическое ядро расчета посадки (Fit Logic).
    
    :param user: Метрики пользователя (chest, shoulders, waist, etc.)
    :param garment: Метрики изделия для конкретного размера
    :param fabric_stretch: Коэффициент растяжимости (1.0 = не тянется)
    """
    
    # 1. Расчет прибавки (Ease)
    # По ГОСТу/стандартам: ease = Полуобхват изделия - Полуобхват тела
    # Если ткань тянется (stretch > 1.1), допускается отрицательная прибавка (Negative Ease)
    ease_chest = garment['chest'] - (user['chest'] / 2)
    
    # 2. Компенсация спущенного плеча (Dropped Shoulder Correction)
    # Если плечо изделия шире плеча пользователя, рукав фактически становится длиннее.
    # Расчет: эффективная_длина_рукава = рукав_изделия + (плечо_изделия - плечо_пользователя_пополам)
    # Применяем тригонометрическую поправку на угол наклона (считаем ~15 градусов)
    shoulder_diff = garment['shoulder'] - (user['shoulders'] / 2)
    effective_sleeve = garment['sleeve'] + (shoulder_diff * math.cos(math.radians(15)))
    sleeve_error = effective_sleeve - user['arm_length']

    # 3. Коррекция на живот (Abdominal/Arc Length Differential)
    # Если обхват талии больше обхвата груди, передняя полочка изделия задирается.
    # Штрафуем длину изделия (length) на разницу дуг.
    stomach_penalty = 0
    if user['waist'] > user['chest']:
        # Эмпирическая формула: каждые 2 см разницы требуют +1 см длины
        stomach_penalty = (user['waist'] - user['chest']) / 4
    
    effective_length = garment['length'] - stomach_penalty
    length_verdict = "ОК"
    if effective_length < (user['height'] * 0.4): # Упрощенно: длина должна быть > 40% роста для верха
        length_verdict = "Коротковато"

    # 4. Итоговый Fit Score (0-100)
    # Идеальный chest_ease для Regular Fit ~ 4-6 см
    ideal_ease = 5.0
    if fabric_stretch > 1.1: ideal_ease = 0.0 # Для стрейч-тканей
    
    chest_score = max(0, 100 - abs(ease_chest - ideal_ease) * 10)
    sleeve_score = max(0, 100 - abs(sleeve_error) * 5)
    
    fit_score = (chest_score * 0.6) + (sleeve_score * 0.4)
    
    # Формирование вердикта
    details = []
    if ease_chest < 2: details.append("Тесно в груди")
    elif ease_chest > 10: details.append("Оверсайз")
    else: details.append("Грудь: Идеально")
    
    if abs(sleeve_error) < 2: details.append("Рукав: ОК")
    elif sleeve_error > 2: details.append(f"Рукав: Длинно на {round(sleeve_error)}см")
    else: details.append(f"Рукав: Коротко на {round(abs(sleeve_error))}см")

    return {
        "score": round(fit_score),
        "verdict": "Идеально" if fit_score > 85 else "Хорошо" if fit_score > 70 else "Посредственно",
        "details": "; ".join(details),
        "metrics_comparison": {
            "garment_chest": garment['chest'],
            "user_chest_half": user['chest']/2,
            "effective_sleeve": round(effective_sleeve, 1),
            "user_arm": user['arm_length']
        }
    }
