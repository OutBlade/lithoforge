"""
Example 02: 3-layer NMOS transistor mask set.

Generates three separate PNG files (one per layer) for a basic NMOS process:
  Layer 1 -- active region (defines source, channel, drain)
  Layer 2 -- gate (polysilicon or metal gate)
  Layer 3 -- contact holes

Designed for a 2 um gate length -- achievable with a 20x objective on the Mars 5 Ultra.
"""

from lithoforge import Mask
from lithoforge import structures

FIELD_UM = 500          # 500x500 um die field
GATE_L = 2.0            # 2 um gate length
GATE_W = 20.0           # 20 um gate width
PIXEL_PITCH = 18.0      # Mars 5 Ultra


def make_field(name: str) -> Mask:
    m = Mask(FIELD_UM, FIELD_UM, pixel_pitch_um=PIXEL_PITCH)
    m.alignment_mark(30, 30, size_um=50)
    m.alignment_mark(FIELD_UM - 30, 30, size_um=50)
    m.alignment_mark(30, FIELD_UM - 30, size_um=50)
    m.alignment_mark(FIELD_UM - 30, FIELD_UM - 30, size_um=50)
    m.vernier(FIELD_UM / 2, 20, pitch_um=10, count=11, height_um=25)
    return m


# ── Layer 1: Active region ────────────────────────────────────────────────────

active = make_field("active")

# Single transistor in center
structures.nmos_active(active, cx=250, cy=250, gate_length_um=GATE_L, gate_width_um=GATE_W, sd_length_um=15.0)

# Row of test transistors with different gate lengths
structures.mosfet_test_structure(active, cx=250, cy=380, gate_lengths_um=[1, 2, 5, 10, 20], gate_width_um=GATE_W)

# Resolution target
structures.resolution_target(active, cx=420, cy=80, pixel_pitch_um=PIXEL_PITCH)

active.save("layer1_active.png")
print("Saved layer1_active.png")


# ── Layer 2: Gate ─────────────────────────────────────────────────────────────

gate = make_field("gate")

# Gate electrode -- exactly GATE_L wide, runs full width of active area
gate.rect(250 - GATE_L / 2, 250 - GATE_W / 2 - 10, GATE_L, GATE_W + 20)

# Gate bus connecting to pad
gate.rect(250 - GATE_L / 2, 100, GATE_L, 140)
gate.rect(200, 80, 100, 30)  # gate pad

gate.save("layer2_gate.png")
print("Saved layer2_gate.png")


# ── Layer 3: Contact holes ────────────────────────────────────────────────────

contacts = make_field("contacts")

# Source contacts (left of gate)
structures.contact_array(contacts, cx=240 - GATE_L / 2 - 10, cy=250, rows=2, cols=2, size_um=1.5, pitch_um=5)

# Drain contacts (right of gate)
structures.contact_array(contacts, cx=260 + GATE_L / 2 + 10, cy=250, rows=2, cols=2, size_um=1.5, pitch_um=5)

# Gate contact
contacts.rect(240, 90, 20, 20)

contacts.save("layer3_contacts.png")
print("Saved layer3_contacts.png")

print("\nMask set complete. Process layers in order: active -> gate -> contacts.")
print("Use vernier marks on each layer to measure overlay error before proceeding.")
