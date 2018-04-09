import pytest
import sys
import os
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

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
        'Preferred Units': {
            'volume': 'liters'
        },
        'malt': {
            'Sucrose': {
                'ppg': 46,
                'degrees lovibond': 0.
            },
            'Munich': {
                'extract potential': 0.8
            }
        }
    }

    recipe_config = {
        'Brewhouse Efficiency': 0.7,
        'Pitchable Volume': '5 gallons',
        'Water to Grist Ratio': '1.2 quarts_per_pound',
        'Malt': [
            {
                'mass': '5 pounds',
                'ppg': 30,
                'degrees lovibond': 5.
            },
            {
                'mass': '5 pounds',
                'extract potential': 0.8,
                'degrees lovibond': 5.
            },
            {
                'mass': '1 pound',
                'name': 'Sucrose'
            },
            {
                'mass': '1 pound',
                'name': 'Munich'
            }
        ]
    }

    _, res = hbc.malt_composition.execute(config, recipe_config)
    assert res['Original Gravity'] == pytest.approx(1.058352)
    assert res['SRM'] == pytest.approx(7.297704408589848)

    
def test_malt_clu():
    this_dir, this_filename = os.path.split(__file__)
    beer_recipe = os.path.join(this_dir, 'resources', 'weddingBrown.json')
    output_recipe = os.path.join(this_dir, 'resources', 'weddingBrown_1.json')
    testargs = ['malt_composition', beer_recipe, '-o', output_recipe]
    with patch.object(sys, 'argv', testargs):
        hbc.malt_composition.main()
        assert os.path.isfile(output_recipe)
