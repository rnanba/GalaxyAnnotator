#!/usr/bin/env python
import sys
from argparse import ArgumentParser

argparser = ArgumentParser(description='Get data of galaxies in the '\
                           'field of view from HyperLeda.')
argparser.add_argument('wcs_fits', metavar='input_wcs.fits',
                       help="input file (the 'wcs.fits' file output by '\
                       'astrometry.net).")
argparser.add_argument('votable_xml', metavar='output_votable.xml', nargs='?',
                       help="output file (data of galaxies from HyperLeda in '\
                       'VOTABLE format). if omitted, output to stndard output.")
argparser.add_argument("-f", "--force-overwrite", action="store_true",
                       help="force overwriting to output file.")
args = argparser.parse_args()
if not args.wcs_fits:
    argparser.print_help(sys.stderr)
    exit(1)
if args.votable_xml:
    import os.path
    if (not args.force_overwrite) and os.path.exists(args.votable_xml):
        input = input("output file '" + args.votable_xml +
                      "' exists. overwrite? > ")
        if input.upper() != 'YES':
            print('bye.')
            sys.exit()

import json
import urllib.request
from astropy import units as u
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord

hdu = fits.open(args.wcs_fits)[0]
w = WCS(hdu.header, fix=False)
image_w = hdu.header['IMAGEW']
image_h = hdu.header['IMAGEH']

sky_top_left = w.pixel_to_world(0, 0)
sky_top_right = w.pixel_to_world(image_w, 0)
sky_bottom_left = w.pixel_to_world(0, image_h)
sky_bottom_right = w.pixel_to_world(image_w, image_h)

ra_min = min(sky_top_left.ra.hour, sky_top_right.ra.hour,
             sky_bottom_left.ra.hour, sky_bottom_right.ra.hour)
ra_max = max(sky_top_left.ra.hour, sky_top_right.ra.hour,
             sky_bottom_left.ra.hour, sky_bottom_right.ra.hour)
dec_min = min(sky_top_left.dec.degree, sky_top_right.dec.degree,
              sky_bottom_left.dec.degree, sky_bottom_right.dec.degree)
dec_max = max(sky_top_left.dec.degree, sky_top_right.dec.degree,
              sky_bottom_left.dec.degree, sky_bottom_right.dec.degree)

where = "al2000<{ra_max} and al2000>{ra_min} and de2000<{dec_max} and de2000>{dec_min} and objtype='G'".format(ra_min=ra_min, ra_max=ra_max, dec_min=dec_min, dec_max=dec_max)
#print(where)
# leda = 'http://leda.univ-lyon1.fr/fG.cgi'
leda = 'http://atlas.obs-hp.fr/hyperleda/fG.cgi' # mirror
# http://atlas.obs-hp.fr/hyperleda/fG.cgi?n=meandata&c=o&of=1,leda,simbad&nra=l&nakd=1&sql=al2000%3C12.965687916818412%20and%20al2000%3E12.925228843825312%20and%20de2000%3C21.871941710192353%20and%20de2000%3E21.491211008587133%20and%20objtype%3D%27G%27&ob=&a=x
query = urllib.parse.urlencode({
    'n': 'meandata',
    'c': 'o',
    'of': '1,leda,simbad',
    'nra': 'l',
    'nakd': '1',
    'sql': where,
    'ob': '',
    'a': 'x'
})
req = urllib.request.Request("{leda}?{query}".format(leda=leda, query=query))
with urllib.request.urlopen(req) as res:
    if args.votable_xml:
        with open(args.votable_xml, 'wb') as out:
            out.write(res.read())
    else:
        sys.stdout.buffer.write(res.read())
