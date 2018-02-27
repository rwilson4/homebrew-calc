from __future__ import print_function
import json
import sys
import os
import math
from unit_parser import unit_parser


FIRST_WORT_HOPPING = 'first wort hopping'
FLAMEOUT = 'flameout'


def bigness_factor(wort_gravity):
    """Wort 'bigness factor' for hop utilization.

    Parameters
    ----------
     wort_gravity : float
        Average specific gravity of wort during boil.

    Returns
    -------
     bigness_factor : float
        Multiplicative factor for hop utilization based on wort
        gravity.

    """
    return 1.65 * (0.000125 ** (wort_gravity - 1))


def boil_time_factor(boil_time_minutes):
    """Boil time factor for hop utilization.

    Parameters
    ----------
     boil_time_minutes : float
        Amount of time hops spend in the boil, in minutes.

    Returns
    -------
     boil_time_factor : float
        Multiplicative factor for hop utilization based on boil time.

    """
    return (1 - math.exp(-0.04 * boil_time_minutes)) / 4.15


def hop_utilization(wort_gravity, boil_time_minutes, addition_type=None):
    """Hop utilization.

    Parameters
    ----------
     wort_gravity : float
        Average specific gravity of wort during boil.
     boil_time_minutes : float
        Amount of time hops spend in the boil, in minutes.
     addition_type : string or None
        Type of hop addition. Currently supported options include
        'first wort hopping', 'flameout', or regular, timed hop
        additions. Any addition type other than 'first wort hopping'
        and 'flameout' will be interpreted as a regular, timed
        addition, e.g. a 20-minute addition.

    Returns
    -------
     utilization : float
        Hop utilization.

    """
    if addition_type is not None and addition_type == FLAMEOUT:
        return 0.13

    bf = bigness_factor(wort_gravity)
    btf = boil_time_factor(boil_time_minutes)
    if addition_type is not None and addition_type == FIRST_WORT_HOPPING:
        return 1.1 * bf * btf
    else:
        return bf * btf


def ibu_contribution(alpha_acids, mass_oz, boil_vol_gal, utilization,
                     hop_type='pellets'):
    """IBU Contribution

    Parameters
    ----------
     alpha_acids : float
        Alpha acid content of hop, e.g. 0.045 for a 4.5% AA hop.
     mass_oz : float
        Weight of hops, in ounces.
     boil_vol_gal : float
        Average volume of boil, in gallons.
     utilization : float
        Hop utilization.
     hop_type : string
        Either 'pellets' or 'whole' (defaults to 'pellets').

    Returns
    -------
     ibus : float
        IBU contribution of this addition.

    """

    ibus = utilization * alpha_acids * mass_oz * 7490 / boil_vol_gal
    if hop_type == 'pellets':
        return ibus / 0.9
    else:
        return ibus


