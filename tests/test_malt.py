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


def test_execute():
    """Functional test

    """
    config = {
        'malt': {
            'Sucrose': {
                'ppg': 46
            }
        }
    }

    recipe_config = {
        'Brewhouse Efficiency': 0.7,
        'Pitchable Volume': '5 gallons',
        'Water to Grist Ratio': '1.2 quarts_per_pound',
        'Malt': [
            {
                'mass': '10 pounds',
                'ppg': 30,
                'degrees lovibond': 5.
            }
        ]
    }

    _, res = hbc.malt_composition.execute(config, recipe_config)
    assert res['Original Gravity'] == pytest.approx(1.042)
    assert res['SRM'] == pytest.approx(7.297704408589848)
