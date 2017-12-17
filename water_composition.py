#!/usr/bin/python

# General references:
# http://www.brewersfriend.com/mash-chemistry-and-brewing-water-calculator/
#
# Acidity of crystal malt is approximately linearly related to color
# acidity = 0.45 * degL + 6
# (acidity measured in mEq/kg)
#
# http://braukaiser.com/wiki/index.php?title=Mash_pH_control

import json
import sys
import numpy as np
from unit_parser import unit_parser
from scipy import interpolate
import cvxpy as cvx
from convert_pH_temp import convert_pH_temp

def execute(config, recipe_config):
    config, recipe_config = water_volume(config, recipe_config)
    config, recipe_config = water_chemistry(config, recipe_config)

    if 'Output' in config:
        with open(config['Output'], 'w') as outfile:
            json.dump(recipe_config, outfile, indent=2, sort_keys=True)
        

def water_volume(config, recipe_config):
    up = unit_parser()

    if 'Boil Time' in recipe_config:
        boil_time = up.convert(recipe_config['Boil Time'], 'hours')
    elif 'Boil Time' in config:
        boil_time = up.convert(config['Boil Time'], 'hours')
    else:
        print 'Boil Length not specified.'
        return config, recipe_config

    if 'Evaporation Rate' in recipe_config:
        evaporation_rate = up.convert(recipe_config['Evaporation Rate'], 'gallons_per_hour')
    elif 'Evaporation Rate' in config:
        evaporation_rate = up.convert(config['Evaporation Rate'], 'gallons_per_hour')
    else:
        print 'Evaporation Rate not specified.'
        return config, recipe_config
    
    if 'Trub Losses' in recipe_config:
        trub_losses = up.convert(recipe_config['Trub Losses'], 'gallons')
    elif 'Trub Losses' in config:
        trub_losses = up.convert(config['Trub Losses'], 'gallons')
    else:
        print 'Trub Losses not specified.'
        return config, recipe_config

    if 'Pitchable Volume' in recipe_config:
        pitchable_volume = up.convert(recipe_config['Pitchable Volume'], 'gallons')
    elif 'Pitchable Volume' in config:
        pitchable_volume = up.convert(config['Pitchable Volume'], 'gallons')
    else:
        pitchable_volume = 5.25
        print 'Pitchable volume not specified, assuming {0:.02f} gallons'.format(pitchable_volume)

    post_boil_volume = pitchable_volume + trub_losses
    pre_boil_volume = post_boil_volume + evaporation_rate * boil_time
    average_boil_volume = 0.5 * (pre_boil_volume + post_boil_volume)
    recipe_config['Pre-Boil Volume'] = '{0:.06f} gallons'.format(pre_boil_volume)
    recipe_config['Average Boil Volume'] = '{0:.06f} gallons'.format(average_boil_volume)

    if 'Absorption Rate' in recipe_config:
        ar = up.convert(recipe_config['Absorption Rate'], 'gallons_per_pound')
    elif 'Absorption Rate' in config:
        ar = up.convert(config['Absorption Rate'], 'gallons_per_pound')
    else:
        ar = 0.2
        print 'Absorption Rate not specified, assuming {0:.02f} gallons_per_pound.'.format(ar)

    if ar is not None:
        mass = 0
        for malt in recipe_config['Malt']:
            if 'mass' in malt:
                mass += up.convert(malt['mass'], 'pounds')
        wltg = ar * mass
    else:
        wltg = 0.

    if 'Mash Water Volume' in recipe_config:
        mwv = up.convert(recipe_config['Mash Water Volume'], 'gallons')
        recipe_config['Sparge and Mash-out Water Volume'] = '{0:.06f} gallons'.format(wltg + pre_boil_volume - mwv)
        print 'Total Water: {0:.01f} gallons'.format(wltg + pre_boil_volume)
    else:
        print 'Mash Water Volume not specified. Try running malt_composition first.'
        print 'Cannot compute water needs.'

    if 'Original Gravity' in recipe_config:
        og = recipe_config['Original Gravity']
        pg = (og - 1) * 1000 * pitchable_volume
        recipe_config['Pre-Boil Gravity'] = 1 + 0.001 * pg / pre_boil_volume
        recipe_config['Average Gravity'] = 1 + 0.001 * pg / average_boil_volume
        print 'Pre-Boil Gravity: {0:.03f}'.format(recipe_config['Pre-Boil Gravity'])
    else:
        print 'Original Gravity not specified. Try running malt_composition first.'
        print 'Cannot compute pre-boil gravity.'

    print ''
    return config, recipe_config

