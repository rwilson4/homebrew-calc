import pytest
from .context import homebrew_calc as hbc


def test_abv_calc():
    """Tests calculating ABV.

    """
    og = 1.050
    fg = 1.010
    abv = 0.0525
    abv_not_simple = 0.05339411100495098
    assert hbc.abv_calc(og, fg) == pytest.approx(abv)
    assert hbc.abv_calc(og, fg, simple=False) == pytest.approx(abv_not_simple)


def test_attenuation():
    """Tests calculating attenuation.

    """
    og = 1.050
    fg = 1.010
    atten = 0.8
    assert hbc.attenuation(og, fg) == atten


def test_final_gravity():
    """Tests calculating final gravity.

    """
    og = 1.050
    attenuation = 0.8
    fg = 1.010
    assert hbc.predict_final_gravity(og, attenuation) == fg


def test_gravity_to_deg_plato():
    """Tests converting from gravity to degrees Plato.

    """
    sg = 1.050
    deg_plato = 12.5
    assert hbc.gravity_to_deg_plato(sg) == pytest.approx(deg_plato)


def test_deg_plato_to_gravity():
    """Tests converting from gravity to degrees Plato.

    """
    sg = 1.050
    deg_plato = 12.5
    assert hbc.deg_plato_to_gravity(deg_plato) == sg
