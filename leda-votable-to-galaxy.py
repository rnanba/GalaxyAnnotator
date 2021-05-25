#!/usr/bin/env python
import sys
from argparse import ArgumentParser

def float_or_none(v):
    return float(v) if v else None

argparser = ArgumentParser(description='Convert votable.xml to galaxies.json '\
                           "for 'galaxy-annotator.py'.")
argparser.add_argument('votable_xml', metavar='input_votable.xml',
                       help="input file (data of galaxies from HyperLeda in '\
                       'VOTABLE format).")
argparser.add_argument('galaxies_json', metavar='output_galaxies.json', nargs='?',
                       help="output file (annotation data for "\
                       " 'galaxy-annotator.py'). if omitted, output to stndard "\
                       "output.")
argparser.add_argument("-f", "--force-overwrite", action="store_true",
                       help="force overwriting to output file.")
argparser.add_argument("-m", "--max-magnitude", dest="max_mag", type=float,
                       help="maximum total magnitude(it,vt,bt)", metavar="MAG")
argparser.add_argument("-s", "--skip-error", dest="skip_error",
                       action="store_true", default=False,
                       help="skip objects on error.")
argparser.add_argument("-i", "--ignore-error", dest="ignore_error",
                       action="store_true", default=False,
                       help="ignore error and process objects.")
argparser.add_argument("-d", "--calc-distance", dest="calc_distance",
                       action='store_true', default=False,
                       help="calcurate light-travel distance and output.")
argparser.add_argument("-j", "--japanese", dest="japanese",
                       action='store_true', default=False,
                       help="output distance in Japanese.")
args = argparser.parse_args()
if not args.votable_xml:
    argparser.print_help(sys.stderr)
    exit(1)
if args.galaxies_json:
    import os.path
    if (not args.force_overwrite) and os.path.exists(args.galaxies_json):
        input = input("output file '" + args.galaxies_json +
                      "' exists. overwrite? > ")
        if input.upper() != 'YES':
            print('bye.')
            sys.exit()

import json
import math
import xml.etree.ElementTree as et
from argparse import ArgumentParser
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN

if args.calc_distance:
    from astropy import units as u
    from astropy.cosmology import LambdaCDM
    cosmo = LambdaCDM(H0=67.3, Om0=0.315, Ode0=0.685)

root = et.parse(args.votable_xml).getroot()
fields = list(map(lambda f: f.attrib['name'],
                  root.findall('./RESOURCE/TABLE/FIELD')))
galaxies = []
for tr in root.findall('./RESOURCE/TABLE/DATA/TABLEDATA/TR'):
    rec = {}
    descs = []
    for i, f in enumerate(tr.findall('./TD')):
        rec[fields[i]] = f.text
    it = rec['it']
    if args.max_mag:
        if it == None:
            it = rec['vt']
        if it == None:
            it = rec['bt']
        if it == None:
            if args.skip_error:
                continue
            elif args.ignore_error:
                it = -100.0
            else:
                print("no magnitude data for '{}'.".format(rec['objname']))
                exit()
        if float(it) > args.max_mag:
            continue
    ltd_Gly = None
    if args.calc_distance and rec['v']:
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
        if args.japanese:
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
output = json.dumps({ "galaxies": galaxies }, indent=2, ensure_ascii=False)
if args.galaxies_json:
    with open(args.galaxies_json, 'w', encoding='utf-8') as out:
        out.write(output)
else:
    print(output)
