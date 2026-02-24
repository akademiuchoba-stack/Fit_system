import math
from dataclasses import dataclass, field
from typing import Dict, List, Any, Tuple

# ==========================================
# 1. КОНВЕНЦИИ И ПЕРЕВОДЫ (flat_half)
# ==========================================
ZONES_RU = {
    'shoulders': 'Плечи',
    'back_width': 'Спина',
    'chest': 'Грудь',
    'waist_top': 'Талия (Верх)',
    'waist_bottom': 'Пояс (Низ)',
    'high_hip': 'Живот / Верх бедер',
    'hips': 'Бедра',
    'thigh': 'Бедро (Нога)',
    'sleeve': 'Рукав',
    'length_top': 'Длина изделия',
    'inseam': 'Шаговый шов',
    'outseam': 'Внешний шов'
}

# Расширенные функциональные допуски (Hard Gate)
MIN_FUNC_ALLOWANCE = {
    'shoulders': 0.5,
    'back_width': 0.5,
    'chest': 2.0,
    'waist_top': 1.0,
    'waist_bottom': 0.5,
    'high_hip': 1.0,
    'hips': 1.0,
    'thigh': 0.5,
    'sleeve': 0.0,
    'length_top': 0.0,
    'inseam': -2.0 
}

SIZES_ORDER = ['XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL']

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
    problem_zones: List[str] = field(default_factory=list)
    comfort_C: Dict[str, dict] = field(default_factory=dict)

    def to_flat_half(self) -> dict:
        """Перевод тела в полуобхваты + математическая аппроксимация недостающих зон"""
        return {
            'height': self.height,
            'shoulders': self.shoulders,
            'back_width': self.shoulders - 2.0, # Аппроксимация ширины спины
            'chest': self.chest / 2.0,
            'waist_top': self.waist / 2.0,
            'waist_bottom': self.waist / 2.0,
            'high_hip': (self.waist + self.hips) / 4.0,
            'hips': self.hips / 2.0,
            'thigh': (self.hips / 2.0) * 0.58, # Аппроксимация ляжки (58% от полуобхвата бедер)
            'sleeve': self.arm_length,
            'length_top': self.height * 0.35,
            'inseam': self.inseam,
            'outseam': self.outseam
        }

@dataclass
class XRayZone:
    zone_name: str
    body_val: float
    target_val: float
    garment_val: float
    delta_eff: float
    status: str
    penalty: float
    message: str
    inferred: bool # Флаг: вычислено ли математически (Estimate Mode)

@dataclass
class SizeResult:
    size_label: str
    is_available: bool
    score: float
    hard_fit: str
    global_status: str
    xray_zones: List[XRayZone]
    warnings: List[str]

def grade_girth(base_val: float, model_size: str, target_size: str) -> float:
    mapping = {'XS': -4.0, 'S': -2.0, 'M': 0.0, 'L': 2.0, 'XL': 6.0, 'XXL': 10.0, '3XL': 14.0}
    offset_model = mapping.get(model_size.upper(), 0.0)
    offset_target = mapping.get(target_size.upper(), 0.0)
    return base_val + (offset_target - offset_model)

def grade_length(base_val: float, model_size: str, target_size: str) -> float:
    try: steps = SIZES_ORDER.index(target_size.upper()) - SIZES_ORDER.index(model_size.upper())
    except ValueError: steps = 0
    return base_val + (steps * 1.0)

