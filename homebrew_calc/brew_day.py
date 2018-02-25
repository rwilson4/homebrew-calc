from __future__ import print_function
import json
import os
import sys
from unit_parser import unit_parser
from malt_composition import specific_gravity_to_gravity_points


def main():
    """Entry point for brew_day command line script.

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
    if 'Mash' not in recipe_config or 'type' not in recipe_config['Mash']:
        raise ValueError('Mash information not provided')

    if 'units' in config:
        config['unit_parser'] = unit_parser(config['units'])
    else:
        config['unit_parser'] = unit_parser()

    if recipe_config['Mash']['type'] == 'Infusion':
        config, recipe_config = infusion_mash(config, recipe_config)
    elif recipe_config['Mash']['type'] == 'Step':
        config, recipe_config = step_mash(config, recipe_config)
    else:
        raise ValueError('Mash type not supported.')

    print('')
    config, recipe_config = lauter(config, recipe_config)
    print('')
    config, recipe_config = boil(config, recipe_config)

    if 'Output' in config:
        with open(config['Output'], 'w') as outfile:
            json.dump(recipe_config, outfile, indent=2, sort_keys=True)


def step_mash(config, recipe_config):
    """ Mash with multiple steps. """

    up = config['unit_parser']

    if 'steps' not in recipe_config['Mash']:
        raise ValueError('Steps not specified; exiting.')

    steps = recipe_config['Mash']['steps']

    for step in steps:
        if 'temperature' not in step or 'duration' not in step:
            raise ValueError('Must specify temperature and duration for each step.')

    first_step = steps[0]
    mash_temp = fahrenheit_to_celsius(first_step['temperature'])
    mash_duration = up.convert(first_step['duration'], 'hours')

    ambient_temp, mwv, gtm, water_density, water_specific_heat, mttm, hlttm, hldt, hlit, mcr, sparge_temp, boiling_temp = get_common_params(config, recipe_config)

    mwtm = mwv * water_density * water_specific_heat # calories per degC

    if 'Water Temperature in Kettle' in first_step:
        wtika = fahrenheit_to_celsius(first_step['Water Temperature in Kettle'])
    else:
        wtika = None

    if 'Water Temperature in Mashtun' in first_step:
        wtitaa = fahrenheit_to_celsius(first_step['Water Temperature in Mashtun'])
    else:
        wtitaa = None

    if 'Final Mash Temperature' in first_step:
        mtfa = fahrenheit_to_celsius(first_step['Final Mash Temperature'])
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

    msg = 'Heat mash water ({0:.2f} gallons) to {1:.1f} degF.'
    mwv_gal = up.convert(mwv, 'liters', 'gallons')
    print(msg.format(mwv_gal, celsius_to_fahrenheit(wtik)))
    if wtika is not None:
        msg = 'Actual temperature achieved: {0:.1f} degF.'
        print(msg.format(celsius_to_fahrenheit(wtika)))

    msg = 'After adding to mash tun (before adding grain),'
    msg += ' temperature is predicted to be {0:.1f} degF.'
    print(msg.format(celsius_to_fahrenheit(wtit)))
    msg = 'Allow water to cool to {0:.1f} degF before adding grain.'
    print(msg.format(celsius_to_fahrenheit(wtita)))
    if wtitaa is not None:
        msg = 'Actual temperature: {0:.1f} degF.'
        print(msg.format(celsius_to_fahrenheit(wtitaa)))

    msg = 'After adding grain and stirring, temperature is'
    msg += ' predicted to be {0:.1f} degF.'
    print(msg.format(celsius_to_fahrenheit(wtitwg)))

    msg = 'After {0:.0f} minutes, mash temp is expected to decrease to {1:.1f} degF.'
    md_min = up.convert(mash_duration, 'hours', 'minutes')
    print(msg.format(md_min, celsius_to_fahrenheit(mtf)))
    if mtfa is not None:
        msg = 'Actual temperature: {0:.1f} degF.'
        print(msg.format(celsius_to_fahrenheit(mtfa)))
    else:
        mtfa = mtf

    # Combined thermal mass
    ctm = mttm + mwtm + gtm

    for step in steps[1:]:
        step_temp = fahrenheit_to_celsius(step['temperature'])
        step_duration = up.convert(step['duration'], 'hours')
        # mash_temp * (swtm + ctm) = bt * swtm + mtfa * ctm
        # mash_temp * swtm + mash_temp * ctm = bt * swtm + mtfa * ctm
        # mash_temp * ctm - mtfa * ctm = bt * swtm - mash_temp * swtm
        # (mash_temp - mtfa) * ctm = (bt - mash_temp) * swtm
        swtm = ctm * (step_temp - mtfa) / (boiling_temp - step_temp)
        swv = swtm / (water_specific_heat * water_density)
        ctm += swtm

        msg = 'To bring mash up to {0:.1f} degF, add {1:.1f} gallons boiling water.'
        swv_gal = up.convert(swv, 'liters', 'gallons')
        print(msg.format(celsius_to_fahrenheit(step_temp), swv_gal))

        if 'Achieved Mash Temperature' in step:
            msg = 'Temperature achieved: {0:.1f} degF'
            print(msg.format(step['Achieved Mash Temperature']))
            step_temp = fahrenheit_to_celsius(step['Achieved Mash Temperature'])

        mtf = step_temp - mcr * step_duration

        msg = 'After {0:.0f} minutes, temperature is'
        msg += ' predicted to drop to {1:.1f} degF.'
        sd_min = up.convert(step_duration, 'hours', 'minutes')
        print(msg.format(sd_min, celsius_to_fahrenheit(mtf)))

        if 'Final Mash Temperature' in step:
            msg = 'Actual temperature: {0:.1f} degF'
            print(msg.format(step['Final Mash Temperature']))
            mtfa = fahrenheit_to_celsius(step['Final Mash Temperature'])
        else:
            mtfa = mtf

    swtm = ctm * (sparge_temp - mtfa) / (boiling_temp - sparge_temp)
    swv = swtm / (water_specific_heat * water_density)

    msg = 'To mash out at {0:.1f} degF, add {1:.1f} gallons boiling water.'
    swv_gal = up.convert(swv, 'liters', 'gallons')
    print(msg.format(celsius_to_fahrenheit(sparge_temp), swv_gal))

    return config, recipe_config


def infusion_mash(config, recipe_config):
    """ Simple infusion mash. """

    up = config['unit_parser']

    if 'temperature' in recipe_config['Mash']:
        mash_temp = fahrenheit_to_celsius(recipe_config['Mash']['temperature'])
    else:
        print('Mash temperature not specified.')
        sys.exit()

    if 'duration' in recipe_config['Mash']:
        mash_duration = up.convert(recipe_config['Mash']['duration'], 'hours')
    else:
        mash_duration = 1
        print('Mash duration not specified, assuming {0:.1f} hours.'.format(mash_duration))

    ambient_temp, mwv, gtm, water_density, water_specific_heat, mttm, hlttm, hldt, hlit, mcr, sparge_temp, boiling_temp = get_common_params(config, recipe_config)

    mwtm = mwv * water_density * water_specific_heat # calories per degC

    if 'Brew Day' in recipe_config and 'Water Temperature in Kettle' in recipe_config['Brew Day']:
        wtika = fahrenheit_to_celsius(recipe_config['Brew Day']['Water Temperature in Kettle'])
    else:
        wtika = None

    if 'Brew Day' in recipe_config and 'Water Temperature in Mashtun' in recipe_config['Brew Day']:
        wtitaa = fahrenheit_to_celsius(recipe_config['Brew Day']['Water Temperature in Mashtun'])
    else:
        wtitaa = None

    if 'Brew Day' in recipe_config and 'Final Mash Temperature' in recipe_config['Brew Day']:
        mtfa = fahrenheit_to_celsius(recipe_config['Brew Day']['Final Mash Temperature'])
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


    print('Heat mash water ({0:.2f} gallons) to {1:.1f} degF.'.format(up.convert(mwv, 'liters', 'gallons'), celsius_to_fahrenheit(wtik)))
    if wtika is not None:
        print('Actual temperature achieved: {0:.1f} degF.'.format(celsius_to_fahrenheit(wtika)))

    print('After adding to mash tun (before adding grain), temperature is predicted to be {0:.1f} degF.'.format(celsius_to_fahrenheit(wtit)))
    print('Allow water to cool to {0:.1f} degF before adding grain.'.format(celsius_to_fahrenheit(wtita)))
    if wtitaa is not None:
        print('Actual temperature: {0:.1f} degF.'.format(celsius_to_fahrenheit(wtitaa)))

    print('After adding grain and stirring, temperature is predicted to be {0:.1f} degF.'.format(celsius_to_fahrenheit(wtitwg)))

    print('After {0:.0f} minutes, mash temp is expected to decrease to {1:.1f} degF.'.format(up.convert(mash_duration, 'hours', 'minutes'), celsius_to_fahrenheit(mtf)))
    if mtfa is not None:
        print('Actual temperature: {0:.1f} degF.'.format(celsius_to_fahrenheit(mtfa)))

    if 'Sparge and Mash-out Water Volume' in recipe_config:
        smwv = up.convert(recipe_config['Sparge and Mash-out Water Volume'], 'gallons')
        print('Begin heating sparge and mash-out water: {0:.2f} gallons.'.format(smwv))
        smwv = up.convert(smwv, 'gallons', 'liters')
        if mtfa is None:
            mowtm = (mttm + mwtm + gtm) * (sparge_temp - mtf) / (boiling_temp - sparge_temp)
        else:
            mowtm = (mttm + mwtm + gtm) * (sparge_temp - mtfa) / (boiling_temp - sparge_temp)

        mowv = mowtm / (water_specific_heat * water_density)

        swv = smwv - mowv
        swtm = swv * water_density * water_specific_heat
        swt = (hlttm * (sparge_temp - ambient_temp) + swtm * sparge_temp) / swtm

        print('When water reaches {0:.1f} degF, transfer {1:.1f} gallons to the hot liquor tank.'.format(celsius_to_fahrenheit(swt), up.convert(swv, 'liters', 'gallons')))
        print('Bring remaining (mash-out) water, {0:.1f} gallons, to a boil.'.format(up.convert(mowv, 'liters', 'gallons')))
        print('Add mash-out water to mash, bringing temperature up to {0:.1f} degF.'.format(celsius_to_fahrenheit(sparge_temp)))

    if 'Brew Day' not in recipe_config:
        recipe_config['Brew Day'] = {}

    if wtika is None:
        recipe_config['Brew Day']['Water Temperature in Kettle'] = celsius_to_fahrenheit(wtik)

    if wtitaa is None:
        recipe_config['Brew Day']['Water Temperature in Mashtun'] = celsius_to_fahrenheit(wtita)

    if mtfa is None:
        recipe_config['Brew Day']['Final Mash Temperature'] = celsius_to_fahrenheit(mtf)

    return config, recipe_config


def lauter(config, recipe_config):
    """ Collect pre-boil wort. """

    up = config['unit_parser']

    if 'Pre-Boil Volume' not in recipe_config or 'Pre-Boil Gravity' not in recipe_config:
        raise ValueError('Pre-Boil Volume not in config; try running water_composition first.')

    pbv = up.convert(recipe_config['Pre-Boil Volume'], 'gallons')
    pbg = recipe_config['Pre-Boil Gravity']
    print('Collect {0:.2f} gallons of wort.'.format(pbv))
    print('Pre-boil gravity should be {0:.03f}.'.format(pbg))

    if 'Brew Day' in recipe_config and 'Pre-Boil Volume' in recipe_config['Brew Day'] and 'Pre-Boil Volume' in recipe_config['Brew Day']:
        apbv = up.convert(recipe_config['Brew Day']['Pre-Boil Volume'], 'gallons')
        apbg = recipe_config['Brew Day']['Pre-Boil Gravity']

        agp = specific_gravity_to_gravity_points(apbg, apbv)
        gp = specific_gravity_to_gravity_points(pbg, pbv)

        if 'Brewhouse Efficiency' in recipe_config:
            planned_efficiency = recipe_config['Brewhouse Efficiency']
        elif 'Brewhouse Efficiency' in config:
            planned_efficiency = config['Brewhouse Efficiency']
        else:
            planned_efficiency = 0.7

        print('Actual wort collected during lauter: {0:.2f} gallons.'.format(apbv))
        print('Actual pre-boil gravity: {0:.03f}.'.format(apbg))

        efficiency = planned_efficiency * agp / gp
        print('Efficiency: {0:.02f}'.format(efficiency))
        recipe_config['Brew Day']['Brewhouse Efficiency'] = efficiency
    else:
        if 'Brew Day' not in recipe_config:
            recipe_config['Brew Day'] = {}

        if 'Pre-Boil Volume' not in recipe_config['Brew Day']:
            recipe_config['Brew Day']['Pre-Boil Volume'] = '{0:.6f} gallons'.format(pbv)

        if 'Pre-Boil Gravity' not in recipe_config['Brew Day']:
            recipe_config['Brew Day']['Pre-Boil Gravity'] = pbg

    return config, recipe_config


def boil(config, recipe_config):
    """ Boil wort. """

    up = config['unit_parser']

    if 'Hops' in recipe_config:
        hops = recipe_config['Hops']
        for hop in hops:
            if 'addition type' in hop and hop['addition type'] == 'fwh':
                if 'mass' in hop and 'name' in hop and 'type' in hop:
                    mass = up.convert(hop['mass'], 'ounces')
                    variety = hop['name']
                    pellets = hop['type']
                    print('Add {0:.2f}oz {1:s} {2:s} during lautering process (first wort hopping).'.format(mass, variety, pellets))

        time_additions = []
        for hop in hops:
            if 'boil_time' in hop and 'mass' in hop and 'name' in hop and 'type' in hop:
                boil_time = up.convert(hop['boil_time'], 'minutes')
                mass = up.convert(hop['mass'], 'ounces')
                variety = hop['name']
                pellets = hop['type']
                time_additions.append({'boil_time': boil_time, 'mass': mass, 'variety': variety, 'pellets': pellets})

        time_additions = sorted(time_additions, key=lambda k: k['boil_time'], reverse=True)
        for hop in time_additions:
            if hop['boil_time'] == 1:
                plural = ''
            else:
                plural = 's'

            print('Add {0:.2f}oz {2:s} {3:s} at {1:.0f} minute{4:s}.'.format(hop['mass'], hop['boil_time'], hop['variety'], hop['pellets'], plural))

        for hop in hops:
            if 'addition type' in hop and hop['addition type'] == 'flameout':
                if 'mass' in hop and 'name' in hop and 'type' in hop:
                    mass = up.convert(hop['mass'], 'ounces')
                    variety = hop['name']
                    pellets = hop['type']
                    print('Add {0:.2f}oz {1:s} {2:s} at flameout.'.format(mass, variety, pellets))

    if ('Pre-Boil Volume' not in recipe_config or
        'Pre-Boil Gravity' not in recipe_config):
        return config, recipe_config

    pre_bv = up.convert(recipe_config['Pre-Boil Volume'], 'gallons')
    pre_bg = recipe_config['Pre-Boil Gravity']

    if ('Brew Day' in recipe_config and
      'Post-Boil Volume' in recipe_config['Brew Day'] and
      'Original Gravity' in recipe_config['Brew Day']):

        if 'Pre-Boil Volume' in recipe_config['Brew Day']:
            actual_pre_bv = up.convert(recipe_config['Brew Day']['Pre-Boil Volume'], 'gallons')

        if 'Boil Time' in recipe_config:
            boil_time = up.convert(recipe_config['Boil Time'], 'hours')
        elif 'Boil Time' in config:
            boil_time = up.convert(config['Boil Time'], 'hours')
        else:
            boil_time = 1.0

        post_bv = up.convert(recipe_config['Brew Day']['Post-Boil Volume'], 'gallons')
        og = recipe_config['Brew Day']['Original Gravity']
        post_gp = specific_gravity_to_gravity_points(og, post_bv)
        pre_gp = specific_gravity_to_gravity_points(pre_bg, pre_bv)

        if 'Brewhouse Efficiency' in recipe_config:
            planned_efficiency = recipe_config['Brewhouse Efficiency']
        elif 'Brewhouse Efficiency' in config:
            planned_efficiency = config['Brewhouse Efficiency']
        else:
            planned_efficiency = 0.7

        efficiency = planned_efficiency * post_gp / pre_gp
        recipe_config['Brew Day']['Brewhouse Efficiency'] = efficiency

        evaporation_rate = (actual_pre_bv - post_bv) / boil_time
        recipe_config['Brew Day']['Evaporation Rate'] = '{0:.06f} gallons_per_hour'.format(evaporation_rate)

        print('Actual post-boil volume: {0:.02f} gallons'.format(post_bv))
        print('Evaporation rate: {0:.02f} gallons per hour'.format(evaporation_rate))
        print('Original gravity: {0:.03f}'.format(og))
        print('Efficiency: {0:.02f}'.format(efficiency))
    elif ('Brew Day' in recipe_config
          and 'Pre-Boil Volume' in recipe_config['Brew Day']
          and 'Pre-Boil Gravity' in recipe_config['Brew Day']):

        pre_boil_volume = up.convert(recipe_config['Brew Day']['Pre-Boil Volume'], 'gallons')
        pre_boil_gravity = recipe_config['Brew Day']['Pre-Boil Gravity']
        pre_gp = pre_boil_gravity - 1

        if 'Boil Time' in recipe_config:
            boil_time = up.convert(recipe_config['Boil Time'], 'hours')
        elif 'Boil Time' in config:
            boil_time = up.convert(config['Boil Time'], 'hours')
        else:
            boil_time = 1.0

        if 'Evaporation Rate' in recipe_config:
            evaporation_rate = up.convert(recipe_config['Evaporation Rate'], 'gallons_per_hour')
        elif 'Evaporation Rate' in config:
            evaporation_rate = up.convert(config['Evaporation Rate'], 'gallons_per_hour')
        else:
            evaporation_rate = 1.75

        post_boil_volume = pre_boil_volume - evaporation_rate * boil_time
        og = 1 + pre_gp * pre_boil_volume / post_boil_volume

        print('Predicted original gravity: {0:.03f}'.format(og))
        recipe_config['Brew Day']['Original Gravity'] = og
    else:
        if 'Original Gravity' in recipe_config:
            print('Predicted original gravity: {0:.03f}'.format(recipe_config['Original Gravity']))

    return config, recipe_config


def get_common_params(config, recipe_config):
    up = config['unit_parser']

    if 'Brew Day' in recipe_config and 'temperature' in recipe_config['Brew Day']:
        ambient_temp = fahrenheit_to_celsius(recipe_config['Brew Day']['temperature'])
    else:
        ambient_temp = fahrenheit_to_celsius(65)
        print('Ambient temperature on brew day not specified; assuming {0:.0f} degF.'.format(celsius_to_fahrenheit(ambient_temp)))

    if 'Mash Water Volume' in recipe_config:
        mwv = up.convert(recipe_config['Mash Water Volume'], 'liters')
    else:
        raise ValueError('Mash Water Volume not specified, try running malt_composition first.')

    grain_mass = 0.
    if 'Malt' in recipe_config:
        for malt in recipe_config['Malt']:
            if 'mass' in malt:
                grain_mass += up.convert(malt['mass'], 'kilograms')

    if grain_mass == 0:
        raise ValueError("No grain mass specified. That's a weak beer!")

    if 'Water Density' in config:
        water_density = up.convert(config['Water Density'], 'kilograms_per_liter')
    else:
        water_density = 1. # kilograms per liter

    if 'Water Specific Heat' in config:
        water_specific_heat = up.convert(config['Water Specific Heat'], "calories_per_kilogram_degC")
    else:
        water_specific_heat = 1000. # calories per kg per degC

    if 'Grain Specific Heat' in config:
        grain_specific_heat = up.convert(config['Grain Specific Heat'], "calories_per_kilogram_degC")
    else:
        grain_specific_heat = 396.8068 # calories per kg per degC

    if 'Mashtun Thermal Mass' in config:
        mttm = up.convert(config['Mashtun Thermal Mass'], "calories_per_degC")
    else:
        mttm = 1362.152 # calories per degC

    if 'Hot Liquor Tank Thermal Mass' in config:
        hlttm = up.convert(config['Hot Liquor Tank Thermal Mass'], "calories_per_degC")
    else:
        print('Assuming Hot Liquor Tank Thermal Mass is the same as the Mashtun Thermal Mass.')
        hlttm = mttm

    # Heat loss during transfer from brew kettle to mash tun
    if 'Heat Loss During Kettle Transfer' in config:
        hldt = up.convert(config['Heat Loss During Kettle Transfer'], "degC")
    else:
        hldt = up.convert(5.2, "degF", "degC")

    # Heat Loss In Tun: temperature drop before adding grain (error margin)
    if 'Heat Loss in Mashtun' in config:
        hlit = up.convert(config['Heat Loss in Mashtun'], "degC")
    else:
        hlit = up.convert(1, "degF", "degC")

    if 'Mash Cooling Rate' in config:
        mcr = up.convert(config['Mash Cooling Rate'], "degC_per_hour")
    else:
        mcr = up.convert(4, "degF_per_hour", "degC_per_hour")

    if 'Sparge Temperature' in config:
        sparge_temp = fahrenheit_to_celsius(config['Sparge Temperature'])
    else:
        sparge_temp = fahrenheit_to_celsius(170)
        print('Assuming Sparge Temperature is {0:.1f} degF.'.format(celsius_to_fahrenheit(sparge_temp)))

    if 'Boiling Temperature' in config:
        boiling_temp = fahrenheit_to_celsius(config['Boiling Temperature'])
    else:
        boiling_temp = fahrenheit_to_celsius(212)
        print('Assuming Boiling Temperature is {0:.1f} degF.'.format(celsius_to_fahrenheit(boiling_temp)))

    gtm = grain_mass * grain_specific_heat
    return ambient_temp, mwv, gtm, water_density, water_specific_heat, mttm, hlttm, hldt, hlit, mcr, sparge_temp, boiling_temp


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
    main()
