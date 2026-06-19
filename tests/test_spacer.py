import pytest
from lithoforge.spacer import (
    calculate_spacer, spacer_for_target, multi_patterning, spacer_process_summary,
)


def test_spacer_output_pitch_halved():
    r = calculate_spacer(2000, 4000, 200)
    assert r.output_pitch_nm == pytest.approx(2000, rel=0.01)


def test_spacer_width_equals_film_minus_loss():
    film = 200
    loss = 10
    r = calculate_spacer(2000, 4000, film, lateral_etch_loss_nm=loss)
    assert r.spacer_width_nm == pytest.approx(film - loss, rel=0.01)


def test_spacer_width_clamped_at_zero():
    r = calculate_spacer(2000, 4000, 5, lateral_etch_loss_nm=20)
    assert r.spacer_width_nm == 0.0


def test_spacer_warns_on_merge():
    r = calculate_spacer(2000, 4000, 2000)
    assert any("merge" in w.lower() for w in r.warnings)


def test_spacer_warns_thin():
    r = calculate_spacer(2000, 4000, 15)
    assert any("thin" in w.lower() for w in r.warnings)


def test_spacer_for_target():
    film = spacer_for_target(100, 4000, lateral_etch_loss_nm=10)
    assert film == pytest.approx(110, rel=0.01)


def test_multi_patterning_single():
    r = multi_patterning(900, 900)
    assert r["passes"] == 1
    assert r["approach"] == "Single patterning"


def test_multi_patterning_sadp():
    r = multi_patterning(100, 900)
    assert r["passes"] > 1
    assert r["achievable_nm"] <= 100


def test_multi_patterning_with_film_limit():
    r = multi_patterning(50, 900, spacer_film_nm=80)
    assert r["achievable_nm"] <= 80


def test_process_summary_contains_steps():
    summary = spacer_process_summary(2000, 4000, 110)
    assert "STEP 1" in summary
    assert "STEP 4" in summary
    assert "nm" in summary