def main():
    """Entry point for hop_composition command line script.

    """
    import argparse

    this_dir, this_filename = os.path.split(__file__)
    homebrew_config = os.path.join(this_dir, 'resources', 'homebrew.json')
    config = json.load(open(homebrew_config, 'r'))

    hop_config_file = os.path.join(this_dir, 'resources', config['files']['hops'])
    hop_config = json.load(open(hop_config_file, 'r'))
    config['hop'] = hop_config

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
    """Calculations relevent to hop characteristics.

    Note: required parameters are in either config or
    recipe_config. Where applicable, if a parameter is specified in
    both config and recipe_config, the latter overrides the former.

    Parameters
    ----------
     'Average Gravity' : float
        Average specific gravity of the boil, e.g. from
        water_composition.
     'Pitchable Volume' : string
        String representing the final volume of wort in which yeast
        will be pitched, e.g. '5 gallons'. Defaults to '5.25 gallons'
        if missing from both recipe_config and config.
     'Hops' : array_like
        Array of hop additions. Each addition is specified by a
        collection of key-value pairs as described below.

    Hop Parameters
    --------------
     'addition type' : string
        Specifies what type of hop addition it is. One of 'first wort
        hopping', 'flameout', 'timed', or 'dry hop'
     'boil_time' : string
        String specifying how long the hop is boiled. Only required
        for 'timed' addition type.
     'mass' : string
        String specifying the mass of the addition. Ounces and pounds
        are considered units of mass for these purposes.
     'alpha acids' : float
        Alpha acid content of hop. For convenience/confusion, this is
        specified as, for example, '4.5' to represent 4.5% instead of
        0.045. This is because alpha acide content is typically
        between 1% and 15%, and I just think it's easier to
        read. Baseline alpha acids are specified in config, but actual
        content can vary from year to year and harvest to harvest, so
        it is best to include the actual value with every recipe.

    Returns
    -------

     This function does not return anything. Instead it prints the
     contribution of each hop addition to the IBUs of the final
     product, then the total IBUs. The latter are appended to
     recipe_config, and if requested, saved to file.

    Fields Appended to recipe_config
    --------------------------------
    'IBUs' : float
        Estimated bitterness level of beer.

    """

    if 'units' in config:
        up = unit_parser(config['units'])
    else:
        up = unit_parser()

    if 'Average Gravity' in recipe_config:
        wort_gravity = recipe_config['Average Gravity']
    else:
        msg = 'Average wort gravity not specified.'
        msg += ' Try running water_composition first.'
        raise ValueError(msg)

    if 'Pitchable Volume' in recipe_config:
        water_volume = up.convert(recipe_config['Pitchable Volume'], 'gallons')
    elif 'Pitchable Volume' in config:
        water_volume = up.convert(config['Pitchable Volume'], 'gallons')
    else:
        water_volume = 5.25
        msg = 'Pitchable volume not specified, assuming {0:.02f} gallons'
        print(msg.format(water_volume))

    total_ibus = 0.
    for hop in recipe_config['Hops']:
        boil_time = 0.
        if 'boil_time' in hop:
            boil_time = up.convert(hop['boil_time'], 'minutes')
        elif 'addition type' in hop and hop['addition type'] == FIRST_WORT_HOPPING:
            boil_time = 20
        elif 'addition type' not in hop:
            msg = 'Boil time not specified for {0:s}; exiting.'
            raise ValueError(msg.format(hop.get('name', '')))

        utilization = hop_utilization(wort_gravity, boil_time,
                                      hop.get('addition type', None))

        if 'mass' in hop:
            mass = up.convert(hop['mass'], 'ounces')
        else:
            msg = 'Mass not specified for {0:s}; exiting.'
            raise ValueError(msg.format(hop.get('name', '')))

        if 'alpha acids' in hop:
            alpha_acids = hop['alpha acids'] / 100.
        elif ('name' in hop and hop['name'] in config['hop']
              and 'alpha acids' in config['hop'][hop['name']]):
            alpha_acids = config['hop'][hop['name']]['alpha acids'] / 100.
        elif utilization > 0:
            msg = 'Alpha Acids not specified for {0:s}; exiting.'
            raise ValueError(msg.format(hop.get('name', '')))

        ibus = ibu_contribution(alpha_acids, mass, water_volume, utilization,
                                hop.get('type', 'pellets'))

        if 'boil_time' in hop:
            msg = '{time:.0f}-minute addition: {ibu:0.1f} IBUs'
            print(msg.format(time=boil_time, ibu=ibus))
        elif 'addition type' in hop and hop['addition type'] == FIRST_WORT_HOPPING:
            print('First-wort hopping addition: {ibu:0.1f} IBUs'.format(ibu=ibus))
        elif 'addition type' in hop and hop['addition type'] == FLAMEOUT:
            print('Flameout hopping addition: {ibu:0.1f} IBUs'.format(ibu=ibus))

        total_ibus += ibus

    recipe_config['IBUs'] = total_ibus
    print('Total IBUs: {0:.1f}'.format(recipe_config['IBUs']))

    if 'Output' in config:
        with open(config['Output'], 'w') as outfile:
            json.dump(recipe_config, outfile, indent=2, sort_keys=True)

    return config, recipe_config


if __name__ == '__main__':
    main()
