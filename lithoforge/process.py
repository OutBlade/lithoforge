"""
Process parameter calculator for DIY semiconductor photolithography.

Covers: spin coating, exposure, development, wet etching, electroless plating,
thermal oxidation, and resolution limits.

All calculations are based on published models. Results are starting points --
calibrate against your actual results.
"""

from __future__ import annotations
import math
from typing import Optional


# ── Photoresist database ────────────────────────────────────────────────────────

RESISTS: dict[str, dict] = {
    "AZ1512": {
        "type": "positive",
        "wavelength_nm": 405,
        "sensitivity_mJ_cm2": 55,
        "contrast": 2.5,
        "k_spin": 82000,         # T(nm) = k * RPM^-0.5  (Scratchell model)
        "developer": "AZ400K_1_4",
        "prebake_C": 100,
        "prebake_s": 60,
        "postbake_C": 110,
        "postbake_s": 60,
        "notes": "Best for 405 nm MSLA. Used in the 2025 Wiley LCD litho paper.",
    },
    "S1813": {
        "type": "positive",
        "wavelength_nm": 405,
        "sensitivity_mJ_cm2": 150,
        "contrast": 2.8,
        "k_spin": 110000,
        "developer": "MF319",
        "prebake_C": 115,
        "prebake_s": 60,
        "postbake_C": 120,
        "postbake_s": 60,
        "notes": "Very well documented. Slightly less sensitive at 405 nm.",
    },
    "AZ5214E": {
        "type": "image_reversal",
        "wavelength_nm": 405,
        "sensitivity_mJ_cm2": 40,
        "contrast": 3.5,
        "k_spin": 86000,
        "developer": "AZ400K_1_4",
        "prebake_C": 90,
        "prebake_s": 50,
        "reversal_bake_C": 120,
        "reversal_bake_s": 120,
        "flood_dose_mJ_cm2": 200,
        "notes": "Image reversal for lift-off and negative tone. Good undercut profile.",
    },
    "DRY_FILM_PCB": {
        "type": "negative",
        "wavelength_nm": 405,
        "sensitivity_mJ_cm2": 30,
        "contrast": 1.8,
        "k_spin": None,
        "fixed_thickness_nm": 25000,
        "developer": "NA2CO3_1PCT",
        "prebake_C": None,
        "prebake_s": None,
        "notes": "No spin coater needed. Laminate with iron. Resolution ~100 um.",
    },
}

DEVELOPERS: dict[str, dict] = {
    "AZ400K_1_4": {
        "prep": "1 part AZ 400K + 4 parts DI water",
        "temp_C": 21,
        "time_s": (20, 60),
        "notes": "Standard for AZ series. Agitate gently. Check visually.",
    },
    "MF319": {
        "prep": "Use undiluted (TMAH-based, metal-ion-free)",
        "temp_C": 21,
        "time_s": (30, 90),
        "notes": "Use in ventilated area. TMAH is neurotoxic in concentrated form.",
    },
    "NA2CO3_1PCT": {
        "prep": "10 g washing soda per 1 L warm water",
        "temp_C": 30,
        "time_s": (30, 120),
        "notes": "Safe and cheap. Works for most dry-film PCB resists.",
    },
}

ETCHANTS: dict[str, dict] = {
    "BHF_7_1": {
        "target": "SiO2",
        "rate_nm_min": 100,
        "selectivity_over_Si": 80,
        "selectivity_over_SiN": 5,
        "temp_C": 21,
        "hazard": "EXTREME -- HF causes deep tissue burns with delayed symptoms. "
                  "Use full face shield, neoprene gloves, and keep calcium gluconate gel within reach.",
    },
    "KOH_30PCT_80C": {
        "target": "Si (anisotropic)",
        "rate_nm_min": 1000,       # <100> plane
        "rate_110_nm_min": 1400,
        "rate_111_nm_min": 10,     # extremely slow on <111>
        "temp_C": 80,
        "hazard": "Strong base. Gloves and goggles required. Use reflux condenser or cover.",
        "notes": "Creates V-grooves in <100> wafers. Stops on <111> planes.",
    },
    "TMAH_25PCT_80C": {
        "target": "Si (anisotropic, CMOS-compatible)",
        "rate_nm_min": 600,
        "temp_C": 80,
        "hazard": "Toxic -- TMAH is neurotoxic. Use fume hood and full PPE.",
        "notes": "Metal-ion-free alternative to KOH. Preferred for CMOS process.",
    },
    "AL_ETCHANT_A": {
        "target": "Al metal",
        "composition": "H3PO4:HNO3:acetic:H2O  16:1:1:2",
        "rate_nm_min": 30,
        "temp_C": 50,
        "hazard": "Corrosive acid mixture. Gloves and goggles required.",
    },
    "DILUTE_HNO3_10PCT": {
        "target": "Ni (spacer etchback)",
        "rate_nm_min": 50,
        "temp_C": 21,
        "hazard": "Oxidising acid. Gloves required.",
        "notes": "Use for timed Ni etchback in spacer lithography. Rate varies with bath age.",
    },
    "ACETONE": {
        "target": "Photoresist / organic mandrel",
        "rate_nm_min": None,
        "temp_C": 21,
        "hazard": "Highly flammable. No ignition sources.",
        "notes": "Soak 60-120 s with gentle agitation. Follow with IPA rinse.",
    },
}


