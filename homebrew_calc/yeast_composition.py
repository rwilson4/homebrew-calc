from __future__ import print_function
import json
import os
import math
from unit_parser import unit_parser


def abvcalc_main():
    """Entry point for abvcalc command line script.

    """
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('og', type=float, help='Original Gravity')
    parser.add_argument('fg', type=float, help='Final Gravity')

    args = parser.parse_args()
    abv = 100. * abv_calc(args.og, args.fg)
    att = 100.0 * attenuation(args.og, args.fg)
    print('{0:.02f}% ABV'.format(abv))
    print('{0:.0f}% Attenuation'.format(att))


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


def gravity_to_deg_plato(sg):
    """Convert gravity to degrees Plato.

    Parameters
    ----------
    sg : float
        Original gravity, like 1.053

    Returns
    -------
    deg_plato : float
        Degrees Plato, like 13.5

    """
    return 250. * (sg - 1.)


def deg_plato_to_gravity(deg_plato):
    """Convert degrees Plato to specific gravity.

    Parameters
    ----------
    deg_plato : float
        Degrees Plato, like 13.5

    Returns
    -------
    sg : float
        Specific gravity, like 1.053

    """
    return 1. + (deg_plato / 250.)


def main():
    """Entry point for yeast_composition command line script.

    """
    import argparse

    this_dir, this_filename = os.path.split(__file__)
    homebrew_config = os.path.join(this_dir, 'resources', 'homebrew.json')
    config = json.load(open(homebrew_config, 'r'))

    if 'units' in config['files']:
        config['units'] = os.path.join(this_dir, 'resources', config['files']['units'])

    parser = argparse.ArgumentParser()
    parser.add_argument('recipe', type=str, help='Recipe JSON')
    parser.add_argument('-o', '--output', type=str, help='Output file')

    args = parser.parse_args()
    recipe_config = json.load(open(args.recipe, 'r'))
    if args.output:
        config['Output'] = args.output

    execute(config, recipe_config)


def execute(config, recipe_config):
    """Calculations relevant to yeast characteristics.

    Note: required parameters are in either config or
    recipe_config. Where applicable, if a parameter is specified in
    both config and recipe_config, the latter overrides the former.

    Parameters
    ----------
     'Yeast' : array_like
        Array of one or more yeast packages. Each package is specified
        by a collection of key-value pairs. See below.
     'Original Gravity' : float
        Specific gravity of wort before pitching yeast. This can
        either be a top-level parameter, representing the predicted
        original gravity from malt_composition, or the actual,
        measured value as recorded, e.g., by brew_day. In the latter
        case, the parameter should be a sub-parameter of 'Brew
        Day'. If both are present, the 'Brew Day' parameter takes
        precedence.
     'Pitchable Volume' : str
        String representing the final volume of wort in which yeast
        will be pitched, e.g. '5 gallons'. Defaults to '5.25 gallons'
        if missing from both recipe_config and config.
     'Ale or Lager' : str
        One of 'Ale' or 'Lager'. If not specified, defaults to 'Ale'.

    Yeast Parameters
    ----------------
     'attenuation' : float
        Attenuation of yeast. If multiple yeast strains are used, we
        assume the overall attenuation is determined by the yeast with
        the highest advertised attenuation.


    Returns
    -------
     This function does not return anything. Instead, it appends the
     following parameters to recipe_config, and if requested, saves
     the latter to the specified file. It also prints the number of
     yeast cells needed, which translates into how big of a starter to
     use. Starter size calculations have not yet been implemented but
     are very imortant!

    Fields Appended to recipe_config
    --------------------------------
     'Final Gravity' : float
        Predicted final gravity of beer.
     'Alcohol by Volume' : float
        Predicted final ABV of beer.

    """
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

        if 'units' in config:
            up = unit_parser(config['units'])
        else:
            up = unit_parser()

        if 'Pitchable Volume' in recipe_config:
            pitchable_volume = up.convert(recipe_config['Pitchable Volume'], 'milliliters')
        elif 'Pitchable Volume' in config:
            pitchable_volume = up.convert(config['Pitchable Volume'], 'milliliters')
        else:
            pitchable_volume = up.convert('5.25 gallons', 'milliliters')
            print('Pitchable volume not specified, assuming 5.25 gallons')

        # Want 750k cells per milliliter per degree Plato for ales
        # 1.5 million for lagers
        if recipe_config.get('Ale or Lager', 'Ale') == 'Ale':
            cells_needed = 750000
        else:
            cells_needed = 1500000

        degP = gravity_to_deg_plato(og)
        cell_count = cells_needed * pitchable_volume * degP
        print('Cells needed (billions): {0:.0f}'.format(cell_count / 1e9))

    if 'Output' in config:
        with open(config['Output'], 'w') as outfile:
            json.dump(recipe_config, outfile, indent=2, sort_keys=True)


if __name__ == '__main__':
    main()
