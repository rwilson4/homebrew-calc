#!/usr/bin/python

import json
import sys
import math
from units import units


def execute(config, recipe_config):
    up = unit_parser()

    if 'Average Gravity' in recipe_config:
        wort_gravity = recipe_config['Average Gravity']
    else:
        print 'Average wort gravity not specified. Try running water_composition first.'
        sys.exit()
    
    if 'Pitchable Volume' in recipe_config:
        water_volume = up.convert(recipe_config['Pitchable Volume'], 'gallons')
    elif 'Pitchable Volume' in config:
        water_volume = up.convert(config['Pitchable Volume'], 'gallons')
    else:
        water_volume = 5.25
        print 'Pitchable volume not specified, assuming {0:.02f} gallons'.format(water_volume)
        
    bigness_factor = 1.65 * (0.000125 ** (wort_gravity - 1))

    ibus = 0.
    for hop in recipe_config['Hops']:
        boil_time = 0.
        if 'boil_time' in hop:
            boil_time = up.convert(hop['boil_time'], 'minutes')
        elif 'addition type' in hop and hop['addition type'] == 'fwh':
            boil_time = 20
        elif 'addition type' not in hop:
            print 'Boil time not specified for {0:s}; exiting.'.format(hop.get('name', ''))
            sys.exit()
            
        boil_time_factor = (1 - math.exp(-0.04 * boil_time)) / 4.15
        utilization = boil_time_factor * bigness_factor
        if 'addition type' in hop and hop['addition type'] == 'fwh':
            utilization *= 1.1
        elif 'addition type' in hop and hop['addition type'] == 'flameout':
            utilization = 0.13

        if 'mass' in hop:
            mass = up.convert(hop['mass'], 'ounces')
        else:
            print 'Mass not specified for {0:s}; exiting.'.format(hop.get('name', ''))
            sys.exit()

        if 'alpha acids' in hop:
            alpha_acids = hop['alpha acids'] / 100.
        elif 'name' in hop and hop['name'] in config['hop'] and 'alpha acids' in config['hop'][hop['name']]:
            alpha_acids = config['hop'][hop['name']]['alpha acids'] / 100.
        elif utilization > 0:
            print 'Alpha Acids not specified for {0:s}; exiting.'.format(hop.get('name', ''))
            sys.exit()
            
        alpha_acids = alpha_acids * mass * 7490 / water_volume
        ibu_contribution = utilization * alpha_acids
        if 'type' in hop and hop['type'] == 'pellets':
            ibu_contribution /= 0.9

        if 'boil_time' in hop:
            boil_time = up.convert(hop['boil_time'], 'minutes')
            print '{time}-minute addition: {ibu:0.1f} IBUs'.format(time=boil_time, ibu=ibu_contribution)
        elif 'addition type' in hop and hop['addition type'] == 'fwh':
            print 'First-wort hopping addition: {ibu:0.1f} IBUs'.format(ibu=ibu_contribution)
        elif 'addition type' in hop and hop['addition type'] == 'flameout':
            print 'Flameout hopping addition: {ibu:0.1f} IBUs'.format(ibu=ibu_contribution)

        ibus += ibu_contribution

    recipe_config['IBUs'] = ibus
    print 'IBUs: {0:.1f}'.format(recipe_config['IBUs'])

    if 'Output' in config:
        with open(config['Output'], 'w') as outfile:
            json.dump(recipe_config, outfile, indent=2, sort_keys=True)


if __name__ == '__main__':
    import argparse
    
    config = json.load(open('/Users/bobwilson/beer/bin/homebrew.json', 'r'))
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

