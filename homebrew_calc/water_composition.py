# General references:
# http://www.brewersfriend.com/mash-chemistry-and-brewing-water-calculator/
#
# Acidity of crystal malt is approximately linearly related to color
# acidity = 0.45 * degL + 6
# (acidity measured in mEq/kg)
#
# http://braukaiser.com/wiki/index.php?title=Mash_pH_control
from __future__ import print_function
import json
import os
import sys
import numpy as np
from unit_parser import unit_parser
from scipy import interpolate
import cvxpy as cvx
from .malt_composition import gravity_points_to_specific_gravity
from .malt_composition import specific_gravity_to_gravity_points


def convert_pH_temp_main():
    """Entry point for convert_ph_temp command line script.

    """
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('pH', type=float, help='pH')
    parser.add_argument('original_temperature', type=float,
                        help='Temperature associated with given pH measurement (in Fahrenheit)')
    parser.add_argument('desired_temperature', type=float,
                        help='Desired temperature for pH measurement (in Fahrenheit)')

    args = parser.parse_args()
    pH = convert_pH_temp(args.pH, args.original_temperature, args.desired_temperature)
    print('{0:.03f}'.format(pH))


def convert_pH_temp(pH, original_temperature, desired_temperature):
    """Convert pH between temperatures.

    Parameters
    ----------
     pH : float
        pH as measured.
     original_temperature : float
        Measurement temperature, in degrees Fahrenheit.
     desired_temperature : float
        Temperature relative to which to express the pH.

    Returns
    -------
     pH : float
        The pH that would be measured at the desired temperature.

    Notes
    -----
     The pH measured by a probe will vary based on the temperature of
     the sample for two reasons. The first is that the probe itself
     works according to electrochemical principles that vary according
     to the temperature. This is specific to the probe and has nothing
     to do with what is being measured. Many probes are branded as
     having "Automatic Temperature Correction" or "ATC", and those
     probes correct for this first phenomenon automatically.

     The second reason for variation is due to the intrinsic pH
     dependency on the temperature of the sample. Basically, the same
     substance at different temperatures really does have different pH
     levels. The variation depends on the substance and thus cannot
     automatically be corrected for by the probe, since the probe
     would have to know the details of the substance. For beer, a
     rough linear relationship holds over a range of desirable
     temperatures.

     This function permits the brewer to measure the sample at any
     temperature (provided it is reasonably close to room temperature;
     to do otherwise risks damage to the probe), and convert the
     measurement to a reference temperature for assessment.

    """
    return pH - 0.003 * (desired_temperature - original_temperature)


def main():
    """Entry point for water_composition command line script.

    """
    import argparse

    this_dir, this_filename = os.path.split(__file__)
    homebrew_config = os.path.join(this_dir, 'resources', 'homebrew.json')
    config = json.load(open(homebrew_config, 'r'))

    water_config_file = os.path.join(this_dir, 'resources', config['files']['water'])
    water_config = json.load(open(water_config_file, 'r'))
    config['water'] = water_config

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
    """Light wrapper for other functions.

    First we compute the water volume required. If the desired water
    profile is part of the recipe, we determine the requisite salts to
    add, and compute the mash pH.

    """
    if 'units' in config:
        config['unit_parser'] = unit_parser(config['units'])
    else:
        config['unit_parser'] = unit_parser()

    config, recipe_config = water_volume(config, recipe_config)
    if 'Water Profile' in recipe_config:
        config, recipe_config = salt_additions(config, recipe_config)
        config, recipe_config = mash_ph(config, recipe_config)

    if 'Output' in config:
        with open(config['Output'], 'w') as outfile:
            json.dump(recipe_config, outfile, indent=2, sort_keys=True)


