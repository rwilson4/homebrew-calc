import pytest
from .context import homebrew_calc as hbc


def test_gravity_points_to_specific_gravity():
    """Tests converting from gravity points to specific gravity.

    """
    gp = 100.
    vol = 5
    sg = 1.020
    assert hbc.gravity_points_to_specific_gravity(gp, vol) == pytest.approx(sg)


def test_specific_gravity_to_gravity_points():
    """Tests converting from specific gravity to gravity points.

    """
    gp = 100.
    vol = 5
    sg = 1.020
    assert hbc.specific_gravity_to_gravity_points(sg, vol) == pytest.approx(gp)


def test_srm():
    """Tests SRM calculation

    """
    mcu = 100.
    vol = 5
    srm = 11.7732662449
    assert hbc.wort_srm(mcu, vol) == pytest.approx(srm)
