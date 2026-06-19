"""
LithoForge command-line interface.

Usage:
    lithoforge thickness AZ1512 4000
    lithoforge expose AZ1512 3.0
    lithoforge etch BHF_7_1 100
    lithoforge develop AZ1512
    lithoforge resolution --magnification 20
    lithoforge spacer 2000 4000 200
    lithoforge oxide 1100 60 --wet
    lithoforge resists
    lithoforge etchants
"""

import click
from .process import (
    spin_thickness, spin_rpm_for_thickness, exposure_time, development_recipe,
    etch_time, oxide_thickness, resolution_limit, full_process_card,
    list_resists, list_etchants, RESISTS, ETCHANTS,
)
from .spacer import calculate_spacer, spacer_process_summary, multi_patterning


@click.group()
@click.version_option("1.0.0")
def cli():
    """LithoForge -- DIY Semiconductor Lithography Toolkit\n
    Process calculators and mask tools for MSLA-based home chip fabrication.
    """


# ── process calculators ───────────────────────────────────────────────────────

@cli.command()
@click.argument("resist")
@click.argument("rpm", type=int)
@click.option("--dilution", default=1.0, show_default=True, help="Resist dilution (1.0 = undiluted)")
def thickness(resist, rpm, dilution):
    """Calculate photoresist thickness from spin speed.

    \b
    Examples:
      lithoforge thickness AZ1512 4000
      lithoforge thickness S1813 5000 --dilution 0.8
    """
    try:
        r = spin_thickness(resist.upper(), rpm, dilution)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    _header("Resist Thickness")
    _row("Resist", r["resist"])
    _row("Spin speed", f"{r['rpm']} RPM")
    _row("Dilution", f"{r['dilution']}")
    _row("Thickness", f"{r['thickness_nm']:.0f} nm  ({r['thickness_um']:.3f} um)")
    _row("Pre-bake", r["prebake"])
    _row("Developer", r["developer"])
    _row("Notes", r["notes"])
    click.echo()


@cli.command()
@click.argument("resist")
@click.argument("target_nm", type=float)
@click.option("--dilution", default=1.0, show_default=True)
def rpm_for(resist, target_nm, dilution):
    """Calculate spin speed needed for a target resist thickness (nm).

    \b
    Example:
      lithoforge rpm-for AZ1512 800
    """
    try:
        rpm = spin_rpm_for_thickness(resist.upper(), target_nm, dilution)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    _header("RPM Calculator")
    _row("Resist", resist.upper())
    _row("Target thickness", f"{target_nm:.0f} nm")
    _row("Required spin speed", f"{rpm} RPM")
    click.echo()


@cli.command()
@click.argument("resist")
@click.argument("intensity", type=float)
@click.option("--overdose", default=1.2, show_default=True, help="Dose multiplier (1.0-1.5)")
@click.option("--transmission", default=0.80, show_default=True, help="LCD panel transmission")
def expose(resist, intensity, overdose, transmission):
    """Calculate MSLA exposure time.

    INTENSITY is the UV output at the LCD surface in mW/cm2.
    Typical Mars 5 Ultra: 2-5 mW/cm2 (measure with UV power meter).

    \b
    Examples:
      lithoforge expose AZ1512 3.0
      lithoforge expose S1813 2.5 --overdose 1.3
    """
    try:
        r = exposure_time(resist.upper(), intensity, overdose, transmission)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    _header("Exposure Calculator")
    _row("Resist", r["resist"])
    _row("Required dose", f"{r['required_dose_mJ_cm2']} mJ/cm2")
    _row("LCD intensity", f"{r['intensity_at_lcd_mW_cm2']} mW/cm2")
    _row("Effective intensity", f"{r['effective_intensity_mW_cm2']} mW/cm2 (after LCD loss)")
    _row("Exposure time", click.style(f"{r['exposure_time_s']} s", bold=True))
    _row("Tip", r["tip"])
    click.echo()


@cli.command()
@click.argument("resist")
def develop(resist):
    """Get development parameters for a resist.

    \b
    Example:
      lithoforge develop AZ1512
    """
    try:
        r = development_recipe(resist.upper())
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    _header("Development Recipe")
    _row("Resist", r["resist"])
    _row("Developer", r["developer_key"])
    _row("Preparation", r["prep"])
    _row("Temperature", f"{r['temp_C']} C")
    _row("Time", f"{r['time_range_s'][0]}-{r['time_range_s'][1]} s")
    _row("Method", r["method"])
    _row("Rinse", r["rinse"])
    _row("Notes", r["notes"])
    click.echo()


