#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Turn a NAView layout into drawing primitives, then into SVG.

The module has two layers on purpose:

1. :func:`build_primitives` produces a flat list of ``line`` / ``circle`` /
   ``text`` dicts in figure-pixel space.  This is the *only* place that knows
   how the figure looks, so the tkinter GUI preview and the SVG export are
   guaranteed to agree -- the GUI just replays the same primitives onto a
   Canvas instead of serialising them.

2. :func:`render_svg` serialises those primitives to an SVG document.

Geometry defaults follow VARNA's own output (measured from its SVG export),
expressed as ratios of the base-to-base distance:

    base disc radius      5.00 px  ->  0.2469 x base_distance
    font size             7.50 px  ->  0.3704 x base_distance
    double-pair offset    1.25 px  ->  0.0617 x base_distance
    line width            1.00 px  ->  0.0494 x base_distance
    backbone trim                     equal to the disc radius

Public API
----------
    build_primitives(layout, sequence=None, **options) -> (prims, width, height)
    render_svg(layout, sequence=None, **options)       -> str
    DEFAULT_OPTIONS, DEFAULT_RING_COLORS, DEFAULT_LETTER_COLORS
"""

__all__ = [
    'build_primitives', 'render_svg',
    'DEFAULT_OPTIONS', 'DEFAULT_RING_COLORS', 'DEFAULT_LETTER_COLORS',
    'BASE_ORDER', 'norm_base',
]

import math

# ---------------------------------------------------------------- palette ---

BACKBONE_COLOR = '#595959'
PAIR_COLOR = '#0000ff'
RING_STROKE = '#595959'
MONO_RING_FILL = '#f0f0f0'
MONO_LETTER_COLOR = '#000000'

# per-nucleotide defaults: a pale ring with a saturated letter reads well on
# screen and in print, and both are user-editable in the GUI.
DEFAULT_RING_COLORS = {
    'A': '#d8f0d8',
    'C': '#d8e6fa',
    'G': '#fdeacd',
    'T': '#fbdada',
    'U': '#fbdada',
    'N': '#eeeeee',
}
DEFAULT_LETTER_COLORS = {
    'A': '#1f9e3a',
    'C': '#1f5fd0',
    'G': '#d98600',
    'T': '#d02020',
    'U': '#d02020',
    'N': '#777777',
}

# the four swatches the GUI shows; U and T share a row
BASE_ORDER = ('A', 'C', 'G', 'T')

# Ratios relative to base_distance.  VARNA's own export measures 0.2469 for
# the disc radius, 0.3704 for the font, 0.0617 for the double-pair offset and
# 0.0494 for the line width.  The values below are this project's own house
# defaults instead: chunky rings and thick lines, which read well on screen
# and in print, and which come out as 6.0 / 6.2 / 2.0 px at the default scale
# of 20.  The GUI can override all of them and remember the choice.
R_RING = 0.31            # 6.2 px at base_distance 20
R_FONT = 0.30            # 6.0 px at base_distance 20
R_BP_OFFSET = 0.0625     # 1.25 px at base_distance 20 (widened for thick lines)
R_LINEWIDTH = 0.10       # 2.0 px at base_distance 20
# SVG puts text on its baseline; lift it by ~35% of the em size to centre it
TEXT_BASELINE = 0.35

DEFAULT_OPTIONS = {
    'base_distance': 20.0,   # figure pixels per NAView unit (ViennaRNA uses 15)
    'margin': 24.0,          # blank border around the figure, in pixels
    'title': None,
    'background': '#ffffff',
    'font_family': 'Verdana',
    'show_bases': True,
    'show_pair_lines': True,
    'show_backbone': True,
    'pair_style': 'single',  # 'single' | 'double'
    'mono': False,           # plain grey rings + black letters
    # NAView has +y upwards.  flip_y=False keeps that (first base ends up at
    # the top); flip_y=True mirrors the figure so the first base starts at the
    # bottom, which is how VARNA draws it.
    'flip_y': True,
    # rotate the whole figure by this many degrees, positive = anticlockwise
    # on screen.  Only the coordinates move -- the letters are drawn upright
    # afterwards, so they never end up on their side.
    'rotation': 0.0,
    # everything below defaults to a value derived from base_distance
    'backbone_width': None,  # line width of the backbone
    'pair_width': None,      # line width of the base-pair lines
    'ring_width': None,      # stroke width of the base circle
    'ring_radius': None,
    'font_size': None,
    'ring_stroke': None,
    'backbone_color': BACKBONE_COLOR,
    'pair_color': PAIR_COLOR,
    'ring_colors': None,     # {base: '#rrggbb'}
    'letter_colors': None,   # {base: '#rrggbb'}
}


def norm_base(ch):
    """Map a nucleotide letter onto the colour-table keys (U -> T)."""
    ch = (ch or 'N').upper()
    return 'T' if ch == 'U' else ch


def _num(v):
    s = '%.3f' % v
    return s.rstrip('0').rstrip('.') if '.' in s else s


def _esc(text):
    return (str(text).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def _trim(p, q, radius):
    """Shorten the segment p->q by *radius* at each end, or None if too short."""
    dx = q[0] - p[0]
    dy = q[1] - p[1]
    d = (dx * dx + dy * dy) ** 0.5
    if d <= 2.0 * radius or d == 0.0:
        return None
    ux, uy = dx / d, dy / d
    return ((p[0] + ux * radius, p[1] + uy * radius),
            (q[0] - ux * radius, q[1] - uy * radius))


def _line(x1, y1, x2, y2, color, width):
    return {'kind': 'line', 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
            'stroke': color, 'width': width}


def _circle(cx, cy, r, fill, stroke, width):
    return {'kind': 'circle', 'cx': cx, 'cy': cy, 'r': r,
            'fill': fill, 'stroke': stroke, 'width': width}


def _text(cx, cy, content, color, size, family):
    return {'kind': 'text', 'cx': cx, 'cy': cy, 'text': content,
            'fill': color, 'size': size, 'family': family}


# ------------------------------------------------------------ primitives ---

def build_primitives(layout, sequence=None, **options):
    """Build the drawing primitives for *layout*.

    Returns ``(prims, width, height)`` where the primitives are in figure
    pixel space with the origin at the top-left corner of the figure.
    """
    opts = dict(DEFAULT_OPTIONS)
    opts.update(options)

    if hasattr(layout, 'xs'):
        xs, ys = layout.xs, layout.ys
        structure = layout.structure
    else:
        xs, ys = layout
        structure = None
    n = len(xs)
    if n == 0:
        return [], 1.0, 1.0

    bd = float(opts['base_distance'])
    r_ring = opts['ring_radius']
    r_ring = R_RING * bd if r_ring is None else float(r_ring)
    font = opts['font_size']
    font = R_FONT * bd if font is None else float(font)
    base_lw = R_LINEWIDTH * bd

    def _width(key):
        value = opts.get(key)
        return base_lw if value is None else max(0.0, float(value))

    bb_w = _width('backbone_width')
    pair_w = _width('pair_width')
    ring_w = _width('ring_width')

    ring_stroke = opts['ring_stroke'] or RING_STROKE
    # keep the two lines of a "double" pair visibly separate even when the
    # line width is large
    bp_off = max(R_BP_OFFSET * bd, pair_w)

    ring_colors = dict(DEFAULT_RING_COLORS)
    letter_colors = dict(DEFAULT_LETTER_COLORS)
    if opts['mono']:
        ring_colors = {k: MONO_RING_FILL for k in ring_colors}
        letter_colors = {k: MONO_LETTER_COLOR for k in letter_colors}
    if opts['ring_colors']:
        ring_colors.update({norm_base(k): v
                            for k, v in opts['ring_colors'].items()})
    if opts['letter_colors']:
        letter_colors.update({norm_base(k): v
                              for k, v in opts['letter_colors'].items()})

    margin = float(opts['margin'])
    # NAView works with +y upwards.  Screen/SVG space has +y downwards, so the
    # sign decides whether the first base ends up at the top or at the bottom
    # of the figure; the min/max shift below then puts it inside the canvas.
    sign = 1.0 if opts['flip_y'] else -1.0
    px = [x * bd for x in xs]
    py = [sign * y * bd for y in ys]

    rotation = float(opts['rotation'] or 0.0) % 360.0
    if rotation:
        # Rotate about the figure's centroid so nothing drifts off.  Done in
        # screen space (y grows downwards), hence the negated sine: a positive
        # angle then turns the picture anticlockwise as seen on screen.
        ang = math.radians(rotation)
        ca, sa = math.cos(ang), math.sin(ang)
        gx = sum(px) / n
        gy = sum(py) / n
        for i in range(n):
            dx = px[i] - gx
            dy = py[i] - gy
            px[i] = gx + ca * dx + sa * dy
            py[i] = gy - sa * dx + ca * dy

    minx, maxx = min(px), max(px)
    miny, maxy = min(py), max(py)
    tx = margin - minx
    ty = margin - miny
    width = (maxx - minx) + 2 * margin
    height = (maxy - miny) + 2 * margin

    title = opts['title']
    if title:
        band = 2.2 * font
        height += band
        ty += band

    def P(i):
        return (px[i] + tx, py[i] + ty)

    prims = []
    add = prims.append

    if title:
        add(_text(width / 2.0, 1.15 * font, title, '#000000',
                  1.15 * font, opts['font_family']))

    breaks = structure.breaks if structure is not None else {n}
    pairs = structure.pairs if structure is not None else []

    # ---- backbone ----------------------------------------------------
    if opts['show_backbone']:
        for i in range(n - 1):
            if (i + 1) in breaks:
                continue
            seg = _trim(P(i), P(i + 1), r_ring)
            if seg is None:
                continue
            (x1, y1), (x2, y2) = seg
            add(_line(x1, y1, x2, y2, opts['backbone_color'], bb_w))

    # ---- base pairs --------------------------------------------------
    if opts['show_pair_lines'] and pairs:
        offsets = (0.0,) if opts['pair_style'] == 'single' else (-bp_off, bp_off)
        for i, j in pairs:
            a = P(i - 1)
            b = P(j - 1)
            dx = b[0] - a[0]
            dy = b[1] - a[1]
            d = (dx * dx + dy * dy) ** 0.5
            if d == 0.0:
                continue
            ux, uy = dx / d, dy / d
            nx, ny = -uy, ux          # normal to the pair axis
            for s in offsets:
                a2 = (a[0] + nx * s, a[1] + ny * s)
                b2 = (b[0] + nx * s, b[1] + ny * s)
                seg = _trim(a2, b2, r_ring)
                if seg is None:
                    continue
                (x1, y1), (x2, y2) = seg
                add(_line(x1, y1, x2, y2, opts['pair_color'], pair_w))

    # ---- bases -------------------------------------------------------
    if opts['show_bases']:
        seq = (sequence or '').upper()
        for i in range(n):
            x, y = P(i)
            if seq:
                key = norm_base(seq[i]) if i < len(seq) else 'N'
                fill = ring_colors.get(key, MONO_RING_FILL)
                add(_circle(x, y, r_ring, fill, ring_stroke, ring_w))
                color = letter_colors.get(key, MONO_LETTER_COLOR)
                add(_text(x, y, seq[i] if i < len(seq) else '?',
                          color, font, opts['font_family']))
            else:
                # no sequence: a small dot still shows where the bases are
                add(_circle(x, y, 0.5 * r_ring, ring_stroke, 'none', 0.0))

    return prims, width, height


# ------------------------------------------------------------------ SVG ----

def render_svg(layout, sequence=None, **options):
    """Render *layout* to a complete SVG document (returns a string)."""
    opts = dict(DEFAULT_OPTIONS)
    opts.update(options)
    prims, width, height = build_primitives(layout, sequence, **options)

    out = []
    w = out.append
    w('<?xml version="1.0" encoding="UTF-8"?>')
    w('<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
      'width="%s" height="%s" viewBox="0 0 %s %s">'
      % (_num(width), _num(height), _num(width), _num(height)))
    w('<rect x="0" y="0" width="%s" height="%s" fill="%s"/>'
      % (_num(width), _num(height), _esc(opts['background'])))

    # lines first, then circles, then text -- so letters stay on top
    groups = {'line': [], 'circle': [], 'text': []}
    for p in prims:
        groups[p['kind']].append(p)

    if groups['line']:
        w('<g stroke-linecap="round">')
        for p in groups['line']:
            w('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" '
              'stroke-width="%s"/>'
              % (_num(p['x1']), _num(p['y1']), _num(p['x2']), _num(p['y2']),
                 _esc(p['stroke']), _num(p['width'])))
        w('</g>')

    for p in groups['circle']:
        stroke = p['stroke']
        sw = (' stroke="%s" stroke-width="%s"' % (_esc(stroke), _num(p['width']))
              if stroke and stroke != 'none' else '')
        w('<circle cx="%s" cy="%s" r="%s" fill="%s"%s/>'
          % (_num(p['cx']), _num(p['cy']), _num(p['r']), _esc(p['fill']), sw))

    for p in groups['text']:
        w('<text x="%s" y="%s" text-anchor="middle" font-family="%s" '
          'font-size="%s" fill="%s">%s</text>'
          % (_num(p['cx']), _num(p['cy'] + TEXT_BASELINE * p['size']),
             _esc(p['family']), _num(p['size']), _esc(p['fill']),
             _esc(p['text'])))

    w('</svg>')
    return '\n'.join(out) + '\n'
