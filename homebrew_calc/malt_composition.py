from __future__ import print_function
import json
import sys
import os
from unit_parser import unit_parser


def gravity_points_to_specific_gravity(gravity_points, vol_gal):
    """Convert gravity points to specific gravity

    Parameters
    ----------
     gravity_points : float
        Gravity points.
     vol_gal : float
        Wort volume, in gallons.

    Returns
    -------
     sg : float
        Specific gravity.

    """
    return 1. + 0.001 * gravity_points / vol_gal


def specific_gravity_to_gravity_points(sg, vol_gal):
    """Convert specific gravity to gravity points

    Parameters
    ----------
     sg : float
        Specific gravity.
     vol_gal : float
        Wort volume, in gallons.

    Returns
    -------
     gravity_points : float
        Gravity points.

    """
    return 1000. * (sg - 1.) * vol_gal


def wort_srm(mcu, vol_gal):
    """Convert Malt Color Units to SRM.

    Parameters
    ----------
     mcu : float
        Malt color units
     vol_gal : float
        Wort volume, in gallons.

    Returns
    -------
     srm : float
        SRM.

    """
    return 1.49 * (mcu / vol_gal) ** 0.69


def main():
    """Entry point for malt_composition script.

    """
    import argparse

    this_dir, this_filename = os.path.split(__file__)
    homebrew_config = os.path.join(this_dir, 'resources', 'homebrew.json')
    config = json.load(open(homebrew_config, 'r'))

    malt_config_file = os.path.join(this_dir, 'resources', config['files']['malt'])
    malt_config = json.load(open(malt_config_file, 'r'))
    config['malt'] = malt_config

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
    """Calculations relevant to malt characteristics.

    Note: required parameters are in either config or
    recipe_config. Where applicable, if a parameter is specified in
    both config and recipe_config, the latter overrides the former.

    Parameters
    ----------
     'Brewhouse Efficiency' : float
        Efficiency of sugar extraction process. Defaults to 70% if
        missing from both recipe_config and config.
     'Pitchable Volume' : str
        String representing the final volume of wort in which yeast
        will be pitched, e.g. '5 gallons'. Defaults to '5.25 gallons'
        if missing from both recipe_config and config.
     'Malt' : array_like
        Array of grist components (not necessarily malted). Each
        component is specified by a collection of key-value pairs
        describing its mass, sugar content, and color. See below.
     'Water to Grist Ratio' : string
        String representing the ratio of mash water to grist mass,
        with dimensions of volume per mass. Something in the range of
        1 to 1.5 quarts per pound is typical, with 1.2 quarts per
        pound used as the default.


    Malt Parameters
    ---------------
     'mass' : string
        String representing the mass of the grain, e.g. '5
        pounds'. Note here that 'pound' is interpreted as 'pounds of
        mass' not 'pounds of force'. Ounces are also interpreted as
        units of mass.
     'ppg' : float
        Gravity points per pound per gallon. For example, if ppg = 30,
        assuming 100% brewhouse efficiency, adding one pound of grain
        to one gallon of water would yield a specific gravity of 1.030.
     'extract potential' : float
        Gravity points, as expressed relative to pure sucrose. Sucrose
        has 46 ppg, so an extract potential of 0.8 has 0.8 * 46 = 37
        ppg. If both ppg and extract potential are specified for a
        malt, ppg is used.

        If neither are specified, 0 ppg is used. This is occasionally
        helpful when using adjuncts like rice hulls that do not
        contribute to the wort gravity, but is also slightly dangerous
        if a typo is made in the recipe formulation. It might be
        better to throw an error in this case.
     'degrees lovibond' : float
        Degrees Lovibond of malt. This translates into the impact of
        the malt on the color of the beer and is often specifically
        listed as part of the name of the malt, like 'Crystal 60L'.

    Returns
    -------
     This function does not return anything. Instead it prints the
     below parameters to STDOUT, and, if requested, appends them to
     the recipe_config before printing to file.

    Fields Appended to recipe_config
    --------------------------------
     'Mash Water Volume' : string
        Amount of mash water needed, in gallons.
     'Original Gravity' : float
        Predicted specific gravity of wort before pitching yeast.
     'SRM' : float
        Predicted SRM (color) of wort.

    """
    if 'units' in config:
        up = unit_parser(config['units'])
    else:
        up = unit_parser()

    if 'Brewhouse Efficiency' in recipe_config:
        brewhouse_efficiency = recipe_config['Brewhouse Efficiency']
    elif 'Brewhouse Efficiency' in config:
        brewhouse_efficiency = config['Brewhouse Efficiency']
    else:
        brewhouse_efficiency = 0.7
        msg = 'Brewhouse efficiency not specified; assuming {0:.0f}%'
        print(msg.format(100. * brewhouse_efficiency))

    if 'Pitchable Volume' in recipe_config:
        pitchable_volume = up.convert(recipe_config['Pitchable Volume'], 'gallons')
    elif 'Pitchable Volume' in config:
        pitchable_volume = up.convert(config['Pitchable Volume'], 'gallons')
    else:
        pitchable_volume = 5.25
        msg = 'Pitchable volume not specified, assuming {0:.02f} gallons'
        print(msg.format(pitchable_volume))

    if 'Sucrose' in config['malt'] and 'ppg' in config['malt']['Sucrose']:
        sucrose_ppg = config['malt']['Sucrose']['ppg']
    else:
        sucrose_ppg = 46

    total_mass = 0.
    gravity_points = 0.
    mcu = 0.

    for malt in recipe_config['Malt']:
        if 'mass' in malt:
            mass = up.convert(malt['mass'], 'pounds')
            total_mass += mass
        else:
            mass = 0.

        if 'ppg' in malt:
            ppg = malt['ppg']
        elif 'extract potential' in malt:
            ppg = malt['extract potential'] * sucrose_ppg
        elif malt['name'] in config['malt'] and 'ppg' in config['malt'][malt['name']]:
            ppg = config['malt'][malt['name']]['ppg']
        elif malt['name'] in config['malt'] and 'extract potential' in config['malt'][malt['name']]:
            ppg = config['malt'][malt['name']]['extract potential'] * sucrose_ppg
        else:
            ppg = 0.

        gravity_points += brewhouse_efficiency * ppg * mass

        if 'degrees lovibond' in malt:
            degL = malt['degrees lovibond']
        elif malt['name'] in config['malt'] and 'degrees lovibond' in config['malt'][malt['name']]:
            degL = config['malt'][malt['name']]['degrees lovibond']
        else:
            degL = 0.

        mcu += degL * mass

    if 'Water to Grist Ratio' in recipe_config:
        wtgr = up.convert(recipe_config['Water to Grist Ratio'], 'gallons_per_pound')
    elif 'Water to Grist Ratio' in config:
        wtgr = up.convert(config['Water to Grist Ratio'], 'gallons_per_pound')
    else:
        wtgr = up.convert(1.2, 'quarts_per_pound', 'gallons_per_pound')
        msg = 'Water to Grist Ratio not specified,'
        msg += ' assuming 1.2 quarts_per_pound'
        print(msg)

    water_volume = '{0:.6f} gallons'.format(wtgr * total_mass)
    if (('Preferred Units' in config
         and 'volume' in config['Preferred Units']
         and config['Preferred Units'] != 'gallons')):
        vol_units = config['Preferred Units']['volume']
        water_volume = up.convert(water_volume, vol_units)
        water_volume = '{0:.6f} {1:s}'.format(water_volume, vol_units)

    recipe_config['Mash Water Volume'] = water_volume
    og = gravity_points_to_specific_gravity(gravity_points, pitchable_volume)
    recipe_config['Original Gravity'] = og
    recipe_config['SRM'] = wort_srm(mcu, pitchable_volume)

    # print('Mash Water Volume: {0:s}'.format(recipe_config['Mash Water Volume']))
    print('Original Gravity: {0:.03f}'.format(og))
    print('SRM: {0:.0f}'.format(recipe_config['SRM']))

    if 'Output' in config:
        with open(config['Output'], 'w') as outfile:
            json.dump(recipe_config, outfile, indent=2, sort_keys=True)

    return config, recipe_config


if __name__ == '__main__':
    main()
