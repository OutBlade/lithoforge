"""
Optical Proximity Correction (OPC) for DIY semiconductor lithography.

Rule-based corrections compensate for diffraction and proximity effects
during UV exposure at 405 nm with MSLA printers.
"""

import numpy as np
from scipy import ndimage


def apply_opc(
    mask_array: np.ndarray,
    pixel_pitch_um: float = 18.0,
    wavelength_nm: float = 405.0,
    na: float = 0.0,
    bias_nm: float = 0.0,
    serif_nm: float = None,
    line_end_extension: bool = True,
    corner_serif: bool = True,
) -> np.ndarray:
    """
    Apply rule-based OPC to a mask.

    Parameters
    ----------
    mask_array : uint8 ndarray, 0=unexposed, 255=exposed
    pixel_pitch_um : LCD pixel pitch in micrometers (18 for Mars 5 Ultra)
    wavelength_nm : exposure wavelength (405 nm for MSLA)
    na : numerical aperture of projection lens; 0 = contact/proximity mode
    bias_nm : global linewidth bias in nm (positive = grow all features)
    serif_nm : serif / hammerhead size in nm (default = lambda/4)
    line_end_extension : extend line ends to prevent end-shortening
    corner_serif : add serif squares to convex corners

    Returns
    -------
    Corrected uint8 mask array
    """
    pixel_nm = pixel_pitch_um * 1000.0

    if serif_nm is None:
        serif_nm = wavelength_nm / 4.0

    binary = (mask_array > 127).astype(np.float32)

    # 1 ── Global bias (grow or shrink all features)
    if abs(bias_nm) >= pixel_nm * 0.5:
        n_iter = max(1, round(abs(bias_nm) / pixel_nm))
        struct = ndimage.generate_binary_structure(2, 1)
        if bias_nm > 0:
            binary = ndimage.binary_dilation(binary.astype(bool), structure=struct, iterations=n_iter).astype(np.float32)
        else:
            binary = ndimage.binary_erosion(binary.astype(bool), structure=struct, iterations=n_iter).astype(np.float32)

    serif_px = max(1, round(serif_nm / pixel_nm))

    # 2 ── Line end extension: find pixels with only one 4-connected neighbour
    if line_end_extension:
        binary = _extend_line_ends(binary, serif_px)

    # 3 ── Corner serifs: find convex L-junctions and add serif squares
    if corner_serif:
        binary = _add_corner_serifs(binary, serif_px)

    return (binary * 255).clip(0, 255).astype(np.uint8)


def simulate_aerial_image(
    mask_array: np.ndarray,
    pixel_pitch_um: float = 18.0,
    wavelength_nm: float = 405.0,
    na: float = 0.4,
    defocus_um: float = 0.0,
    threshold: float = 0.35,
) -> np.ndarray:
    """
    Simulate the aerial image (intensity pattern) formed by the optical system.

    Uses a Gaussian PSF approximation -- adequate for rule-based OPC evaluation.
    Returns a uint8 array: values show expected intensity, thresholded image
    approximates the developed resist profile.

    Parameters
    ----------
    threshold : normalised intensity at which resist clears (0-1)
    """
    if na <= 0:
        sigma_px = (wavelength_nm / 1000.0) / pixel_pitch_um * 0.3
    else:
        rayleigh_um = 0.61 * wavelength_nm / 1000.0 / na
        sigma_px = rayleigh_um / pixel_pitch_um

    if defocus_um != 0:
        sigma_px = (sigma_px**2 + (abs(defocus_um) * 0.25 / pixel_pitch_um) ** 2) ** 0.5

    if sigma_px < 0.05:
        return mask_array.copy()

    blurred = ndimage.gaussian_filter(mask_array.astype(np.float32), sigma=sigma_px)
    return np.clip(blurred, 0, 255).astype(np.uint8)


def process_window(
    mask_array: np.ndarray,
    pixel_pitch_um: float = 18.0,
    wavelength_nm: float = 405.0,
    na: float = 0.4,
    doses: list = None,
    defoci_um: list = None,
) -> dict:
    """
    Compute a simple process window: how much dose/defocus latitude exists.

    Returns a dict with aerial images at each dose/defocus combo and
    a rough depth-of-focus estimate.
    """
    if doses is None:
        doses = [0.7, 1.0, 1.3]
    if defoci_um is None:
        defoci_um = [-2.0, 0.0, 2.0]

    results = {}
    for dose in doses:
        for defocus in defoci_um:
            scaled = np.clip(mask_array.astype(np.float32) * dose, 0, 255).astype(np.uint8)
            aerial = simulate_aerial_image(scaled, pixel_pitch_um, wavelength_nm, na, defocus)
            results[(dose, defocus)] = aerial

    return results


# ── internal helpers ────────────────────────────────────────────────────────────

def _extend_line_ends(binary: np.ndarray, ext_px: int) -> np.ndarray:
    """Extend isolated line ends to compensate for end-shortening."""
    b = binary > 0.5
    result = binary.copy()

    # Count 4-connected neighbours
    neighbors = (
        np.roll(b, 1, axis=0).astype(int)
        + np.roll(b, -1, axis=0).astype(int)
        + np.roll(b, 1, axis=1).astype(int)
        + np.roll(b, -1, axis=1).astype(int)
    )

    # Line end = exposed pixel with exactly 1 neighbour
    ends = b & (neighbors == 1)

    for shift in range(1, ext_px + 1):
        for axis, direction in [(0, 1), (0, -1), (1, 1), (1, -1)]:
            shifted = np.roll(ends, shift * direction, axis=axis)
            result = np.maximum(result, shifted.astype(np.float32))

    return result


def _add_corner_serifs(binary: np.ndarray, serif_px: int) -> np.ndarray:
    """Add serif squares at convex corners (L-junctions)."""
    b = binary > 0.5
    result = binary.copy()

    padded = np.pad(b.astype(int), 1, constant_values=0)

    for dy, dx in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        # Convex corner: pixel is exposed, both orthogonal neighbours exposed,
        # but the diagonal neighbour is unexposed
        n = padded[1 + dy : padded.shape[0] - 1 + dy, 1 : padded.shape[1] - 1]
        e = padded[1 : padded.shape[0] - 1, 1 + dx : padded.shape[1] - 1 + dx]
        d = padded[1 + dy : padded.shape[0] - 1 + dy, 1 + dx : padded.shape[1] - 1 + dx]

        h, w = b.shape
        n = n[:h, :w]
        e = e[:h, :w]
        d = d[:h, :w]

        convex = b & (n.astype(bool)) & (e.astype(bool)) & (~d.astype(bool))

        for step in range(1, serif_px + 1):
            shifted = np.zeros_like(convex)
            ys = max(0, step * dy)
            ye = h + min(0, step * dy)
            xs = max(0, step * dx)
            xe = w + min(0, step * dx)
            src_ys = max(0, -step * dy)
            src_ye = h + min(0, -step * dy)
            src_xs = max(0, -step * dx)
            src_xe = w + min(0, -step * dx)
            shifted[ys:ye, xs:xe] = convex[src_ys:src_ye, src_xs:src_xe]
            result = np.maximum(result, shifted.astype(np.float32))

    return result
