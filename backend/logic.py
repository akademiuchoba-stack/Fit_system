import math
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Tuple

# -----------------------------------------
# Fit Engine v4.2 (Full Architectural)
# - IdealEase + mode detector + scaling
# - hard gate
# - compensation + reverse deformation
# - problem zones as critical zones
# - comfort_C (personal ease offsets)
# - Exact / Partial / Estimate via inferred
# -----------------------------------------

ZONES_RU = {
    # top
    "chest": "Грудь",
    "waist_top": "Талия (естественная)",
    "hem_top": "Низ изделия",
    "belly": "Живот (выступающий)",
    "bicep": "Бицепс",
    "shoulders": "Плечи",
    "sleeve": "Рукав",
    "length_top": "Длина (Торс)",
    # bottom
    "waist_bottom": "Пояс",
    "high_hip": "Верх бедер",
    "hips": "Бедра",
    "thigh": "Бедро",
    "knee": "Колено",
    "calf": "Икра",
    "inseam": "Шаговый шов",
    "outseam": "Внешняя длина",
    "front_rise": "Посадка спереди",
    "back_rise": "Посадка сзади",
    "leg_opening": "Низ штанины",
}

# Zones grouped
TOP_HALF_ZONES = ["chest", "waist_top", "hem_top", "bicep"]
TOP_LEN_ZONES = ["shoulders", "sleeve", "length_top"]

BOTTOM_HALF_ZONES = ["waist_bottom", "high_hip", "hips", "thigh", "knee", "calf", "leg_opening"]
BOTTOM_LEN_ZONES = ["inseam", "outseam", "front_rise", "back_rise"]

# -----------------------------
# Baseline ranges (half, cm)
# -----------------------------
BASELINE = {
    ("tshirt", "male"): {
        "chest": (3.0, 6.0),
        "waist_top": (3.0, 7.0),
        "hem_top": (3.0, 8.0),
        "shoulders": (0.0, 2.0),
        "bicep": (1.0, 3.0),
    },
    ("tshirt", "female"): {
        "chest": (2.0, 5.0),
        "waist_top": (2.0, 6.0),
        "hem_top": (3.0, 8.0),
        "shoulders": (0.0, 2.0),
        "bicep": (1.0, 3.0),
    },
    ("trousers", "male"): {
        "waist_bottom": (1.0, 3.0),
        "hips": (2.0, 5.0),
        "thigh": (1.0, 4.0),
    },
    ("trousers", "female"): {
        "waist_bottom": (1.0, 3.0),
        "high_hip": (2.0, 5.0),
        "hips": (2.0, 6.0),
        "thigh": (1.0, 4.0),
    },
}

# -----------------------------
# Weights (MVP+)
# -----------------------------
WEIGHTS = {
    ("tshirt", "male"): {
        "chest": 1.2,
        "waist_top": 0.7,
        "hem_top": 0.5,
"bicep": 0.6,
        "shoulders": 1.0,
        "sleeve": 0.4,
        "length_top": 0.4,
    },
    ("tshirt", "female"): {
        "chest": 1.1,
        "waist_top": 1.0,
        "hem_top": 0.8,
"bicep": 0.5,
        "shoulders": 0.6,
        "sleeve": 0.4,
        "length_top": 0.4,
    },
    ("trousers", "male"): {
        "waist_bottom": 1.2,
        "high_hip": 0.6,
        "hips": 1.0,
        "thigh": 0.9,
        "belly": 0.9,
        "inseam": 0.6,
        "outseam": 0.4,
        "front_rise": 0.6,
        "back_rise": 0.6,
        "leg_opening": 0.4,
    },
    ("trousers", "female"): {
        "waist_bottom": 1.1,
        "high_hip": 1.0,
        "hips": 1.2,
        "thigh": 0.9,
        "belly": 0.7,
        "inseam": 0.6,
        "outseam": 0.4,
        "front_rise": 0.6,
        "back_rise": 0.6,
        "leg_opening": 0.5,
    },
}

# Standard tolerances (within this band, penalty=0)
STD_TOL = {
    # top
    "chest": (0.5, 2.0),
    "waist_top": (0.5, 2.0),
    "hem_top": (0.5, 2.0),
    "belly": (0.5, 2.0),
    "bicep": (0.3, 1.5),
    "shoulders": (0.3, 1.5),
    "sleeve": (0.5, 1.5),
    "length_top": (0.5, 2.0),
    # bottom
    "waist_bottom": (0.3, 1.5),
    "high_hip": (0.5, 2.0),
    "hips": (0.5, 2.0),
    "thigh": (0.5, 2.0),
    "leg_opening": (0.5, 1.5),
    "inseam": (1.0, 2.0),
    "outseam": (1.0, 2.0),
    "front_rise": (0.5, 1.5),
    "back_rise": (0.5, 1.5),
}

