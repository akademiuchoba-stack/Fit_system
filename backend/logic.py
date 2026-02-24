import math
from dataclasses import dataclass, field
from typing import Dict, List, Any, Tuple

ZONES_RU = {
    'shoulders': 'Плечи',
    'back_width': 'Спина',
    'chest': 'Грудь',
    'underbust': 'Под грудью',
    'waist_top': 'Талия (естественная)',
    'belly': 'Живот (выступающий)',
    'hem_top': 'Низ изделия',
    'waist_bottom': 'Пояс (линия ремня)',
    'high_hip': 'Верх бедер (косточки)',
    'hips': 'Бедра',
    'front_rise': 'Посадка спереди',
    'back_rise': 'Посадка сзади',
    'thigh': 'Бедро (Ляжка)',
    'knee': 'Колено',
    'leg_opening': 'Ширина штанины',
    'bicep': 'Бицепс',
    'collar': 'Воротник',
    'sleeve': 'Рукав',
    'length_top': 'Длина (Торс)',
    'length_dress': 'Длина (Платье)',
    'inseam': 'Шаговый шов',
    'outseam': 'Внешний шов'
}

MIN_FUNC_ALLOWANCE = {
    'shoulders': 0.5, 'back_width': 0.5, 'chest': 2.0, 'underbust': 1.0,
    'waist_top': 1.0, 'belly': 1.5, 'hem_top': 1.0, 'waist_bottom': 0.5,
    'high_hip': 1.0, 'hips': 1.0, 'thigh': 0.5, 'bicep': 0.5,
    'sleeve': 0.0, 'length_top': 0.0, 'inseam': -2.0 
}

SIZES_ORDER = ['XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL']

@dataclass
class Profile:
    height: float
    shoulders: float; back_width: float; chest: float; underbust: float
    waist_top: float; belly: float; waist_bottom: float; high_hip: float; hips: float
    thigh: float; knee: float; calf: float; bicep: float; neck: float
    arm_length: float; outseam: float; inseam: float; length_dress: float
    problem_zones: List[str] = field(default_factory=list)
    comfort_C: Dict[str, dict] = field(default_factory=dict)

    def to_flat_half(self) -> dict:
        flat = {'height': self.height, 'sleeve': self.arm_length, 'outseam': self.outseam, 'inseam': self.inseam, 'length_dress': self.length_dress}
        
        flat['shoulders'] = self.shoulders if self.shoulders else 42.0
        flat['back_width'] = self.back_width if self.back_width else (flat['shoulders'] - 2.0)
        flat['chest'] = (self.chest / 2.0) if self.chest else 45.0
        flat['underbust'] = (self.underbust / 2.0) if self.underbust else (flat['chest'] - 4.0)
        
        flat['waist_top'] = (self.waist_top / 2.0) if self.waist_top else (flat['chest'] - 2.0)
        flat['belly'] = (self.belly / 2.0) if self.belly else flat['waist_top']
        flat['waist_bottom'] = (self.waist_bottom / 2.0) if self.waist_bottom else 42.0
        flat['high_hip'] = (self.high_hip / 2.0) if self.high_hip else ((flat['waist_bottom'] + (self.hips/2.0 if self.hips else 48.0)) / 2.0)
        flat['hips'] = (self.hips / 2.0) if self.hips else 48.0
        
        flat['thigh'] = (self.thigh / 2.0) if self.thigh else (flat['hips'] * 0.58)
        flat['knee'] = (self.knee / 2.0) if self.knee else (flat['thigh'] * 0.7)
        flat['leg_opening'] = (self.calf / 2.0) if self.calf else 18.0
        flat['bicep'] = (self.bicep / 2.0) if self.bicep else (flat['chest'] * 0.35)
        flat['collar'] = self.neck if self.neck else 40.0
        flat['length_top'] = self.height * 0.35
        
        return flat

@dataclass
class XRayZone:
    zone_name: str; body_val: float; target_val: float; garment_val: float
    delta_eff: float; status: str; penalty: float; message: str; inferred: bool 

@dataclass
class SizeResult:
    size_label: str; is_available: bool; score: float; hard_fit: str
    global_status: str; xray_zones: List[XRayZone]; warnings: List[str]

