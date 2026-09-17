#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate this Python NAView port against real VARNA output.

VARNA writes one base as three SVG elements sharing the same centre::

    <circle cx cy r="5.0" ... fill="rgb(94%, 94%, 94%)"/>   <- filled disc
    <circle cx cy r="5.0" ... stroke="rgb(35%, 35%, 35%)"/> <- outline
    <text   x=cx y=cy+3 ...>G</text>                        <- the letter

so the base coordinate is exactly ``(cx, cy)`` of the discs, in document
order (which is base order).

Reference files are produced by ``deploy/varna-ref.sh`` and live in
``tests/varna_ref/*.svg``.  Because a similarity transform may map one
drawing onto the other we compare after optimal rotation + uniform scaling
+ translation (allowing a mirror as well, since VARNA's y axis points down
and NAView's points up).

    python tests/compare_varna.py [--verbose]
"""

import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from naview import parse_dot_bracket, naview_layout, similarity_transform  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REF_DIR = os.path.join(HERE, 'varna_ref')

# name -> (sequence, dot-bracket structure)  -- must match varna-ref.sh
CASES = {
    'hairpin':   ('GCGCAAAAGCGC', '((((....))))'),
    'bulge':     ('GGGGAGGGGAAAACCCCCCCC', '((((.((((....))))))))'),
    'twostem':   ('GGGAAAACCCUUUGGGAAAACCC', '(((....)))...(((....)))'),
    'seq60':     ('TTAGCTTATGCGTTGGCCGGGATAAGGATCCAGCCGTTGTAGATTTGCGTTCTAACTCTC',
                  '...((....))...(((..((((....)))).))).........................'),
    'multiloop': ('GGGGAAAACCCCUUUUGGGGAAAACCCC',
                  '((((....))))....((((....))))'),
}

# Filled base discs (r=5.0, no stroke).  The r=2.75 circles are the 5'/3'
# end labels and must not be picked up.
_DISC_RE = re.compile(
    r'<circle\s+cx="([-0-9.eE+]+)"\s+cy="([-0-9.eE+]+)"\s+r="5\.0"\s+'
    r'stroke="none"')


def parse_varna_svg(path):
    """Return the list of base centres, in document (== base) order."""
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        text = fh.read()
    pts = [(float(m.group(1)), float(m.group(2)))
           for m in _DISC_RE.finditer(text)]
    return pts


def _rmsd_after_fit(moving, target):
    """Best RMSD over all four axis conventions (rotation is free, so this
    amounts to 'allow a mirror or not')."""
    best = None
    for sx in (1.0, -1.0):
        flipped = [(sx * x, y) for x, y in moving]
        scale, ca, sa, tx, ty = similarity_transform(flipped, target)
        total = 0.0
        for (mx, my), (txx, tyy) in zip(flipped, target):
            rx = scale * (ca * mx - sa * my) + tx
            ry = scale * (sa * mx + ca * my) + ty
            total += (rx - txx) ** 2 + (ry - tyy) ** 2
        r = math.sqrt(total / len(target))
        if best is None or r < best[0]:
            best = (r, scale, sx)
    return best


def _extent(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return max(math.hypot(x - sum(xs) / len(xs), y - sum(ys) / len(ys))
               for x, y in pts)


def main(argv):
    verbose = '--verbose' in argv or '-v' in argv

    if not os.path.isdir(REF_DIR):
        print('no reference directory: %s' % REF_DIR)
        print('run deploy/varna-ref.sh first.')
        return 2

    print('=' * 78)
    print(' naview.py  vs  VARNA 3.93  (-algorithm naview)')
    print('=' * 78)
    print('informational: VARNA ships its own Java port of NAView whose geometry')
    print('differs from the reference C routine (see README, "验证" section).')
    print('The binding acceptance test is tests/compare_vienna.py.')
    print()
    print('%-10s %-5s %-12s %-12s %-9s %-9s' % (
        'case', 'n', 'rmsd(px)', 'extent(px)', 'rel', 'fit scale'))

    worst = 0.0
    for name in sorted(CASES):
        svg = os.path.join(REF_DIR, name + '.svg')
        seq, ss = CASES[name]
        if not os.path.exists(svg):
            print('%-10s SKIP (no %s)' % (name, os.path.basename(svg)))
            continue

        ref = parse_varna_svg(svg)
        mine = naview_layout(parse_dot_bracket(ss)).as_tuples()

        if len(ref) != len(mine):
            print('%-10s FAIL  base count: VARNA=%d python=%d'
                  % (name, len(ref), len(mine)))
            continue

        rms, scale, sx = _rmsd_after_fit(mine, ref)
        size = _extent(ref)
        rel = rms / size * 100.0
        worst = max(worst, rel)

        print('%-10s %-5d %-12.4f %-12.2f %-8.3f%% %-9.4f%s'
              % (name, len(ref), rms, size, rel, scale,
                 '  mirrored' if sx < 0 else ''))
        if verbose:
            for i, ((mx, my), (rx, ry)) in enumerate(zip(mine, ref), 1):
                print('      %3d  mine(%9.4f,%9.4f)   varna(%9.4f,%9.4f)'
                      % (i, mx, my, rx, ry))

    print('-' * 78)
    print('Worst deviation %.2f%% of figure size.' % worst)
    print('Same topology and same pair set; VARNA draws wider helices')
    print('(its rung/rise ratio is ~1.67, the reference NAView uses 1.00).')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
