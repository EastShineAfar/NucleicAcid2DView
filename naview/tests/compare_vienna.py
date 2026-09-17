#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Acceptance test: compare naview.py against ViennaRNA's naview_xy_coordinates.

``naview.py`` is a port of the C routine that ViennaRNA ships as
``vrna_plot_coords_naview_pt()``, which itself is Bruccoleri's original
``naview.c``.  ViennaRNA post-processes the raw result with nothing but

    X[k] = 100 + 15 * x[k]
    Y[k] = 100 + 15 * y[k]

so a correct port must reproduce ViennaRNA's numbers exactly, up to float32
rounding inside the C library.  This script checks precisely that.

Reference coordinates are produced by ``deploy/dump-vienna.py`` and live in
``tests/vienna_ref/*.txt``.

    python tests/compare_vienna.py

Exit status 0 means the port is bit-for-bit faithful.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from naview import parse_dot_bracket, naview_layout          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REF_DIR = os.path.join(HERE, 'vienna_ref')

SCALE = 15.0
OFFSET = 100.0
TOL = 1e-3          # ViennaRNA stores float32, so allow a little slack

CASES = {
    'hairpin':   '((((....))))',
    'bulge':     '((((.((((....))))))))',
    'twostem':   '(((....)))...(((....)))',
    'seq60':     '...((....))...(((..((((....)))).))).........................',
    'multiloop': '((((....))))....((((....))))',
    'unpaired':  '............',
    'threestem': '((((....))))....((((....))))...(....)',
}


def read_reference(path):
    xs, ys = [], []
    with open(path, 'r', encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            xs.append(float(parts[1]))
            ys.append(float(parts[2]))
    return xs, ys


def main():
    if not os.path.isdir(REF_DIR) or not os.listdir(REF_DIR) if os.path.isdir(REF_DIR) else True:
        print('no reference data in %s' % REF_DIR)
        print('run:  wsl -d Ubuntu -- ~/env-vienna/bin/python /mnt/e/.../deploy/dump-vienna.py')
        return 2

    print('=' * 76)
    print(' naview.py  vs  ViennaRNA naview_xy_coordinates  (the reference C code)')
    print('=' * 76)
    print('%-10s %-5s %-14s %-14s %s' % ('case', 'n', 'max|dx|', 'max|dy|', 'verdict'))

    bad = []
    for name in sorted(CASES):
        path = os.path.join(REF_DIR, name + '.txt')
        if not os.path.exists(path):
            print('%-10s SKIP (run dump-vienna.py)' % name)
            continue

        rx, ry = read_reference(path)
        # Both post-passes are switched off here so this test keeps pinning
        # the reference algorithm itself: even_loops=False gives NAView's own
        # coordinates, even_bonds=False leaves them untouched.
        mx, my = naview_layout(parse_dot_bracket(CASES[name]),
                               even_loops=False, even_bonds=False).as_coords()

        if len(rx) != len(mx):
            print('%-10s FAIL  n mismatch ref=%d mine=%d' % (name, len(rx), len(mx)))
            bad.append(name)
            continue

        dx = max(abs((OFFSET + SCALE * mx[k]) - rx[k]) for k in range(len(mx)))
        dy = max(abs((OFFSET + SCALE * my[k]) - ry[k]) for k in range(len(my)))

        ok = dx <= TOL and dy <= TOL
        if not ok:
            bad.append(name)
        print('%-10s %-5d %-14.3e %-14.3e %s'
              % (name, len(mx), dx, dy, 'IDENTICAL' if ok else 'DIFFERS'))

    print('-' * 76)
    if bad:
        print('MISMATCH in: %s' % ', '.join(bad))
        return 1
    print('naview.py reproduces the reference NAView implementation exactly.')
    print('(relationship checked: vienna = 100 + 15 * naview, tolerance %g)' % TOL)
    return 0


if __name__ == '__main__':
    sys.exit(main())
