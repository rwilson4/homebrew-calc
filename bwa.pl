#!/usr/bin/perl

use constant QUARTS_PER_GALLON => 4;
use constant CUPS_PER_QUART => 4;
use constant MASH_TUN_THERMAL_MASS => 1845.32957; # cal/degK
use constant LITERS_PER_QUART => 1.05669;
use constant DENSITY_OF_WATER => 1; # Liters per kg

if ($#ARGV < 3 || $ARGV[0] eq "-h") {
    print "Usage: ./bwa.pl lbsOfGrain qtsPerLB targetStrike ambientTemp\n";
    print "Usage: ./bwa.pl 9.75 1.5 149 72\n";
    exit;
}

$lbsOfGrain = $ARGV[0];
$qtsPerLB = $ARGV[1];
$targetTemp = $ARGV[2];
$ambientTemp = $ARGV[3];

$strikeWaterTemp = (0.2 / $qtsPerLB)*($targetTemp - $ambientTemp) + $targetTemp;

$qtsWater = $lbsOfGrain * $qtsPerLB;
$qtsSpargeWater = 1.5 * $qtsWater;

$tempLoss = &mashTunCorrection($qtsWater, $strikeWaterTemp, $ambientTemp);
$strikeWaterTemp += $tempLoss;

$spargeWaterTemp = 170;
$spargeTempLoss = &mashTunCorrection($qtsSpargeWater, $spargeWaterTemp, $ambientTemp);
$spargeWaterTemp += $spargeTempLoss;

($gallonsWater, $qtsWater, $cupsWater) = &qtsToGQC($qtsWater);
($gallonsSpargeWater, $qtsSpargeWater, $cupsSpargeWater) = &qtsToGQC($qtsSpargeWater);

printf "Amount of mash water: %d gallons %d quarts %0.1f cups\n", $gallonsWater, $qtsWater, $cupsWater;
printf "Strike water temp: %0.1fF (will lose ~%0.1f degrees to achieve %.1fF) \n", $strikeWaterTemp, $tempLoss, ($strikeWaterTemp - $tempLoss);
printf "Amount of sparge water (at %.1fF): %d gallons %d quarts %0.1f cups\n", $spargeWaterTemp, $gallonsSpargeWater, $qtsSpargeWater, $cupsSpargeWater;

# 192 -> 179

# mT*cT*64 + mW*cW*192 = (mT*cT + mW*CW)*179
# mW = 16.3246 kg
# cW = 1 cal/gm/degK = 1000 cal/kg/degK
# x*(290.928degK) + (16324.6 cal/degK)*(362.039degK) = (x + 16324.6 cal/degK)*(354.817degK)
# x*(354.817 - 290.928)degK = 16324.6 cal/degK * (362.039 - 354.817) degK
# x = 1845.32957473 cal / degK

# x*64 + mW*cW*Y = (x + mW*cW)*T
# mW*cW*Y = x*(T - 64) + mW*cW*T
# Y = (x/(mW*cW)) * (T - 64) + T

sub qtsToGQC {
    my $qts = shift;
    my $gal = int($qts / QUARTS_PER_GALLON);
    $qts -= $gal * QUARTS_PER_GALLON;
    my $cups = $qts * CUPS_PER_QUART;
    $qts = int($qts);
    $cups -= $qts * CUPS_PER_QUART;

    return ($gal, $qts, $cups);
}

sub qtsWaterToKG {
    my $qts = shift;
    my $ltrs = $qts * LITERS_PER_QUART;
    my $kg = $ltrs * DENSITY_OF_WATER;
    return $kg
}

sub mashTunCorrection {
    my $qts = shift;
    my $strikeTemp = shift;
    my $ambientTemp = shift;

    my $mW = &qtsWaterToKG($qts);
    my $tempCorrection = ($strikeTemp - $ambientTemp) * MASH_TUN_THERMAL_MASS / ($mW * 1000);
}
