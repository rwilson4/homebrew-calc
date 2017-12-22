from __future__ import print_function
import json
import os
import math
from unit_parser import unit_parser


def abv_calc(og, fg, simple=None):
    """Computes ABV from OG and FG.

    Parameters
    ----------
    og : float
        Original gravity, like 1.053
    fg : float
        Final gravity, like 1.004
    simple : bool or None, defaults to None.
        Flag specifying whether to use the simple (linear) equation or
        the more complicated nonlinear equation. The simple equation
        is generally appropriate provided the difference in original
        and final gravities is less than 0.05. If None, this function
        will decide for itself which formula to use.

    Returns
    -------
    abv : float
        Alcohol by volume, like 0.064.

    """
    if (simple is None and og < fg + 0.05) or simple:
        return (og - fg) * 1.3125
    else:
        return (0.7608 * (og - fg) / (1.775 - og)) * (fg / 0.794)


def attenuation(og, fg):
    """Attenuation

    Parameters
    ----------
    og : float
        Original gravity, like 1.053
    fg : float
        Final gravity, like 1.004

    Returns
    -------
    attenuation : float
       Attenuation, like 0.92.

    """
    return (og - fg) / (og - 1.0)


def predict_final_gravity(og, attenuation):
    """Final gravity

    Parameters
    ----------
    og : float
        Original gravity, like 1.053
    attenuation : float
       Attenuation, like 0.92.

    Returns
    -------
    fg : float
        Final gravity, like 1.004

    """
    return og - attenuation * (og - 1.)


def gravity_to_deg_plato(og):
    """Convert gravity to degrees Plato.

    Parameters
    ----------
    og : float
        Original gravity, like 1.053

    Returns
    -------
    deg_plato : float
        Degrees Plato, like 13.5

    """
    return 250. * (og - 1.)


def execute(config, recipe_config):
    # Viability
    # Starter calculation

    attenuation = 0.
    for yeast in recipe_config['Yeast']:
        if 'attenuation' in yeast and yeast['attenuation'] > attenuation:
            attenuation = yeast['attenuation']

    og = None
    if 'Brew Day' in recipe_config and 'Original Gravity' in recipe_config['Brew Day']:
        og = recipe_config['Brew Day']['Original Gravity']
    elif 'Original Gravity' in recipe_config:
        og = recipe_config['Original Gravity']

    if og is not None:
        fg = predict_final_gravity(og, attenuation)
        recipe_config['Final Gravity'] = fg
        abv = abv_calc(og, fg)
        recipe_config['Alcohol by Volume'] = abv
        print('Final Gravity: {0:.03f}'.format(fg))
        print('Alcohol by Volume: {0:.01f}%'.format(100. * abv))

        if 'Pitchable Volume' in recipe_config:
            # Want 750k cells per milliliter per degree Plato for ales
            # 1.5 million for lagers
            if recipe_config.get('Ale or Lager', 'Ale') == 'Ale':
                cells_needed = 750000
            else:
                cells_needed = 1500000
            
            up = unit_parser()
            pv = up.convert(recipe_config['Pitchable Volume'], 'milli_liters')
            degP = gravity_to_deg_plato(og)
            cell_count = cells_needed * pv * degP
            print('Cells needed (billions): {0:.0f}'.format(cell_count / 1e9))

    if 'Output' in config:
        with open(config['Output'], 'w') as outfile:
            json.dump(recipe_config, outfile, indent=2, sort_keys=True)


if __name__ == '__main__':
    import argparse

    this_dir, this_filename = os.path.split(__file__)
    homebrew_config = os.join(this_dir, 'bin', 'homebrew.json')

    config = json.load(open(homebrew_config, 'r'))
    hop_config = json.load(open(config['files']['hops'], 'r'))
    config['hop'] = hop_config

    parser = argparse.ArgumentParser()
    parser.add_argument('recipe', type=str, help='Recipe JSON')
    parser.add_argument('-o', '--output', type=str, help='Output file')

    args = parser.parse_args()
    recipe_config = json.load(open(args.recipe, 'r'))
    if args.output:
        config['Output'] = args.output

    execute(config, recipe_config)
