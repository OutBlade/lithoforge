"""
Spacer lithography calculator for sub-lithographic feature generation.

Implements Self-Aligned Double Patterning (SADP) process calculations,
electroless plating time estimates, and multi-patterning analysis.

Spacer lithography flow:
    1. Pattern mandrel via lithography
    2. Deposit conformal thin film (thickness T = final feature width)
    3. Anisotropic etchback -- removes film from flat surfaces, keeps sidewalls
    4. Remove mandrel selectively
    Result: two spacer lines per mandrel, each T nm wide
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from .process import electroless_ni_time, electroless_ni_thickness


@dataclass
class SpacerResult:
    mandrel_width_nm: float
    mandrel_pitch_nm: float
    film_thickness_nm: float
    spacer_width_nm: float
    output_pitch_nm: float
    pitch_halved: bool
    process_steps: list[str]
    warnings: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        lines = [
            "Spacer Lithography Result",
            "=" * 45,
            f"Mandrel:       {self.mandrel_width_nm:.0f} nm wide  /  {self.mandrel_pitch_nm:.0f} nm pitch",
            f"Film:          {self.film_thickness_nm:.0f} nm",
            f"Spacer width:  {self.spacer_width_nm:.0f} nm",
            f"Output pitch:  {self.output_pitch_nm:.0f} nm",
            "",
            "Process steps:",
        ]
        for step in self.process_steps:
            lines.append(f"  {step}")
        if self.warnings:
            lines.append("")
            lines.append("Warnings:")
            for w in self.warnings:
                lines.append(f"  ! {w}")
        return "\n".join(lines)


def calculate_spacer(
    mandrel_width_nm: float,
    mandrel_pitch_nm: float,
    film_thickness_nm: float,
    lateral_etch_loss_nm: float = 5.0,
    mandrel_material: str = "resist",
) -> SpacerResult:
    """
    Calculate SADP spacer lithography dimensions.

    After etchback and mandrel removal each original mandrel line yields two
    spacer lines. The output half-pitch equals (original pitch / 2).

    Parameters
    ----------
    mandrel_width_nm : mandrel line width in nm
    mandrel_pitch_nm : mandrel center-to-center pitch in nm
    film_thickness_nm : deposited conformal film thickness in nm
                        This is the target spacer width.
    lateral_etch_loss_nm : spacer width reduction from lateral etching during etchback
    mandrel_material : 'resist', 'oxide', or 'nitride' -- determines removal chemistry
    """
    space_nm = mandrel_pitch_nm - mandrel_width_nm
    spacer_width = max(0.0, film_thickness_nm - lateral_etch_loss_nm)
    output_pitch = mandrel_pitch_nm / 2.0

    removal = {
        "resist": "Acetone / NMP soak 60-120 s, then IPA rinse",
        "oxide": "BHF (1:10) -- CAUTION: HF hazard",
        "nitride": "Hot H3PO4 at 150 C -- CAUTION: concentrated acid",
    }.get(mandrel_material, "See datasheet for mandrel material")

    plating_time = electroless_ni_time(film_thickness_nm)

    steps = [
        f"Pattern mandrel:    {mandrel_width_nm:.0f} nm wide, {mandrel_pitch_nm:.0f} nm pitch ({mandrel_material})",
        f"Deposit spacer film: {film_thickness_nm:.0f} nm conformal film",
        f"   Electroless Ni:   ~{plating_time:.0f} min at 25 C  (verify with SEM/profilometer)",
        f"Anisotropic etchback: remove {film_thickness_nm:.0f} nm from flat surfaces",
        f"   Use oxygen plasma cleaner (best) or timed wet etch in dilute HNO3",
        f"Remove mandrel:      {removal}",
        f"Result:              {spacer_width:.0f} nm spacers at {output_pitch:.0f} nm pitch",
    ]

    warns = []
    if spacer_width < 20:
        warns.append(f"Very thin spacers ({spacer_width:.0f} nm) -- process control is critical.")
    if space_nm < film_thickness_nm * 2:
        warns.append(
            f"Spacer gap ({space_nm:.0f} nm) < 2x film ({film_thickness_nm*2:.0f} nm) -- "
            "spacers from adjacent mandrels may merge. Increase mandrel pitch."
        )
    if lateral_etch_loss_nm / film_thickness_nm > 0.25:
        warns.append("High lateral etch loss (>25 %). Improve etch anisotropy or use thicker film.")

    return SpacerResult(
        mandrel_width_nm=mandrel_width_nm,
        mandrel_pitch_nm=mandrel_pitch_nm,
        film_thickness_nm=film_thickness_nm,
        spacer_width_nm=round(spacer_width, 1),
        output_pitch_nm=round(output_pitch, 1),
        pitch_halved=True,
        process_steps=steps,
        warnings=warns,
    )


def spacer_for_target(
    target_nm: float,
    mandrel_pitch_nm: float,
    lateral_etch_loss_nm: float = 5.0,
) -> float:
    """
    Return the film thickness needed to achieve a target spacer width.
    """
    return target_nm + lateral_etch_loss_nm


def multi_patterning(
    target_half_pitch_nm: float,
    litho_resolution_nm: float,
    spacer_film_nm: Optional[float] = None,
) -> dict:
    """
    How many patterning passes are needed to reach a target half-pitch?

    Each SADP pass halves the pitch (or limits to spacer film thickness if given).
    """
    if litho_resolution_nm <= target_half_pitch_nm:
        return {
            "approach": "Single patterning",
            "passes": 1,
            "achievable_nm": litho_resolution_nm,
            "note": "Direct lithography sufficient.",
        }

    current = litho_resolution_nm
    passes = 0
    while current > target_half_pitch_nm and passes < 6:
        current = current / 2.0
        if spacer_film_nm is not None:
            current = min(current, spacer_film_nm)
        passes += 1

    names = {1: "SADP", 2: "SAQP", 3: "SAOP"}
    approach = names.get(passes, f"{passes}-pass multi-patterning")

    return {
        "approach": approach,
        "passes": passes,
        "achievable_nm": round(current, 1),
        "note": f"Each pass requires a full deposit-etch-strip cycle.",
    }


def spacer_process_summary(
    mandrel_width_nm: float,
    mandrel_pitch_nm: float,
    film_thickness_nm: float,
) -> str:
    """Return a one-page printable process summary."""
    result = calculate_spacer(mandrel_width_nm, mandrel_pitch_nm, film_thickness_nm)
    plating_time = electroless_ni_time(film_thickness_nm)
    achieved_nm = result.spacer_width_nm

    lines = [
        "=" * 55,
        "  SPACER LITHOGRAPHY PROCESS CARD",
        "=" * 55,
        "",
        f"  Target feature:    {achieved_nm:.0f} nm",
        f"  Mandrel:           {mandrel_width_nm:.0f} nm / {mandrel_pitch_nm:.0f} nm pitch",
        f"  Film:              {film_thickness_nm:.0f} nm electroless Ni-P",
        "",
        "  STEP 1 -- Mandrel lithography",
        f"    Expose mandrel pattern at {mandrel_width_nm:.0f} nm feature size.",
        f"    With Mars 5 Ultra (18 um pixel) use 20x objective -> ~0.9 um features",
        f"    or spacer lithography from a coarser mandrel.",
        "",
        "  STEP 2 -- Electroless Ni-P deposition",
        f"    Dip in electroless Ni solution for ~{plating_time:.0f} min at 25 C.",
        f"    Verify thickness with profilometer or SEM cross-section.",
        "",
        "  STEP 3 -- Anisotropic etchback",
        f"    Remove {film_thickness_nm:.0f} nm Ni from horizontal surfaces.",
        "    Use: O2 plasma cleaner (preferred) or timed 10% HNO3.",
        "    Stop when flat surfaces are clear but sidewalls remain.",
        "",
        "  STEP 4 -- Mandrel removal",
        "    Strip resist mandrel: acetone 120 s + IPA rinse + N2 dry.",
        "",
        f"  RESULT: {achieved_nm:.0f} nm Ni spacer lines at {result.output_pitch_nm:.0f} nm pitch",
        "",
    ]
    if result.warnings:
        lines.append("  WARNINGS:")
        for w in result.warnings:
            lines.append(f"    ! {w}")
    lines.append("=" * 55)
    return "\n".join(lines)
