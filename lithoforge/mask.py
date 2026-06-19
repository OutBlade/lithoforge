"""
Mask design module for DIY semiconductor lithography.
Coordinates are in micrometers. Origin (0,0) is top-left.
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import List, Tuple, Optional

# Elegoo Mars 5 Ultra specs
MARS5_PIXEL_PITCH_UM = 18.0
MARS5_RESOLUTION = (8520, 4320)
MARS5_BUILD_AREA_MM = (153.36, 77.76)


class Mask:
    """
    Lithography mask for MSLA-based DIY semiconductor fabrication.

    All dimensions in micrometers (um). Pixel values: 0 = unexposed, 255 = exposed.
    For positive resist: 255 = resist removed after development.
    """

    def __init__(
        self,
        width_um: float,
        height_um: float,
        pixel_pitch_um: float = MARS5_PIXEL_PITCH_UM,
        background: str = "clear",
    ):
        self.width_um = width_um
        self.height_um = height_um
        self.pixel_pitch_um = pixel_pitch_um

        self.width_px = max(1, round(width_um / pixel_pitch_um))
        self.height_px = max(1, round(height_um / pixel_pitch_um))

        bg = 0 if background == "clear" else 255
        self._data = np.full((self.height_px, self.width_px), bg, dtype=np.uint8)

    # ── coordinate helpers ────────────────────────────────────────────────────

    def _px(self, v: float) -> int:
        return int(round(v / self.pixel_pitch_um))

    def _clip(self, v: int, lo: int, hi: int) -> int:
        return max(lo, min(hi, v))

    # ── primitive shapes ──────────────────────────────────────────────────────

    def rect(self, x: float, y: float, w: float, h: float, expose: bool = True) -> "Mask":
        """Draw a filled rectangle. x,y = top-left in um."""
        x0 = self._clip(self._px(x), 0, self.width_px)
        y0 = self._clip(self._px(y), 0, self.height_px)
        x1 = self._clip(self._px(x + w), 0, self.width_px)
        y1 = self._clip(self._px(y + h), 0, self.height_px)
        self._data[y0:y1, x0:x1] = 255 if expose else 0
        return self

    def circle(self, cx: float, cy: float, r: float, expose: bool = True) -> "Mask":
        """Draw a filled circle. cx,cy = center in um."""
        img = Image.fromarray(self._data)
        draw = ImageDraw.Draw(img)
        x0 = self._px(cx - r)
        y0 = self._px(cy - r)
        x1 = self._px(cx + r)
        y1 = self._px(cy + r)
        draw.ellipse([x0, y0, x1, y1], fill=255 if expose else 0)
        self._data = np.array(img)
        return self

    def polygon(self, points: List[Tuple[float, float]], expose: bool = True) -> "Mask":
        """Draw a filled polygon. points = [(x,y), ...] in um."""
        img = Image.fromarray(self._data)
        draw = ImageDraw.Draw(img)
        px_pts = [(self._px(x), self._px(y)) for x, y in points]
        draw.polygon(px_pts, fill=255 if expose else 0)
        self._data = np.array(img)
        return self

    def ring(self, cx: float, cy: float, r_outer: float, r_inner: float, expose: bool = True) -> "Mask":
        """Draw an annular ring."""
        self.circle(cx, cy, r_outer, expose=expose)
        self.circle(cx, cy, r_inner, expose=not expose)
        return self

    def line(self, x0: float, y0: float, x1: float, y1: float, width_um: float, expose: bool = True) -> "Mask":
        """Draw a line with given width in um."""
        img = Image.fromarray(self._data)
        draw = ImageDraw.Draw(img)
        w_px = max(1, self._px(width_um))
        draw.line(
            [(self._px(x0), self._px(y0)), (self._px(x1), self._px(y1))],
            fill=255 if expose else 0,
            width=w_px,
        )
        self._data = np.array(img)
        return self

    # ── composite structures ───────────────────────────────────────────────────

    def array(
        self,
        shape_fn,
        rows: int,
        cols: int,
        pitch_x_um: float,
        pitch_y_um: float,
        **kwargs,
    ) -> "Mask":
        """Tile a shape in a rectangular array."""
        for r in range(rows):
            for c in range(cols):
                shape_fn(x_offset=c * pitch_x_um, y_offset=r * pitch_y_um, **kwargs)
        return self

    def alignment_mark(self, cx: float, cy: float, size_um: float = 60.0) -> "Mask":
        """
        Crosshair + outer box alignment mark.
        Generates a cross and surrounding box for layer-to-layer alignment.
        """
        h = size_um / 2
        bar = max(self.pixel_pitch_um * 2, size_um * 0.06)

        self.rect(cx - h, cy - bar / 2, size_um, bar)
        self.rect(cx - bar / 2, cy - h, bar, size_um)
        self._box_outline(cx - h, cy - h, size_um, size_um, bar * 0.5)
        return self

    def vernier(
        self,
        cx: float,
        cy: float,
        pitch_um: float = 10.0,
        count: int = 11,
        height_um: float = 40.0,
    ) -> "Mask":
        """
        Vernier scale alignment marks.
        Primary scale at pitch_um, secondary at pitch_um * count/(count+1).
        Place matching vernier on each layer to measure overlay error.
        """
        bar_w = max(self.pixel_pitch_um, pitch_um * 0.15)
        total = count * pitch_um
        fine_pitch = pitch_um * count / (count + 1)

        for i in range(count):
            x = cx - total / 2 + i * pitch_um
            self.rect(x, cy - height_um, bar_w, height_um)

        for i in range(count):
            x = cx - total / 2 + i * fine_pitch
            self.rect(x, cy, bar_w, height_um)

        return self

    def cd_bars(
        self,
        x: float,
        y: float,
        widths_um: Optional[List[float]] = None,
        length_um: float = 80.0,
        spacing_um: float = 10.0,
    ) -> "Mask":
        """
        Critical Dimension test structures -- a row of lines of increasing width.
        Measure these after exposure to calibrate your actual print resolution.
        """
        if widths_um is None:
            widths_um = [1, 2, 5, 10, 20, 50, 100]

        cursor = x
        for w in widths_um:
            self.rect(cursor, y, w, length_um)
            cursor += w + spacing_um

        return self

    def van_der_pauw(self, cx: float, cy: float, size_um: float = 200.0) -> "Mask":
        """
        Van der Pauw structure for measuring sheet resistance.
        Square active area with four contact pads at corners.
        """
        half = size_um / 2
        pad = size_um * 0.3
        gap = size_um * 0.05

        self.rect(cx - half, cy - half, size_um, size_um)

        for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
            px = cx + dx * (half + gap)
            py = cy + dy * (half + gap)
            self.rect(px - pad / 2 if dx < 0 else px, py - pad / 2, pad, pad)

        return self

    def hall_bar(self, cx: float, cy: float, length_um: float = 400.0, width_um: float = 80.0) -> "Mask":
        """
        Hall bar test structure for measuring carrier mobility and sheet resistance.
        """
        half_l = length_um / 2
        half_w = width_um / 2
        arm_w = width_um * 0.4
        arm_l = width_um * 1.5

        self.rect(cx - half_l, cy - half_w, length_um, width_um)

        for side in [-1, 1]:
            for frac in [-0.4, 0.0, 0.4]:
                self.rect(
                    cx + frac * length_um - arm_w / 2,
                    cy + side * half_w,
                    arm_w,
                    side * arm_l,
                )

        return self

    # ── boolean operations ────────────────────────────────────────────────────

    def invert(self) -> "Mask":
        """Invert exposed/unexposed areas (swap dark/clear field)."""
        self._data = 255 - self._data
        return self

    def merge(self, other: "Mask", operation: str = "union") -> "Mask":
        """Combine with another mask. operations: union, intersect, subtract."""
        assert other._data.shape == self._data.shape, "Mask dimensions must match"
        a = self._data.astype(bool)
        b = other._data.astype(bool)

        if operation == "union":
            result = a | b
        elif operation == "intersect":
            result = a & b
        elif operation == "subtract":
            result = a & ~b
        else:
            raise ValueError(f"Unknown operation: {operation}")

        self._data = result.astype(np.uint8) * 255
        return self

    # ── output ────────────────────────────────────────────────────────────────

    def save(self, path: str, dpi: Optional[int] = None) -> None:
        """Save as PNG. Set dpi to embed resolution metadata."""
        img = Image.fromarray(self._data, mode="L")
        save_kwargs = {}
        if dpi:
            save_kwargs["dpi"] = (dpi, dpi)
        img.save(path, **save_kwargs)

    def save_for_mars5(self, path: str) -> None:
        """Save PNG sized and DPI-annotated for the Elegoo Mars 5 Ultra LCD."""
        dpi_x = round(25400 / MARS5_PIXEL_PITCH_UM)
        self.save(path, dpi=dpi_x)

    def preview(self, title: str = "Mask Preview", show_grid: bool = False) -> None:
        """Display mask with matplotlib."""
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches

        fig, ax = plt.subplots(figsize=(12, 7))
        ax.imshow(
            self._data,
            cmap="gray",
            origin="upper",
            extent=[0, self.width_um, self.height_um, 0],
            vmin=0,
            vmax=255,
        )

        if show_grid:
            step = max(self.width_um, self.height_um) / 10
            ax.set_xticks(np.arange(0, self.width_um, step))
            ax.set_yticks(np.arange(0, self.height_um, step))
            ax.grid(color="red", alpha=0.3, linewidth=0.5)

        ax.set_xlabel("X (um)")
        ax.set_ylabel("Y (um)")
        ax.set_title(f"{title}  [{self.width_px}x{self.height_px} px @ {self.pixel_pitch_um}um/px]")

        exposed = mpatches.Patch(color="white", label="Exposed (positive resist: removed)")
        unexposed = mpatches.Patch(color="black", label="Unexposed (resist retained)")
        ax.legend(handles=[exposed, unexposed], loc="lower right", fontsize=8)

        plt.tight_layout()
        plt.show()

    def get_array(self) -> np.ndarray:
        return self._data.copy()

    def stats(self) -> dict:
        total = self._data.size
        exposed = int(np.sum(self._data > 127))
        return {
            "width_um": self.width_um,
            "height_um": self.height_um,
            "width_px": self.width_px,
            "height_px": self.height_px,
            "pixel_pitch_um": self.pixel_pitch_um,
            "total_pixels": total,
            "exposed_pixels": exposed,
            "exposed_pct": round(exposed / total * 100, 2),
            "exposed_area_mm2": round(exposed * (self.pixel_pitch_um / 1000) ** 2, 4),
        }

    # ── internal helpers ──────────────────────────────────────────────────────

    def _box_outline(self, x, y, w, h, lw):
        self.rect(x, y, w, lw)
        self.rect(x, y + h - lw, w, lw)
        self.rect(x, y, lw, h)
        self.rect(x + w - lw, y, lw, h)