def water_chemistry(config, recipe_config):
    up = unit_parser()
    A, target_composition, rac = get_targets(config, recipe_config)
    
    ingredients = ['Distilled water',
                   'Food-grade Chalk',
                   'Baking Soda',
                   'Gypsum',
                   'Epsom Salt',
                   'Calcium Chloride',
                   'Magnesium Chloride',
                   'Table Salt']

    minerals = ['Calcium', 'Magnesium', 'Sulfate', 'Sodium', 'Chloride', 'Total Alkalinity']

    target_rac = rac.dot(target_composition)
    w = cvx.Variable(A.shape[1])
    r = cvx.Variable(A.shape[0])
    b = np.array([10, 1, 5, 0.001, 5, 10])
    complexity_penalty = 1.0
    obj = cvx.norm(cvx.mul_elemwise(b, r - target_composition)) + complexity_penalty * cvx.norm(w[1:], 1)
    constraints = [0 <= w[:],
                   w[0] == 1.0, # 100% distilled
                   r[:] == A * w[:],
                   50 <= r[0], # Calcium
                   r[0] <= 200,
                   50 <= r[2], # Sulfate
                   r[2] <= 500,
                   r[3] <= 100, # Sodium
                   50 <= r[4], # Chloride
                   r[4] <= 200,
                   r.T * rac == target_rac, # Residual alkalinity
                   r[4] * target_composition[2] == r[2] * target_composition[4], # Chloride to sulfate ratio
                   w[1] == 0, # No chalk
                   w[6] == 0, # No MgSO4
                   
                   ]

    objective = cvx.Minimize(obj)
    prob = cvx.Problem(objective, constraints)
    prob.solve()

    r = r.value.A.squeeze()
    w = w.value.A.squeeze()
    w[w < 0.1] = 0
    r = A.dot(w)

    recipe_config['Water'] = {'distilled': 1.0}
    print '100% distilled water'

    recipe_config['Salts'] = {}
    for i in range(1,len(w)):
        if w[i] > 0:
            recipe_config['Salts'][ingredients[i]] = '{0:.04f} grams_per_gallon'.format(w[i])
            print '{0:.04f} grams per gallon {1:s}'.format(w[i], ingredients[i])

    if 'Mash Water Volume' in recipe_config:
        print ''
        mwv = up.convert(recipe_config['Mash Water Volume'], 'gallons')
        for i in range(1,len(w)):
            if w[i] > 0:
                print '{0:.02f} grams {1:s} in mash'.format(w[i] * mwv, ingredients[i])

    if 'Lactic Acid' in recipe_config:
        print '{0:.2f} tsp lactic acid in mash'.format(up.convert(recipe_config['Lactic Acid'], 'tsp'))
        
    if 'Sparge and Mash-out Water Volume' in recipe_config:
        print ''
        smwv = up.convert(recipe_config['Sparge and Mash-out Water Volume'], 'gallons')
        for i in range(1,len(w)):
            if w[i] > 0.1:
                print '{0:.02f} grams {1:s} in sparge/mash-out water'.format(w[i] * smwv, ingredients[i])

    print ''
    recipe_config['Water Profile Achieved'] = {}
    for i in range(len(r)):
        recipe_config['Water Profile Achieved'][minerals[i]] = r[i]
        print '{0:.1f} ppm {1:s}'.format(r[i], minerals[i])

    recipe_config['Water Profile Achieved']['Residual Alkalinity'] = rac.dot(r)
    print 'Residual alkalinity: {0:.0f}'.format(rac.dot(r))

    if (r[4] / r[2] < 0.5):
        descriptor = 'very hoppy'
    elif (r[4] / r[2] < 1.0):
        descriptor = 'hoppy'
    elif (r[4] / r[2] < 2):
        descriptor = 'malty'
    else:
        descriptor = 'very malty'

    recipe_config['Water Profile Achieved']['Chloride to Sulfate Ratio'] = r[4] / r[2]
    print 'Chloride to sulfate ratio: {0:.1f} ({1:s})'.format(r[4] / r[2], descriptor)

    config['r'] = r

    target_mash_pH = [4.5, 8.5]
    tol = 1e-6
    successful = True
    while (target_mash_pH[1] - target_mash_pH[0] > tol):
        pH = 0.5 * (target_mash_pH[0] + target_mash_pH[1])
        try:
            b = balance_eq(pH, config, recipe_config)
        except:
            print 'Cannot compute mash pH.'
            successful = False
            break
        
        if b > 0:
            target_mash_pH[0] = pH
        else:
            target_mash_pH[1] = pH

    pH = 0.5 * (target_mash_pH[0] + target_mash_pH[1])

    acidulated_mass = 0.
    malt_mass = 0.
    for m in recipe_config['Malt']:
        if m['name'] == 'Rice Hulls':
            continue
        
        malt_mass += up.convert(m.get('mass', 0), 'kilograms')
        if m['name'] == 'Acidulated Malt':
            acidulated_mass += up.convert(m.get('mass', 0), 'kilograms')
    acidulated_delta = 100 * 0.1 * acidulated_mass / malt_mass
    pH -= acidulated_delta

    pH_temp = config['water'].get('pH reference temperature', 68)
    pH = convert_pH_temp(pH, 68, pH_temp)
    pH_range_low = convert_pH_temp(5.4, 77, pH_temp)
    pH_range_high = convert_pH_temp(5.7, 77, pH_temp)

    if successful:
        recipe_config['Mash pH'] = pH
        recipe_config['pH Reference Temperature'] = pH_temp
        print 'Mash pH: {0:.03f} at {1:.0f} degF (target between {2:.03f} and {3:.03f})'.format(pH, pH_temp, pH_range_low, pH_range_high)

    return config, recipe_config

