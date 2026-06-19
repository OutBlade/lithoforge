import pytest
from lithoforge.process import (
    spin_thickness, spin_rpm_for_thickness, exposure_time,
    development_recipe, etch_time, oxide_thickness,
    resolution_limit, electroless_ni_thickness, electroless_ni_time,
)


def test_spin_thickness_az1512():
    r = spin_thickness("AZ1512", 4000)
    assert 1000 < r["thickness_nm"] < 2500
    assert r["developer"] == "AZ400K_1_4"


def test_spin_thickness_increases_with_dilution():
    t1 = spin_thickness("AZ1512", 4000, dilution=1.0)["thickness_nm"]
    t2 = spin_thickness("AZ1512", 4000, dilution=0.5)["thickness_nm"]
    assert t2 < t1


def test_spin_thickness_decreases_with_rpm():
    t1 = spin_thickness("AZ1512", 2000)["thickness_nm"]
    t2 = spin_thickness("AZ1512", 6000)["thickness_nm"]
    assert t2 < t1


def test_rpm_for_thickness_roundtrip():
    target = 1000
    rpm = spin_rpm_for_thickness("AZ1512", target)
    t = spin_thickness("AZ1512", rpm)["thickness_nm"]
    assert abs(t - target) < 50


def test_exposure_time_increases_with_lower_intensity():
    e1 = exposure_time("AZ1512", 5.0)["exposure_time_s"]
    e2 = exposure_time("AZ1512", 2.0)["exposure_time_s"]
    assert e2 > e1


def test_exposure_time_unknown_resist():
    with pytest.raises(ValueError):
        exposure_time("UNKNOWN_RESIST", 3.0)


def test_development_recipe():
    d = development_recipe("AZ1512")
    assert d["developer_key"] == "AZ400K_1_4"
    assert d["temp_C"] == 21


def test_etch_time_bhf():
    r = etch_time("BHF_7_1", 100)
    assert r["etch_time_s"] > 0
    assert "HF" in r["hazard"]


def test_etch_time_unknown():
    with pytest.raises(ValueError):
        etch_time("MADE_UP_ETCHANT", 100)


def test_oxide_thickness_increases_with_time():
    t1 = oxide_thickness(1100, 30, wet=False)["thickness_nm"]
    t2 = oxide_thickness(1100, 60, wet=False)["thickness_nm"]
    assert t2 > t1


def test_oxide_wet_faster_than_dry():
    dry = oxide_thickness(1000, 30, wet=False)["thickness_nm"]
    wet = oxide_thickness(1000, 30, wet=True)["thickness_nm"]
    assert wet > dry


def test_resolution_contact_mode():
    r = resolution_limit(18.0, 405.0, na=0.0, magnification=1.0)
    assert r["limiting_factor"] == "pixel"
    assert r["resolution_um"] == pytest.approx(18.0, rel=0.1)


def test_resolution_with_20x():
    r = resolution_limit(18.0, 405.0, na=0.40, magnification=20.0)
    assert r["effective_pixel_um"] == pytest.approx(0.9, rel=0.1)


def test_electroless_ni_roundtrip():
    target = 150.0
    t = electroless_ni_time(target)
    result = electroless_ni_thickness(t)
    assert abs(result - target) < 5