# Designer tolerances (wider band, for design zones)
DES_TOL = {
    # top
    "chest": (1.0, 2.5),
    "waist_top": (1.0, 3.0),
    "hem_top": (1.0, 3.5),
    "belly": (1.0, 3.0),
    "bicep": (0.5, 1.5),
    "shoulders": (0.5, 1.5),
    "sleeve": (1.0, 2.0),
    "length_top": (1.0, 3.0),
    # bottom
    "waist_bottom": (0.8, 2.0),
    "high_hip": (1.0, 2.5),
    "hips": (1.0, 2.5),
    "thigh": (0.8, 2.0),
    "leg_opening": (0.5, 1.5),
    "inseam": (1.5, 2.5),
    "outseam": (1.5, 2.5),
    "front_rise": (0.8, 2.0),
    "back_rise": (0.8, 2.0),
}

# Hard gate minimal allowance (cm half/len)
GATE_MIN = {
    # top
    "chest": 1.0,
    "waist_top": 0.5,
    "hem_top": 0.5,
    "belly": 1.0,
    "bicep": 0.5,
    "shoulders": 0.3,
    # bottom
    "waist_bottom": 0.5,
    "high_hip": 0.5,
    "hips": 1.0,
    "thigh": 0.5,
    "leg_opening": 0.2,
}

# -----------------------------
# v4.1 additions
# -----------------------------

# Nonlinear scaling
ALPHA_TOP = 0.6
ALPHA_BOTTOM = 0.7

# Zone-specific scaling impact for IdealEase transfer
ZONE_SCALE = {
    # half zones
    "chest": 1.0,
    "waist_top": 1.0,
    "hem_top": 1.0,
    "belly": 1.0,
    "bicep": 0.6,
    "waist_bottom": 1.0,
    "high_hip": 1.0,
    "hips": 1.0,
    "thigh": 1.0,
    "leg_opening": 0.6,
    # length zones
    "shoulders": 0.5,
    "sleeve": 0.3,
    "length_top": 0.0,
    "inseam": 0.0,
    "outseam": 0.0,
    "front_rise": 0.2,
    "back_rise": 0.2,
}

# Direct compensation: if one zone has extra, it can "help" another
# affected += k * max(0, source_delta)
COMP_MATRIX = {
    "sleeve": ("shoulders", 0.7),
    "bicep": ("chest", 0.5),
    "thigh": ("hips", 0.4),
}

# Reverse deformation: tight belly consumes length / rise
FABRIC_BETA = {
    "knit": 0.4,
    "woven": 0.6,
    "denim": 0.8,
}

# Problem zones effect (critical comfort zones)
PROBLEM_WEIGHT_MULT = 1.3
PROBLEM_TOL_SHRINK = 0.8  # tolerance * 0.8 => stricter

# Penalty multipliers (tight more expensive)
TIGHT_MULT = 8.0
LOOSE_MULT = 3.0

# -----------------------------
# Data structs
# -----------------------------
@dataclass
class ZoneDetail:
    zone: str
    label: str
    body: Optional[float]
    garment: Optional[float]
    target: Optional[float]
    delta: Optional[float]               # effective delta (after compensation)
    raw_delta: Optional[float]           # raw delta (before compensation)
    status: str
    penalty: float
    inferred: bool
    weight: Optional[float] = None
    used: Optional[str] = None
    notes: Optional[str] = None

@dataclass
class SizeResult:
    size_label: str
    score: float
    confidence: float
    mode: str
    hard_fail: bool
    global_status: str
    warnings: List[str]
    details: List[ZoneDetail]

    size_label: str
    score: float
    confidence: float
    mode: str
    hard_fail: bool
    global_status: str
    warnings: List[str]
    details: List[ZoneDetail]


# -----------------------------
# Helpers
# -----------------------------
def _center(r: Tuple[float, float]) -> float:
    return (r[0] + r[1]) / 2.0

def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def _to_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, bool):
            return None
        s = str(x).strip().replace(",", ".")
        if s == "":
            return None
        return float(s)
    except Exception:
        return None

def _half_from_circ(x: Optional[float]) -> Optional[float]:
    if x is None:
        return None
    return x / 2.0

def _norm_fabric_type(fabric: Dict[str, Any]) -> str:
    ft = (fabric.get("fabric_type") or "").lower().strip()
    # user might have unknown strings; normalize by substring
    if "denim" in ft or "jean" in ft:
        return "denim"
    if "knit" in ft or "jersey" in ft or "rib" in ft:
        return "knit"
    if "woven" in ft or "cotton" in ft or "linen" in ft:
        return "woven"
    # default safe
    return ft or "woven"

