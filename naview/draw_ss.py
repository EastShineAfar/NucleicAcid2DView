#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Draw a DNA/RNA secondary structure with the NAView algorithm.

    # sequence + structure given explicitly
    python draw_ss.py --seq GCGCAAAAGCGC --struct '((((....))))' -o hairpin.svg

    # structure only (letters are then left blank)
    python draw_ss.py --struct '...((....))...(((..((((....)))).)))' -o s.svg

    # tweak sizes and line widths
    python draw_ss.py --seq GCGCAAAAGCGC --struct '((((....))))' \
                      --font-size 12 --ring-radius 9 \
                      --backbone-width 1.5 --pair-width 2 --ring-width 0.6 -o big.svg

    # read from a file (FASTA sequence and/or a dot-bracket line)
    python draw_ss.py structure.txt -o out.svg

    # dump the raw NAView coordinates
    python draw_ss.py --struct '((((....))))' --coords

The layout is the NAView algorithm of Bruccoleri & Heinrich (1988) -- the same
algorithm VARNA and ViennaRNA use -- implemented in pure standard-library
Python.  See README.md for how it was verified.
"""

from __future__ import print_function

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from naview import clean_sequence, parse_dot_bracket, naview_layout  # noqa: E402
from render_svg import render_svg                                     # noqa: E402

__version__ = '1.0.0'

_STRUCT_CHARS = set('.()[]{}<>+-_ :&')
_SEQ_CHARS = set('ACGTUNacgtun')


def _looks_like_structure(text):
    stripped = re.sub(r'[\s]', '', text or '')
    return bool(stripped) and set(stripped) <= _STRUCT_CHARS


def _looks_like_sequence(text):
    stripped = re.sub(r'[\s\d>#]', '', text or '')
    return bool(stripped) and set(stripped) <= _SEQ_CHARS


def _read_file(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        return fh.read()


def _split_blob(text):
    """Split a mixed text blob into (sequence, structure) heuristically."""
    seq_part, struct_part = [], []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        body = re.sub(r'^>\S*\s*', '', line)
        if _looks_like_structure(body) and any(c in '()[]{}' for c in body):
            struct_part.append(body)
        elif _looks_like_sequence(body):
            seq_part.append(body)
    seq = clean_sequence('\n'.join(seq_part)) if seq_part else None
    struct = re.sub(r'\s', '', ''.join(struct_part)) or None
    return seq, struct


def build_parser():
    p = argparse.ArgumentParser(
        prog='draw_ss.py',
        description='Draw a DNA/RNA secondary structure using the NAView algorithm.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split('The layout is the NAView')[0].strip())
    p.add_argument('input', nargs='?',
                   help='file containing a sequence and/or a dot-bracket structure '
                        '(use "-" for stdin)')
    p.add_argument('--seq', help='nucleotide sequence')
    p.add_argument('--struct', dest='struct',
                   help='dot-bracket structure, e.g. "((((....))))"')
    p.add_argument('--seq-file', help='file containing just the sequence (FASTA ok)')
    p.add_argument('--struct-file', help='file containing just the structure')
    p.add_argument('-o', '--output', help='output .svg path (default: stdout)')
    p.add_argument('--coords', action='store_true',
                   help='print the NAView coordinates as text instead of SVG')
    p.add_argument('--title', help='figure title')
    p.add_argument('--base-distance', type=float, default=20.0,
                   help='pixels per NAView unit (default: 20)')
    p.add_argument('--mono', action='store_true',
                   help="plain grey rings + black letters (VARNA's default look)")
    p.add_argument('--pair-style', choices=['single', 'double'], default='single',
                   help='draw each base pair as one line or as two parallel '
                        'lines (default: single)')
    p.add_argument('--font-size', type=float, default=None,
                   help='base letter size in figure pixels (default: 0.37 x '
                        'base distance, i.e. 7.5 at the default scale)')
    p.add_argument('--ring-radius', type=float, default=None,
                   help='base circle radius in figure pixels (default: 0.25 x '
                        'base distance, i.e. 5.0 at the default scale)')
    p.add_argument('--backbone-width', type=float, default=None,
                   help='backbone line width in figure pixels (default: 1.0)')
    p.add_argument('--pair-width', type=float, default=None,
                   help='base-pair line width in figure pixels (default: 1.0)')
    p.add_argument('--ring-width', type=float, default=None,
                   help='base circle stroke width in figure pixels (default: 1.0)')
    p.add_argument('--flip-y', dest='flip_y', action='store_true', default=True,
                   help='draw with the first base at the bottom (default)')
    p.add_argument('--no-flip-y', dest='flip_y', action='store_false',
                   help='draw with the first base at the top')
    p.add_argument('--even-loops', dest='even_loops', action='store_const',
                   const=True, default='auto',
                   help='force the loop-angle evening pass on')
    p.add_argument('--no-even-loops', dest='even_loops', action='store_const',
                   const=False,
                   help='never evening the angles; closest to the reference '
                        'NAView layout')
    p.add_argument('--rotation', type=float, default=0.0,
                   help='rotate the whole figure by this many degrees; the '
                        'base letters stay upright (default: 0)')
    p.add_argument('--reference', dest='reference', action='store_true',
                   help='pure reference NAView: no post-passes at all '
                        '(bit-for-bit identical to ViennaRNA)')
    p.add_argument('--no-bases', action='store_true',
                   help='draw the skeleton only')
    p.add_argument('--no-pairs', action='store_true',
                   help='omit base-pair lines')
    p.add_argument('--no-backbone', action='store_true',
                   help='omit the backbone line')
    p.add_argument('--open', action='store_true',
                   help='open the result in the default viewer when done')
    p.add_argument('--version', action='version',
                   version='draw_ss.py %s' % __version__)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    seq = clean_sequence(args.seq)
    struct = re.sub(r'\s', '', args.struct) if args.struct else None

    if args.seq_file:
        seq = clean_sequence(_read_file(args.seq_file)) or seq
    if args.struct_file:
        struct = re.sub(r'\s', '', _read_file(args.struct_file)) or struct

    if args.input:
        text = sys.stdin.read() if args.input == '-' else _read_file(args.input)
        f_seq, f_struct = _split_blob(text)
        if seq is None:
            seq = f_seq
        if struct is None:
            struct = f_struct

    # nothing on the command line? try stdin if it is not a terminal
    if seq is None and struct is None and not sys.stdin.isatty():
        text = sys.stdin.read()
        if text.strip():
            seq, struct = _split_blob(text)

    if not struct:
        raise SystemExit('error: no structure given.  Use --struct, --struct-file, '
                         'or an input file.')

    try:
        structure = parse_dot_bracket(struct)
    except ValueError as exc:
        raise SystemExit('error: %s' % exc)

    if seq is not None and len(seq) != structure.n:
        raise SystemExit(
            'error: sequence length %d does not match structure length %d'
            % (len(seq), structure.n))

    layout = naview_layout(structure, even_loops=args.even_loops,
                            even_bonds=not args.reference)
    for warning in layout.warnings:
        print('warning: %s' % warning, file=sys.stderr)

    if args.coords:
        handle = open(args.output, 'w', encoding='utf-8') if args.output else sys.stdout
        try:
            handle.write('# NAView coordinates for %s\n' % struct)
            handle.write('# seq %s\n' % (seq or ''))
            handle.write('# index x y pairs_with\n')
            for i in range(structure.n):
                partner = structure.pair_table[i + 1]
                handle.write('%d %.6f %.6f %s\n'
                             % (i + 1, layout.xs[i], layout.ys[i],
                                partner if partner else '.'))
        finally:
            if args.output:
                handle.close()
        return 0

    svg = render_svg(
        layout, seq,
        base_distance=args.base_distance,
        mono=args.mono,
        pair_style=args.pair_style,
        font_size=args.font_size,
        ring_radius=args.ring_radius,
        backbone_width=args.backbone_width,
        pair_width=args.pair_width,
        ring_width=args.ring_width,
        flip_y=args.flip_y,
        rotation=args.rotation,
        show_bases=not args.no_bases,
        show_pair_lines=not args.no_pairs,
        show_backbone=not args.no_backbone,
        title=args.title,
    )

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as fh:
            fh.write(svg)
        print('wrote %s  (%d bases, %d pairs, %d loops)'
              % (args.output, structure.n, len(structure.pairs),
                 len(layout.loops)), file=sys.stderr)
        if args.open:
            _open_file(os.path.abspath(args.output))
    else:
        sys.stdout.write(svg)
    return 0


def _open_file(path):
    try:
        if hasattr(os, 'startfile'):          # Windows
            os.startfile(path)                # noqa: S606
        elif sys.platform == 'darwin':
            os.system('open "%s"' % path)
        else:
            os.system('xdg-open "%s"' % path)
    except Exception as exc:                  # pragma: no cover
        print('could not open %s: %s' % (path, exc), file=sys.stderr)


if __name__ == '__main__':
    sys.exit(main())
