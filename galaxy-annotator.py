#!/usr/bin/env python
import sys
import os.path
import math
import json
import copy
import re
from functools import reduce
from argparse import ArgumentParser

argparser = ArgumentParser(description='Convert votable.xml to galaxies.json '\
                           "for 'galaxy-annotator.py'.")
argparser.add_argument('galaxies_json', metavar='galaxies.json',
                       help="annotation data file.")
argparser.add_argument('style_json', metavar='style.json',
                       help="style sttings.")
argparser.add_argument('wcs_fits', metavar='wcs.fits',
                       help="wcs file(output of astrometry.net in FITS format).")
argparser.add_argument('image_file', metavar='image_file',
                       help="image file(input of astrometry.net in image format "\
                       "(JPEG/PNG etc.)).")
argparser.add_argument('out_file', metavar='out.svg',
                       help="output image file in SVG format.")
argparser.add_argument("-f", "--force-overwrite", action="store_true",
                       help="force overwriting to output image file.")
argparser.add_argument("--debug", action="store_true",
                       help="debug mode.")
args = argparser.parse_args()
if not args.out_file:
    argparser.print_help(sys.stderr)
    exit(1)

galaxies_json = args.galaxies_json
style_json = args.style_json
wcs_fits = args.wcs_fits
image_file = args.image_file
out_file = args.out_file
debug = args.debug

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
    'label-vertical-align': 'auto'
}
non_svg_desc_style_defaults = {
    'line-height': 1
}
style = {
    'marker': {
        'fill': 'none',
        'stroke': 'gray',
        'stroke-width': 1
    },
    'name': {
        'font-size': 40,
        'fill': 'gray',
        'direction': 'ltr'
    },
    'desc': [
        {
            'font-size': 40,
            'fill': 'gray',
            'direction': 'ltr'
        }
    ]
}
style['marker'].update(non_svg_marker_style_defaults)

def update_style(s, s_diff):
    for key in iter(s):
        if not key in s_diff:
            continue
        v = s[key]
        if type(v) == dict:
            v.update(s_diff[key]) 
        elif type(v) == list:
            for i, e in enumerate(s_diff[key]):
                if len(v) > i:
                    v[i].update(e)
                else:
                    v.append(e)
        else:
            s[key] = s_diff[key]
    for ds in s['desc']:
        for k in non_svg_desc_style_defaults:
            if not(k in ds):
                ds[k] = non_svg_desc_style_defaults[k]

def s_to_ss(selector, s):
    ss = selector + ' {\n' if selector else ''
    for prop in s:
        if prop in non_svg_marker_style_defaults:
            continue
        if prop in non_svg_desc_style_defaults:
            continue
        v = s[prop]
        ss += "  " + prop + ": "
        if (type(v) == int or type(v) == float) and prop in SVG_LENGTH_PROPS:
            ss += "{}px".format(v)
        elif type(v) == str and prop == 'font-family':
            ss += '\"{}\"'.format(v)
        else:
            ss += str(v)
        ss += ';\n' if selector else ';'
    if selector:
        ss += '}\n'
    return ss

POS_RE = re.compile('(top|middle|bottom)-(left|middle|right)')
def parse_label_position(value, file):
    res = POS_RE.match(value)
    if not(res):
        print('{}: ERROR: "label-position" of "marker" '\
              'is invalid.'.format(file), file=sys.stderr)
        sys.exit(1)
    else:
        return [res.group(2), res.group(1)]

def get_label_anchor(xpos):
    # TBD: label_anchor for rtl language.
    if xpos == 'left':
        return 'end'
    elif xpos == 'right':
        return 'start'
    elif xpos == 'middle':
        return 'middle'

VALIGN_RE = re.compile('(auto|baseline|top|middle|bottom)')
def parse_label_valign(value, file):
    res = VALIGN_RE.match(value)
    if not(res):
        print('{}: ERROR: "label-vertical-align" of "marker" '\
              'is invalid.'.format(file), file=sys.stderr)
        sys.exit(1)
    else:
        return res.group(1)    

with open(style_json, 'r', encoding='utf-8') as f:
    update_style(style, json.load(f))

if not (type(style['name']['font-size']) == int or
        type(style['name']['font-size']) == float):
    print('{}: ERROR: "font-size" of "name" '\
          'must be of numeric type.'.format(style_json), file=sys.stderr)
    sys.exit(1)
for i, desc in enumerate(style['desc']):
    if not (type(desc['font-size']) == int or type(desc['font-size']) == float):
        print('{}: ERROR: "font-size" of "desc"[{}] must be of '\
              'numeric type.'.format(style_json, i), file=sys.stderr)
        sys.exit(1)