def water_volume(config, recipe_config):
    """Determine water volume required.

    Note: required parameters are in either config or
    recipe_config. Where applicable, if a parameter is specified in
    both config and recipe_config, the latter overrides the former.

    Parameters
    ----------
     'Boil Time' : string
        String representing the length of the boil, e.g. '1 hour'.
     'Evaporation Rate' : string
        String representing how quickly boiling water evaporates, with
        dimensions of volume per time, e.g. '1
        gallon_per_hour'. Evaporation rate depends on ambient
        humidity, how windy it is, how strong the burner is, etc. I
        find this to be one of the biggest sources of variation from
        batch to batch. It might be best to use an evaporation rate
        lower than expected, and adding extra (sanitary) water at the
        end to make up for extra lost water.
     'Trub Losses' : string
        String representing how much volume of water is left in the
        kettle at the end (all the gunk).
     'Pitchable Volume' : string
        String representing the final volume of wort in which yeast
        will be pitched, e.g. '5 gallons'. Defaults to '5.25 gallons'
        if missing from both recipe_config and config.
     'Absorption Rate' : string
        String representing the amount of mash water lost to grain
        absorption, with dimension of volume (of water) per mass (of
        grain), e.g. '0.2 gallons_per_pound'.
     'Malt' : array_like
        Array of grist components (not necessarily malted). This is
        the same input as is used in malt_composition. See the
        documentation there. (The only input used here is the mass,
        which is needed to determine water absorption during the
        mash.)
     'Mash Water Volume' : string
        Amount of mash water needed, in gallons. Output from
        malt_composition.
     'Original Gravity' : float
        Predicted specific gravity of wort before pitching
        yeast. Output from malt_composition.

    Returns
    -------
     This function appends fields (documented below) to recipe_config
     and returns both config (unmodified) and recipe_config. It also
     prints the total water volume required (that is, how much water
     to go buy at the store or run through the RO filter, or
     whatever). It also prints the predicted pre-boil gravity.

    Fields Appended to recipe_config
    --------------------------------
     'Pre-Boil Volume' : string
        String representing the pre-boil volume of wort, for the
        purposes of assessing how much wort needs to be collected
        during the sparge/lauter process.
     'Average Boil Volume' : string
        String representing the boil volume half-way through the boil,
        for the purposes of estimating hop utilization.
     'Sparge and Mash-out Water Volume' : string
        String representing the total water needed for mashing-out and
        sparging.
     'Pre-Boil Gravity' : float
        Predicted specific gravity of wort before the boil. This gives
        a comparison point for assessing the efficiency of the mash on
        brew day.
     'Average Gravity' : float
        Predicted specific gravity of wort half-way through the
        boil. This is used for predicting hop utilization.

    """

    up = config['unit_parser']

    if 'Boil Time' in recipe_config:
        boil_time = up.convert(recipe_config['Boil Time'], 'hours')
    elif 'Boil Time' in config:
        boil_time = up.convert(config['Boil Time'], 'hours')
    else:
        raise ValueError('Boil Length not specified.')

    if 'Evaporation Rate' in recipe_config:
        evaporation_rate = up.convert(recipe_config['Evaporation Rate'],
                                      'gallons_per_hour')
    elif 'Evaporation Rate' in config:
        evaporation_rate = up.convert(config['Evaporation Rate'], 'gallons_per_hour')
    else:
        raise ValueError('Evaporation Rate not specified.')

    if 'Trub Losses' in recipe_config:
        trub_losses = up.convert(recipe_config['Trub Losses'], 'gallons')
    elif 'Trub Losses' in config:
        trub_losses = up.convert(config['Trub Losses'], 'gallons')
    else:
        raise ValueError('Trub Losses not specified.')

    if 'Pitchable Volume' in recipe_config:
        pitchable_volume = up.convert(recipe_config['Pitchable Volume'], 'gallons')
    elif 'Pitchable Volume' in config:
        pitchable_volume = up.convert(config['Pitchable Volume'], 'gallons')
    else:
        pitchable_volume = 5.25
        msg = 'Pitchable volume not specified, assuming {0:.02f} gallons'
        print(msg.format(pitchable_volume))

    post_boil_volume = pitchable_volume + trub_losses
    pre_boil_volume = post_boil_volume + evaporation_rate * boil_time
    average_boil_volume = 0.5 * (pre_boil_volume + post_boil_volume)
    recipe_config['Pre-Boil Volume'] = '{0:.06f} gallons'.format(pre_boil_volume)
    recipe_config['Average Boil Volume'] = '{0:.06f} gallons'.format(average_boil_volume)

    if 'Absorption Rate' in recipe_config:
        abs_rate = up.convert(recipe_config['Absorption Rate'], 'gallons_per_pound')
    elif 'Absorption Rate' in config:
        abs_rate = up.convert(config['Absorption Rate'], 'gallons_per_pound')
    else:
        abs_rate = 0.2
        msg = 'Absorption Rate not specified,'
        msg += ' assuming {0:.02f} gallons_per_pound.'
        print(msg.format(abs_rate))

    grain_mass = 0
    for malt in recipe_config['Malt']:
        if 'mass' in malt:
            grain_mass += up.convert(malt['mass'], 'pounds')

    water_lost_to_grain = abs_rate * grain_mass
    total_water = water_lost_to_grain + pre_boil_volume

    if 'Mash Water Volume' in recipe_config:
        mash_water_vol = up.convert(recipe_config['Mash Water Volume'], 'gallons')
        smowv = total_water - mash_water_vol
        sparge_mash_out_water_vol = '{0:.06f} gallons'.format(smowv)
        recipe_config['Sparge and Mash-out Water Volume'] = sparge_mash_out_water_vol
        msg = 'Total Water: {0:.01f} gallons'
        print(msg.format(total_water))
    else:
        msg = 'Mash Water Volume not specified.'
        msg += ' Try running malt_composition first.'
        raise ValueError(msg)

    if 'Original Gravity' in recipe_config:
        og = recipe_config['Original Gravity']
        gp = specific_gravity_to_gravity_points(og, pitchable_volume)
        sg = gravity_points_to_specific_gravity(gp, pre_boil_volume)
        recipe_config['Pre-Boil Gravity'] = sg
        sg = gravity_points_to_specific_gravity(gp, average_boil_volume)
        recipe_config['Average Gravity'] = sg
        msg = 'Pre-Boil Gravity: {0:.03f}'
        print(msg.format(recipe_config['Pre-Boil Gravity']))
    else:
        msg = 'Original Gravity not specified.'
        msg += ' Try running malt_composition first.'
        raise ValueError(msg)

    print('')
    return config, recipe_config