@cli.command()
@click.argument("etchant")
@click.argument("thickness_nm", type=float)
@click.option("--temp", default=None, type=float, help="Temperature in Celsius (overrides default)")
def etch(etchant, thickness_nm, temp):
    """Calculate wet etch time.

    \b
    Examples:
      lithoforge etch BHF_7_1 100
      lithoforge etch KOH_30PCT_80C 500
      lithoforge etch DILUTE_HNO3_10PCT 200
    """
    try:
        r = etch_time(etchant.upper(), thickness_nm, temp)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    _header("Wet Etch Calculator")
    _row("Etchant", r["etchant"])
    _row("Target material", r.get("target_material", "N/A"))
    _row("Removal target", f"{r.get('target_nm', thickness_nm):.0f} nm")

    if "etch_rate_nm_min" in r:
        _row("Etch rate", f"{r['etch_rate_nm_min']} nm/min")
        _row("Etch time", click.style(f"{r['etch_time_s']:.0f} s  ({r['etch_time_min']:.2f} min)", bold=True))
        _row("With 10% overetch", f"{r['overetch_10pct_min']:.2f} min")

    click.echo(f"\n  {click.style('HAZARD:', fg='red', bold=True)} {r['hazard']}\n")


@cli.command()
@click.argument("temp_c", type=float)
@click.argument("time_min", type=float)
@click.option("--wet", is_flag=True, default=False, help="Wet oxidation (steam); default is dry O2")
def oxide(temp_c, time_min, wet):
    """Estimate thermal oxide thickness (Deal-Grove model).

    \b
    Examples:
      lithoforge oxide 1100 60          # dry oxidation
      lithoforge oxide 1000 30 --wet    # wet (steam) oxidation
    """
    r = oxide_thickness(temp_c, time_min, wet)
    _header("Thermal Oxidation (Deal-Grove)")
    _row("Temperature", f"{r['temp_C']} C")
    _row("Time", f"{r['time_min']} min")
    _row("Mode", r["mode"])
    _row("Oxide thickness", click.style(f"{r['thickness_nm']:.0f} nm  ({r['thickness_um']:.3f} um)", bold=True))
    _row("Notes", r["notes"])
    click.echo()


@cli.command()
@click.option("--pitch", default=18.0, show_default=True, help="LCD pixel pitch in um")
@click.option("--wavelength", default=405.0, show_default=True, help="Wavelength in nm")
@click.option("--na", default=0.0, show_default=True, help="Numerical aperture (0 = contact mode)")
@click.option("--magnification", default=1.0, show_default=True, help="Objective magnification")
def resolution(pitch, wavelength, na, magnification):
    """Calculate minimum feature size for your optical setup.

    \b
    Examples:
      lithoforge resolution                          # contact mode, Mars 5 Ultra
      lithoforge resolution --magnification 20 --na 0.40
      lithoforge resolution --magnification 40 --na 0.65
    """
    r = resolution_limit(pitch, wavelength, na, magnification)
    _header("Resolution Limit")
    _row("LCD pixel pitch", f"{r['pixel_pitch_um']} um")
    _row("Magnification", f"{r['magnification']}x")
    _row("Effective pixel size", f"{r['effective_pixel_um']} um")
    _row("Diffraction limit (Rayleigh)", f"{r['diffraction_limit_um']} um")
    _row("Actual resolution", click.style(f"{r['resolution_um']} um  ({r['resolution_nm']} nm)", bold=True))
    _row("Limiting factor", r["limiting_factor"])
    click.echo()


# ── spacer lithography ────────────────────────────────────────────────────────

@cli.command()
@click.argument("mandrel_width_nm", type=float)
@click.argument("mandrel_pitch_nm", type=float)
@click.argument("film_thickness_nm", type=float)
@click.option("--etch-loss", default=5.0, show_default=True, help="Lateral etch loss in nm")
@click.option("--mandrel", default="resist", show_default=True,
              type=click.Choice(["resist", "oxide", "nitride"]), help="Mandrel material")
