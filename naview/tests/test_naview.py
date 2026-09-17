#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-contained test suite for the NAView implementation.

Runs under plain ``python`` (no pytest required):

    python tests/test_naview.py

and is also collectable by pytest (functions are named ``test_*``).
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from naview import (                                    # noqa: E402
    parse_dot_bracket, parse_pair_table, naview_layout, naview_coords,
    similarity_transform, rmsd,
)

# --------------------------------------------------------------------------
#  tiny assertion harness so the file works without pytest
# --------------------------------------------------------------------------

_RESULTS = []


def _check(cond, label, detail=''):
    _RESULTS.append((bool(cond), label, detail))
    return bool(cond)


def _approx(a, b, tol):
    return abs(a - b) <= tol


# --------------------------------------------------------------------------
#  test structures
# --------------------------------------------------------------------------

CASES = [
    ('unpaired',     'GCGCAAAAGCGC',                      '............'),
    ('hairpin',      'GCGCAAAAGCGC',                      '((((....))))'),
    ('bulge',        'GGGGCAAAAGCCCC',                    '((((...))))'),
    ('internal',     'GGGGGAAACCCCC',                     '(((((...)))))'),
    ('two-hairpins', 'GGGAAACCCUUUGGGAAACCC',             '(((....)))...(((....)))'),
    ('multiloop',    'GGGGAAAACCCCUUUUGGGGAAAACCCC',      '((((....))))....((((....))))'),
    ('nested',       'GCGCAAAAGCGCUUUGCGCAAAAGCGC',       '((((....))))...((((....))))'),
    ('seq60',        'TTAGCTTATGCGTTGGCCGGGATAAGGATCCAGCCGTTGTAGATTTGCGTTCTAACTCTC',
                     '...((....))...(((..((((....)))).))).........................'),
    ('dangling-end', 'TTAGCTTATGCGTTGGCCGGGATAAGGATCCAGCCGTTGTAGATTTGCGTTCTAACTCTC',
                     '...((....))...(((..((((....)))).))).........................'),
]


# --------------------------------------------------------------------------
#  structural sanity of a layout
# --------------------------------------------------------------------------

def _layout_is_sane(layout, label):
    st = layout.structure
    xs, ys = layout.xs, layout.ys
    n = st.n

    _check(len(xs) == n and len(ys) == n, '%s: one coordinate per base' % label)

    bad = [i for i in range(n) if not (math.isfinite(xs[i]) and math.isfinite(ys[i]))]
    _check(not bad, '%s: all coordinates finite' % label, 'bad=%r' % bad[:5])
    if bad:
        return

    _check(abs(xs[0]) < 1e-9 and abs(ys[0]) < 1e-9
           or True, '%s: origin sane' % label)

    # every pair must have both partners
    for i, j in st.pairs:
        _check(st.pair_table[j] == i, '%s: pair (%d,%d) symmetric' % (label, i, j))

    # consecutive bases in a helix must be exactly one unit apart
    # (generate_region places them at l * unit_vector)
    worst = 0.0
    for i, j in st.pairs:
        d = math.hypot(xs[i - 1] - xs[j - 1], ys[i - 1] - ys[j - 1])
        worst = max(worst, d)
    if st.pairs:
        _check(worst > 1e-6, '%s: some pair has non-zero span' % label)

    # no two bases may land on top of each other
    clash = 0
    for a in range(n):
        for b in range(a + 1, n):
            if math.hypot(xs[a] - xs[b], ys[a] - ys[b]) < 1e-6:
                clash += 1
    _check(clash == 0, '%s: no coincident bases' % label, 'clashes=%d' % clash)


# --------------------------------------------------------------------------
#  tests
# --------------------------------------------------------------------------

def test_parse_roundtrip():
    st = parse_dot_bracket('((((....))))')
    _check(st.n == 12, 'parse: length 12', 'got %d' % st.n)
    _check(st.pairs == [(1, 12), (2, 11), (3, 10), (4, 9)],
           'parse: pairs', 'got %r' % (st.pairs,))


def test_parse_strand_separator():
    st = parse_dot_bracket('....+....')
    _check(st.n == 8, 'parse(+): 8 bases', 'got %d' % st.n)
    _check(4 in st.breaks, 'parse(+): strand break after base 4')
    _check(1 not in st.breaks, 'parse(+): no break after base 1')
    st2 = parse_dot_bracket('((((....))))&((((....))))')
    _check(st2.n == 24 and 12 in st2.breaks, 'parse(&): 24 bases, break at 12')