def salt_additions(config, recipe_config):
    """Determines what salts (if any) to use.

    Note: required parameters are in either config or
    recipe_config. Where applicable, if a parameter is specified in
    both config and recipe_config, the latter overrides the former.

    Parameters
    ----------
     'Water Profile' : dict
        Dictionary specifying the desired water profile, in terms of
        the ppm of various minerals: calcium, magnesium, sulfate,
        sodium, chloride, as well as the alkalinity of the water,
        which can either be specified directly, or in terms of the
        carbonate content.
     'Mash Water Volume' : string
        Amount of mash water needed, in gallons. Output from
        malt_composition.
     'Sparge and Mash-out Water Volume' : string
        String representing the total water needed for mashing-out and
        sparging.

    Returns
    -------
     This function appends fields (documented below) to recipe_config
     and returns both config (unmodified) and recipe_config. It also
     prints how much of each salt to add to the mash, and to the
     sparge/mash-out water. It also shows whether the achieved water
     profile is conducive to highlighting malty or hoppy flavors.

    Fields Appended to recipe_config
    --------------------------------
     'Water' : dict
        Collection of key-value pairs describing the recommended water
        content. Currently, it is hard-coded to recommend 100%
        distilled or Reverse-Osmosis (RO) water, but it might be
        better to permit the user to describe their own tap water
        profile which is often cheaper and just as good as starting
        from distilled.
     'Salts' : dict
        Specifies amount of each salt to be added, in units of grams
        per gallon.
     'Water Profile Achieved' : dict
        Collection of key-value pairs showing the achieved water
        profile.

    Notes
    -----
     This function uses cvxpy to solve a convex optimization problem
     minimizing the discrepancy between the desired water profile and
     that achieved by various salt additions. Various constraints
     embody the recommendations of John Palmer in his Water book.

    """

    up = config['unit_parser']
    A, target_composition, rac = get_targets(config, recipe_config)
    num_minerals, num_ingredients = A.shape

    ingredients = ['Distilled water',
                   'Food-grade Chalk',
                   'Baking Soda',
                   'Gypsum',
                   'Epsom Salt',
                   'Calcium Chloride',
                   'Magnesium Chloride',
                   'Table Salt']

    minerals = ['Calcium',
                'Magnesium',
                'Sulfate',
                'Sodium',
                'Chloride',
                'Total Alkalinity']

    target_rac = rac.dot(target_composition)
    w = cvx.Variable(num_ingredients)
    r = cvx.Variable(num_minerals)
    b = np.array([10, 1, 5, 0.001, 5, 10])
    complexity_penalty = 1.0

    obj = cvx.norm(cvx.mul_elemwise(b, r - target_composition))
    obj += complexity_penalty * cvx.norm(w[1:], 1)

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

    w = w.value.A.squeeze()
    # If the optimal water profile calls for less than 0.1 grams of a
    # particular salt, just skip it.
    w[w < 0.1] = 0
    r = A.dot(w)

    recipe_config['Water'] = {'distilled': 1.0}
    print('100% distilled water')

    recipe_config['Salts'] = {}
    for i in range(1, num_ingredients):
        if w[i] > 0:
            salt_amount = '{0:.04f} grams_per_gallon'.format(w[i])
            recipe_config['Salts'][ingredients[i]] = salt_amount
            print('{0:.04f} grams per gallon {1:s}'.format(w[i], ingredients[i]))

    if 'Mash Water Volume' in recipe_config:
        print('')
        mash_water_vol = up.convert(recipe_config['Mash Water Volume'], 'gallons')
        for i in range(1, num_ingredients):
            if w[i] > 0:
                print('{0:.02f} grams {1:s} in mash'.format(w[i] * mash_water_vol, ingredients[i]))

    if 'Lactic Acid' in recipe_config:
        lactic_tsp = up.convert(recipe_config['Lactic Acid'], 'tsp')
        print('{0:.2f} tsp lactic acid in mash'.format(lactic_tsp))

    if 'Sparge and Mash-out Water Volume' in recipe_config:
        print('')
        smowv = recipe_config['Sparge and Mash-out Water Volume']
        smowv = up.convert(smowv, 'gallons')
        for i in range(1, num_ingredients):
            if w[i] > 0:
                msg = '{0:.02f} grams {1:s} in sparge/mash-out water'
                print(msg.format(w[i] * smowv, ingredients[i]))

    print('')
    recipe_config['Water Profile Achieved'] = {}
    for i in range(num_minerals):
        recipe_config['Water Profile Achieved'][minerals[i]] = r[i]
        print('{0:.1f} ppm {1:s}'.format(r[i], minerals[i]))

    recipe_config['Water Profile Achieved']['Residual Alkalinity'] = rac.dot(r)
    print('Residual alkalinity: {0:.0f}'.format(rac.dot(r)))

    if (r[4] / r[2] < 0.5):
        descriptor = 'very hoppy'
    elif (r[4] / r[2] < 1.0):
        descriptor = 'hoppy'
    elif (r[4] / r[2] < 2):
        descriptor = 'malty'
    else:
        descriptor = 'very malty'

    recipe_config['Water Profile Achieved']['Chloride to Sulfate Ratio'] = r[4] / r[2]
    print('Chloride to sulfate ratio: {0:.1f} ({1:s})'.format(r[4] / r[2], descriptor))

    config['r'] = r
    return config, recipe_config


