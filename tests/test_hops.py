import pytest
from .context import homebrew_calc as hbc


def test_bigness_factor():
    """Tests wort bigness factor.

    """
    sg = 1.055
    bf = 1.0065004999
    assert hbc.bigness_factor(sg) == pytest.approx(bf)


def test_boil_time_factor():
    """Tests wort boil time factor.

    """
    bt = 60.
    btf = 0.2191041076
    assert hbc.boil_time_factor(bt) == pytest.approx(btf)


def test_hop_utilization_timed():
    """Tests hop utilization

    """
    sg = 1.055
    bt = 60.
    utilization = 0.2205283938
    assert hbc.hop_utilization(sg, bt) == pytest.approx(utilization)


def test_hop_utilization_flameout():
    """Tests hop utilization

    """
    sg = 1.055
    bt = 60.
    utilization = 10.
    assert hbc.hop_utilization(sg, bt, 'flameout') == pytest.approx(0.13)


def test_hop_utilization_fwh():
    """Tests hop utilization

    """
    sg = 1.055
    bt = 60.
    utilization = 1.1 * 0.2205283938
    assert hbc.hop_utilization(sg, bt, 'first wort hopping') == pytest.approx(utilization)


def test_ibu_contribution():
    """Tests hop IBU contribution.

    """
    aa = 0.045
    m = 2
    bv = 5
    ut = 0.2205283938
    ibu_whole = 29.7316380521
    ibu_pellets = 29.7316380521 / 0.9
    assert hbc.ibu_contribution(aa, m, bv, ut, 'whole') == pytest.approx(ibu_whole)
    assert hbc.ibu_contribution(aa, m, bv, ut, 'pellets') == pytest.approx(ibu_pellets)
