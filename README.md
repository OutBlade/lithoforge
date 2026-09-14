# LithoForge

<!-- project-navigation -->
[Getting started](#install) · [Features](#what-it-does)
<!-- /project-navigation -->

**DIY semiconductor lithography toolkit for MSLA printers.**

Process calculators, mask designer, OPC engine, and spacer lithography tools
built for hobbyists using consumer LCD/MSLA printers (Elegoo Mars 5 Ultra and compatible).

Validated against the [2025 Wiley maskless LCD lithography paper](https://onlinelibrary.wiley.com/doi/full/10.1002/smtd.202501336)
and [Sam Zeloof's home chip fab](https://sam.zeloof.xyz/category/semiconductor/).

---

## What it does

| Module | Purpose |
|--------|---------|
| `lithoforge.Mask` | Draw mask patterns in micrometers, export PNG for your MSLA printer |
| `lithoforge.opc` | Rule-based Optical Proximity Correction for 405 nm exposure |
| `lithoforge.process` | Spin thickness, exposure time, develop, etch, and oxide calculators |
| `lithoforge.spacer` | SADP spacer lithography -- calculate 50-200 nm features from micron mandrels |
| `lithoforge.structures` | Pre-built MOSFET, DRAM cell, Van der Pauw, Hall bar, and test structures |
| `lithoforge` CLI | All calculators from the terminal |

---

## Hardware this targets

| Parameter | Value |
|-----------|-------|
| Printer | Elegoo Mars 5 Ultra (or any 405 nm MSLA) |
| LCD pixel pitch | 18 x 18 um |
| Native resolution (contact mode) | ~18 um |
| With 20x objective (NA 0.40) | ~0.9 um |
| With spacer lithography | 50-200 nm |
| Photoresist | AZ 1512 (recommended), S1813, or dry film |

---

## Install

```bash
pip install lithoforge
```

Or from source:

```bash
git clone https://github.com/OutBlade/lithoforge
cd lithoforge
pip install -e .
```

---

## Quick start

### Python API

```python
from lithoforge import Mask
from lithoforge.process import spin_thickness, exposure_time

# Design a mask
mask = Mask(500, 300)           # 500 x 300 um field
mask.rect(100, 100, 10, 50)    # 10 x 50 um rectangle
mask.alignment_mark(20, 20)    # crosshair alignment mark
mask.cd_bars(20, 200)          # critical dimension test bars
mask.save("layer1.png")        # ready for your slicer

# Calculate process parameters
t = spin_thickness("AZ1512", 4000)
print(f"Thickness: {t['thickness_nm']:.0f} nm")

e = exposure_time("AZ1512", intensity_mW_cm2=3.0)
print(f"Expose for: {e['exposure_time_s']} s")
```

### CLI

```bash
# Resist thickness from spin speed
lithoforge thickness AZ1512 4000

# Exposure time (3 mW/cm2 intensity)
lithoforge expose AZ1512 3.0

# Wet etch calculator
lithoforge etch BHF_7_1 100

# Resolution limit for 20x objective
lithoforge resolution --magnification 20 --na 0.40

# Spacer lithography: 2 um mandrel -> 100 nm spacers
lithoforge spacer 2000 4000 110 --card

# Thermal oxide (Deal-Grove model)
lithoforge oxide 1100 60

# List all supported resists or etchants
lithoforge resists
lithoforge etchants
```

---

## Mask design

```python
from lithoforge import Mask

m = Mask(width_um=1000, height_um=600)

# Primitives
m.rect(x, y, w, h)                     # rectangle
m.circle(cx, cy, radius)               # filled circle
m.ring(cx, cy, r_outer, r_inner)       # annular ring
m.polygon([(x0,y0), (x1,y1), ...])    # arbitrary polygon
m.line(x0, y0, x1, y1, width_um)      # line with width

# Alignment and metrology
m.alignment_mark(cx, cy, size_um=60)   # crosshair + box
m.vernier(cx, cy, pitch_um=10)         # vernier scale for overlay measurement
m.cd_bars(x, y)                        # critical dimension test bars

# Boolean operations
m.invert()                             # swap exposed / unexposed
m.merge(other_mask, "union")           # union / intersect / subtract

# Export
m.save("mask.png")                     # standard PNG
m.save_for_mars5("mask.png")          # PNG with correct DPI metadata
m.preview()                            # matplotlib preview window
```

---

## Optical Proximity Correction

```python
from lithoforge import Mask
from lithoforge.opc import apply_opc, simulate_aerial_image

mask = Mask(200, 100)
mask.rect(10, 10, 5, 80)

# Apply OPC corrections
corrected = apply_opc(
    mask.get_array(),
    pixel_pitch_um=18.0,
    wavelength_nm=405.0,
    na=0.40,              # NA of your objective
    bias_nm=50,           # grow features by 50 nm to compensate shrinkage
    corner_serif=True,    # add serifs to convex corners
    line_end_extension=True,
)

# Simulate what the aerial image looks like
aerial = simulate_aerial_image(corrected, na=0.40, defocus_um=1.0)
```

---

## Spacer lithography (50-200 nm)

```python
from lithoforge.spacer import calculate_spacer, spacer_process_summary

# 2 um mandrel, 110 nm Ni film -> ~100 nm spacers
result = calculate_spacer(
    mandrel_width_nm=2000,
    mandrel_pitch_nm=4000,
    film_thickness_nm=110,
)
print(result)

# Print a full process card
print(spacer_process_summary(2000, 4000, 110))
```

Spacer lithography process (minimal equipment ~$450):
1. Print mandrel mask on AZ1512 with Mars 5 Ultra + 20x objective
2. Electroless Ni-P plate for ~7 min at room temperature
3. Etch back with oxygen plasma (or timed 10% HNO3)
4. Strip resist mandrel in acetone
5. Result: ~100 nm Ni lines at 2 um pitch

---

## Pre-built structures

```python
from lithoforge import Mask, structures

m = Mask(500, 500)

# NMOS transistor (4-layer process)
structures.nmos_active(m, cx=250, cy=250, gate_length_um=2.0, gate_width_um=20.0)

# DRAM cell array -- same as Dr. Semiconductor's 2026 demo
structures.dram_array(m, origin_x=50, origin_y=50, rows=4, cols=5, layer="active")

# Test structures
structures.van_der_pauw(m, cx=100, cy=100)    # sheet resistance
structures.hall_bar(m, cx=300, cy=100)         # carrier mobility
structures.serpentine_resistor(m, x=50, y=300)
structures.resolution_target(m, cx=400, cy=400)
```

---

## Process database

### Resists

| Name | Type | Sensitivity | Notes |
|------|------|-------------|-------|
| AZ1512 | Positive | 55 mJ/cm2 | Best for 405 nm MSLA |
| S1813 | Positive | 150 mJ/cm2 | Very well documented |
| AZ5214E | Image reversal | 40 mJ/cm2 | Lift-off and negative tone |
| DRY_FILM_PCB | Negative | 30 mJ/cm2 | No spin coater needed |

### Etchants

| Name | Target | Rate |
|------|--------|------|
| BHF_7_1 | SiO2 | 100 nm/min |
| KOH_30PCT_80C | Si (anisotropic) | 1000 nm/min |
| TMAH_25PCT_80C | Si (anisotropic) | 600 nm/min |
| AL_ETCHANT_A | Al metal | 30 nm/min |
| DILUTE_HNO3_10PCT | Ni (spacer etchback) | 50 nm/min |

---

## Examples

| File | Description |
|------|-------------|
| `examples/01_first_mask.py` | First exposure test -- contact mode |
| `examples/02_mosfet_mask_set.py` | 3-layer NMOS process |
| `examples/03_spacer_lithography.py` | SADP to 100 nm features |
| `examples/04_dram_cell_array.py` | 5x4 DRAM array (Dr. Semiconductor style) |

---

## Safety

Working with photoresist chemicals and etchants requires proper precautions.
LithoForge prints hazard warnings for every etchant. Key rules:

- HF and BHF: full face shield, neoprene gloves, calcium gluconate gel nearby
- KOH / TMAH: chemical splash goggles, gloves, fume hood
- Photoresist solvents: flammable -- no ignition sources
- Start with dry film resist and washing soda developer (both very safe) before progressing to liquid resist and acid etchants

---

## References

- [Low-Cost Maskless Photolithography Using LCD 3D Printer (Wiley 2025)](https://onlinelibrary.wiley.com/doi/full/10.1002/smtd.202501336)
- [Sam Zeloof Home Chip Lab](https://sam.zeloof.xyz/category/semiconductor/)
- [Dr. Semiconductor DRAM in a Shed (Hackaday 2026)](https://hackaday.com/2026/04/22/making-ram-at-home-in-your-own-semiconductor-fab/)
- [AZ1512 Process SOP -- University of Washington](https://faculty.washington.edu/tcchen/EE527Wi/Labs/SOP_AZ1512_Photolithography_WangLugo2009.pdf)

---

## License

MIT