def mash_ph(config, recipe_config):
    """Estimates the pH of the mash.

    Note: required parameters are in either config or
    recipe_config. Where applicable, if a parameter is specified in
    both config and recipe_config, the latter overrides the former.

    Parameters
    ----------
     'mmole' : filename
        Location of file specifying the blah blah blah. This parameter
        needs to be a subparameter of the 'files' subparameter of the
        'water' parameter in config.
     'Malt' : array_like
        Array of grist components (not necessarily malted). This is
        the same input as is used in malt_composition. See the
        documentation there. (The only inputs used here are the name
        and mass, which are needed to determine what fraction of the
        grain bill is acidulated malt.)
     'pH reference temperature' : float
        Reference temperature for pH measurements. This parameter
        needs to be a subparameter of the 'water' parameter in config.

    Returns
    -------
     This function appends fields (documented below) to recipe_config
     and returns both config (unmodified) and recipe_config.

    Fields Appended to recipe_config
    --------------------------------
     'Mash pH' : float
        The predicted pH of the mash.
     'pH Reference Temperature' : float
        The reference temperature for the predicted mash pH, in
        degrees Fahrenheit.

    Notes
    -----
     The mash pH is defined implicitly by the balance equation. The
     mash pH is computed via a root-finding algorithm. Basically, we
     guess the mash pH and see if the balance equation holds,
     adjusting the guess until we are right.

    """

    up = config['unit_parser']

    this_dir, this_filename = os.path.split(__file__)
    mmole_config = os.path.join(this_dir, 'resources', config['water']['files']['mmole'])
    data = np.genfromtxt(mmole_config, delimiter=',')

    target_mash_pH = [4.5, 8.5]
    tol = 1e-6
    while (target_mash_pH[1] - target_mash_pH[0] > tol):
        pH = 0.5 * (target_mash_pH[0] + target_mash_pH[1])
        b = balance_eq(pH, data, config, recipe_config)
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

        if 'mass' in m:
            malt_mass += up.convert(m['mass'], 'kilograms')

        if m['name'] == 'Acidulated Malt' and 'mass' in m:
            acidulated_mass += up.convert(m['mass'], 'kilograms')

    acidulated_delta = 100 * 0.1 * acidulated_mass / malt_mass
    pH -= acidulated_delta

    pH_temp = config['water'].get('pH reference temperature', 68)
    pH = convert_pH_temp(pH, 68, pH_temp)
    pH_range_low = convert_pH_temp(5.4, 77, pH_temp)
    pH_range_high = convert_pH_temp(5.7, 77, pH_temp)

    recipe_config['Mash pH'] = pH
    recipe_config['pH Reference Temperature'] = pH_temp
    msg = 'Mash pH: {0:.03f} at {1:.0f} degF (target between'
    msg += ' {2:.03f} and {3:.03f})'
    print(msg.format(pH, pH_temp, pH_range_low, pH_range_high))

    return config, recipe_config


