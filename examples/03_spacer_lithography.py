"""
Example 03: Spacer lithography to 100 nm features.

Demonstrates the full SADP workflow calculation and generates the mandrel mask.
Goal: 100 nm Ni spacers from a 2 um lithographic mandrel.

Physical process:
    1. Print this mandrel mask on AZ1512
    2. Plate ~110 nm electroless Ni
    3. Etch back Ni (plasma cleaner ~30 s, or timed HNO3)
    4. Strip resist mandrel in acetone
    Result: 100 nm Ni lines at 1000 nm pitch
"""

from lithoforge import Mask
from lithoforge.spacer import calculate_spacer, spacer_process_summary, multi_patterning
from lithoforge.process import resolution_limit, spin_thickness, exposure_time, electroless_ni_time

# ── 1. Process design ─────────────────────────────────────────────────────────

MANDREL_NM = 2000        # 2 um -- achievable with 20x objective (0.9 um pixel)
PITCH_NM = 4000          # 4 um pitch
TARGET_NM = 100          # 100 nm spacer target

result = calculate_spacer(
    mandrel_width_nm=MANDREL_NM,
    mandrel_pitch_nm=PITCH_NM,
    film_thickness_nm=TARGET_NM + 10,   # add 10 nm margin for etch loss
    lateral_etch_loss_nm=10,
)

print(result)

# ── 2. Multi-patterning analysis ──────────────────────────────────────────────

print("\nHow many passes from 900 nm litho resolution to 100 nm?")
mp = multi_patterning(target_half_pitch_nm=100, litho_resolution_nm=900, spacer_film_nm=110)
print(f"  Approach: {mp['approach']}")
print(f"  Passes:   {mp['passes']}")
print(f"  Achievable: {mp['achievable_nm']} nm")

# ── 3. Equipment parameters ───────────────────────────────────────────────────

print("\nOptical setup for 2 um mandrels with Mars 5 Ultra:")
r = resolution_limit(pixel_pitch_um=18.0, wavelength_nm=405, na=0.40, magnification=20)
print(f"  20x objective:  {r['resolution_nm']} nm resolution  (limiting: {r['limiting_factor']})")

print(f"\nElectroless Ni plating for 110 nm film:")
t_min = electroless_ni_time(110, temp_C=25)
print(f"  ~{t_min:.0f} min at 25 C room temperature")

# ── 4. Generate mandrel mask ──────────────────────────────────────────────────

# 200 um wide strip with repeating 2 um lines at 4 um pitch
mask = Mask(400, 200, pixel_pitch_um=18.0)

pitch_um = PITCH_NM / 1000
mandrel_w_um = MANDREL_NM / 1000

x = 20.0
while x + mandrel_w_um < 380:
    mask.rect(x, 40, mandrel_w_um, 120)
    x += pitch_um

mask.alignment_mark(20, 170, size_um=30)
mask.alignment_mark(380, 170, size_um=30)
mask.cd_bars(20, 10, widths_um=[mandrel_w_um, mandrel_w_um * 2], length_um=25)

mask.save("mandrel_mask.png")
print("\nSaved mandrel_mask.png")
print(f"  {mask.width_px} x {mask.height_px} pixels")
print(f"  Mandrel lines: {mandrel_w_um} um wide at {pitch_um} um pitch")

# ── 5. Full process card ──────────────────────────────────────────────────────

print("\n" + spacer_process_summary(MANDREL_NM, PITCH_NM, TARGET_NM + 10))