def grade_girth(base_val: float, model_size: str, target_size: str) -> float:
    mapping = {'XS': -4.0, 'S': -2.0, 'M': 0.0, 'L': 2.0, 'XL': 6.0, 'XXL': 10.0, '3XL': 14.0}
    return base_val + (mapping.get(target_size.upper(), 0.0) - mapping.get(model_size.upper(), 0.0))

def grade_length(base_val: float, model_size: str, target_size: str) -> float:
    try: steps = SIZES_ORDER.index(target_size.upper()) - SIZES_ORDER.index(model_size.upper())
    except ValueError: steps = 0
    return base_val + (steps * 1.0)

def calculate_single_size(user_flat: dict, user_profile: Profile, model_size: str, theory: dict, target_size: str, is_available: bool) -> SizeResult:
    warnings = []; xray = []; score = 100.0; hard_fit_status = "PASS"
    cat_type = theory.get('category_type', 'top').lower()
    fit_profile = theory.get('fit_profile', 'regular').lower()
    elastane = float(theory.get('elastane_pct', 0.0))
    stiffness = theory.get('stiffness_class', 'medium').lower()
    
    m_chest = theory.get('chest', 90.0) / 2.0
    m_waist = theory.get('waist', 70.0) / 2.0
    m_hips = theory.get('hips', 95.0) / 2.0
    
    ease_map = {'slim': (1.0, 0.5), 'regular': (3.0, 1.5), 'oversize': (7.0, 3.0)}
    base_ease_top, base_ease_bot = ease_map.get(fit_profile, ease_map['regular'])

    base_g = {}; inferred_zones = set()

    if cat_type == 'top':
        base_g['shoulders'] = theory.get('shoulders', 42.0)
        base_g['chest'] = m_chest + base_ease_top
        
        base_g['waist_top'] = float(theory['g_waist_top']) if theory.get('g_waist_top') else (base_g['chest'] - (1.0 if fit_profile == 'slim' else 0.0))
        if not theory.get('g_waist_top'): inferred_zones.add('waist_top')

        # Интеграция Живота (belly) для верха
        base_g['belly'] = float(theory['g_belly']) if theory.get('g_belly') else base_g['waist_top']
        if not theory.get('g_belly'): inferred_zones.add('belly')

        base_g['back_width'] = float(theory['g_back_width']) if theory.get('g_back_width') else (base_g['chest'] - 4.0)
        if not theory.get('g_back_width'): inferred_zones.add('back_width')
            
        base_g['bicep'] = float(theory['g_bicep']) if theory.get('g_bicep') else (base_g['chest'] * 0.35)
        if not theory.get('g_bicep'): inferred_zones.add('bicep')

        base_g['sleeve'] = theory.get('g_sleeve', 64.0)
        base_g['length_top'] = theory.get('g_length', 70.0)

    else:
        base_g['waist_bottom'] = m_waist + base_ease_bot
        base_g['hips'] = m_hips + base_ease_bot
        
        base_g['high_hip'] = float(theory['g_high_hip']) if theory.get('g_high_hip') else max(base_g['waist_bottom'], base_g['hips'] - (2.0 if fit_profile == 'slim' else 1.0))
        if not theory.get('g_high_hip'): inferred_zones.add('high_hip')

        # Интеграция Живота (belly) для низа (высокая посадка)
        base_g['belly'] = float(theory['g_belly']) if theory.get('g_belly') else base_g['waist_bottom']
        if not theory.get('g_belly'): inferred_zones.add('belly')

        base_g['thigh'] = float(theory['g_thigh']) if theory.get('g_thigh') else (base_g['hips'] * 0.60)
        if not theory.get('g_thigh'): inferred_zones.add('thigh')

        base_g['leg_opening'] = float(theory['g_leg_opening']) if theory.get('g_leg_opening') else 18.0
        if not theory.get('g_leg_opening'): inferred_zones.add('leg_opening')

        base_g['inseam'] = theory.get('g_inseam', 80.0)
        if theory.get('g_front_rise'): base_g['front_rise'] = float(theory['g_front_rise'])
        if theory.get('g_back_rise'): base_g['back_rise'] = float(theory['g_back_rise'])

    g_graded = {}
    for z, val in base_g.items():
        if z in ['sleeve', 'length_top', 'inseam', 'outseam', 'front_rise', 'back_rise']:
            g_graded[z] = grade_length(val, model_size, target_size)
        else:
            g_graded[z] = grade_girth(val, model_size, target_size)

    zones_to_check = {}
    for z in base_g.keys():
        if z in ['front_rise', 'back_rise']: continue
        ip0 = base_ease_top if cat_type == 'top' and z not in ['sleeve', 'length_top'] else \
             (base_ease_bot if cat_type == 'bottom' and z not in ['inseam'] else 0.0)
        zones_to_check[z] = {'B': user_flat[z], 'G': g_graded[z], 'IP0': ip0}

    raw_deltas = {}
    for z, data in zones_to_check.items():
        T_base = data['B'] + data['IP0']
        T_final = T_base
        
        if user_profile.comfort_C and cat_type in user_profile.comfort_C:
            cat_comfort = user_profile.comfort_C[cat_type]
            if z in cat_comfort:
                delta_comfort = float(cat_comfort[z]) - T_base
                clamped_delta = max(-3.0, min(5.0, delta_comfort))
                T_final = T_base + clamped_delta
                if abs(clamped_delta) > 0.1: warnings.append(f"🎯 Зона '{ZONES_RU.get(z, z)}' скорректирована по эталону.")

        data['T_final'] = T_final
        raw_deltas[z] = data['G'] - T_final

    eff_deltas = raw_deltas.copy()
    if 'sleeve' in eff_deltas and 'shoulders' in raw_deltas:
        if raw_deltas['shoulders'] > 0: eff_deltas['sleeve'] += raw_deltas['shoulders'] * 0.7
            
    if 'length_top' in eff_deltas and 'belly' in raw_deltas:
        if raw_deltas['belly'] < 0:
            stretch_loss = abs(raw_deltas['belly']) * (0.7 if elastane < 2 else 0.4)
            eff_deltas['length_top'] -= stretch_loss

    for z, data in zones_to_check.items():
        B, G, T = data['B'], data['G'], data['T_final']
        delta_eff = eff_deltas[z]
        is_inferred = z in inferred_zones
        
        min_allowance = MIN_FUNC_ALLOWANCE.get(z, 0.0)
        if elastane >= 2.0: min_allowance -= 1.0 
        
        if G < (B + min_allowance):
            hard_fit_status = "FAIL"
            warnings.append(f"Критично мало: {ZONES_RU.get(z, z)} (Вещь: {G:.1f}см, Тело: {B:.1f}см)")

        penalty = 0.0; status_txt = "Идеально"
        tol_strict = 1.0; tol_loose = 2.5 if elastane >= 2 else 1.5
        
        neg_penalty_mult = 5.0
        if stiffness == 'stiff': neg_penalty_mult = 6.5
        elif stiffness == 'soft': neg_penalty_mult = 4.0
        
        if z in user_profile.problem_zones: neg_penalty_mult *= 1.3 

        if abs(delta_eff) <= tol_strict: status_txt = "Оптимально"
        elif delta_eff < -tol_strict: 
            penalty = abs(delta_eff) * neg_penalty_mult
            status_txt = "Тесно / Жмет"
        elif delta_eff > tol_strict: 
            penalty = abs(delta_eff) * 2.0
            status_txt = "Свободно"
            
        if penalty > 0: score -= penalty
        
        xray.append(XRayZone(
            zone_name=ZONES_RU.get(z, z), body_val=B, target_val=T, garment_val=G,
            delta_eff=delta_eff, status=status_txt, penalty=penalty, message=f"Дельта: {delta_eff:+.1f}см",
            inferred=is_inferred
        ))

    score = max(0.0, min(100.0, score))
    if hard_fit_status == "FAIL": g_status = "МАЛО"
    elif score >= 80: g_status = "ИДЕАЛЬНО"
    elif score >= 60: g_status = "ХОРОШО"
    else: g_status = "ПЛОХО"

    return SizeResult(size_label=target_size, is_available=is_available, score=score, hard_fit=hard_fit_status, global_status=g_status, xray_zones=xray, warnings=warnings)

def evaluate_all_sizes(user: Profile, theory: dict, available_sizes: List[str]) -> Dict[str, Any]:
    user_flat = user.to_flat_half()
    model_size = theory.get('model_size', 'M')
    results = []; best_score = -1.0; best_size = None
    
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