# ── Spin coating ────────────────────────────────────────────────────────────────

def spin_thickness(resist: str, rpm: int, dilution: float = 1.0) -> dict:
    """
    Estimate photoresist thickness from spin speed using Scratchell model.

    T(nm) = k * dilution^0.33 * RPM^-0.5

    Parameters
    ----------
    resist : key from RESISTS (e.g. 'AZ1512')
    rpm : spin speed in RPM
    dilution : volume fraction of resist (1.0 = undiluted, 0.5 = 1:1 with thinner)
    """
    r = _get_resist(resist)

    if r.get("k_spin") is None:
        nm = r.get("fixed_thickness_nm", 25000) * dilution
    else:
        nm = r["k_spin"] * (dilution ** 0.33) * (rpm ** -0.5)

    return {
        "resist": resist,
        "rpm": rpm,
        "dilution": dilution,
        "thickness_nm": round(nm, 1),
        "thickness_um": round(nm / 1000, 3),
        "prebake": f"{r['prebake_C']} C for {r['prebake_s']} s" if r.get("prebake_C") else "N/A",
        "developer": r["developer"],
        "notes": r["notes"],
    }


def spin_rpm_for_thickness(resist: str, target_nm: float, dilution: float = 1.0) -> int:
    """Return the spin speed needed to achieve a target resist thickness."""
    r = _get_resist(resist)
    if r.get("k_spin") is None:
        raise ValueError(f"{resist} has fixed thickness -- cannot adjust by spin speed.")
    k = r["k_spin"] * (dilution ** 0.33)
    return round((k / target_nm) ** 2)


# ── Exposure ────────────────────────────────────────────────────────────────────

def exposure_time(
    resist: str,
    intensity_mW_cm2: float,
    overdose_factor: float = 1.2,
    lcd_transmission: float = 0.80,
) -> dict:
    """
    Calculate exposure time for a given resist and MSLA light intensity.

    Parameters
    ----------
    intensity_mW_cm2 : UV intensity at the LCD surface (mW/cm2)
    overdose_factor : multiply the minimum clearing dose by this (1.0 -- 1.5 typical)
    lcd_transmission : fraction of light transmitted through the LCD panel (~0.75-0.85)
    """
    r = _get_resist(resist)
    dose = r["sensitivity_mJ_cm2"] * overdose_factor
    eff_intensity = intensity_mW_cm2 * lcd_transmission

    if eff_intensity <= 0:
        raise ValueError("Intensity must be positive.")

    return {
        "resist": resist,
        "required_dose_mJ_cm2": round(dose, 1),
        "intensity_at_lcd_mW_cm2": intensity_mW_cm2,
        "effective_intensity_mW_cm2": round(eff_intensity, 3),
        "exposure_time_s": round(dose / eff_intensity, 1),
        "tip": "Adjust +/-20% and inspect -- your LCD intensity may differ.",
    }


# ── Development ─────────────────────────────────────────────────────────────────

def development_recipe(resist: str) -> dict:
    """Return development parameters for a resist."""
    r = _get_resist(resist)
    dev = DEVELOPERS.get(r["developer"], {})
    return {
        "resist": resist,
        "developer_key": r["developer"],
        "prep": dev.get("prep", "See datasheet"),
        "temp_C": dev.get("temp_C", 21),
        "time_range_s": dev.get("time_range_s", (30, 60)),
        "method": "Immerse with gentle agitation. Inspect every 5 s near the end.",
        "rinse": "DI water 30 s, then N2 blow dry or IPA rinse.",
        "notes": dev.get("notes", ""),
    }


# ── Wet etching ─────────────────────────────────────────────────────────────────

def etch_time(etchant: str, target_nm: float, temp_C: Optional[float] = None) -> dict:
    """
    Calculate wet etch time for target material removal.

    Uses Arrhenius correction (~5 %/K) if a non-default temperature is given.
    """
    e = _get_etchant(etchant)
    rate = e.get("rate_nm_min")

    if rate is None:
        return {"etchant": etchant, "note": "Time-controlled -- see notes.", "hazard": e.get("hazard", "")}

    if temp_C is not None and "temp_C" in e:
        rate = rate * (1.05 ** (temp_C - e["temp_C"]))

    t_min = target_nm / rate

    return {
        "etchant": etchant,
        "target_material": e["target"],
        "target_nm": target_nm,
        "etch_rate_nm_min": round(rate, 1),
        "etch_time_min": round(t_min, 2),
        "etch_time_s": round(t_min * 60),
        "overetch_10pct_min": round(t_min * 1.1, 2),
        "hazard": e.get("hazard", "Unknown"),
    }


# ── Thermal oxidation ───────────────────────────────────────────────────────────