def balance_eq(mash_pH, config, recipe_config):
    up = unit_parser()
    baseline_pH = 4.3

    r = config['r']
    
    if 'Lactic Acid' in recipe_config:
        lactic_acid_volume = up.convert(recipe_config['Lactic Acid'], 'milliliters')
    else:
        lactic_acid_volume = 0.

    if 'Mash Water Volume' in recipe_config:
        water_volume = up.convert(recipe_config['Mash Water Volume'], 'liters')
    else:
        print 'Mash Water Volume not specified. Try running malt_composition first.'
        sys.exit()

    brewing_water_pH = config['water']['water']['distilled']['pH']

    malt_dipH = []
    malt_buffering_capacity = []
    malt_acidity = []
    acids = []
    malt_mass = []
    for x in recipe_config['Malt']:
        if x['name'] == 'Acidulated Malt':
            continue
        elif 'distilled pH' in x:
            malt_dipH.append(x['distilled pH'])
            malt_acidity.append(0.)
            acids.append(0)
            
            if 'buffering capacity' in x:
                malt_buffering_capacity.append(x['buffering capacity'])
            else:
                print 'Buffering capacity required for {0:s}.'.format(x['name'])
                sys.exit()

        elif 'acidity' in x:
            malt_acidity.append(x['acidity'])
            malt_dipH.append(0.)
            malt_buffering_capacity.append(0.)
            acids.append(1)

        elif 'type' in x and x['type'] == 'crystal' and 'degrees lovibond' in x:
            color = x['degrees lovibond']
            malt_acidity.append(0.45 * color + 6)
            malt_dipH.append(0.)
            malt_buffering_capacity.append(0.)
            acids.append(1)
            
        elif x['name'] in config['malt'] and 'distilled pH' in config['malt'][x['name']]:
            malt_dipH.append(config['malt'][x['name']]['distilled pH'])
            malt_acidity.append(0.)
            acids.append(0)

            if 'buffering capacity' in config['malt'][x['name']]:
                malt_buffering_capacity.append(config['malt'][x['name']]['buffering capacity'])
            else:
                print 'Buffering capacity required for {0:s}.'.format(x['name'])
                sys.exit()

        elif x['name'] in config['malt'] and 'acidity' in config['malt'][x['name']]:
            malt_acidity.append(config['malt'][x['name']]['acidity'])
            malt_dipH.append(0.)
            malt_buffering_capacity.append(0.)
            acids.append(1)

        elif x['name'] in config['malt'] and 'type' in config['malt'][x['name']] and config['malt'][x['name']]['type'] == 'crystal' and 'degrees lovibond' in config['malt'][x['name']]:

            color = config['malt'][x['name']]['degrees lovibond']
            malt_acidity.append(0.45 * color + 6)
            malt_dipH.append(0.)
            malt_buffering_capacity.append(0.)
            acids.append(1)

        else:
            malt_acidity.append(0.)
            malt_dipH.append(0.)
            malt_buffering_capacity.append(0.)
            acids.append(1)
            #print 'Acdidity for {0:s} not specified; assuming 0.'.format(x['name'])

        malt_mass.append(up.convert(x.get('mass', '0 kg'), 'kg'))

    malt_dipH = np.array(malt_dipH)
    malt_buffering_capacity = np.array(malt_buffering_capacity)
    malt_acidity = np.array(malt_acidity)
    acids = np.array(acids)
    malt_mass = np.array(malt_mass)

    total_alkalinity = (r[5] - (100 / 0.17) * lactic_acid_volume / water_volume) / 50 # mEq / L
    delta_c0 = charge_per_mmole(baseline_pH, config) - charge_per_mmole(brewing_water_pH, config)
    delta_cz = charge_per_mmole(mash_pH, config) - charge_per_mmole(brewing_water_pH, config)

    z_alkalinity = total_alkalinity * delta_cz / delta_c0
    z_ra = z_alkalinity - (r[0] * 2 / 40.078) / 3.5 - (r[1] * 2 / 24.305) / 7
    mw_alkalinity = z_ra * water_volume # mEq
    malt_dpH = malt_dipH - mash_pH
    
    alkalinity_contribution = malt_dpH * malt_buffering_capacity # mEq / kg
    for i in range(len(malt_acidity)):
        if acids[i] == 1:
            alkalinity_contribution[i] = -malt_acidity[i]

    malt_alkalinity = malt_mass.dot(alkalinity_contribution)

    balance = mw_alkalinity + malt_alkalinity
    return balance

