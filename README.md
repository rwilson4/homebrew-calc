# homebrew-calc

<table>
<tr>
  <td>Build Status</td>
  <td>
    <a href="https://travis-ci.org/rwilson4/homebrew-calc">
    <img src="https://travis-ci.org/rwilson4/homebrew-calc.svg?branch=master&label=Travis%20CI" alt="travis build status" />
    </a>
  </td>
</tr>
<tr>
  <td>Code Coverage</td>
  <td>
    <a href="https://codecov.io/gh/rwilson4/homebrew-calc">
    <img src="https://codecov.io/gh/rwilson4/homebrew-calc/branch/master/graph/badge.svg" />
    </a>
  </td>
</tr>
</table>

This is a collection of utilities for planning and executing beer
recipes. It takes recipes in JSON form, and predicts the Original
Gravity (OG), the beer color in terms of the Standard Reference Method
(SRM), the bitterness in terms of International Bitterness Units
(IBU), and the final Alcohol by Volume (ABV) level. It also calculates
the minerals that should be added to the mash in order to achieve a
desired water profile, and estimates the pH of the mash. And if that's
not enough, it also performs several helpful calculations relevant to
brew day, like strike water temperature calculations, and computing
mash efficiency. All that for the low-low-price of (you have to do
everything via the command line)!

## Installation
Clone this repository on your local machine, cd to the appropriate
folder, and type "pip install ."

## Usage
Perhaps the best way of illustrating its use is through example. The
following recipe is what I brewed for my wedding. It is in the style
of a Southern English Brown Ale, which is a bit sweet, nutty, and very
malty. Although I brewed 15 gallons total, my equipment can only
handle 5 gallon batches, which is reflected below.

For those new to brewing, you may wonder how I came up with the
recipe. I started with a recipe from "Brewing Classic Styles" by Jamil
Zainasheff and John Palmer. I made a few modifications to suit my
individual tastes, but often I just take recipes verbatim and only use
these calculators to help me carry out the brew. I will assume the
readers are broadly familiar with the brewing process.

In the words of Charlie Papazian, let's cut the shuck and jive and get
on with the recipe! (To follow along, the recipe is included in the
examples folder.)
```
{
  "Pitchable Volume": "5.25 gallons",
  "Malt": [
    {
      "name": "Maris Otter",
      "mass": "6.5 pounds"
    },
    {
      "name": "Victory Malt",
      "mass": "1.5 pounds",
      "type": "roast",
      "acidity": 40.0,
      "extract potential": 0.75,
      "degrees lovibond": 19.0
    },
    {
      "name": "Pale Chocolate",
      "mass": "10 ounces",
      "type": "roast",
      "acidity": 40.0,
      "extract potential": 0.71,
      "degrees lovibond": 200.0
    },
    {
      "name": "Dehusked Carafa II",
      "mass": "6 ounces",
      "type": "roast",
      "acidity": 40.0,
      "extract potential": 0.70,
      "degrees lovibond": 430
    }
  ],
  "Hops": [
    {
      "name": "EK Goldings",
      "mass": "0.75 ounce",
      "type": "pellets",
      "boil_time": "60 minutes"
    }
  ],
  "Yeast": [
    {
      "name": "WLP002 English Ale",
      "attenuation": 0.8
    }
  ],
  "Mash": {
    "type": "Infusion",
    "temperature": 156,
    "duration": "60 minutes"
  }
}
```
Starting from the top, we see this is a recipe for a 5.25 gallon
batch. This is the amount of wort into which one would pitch yeast. I
typically lose about .25 gallons by the time I get the final product
in the keg, so this volume works for me, but of course you can use
whatever you want. This library leverages my unit_parser library, so
most physical quantities like volumes of water should actually be
specified as a string with a unit of measurement explicitly listed,
like "5.25 gallons". This is broadly true except for temperatures,
since the conversion between Fahrenheit and Celsius is more
complicated than just multiplying by a number. Perhaps confusingly,
temperature deltas *are* specified with the unit attached, since a
temperature difference of 5 degrees Fahrenheit *is* related to a
corresponding Celsius value by a simple multiplication. Sorry!

Next we see the grain bill (the "Malt" section). We are using Maris
Otter, Victory Malt, Pale Chocolate, and Dehusked Carafa II. In order
to calculate things like Original Gravity, this library needs to know
some information about each grain used. Information corresponding to
many grains is already included in this library, but you can also
explicitly list the relevant information. Basically, every time I use
a new malt, I add it to the library.

Next are the hops used. Like the malt, we list each hop addition
(there is only one in this recipe), specifying the variety, amount,
and what we do with it. "Standard" boiled hops are specified in terms
of how long they are in the boil; first wort, flameout, and dry hops
are also supported.

Then comes the yeast. We simply list the name and attenuation of the
yeast. In its current form, the calculator does not support yeast
starters, mostly because I don't do yeast starters (that's a whole
separate discussion). Finally, we are using a simple infusion mash for
1 hour at 156 degrees Fahrenheit. Although this library features
advanced water chemistry calculations, we are not targeting any
particular water profile in this recipe.

First we run malt_composition:
```sh
$ malt_composition weddingBrown.json -o weddingBrown1.json
```
This does a few things. It tells us that we can expect an OG of about
1.045, and an SRM of 26. It also generates a file weddingBrown1.json
with additional details about the recipe that can be leveraged by
subsequent scripts.

Next we run water_composition:
```sh
$ water_composition weddingBrown1.json -o weddingBrown1.json
```
This tells us exactly how much water we need. I always use distilled
water, which I buy at the grocery store. I round up to the nearest
gallon to give a little margin. It predicts the pre-boil gravity based
on the anticipated mash efficiency. I measure the gravity after
sparging to compute the actual efficiency achieved. If we were
targeting a particular water profile, this command would also perform
the relevant calculations.

Next we run hop_composition:
```sh
$ hop_composition weddingBrown1.json -o weddingBrown1.json
```
This command simply computes the bitterness of the beer.

Next is yeast_composition:
```sh
$ yeast_composition weddingBrown1.json -o weddingBrown1.json
```
This command tells us the number of yeast cells needed, the Final
Gravity, and the ABV. As I mentioned earlier, I don't do yeast
starters, purely out of laziness. I'd rather just buy the appropriate
number of vials of yeast. (I value my time more than I value my
money. Then why do I brew beer? Because brewing beer is fun, and
making starters is not.) There are about 100 billion cells in a vial
of yeast, so the math is easy.

Finally, on brew day:
```sh
$ brew_day weddingBrown1.json -o weddingBrown1.json
```
This command tells me the appropriate temperature to which to heat the
mash water. For example, if I am targeting a mash temperature of 156,
I actually need to heat the water to 185 in the brew kettle since it
will cool down during the transfer. The command is tailored
specifically for my setup and is probably less useful to others. This
command can also be used for step mash calculations.
