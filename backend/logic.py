import math
from dataclasses import dataclass, field
from typing import Dict, List, Any, Tuple

# ==========================================
# 1. КОНВЕНЦИИ И ПЕРЕВОДЫ (flat_half)
# ==========================================
ZONES_RU = {
    'shoulders': 'Плечи',
    'chest': 'Грудь',
    'waist_top': 'Талия (Верх)',
    'waist_bottom': 'Пояс (Низ)',
    'high_hip': 'Живот / Верх бедер',
    'hips': 'Бедра',
    'sleeve': 'Рукав',
    'length_top': 'Длина изделия',
    'inseam': 'Шаговый шов',
    'outseam': 'Внешний шов'
}

MIN_FUNC_ALLOWANCE = {
    'shoulders': 0.5,
    'chest': 2.0,
    'waist_top': 1.0,
    'waist_bottom': 0.5,
    'high_hip': 1.0,
    'hips': 1.0,
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
        return {
            'height': self.height,
            'shoulders': self.shoulders,
            'chest': self.chest / 2.0,
            'waist_top': self.waist / 2.0,
            'waist_bottom': self.waist / 2.0,
            'high_hip': (self.waist + self.hips) / 4.0,
            'hips': self.hips / 2.0,
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
    
    m_chest = theory.get('chest', 90.0) / 2.0
    m_waist = theory.get('waist', 70.0) / 2.0
    m_hips = theory.get('hips', 95.0) / 2.0
    
    ease_map = {'slim': (1.0, 0.5), 'regular': (3.0, 1.5), 'oversize': (7.0, 3.0)}
    base_ease_top, base_ease_bot = ease_map.get(fit_profile, ease_map['regular'])

    g_chest = grade_girth(m_chest + base_ease_top, model_size, target_size) if cat_type == 'top' else 0
    g_waist_top = grade_girth(m_waist + base_ease_bot, model_size, target_size) if cat_type == 'top' else 0
    g_waist_bot = grade_girth(m_waist + base_ease_bot, model_size, target_size) if cat_type == 'bottom' else 0
    g_hips = grade_girth(m_hips + base_ease_bot, model_size, target_size) if cat_type == 'bottom' else 0
    
    g_shoulders = grade_girth(theory.get('shoulders', 42.0), model_size, target_size)
    g_sleeve = grade_length(theory.get('g_sleeve', 64.0), model_size, target_size)
    g_inseam = grade_length(theory.get('g_inseam', 80.0), model_size, target_size)
    g_length_top = grade_length(theory.get('g_length', 70.0), model_size, target_size)

    zones_to_check = {}
    if cat_type == 'top':
        zones_to_check['shoulders'] = {'B': user_flat['shoulders'], 'G': g_shoulders, 'IP0': base_ease_top}
        zones_to_check['chest'] = {'B': user_flat['chest'], 'G': g_chest, 'IP0': base_ease_top}
        zones_to_check['waist_top'] = {'B': user_flat['waist_top'], 'G': g_waist_top, 'IP0': base_ease_top}
        if theory.get('sleeve_type', 'long') == 'long':
            zones_to_check['sleeve'] = {'B': user_flat['sleeve'], 'G': g_sleeve, 'IP0': 0.0}
        zones_to_check['length_top'] = {'B': user_flat['length_top'], 'G': g_length_top, 'IP0': 0.0}
    else:
        zones_to_check['waist_bottom'] = {'B': user_flat['waist_bottom'], 'G': g_waist_bot, 'IP0': base_ease_bot}
        zones_to_check['high_hip'] = {'B': user_flat['high_hip'], 'G': g_hips - 1.0, 'IP0': base_ease_bot}
        zones_to_check['hips'] = {'B': user_flat['hips'], 'G': g_hips, 'IP0': base_ease_bot}
        if theory.get('leg_type', 'long') != 'shorts':
            zones_to_check['inseam'] = {'B': user_flat['inseam'], 'G': g_inseam, 'IP0': 0.0}

    # ==========================================
    # ИНТЕГРАЦИЯ COMFORT_C (Адаптация Цели T)
    # ==========================================
    raw_deltas = {}
    for z, data in zones_to_check.items():
        T_base = data['B'] + data['IP0']
        T_final = T_base
        
        # Если есть сохраненные любимые вещи для этой категории
        if user_profile.comfort_C and cat_type in user_profile.comfort_C:
            cat_comfort = user_profile.comfort_C[cat_type]
            if z in cat_comfort:
                C_z = float(cat_comfort[z])
                delta_comfort = C_z - T_base
                # Лимиты по спецификации IP 2.0: min = -3.0, max = +5.0
                clamped_delta = max(-3.0, min(5.0, delta_comfort))
                T_final = T_base + clamped_delta
                
                if abs(clamped_delta) > 0.1:
                    warnings.append(f"🎯 Зона '{ZONES_RU.get(z, z)}' скорректирована по вашей любимой вещи: цель {T_final:.1f}см (было {T_base:.1f}см).")

        data['T_final'] = T_final
        raw_deltas[z] = data['G'] - T_final

    eff_deltas = raw_deltas.copy()
    
    if 'sleeve' in eff_deltas and 'shoulders' in raw_deltas:
        if raw_deltas['shoulders'] > 0:
            eff_deltas['sleeve'] += raw_deltas['shoulders'] * 0.7
            
    if 'length_top' in eff_deltas and 'waist_top' in raw_deltas:
        if raw_deltas['waist_top'] < 0:
            stretch_loss = abs(raw_deltas['waist_top']) * (0.7 if elastane < 2 else 0.4)
            eff_deltas['length_top'] -= stretch_loss

    for z, data in zones_to_check.items():
        B = data['B']
        G = data['G']
        T = data['T_final']
        delta_eff = eff_deltas[z]
        
        min_allowance = MIN_FUNC_ALLOWANCE.get(z, 0.0)
        if elastane >= 2.0: min_allowance -= 1.0 
        
        if G < (B + min_allowance):
            hard_fit_status = "FAIL"
            warnings.append(f"Критично мало: {ZONES_RU.get(z, z)} (Вещь: {G:.1f}см, Тело: {B:.1f}см)")

        penalty = 0.0
        status_txt = "Идеально"
        
        tol_strict = 1.0
        tol_loose = 2.5 if elastane >= 2 else 1.5

        if abs(delta_eff) <= tol_strict:
            status_txt = "Оптимально"
        elif delta_eff < -tol_strict: 
            penalty = abs(delta_eff) * 5.0
            status_txt = "Тесно / Жмет"
        elif delta_eff > tol_strict: 
            penalty = abs(delta_eff) * 2.0
            status_txt = "Свободно"
            
        if penalty > 0: score -= penalty

        xray.append(XRayZone(
            zone_name=ZONES_RU.get(z, z),
            body_val=B,
            target_val=T,
            garment_val=G,
            delta_eff=delta_eff,
            status=status_txt,
            penalty=penalty,
            message=f"Дельта: {delta_eff:+.1f}см"
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