def oxide_thickness(temp_C: float, time_min: float, wet: bool = False) -> dict:
    """
    Estimate SiO2 thickness from Deal-Grove model (simplified linear-parabolic).

    Suitable for garage fab tube furnaces. Wet oxidation (steam) is ~5-10x faster
    than dry but produces lower-quality oxide.

    Parameters
    ----------
    temp_C : furnace temperature (900-1200 C typical)
    time_min : oxidation time in minutes
    wet : True = wet oxidation (steam), False = dry O2
    """
    T_K = temp_C + 273.15
    t_s = time_min * 60

    if wet:
        A = 0.226e-3 * math.exp(-0.78 / (8.617e-5 * T_K))
        B = 0.787 * math.exp(-1.23 / (8.617e-5 * T_K))
    else:
        A = 0.165e-3 * math.exp(-0.78 / (8.617e-5 * T_K))
        B = 0.0117 * math.exp(-1.24 / (8.617e-5 * T_K))

    A_cm = A * 1e-4
    B_cm2_s = B * 1e-8
    t_s_eff = t_s + A_cm ** 2 / (4 * B_cm2_s)

    thickness_cm = (A_cm / 2) * (math.sqrt(1 + 4 * B_cm2_s * t_s_eff / A_cm ** 2) - 1)
    thickness_nm = thickness_cm * 1e7

    return {
        "temp_C": temp_C,
        "time_min": time_min,
        "mode": "wet" if wet else "dry",
        "thickness_nm": round(thickness_nm, 1),
        "thickness_um": round(thickness_nm / 1000, 3),
        "notes": "Deal-Grove model. Calibrate against actual measurements.",
    }


# ── Electroless nickel plating ──────────────────────────────────────────────────

def electroless_ni_thickness(time_min: float, temp_C: float = 25.0) -> float:
    """Estimate electroless Ni-P thickness in nm from plating time."""
    base_rate_nm_min = 15.0
    rate = base_rate_nm_min * (1.035 ** (temp_C - 25.0))
    return round(rate * time_min, 1)


def electroless_ni_time(target_nm: float, temp_C: float = 25.0) -> float:
    """Return plating time in minutes to reach target Ni-P thickness."""
    base_rate_nm_min = 15.0
    rate = base_rate_nm_min * (1.035 ** (temp_C - 25.0))
    return round(target_nm / rate, 1)


# ── Resolution limits ───────────────────────────────────────────────────────────

def resolution_limit(
    pixel_pitch_um: float = 18.0,
    wavelength_nm: float = 405.0,
    na: float = 0.0,
    magnification: float = 1.0,
) -> dict:
    """
    Calculate minimum feature size for a given optical configuration.

    Parameters
    ----------
    magnification : reduction factor of objective lens (1 = contact mode, 20 = 20x obj)
    na : numerical aperture of objective; 0 = contact mode
    """
    eff_pixel_um = pixel_pitch_um / magnification

    if na > 0:
        diff_limit_um = 0.61 * wavelength_nm / 1000.0 / na
    else:
        diff_limit_um = wavelength_nm / 1000.0 * 0.5   # rough contact mode estimate

    actual_um = max(eff_pixel_um, diff_limit_um)

    return {
        "pixel_pitch_um": pixel_pitch_um,
        "magnification": magnification,
        "effective_pixel_um": round(eff_pixel_um, 3),
        "diffraction_limit_um": round(diff_limit_um, 3),
        "resolution_um": round(actual_um, 3),
        "resolution_nm": round(actual_um * 1000, 1),
        "limiting_factor": "pixel" if eff_pixel_um >= diff_limit_um else "diffraction",
    }


# ── Convenience summary ─────────────────────────────────────────────────────────

def full_process_card(resist: str, rpm: int, intensity_mW_cm2: float) -> str:
    """Return a human-readable process card for a given resist and setup."""
    t = spin_thickness(resist, rpm)
    e = exposure_time(resist, intensity_mW_cm2)
    d = development_recipe(resist)

    lines = [
        f"Process Card -- {resist}",
        "=" * 50,
        f"Spin coat:   {rpm} RPM  -->  {t['thickness_nm']:.0f} nm",
        f"Pre-bake:    {t['prebake']}",
        f"Expose:      {e['exposure_time_s']} s  (dose {e['required_dose_mJ_cm2']} mJ/cm2)",
        f"Developer:   {d['prep']}",
        f"Dev time:    {d['time_range_s'][0]}-{d['time_range_s'][1]} s  @ {d['temp_C']} C",
        f"Rinse:       {d['rinse']}",
        "",
        f"Notes: {t['notes']}",
    ]
    return "\n".join(lines)


def list_resists() -> list[str]:
    return list(RESISTS.keys())


def list_etchants() -> list[str]:
    return list(ETCHANTS.keys())


# ── internal helpers ────────────────────────────────────────────────────────────

def _get_resist(name: str) -> dict:
    key = name.upper()
    if key not in RESISTS:
        raise ValueError(f"Unknown resist '{name}'. Available: {list(RESISTS.keys())}")
    return RESISTS[key]


def _get_etchant(name: str) -> dict:
    key = name.upper()
    if key not in ETCHANTS:
        raise ValueError(f"Unknown etchant '{name}'. Available: {list(ETCHANTS.keys())}")
    return ETCHANTS[key]
