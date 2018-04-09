import pytest
import sys
import os
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

from .context import homebrew_calc as hbc


def test_ph_temp_same_temp():
    pH = 5.7
    original_temperature = 77
    desired_temperature = 77
    expected = 5.7
    res = hbc.convert_pH_temp(pH, original_temperature, desired_temperature)
    assert res == expected


def test_ph_temp_same_temp():
    pH = 5.7
    original_temperature = 77
    desired_temperature = 68
    expected = 5.727
    res = hbc.convert_pH_temp(pH, original_temperature, desired_temperature)
    assert res == expected


def test_ph_temp_clu():
    pH = '5.7'
    original_temperature = '77'
    desired_temperature = '68'
    expected = 5.727

    testargs = ['convert_ph_temp', pH, original_temperature, desired_temperature]
    with patch.object(sys, 'argv', testargs):
        res = hbc.water_composition.convert_pH_temp_main()
        assert res == expected


def test_functional():
    this_dir, this_filename = os.path.split(__file__)
    beer_recipe = os.path.join(this_dir, 'resources', 'weddingBrownWater.json')
    output_recipe = os.path.join(this_dir, 'resources', 'weddingBrownWater_1.json')
    testargs = ['water_composition', beer_recipe, '-o', output_recipe]
    with patch.object(sys, 'argv', testargs):
        hbc.water_composition.main()
        assert os.path.isfile(output_recipe)