def calculate_single_size(user_flat: dict, user_profile: Profile, model_size: str, theory: dict, target_size: str, is_available: bool) -> SizeResult:
    warnings = []
    xray = []
    score = 100.0
    hard_fit_status = "PASS"

    cat_type = theory.get('category_type', 'top').lower()
    fit_profile = theory.get('fit_profile', 'regular').lower()
    elastane = float(theory.get('elastane_pct', 0.0))
    stiffness = theory.get('stiffness_class', 'medium').lower()
    
    m_chest = theory.get('chest', 90.0) / 2.0
    m_waist = theory.get('waist', 70.0) / 2.0
    m_hips = theory.get('hips', 95.0) / 2.0
    
    ease_map = {'slim': (1.0, 0.5), 'regular': (3.0, 1.5), 'oversize': (7.0, 3.0)}
    base_ease_top, base_ease_bot = ease_map.get(fit_profile, ease_map['regular'])

    # ==========================================
    # 2. INFERENCE ENGINE (ESTIMATE MODE)
    # ==========================================
    base_g = {}
    inferred_zones = set()

    # --- ВЕРХ ---
    if cat_type == 'top':
        base_g['shoulders'] = theory.get('shoulders', 42.0)
        base_g['chest'] = m_chest + base_ease_top
        
        # Inference: shirt_waist_from_chest
        drop = 1.0 if fit_profile == 'slim' else (0.0 if fit_profile == 'oversize' else 0.5)
        base_g['waist_top'] = base_g['chest'] - drop
        inferred_zones.add('waist_top')

        # Inference: blazer_back_width_from_chest
        if theory.get('g_back_width'):
            base_g['back_width'] = float(theory['g_back_width'])
        else:
            base_g['back_width'] = base_g['chest'] - 4.0
            inferred_zones.add('back_width')
            
        base_g['sleeve'] = theory.get('g_sleeve', 64.0)
        base_g['length_top'] = theory.get('g_length', 70.0)

    # --- НИЗ ---
    else:
        base_g['waist_bottom'] = m_waist + base_ease_bot
        base_g['hips'] = m_hips + base_ease_bot
        
        # Inference: bottom_high_hip_from_waist_hip (max(waist, hip - s))
        s_drop = 2.0 if fit_profile == 'slim' else 1.0
        base_g['high_hip'] = max(base_g['waist_bottom'], base_g['hips'] - s_drop)
        inferred_zones.add('high_hip')

        # Inference: bottom_thigh_from_hip
        if theory.get('g_thigh'):
            base_g['thigh'] = float(theory['g_thigh'])
        else:
            k_thigh = 0.55 if fit_profile == 'slim' else (0.65 if fit_profile == 'oversize' else 0.60)
            base_g['thigh'] = base_g['hips'] * k_thigh
            inferred_zones.add('thigh')

        base_g['inseam'] = theory.get('g_inseam', 80.0)

    # ==========================================
    # 3. ГРЕЙДИРОВАНИЕ НА ЦЕЛЕВОЙ РАЗМЕР
    # ==========================================
    g_graded = {}
    for z, val in base_g.items():
        if z in ['sleeve', 'length_top', 'inseam', 'outseam']:
            g_graded[z] = grade_length(val, model_size, target_size)
        else:
            g_graded[z] = grade_girth(val, model_size, target_size)

    # ==========================================
    # 4. ФОРМИРОВАНИЕ ЗОН И ИНТЕГРАЦИЯ COMFORT_C
    # ==========================================
    zones_to_check = {}
    for z in base_g.keys():
        ip0 = base_ease_top if cat_type == 'top' and z not in ['sleeve', 'length_top'] else \
             (base_ease_bot if cat_type == 'bottom' and z not in ['inseam'] else 0.0)
        zones_to_check[z] = {'B': user_flat[z], 'G': g_graded[z], 'IP0': ip0}

    raw_deltas = {}
    for z, data in zones_to_check.items():
        T_base = data['B'] + data['IP0']
        T_final = T_base
        
        # Сдвиг цели по любимым вещам
        if user_profile.comfort_C and cat_type in user_profile.comfort_C:
            cat_comfort = user_profile.comfort_C[cat_type]
            if z in cat_comfort:
                C_z = float(cat_comfort[z])
                delta_comfort = C_z - T_base
                clamped_delta = max(-3.0, min(5.0, delta_comfort))
                T_final = T_base + clamped_delta
                
                if abs(clamped_delta) > 0.1:
                    warnings.append(f"🎯 Зона '{ZONES_RU.get(z, z)}' скорректирована: цель {T_final:.1f}см.")

        data['T_final'] = T_final
        raw_deltas[z] = data['G'] - T_final

    # ==========================================
    # 5. КОМПЕНСАЦИИ
    # ==========================================
    eff_deltas = raw_deltas.copy()
    
    if 'sleeve' in eff_deltas and 'shoulders' in raw_deltas:
        if raw_deltas['shoulders'] > 0:
            eff_deltas['sleeve'] += raw_deltas['shoulders'] * 0.7
            
    if 'length_top' in eff_deltas and 'waist_top' in raw_deltas:
        if raw_deltas['waist_top'] < 0:
            stretch_loss = abs(raw_deltas['waist_top']) * (0.7 if elastane < 2 else 0.4)
            eff_deltas['length_top'] -= stretch_loss

    # ==========================================
    # 6. HARD GATE И АСИММЕТРИЧНЫЙ СКОРИНГ
    # ==========================================
    for z, data in zones_to_check.items():
        B = data['B']
        G = data['G']
        T = data['T_final']
        delta_eff = eff_deltas[z]
        is_inferred = z in inferred_zones
        
        # Hard Gate
        min_allowance = MIN_FUNC_ALLOWANCE.get(z, 0.0)
        if elastane >= 2.0: min_allowance -= 1.0 
        
        if G < (B + min_allowance):
            hard_fit_status = "FAIL"
            warnings.append(f"Критично мало: {ZONES_RU.get(z, z)} (Вещь: {G:.1f}см, Тело: {B:.1f}см)")

        # Настройка штрафов (учитываем жесткость ткани и проблемные зоны)
        penalty = 0.0
        status_txt = "Идеально"
        
        tol_strict = 1.0
        tol_loose = 2.5 if elastane >= 2 else 1.5
        
        neg_penalty_mult = 5.0
        if stiffness == 'stiff': neg_penalty_mult = 6.5
        elif stiffness == 'soft': neg_penalty_mult = 4.0
        
        if z in user_profile.problem_zones:
            neg_penalty_mult *= 1.3 # Увеличиваем штраф для проблемных зон

        if abs(delta_eff) <= tol_strict:
            status_txt = "Оптимально"
        elif delta_eff < -tol_strict: 
            penalty = abs(delta_eff) * neg_penalty_mult
            status_txt = "Тесно / Жмет"
        elif delta_eff > tol_strict: 
            penalty = abs(delta_eff) * 2.0
            status_txt = "Свободно"
            
        if penalty > 0: score -= penalty
        
        # Формируем сообщение для рентгена
        msg = f"Дельта: {delta_eff:+.1f}см"
        if is_inferred: msg += " [INFERRED]"

        xray.append(XRayZone(
            zone_name=ZONES_RU.get(z, z), body_val=B, target_val=T, garment_val=G,
            delta_eff=delta_eff, status=status_txt, penalty=penalty, message=msg,
            inferred=is_inferred
        ))

    score = max(0.0, min(100.0, score))
    
    if hard_fit_status == "FAIL": g_status = "МАЛО (Не влезет)"
    elif score >= 80: g_status = "ИДЕАЛЬНО"
    elif score >= 60: g_status = "ХОРОШО"
    elif score >= 40: g_status = "ПРИЕМЛЕМО"
    else: g_status = "ПЛОХО СИДИТ"

    return SizeResult(
        size_label=target_size, is_available=is_available, score=score,
        hard_fit=hard_fit_status, global_status=g_status, xray_zones=xray, warnings=warnings
    )

def evaluate_all_sizes(user: Profile, theory: dict, available_sizes: List[str]) -> Dict[str, Any]:
    user_flat = user.to_flat_half()
    model_size = theory.get('model_size', 'M')
    
    results = []
    best_score = -1.0
    best_size = None
    
    for size in SIZES_ORDER:
        is_avail = size.upper() in [s.upper() for s in available_sizes]
        res = calculate_single_size(user_flat, user, model_size, theory, size, is_avail)
        results.append(res)
        
        if is_avail and res.hard_fit != "FAIL" and res.score > best_score:
            best_score = res.score
            best_size = size
            
    if not best_size:
        for res in results:
            if res.hard_fit != "FAIL" and res.score > best_score:
                best_score = res.score
                best_size = res.size_label

    return {"best_size": best_size, "available_sizes": available_sizes, "all_results": results}