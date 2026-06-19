"""
LithoForge -- DIY Semiconductor Lithography Toolkit

Quick start:
    from lithoforge import Mask
    from lithoforge.process import spin_thickness, exposure_time
    from lithoforge.spacer import calculate_spacer
    from lithoforge.opc import apply_opc

    mask = Mask(500, 300)              # 500 x 300 um field
    mask.rect(100, 100, 10, 50)       # 10x50 um rectangle
    mask.alignment_mark(20, 20)
    mask.save("layer1.png")
"""

__version__ = "1.0.0"
__author__ = "LithoForge Contributors"
__license__ = "MIT"

from .mask import Mask, MARS5_PIXEL_PITCH_UM, MARS5_RESOLUTION
from . import process, spacer, opc, structures

__all__ = [
    "Mask",
    "MARS5_PIXEL_PITCH_UM",
    "MARS5_RESOLUTION",
    "process",
    "spacer",
    "opc",
    "structures",
]
