#!/usr/bin/python

def convert_pH_temp(pH, original_temperature, desired_temperature):
    return pH - 0.003 * (desired_temperature - original_temperature)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('pH', type=float, help='pH')
    parser.add_argument('original_temperature', type=float, help='Temperature associated with given pH measurement (in Fahrenheit)')
    parser.add_argument('desired_temperature', type=float, help='Desired temperature for pH measurement (in Fahrenheit)')

    args = parser.parse_args()
    pH = convert_pH_temp(args.pH, args.original_temperature, args.desired_temperature)
    print '{0:.03f}'.format(pH)
