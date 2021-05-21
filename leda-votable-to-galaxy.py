#!/usr/bin/env python
import sys
import json
import math
import xml.etree.ElementTree as et
from optparse import OptionParser
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN

def float_or_none(v):
    return float(v) if v else None

usage = "Usage: %prog [options] votable_xml_file"
optparser = OptionParser(usage=usage)
optparser.add_option("-m", "--max-magnitude", dest="max_mag", type='float',
                     help="maximum total magnitude(it)", metavar="MAG")
optparser.add_option("-d", "--calc-distance", dest="calc_distance",
                     action='store_true', default=False,
                     help="calicurate light-travel distance.")
optparser.add_option("-j", "--japanese", dest="japanese",
                     action='store_true', default=False,
                     help="distance in Japanese.")
(options, args) = optparser.parse_args(sys.argv)

if options.calc_distance:
    from astropy import units as u
    from astropy.cosmology import LambdaCDM
    cosmo = LambdaCDM(H0=67.3, Om0=0.315, Ode0=0.685)

root = et.parse(args[1]).getroot()
fields = list(map(lambda f: f.attrib['name'],
                  root.findall('./RESOURCE/TABLE/FIELD')))
galaxies = []
for tr in root.findall('./RESOURCE/TABLE/DATA/TABLEDATA/TR'):
    rec = {}
    descs = []
    for i, f in enumerate(tr.findall('./TD')):
        rec[fields[i]] = f.text
    it = rec['it']
    if options.max_mag:
        if it == None:
            it = rec['vt']
        if float(it) > options.max_mag:
            continue
    ltd_Gly = None
    if options.calc_distance and rec['v']:
        z = [ float(rec['v']) / 299792.458 ]
        d = cosmo.lookback_distance(z)
        ltd_Gly = d[0].to(u.lyr).value / 1000000000.0
        ltd_en_str = str(Decimal(ltd_Gly).quantize(Decimal('0.001'),
                                                   rounding=ROUND_HALF_UP))
        ltd_en_str += ' Gly'
        # japanese
        ltd_oku_kounen = ltd_Gly * 10
        ltd_ja_str = ''
        oku = math.floor(ltd_oku_kounen)
        if oku > 0:
            ltd_ja_str += str(oku) + '億'
        man = 10000 * Decimal(str(ltd_oku_kounen - oku)).quantize(Decimal('0.01'),
                                                          rounding=ROUND_HALF_UP)
        if int(man) >= 100:
            ltd_ja_str += str(math.floor(man)) + '万'
        ltd_ja_str += '光年'
        if options.japanese:
            descs.append(ltd_ja_str)
        else:
            descs.append(ltd_en_str)

    name = rec['objname']
    if (not (name.startswith('PGC') or
             name.startswith('NGC') or
             name.startswith('IC') or
             name.startswith('M'))):
        name += "(PGC" + rec['pgc'] + ")"
    
    galaxies.append({
        "name": name,
        "al2000": float(rec['al2000']),
        "de2000": float(rec['de2000']),
        "pa": float_or_none(rec['pa']),
        "logd25": float_or_none(rec['logd25']),
        "logr25": float_or_none(rec['logr25']),
        "descs": descs
    })
print(json.dumps({ "galaxies": galaxies }, indent=2))

