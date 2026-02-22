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

def grade_girth(base_val: float, model_size: str, target_size: str) -> float:
    """
    Нелинейное грейдирование обхватов (Сетка O'stin).
    До L шаг +4 см, после L шаг +8 см.
    """
    mapping = {'XS': -8.0, 'S': -4.0, 'M': 0.0, 'L': 4.0, 'XL': 12.0, 'XXL': 20.0, '3XL': 28.0}
    offset_model = mapping.get(model_size.upper(), 0.0)
    offset_target = mapping.get(target_size.upper(), 0.0)
    return base_val + (offset_target - offset_model)

def grade_length(base_val: float, model_size: str, target_size: str) -> float:
    """Грейдирование длины (рукава, штанины). Обычно растет линейно по 1 см на размер."""
    try:
        steps = SIZES_ORDER.index(target_size.upper()) - SIZES_ORDER.index(model_size.upper())
    except ValueError:
        steps = 0
    return base_val + (steps * 1.0)

def calculate_fit(user: Profile, model_size: str, base_data: dict, target_size: str) -> FitResult:
    warnings = []
    details = {}
    score = 100.0

    # 1. Читаем данные модели
    m_chest = base_data.get('chest', 90.0)
    m_waist = base_data.get('waist', 70.0)
    m_hips = base_data.get('hips', 95.0)
    m_height = base_data.get('height', 175.0)

    fit_profile = base_data.get('fit_profile', 'regular').lower()
    cat_type = base_data.get('category_type', 'top').lower()
    elastane = float(base_data.get('elastane_pct', 0.0))
    
    # Фасоны и замеры самой вещи (если есть)
    sleeve_type = base_data.get('sleeve_type', 'long') # long, short, sleeveless
    leg_type = base_data.get('leg_type', 'long')       # long, cropped, shorts
    g_inseam_declared = base_data.get('g_inseam')

    # 2. ИДЕАЛЬНЫЙ ПРИПУСК (Точка Ноль)
    ideal_ease = DESIGN_EASE.get(fit_profile, DESIGN_EASE['regular'])
    base_ease_chest = ideal_ease['top'] if cat_type == 'top' else ideal_ease['bottom']
    base_ease_waist = ideal_ease['bottom']
    base_ease_hips = ideal_ease['bottom']

    # 3. ВИРТУАЛЬНАЯ ВЕЩЬ НА МОДЕЛИ
    g0_chest = m_chest + base_ease_chest
    g0_waist = m_waist + base_ease_waist
    g0_hips = m_hips + base_ease_hips

    # 4. МАСШТАБИРОВАНИЕ НА ЦЕЛЕВОЙ РАЗМЕР (Сетка O'stin)
    gt_chest = grade_girth(g0_chest, model_size, target_size)
    gt_waist = grade_girth(g0_waist, model_size, target_size)
    gt_hips = grade_girth(g0_hips, model_size, target_size)

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
        
        # Штраф на выступающий живот
        if user.waist > user.chest:
            belly_protrusion = (user.waist - user.chest) / math.pi
            base_torso_length = 20.0
            arc_length = math.sqrt(base_torso_length**2 + belly_protrusion**2)
            length_loss = arc_length - base_torso_length
            stretch_factor = max(0.2, 1.0 - (elastane / 10.0))
            eff_loss = length_loss * stretch_factor
            
            if eff_loss > 0.5:
                penalty = eff_loss * 3.0
                score -= penalty
                warnings.append(f"Из-за объема в талии передняя часть изделия может 'подскочить' на ~{eff_loss:.1f}см.")

    else:
        eval_zone('Талия', user.waist, user_ease_waist, base_ease_waist, gt_waist)
        eval_zone('Бедра', user.hips, user_ease_hips, base_ease_hips, gt_hips)

    # 7. ОЦЕНКА РОСТА И ДЛИНЫ
    if cat_type == 'bottom':
        # Пропускаем штрафы за длину для шорт
        if leg_type != 'shorts':
            # Если есть заявленный шаговый шов магазина, берем его. Иначе - формула (45% роста модели).
            m_inseam = g_inseam_declared if g_inseam_declared else (m_height * 0.45)
            gt_inseam = grade_length(m_inseam, model_size, target_size)
            inseam_diff = user.inseam - gt_inseam
            
            if inseam_diff > 2.5:
                details['Длина (Шаг)'] = f"Ваш шаг ({user.inseam:.1f}) > расчетного ({gt_inseam:.1f}). Короче на ~{inseam_diff:.1f}см."
                score -= inseam_diff * 2.0
                if leg_type == 'long': warnings.append(f"Брюки могут быть коротковаты (-{inseam_diff:.1f}см)")
            elif inseam_diff < -2.5:
                details['Длина (Шаг)'] = f"Расчетная длина ({gt_inseam:.1f}) > вашей. Длиннее на ~{abs(inseam_diff):.1f}см."
                score -= abs(inseam_diff) * 1.0
            else:
                details['Длина (Шаг)'] = f"Длина штанин оптимальна -> [green]ИДЕАЛЬНО[/green]"
        else:
            details['Длина'] = "Шорты — ограничений по длине штанин нет."
            
    else:
        # Для верха пропускаем штрафы, если это футболка (short sleeve) или без рукавов
        if sleeve_type == 'long':
            height_diff = user.height - m_height
            if abs(height_diff) > 3.0:
                len_diff = height_diff * 0.35 
                if len_diff > 2.5:
                    details['Длина'] = f"Рост больше эталона. Рукава/изделие будут короче на ~{len_diff:.1f}см."
                    score -= len_diff * 1.5
                elif len_diff < -2.5:
                    details['Длина'] = f"Изделие будет длиннее задуманного на ~{abs(len_diff):.1f}см."
                    score -= abs(len_diff) * 1.0
        else:
            details['Длина'] = "Короткий рукав/Без рукава — ограничений по росту нет."

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