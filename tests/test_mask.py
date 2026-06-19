import numpy as np
import pytest
from lithoforge import Mask


def test_mask_creation():
    m = Mask(180, 90, pixel_pitch_um=18.0)
    assert m.width_px == 10
    assert m.height_px == 5
    assert m._data.shape == (5, 10)
    assert m._data.max() == 0


def test_rect_exposed():
    m = Mask(180, 180, pixel_pitch_um=18.0)
    m.rect(0, 0, 90, 90)
    assert m._data[0, 0] == 255
    assert m._data[9, 9] == 0


def test_rect_clear():
    m = Mask(180, 180, pixel_pitch_um=18.0, background="exposed")
    m.rect(0, 0, 90, 90, expose=False)
    assert m._data[0, 0] == 0
    assert m._data[9, 9] == 255


def test_invert():
    m = Mask(180, 180, pixel_pitch_um=18.0)
    m.rect(0, 0, 90, 90)
    before = m._data.copy()
    m.invert()
    assert np.all(m._data == (255 - before))


def test_circle():
    m = Mask(360, 360, pixel_pitch_um=18.0)
    m.circle(180, 180, 50)
    center_px = m._px(180)
    assert m._data[center_px, center_px] == 255


def test_merge_union():
    a = Mask(180, 180, pixel_pitch_um=18.0)
    a.rect(0, 0, 90, 90)
    b = Mask(180, 180, pixel_pitch_um=18.0)
    b.rect(90, 90, 90, 90)
    a.merge(b, "union")
    assert a._data[0, 0] == 255
    assert a._data[9, 9] == 255


def test_stats():
    m = Mask(180, 180, pixel_pitch_um=18.0)
    m.rect(0, 0, 180, 180)
    s = m.stats()
    assert s["exposed_pct"] == 100.0


def test_chaining():
    m = Mask(360, 360, pixel_pitch_um=18.0)
    result = m.rect(0, 0, 36, 36).circle(180, 180, 18)
    assert result is m


def test_save_load(tmp_path):
    m = Mask(180, 90, pixel_pitch_um=18.0)
    m.rect(0, 0, 90, 90)
    out = tmp_path / "test.png"
    m.save(str(out))
    assert out.exists()
    from PIL import Image
    img = Image.open(out)
    assert img.size == (10, 5)
