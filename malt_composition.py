#!/usr/bin/python

import json
import sys
from unit_parser import unit_parser

def execute(config, recipe_config):
    up = unit_parser()
    
    if 'Brewhouse Efficiency' in recipe_config:
        brewhouse_efficiency = recipe_config['Brewhouse Efficiency']
    elif 'Brewhouse Efficiency' in config:
        brewhouse_efficiency = config['Brewhouse Efficiency']
    else:
        brewhouse_efficiency = 0.7
        print 'Brewhouse efficiency not specified; assuming {0:.0f}%'.format(100. * brewhouse_efficiency)
    
    if 'Pitchable Volume' in recipe_config:
        pitchable_volume = up.convert(recipe_config['Pitchable Volume'], 'gallons')
    elif 'Pitchable Volume' in config:
        pitchable_volume = up.convert(config['Pitchable Volume'], 'gallons')
    else:
        pitchable_volume = 5.25
        print 'Pitchable volume not specified, assuming {0:.02f} gallons'.format(pitchable_volume)

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
        wtgr = 0.3
        print 'Water to Grist Ratio not specified, assuming 1.2 quarts_per_pound'
    
    water_volume = wtgr * total_mass
    recipe_config['Mash Water Volume'] = '{0:.6f} gallons'.format(water_volume)

    recipe_config['Original Gravity'] = 1 + 0.001 * (gravity_points / pitchable_volume)
    recipe_config['SRM'] = 1.49 * (mcu / pitchable_volume) ** 0.69

    print 'Mash Water Volume: {0:s}'.format(recipe_config['Mash Water Volume'])
    print 'Original Gravity: {0:.03f}'.format(recipe_config['Original Gravity'])
    print 'SRM: {0:.0f}'.format(recipe_config['SRM'])

    if 'Output' in config:
        with open(config['Output'], 'w') as outfile:
            json.dump(recipe_config, outfile, indent=2, sort_keys=True)

if __name__ == '__main__':
    import argparse
    config = json.load(open('/Users/bobwilson/beer/bin/homebrew.json', 'r'))
    malt_config = json.load(open(config['files']['malt'], 'r'))
    config['malt'] = malt_config

    parser = argparse.ArgumentParser()
    parser.add_argument('recipe', type=str, help='Recipe JSON')
    parser.add_argument('-o', '--output', type=str, help='Output file')

    args = parser.parse_args()
    recipe_config = json.load(open(args.recipe, 'r'))
    if args.output:
        config['Output'] = args.output

    execute(config, recipe_config)

