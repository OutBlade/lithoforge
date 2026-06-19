"""
Example 04: DRAM cell array mask set (5x4 = 20 bits).

Replicates the Dr. Semiconductor approach (Hackaday, April 2026) --
the first hobbyist-made DRAM array.

Generates masks for all four process layers:
  active    -- diffusion regions (source + capacitor)
  gate      -- wordlines (access transistor gates)
  capacitor -- storage capacitor bottom plate
  bitline   -- bitline metal + contacts

Feature size: 4 um transistor width -- achievable in contact mode on Mars 5 Ultra.
For smaller cells use a 20x objective and scale down.
"""

from lithoforge import Mask
from lithoforge import structures
from lithoforge.process import oxide_thickness, spin_thickness, exposure_time

ROWS = 4
COLS = 5
CELL_PITCH_X = 40.0    # um
CELL_PITCH_Y = 50.0    # um
TRANSISTOR_W = 4.0     # um
CAP_SIZE = 12.0        # um
PIXEL_PITCH = 18.0

FIELD_W = COLS * CELL_PITCH_X + 100
FIELD_H = ROWS * CELL_PITCH_Y + 100
ORIGIN_X = 50.0
ORIGIN_Y = 50.0


def base_mask(layer_name: str) -> Mask:
    m = Mask(FIELD_W, FIELD_H, pixel_pitch_um=PIXEL_PITCH)
    m.alignment_mark(20, 20, size_um=40)
    m.alignment_mark(FIELD_W - 20, 20, size_um=40)
    m.alignment_mark(20, FIELD_H - 20, size_um=40)
    m.alignment_mark(FIELD_W - 20, FIELD_H - 20, size_um=40)
    m.vernier(FIELD_W / 2, 10, pitch_um=8, count=9, height_um=20)
    return m


for layer in ["active", "gate", "capacitor", "bitline"]:
    m = base_mask(layer)

    structures.dram_array(
        m,
        origin_x=ORIGIN_X,
        origin_y=ORIGIN_Y,
        rows=ROWS,
        cols=COLS,
        cell_pitch_x_um=CELL_PITCH_X,
        cell_pitch_y_um=CELL_PITCH_Y,
        transistor_width_um=TRANSISTOR_W,
        capacitor_size_um=CAP_SIZE,
        layer=layer,
    )

    filename = f"dram_{layer}.png"
    m.save(filename)
    print(f"Saved {filename}  [{m.width_px}x{m.height_px} px]")

# ── Process notes ─────────────────────────────────────────────────────────────

print("\n" + "=" * 55)
print("  DRAM PROCESS NOTES")
print("=" * 55)

print("\n  Gate oxide:")
ox = oxide_thickness(1100, 30, wet=False)
print(f"    Dry oxidation 1100 C / 30 min = {ox['thickness_nm']:.0f} nm SiO2")
ox_wet = oxide_thickness(1000, 10, wet=True)
print(f"    Wet oxidation 1000 C / 10 min = {ox_wet['thickness_nm']:.0f} nm SiO2 (faster)")

print("\n  Resist for 4 um features (contact mode, no objective):")
t = spin_thickness("AZ1512", 4000)
e = exposure_time("AZ1512", 3.0)
print(f"    AZ1512 @ 4000 RPM = {t['thickness_nm']:.0f} nm")
print(f"    Exposure = {e['exposure_time_s']} s at 3 mW/cm2")

print("\n  Expected result:")
print(f"    {ROWS}x{COLS} = {ROWS*COLS} DRAM cells")
print(f"    Storage capacitance target: ~12 pF (matches Dr. Semiconductor result)")
print(f"    Test with C-V plotter or LCR meter")
print()