def _fabric_gate_multiplier(fabric: Dict[str, Any]) -> float:
    fabric_type = _norm_fabric_type(fabric)
    elast = _to_float(fabric.get("elastane_pct")) or 0.0
    stiff = (fabric.get("stiffness") or "medium").lower().strip()

    # stretch knit with elastane => easier to wear
    if fabric_type == "knit" and elast >= 3.0:
        return 0.7
    # denim / stiff => harder to wear
    if fabric_type == "denim" or stiff == "stiff":
        return 1.2
    # woven with low elastane => slightly harder
    if fabric_type == "woven" and elast <= 1.0:
        return 1.1
    return 1.0

def _fabric_penalty_multipliers(fabric: Dict[str, Any]) -> Tuple[float, float]:
    fabric_type = _norm_fabric_type(fabric)
    elast = _to_float(fabric.get("elastane_pct")) or 0.0
    stiff = (fabric.get("stiffness") or "medium").lower().strip()

    # base
    neg = 1.0
    pos = 1.0

    # stiff => tight penalties worse
    if fabric_type == "denim" or stiff == "stiff":
        neg *= 1.25
        pos *= 1.05

    # high stretch => tight penalties softer
    if fabric_type == "knit" and elast >= 3.0:
        neg *= 0.85
        pos *= 1.0

    return (neg, pos)

def _fabric_beta(fabric: Dict[str, Any]) -> float:
    fabric_type = _norm_fabric_type(fabric)
    stiff = (fabric.get("stiffness") or "medium").lower().strip()
    elast = _to_float(fabric.get("elastane_pct")) or 0.0

    beta = FABRIC_BETA.get(fabric_type, 0.6)
    # stiff increases deformation effect
    if stiff == "stiff":
        beta = max(beta, 0.7)
    # high elastane reduces
    if elast >= 4.0:
        beta *= 0.85
    return _clamp(beta, 0.25, 0.95)

def _status_from_delta(delta: float, tol_neg: float, tol_pos: float) -> str:
    if delta < -tol_neg:
        return "TIGHT"
    if delta > tol_pos:
        return "LOOSE"
    return "OK"

def _critical_zones(garment_type: str) -> Tuple[List[str], List[str]]:
    """
    Returns (must, recommended) zones for confidence calculation.
    If zone missing/inferred => confidence drops.
    """
    if garment_type == "tshirt":
        must = ["chest"]
        rec = ["waist_top", "hem_top", "sleeve", "length_top"]
        return must, rec
    # trousers
    must = ["waist_bottom", "hips", "inseam"]
    rec = ["high_hip", "thigh", "leg_opening", "front_rise", "back_rise", "outseam"]
    return must, rec

def _hard_gate_zones(garment_type: str, mapped_problem: List[str]) -> List[str]:
    # v4.2: hard gate uses measurement-zones (mapped_problem), not raw human zones.
    mp = set(mapped_problem or [])
    if garment_type == "tshirt":
        zones = ["chest", "bicep"]
        if any(z in mp for z in ("waist_top", "hem_top", "chest")):
            zones += ["waist_top", "hem_top"]
        return sorted(set(zones))
    if garment_type in ("trousers", "jeans"):
        zones = ["waist_bottom", "high_hip", "hips", "thigh", "front_rise"]
        # if belly is a problem, high_hip/front_rise already cover it; keep them in gate
        return sorted(set(zones))
    if garment_type in ("shirt", "blazer", "coat"):
        zones = ["shoulders", "chest"]
        if garment_type in ("blazer", "coat"):
            zones += ["back_width", "bicep"]
        if "waist_top" in mp:
            zones += ["waist_top"]
        return sorted(set(zones))
    if garment_type == "sneakers":
        zones = ["insole_length", "insole_width_forefoot"]
        if "instep_height" in mp:
            zones += ["instep_height"]
        return sorted(set(zones))
    return []


def _map_problem_zones(garment_type: str, problem_zones: List[str]) -> List[str]:
    """Map human 'problem_zones' (belly/arms/etc.) to measurement zones used by the engine.

    v4.2: 'belly' is NOT a garment measurement zone. For bottoms we map it to high_hip/front_rise/waist_bottom,
    for tops we map it to waist_top/hem_top/chest (and sometimes length).
    """
    p = set(problem_zones or [])
    mapped: List[str] = []

    # direct zones (if user explicitly uses engine zones)
    for z in p:
        if z in ZONES_RU:
            mapped.append(z)

    # semantic mappings
    if "belly" in p:
        if garment_type in ("trousers", "jeans"):
            mapped += ["high_hip", "front_rise", "waist_bottom"]
        else:
            mapped += ["waist_top", "hem_top", "chest", "length_top"]

    if "arms" in p:
        mapped += ["sleeve", "bicep"]
    if "shoulders" in p:
        mapped += ["shoulders", "back_width"]
    if "legs" in p:
        mapped += ["inseam", "outseam"]
    if "calves" in p:
        mapped += ["knee", "leg_opening"]
    if "foot_width" in p:
        mapped += ["insole_width_forefoot"]
    if "high_instep" in p:
        mapped += ["instep_height"]

    # dedupe while preserving order
    out: List[str] = []
    for z in mapped:
        if z not in out:
            out.append(z)
    # v4.2: normalize weights for comparable scoring across garment types
    w_sum = sum((v.get("weight") or 0.0) for v in out.values())
    if w_sum > 0:
        for z in out:
            out[z]["weight"] = float(out[z]["weight"]) / w_sum

    return out