@click.option("--card", is_flag=True, default=False, help="Print full process card")
def spacer(mandrel_width_nm, mandrel_pitch_nm, film_thickness_nm, etch_loss, mandrel, card):
    """Calculate spacer (SADP) lithography dimensions.

    MANDREL_WIDTH_NM  mandrel line width in nm
    MANDREL_PITCH_NM  mandrel center-to-center pitch in nm
    FILM_THICKNESS_NM film thickness (= target spacer width) in nm

    \b
    Examples:
      lithoforge spacer 2000 4000 100       # 2um mandrel -> 100nm spacers
      lithoforge spacer 900 1800 50 --card  # print full process card
    """
    if card:
        click.echo(spacer_process_summary(mandrel_width_nm, mandrel_pitch_nm, film_thickness_nm))
        return

    try:
        r = calculate_spacer(mandrel_width_nm, mandrel_pitch_nm, film_thickness_nm, etch_loss, mandrel)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    _header("Spacer Lithography (SADP)")
    _row("Mandrel", f"{r.mandrel_width_nm:.0f} nm wide / {r.mandrel_pitch_nm:.0f} nm pitch")
    _row("Film thickness", f"{r.film_thickness_nm:.0f} nm")
    _row("Spacer width", click.style(f"{r.spacer_width_nm:.0f} nm", bold=True))
    _row("Output pitch", click.style(f"{r.output_pitch_nm:.0f} nm", bold=True))
    click.echo("\n  Process steps:")
    for step in r.process_steps:
        click.echo(f"    {step}")
    if r.warnings:
        click.echo()
        for w in r.warnings:
            click.echo(f"  {click.style('!', fg='yellow')} {w}")
    click.echo()


@cli.command()
@click.argument("target_nm", type=float)
@click.argument("litho_resolution_nm", type=float)
@click.option("--film-nm", default=None, type=float, help="Spacer film thickness limit in nm")
def multipattern(target_nm, litho_resolution_nm, film_nm):
    """Calculate how many SADP passes reach a target feature size.

    \b
    Example:
      lithoforge multipattern 100 900 --film-nm 80
    """
    r = multi_patterning(target_nm, litho_resolution_nm, film_nm)
    _header("Multi-Patterning Analysis")
    _row("Target half-pitch", f"{r['target_nm']} nm")
    _row("Litho resolution", f"{r['litho_resolution_nm']} nm")
    _row("Approach", click.style(r["approach"], bold=True))
    _row("Passes", f"{r['passes']}")
    _row("Achievable", click.style(f"{r['achievable_nm']} nm", bold=True))
    _row("Note", r["note"])
    click.echo()


# ── reference tables ──────────────────────────────────────────────────────────

@cli.command()
def resists():
    """List all supported photoresists."""
    click.echo(f"\n{'Photoresists':^55}")
    click.echo("=" * 55)
    for name, r in RESISTS.items():
        click.echo(f"\n  {click.style(name, bold=True)}")
        click.echo(f"    Type:        {r['type']}")
        click.echo(f"    Wavelength:  {r['wavelength_nm']} nm")
        click.echo(f"    Sensitivity: {r['sensitivity_mJ_cm2']} mJ/cm2")
        click.echo(f"    Developer:   {r['developer']}")
        click.echo(f"    Notes:       {r['notes']}")
    click.echo()


@cli.command()
def etchants():
    """List all supported etchants."""
    click.echo(f"\n{'Etchants':^55}")
    click.echo("=" * 55)
    for name, e in ETCHANTS.items():
        click.echo(f"\n  {click.style(name, bold=True)}")
        click.echo(f"    Target:  {e.get('target', 'N/A')}")
        rate = e.get("rate_nm_min")
        click.echo(f"    Rate:    {rate} nm/min" if rate else "    Rate:    see notes")
        click.echo(f"    Hazard:  {click.style(e.get('hazard','?'), fg='yellow')}")
    click.echo()


@cli.command()
@click.argument("resist")
@click.argument("rpm", type=int)
@click.argument("intensity", type=float)
def process_card(resist, rpm, intensity):
    """Print a full process card for a resist/setup combination.

    \b
    Example:
      lithoforge process-card AZ1512 4000 3.0
    """
    try:
        click.echo("\n" + full_process_card(resist.upper(), rpm, intensity))
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# ── helpers ───────────────────────────────────────────────────────────────────

def _header(title: str) -> None:
    click.echo(f"\n  {click.style(title, bold=True, underline=True)}")
    click.echo(f"  {'─' * 42}")


def _row(label: str, value: str) -> None:
    click.echo(f"  {label:<24} {value}")
