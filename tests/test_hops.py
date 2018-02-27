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


def test_execution():
    """Functional test

    """
    config = {
        'hop': {
            'Mosaic': {
                'alpha acids': 5.
            }
        }
    }
    recipe_config = {
        'Average Gravity': 1.050,
        'Pitchable Volume': '5 gallons',
        'Hops': [
            {
                'name': 'Mosaic',
                'addition type': 'first wort hopping',
                'mass': '1 oz'
            },
            {
                'name': '60m',
                'boil_time': '1 hour',
                'mass': '1 oz',
                'alpha acids': 5.
            },
            {
                'name': 'Flameout',
                'addition type': 'flameout',
                'mass': '1 oz',
                'alpha acids': 5.
            },
            {
                'name': 'Dry Hop',
                'addition type': 'dry hop',
                'mass': '1 oz',
                'alpha acids': 5.
            }
            ]
    }

    _, res = hbc.hop_composition.execute(config, recipe_config)
    assert res['IBUs'] == pytest.approx(42.803352792814394)
