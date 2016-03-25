#!/usr/bin/python

import json
import argparse
import sys
from units import units

def execute(config, recipe_config):
    if 'Mash' not in recipe_config:
        print 'Mash information not provided'
        sys.exit()
        
    if 'type' in recipe_config['Mash'] and recipe_config['Mash']['type'] == 'Infusion':
        config, recipe_config = infusion_mash(config, recipe_config)
    else:
        print 'Not supported.'
        sys.exit()

    if 'Output' in config:
        with open(config['Output'], 'w') as outfile:
            json.dump(recipe_config, outfile, indent=2, sort_keys=True)


def infusion_mash(config, recipe_config):

    if 'temperature' in recipe_config['Mash']:
        mash_temp = fahrenheit_to_celsius(recipe_config['Mash']['temperature'])
    else:
        print 'Mash temperature not specified.'
        sys.exit()

    if 'duration' in recipe_config['Mash']:
        mash_duration = config['unit'].convertUnits(recipe_config['Mash']['duration'], 'hours')
    else:
        mash_duration = 1
        print 'Mash duration not specified, assuming {0:.1f} hours.'.format(mash_duration)

    if 'Brew Day' in recipe_config and 'temperature' in recipe_config['Brew Day']:
        ambient_temp = fahrenheit_to_celsius(recipe_config['Brew Day']['temperature'])
    else:
        ambient_temp = fahrenheit_to_celsius(65)
        print 'Ambient temperature on brew day not specified; assuming {0:.0f} degF.'.format(celsius_to_fahrenheit(ambient_temp))

    if 'Mash Water Volume' in recipe_config:
        mwv = config['unit'].convertUnits(recipe_config['Mash Water Volume'], 'liters')
    else:
        print 'Mash Water Volume not specified, try running malt_composition first.'
        sys.exit()

    grain_mass = 0.
    if 'Malt' in recipe_config:
        for malt in recipe_config['Malt']:
            if 'mass' in malt:
                grain_mass += config['unit'].convertUnits(malt['mass'], 'kilograms')

    if grain_mass == 0:
        print "No grain mass specified. That's a weak beer!"
        sys.exit()

    if 'Water Density' in config:
        water_density = config['unit'].convertUnits(config['Water Density'], 'kilograms_per_liter')
    else:
        water_density = 1. # kilograms per liter

    if 'Water Specific Heat' in config:
        water_specific_heat = config['Water Specific Heat']
    else:
        water_specific_heat = 1000. # calories per kg per degC

    if 'Grain Specific Heat' in config:
        grain_specific_heat = config['Grain Specific Heat']
    else:
        grain_specific_heat = 396.8068 # calories per kg per degC

    if 'Mashtun Thermal Mass' in config:
        mttm = config['Mashtun Thermal Mass']
    else:
        mttm = 1362.152 # calories per degC

    if 'Hot Liquor Tank Thermal Mass' in config:
        hlttm = config['Hot Liquor Tank Thermal Mass']
    else:
        print 'Assuming Hot Liquor Tank Thermal Mass is the same as the Mashtun Thermal Mass.'
        hlttm = mttm

    # Heat loss during transfer from brew kettle to mash tun
    if 'Heat Loss During Kettle Transfer' in config:
        hldt = fahrenheit_to_celsius(config['Heat Loss During Kettle Transfer'], difference=True)
    else:
        hldt = fahrenheit_to_celsius(5.2, difference=True)

    # Heat Loss In Tun: temperature drop before adding grain (error margin)
    if 'Heat Loss in Mashtun' in config:
        hlit = fahrenheit_to_celsius(config['Heat Loss in Mashtun'], difference=True)
    else:
        hlit = fahrenheit_to_celsius(1.6, difference=True)

    if 'Mash Cooling Rate' in config:
        mcr = fahrenheit_to_celsius(config['Mash Cooling Rate'], difference=True)
    else:
        mcr = fahrenheit_to_celsius(4, difference=True) # degC per hour

    if 'Sparge Temperature' in config:
        sparge_temp = fahrenheit_to_celsius(config['Sparge Temperature'])
    else:
        sparge_temp = fahrenheit_to_celsius(170)
        print 'Assuming Sparge Temperature is {0:.1f} degF.'.format(celsius_to_fahrenheit(sparge_temp))

    if 'Boiling Temperature' in config:
        boiling_temp = fahrenheit_to_celsius(config['Boiling Temperature'])
    else:
        boiling_temp = fahrenheit_to_celsius(212)
        print 'Assuming Boiling Temperature is {0:.1f} degF.'.format(celsius_to_fahrenheit(boiling_temp))
    
    mwtm = mwv * water_density * water_specific_heat # calories per degC
    gtm = grain_mass * grain_specific_heat


    if 'Water Temperature in Kettle' in recipe_config:
        wtika = fahrenheit_to_celsius(recipe_config['Water Temperature in Kettle'])
    else:
        wtika = None

    if 'Water Temperature in Mashtun' in recipe_config:
        wtitaa = fahrenheit_to_celsius(recipe_config['Water Temperature in Mashtun'])
    else:
        wtitaa = None
    
    if 'Final Mash Temperature' in recipe_config:
        mtfa = fahrenheit_to_celsius(recipe_config['Final Mash Temperature'])
    else:
        mtfa = None

    # Water temp in kettle
    wtik = mash_temp * (mwtm + mttm + gtm) - ambient_temp * (gtm + mttm) + hlit * (mttm + mwtm)
    wtik /= mwtm
    wtik += hldt

    if wtika is None:
        wtit = (mwtm * (wtik - hldt) + ambient_temp * mttm) / (mttm + mwtm)
    else:
        wtit = (mwtm * (wtika - hldt) + ambient_temp * mttm) / (mttm + mwtm)
        
    wtita = (mash_temp * (mttm + mwtm + gtm) - ambient_temp * gtm) / (mttm + mwtm)

    if wtitaa is None:
        wtitwg = (wtita * (mttm + mwtm) + ambient_temp * gtm) / (mttm + mwtm + gtm)
    else:
        wtitwg = (wtitaa * (mttm + mwtm) + ambient_temp * gtm) / (mttm + mwtm + gtm)
        
    mtf = wtitwg - mcr * mash_duration


    print 'Heat mash water to {0:.1f} degF.'.format(celsius_to_fahrenheit(wtik))
    if wtika is not None:
        print 'Actual temperature achieved: {0:.1f} degF.'.format(celsius_to_fahrenheit(wtika))
    
    print 'After adding to mash tun (before adding grain), temperature is predicted to be {0:.1f} degF.'.format(celsius_to_fahrenheit(wtit))
    print 'Allow water to cool to {0:.1f} degF before adding grain.'.format(celsius_to_fahrenheit(wtita))
    if wtitaa is not None:
        print 'Actual temperature: {0:.1f} degF.'.format(celsius_to_fahrenheit(wtitaa))
        
    print 'After adding grain and stirring, temperature is predicted to be {0:.1f} degF.'.format(celsius_to_fahrenheit(wtitwg))

    print 'After {0:.0f} minutes, mash temp is expected to decrease to {1:.1f} degF.'.format(config['unit'].convertUnits(mash_duration, 'hours', 'minutes'), celsius_to_fahrenheit(mtf))
    if mtfa is not None:
        print 'Actual temperature: {0:.1f} degF.'.format(celsius_to_fahrenheit(mtfa))

    if 'Sparge and Mash-out Water Volume' in recipe_config:
        smwv = config['unit'].convertUnits(recipe_config['Sparge and Mash-out Water Volume'], 'gallons')
        print 'Begin heating sparge and mash-out water: {0:.2f} gallons.'.format(smwv)
        smwv = config['unit'].convertUnits(smwv, 'gallons', 'liters')
        if mtfa is None:
            mowtm = (mttm + mwtm + gtm) * (sparge_temp - mtf) / (boiling_temp - sparge_temp)
        else:
            mowtm = (mttm + mwtm + gtm) * (sparge_temp - mtfa) / (boiling_temp - sparge_temp)
            
        mowv = mowtm / (water_specific_heat * water_density)

        swv = smwv - mowv
        swtm = swv * water_density * water_specific_heat
        swt = (hlttm * (sparge_temp - ambient_temp) + swtm * sparge_temp) / swtm
        
        print 'When water reaches {0:.1f} degF, transfer {1:.1f} gallons to the hot liquor tank.'.format(celsius_to_fahrenheit(swt), config['unit'].convertUnits(swv, 'liters', 'gallons'))
        print 'Bring remaining (mash-out) water, {0:.1f} gallons, to a boil.'.format(config['unit'].convertUnits(mowv, 'liters', 'gallons'))
        print 'Add mash-out water to mash, bringing temperature up to {0:.1f} degF.'.format(celsius_to_fahrenheit(sparge_temp))


    recipe_config['Water Temperature in Kettle'] = celsius_to_fahrenheit(wtik)
    recipe_config['Water Temperature in Mashtun'] = celsius_to_fahrenheit(wtita)
    recipe_config['Final Mash Temperature'] = celsius_to_fahrenheit(mtf)
    
    return config, recipe_config

def fahrenheit_to_celsius(degf, difference=False):
    if difference:
        return (5. / 9.) * degf
    else:
        return (5. / 9.) * (degf - 32.)

def celsius_to_fahrenheit(degc, difference=False):
    if difference:
        return (9. / 5.) * degc
    else:
        return (9. / 5.) * degc + 32

if __name__ == '__main__':
    config = json.load(open('/Users/bobwilson/beer/bin/homebrew.json', 'r'))
    unit = units()
    unit.parseUnitFile(config['files']['units'])
    config['unit'] = unit

    parser = argparse.ArgumentParser()
    parser.add_argument('recipe', type=str, help='Recipe JSON')
    parser.add_argument('-o', '--output', type=str, help='Output file')

    args = parser.parse_args()
    recipe_config = json.load(open(args.recipe, 'r'))
    if args.output:
        config['Output'] = args.output

    execute(config, recipe_config)