def _get_comfort_offset(
    comfort_C: Dict[str, Any],
    garment_type: str,
    zone: str,
    is_half_zone: bool
) -> float:
    """
    comfort_C can be:
      - { "tshirt": { "chest": 1.0, ... }, "trousers": {...} }
      - or { "chest": 1.0, "hips": 0.5 }
    Value is interpreted in cm (engine units):
      - half zones: cm-half
      - length zones: cm
    Heuristic: if half-zone offset is unusually large, treat as circumference and /2.
    """
    if not isinstance(comfort_C, dict):
        return 0.0

    v = None
    gt = comfort_C.get(garment_type)
    if isinstance(gt, dict) and zone in gt:
        v = _to_float(gt.get(zone))
    if v is None and zone in comfort_C:
        v = _to_float(comfort_C.get(zone))

    if v is None:
        return 0.0

    if is_half_zone:
        # heuristic: if user stored circumference offset
        if abs(v) > 15.0:
            v = v / 2.0
    return float(v)

def _ease_transfer_scale(garment_type: str, buyer_half: Dict[str, float], model_half: Dict[str, float]) -> float:
    """
    Nonlinear scaling factor Ks = S^alpha.
    S computed using a stable reference zone:
      - tshirt: chest
      - trousers: hips or waist_bottom
    If ratio near 1 => Ks=1 to avoid noise.
    """
    if garment_type == "trousers":
        b = buyer_half.get("hips") or buyer_half.get("waist_bottom")
        m = model_half.get("hips") or model_half.get("waist_bottom")
        alpha = ALPHA_BOTTOM
    else:
        b = buyer_half.get("chest")
        m = model_half.get("chest")
        alpha = ALPHA_TOP

    if not b or not m or m <= 0:
        return 1.0

    S = b / m
    if 0.85 <= S <= 1.15:
        return 1.0

    Ks = math.pow(S, alpha)
    # clamp to keep sane
    return _clamp(Ks, 0.75, 1.35)

def _apply_compensations(
    deltas: Dict[str, float],
    garment_type: str,
    fabric: Dict[str, Any]
) -> Dict[str, float]:
    """
    Returns effective deltas (delta_eff) after:
      - direct compensation
      - reverse deformation
    """
    delta_eff = dict(deltas)

    # direct compensation: only from positive (extra) to help deficits
    for affected, (source, k) in COMP_MATRIX.items():
        if affected in delta_eff and source in delta_eff:
            if delta_eff[source] > 0:
                delta_eff[affected] = delta_eff[affected] + k * delta_eff[source]

    # reverse deformation (tight torso/upper hip consumes length / rise)
    beta = _fabric_beta(fabric)

    # v4.2: 'belly' is not a garment zone; infer tightness from measured zones.
    tight_source = None
    if garment_type == "tshirt":
        # choose the most negative of available torso zones
        candidates = [delta_eff.get("waist_top"), delta_eff.get("hem_top"), delta_eff.get("chest")]
        candidates = [c for c in candidates if c is not None]
        tight_source = min(candidates) if candidates else None
    elif garment_type == "trousers":
        tight_source = delta_eff.get("high_hip")
        if tight_source is None:
            tight_source = delta_eff.get("waist_bottom")

    if tight_source is not None and tight_source < 0:
        loss = abs(tight_source) * beta

        # tshirt: length_top gets worse
        if garment_type == "tshirt":
            if "length_top" in delta_eff:
                delta_eff["length_top"] = delta_eff["length_top"] - loss

        # trousers: rise gets worse primarily; outseam slightly
        if garment_type == "trousers":
            if "front_rise" in delta_eff:
                delta_eff["front_rise"] = delta_eff["front_rise"] - (0.6 * loss)
            if "back_rise" in delta_eff:
                delta_eff["back_rise"] = delta_eff["back_rise"] - (0.6 * loss)
            if "outseam" in delta_eff:
                delta_eff["outseam"] = delta_eff["outseam"] - (0.2 * loss)

    return delta_eff

