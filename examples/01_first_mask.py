"""
Example 01: Your first lithography mask.

Generates a simple test field with alignment marks, CD bars, and a rectangle.
Save the PNG, load it into your slicer as a flat single-layer print,
place your substrate on the LCD, and expose.
"""

from lithoforge import Mask
from lithoforge.process import spin_thickness, exposure_time, development_recipe, resolution_limit

# ── 1. Design the mask ────────────────────────────────────────────────────────

# 3mm x 2mm field on the Mars 5 Ultra (18 um/pixel)
mask = Mask(3000, 2000, pixel_pitch_um=18.0)

# Alignment marks at all four corners
for ax, ay in [(100, 100), (2900, 100), (100, 1900), (2900, 1900)]:
    mask.alignment_mark(ax, ay, size_um=60)

# CD bars across the center -- measures your actual print resolution
mask.cd_bars(x=200, y=900, widths_um=[18, 36, 54, 90, 180, 360], length_um=200)

# A simple test rectangle (10 um x 100 um -- 1 pixel wide at 18 um/px)
mask.rect(1400, 800, 100, 400)

# Label row (visible under microscope)
mask.rect(200, 1700, 50, 20)  # layer marker

# Save for Mars 5 Ultra
mask.save("first_mask.png")
print("Saved first_mask.png")
print(f"Stats: {mask.stats()}")

# ── 2. Print process parameters ───────────────────────────────────────────────

print("\n" + "=" * 50)
print("PROCESS PARAMETERS -- AZ1512 @ 4000 RPM")
print("=" * 50)

t = spin_thickness("AZ1512", 4000)
print(f"Resist thickness:  {t['thickness_nm']:.0f} nm")
print(f"Pre-bake:          {t['prebake']}")

e = exposure_time("AZ1512", intensity_mW_cm2=3.0)
print(f"Exposure time:     {e['exposure_time_s']} s  (at 3 mW/cm2)")

d = development_recipe("AZ1512")
print(f"Developer:         {d['prep']}")
print(f"Dev time:          {d['time_range_s'][0]}-{d['time_range_s'][1]} s")

r = resolution_limit(pixel_pitch_um=18.0)
print(f"\nContact mode resolution: {r['resolution_nm']} nm  (pixel-limited)")
