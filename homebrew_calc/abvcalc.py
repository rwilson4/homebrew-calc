from __future__ import print_function
from yeast_composition import abv_calc, attenuation


def execute():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('og', type=float, help='Original Gravity')
    parser.add_argument('fg', type=float, help='Final Gravity')

    args = parser.parse_args()
    abv = 100. * abv_calc(args.og, args.fg)
    att = 100.0 * attenuation(args.og, args.fg)
    print('{0:.02f}% ABV'.format(abv))
    print('{0:.0f}% Attenuation'.format(att))


if __name__ == '__main__':
    execute()
