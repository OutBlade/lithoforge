"""
Pre-built test and device structures for DIY semiconductor lithography.

Each function takes a Mask and adds the structure at the given position.
All coordinates and sizes in micrometers.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .mask import Mask


def nmos_gate_mask(
    mask: "Mask",
    cx: float,
    cy: float,
    gate_length_um: float = 2.0,
    gate_width_um: float = 20.0,
) -> None:
    """
    Single NMOS gate electrode. Place over active region on a separate layer.
    gate_length_um is the critical dimension (channel length after gate patterning).
    """
    mask.rect(cx - gate_length_um / 2, cy - gate_width_um / 2, gate_length_um, gate_width_um)


def nmos_active(
    mask: "Mask",
    cx: float,
    cy: float,
    gate_length_um: float = 2.0,
    gate_width_um: float = 20.0,
    sd_length_um: float = 15.0,
) -> None:
    """
    NMOS active area: source + channel + drain as one rectangle.
    Typically used on the first layer (active / implant mask).
    """
    total_length = sd_length_um * 2 + gate_length_um
    mask.rect(cx - total_length / 2, cy - gate_width_um / 2, total_length, gate_width_um)


def contact_array(
    mask: "Mask",
    cx: float,
    cy: float,
    rows: int = 2,
    cols: int = 3,
    size_um: float = 1.5,
    pitch_um: float = 4.0,
) -> None:
    """Rectangular array of contact holes (vias)."""
    origin_x = cx - (cols - 1) * pitch_um / 2
    origin_y = cy - (rows - 1) * pitch_um / 2
    for r in range(rows):
        for c in range(cols):
            x = origin_x + c * pitch_um - size_um / 2
            y = origin_y + r * pitch_um - size_um / 2
            mask.rect(x, y, size_um, size_um)


def dram_cell(
    mask: "Mask",
    cx: float,
    cy: float,
    transistor_width_um: float = 4.0,
    capacitor_size_um: float = 10.0,
    layer: str = "active",
) -> None:
    """
    Single DRAM 1T1C cell structure.

    Layers:
    -------
    'active'   -- active region (diffusion)
    'gate'     -- wordline / gate
    'capacitor'-- storage capacitor plate
    'bitline'  -- bitline contact + metal
    """
    if layer == "active":
        # L-shaped active region: FET channel + capacitor node
        mask.rect(cx - transistor_width_um, cy - transistor_width_um / 2,
                  transistor_width_um * 2, transistor_width_um)
        mask.rect(cx - capacitor_size_um / 2, cy - transistor_width_um / 2 - capacitor_size_um,
                  capacitor_size_um, capacitor_size_um)

    elif layer == "gate":
        # Wordline runs perpendicular to the bitline
        mask.rect(cx - transistor_width_um / 2, cy - transistor_width_um * 1.5,
                  transistor_width_um / 2, transistor_width_um * 3)

    elif layer == "capacitor":
        # Storage node plate over capacitor active area
        pad = 1.0
        mask.rect(cx - capacitor_size_um / 2 + pad,
                  cy - transistor_width_um / 2 - capacitor_size_um + pad,
                  capacitor_size_um - 2 * pad,
                  capacitor_size_um - 2 * pad)

    elif layer == "bitline":
        # Bitline contact + vertical metal trace
        mask.rect(cx + transistor_width_um / 2, cy - transistor_width_um / 2,
                  transistor_width_um / 4, transistor_width_um)
        mask.rect(cx + transistor_width_um / 2 + transistor_width_um / 8,
                  cy - transistor_width_um * 3, transistor_width_um / 4,
                  transistor_width_um * 6)


def dram_array(
    mask: "Mask",
    origin_x: float,
    origin_y: float,
    rows: int = 4,
    cols: int = 5,
    cell_pitch_x_um: float = 30.0,
    cell_pitch_y_um: float = 30.0,
    transistor_width_um: float = 4.0,
    capacitor_size_um: float = 10.0,
    layer: str = "active",
) -> None:
    """
    Array of DRAM cells (same as Dr. Semiconductor's 5x4 demo array).
    Target: 5x4 = 20 bits.
    """
    for r in range(rows):
        for c in range(cols):
            cx = origin_x + c * cell_pitch_x_um
            cy = origin_y + r * cell_pitch_y_um
            dram_cell(mask, cx, cy, transistor_width_um, capacitor_size_um, layer)


def mosfet_test_structure(
    mask: "Mask",
    cx: float,
    cy: float,
    gate_lengths_um: list = None,
    gate_width_um: float = 20.0,
) -> None:
    """
    Row of MOSFETs with increasing gate lengths for process evaluation.
    Each device has its own source/drain and gate.
    """
    if gate_lengths_um is None:
        gate_lengths_um = [1.0, 2.0, 5.0, 10.0, 20.0]

    spacing = 60.0
    x = cx
    for gl in gate_lengths_um:
        nmos_active(mask, x, cy, gl, gate_width_um)
        x += spacing


def serpentine_resistor(
    mask: "Mask",
    x: float,
    y: float,
    width_um: float = 5.0,
    segment_length_um: float = 100.0,
    n_segments: int = 10,
) -> None:
    """
    Serpentine resistor for sheet resistance extraction.
    Resistance R = Rs * (n_segments * segment_length / width).
    """
    turn_gap = width_um * 0.5
    pitch = width_um + turn_gap
    cursor_y = y

    for i in range(n_segments):
        if i % 2 == 0:
            mask.rect(x, cursor_y, segment_length_um, width_um)
            if i < n_segments - 1:
                mask.rect(x + segment_length_um - width_um, cursor_y, width_um, pitch + width_um)
        else:
            mask.rect(x, cursor_y, segment_length_um, width_um)
            if i < n_segments - 1:
                mask.rect(x, cursor_y, width_um, pitch + width_um)
        cursor_y += pitch


def resolution_target(
    mask: "Mask",
    cx: float,
    cy: float,
    pixel_pitch_um: float = 18.0,
) -> None:
    """
    Resolution test target: Siemens star + CD bars at 1-10x pixel pitch.
    Use this on every wafer run to track your actual achievable resolution.
    """
    import numpy as np

    # Siemens star: 24 spokes, fills a 60 um circle
    r = 60.0
    spokes = 24
    for i in range(spokes):
        angle = i * 2 * np.pi / spokes
        x1 = cx + r * np.cos(angle)
        y1 = cy + r * np.sin(angle)
        mask.line(cx, cy, x1, y1, pixel_pitch_um * 0.5)

    # CD bars at multiples of pixel pitch
    widths = [pixel_pitch_um * m for m in [1, 2, 3, 5, 10]]
    mask.cd_bars(cx - 200, cy + r + 20, widths, length_um=50)

    # Alignment mark in corner
    mask.alignment_mark(cx - 200, cy)
