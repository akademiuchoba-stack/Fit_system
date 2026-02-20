from dataclasses import dataclass
from typing import Dict, List, Any

@dataclass
class Profile:
    height: float
    chest: float
    waist: float
    hips: float
    shoulders: float
    arm_length: float
    outseam: float
    inseam: float

@dataclass
class FitResult:
    size_label: str
    score: float
    status: str
    status_color: str
    details: Dict[str, str]
    warnings: List[str]

SIZES_ORDER = ['XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL']

# Дизайнерские припуски (ИДЕАЛ)
DESIGN_EASE = {
    'slim': {'top': 2.0, 'bottom': 1.0},
    'regular': {'top': 6.0, 'bottom': 3.0},
    'oversize': {'top': 14.0, 'bottom': 6.0}
}

GRADE_STEP = 4.0 

def calculate_fit(user: Profile, model_size: str, base_data: dict, target_size: str) -> FitResult:
    warnings = []
    details = {}
    score = 100.0

    # 1. Читаем данные
    m_chest = base_data.get('chest', 90.0)
    m_waist = base_data.get('waist', 70.0)
    m_hips = base_data.get('hips', 95.0)
    m_height = base_data.get('height', 175.0) # ВАЖНО: берем рост модели

    fit_profile = base_data.get('fit_profile', 'regular').lower()
    cat_type = base_data.get('category_type', 'top').lower()
    elastane = float(base_data.get('elastane_pct', 0.0))

    # 2. ИДЕАЛЬНЫЙ ПРИПУСК
    ideal_ease = DESIGN_EASE.get(fit_profile, DESIGN_EASE['regular'])
    base_ease_chest = ideal_ease['top'] if cat_type == 'top' else ideal_ease['bottom']
    base_ease_waist = ideal_ease['bottom']
    base_ease_hips = ideal_ease['bottom']

    # 3. ВИРТУАЛЬНАЯ ВЕЩЬ (на модели)
    g0_chest = m_chest + base_ease_chest
    g0_waist = m_waist + base_ease_waist
    g0_hips = m_hips + base_ease_hips

    # 4. МАСШТАБИРОВАНИЕ
    try:
        steps = SIZES_ORDER.index(target_size.upper()) - SIZES_ORDER.index(model_size.upper())
    except ValueError:
        steps = 0 

    gt_chest = g0_chest + (steps * GRADE_STEP)
    gt_waist = g0_waist + (steps * GRADE_STEP)
    gt_hips = g0_hips + (steps * GRADE_STEP)

    # 5. ПРИМЕРКА НА ПОЛЬЗОВАТЕЛЯ
    user_ease_chest = gt_chest - user.chest
    user_ease_waist = gt_waist - user.waist
    user_ease_hips = gt_hips - user.hips

    # 6. ОЦЕНКА ОТКЛОНЕНИЙ (ШИРИНА)
    strict_tol = 2.0 # Идеальное попадание: +/- 2 см
    loose_tol = 4.5 if elastane >= 2 else 3.0 # Приемлемое попадание

    def eval_zone(zone_name, user_val, user_ease, base_ease, gt_val):
        nonlocal score
        delta = user_ease - base_ease # Разница между реальностью и задумкой
        
        if abs(delta) <= strict_tol:
            details[zone_name] = f"Вещь {gt_val:.1f} - Вы {user_val:.1f} = Припуск {user_ease:+.1f}см -> [green]ОПТИМАЛЬНО[/green]"
        elif abs(delta) <= loose_tol:
            penalty = abs(delta) * 2.0
            score -= penalty
            details[zone_name] = f"Припуск {user_ease:+.1f}см (Идеал +{base_ease}см) -> [yellow]ПРИЕМЛЕМО[/yellow]"
        elif delta < -loose_tol:
            penalty = abs(delta) * (5.0 if elastane < 2 else 3.0)
            score -= penalty
            if user_ease < 0: warnings.append(f"В зоне '{zone_name}' вещь меньше тела на {abs(user_ease):.1f}см!")
            details[zone_name] = f"Припуск {user_ease:+.1f}см (Идеал +{base_ease}см) -> [red]ТЕСНО[/red]"
        else:
            score -= abs(delta) * 2.0
            details[zone_name] = f"Припуск {user_ease:+.1f}см (Идеал +{base_ease}см) -> [magenta]СВОБОДНО[/magenta]"

    if cat_type == 'top':
        eval_zone('Грудь', user.chest, user_ease_chest, base_ease_chest, gt_chest)
        eval_zone('Талия', user.waist, user_ease_waist, base_ease_waist, gt_waist)
    else:
        # Для низа грудь игнорируем, считаем талию и БЕДРА
        eval_zone('Талия', user.waist, user_ease_waist, base_ease_waist, gt_waist)
        eval_zone('Бедра', user.hips, user_ease_hips, base_ease_hips, gt_hips)

    # 7. ОЦЕНКА РОСТА И ДЛИНЫ (АНАТОМИЧЕСКИЙ РАСЧЕТ)
    height_diff = user.height - m_height
    
    # Если разница в росте существенная (> 3 см), начинаем считать длины
    if abs(height_diff) > 3.0:
        if cat_type == 'bottom':
            # Ноги человека составляют примерно 60% от его роста
            len_diff = height_diff * 0.6 
            if len_diff > 2.5:
                details['Длина'] = f"Ваш рост ({user.height}) больше модели ({m_height}). Штанины будут короче на ~{len_diff:.1f}см."
                score -= len_diff * 2.0 # Жесткий штраф за "подстреленность"
                warnings.append(f"Штанины могут быть коротковаты (-{len_diff:.1f}см)")
            elif len_diff < -2.5:
                details['Длина'] = f"Модель выше вас. Брюки будут длиннее на ~{abs(len_diff):.1f}см."
                score -= abs(len_diff) * 1.0 # Длинные можно подшить, штраф меньше
        else:
            # Рукава и торс составляют примерно 35-40% от роста
            len_diff = height_diff * 0.35 
            if len_diff > 2.5:
                details['Длина'] = f"Рост больше эталона. Рукава/изделие будут короче на ~{len_diff:.1f}см."
                score -= len_diff * 1.5
            elif len_diff < -2.5:
                details['Длина'] = f"Изделие будет длиннее задуманного на ~{abs(len_diff):.1f}см."
                score -= abs(len_diff) * 1.0

    # Финализация
    score = max(0.0, min(100.0, score))
    if score >= 85 and not warnings:
        status, color = "Идеально", "green"
    elif score >= 65:
        status, color = "Хорошо", "cyan"
    elif score >= 45:
        status, color = "Приемлемо", "yellow"
    else:
        status, color = "Не подходит", "red"

    return FitResult(target_size, score, status, color, details, warnings)