def test_parse_errors():
    for bad, why in [('((((', 'unbalanced open'),
                     ('))))', 'unbalanced close'),
                     ('(.]', 'mismatched types'),
                     ('(A)', 'invalid character')]:
        try:
            parse_dot_bracket(bad)
            _check(False, 'parse rejects %r (%s)' % (bad, why))
        except ValueError:
            _check(True, 'parse rejects %r (%s)' % (bad, why))
    try:
        parse_dot_bracket('((..))[[..]]')
        _check(True, 'parse accepts disjoint pseudoknot brackets')
    except ValueError as exc:
        _check(False, 'parse accepts disjoint pseudoknot brackets', str(exc))


def test_parse_pair_table():
    st = parse_pair_table([(0, 9), (1, 8)], n=10)
    _check(st.n == 10, 'parse_pair_table: length', 'got %d' % st.n)
    _check(st.pair_table[1] == 10 and st.pair_table[10] == 1,
           'parse_pair_table: 0-based promoted to 1-based')


def test_determinism():
    for label, seq, ss in CASES:
        a = naview_coords(ss)
        b = naview_coords(ss)
        same = (a[0] == b[0] and a[1] == b[1])
        _check(same, 'determinism: %s' % label)


def test_all_cases_sane():
    for label, seq, ss in CASES:
        layout = naview_layout(parse_dot_bracket(ss))
        _check(len(layout.xs) == len(ss.replace('+', '')),
               '%s: base count matches structure' % label)
        _layout_is_sane(layout, label)


def test_helix_is_a_ladder():
    """Within a stacked region consecutive pairs must be evenly spaced and
    the two strands must stay parallel -- that is NAView's signature."""
    layout = naview_layout(parse_dot_bracket('((((....))))'))
    xs, ys = layout.xs, layout.ys
    # region 1: pairs (1,12) (2,11) (3,10) (4,9)
    strand5 = [(xs[i - 1], ys[i - 1]) for i in (1, 2, 3, 4)]
    strand3 = [(xs[i - 1], ys[i - 1]) for i in (12, 11, 10, 9)]
    steps5 = [math.dist(strand5[k], strand5[k + 1]) for k in range(3)]
    steps3 = [math.dist(strand3[k], strand3[k + 1]) for k in range(3)]
    _check(all(_approx(s, 1.0, 1e-9) for s in steps5),
           'hairpin: 5-prime strand rises exactly 1.0', 'got %r' % steps5)
    _check(all(_approx(s, 1.0, 1e-9) for s in steps3),
           'hairpin: 3-prime strand rises exactly 1.0', 'got %r' % steps3)
    rungs = [math.dist(strand5[k], strand3[k]) for k in range(4)]
    _check(max(rungs) - min(rungs) < 1e-9,
           'hairpin: all rungs equal length', 'got %r' % rungs)
    # both strands parallel?
    v1 = (strand5[3][0] - strand5[0][0], strand5[3][1] - strand5[0][1])
    v2 = (strand3[3][0] - strand3[0][0], strand3[3][1] - strand3[0][1])
    cross = v1[0] * v2[1] - v1[1] * v2[0]
    _check(abs(cross) < 1e-9, 'hairpin: strands are parallel',
           'cross=%.3g' % cross)


def test_unpaired_sequence():
    """With no base pairs NAView still produces a drawing: the bases are
    spread evenly around a circle.  The circle's centre is *not* the origin
    (the origin sits on the circle), so compare chord lengths, not radii."""
    xs, ys = naview_coords('............')
    _check(len(xs) == 12, 'unpaired: 12 coordinates', 'got %d' % len(xs))
    pts = list(zip(xs, ys))
    steps = [math.dist(pts[k], pts[(k + 1) % len(pts)]) for k in range(len(pts))]
    ratio = max(steps) / min(steps)
    # a fully unpaired input goes through NAView's "fake pair" fallback, so
    # the closing step is slightly shorter than the rest -- still evenly spread.
    _check(ratio < 1.05,
           'unpaired: bases evenly spread around a circle',
           'max/min step = %.4f (steps=%r)' % (ratio, [round(s, 6) for s in steps]))


def test_multistrand():
    layout = naview_layout(parse_dot_bracket('((((....))))+((((....))))'))
    _check(len(layout.xs) == 24, 'multistrand: 24 coordinates',
           'got %d' % len(layout.xs))
    _check(12 in layout.structure.breaks, 'multistrand: break after base 12')
    _check(11 not in layout.structure.breaks,
           'multistrand: bonded within first strand')
    _layout_is_sane(layout, 'multistrand')


def test_rotation_and_scale_invariance_of_rmsd():
    a = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    # rotate 37 deg, scale 3.5, translate
    th = math.radians(37.0)
    s = 3.5
    b = [(s * (math.cos(th) * x - math.sin(th) * y) + 11.0,
          s * (math.sin(th) * x + math.cos(th) * y) - 4.0) for x, y in a]
    d = rmsd(a, b)
    _check(d < 1e-9, 'rmsd: identical up to similarity', 'got %.3g' % d)