parse_label_valign(style['marker']['label-vertical-align'], style_json)
def_label_position = style['marker']['label-position']
def_x_pos, def_y_pos = parse_label_position(def_label_position, style_json)
def_label_anchor = get_label_anchor(def_x_pos)
if not('text-anchor' in style['name']):
    style['name']['text-anchor'] = def_label_anchor

style_sheet = "\n"
style_sheet += s_to_ss('ellipse.marker', style['marker'])
style_sheet += s_to_ss('text.name', style['name'])
for i, desc in enumerate(style['desc']):
    if not('text-anchor' in desc):
        desc['text-anchor'] = def_label_anchor
    style_sheet += s_to_ss('text.desc{}'.format(i), desc)

if debug:
    style_sheet += '''
.debug_marker { fill: none; stroke: white; stroke-width: 2px; stroke-opacity: 0.8; }
.debug_margin { fill: none; stroke: white; stroke-width: 1.5px; stroke-opacity: 0.8; stroke-dasharray: 8;}
.debug_centerline { fill: none; stroke: white; stroke-width: 1.5px; stroke-opacity: 0.6; stroke-dasharray: 8 4;}
.debug_baseline { fill: none; stroke: white; stroke-width: 1.5px; stroke-opacity: 0.8; stroke-dasharray: 16;}
.debug_middleline { fill: none; stroke: white; stroke-width: 1.5px; stroke-opacity: 0.6; stroke-dasharray: 8 4;}
.debug_label { fill: none; stroke: white; stroke-width: 2px; stroke-opacity: 0.8; }
'''

