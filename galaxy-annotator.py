#!/usr/bin/env python
import sys
import os.path
import math
import json

galaxies_json = sys.argv[1]
style_json = sys.argv[2]
wcs_fits = sys.argv[3]
image_file = sys.argv[4]
out_file = sys.argv[5]

with open(galaxies_json, 'r', encoding='utf-8') as f:
    galaxies = json.load(f)

SVG_LENGTH_PROPS = [ 'baseline-shift', 'font-size', 'kerning', 'letter-spacing',
                     'stroke-dashoffset', 'stroke-width', 'stroke-width',
                     'word-spacing' ]

non_svg_marker_style_defaults = {
    'size': 1.5,
    'min-size': None,
    'min-r': 15,
    'min-size-r': None,
    'x-margin': 4,
    'y-margin': 0,
    'label-position': 'top-right',
    'label-vertical-align': 'baseline'
}
style = {
    'marker': {
        'fill': 'none',
        'stroke': 'gray',
        'stroke-width': 1
    },
    'name': {
        'font-size': 40,
        'fill': 'gray'
    },
    'desc': [
        {
            'font-size': 40,
            'fill': 'gray'
        }
    ]
}
style['marker'].update(non_svg_marker_style_defaults)
with open(style_json, 'r', encoding='utf-8') as f:
    in_style = json.load(f)
    for key in iter(style):
        if type(style[key]) == dict:
            if key in in_style:
                style[key].update(in_style[key]) 
        elif type(style[key]) == list:
            for i, e in enumerate(in_style[key]):
                if len(style[key]) > i:
                    style[key][i].update(e)
                else:
                    style[key].append(e)
                    
def s_to_ss(selector, s):
    ss = selector + ' {\n'
    for prop in s:
        if prop in non_svg_marker_style_defaults:
            continue
        v = s[prop]
        ss += "  " + prop + ": "
        if (type(v) == int or type(v) == float) and prop in SVG_LENGTH_PROPS:
            ss += "{}px".format(v)
        elif type(v) == str and prop == 'font-family':
            ss += '\"{}\"'.format(v)
        else:
            ss += str(v)
        ss += ';\n'
    ss += '}\n'
    return ss

if not (type(style['name']['font-size']) == int or
        type(style['name']['font-size']) == float):
    print('{}: ERROR: "font-size" of "name" '\
          'must be of numeric type.'.format(style_json), file=sys.stderr)
    sys.exit()
for i, desc in enumerate(style['desc']):
    if not (type(desc['font-size']) == int or type(desc['font-size']) == float):
        print('{}: ERROR: "font-size" of "desc"[{}] must be of '\
              'numeric type.'.format(style_json, i), file=sys.stderr)
        sys.exit()

style_sheet = "\n"
style_sheet += s_to_ss('ellipse.marker', style['marker'])
style_sheet += s_to_ss('text.name', style['name'])
for i, desc in enumerate(style['desc']):
    style_sheet += s_to_ss('text.desc{}'.format(i), desc)

if out_file and os.path.exists(out_file):
    input = input("output file '" + out_file + "' exists. overwrite? > ")
    if input.upper() != 'YES':
        print('bye.')
        sys.exit()

import base64
import svgwrite
from astropy import units as u
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord

hdu = fits.open(wcs_fits)[0]
w = WCS(hdu.header, fix=False)
image_w = hdu.header['IMAGEW']
image_h = hdu.header['IMAGEH']

sky_left = w.pixel_to_world(0, 0)
sky_right = w.pixel_to_world(image_w, 0)
sky_right2 = SkyCoord(ra=sky_right.ra, dec=sky_left.dec)
x2, y2 = w.world_to_pixel(sky_right2)
image_tilt = math.degrees(math.atan(y2 / x2))
print('tilt=', image_tilt)
scales = w.proj_plane_pixel_scales()
px_scale = (scales[0].to_value(unit=u.deg) + scales[1].to_value(unit=u.deg)) / 2
print('scale=', px_scale)

marker_size = float(style['marker']['size'])
drw = svgwrite.Drawing(out_file, size=(image_w, image_h))
drw.add(drw.style(style_sheet))

#TBD: select embed or link by option.
embed_image = True
if embed_image:
    with open(image_file, 'rb') as f:
        mime = ''
        if image_file.upper().endswith('.JPG'):
            mime = 'image/jpeg'
        elif image_file.upper().endswith('.PNG'):
            mime = 'image/png'
        image_data = 'data:' + mime + ';base64,'
        image_data += base64.standard_b64encode(f.read()).decode()
    drw.add(drw.image(image_data))
else:
    drw.add(drw.image(image_file))

for gal in galaxies['galaxies']:
    sky = SkyCoord(ra=float(gal['al2000']), dec=float(gal['de2000']),
                   unit=(u.hourangle, u.deg))
    x, y = w.world_to_pixel(sky)
    if x < 0 or y < 0 or x > image_w or y > image_h:
        continue
    
    svg_group = drw.g()
    drw.add(svg_group)
    gal_name = gal['name']
    print("{name}: ({x}, {y})".format(name=gal_name, x=x, y=y))
    gal_pa = float(gal['pa']) if gal['pa'] else 0.0
    gal_d = 10 ** float(gal['logd25']) / 10 / 60 if gal['logd25'] else None
    gal_r = 10 ** float(gal['logr25']) if gal['logr25'] else 1.0
    
    marker_rot = -1.0 * (gal_pa - image_tilt)
    marker_min_r = style['marker']['min-r']
    marker_min_size_r = style['marker']['min-size-r'] or (marker_min_r + 1)
    marker_min_size = style['marker']['min-size'] or marker_size
    
    if gal_d:
        gal_ry = gal_d / 2 / px_scale
        sz = (gal_ry - marker_min_r) * (marker_min_size - marker_size) / \
             (marker_min_size_r - marker_min_r) + marker_size
        marker_ry = max(gal_ry * max(sz, marker_min_size), marker_min_r)
    else:
        marker_ry = marker_min_r

    marker_rx = marker_ry / gal_r
    print("  d={d}".format(d=gal_d))
    print("  marker: ({rx} x {ry}), rot={rot}".format(rx=marker_rx,
                                                      ry=marker_ry,
                                                      rot=marker_rot))
    transform = "rotate({rot}, {x}, {y})".format(rot=marker_rot, x=x, y=y)
    svg_group.add(drw.ellipse(center=(float(x), float(y)),
                              r=(marker_rx, marker_ry),
                              transform=transform, class_='marker'))
    th = math.radians(marker_rot)
    dx = math.sqrt(marker_rx**2 * math.cos(th)**2 +
                   marker_ry**2 * math.sin(th)**2)
    dy = math.sqrt(marker_rx**2 * math.sin(th)**2 +
                   marker_ry**2 * math.cos(th)**2)
    name_x = x + dx + float(style['marker']['x-margin'])
    name_y = y - dy - float(style['marker']['y-margin'])
    print("  name: ({x}, {y})".format(x=name_x, y=name_y))
    svg_group.add(drw.text(gal_name, x=[name_x], y=[name_y], class_='name'))
    desc_x = name_x
    desc_y = name_y
    for i, desc in enumerate(gal['descs']):
        desc_y += float(style['desc'][i]['font-size'])
        print("  desc[{i}]: ({x}, {y})".format(i=i, x=desc_x, y=desc_y))
        svg_group.add(drw.text(desc, x=[desc_x], y=[desc_y],
                               class_='desc'+str(i)))
drw.save(pretty=True)