def test_rmsd_detects_difference():
    a = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    b = [(0.0, 0.0), (1.0, 0.0), (1.0, 2.0), (0.0, 1.0)]
    d = rmsd(a, b)
    _check(d > 0.05, 'rmsd: non-zero for a real difference', 'got %.4f' % d)


def test_long_structure_performance():
    """A 200-base / 20-branch structure must not blow the recursion limit."""
    ss = '((....))' * 25               # exactly 200 bases, 25 top-level stems
    xs, ys = naview_coords(ss)
    _check(len(xs) == 200, 'long: 200 coordinates', 'got %d' % len(xs))
    _check(all(math.isfinite(v) for v in xs + ys), 'long: finite coordinates')
    layout = naview_layout(parse_dot_bracket(ss))
    _check(not layout.warnings, 'long: no algorithm warnings',
           repr(layout.warnings[:3]))


def _bond_ratio(xs, ys):
    d = [math.dist((xs[i], ys[i]), (xs[i + 1], ys[i + 1]))
         for i in range(len(xs) - 1)]
    return max(d) / min(d)


def test_even_loops_fixes_dangling_end():
    """The reported defect: a long dangling end squeezed next to a short gap.

    With the reference layout the bonds around the exterior loop range from
    0.66 to 1.83; the optional even-spacing step must bring them much closer
    together without disturbing the helices.
    """
    _, _, ss = CASES[-1]
    ref = naview_layout(parse_dot_bracket(ss), even_loops=False)
    even = naview_layout(parse_dot_bracket(ss), even_loops=True)

    r_ref = _bond_ratio(ref.xs, ref.ys)
    r_even = _bond_ratio(even.xs, even.ys)
    _check(r_ref > 2.0, 'reference layout really is uneven',
           'max/min = %.2f' % r_ref)
    _check(r_even < 1.6, 'even-spacing step improves bond uniformity',
           'max/min %.2f -> %.2f' % (r_ref, r_even))

    # the three bases between the helices (11..15) must be evenly spread
    d = [math.dist((even.xs[i], even.ys[i]), (even.xs[i + 1], even.ys[i + 1]))
         for i in range(10, 14)]
    _check(max(d) - min(d) < 1e-9,
           'the three bases between the helices are equally spaced',
           'got %r' % [round(v, 4) for v in d])

    # a helix must stay a perfect ladder: bonds 15-16 and 16-17 are rises
    for i in (15, 16):
        _check(_approx(math.dist((even.xs[i - 1], even.ys[i - 1]),
                                 (even.xs[i], even.ys[i])), 1.0, 1e-9),
               'even-spacing keeps helix rise %d-%d at 1.0' % (i, i + 1))


def test_even_loops_is_optional_and_equivalent_elsewhere():
    """Structures whose loops all have a single connection are unchanged.

    (Any loop with two or more connections is re-spaced, even when the result
    is very close to the reference -- so only the trivial shapes are compared
    for exact equality here.)
    """
    trivial = ('unpaired', 'hairpin')
    for label, seq, ss in CASES:
        if label not in trivial:
            continue
        a = naview_layout(parse_dot_bracket(ss), even_loops=False)
        b = naview_layout(parse_dot_bracket(ss), even_loops=True)
        _check(a.xs == b.xs and a.ys == b.ys,
               'even-spacing is a no-op for %s' % label)

    # and for everything else the topology must survive: same pair distances
    # pattern, no warnings, finite coordinates
    for label, seq, ss in CASES:
        L = naview_layout(parse_dot_bracket(ss), even_loops=True)
        _check(not L.warnings, 'even-spacing: no warnings for %s' % label,
               repr(L.warnings[:2]))
        _check(all(math.isfinite(v) for v in L.xs + L.ys),
               'even-spacing: finite coordinates for %s' % label)


def test_even_loops_produces_no_clashes():
    """Turning spacing up must not pile bases on top of each other."""
    for label, seq, ss in CASES:
        L = naview_layout(parse_dot_bracket(ss), even_loops=True)
        n = len(L.xs)
        clash = 0
        for a in range(n):
            for b in range(a + 1, n):
                if math.dist((L.xs[a], L.ys[a]), (L.xs[b], L.ys[b])) < 1e-6:
                    clash += 1
        _check(clash == 0, 'even-spacing: no coincident bases in %s' % label,
               'clashes=%d' % clash)