if out_file and os.path.exists(out_file) and (not args.force_overwrite):
    input = input("output file '" + out_file + "' exists. overwrite? > ")
    if input.upper() != 'YES':
        print('bye.')
        sys.exit(1)

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
    x, y = float(x), float(y)
    if x < 0 or y < 0 or x > image_w or y > image_h:
        continue

    x_pos = def_x_pos
    y_pos = def_y_pos
    
    gal_style = copy.deepcopy(style)
    marker_ss = None
    name_ss = None
    desc_ss = None
    if 'style' in gal:
        s = gal['style']
        if 'marker' in s:
            s_label_position = s['marker']['label-position'] \
                               if ('label-position' in s['marker']) else None
            if s_label_position:
                x_pos, y_pos = parse_label_position(s_label_position, \
                                                    galaxies_json)
                label_anchor = get_label_anchor(x_pos)
                if not('name' in s):
                    s['name'] = {}
                if not('desc' in s):
                    s['desc'] = []
                n = len(s['desc'])
                for i, desc in enumerate(gal['descs']):
                    if i >= n:
                        s['desc'].append({})
            marker_ss = s_to_ss(None, s['marker'])
        if 'name' in s:
            if not('text-anchor' in s['name']) and s_label_position:
                s['name']['text-anchor'] = label_anchor
            name_ss = s_to_ss(None, s['name'])
        if 'desc' in s:
            desc_ss = []
            for i, desc in enumerate(s['desc']):
                if not('text-anchor' in desc) and s_label_position:
                    desc['text-anchor'] = label_anchor
                desc_ss.append(s_to_ss(None, desc))
        
        update_style(gal_style, s)

    marker_size = float(gal_style['marker']['size'])
    label_valign = gal_style['marker']['label-vertical-align']
    parse_label_valign(label_valign, galaxies_json)
    
    svg_group = drw.g()
    drw.add(svg_group)
    gal_name = gal['name']
    print("{name}: ({x}, {y})".format(name=gal_name, x=x, y=y))
    gal_pa = float(gal['pa']) if gal['pa'] else 0.0
    gal_d = 10 ** float(gal['logd25']) / 10 / 60 if gal['logd25'] else None
    gal_r = 10 ** float(gal['logr25']) if gal['logr25'] else 1.0
    
    marker_rot = -1.0 * (gal_pa - image_tilt)
    marker_min_r = gal_style['marker']['min-r']
    marker_min_size_r = gal_style['marker']['min-size-r'] or (marker_min_r + 1)
    marker_min_size = gal_style['marker']['min-size'] or marker_size
    
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
    ellipse = drw.ellipse(center=(float(x), float(y)),
                          r=(marker_rx, marker_ry),
                          transform=transform, class_='marker')
    if marker_ss:
        ellipse.update({ 'style': marker_ss })
    svg_group.add(ellipse)
    
    th = math.radians(marker_rot)
    dx = math.sqrt(marker_rx**2 * math.cos(th)**2 +
                   marker_ry**2 * math.sin(th)**2)
    dy = math.sqrt(marker_rx**2 * math.sin(th)**2 +
                   marker_ry**2 * math.cos(th)**2)
    
    x_margin = float(gal_style['marker']['x-margin'])
    y_margin = float(gal_style['marker']['y-margin'])

    if x_pos == 'left':
        name_x = x - dx - x_margin
    elif x_pos == 'right':
        name_x = x + dx + x_margin
    elif x_pos == 'middle':
        name_x = x

    # y of 'name' baseline 
    if y_pos == 'top':
        name_y = y - dy - y_margin
    elif y_pos == 'bottom':
        name_y = y + dy + y_margin
    elif y_pos == 'middle':
        name_y = y

    if label_valign == 'auto':
        label_valign = 'baseline'
        if x_pos == 'middle':
            if y_pos == 'top':
                label_valign = 'bottom'
            elif y_pos == 'bottom':
                label_valign = 'top'
    
    desc_height = reduce(lambda h, desc: \
                         h + desc['font-size'] * desc['line-height'],\
                         gal_style['desc'], 0)
    # print('desc_height:', desc_height)
    name_height = float(gal_style['name']['font-size'])
    
    if label_valign == 'top':
        name_y += name_height
    elif label_valign == 'bottom':
        name_y -= desc_height
    elif label_valign == 'middle':
        name_y += name_height - (name_height + desc_height) / 2
    
    print("  name: ({x}, {y})".format(x=name_x, y=name_y))
    name_text = drw.text(gal_name, x=[name_x], y=[name_y], class_='name')
    if name_ss:
        name_text.update({ 'style': name_ss })
    svg_group.add(name_text)
    
    if len(gal['descs']) > 0:
        desc_x = name_x
        desc_y = name_y
        for i, desc in enumerate(gal['descs']):
            desc_y += gal_style['desc'][i]['font-size'] * \
                      gal_style['desc'][i]['line-height']
            print("  desc[{i}]: ({x}, {y})".format(i=i, x=desc_x, y=desc_y))
            desc_text = drw.text(desc, x=[desc_x], y=[desc_y],
                                 class_='desc'+str(i))
            if desc_ss and i < len(desc_ss):
                desc_text.update({ 'style': desc_ss[i] })
            svg_group.add(desc_text)

    if debug:
        marker_rect = drw.rect(insert=(x-dx,y-dy), size=(2*dx,2*dy),
                               class_='debug_marker')
        margin_rect = drw.rect(insert=(x-dx-x_margin,y-dy-y_margin),
                               size=(2*(dx+x_margin),2*(dy+y_margin)),
                               class_='debug_margin')
        center_line_h = drw.line(start=(x-dx-x_margin,y), end=(x+dx+x_margin,y),
                                 class_='debug_centerline')
        center_line_v = drw.line(start=(x,y-dy-y_margin), end=(x,y+dy+y_margin),
                                 class_='debug_centerline')
        label_width = name_height*12 # not a real width.
        name_baseline = drw.line(start=(name_x,name_y),
                                 end=(name_x+label_width,name_y),
                                 class_='debug_baseline')
        middle_y = name_y - name_height + (name_height + desc_height) / 2
        label_middleline = drw.line(start=(name_x,middle_y),
                                    end=(name_x+label_width,middle_y),
                                    class_='debug_middleline')
        label_rect = drw.rect(insert=(name_x,name_y-name_height),
                              size=(label_width,name_height+desc_height),
                              class_='debug_label')
        if x_pos == 'left':
            name_baseline.scale(-1, 1)
            name_baseline.translate(-name_x*2, 0)
            label_middleline.scale(-1, 1)
            label_middleline.translate(-name_x*2, 0)
            label_rect.scale(-1, 1)
            label_rect.translate(-name_x*2, 0)
        elif x_pos == 'middle':
            center_x = name_x + label_width / 2
            label_centerline = drw.line(start=(center_x,name_y-name_height),
                                        end=(center_x,name_y+desc_height),
                                        class_='debug_middleline')
            name_baseline.translate(-label_width/2, 0)
            label_middleline.translate(-label_width/2, 0)
            label_centerline.translate(-label_width/2, 0)
            label_rect.translate(-label_width/2, 0)
            
        debug_group = drw.g()
        debug_group.add(marker_rect)
        debug_group.add(margin_rect)
        debug_group.add(center_line_h)
        debug_group.add(center_line_v)
        debug_group.add(name_baseline)
        debug_group.add(label_middleline)
        if x_pos == 'middle':
            debug_group.add(label_centerline)
        debug_group.add(label_rect)
        drw.add(debug_group)

drw.save(pretty=True)
