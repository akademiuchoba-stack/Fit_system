
from typing import Dict, List, Any

# Константы "золотого сечения" припусков (защищено на сервере)
IDEAL_EASE_NORMS = {
    "CHEST": {"min": 4.0, "max": 8.0},
    "WAIST": {"min": 2.0, "max": 5.0},
    "HIPS": {"min": 2.0, "max": 6.0}
}

def calculate_fit_verdict(user_params: Dict[str, Any], product_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ядро алгоритма 'Идеальный припуск'.
    Рассчитывает соответствие на основе векторов тела, изделия и свойств ткани.
    """
    details = []
    total_score = 5.0
    
    # 1. Расчет припуска по груди
    chest_ease = product_params["garment_chest"] - user_params["chest"]
    is_stretch = product_params.get("elasticity_percent", 0) > 3
    
    if product_params.get("category") == "верх":
        if IDEAL_EASE_NORMS["CHEST"]["min"] <= chest_ease <= IDEAL_EASE_NORMS["CHEST"]["max"]:
            details.append({"zone": "Грудь", "status": "OK", "message": "Идеальный объем"})
        elif chest_ease < 0:
            if is_stretch and product_params["garment_chest"] >= user_params["chest"] * 0.94:
                details.append({"zone": "Грудь", "status": "Slim", "message": "Плотная посадка (Stretch)"})
                total_score -= 0.5
            else:
                details.append({"zone": "Грудь", "status": "Tight", "message": "Будет тесно"})
                total_score -= 2.5
        else:
            msg = "Оверсайз" if chest_ease > 12 else "Свободно"
            details.append({"zone": "Грудь", "status": "OK", "message": msg})

    # 2. Расчет припуска по талии
    waist_ease = product_params["garment_waist"] - user_params["waist"]
    if waist_ease < 1.5:
        details.append({"zone": "Талия", "status": "Tight", "message": "Тесно в поясе"})
        total_score -= 1.5
    elif waist_ease > 10:
        details.append({"zone": "Талия", "status": "Loose", "message": "Свободно"})
        total_score -= 0.5
    else:
        details.append({"zone": "Талия", "status": "OK", "message": "Комфортно"})

    # Определение финального вердикта
    score = max(0, total_score)
    if score >= 4.5:
        label, color = "Идеально", "bg-green-600"
    elif score >= 3.5:
        label, color = "Хорошо", "bg-blue-500"
    elif score >= 2.5:
        label, color = "Туго", "bg-yellow-500"
    else:
        label, color = "Не подходит", "bg-red-500"

    return {
        "score": round(score, 1),
        "label": label,
        "color": color,
        "details": details
    }