# -----------------------------
# MODE DETECTOR (STANDARD/DESIGN/UNCERTAIN)
# -----------------------------
def detect_mode_v31(
    garment_type: str,
    gender: str,
    fabric: Dict[str, Any],
    model_half: Dict[str, float],
    garment_on_model: Dict[str, float]
) -> Dict[str, Any]:
    """
    Determine if this item is STANDARD or DESIGN based on ease-on-model vs baseline range.
    Also flags UNCERTAIN if there is suspicious ease pattern.
    """
    base = BASELINE.get((garment_type, gender), {})
    design_zones: List[str] = []
    flags: List[str] = []
    suspect: List[str] = []
    ease_model: Dict[str, float] = {}

    # compute ease on model where possible
    zones = list(base.keys())
    for z in zones:
        gm = garment_on_model.get(z)
        m = model_half.get(z)
        if gm is None or m is None:
            continue
        ease = gm - m
        ease_model[z] = ease
        lo, hi = base[z]
        # major if outside baseline range by >1 cm
        if ease < (lo - 1.0) or ease > (hi + 1.0):
            design_zones.append(z)
        # suspect if in a strange direction for this garment_type
        if garment_type == "tshirt" and z in ("shoulders", "bicep") and ease > (hi + 2.0):
            suspect.append(z)
        if garment_type == "trousers" and z in ("thigh",) and ease > (hi + 2.0):
            suspect.append(z)

    # silhouette flags (light rule set)
    if garment_type == "tshirt":
        if "chest" in ease_model and ease_model["chest"] >= 7.5:
            flags.append("oversized_chest")
        if "hem_top" in ease_model and ease_model["hem_top"] >= 9.0:
            flags.append("wide_hem")
    if garment_type == "trousers":
        if "thigh" in ease_model and ease_model["thigh"] >= 5.0:
            flags.append("wide_thigh")

    mode = "STANDARD"
    # v4.2: suspect overrides DESIGN (uncertain means "design-like but unreliable")
    if len(suspect) >= 1:
        mode = "UNCERTAIN"
    elif len(design_zones) >= 1 or len(flags) >= 1:
        mode = "DESIGN"

    return {
        "mode": mode,
        "design_zones": sorted(set(design_zones)),
        "silhouette_flags": sorted(set(flags)),
        "suspect_zones": sorted(set(suspect)),
        "ease_model": ease_model,
    }

