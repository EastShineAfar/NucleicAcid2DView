"""Diagnose how VARNA's rendered geometry relates to raw NAView output."""
import math
import os
import re
import sys

sys.path.insert(0, r'E:\AIspace\naview')
sys.path.insert(0, r'E:\AIspace\naview\tests')
from naview import parse_dot_bracket, naview_layout
from compare_varna import parse_varna_svg, CASES, REF_DIR


def fit_affine(mine, ref):
    """Least squares: ref ~ A * mine + b, six free parameters."""
    n = len(mine)
    # normal equations for each output coordinate separately, shared 3x3 matrix
    # design row = [x, y, 1]
    import itertools
    M = [[0.0] * 3 for _ in range(3)]
    bx = [0.0] * 3
    by = [0.0] * 3
    for (x, y), (X, Y) in zip(mine, ref):
        row = (x, y, 1.0)
        for i in range(3):
            for j in range(3):
                M[i][j] += row[i] * row[j]
            bx[i] += row[i] * X
            by[i] += row[i] * Y
    # solve 3x3 twice (Gaussian elimination with partial pivoting)
    def solve(A, b):
        A = [r[:] for r in A]
        b = b[:]
        for c in range(3):
            p = max(range(c, 3), key=lambda r: abs(A[r][c]))
            A[c], A[p] = A[p], A[c]
            b[c], b[p] = b[p], b[c]
            for r in range(c + 1, 3):
                f = A[r][c] / A[c][c]
                for k in range(c, 3):
                    A[r][k] -= f * A[c][k]
                b[r] -= f * b[c]
        out = [0.0] * 3
        for r in (2, 1, 0):
            s = b[r] - sum(A[r][k] * out[k] for k in range(r + 1, 3))
            out[r] = s / A[r][r]
        return out
    ax = solve(M, bx)
    ay = solve(M, by)
    res = 0.0
    for (x, y), (X, Y) in zip(mine, ref):
        px = ax[0] * x + ax[1] * y + ax[2]
        py = ay[0] * x + ay[1] * y + ay[2]
        res += (px - X) ** 2 + (py - Y) ** 2
    return (ax, ay), math.sqrt(res / n)


def main():
    print('%-10s %-8s %-10s %-10s   affine matrix' % (
        'case', 'n', 'rmsd_sim', 'rmsd_aff'))
    for name in sorted(CASES):
        svg = os.path.join(REF_DIR, name + '.svg')
        if not os.path.exists(svg):
            continue
        seq, ss = CASES[name]
        ref = parse_varna_svg(svg)
        mine = naview_layout(parse_dot_bracket(ss)).as_tuples()
        if len(ref) != len(mine):
            print('%-10s length mismatch %d vs %d' % (name, len(ref), len(mine)))
            continue
        (ax, ay), ra = fit_affine(mine, ref)
        # similarity-only rmsd for reference
        from compare_varna import _rmsd_after_fit
        rs, scale, sx = _rmsd_after_fit(mine, ref)
        print('%-10s %-8d %-10.4f %-10.4f   x=[%7.4f %7.4f]  y=[%7.4f %7.4f]'
              % (name, len(ref), rs, ra, ax[0], ax[1], ay[0], ay[1]))
    print()
    print('If rmsd_aff ~ 0 the difference is a pure affine (linear) map;')
    print('if it stays large the geometry itself differs.')


if __name__ == '__main__':
    main()
