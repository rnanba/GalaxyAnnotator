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
argparser.add_argument("-m", "--max-magnitude", dest="max_mag", type=float,
                       help="maximum total magnitude(it,vt,bt)", metavar="MAG")
argparser.add_argument("-f", "--force-overwrite", action="store_true",
                       help="force overwriting to output file.")
argparser.add_argument("--dry-run", dest="dryrun", action="store_true",
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
sky_center = w.pixel_to_world(image_w/2, image_h/2)

def hit_test(x, y):
    return (x >= 0 and x < image_w) and (y >= 0 and y < image_h)

def ra_min_max(ra_left, ra_right):
    # 写野に極が入らないと仮定
    # センターを挟んで対角線を辿って前後のRAの差の符号が食い違うなら
    if ((ra_left > sky_center.ra.hour) ^ (sky_center.ra.hour > ra_right)):
        # 0h をまたいでいるので大きい方のRAから24h引いてマイナスにする
        ra_min = max(ra_left, ra_right) - 24
        ra_max = min(ra_left, ra_right)
    else:
        ra_max = max(ra_left, ra_right)
        ra_min = min(ra_left, ra_right)
    return ra_min, ra_max

ra_min = None
ra_max = None
dec_min = None
dec_max = None

import warnings
warnings.filterwarnings('ignore', category=RuntimeWarning)
warnings.filterwarnings('ignore', category=UserWarning)
px, py = w.world_to_pixel(SkyCoord(0*u.hour, 90.0*u.deg))
spx, spy = w.world_to_pixel(SkyCoord(0*u.hour, -90.0*u.deg))
warnings.filterwarnings('default', category=RuntimeWarning)
warnings.filterwarnings('default', category=UserWarning)

if hit_test(px, py):
    # 写野に天の北極がある場合
    dec_min = min(sky_top_left.dec.degree, sky_top_right.dec.degree,
                  sky_bottom_left.dec.degree, sky_bottom_right.dec.degree)
    dec_max = 90.0
    ra_min = 0.0
    ra_max = 24.0
elif hit_test(spx, spy):
    # 写野に天の南極がある場合
    dec_min = -90.0
    dec_max = max(sky_top_left.dec.degree, sky_top_right.dec.degree,
                  sky_bottom_left.dec.degree, sky_bottom_right.dec.degree)
    ra_min = 0.0
    ra_max = 24.0
else:    
    ra_min1, ra_max1 = ra_min_max(sky_top_left.ra.hour, sky_bottom_right.ra.hour)
    ra_min2, ra_max2 = ra_min_max(sky_bottom_left.ra.hour, sky_top_right.ra.hour)
    ra_min = min(ra_min1, ra_min2)
    ra_max = max(ra_max1, ra_max2)
    dec_min = min(sky_top_left.dec.degree, sky_top_right.dec.degree,
                  sky_bottom_left.dec.degree, sky_bottom_right.dec.degree)
    dec_max = max(sky_top_left.dec.degree, sky_top_right.dec.degree,
                  sky_bottom_left.dec.degree, sky_bottom_right.dec.degree)

mag_where = ""
if args.max_mag:
    mm = args.max_mag
    mag_where = f"and (it<={mm} or vt<={mm} or bt<={mm})"

where = f"al2000<{ra_max} and al2000>{ra_min} and de2000<{dec_max} and de2000>{dec_min} and objtype='G' {mag_where}"

if args.dryrun:
    print(f"WHERE {where}")
    exit(0)

select = "pgc,objname,objtype,al1950,de1950,al2000,de2000,l2,b2,sgl,sgb,f_astrom,type,bar,ring,multiple,compactness,t,e_t,agnclass,logd25,e_logd25,logr25,e_logr25,pa,brief,e_brief,ut,e_ut,bt,e_bt,vt,e_vt,it,e_it,kt,e_kt,m21,e_m21,mfir,ube,bve,vmaxg,e_vmaxg,vmaxs,e_vmaxs,vdis,e_vdis,vrad,e_vrad,vopt,e_vopt,v,e_v,ag,ai,incl,a21,logdc,btc,itc,ubtc,bvtc,bri25,vrot,e_vrot,mg2,e_mg2,m21c,hic,vlg,vgsr,vvir,v3k,modz,e_modz,mod0,e_mod0,modbest,e_modbest,mabs,e_mabs,hl_names(pgc)"

# leda = 'http://leda.univ-lyon1.fr/fG.cgi'
leda = 'http://atlas.obs-hp.fr/hyperleda/fG.cgi' # mirror
# http://atlas.obs-hp.fr/hyperleda/fG.cgi?n=meandata&c=o&of=1,leda,simbad&nra=l&nakd=1&sql=al2000%3C12.965687916818412%20and%20al2000%3E12.925228843825312%20and%20de2000%3C21.871941710192353%20and%20de2000%3E21.491211008587133%20and%20objtype%3D%27G%27&ob=&a=x
query = urllib.parse.urlencode({
    'n': 'meandata',
    'c': 'o',
    'of': '1,leda,simbad',
    'nra': 'l',
    'nakd': '1',
    'd': select,
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