def charge_per_mmole(pH, config):
    data = np.genfromtxt(config['water']['files']['mmole'], delimiter=',')

    f = interpolate.interp1d(data[:,0], data[:,1])
    return f(pH)

def get_targets(config, recipe_config):
    # Generate A matrix
    cols = {}
    for w in config['water']['water']:
        calcium    = config['water']['water'][w].get('calcium',   0.)
        magnesium  = config['water']['water'][w].get('magnesium', 0.)
        sulfate    = config['water']['water'][w].get('sulfate',   0.)
        sodium     = config['water']['water'][w].get('sodium',    0.)
        chloride   = config['water']['water'][w].get('chloride',  0.)
        alkalinity = config['water']['water'][w].get('alkalinity', config['water']['water'][w].get('carbonate', 0.) * 50. / 61)
        r = np.array([calcium, magnesium, sulfate, sodium, chloride, alkalinity])
        cols[w] = r

    for s in config['water']['salts']:
        calcium    = config['water']['salts'][s].get('calcium',   0.)
        magnesium  = config['water']['salts'][s].get('magnesium', 0.)
        sulfate    = config['water']['salts'][s].get('sulfate',   0.)
        sodium     = config['water']['salts'][s].get('sodium',    0.)
        chloride   = config['water']['salts'][s].get('chloride',  0.)
        alkalinity = config['water']['salts'][s].get('alkalinity', config['water']['salts'][s].get('carbonate', 0.) * 50. / 61)
        r = np.array([calcium, magnesium, sulfate, sodium, chloride, alkalinity])
        cols[s] = r

    A = np.array([cols['distilled'],
                  cols['Food-grade Chalk'],
                  cols['Baking Soda'],
                  cols['Gypsum'],
                  cols['Epsom Salt'],
                  cols['Calcium Chloride'],
                  cols['Magnesium Chloride'],
                  cols['Table Salt']]).transpose()

    calcium    = recipe_config['Water Profile'].get('calcium',    0.)
    magnesium  = recipe_config['Water Profile'].get('magnesium',  0.)
    sulfate    = recipe_config['Water Profile'].get('sulfate',    0.)
    sodium     = recipe_config['Water Profile'].get('sodium',     0.)
    chloride   = recipe_config['Water Profile'].get('chloride',   0.)
    alkalinity = recipe_config['Water Profile'].get('alkalinity', recipe_config['Water Profile'].get('carbonate', 0.) * 50. / 61)
    target_composition = np.array([calcium, magnesium, sulfate, sodium, chloride, alkalinity])

    calcium    = config['water']['Residual Alkalinity'].get('calcium',    0.)
    magnesium  = config['water']['Residual Alkalinity'].get('magnesium',  0.)
    sulfate    = config['water']['Residual Alkalinity'].get('sulfate',    0.)
    sodium     = config['water']['Residual Alkalinity'].get('sodium',     0.)
    chloride   = config['water']['Residual Alkalinity'].get('chloride',   0.)
    alkalinity = config['water']['Residual Alkalinity'].get('alkalinity', config['water']['Residual Alkalinity'].get('carbonate', 0.) * 50. / 61)
    rac = np.array([calcium, magnesium, sulfate, sodium, chloride, alkalinity])

    return A, target_composition, rac

if __name__ == '__main__':
    import argparse

    config = json.load(open('/Users/bobwilson/beer/bin/homebrew.json', 'r'))
    water_config = json.load(open(config['files']['water'], 'r'))
    config['water'] = water_config
    
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