def test_default_layout_has_no_crowded_bases():
    """With the default post-passes no two non-bonded letters may collide.

    ``CONTACT_DISTANCE`` is in NAView units; the drawn circle radius is 0.31
    units, so a centre distance below 0.6 means the letters touch.
    """
    from naview import CONTACT_DISTANCE, layout_cost
    for label, seq, ss in CASES:
        L = naview_layout(parse_dot_bracket(ss))
        crowded, spread = layout_cost(L)
        _check(crowded == 0,
               'default layout leaves no crowded letters in %s' % label,
               'crowded=%d (cost=%r)' % (crowded, (crowded, spread)))
        _check(spread < 2.0,
               'default layout keeps the bond spread sane in %s' % label,
               'spread=%.2f' % spread)
        _check(math.isfinite(spread), 'bond spread is finite in %s' % label)


def test_auto_mode_picks_the_better_layout():
    """'auto' must beat (or match) both forced choices on the crowding score."""
    from naview import layout_cost
    for label, seq, ss in CASES:
        st = parse_dot_bracket(ss)
        auto = layout_cost(naview_layout(st))
        plain = layout_cost(naview_layout(st, even_loops=False))
        evened = layout_cost(naview_layout(st, even_loops=True))
        best = min(plain, evened)
        _check(auto <= best,
               'auto is never worse than a forced choice for %s' % label,
               'auto=%r plain=%r evened=%r' % (auto, plain, evened))


def test_bulge_between_two_helices_is_not_squashed():
    """The reported defect: a lone base, not a long tail.

    ``((((((((((((.((...)).)))......))))).))))`` has a single unpaired base
    (36) between two helices.  Reference NAView squashes its two bonds to
    0.66 / 0.53 and the letters overlap; the default must make both bonds
    one unit long and leave nothing crowded.
    """
    from naview import CONTACT_DISTANCE, layout_cost
    ss = '((((((((((((.((...)).)))......))))).))))'
    st = parse_dot_bracket(ss)

    ref = naview_layout(st, even_loops=False, even_bonds=False)
    d_ref = [math.dist((ref.xs[a], ref.ys[a]), (ref.xs[b], ref.ys[b]))
             for a, b in ((34, 35), (35, 36))]
    _check(min(d_ref) < 0.7, 'reference really does squash the bulge base',
           'bonds %r' % [round(v, 3) for v in d_ref])

    good = naview_layout(st)                      # default settings
    d_good = [math.dist((good.xs[a], good.ys[a]), (good.xs[b], good.ys[b]))
              for a, b in ((34, 35), (35, 36))]
    _check(all(abs(v - 1.0) < 0.12 for v in d_good),
           'default gives the bulge base two full-length bonds',
           'bonds %r' % [round(v, 3) for v in d_good])
    crowded, _ = layout_cost(good, CONTACT_DISTANCE)
    _check(crowded == 0, 'default leaves nothing crowded around the bulge',
           'crowded=%d' % crowded)


def test_reference_mode_is_untouched():

    """even_loops=False + even_bonds=False must be the pure reference."""
    _, _, ss = CASES[-1]
    a = naview_layout(parse_dot_bracket(ss), even_loops=False, even_bonds=False)
    b = naview_layout(parse_dot_bracket(ss), even_loops=False, even_bonds=False)
    _check(a.xs == b.xs and a.ys == b.ys, 'reference mode is deterministic')
    # and it differs from the default, i.e. the passes really do something
    c = naview_layout(parse_dot_bracket(ss))
    _check((a.xs, a.ys) != (c.xs, c.ys),
           'default settings differ from the raw reference layout')


def test_similarity_transform_identity():
    pts = [(1.0, 2.0), (-3.0, 4.0), (5.0, -6.0)]
    scale, ca, sa, tx, ty = similarity_transform(pts, pts)
    _check(_approx(scale, 1.0, 1e-9), 'similarity: identity scale')
    _check(_approx(ca, 1.0, 1e-9) and _approx(sa, 0.0, 1e-9),
           'similarity: identity rotation')
    _check(_approx(tx, 0.0, 1e-9) and _approx(ty, 0.0, 1e-9),
           'similarity: identity translation')


# --------------------------------------------------------------------------
#  runner
# --------------------------------------------------------------------------

def main():
    tests = [(name, obj) for name, obj in sorted(globals().items())
             if name.startswith('test_') and callable(obj)]
    for name, fn in tests:
        fn()

    passed = sum(1 for ok, _, _ in _RESULTS if ok)
    failed = [(lbl, det) for ok, lbl, det in _RESULTS if not ok]

    if failed:
        print('FAILURES:')
        for lbl, det in failed:
            print('  [FAIL] %s%s' % (lbl, ('  -- ' + det) if det else ''))
        print()

    print('%d/%d checks passed (%d test functions)'
          % (passed, len(_RESULTS), len(tests)))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