# -----------------------------
# TARGETS LAYER (baseline / design / comfort)
# -----------------------------
def _targets_for_zone(
    garment_type: str,
    gender: str,
    mode_info: Dict[str, Any],
    buyer_half: Dict[str, float],
    model_half: Dict[str, float],
    fabric: Dict[str, Any],
    mapped_problem: List[str],
    comfort_C: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    Outputs per-zone target + tolerance + weight.
    - STANDARD: uses baseline center (body + center(baseline))
    - DESIGN: uses model ease (IE0) transferred with scaling
    - Adds comfort_C offsets to target
    - Applies problem zone stricter tolerance + higher weights
    """
    base = BASELINE.get((garment_type, gender), {})
    wmap = WEIGHTS.get((garment_type, gender), {})

    design_zones = set(mode_info.get("design_zones") or [])
    mode = mode_info.get("mode") or "STANDARD"
    ease_model = mode_info.get("ease_model") or {}

    Ks = _ease_transfer_scale(garment_type, buyer_half, model_half)

    # v4.2: mapped problem zones are measurement zones, not raw human labels
    mapped_problem_set = set(mapped_problem or [])

    out: Dict[str, Dict[str, Any]] = {}
    zones = set(list(wmap.keys()) + list(base.keys()) + list(buyer_half.keys()))
    zones = [z for z in zones if z in wmap]

    for z in zones:
        target = None
        tol = STD_TOL.get(z, (0.5, 2.0))
        used = "standard"

        # is this a half (circ) zone for comfort conversion?
        is_half_zone = (z in TOP_HALF_ZONES) or (z in BOTTOM_HALF_ZONES)

        if mode == "DESIGN" and z in design_zones and z in ease_model and buyer_half.get(z) is not None:
            # v4.1: zonal scaling of IdealEase transfer
            zone_scale = ZONE_SCALE.get(z, 1.0)
            ease_scaled = ease_model[z] * (1.0 + zone_scale * (Ks - 1.0))
            target = buyer_half[z] + ease_scaled
            tol = DES_TOL.get(z, tol)
            used = "design"
        else:
            if buyer_half.get(z) is not None and z in base:
                target = buyer_half[z] + _center(base[z])
            elif buyer_half.get(z) is not None and z not in base:
                target = buyer_half[z]
            else:
                target = None

        # v4.1: comfort_C shifts target
        if target is not None:
            c_off = _get_comfort_offset(comfort_C, garment_type, z, is_half_zone=is_half_zone)
            target = target + c_off
            if abs(c_off) > 0.0001:
                used = used + "+comfort"

        # v4.1: problem zones tighten tolerance + increase weight (critical comfort zones)
        weight = float(wmap.get(z, 0.0))
        tol_neg, tol_pos = float(tol[0]), float(tol[1])
        if z in mapped_problem_set:
            weight *= PROBLEM_WEIGHT_MULT
            tol_neg *= PROBLEM_TOL_SHRINK
            tol_pos *= PROBLEM_TOL_SHRINK

        out[z] = {
            "target": target,
            "tol_neg": tol_neg,
            "tol_pos": tol_pos,
            "used": used,
            "weight": weight,
        }

    return out

# -----------------------------
# MAIN ENGINE
# -----------------------------
def calculate_fit_v31(buyer: Dict[str, Any], v31: Dict[str, Any]) -> Dict[str, Any]:
    product = v31.get("product") or {}
    fabric = v31.get("fabric") or {}
    garment_type = (product.get("garment_type") or "").strip().lower()
    if garment_type not in ("tshirt", "trousers"):
        raise ValueError("Unsupported garment_type in v31 (only tshirt/trousers)")

    gender = (buyer.get("gender") or "male").strip().lower()
    if gender not in ("male", "female"):
        gender = "male"

    bm = buyer.get("measurements") or {}

    # v4.2: legacy aliases (do not break old profiles)
    if isinstance(bm, dict):
        if "hip_circ" in bm and "hips_circ" not in bm:
            bm["hips_circ"] = bm.get("hip_circ")
        if "hip" in bm and "hips" not in bm:
            bm["hips"] = bm.get("hip")
    buyer_half: Dict[str, float] = {}
    # half zones: accept either z_circ or z (circumference)
    for z in TOP_HALF_ZONES + BOTTOM_HALF_ZONES:
        key = f"{z}_circ"
        if key in bm:
            v = _to_float(bm.get(key))
            buyer_half[z] = _half_from_circ(v) if v is not None else None
        else:
            v = _to_float(bm.get(z))
            buyer_half[z] = _half_from_circ(v) if v is not None else None

    # length zones: accept either z_len or z (length)
    for z in TOP_LEN_ZONES + BOTTOM_LEN_ZONES:
        key = f"{z}_len"
        v = _to_float(bm.get(key))
        if v is None:
            v = _to_float(bm.get(z))
        if v is not None:
            buyer_half[z] = v

    # critical layers
    problem_zones = buyer.get("problem_zones") or []
    if not isinstance(problem_zones, list):
        problem_zones = []
    problem_zones = [str(x).strip().lower() for x in problem_zones if str(x).strip() != ""]

    # v4.2: map human problem zones into measurement zones
    mapped_problem = _map_problem_zones(garment_type=garment_type, problem_zones=problem_zones)

    comfort_C = buyer.get("comfort_C") or {}
    if not isinstance(comfort_C, dict):
        comfort_C = {}

    model = v31.get("model") or {}
    model_body = (model.get("body") or {})
    model_half: Dict[str, float] = {}

    for z in TOP_HALF_ZONES + BOTTOM_HALF_ZONES:
        key = f"{z}_circ"
        v = _to_float(model_body.get(key))
        if v is None:
            v = _to_float(model_body.get(z))
        model_half[z] = _half_from_circ(v) if v is not None else None

    for z in TOP_LEN_ZONES + BOTTOM_LEN_ZONES:
        key = f"{z}_len"
        v = _to_float(model_body.get(key))
        if v is None:
            v = _to_float(model_body.get(z))
        if v is not None:
            model_half[z] = v

    gom = v31.get("garment_on_model") or {}
    gom_m = (gom.get("measurements") or {})
    garment_on_model: Dict[str, float] = {}
    for z in TOP_HALF_ZONES + BOTTOM_HALF_ZONES + TOP_LEN_ZONES + BOTTOM_LEN_ZONES:
        v = _to_float(gom_m.get(z))
        if v is not None:
            garment_on_model[z] = v

    mode_info = detect_mode_v31(garment_type, gender, fabric, model_half, garment_on_model)

    # targets layer (baseline/design/comfort/problem)
    targets = _targets_for_zone(
        garment_type=garment_type,
        gender=gender,
        mode_info=mode_info,
        buyer_half=buyer_half,
        model_half=model_half,
        fabric=fabric,
        mapped_problem=mapped_problem,
        comfort_C=comfort_C,
    )

    sizes = product.get("available_sizes") or []
    if not isinstance(sizes, list):
        sizes = []
    size_matrix = v31.get("size_matrix") or {}
    if not isinstance(size_matrix, dict):
        size_matrix = {}

    gate_mul = _fabric_gate_multiplier(fabric)
    pen_mul_neg, pen_mul_pos = _fabric_penalty_multipliers(fabric)

    # v4.2: normalize fabric meta once (used in score + confidence)
    stiff = (fabric.get("stiffness") or "medium").lower().strip()
    fabric_type = _norm_fabric_type(fabric)
    elast = _to_float(fabric.get("elastane_pct")) or 0.0

    all_results: List[SizeResult] = []

    # confidence config
    must_zones, rec_zones = _critical_zones(garment_type)

    for size in sizes:
        size = str(size)
        node = size_matrix.get(size) or {}
        m = (node.get("measurements") or {}) if isinstance(node, dict) else {}

        g_meas: Dict[str, Optional[float]] = {}
        inferred: Dict[str, bool] = {}

        for z in targets.keys():
            v = _to_float(m.get(z))
            if v is None:
                g_meas[z] = None
                inferred[z] = True
            else:
                g_meas[z] = v
                inferred[z] = False

        warnings: List[str] = []
        details: List[ZoneDetail] = []
        hard_fail = False

        # v4.2: precompute mapped problem set (measurement zones) and hard-gate zones
        mapped_problem_set = set(mapped_problem or [])
        hard_gate_zones = set(_hard_gate_zones(garment_type, mapped_problem))


        # -------------------------
        # HARD GATE LAYER (v4.1)
        # -------------------------
        for z in hard_gate_zones:
            if z not in targets:
                continue
            if inferred.get(z, True):
                # missing measurement => cannot gate, but confidence should drop later
                continue

            body = buyer_half.get(z)
            gar = g_meas.get(z)
            if body is None or gar is None:
                continue

            min_allow = GATE_MIN.get(z, 0.5)
            # problem zones stricter gate
            if z in mapped_problem_set:
                min_allow += 0.5

            min_allow_eff = min_allow * gate_mul
            if gar < (body + min_allow_eff):
                hard_fail = True
                warnings.append(
                    f"Критично мало: {ZONES_RU.get(z, z)} (Вещь: {gar:.1f}см, Тело: {body:.1f}см)"
                )

        # if hard fail => record and continue
        if hard_fail:
            all_results.append(
                SizeResult(
                    size_label=size,
                    score=0.0,
                    confidence=0.0,
                    mode=mode_info.get("mode", "STANDARD"),
                    hard_fail=True,
                    global_status="0% - МАЛО",
                    warnings=warnings,
                    details=[],
                )
            )
            continue

        # -------------------------
        # DELTA LAYER + COMPENSATION
        # -------------------------
        raw_deltas: Dict[str, float] = {}
        for z, tinfo in targets.items():
            body = buyer_half.get(z)
            gar = g_meas.get(z)
            if body is None or gar is None:
                continue
            target = tinfo.get("target")
            if target is None:
                continue
            raw_deltas[z] = gar - float(target)

        # v4.1 compensation + reverse deformation
        eff_deltas = _apply_compensations(raw_deltas, garment_type=garment_type, fabric=fabric)

        # -------------------------
        # PENALTY / SCORE LAYER
        # -------------------------
        total_loss = 0.0

        for z, tinfo in targets.items():
            body = buyer_half.get(z)
            gar = g_meas.get(z)

            if body is None or gar is None:
                # v4.2: missing zones must reduce SCORE (not only confidence)
                weight = float(tinfo.get("weight") or 0.0)

                # add warning for key zones
                if gar is None and z in ("chest", "waist_bottom", "high_hip", "hips", "thigh", "front_rise", "inseam"):
                    warnings.append(f"Нет замера вещи: {ZONES_RU.get(z, z)}")

                miss_mult = 1.0
                if z in must_zones:
                    miss_mult = 2.2
                elif z in rec_zones:
                    miss_mult = 1.2
                if z in hard_gate_zones:
                    miss_mult = max(miss_mult, 2.2)
                if z in mapped_problem_set:
                    miss_mult *= 1.3

                # fabric gates: stiff/denim punishes missing more
                if fabric_type == "denim" or stiff == "stiff":
                    miss_mult *= 1.15

                missing_zone_loss = 2.5 * miss_mult
                total_loss += weight * missing_zone_loss

                details.append(
                    ZoneDetail(
                        zone=z,
                        label=ZONES_RU.get(z, z),
                        body=float(body) if body is not None else None,
                        garment=float(gar) if gar is not None else None,
                        target=None,
                        delta=None,
                        raw_delta=None,
                        status="missing",
                        penalty=float(missing_zone_loss),
                        inferred=True,
                        weight=float(weight),
                        used=tinfo.get("used") or "unknown",
                        notes="missing_measurement",
                    )
                )
                continue

            target = tinfo.get("target")
            if target is None:
                # missing target also reduces score mildly
                weight = float(tinfo.get("weight") or 0.0)
                total_loss += weight * 1.0
                continue

            # effective delta
            raw_delta = raw_deltas.get(z)
            delta = eff_deltas.get(z)
            if delta is None:
                continue

            tol_neg = float(tinfo.get("tol_neg") or 0.5)
            tol_pos = float(tinfo.get("tol_pos") or 2.0)

            penalty = 0.0
            if delta < -tol_neg:
                penalty = TIGHT_MULT * (abs(delta) - tol_neg) * pen_mul_neg
            elif delta > tol_pos:
                penalty = LOOSE_MULT * (delta - tol_pos) * pen_mul_pos

            weight = float(tinfo.get("weight") or 0.0)

            # inferred zones reduce impact (Estimate / Partial)
            if inferred.get(z, False):
                weight *= 0.5

            total_loss += (weight * penalty)

            status = _status_from_delta(delta, tol_neg, tol_pos)
            details.append(
                ZoneDetail(
                    zone=z,
                    label=ZONES_RU.get(z, z),
                    body=float(body),
                    garment=float(gar),
                    target=float(target),
                    delta=float(delta),
                    raw_delta=float(raw_delta) if raw_delta is not None else None,
                    status=status,
                    penalty=float(weight * penalty),
                    inferred=bool(inferred.get(z, False)),
                )
            )

        score = 100.0 - total_loss
        score = _clamp(score, 0.0, 100.0)

        if score >= 80:
            global_status = f"{score:.0f}% - ОТЛИЧНО"
        elif score >= 60:
            global_status = f"{score:.0f}% - НОРМА"
        elif score >= 40:
            global_status = f"{score:.0f}% - РИСК"
        else:
            global_status = f"{score:.0f}% - ПЛОХО"

        # -------------------------
        # CONFIDENCE LAYER (v4.1)
        # -------------------------
        confidence = 100.0

        # missing must/recommended zones drop confidence (Exact/Partial/Estimate)
        missing_must = [z for z in must_zones if inferred.get(z, True)]
        missing_rec = [z for z in rec_zones if inferred.get(z, True)]

        # v4.2: confidence depends on zone weights + criticality (not flat counts)

        for z in missing_must:
            w = float(targets.get(z, {}).get("weight") or 0.0)
            # must zones are high-impact; add small constant to avoid w=0 edge
            confidence -= 60.0 * (w + 0.04)

        for z in missing_rec:
            w = float(targets.get(z, {}).get("weight") or 0.0)
            confidence -= 25.0 * (w + 0.02)

        # mapped problem zones missing => bigger confidence drop (critical comfort zones)
        for z in mapped_problem:
            if inferred.get(z, True):
                w = float(targets.get(z, {}).get("weight") or 0.0)
                confidence -= 20.0 * (w + 0.03)

        # stiff fabric + many missing rec zones => confidence lower
        if (fabric_type == "denim" or stiff == "stiff") and len(missing_rec) >= 3:
            confidence -= 10.0
        if fabric_type == "denim" and elast < 1.0 and len(missing_must) >= 1:
            confidence -= 5.0

        # uncertain mode => lower confidence
        if mode_info.get("mode") == "UNCERTAIN":
            confidence -= 15.0

        # clamp
        confidence = _clamp(confidence, 0.0, 100.0)

        # sort details by weight (most important top)
        details.sort(
            key=lambda d: WEIGHTS.get((garment_type, gender), {}).get(d.zone, 0.0),
            reverse=True
        )

        all_results.append(
            SizeResult(
                size_label=size,
                score=float(score),
                confidence=float(confidence),
                mode=mode_info.get("mode", "STANDARD"),
                hard_fail=False,
                global_status=global_status,
                warnings=warnings,
                details=details,
            )
        )

    best = None
    non_fail = [r for r in all_results if not r.hard_fail]
    if non_fail:
        best = sorted(non_fail, key=lambda r: (r.score, r.confidence), reverse=True)[0]
    elif all_results:
        best = sorted(all_results, key=lambda r: (r.score, r.confidence), reverse=True)[0]

    return {
        "engine_version": "fit_v4.1_full",
        "mode": mode_info.get("mode", "STANDARD"),
        "design_zones": mode_info.get("design_zones", []),
        "silhouette_flags": mode_info.get("silhouette_flags", []),
        "suspect_zones": mode_info.get("suspect_zones", []),
        "best_size": best.size_label if best else None,
        "score": float(best.score) if best else 0.0,
        "confidence": float(best.confidence) if best else 0.0,
        "all_results": [asdict(r) for r in all_results],
    }