def balance_eq(mash_pH, data, config, recipe_config):
    """Computes the mash pH misbalance.

    Parameters
    ----------
     mash_pH : float
       Candidate mash pH.
     data : array
       Array of data for calculation.


    Returns
    -------
     balance : float
        Value of balance equation. See notes in mash_ph().

    """
    up = config['unit_parser']
    baseline_pH = 4.3

    r = config['r']

    if 'Lactic Acid' in recipe_config:
        lactic_acid_volume = up.convert(recipe_config['Lactic Acid'], 'milliliters')
    else:
        lactic_acid_volume = 0.

    if 'Mash Water Volume' in recipe_config:
        water_volume = up.convert(recipe_config['Mash Water Volume'], 'liters')
    else:
        msg = 'Mash Water Volume not specified.'
        msg += ' Try running malt_composition first.'
        raise ValueError(msg)

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
                msg = 'Buffering capacity required for {0:s}.'
                raise ValueError(msg.format(x['name']))

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
                msg = 'Buffering capacity required for {0:s}.'
                raise ValueError(msg.format(x['name']))

        elif x['name'] in config['malt'] and 'acidity' in config['malt'][x['name']]:
            malt_acidity.append(config['malt'][x['name']]['acidity'])
            malt_dipH.append(0.)
            malt_buffering_capacity.append(0.)
            acids.append(1)

        elif (x['name'] in config['malt'] and 'type' in config['malt'][x['name']]
              and config['malt'][x['name']]['type'] == 'crystal'
              and 'degrees lovibond' in config['malt'][x['name']]):

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

        if 'mass' in x:
            malt_mass.append(up.convert(x['mass'], 'kilograms'))
        else:
            malt_mass.append(0.)

    malt_dipH = np.array(malt_dipH)
    malt_buffering_capacity = np.array(malt_buffering_capacity)
    malt_acidity = np.array(malt_acidity)
    acids = np.array(acids)
    malt_mass = np.array(malt_mass)

    charge_per_mmole = interpolate.interp1d(data[:, 0], data[:, 1])

    total_alkalinity = (r[5] - (100 / 0.17) * lactic_acid_volume / water_volume) / 50 # mEq / L
    delta_c0 = charge_per_mmole(baseline_pH) - charge_per_mmole(brewing_water_pH)
    delta_cz = charge_per_mmole(mash_pH) - charge_per_mmole(brewing_water_pH)

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


def get_targets(config, recipe_config):
    """Get water information.

    Note: required parameters are in either config or
    recipe_config. Where applicable, if a parameter is specified in
    both config and recipe_config, the latter overrides the former.

    Parameters
    ----------
     'water' : array_like
        Array of candidate water sources, e.g. distilled vs. tap
        water. Permits the user to specify different water sources,
        and this script will determine what blend to use. Each water
        source must specify its mineral contents via a collection of
        key-value pairs, with key the name of the mineral (one of:
          calcium
          magnesium
          sulfate
          sodium
          chloride
          alkalinity
          carbonate (different way of specifying alkalinity)
        ) and value the parts-per-million concentration.
     'Water Profile' : dictionary
        Collection of key-value pairs specifying the desired mineral
        levels for brewing, in parts-per-million. This parameter needs
        to be a top-level parameter of recipe_config.
     'salts' : array_like
        Array of salts. This shouldn't be an input, it should just be
        hard-coded.
     'Residual Alkalinity' : array_like
        Array of coefficients for residual alkalinity
        calculation. This shouldn't be an input, it should just be
        hard-coded.

    Returns
    -------
     A : 2d array
       Design matrix for optimization problem. The columns correspond
       to the available ingredients, and the rows to the mineral
       content.
     target_composition : array
       Array of desired mineral content.
     rac : array
       Coefficients for residual alkalinity calculation.

    """

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
    main()
