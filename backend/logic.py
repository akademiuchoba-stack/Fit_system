from dataclasses import dataclass
from typing import Dict, List, Any
import math

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

    # 1. Читаем данные модели и изделия
    m_chest = base_data.get('chest', 90.0)
    m_waist = base_data.get('waist', 70.0)
    m_hips = base_data.get('hips', 95.0)
    m_height = base_data.get('height', 175.0)

    fit_profile = base_data.get('fit_profile', 'regular').lower()
    cat_type = base_data.get('category_type', 'top').lower()
    elastane = float(base_data.get('elastane_pct', 0.0))

    # 2. ИДЕАЛЬНЫЙ ПРИПУСК (задумка дизайнера)
    ideal_ease = DESIGN_EASE.get(fit_profile, DESIGN_EASE['regular'])
    base_ease_chest = ideal_ease['top'] if cat_type == 'top' else ideal_ease['bottom']
    base_ease_waist = ideal_ease['bottom']
    base_ease_hips = ideal_ease['bottom']

    # 3. ВИРТУАЛЬНАЯ ВЕЩЬ (базовые габариты на модели)
    g0_chest = m_chest + base_ease_chest
    g0_waist = m_waist + base_ease_waist
    g0_hips = m_hips + base_ease_hips

    # 4. МАСШТАБИРОВАНИЕ (грейдирование под целевой размер)
    try:
        steps = SIZES_ORDER.index(target_size.upper()) - SIZES_ORDER.index(model_size.upper())
    except ValueError:
        steps = 0 

    gt_chest = g0_chest + (steps * GRADE_STEP)
    gt_waist = g0_waist + (steps * GRADE_STEP)
    gt_hips = g0_hips + (steps * GRADE_STEP)

    # 5. ПРИМЕРКА НА ПОЛЬЗОВАТЕЛЯ (фактические припуски)
    user_ease_chest = gt_chest - user.chest
    user_ease_waist = gt_waist - user.waist
    user_ease_hips = gt_hips - user.hips

    # 6. ОЦЕНКА ОТКЛОНЕНИЙ (ШИРИНА)
    strict_tol = 2.0 
    loose_tol = 4.5 if elastane >= 2 else 3.0 

    def eval_zone(zone_name, user_val, user_ease, base_ease, gt_val):
        nonlocal score
        delta = user_ease - base_ease 
        
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
        
        # --- МАТЕМАТИКА: ШТРАФ НА ВЫСТУПАЮЩИЙ ЖИВОТ ---
        if user.waist > user.chest:
            # Разница радиусов дает нам размер выступа спереди
            belly_protrusion = (user.waist - user.chest) / math.pi
            base_torso_length = 20.0 # Условное расстояние от груди до талии по прямой
            
            # Длина дуги по теореме Пифагора
            arc_length = math.sqrt(base_torso_length**2 + belly_protrusion**2)
            length_loss = arc_length - base_torso_length
            
            # Ткань с эластаном частично компенсирует натяжение
            stretch_factor = max(0.2, 1.0 - (elastane / 10.0))
            eff_loss = length_loss * stretch_factor
            
            if eff_loss > 0.5:
                penalty = eff_loss * 3.0
                score -= penalty
                warnings.append(f"Из-за объема в талии передняя часть изделия может 'подскочить' на ~{eff_loss:.1f}см.")
                details['Особенность посадки'] = f"Геометрический штраф за натяжение ткани на животе: -{penalty:.1f} баллов."

    else:
        # Для низа грудь игнорируем, считаем талию и БЕДРА
        eval_zone('Талия', user.waist, user_ease_waist, base_ease_waist, gt_waist)
        eval_zone('Бедра', user.hips, user_ease_hips, base_ease_hips, gt_hips)

    # 7. ОЦЕНКА РОСТА И ДЛИНЫ (АНАТОМИЧЕСКИЙ РАСЧЕТ + ШАГОВЫЙ ШОВ)
    height_diff = user.height - m_height
    
    if cat_type == 'bottom':
        # --- МАТЕМАТИКА: РАСЧЕТ ПО ШАГОВОМУ ШВУ ---
        # Если в базе нет шагового шва модели, аппроксимируем его как 45% от роста модели
        m_inseam = base_data.get('inseam', m_height * 0.45)
        
        # Масштабируем длину штанин модели в зависимости от размера (примерно +1 см на грейд)
        gt_inseam = m_inseam + (steps * 1.0)
        inseam_diff = user.inseam - gt_inseam
        
        if inseam_diff > 2.5:
            details['Длина (Шаговый шов)'] = f"Ваш шаг ({user.inseam:.1f}) больше расчетного ({gt_inseam:.1f}). Штанины будут короче на ~{inseam_diff:.1f}см."
            score -= inseam_diff * 2.0 # Штраф за подстреленность
            warnings.append(f"Брюки могут быть коротковаты (-{inseam_diff:.1f}см)")
        elif inseam_diff < -2.5:
            details['Длина (Шаговый шов)'] = f"Расчетная длина штанин ({gt_inseam:.1f}) больше вашей ({user.inseam:.1f}). Брюки будут длиннее на ~{abs(inseam_diff):.1f}см."
            score -= abs(inseam_diff) * 1.0 # Длинные можно подшить (штраф меньше)
        else:
            details['Длина (Шаговый шов)'] = f"Длина штанин оптимальна (разница {inseam_diff:+.1f}см) -> [green]ИДЕАЛЬНО[/green]"
            
    else:
        # Для верха оставляем базовый расчет по пропорциям роста (рукава и торс ~35% от роста)
        if abs(height_diff) > 3.0:
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