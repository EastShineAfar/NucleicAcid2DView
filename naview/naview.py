#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NAView layout for DNA/RNA secondary structures.

Pure Python, standard library only -- no numpy, no Java, no WSL.

NAView ("A modified radial drawing of an RNA secondary structure") is the
algorithm of Bruccoleri & Heinrich, CABIOS 4(1):167-173, 1988.  It is the
default layout both in VARNA (package ``fr.orsay.lri.varna.models.naView``)
and in ViennaRNA (``VRNA_PLOT_TYPE_NAVIEW``).

How it works, in one paragraph
------------------------------
The structure is decomposed into *regions* (maximal stacks of consecutive
base pairs) and *loops* (exterior loop, hairpin loops, bulges, internal
loops and multi-branch loops).  Regions and loops form a tree.  Starting
from the loop with the most branches, every loop is placed as a circle
whose radius is chosen by least squares so that consecutive bases sit
roughly one unit apart; regions are drawn as straight ladders of unit
rungs.  Whenever a segment of a loop would overlap its neighbours the
connector is flagged "extruded" and pushed outside the circle.  Unpaired
stretches that do not fit on the circle are drawn as arcs.

This module reproduces the reference implementation closely, including a
few quirks of the original C code, so that the coordinates agree with
VARNA's to within a similarity transform.

Public API
----------
    parse_dot_bracket(ss)     -> Structure
    naview_layout(structure)  -> Layout   (xs, ys, loops, ...)
    naview_coords(ss)         -> (xs, ys)
    rmsd_to(reference, ...)   -> float    (similarity-invariant comparison)

Coordinates are returned in NAView's native unit (one base-pair rise == 1.0),
with +y pointing *up*, exactly like the C original.  Renderers are expected
to flip the y axis for SVG/canvas.
"""

from __future__ import division

import math
import sys

__all__ = [
    'Structure', 'Layout', 'Loop',
    'parse_dot_bracket', 'parse_pair_table', 'clean_sequence',
    'naview_layout', 'naview_coords',
    'similarity_transform', 'rmsd',
]

__version__ = '1.0.0'

PI = math.pi
ANUM = 9999.0          # "no coordinate yet" marker, as in the C original
LENCUT = 0.5           # minimum separation of bases around a loop
MIN_BOND = 0.8         # below this a backbone bond is re-shaped
# only re-space a loop's angles when its biggest unpaired stretch has
# at least this many bases; small bulges are better left to the
# bond-shaping pass below (re-spacing their angles can squeeze the two
# helices together until the bulge has nowhere to go)
EVEN_LOOPS_MIN_GAP = 3


def _angdiff(x, y):
    """Smallest absolute difference between two angles."""
    return abs((x - y + math.pi) % (2.0 * math.pi) - math.pi)
RT2_2 = 0.7071068      # sqrt(2)/2, minimum loop radius

_OPEN_TO_CLOSE = {'(': ')', '[': ']', '{': '}', '<': '>'}
_CLOSE_TO_OPEN = {v: k for k, v in _OPEN_TO_CLOSE.items()}
_UNPAIRED_CHARS = '.·-_: '
_STRAND_BREAK_CHARS = '+&'


# --------------------------------------------------------------------------
#  Input parsing
# --------------------------------------------------------------------------

class Structure(object):
    """A pseudoknot-free secondary structure.

    Attributes
    ----------
    pair_table : list of int, length n+1 (1-based; index 0 is unused)
        ``pair_table[i]`` is the partner of base *i*, or 0 if unpaired.
    breaks : set of int
        ``i`` in ``breaks`` means there is no backbone bond between base *i*
        and base *i+1* (i.e. a strand boundary, or the sequence ends there).
    n : int
        Number of bases.
    """

    __slots__ = ('pair_table', 'breaks', 'n')

    def __init__(self, pair_table, breaks):
        self.pair_table = pair_table
        self.breaks = breaks
        self.n = len(pair_table) - 1

    @property
    def pairs(self):
        """List of ``(i, j)`` pairs with ``i < j``, sorted by *i*."""
        return [(i, self.pair_table[i]) for i in range(1, self.n + 1)
                if self.pair_table[i] > i]

    def __repr__(self):
        return '<Structure n=%d pairs=%d strands=%d>' % (
            self.n, len(self.pairs), len(self.breaks) + 1)


def parse_dot_bracket(ss):
    """Parse a dot-bracket string into a :class:`Structure`.

    Accepts ``.`` (also space, ``-``, ``_``, ``:``) for unpaired bases and the
    four bracket flavours ``() [] {} <>`` for pairs.  ``+`` and ``&`` mark
    strand boundaries and do **not** consume a base.

    Brackets must nest properly; a crossing (pseudoknot) raises ``ValueError``
    because NAView, like VARNA's naview layout, cannot draw pseudoknots.
    """
    if not isinstance(ss, str):
        raise TypeError('structure must be a string, got %r' % type(ss))

    pt = [0]
    breaks = set()
    stack = []
    for ch in ss:
        if ch in _STRAND_BREAK_CHARS:
            if len(pt) > 1:
                breaks.add(len(pt) - 1)
        elif ch in _UNPAIRED_CHARS:
            pt.append(0)
        elif ch in _OPEN_TO_CLOSE:
            pt.append(0)
            stack.append((ch, len(pt) - 1))
        elif ch in _CLOSE_TO_OPEN:
            if not stack:
                raise ValueError(
                    "unbalanced %r at position %d" % (ch, len(pt)))
            opener, idx = stack.pop()
            if opener != _CLOSE_TO_OPEN[ch]:
                raise ValueError(
                    "mismatched brackets: %r closed by %r at position %d"
                    % (opener, ch, len(pt)))
            pt.append(0)
            pt[idx] = len(pt) - 1
            pt[len(pt) - 1] = idx
        else:
            hint = ''
            if ch.upper() in 'ACGTU':
                hint = (' -- this looks like a nucleotide sequence; '
                        'parse_dot_bracket() expects a dot-bracket structure '
                        'such as "((((....))))"')
            raise ValueError(
                "invalid character %r at position %d%s" % (ch, len(pt), hint))

    if stack:
        raise ValueError(
            "unclosed %r at position %d" % (stack[-1][0], stack[-1][1]))

    if len(pt) > 1:
        breaks.add(len(pt) - 1)     # the 3' end always terminates a strand
    return Structure(pt, breaks)


_SEQ_RE = None


def clean_sequence(text):
    """Normalise a pasted sequence: drop FASTA headers, digits and whitespace.

    Returns an upper-case string, or ``None`` for empty input.  Used by both
    the command line tool and the GUI so pasted text behaves identically.
    """
    if text is None:
        return None
    import re
    global _SEQ_RE
    if _SEQ_RE is None:
        _SEQ_RE = re.compile(r'[\s\d]')
    parts = []
    for line in str(text).splitlines():
        line = line.strip()
        if not line or line.startswith('>') or line.startswith('#'):
            continue
        parts.append(line)
    cleaned = _SEQ_RE.sub('', ''.join(parts))
    return cleaned.upper() or None


def parse_pair_table(pairs, n=None):
    """Build a :class:`Structure` from an explicit list of ``(i, j)`` pairs.

    Indices may be 0-based or 1-based; they are normalised to 1-based.
    """
    pairs = list(pairs)
    if not pairs:
        n = n or 0
        return Structure([0] * (n + 1), set(range(n + 1)))
    lo = min(min(p) for p in pairs)
    shift = 1 if lo == 0 else 0
    if n is None:
        n = max(max(p) for p in pairs) + shift
    pt = [0] * (n + 1)
    pairs = sorted(set((i + shift, j + shift) for i, j in pairs))
    for i, j in pairs:
        if not (1 <= i < j <= n):
            raise ValueError('bad pair (%d, %d) for length %d' % (i, j, n))
        if pt[i] or pt[j]:
            raise ValueError('base %d or %d paired twice' % (i, j))
        pt[i] = j
        pt[j] = i
    breaks = set(range(n + 1))
    return Structure(pt, breaks)


# --------------------------------------------------------------------------
#  Internal data model (mirrors the C structs)
# --------------------------------------------------------------------------

class Loop(object):
    """One loop of the structure (exterior loop, hairpin, bulge, ...)."""

    __slots__ = ('connections', 'number', 'depth', 'mark',
                 'x', 'y', 'radius')

    def __init__(self, number):
        self.connections = []
        self.number = number
        self.depth = 0
        self.mark = False
        self.x = 0.0
        self.y = 0.0
        self.radius = 0.0

    @property
    def nconnection(self):
        return len(self.connections)

    def __repr__(self):
        return '<Loop #%d %d connections r=%.3f>' % (
            self.number, self.nconnection, self.radius)


class _Base(object):
    __slots__ = ('mate', 'x', 'y', 'extracted', 'region')

    def __init__(self):
        self.mate = 0
        self.x = ANUM
        self.y = ANUM
        self.extracted = False
        self.region = None


class _Region(object):
    __slots__ = ('start1', 'end1', 'start2', 'end2')

    def __init__(self):
        self.start1 = self.end1 = self.start2 = self.end2 = 0

    def __repr__(self):
        return '<Region %d-%d / %d-%d>' % (
            self.start1, self.end1, self.start2, self.end2)


class _Connection(object):
    __slots__ = ('loop', 'region', 'start', 'end', 'xrad', 'yrad',
                 'angle', 'extruded', 'broken')

    def __init__(self):
        self.loop = None
        self.region = None
        self.start = self.end = 0
        self.xrad = self.yrad = self.angle = 0.0
        self.extruded = False
        self.broken = False


class Layout(object):
    """Result of :func:`naview_layout`."""

    __slots__ = ('x', 'y', 'xs', 'ys', 'structure', 'loops', 'root', 'warnings')

    def __init__(self, xs, ys, structure, loops, root, warnings):
        self.xs = xs
        self.ys = ys
        self.structure = structure
        self.loops = loops
        self.root = root
        self.warnings = warnings

    def as_coords(self):
        """Return ``(xs, ys)`` as two plain lists."""
        return list(self.xs), list(self.ys)

    def as_tuples(self):
        return list(zip(self.xs, self.ys))

    def bbox(self):
        if not self.xs:
            return (0.0, 0.0, 0.0, 0.0)
        return (min(self.xs), min(self.ys), max(self.xs), max(self.ys))

    def __repr__(self):
        return '<Layout n=%d loops=%d warnings=%d>' % (
            len(self.xs), len(self.loops), len(self.warnings))


# --------------------------------------------------------------------------
#  The solver
# --------------------------------------------------------------------------

class _NAView(object):
    """Faithful port of naview.c (Bruccoleri; ViennaRNA adaptation)."""

    def __init__(self, structure, even_loops=True, even_bonds=True):
        self.st = structure
        self.nbase = structure.n
        self.even_loops = bool(even_loops)
        self.even_bonds = bool(even_bonds)
        self.bases = [_Base() for _ in range(self.nbase + 1)]
        self.regions = []
        self.loops = []
        self.loop_count = 0
        self.root = None
        self.warnings = []

    # -- helpers ---------------------------------------------------------

    def _warn(self, msg):
        self.warnings.append(msg)

    # -- step 1: load the pair table -------------------------------------

    def _read_in_bases(self):
        b = self.bases
        b[0].mate = 0
        b[0].extracted = False
        npairs = 0
        for i in range(1, self.nbase + 1):
            b[i].extracted = False
            b[i].x = ANUM
            b[i].y = ANUM
            b[i].mate = self.st.pair_table[i]
            if b[i].mate > i:
                npairs += 1
        if npairs == 0 and self.nbase >= 2:
            # The C original fakes one pair so the rest of the code has
            # something to walk around; it keeps an unpaired sequence from
            # producing an empty drawing.
            b[1].mate = self.nbase
            b[self.nbase].mate = 1

    # -- step 2: find maximal stacked regions ----------------------------

    def _find_regions(self):
        nbase = self.nbase
        bases = self.bases
        mark = [False] * (nbase + 1)
        i = 0
        while i <= nbase:
            mate = bases[i].mate
            if mate and not mark[i]:
                r = _Region()
                r.start1 = i
                r.end2 = mate
                mark[i] = mark[mate] = True
                bases[i].region = bases[mate].region = r
                self.regions.append(r)

                i += 1
                mate -= 1
                while i < mate and bases[i].mate == mate:
                    mark[i] = mark[mate] = True
                    bases[i].region = bases[mate].region = r
                    i += 1
                    mate -= 1
                i -= 1
                r.end1 = i
                r.start2 = mate + 1
            i += 1

    # -- step 3: build the loop tree -------------------------------------

    def _construct_loop(self, ibase):
        nbase = self.nbase
        bases = self.bases
        retloop = Loop(self.loop_count + 1)
        self.loop_count += 1
        self.loops.append(retloop)

        i = ibase
        while True:
            mate = bases[i].mate
            if mate:
                rp = bases[i].region
                if not bases[rp.start1].extracted:
                    if i == rp.start1:
                        bases[rp.start1].extracted = True
                        bases[rp.end1].extracted = True
                        bases[rp.start2].extracted = True
                        bases[rp.end2].extracted = True
                        nxt = rp.end1 + 1 if rp.end1 < nbase else 0
                        lp = self._construct_loop(nxt)
                    elif i == rp.start2:
                        bases[rp.start2].extracted = True
                        bases[rp.end2].extracted = True
                        bases[rp.start1].extracted = True
                        bases[rp.end1].extracted = True
                        nxt = rp.end2 + 1 if rp.end2 < nbase else 0
                        lp = self._construct_loop(nxt)
                    else:
                        raise RuntimeError(
                            'construct_loop: base %d not in region table' % i)

                    cp = _Connection()
                    cp.loop = lp
                    cp.region = rp
                    if i == rp.start1:
                        cp.start, cp.end = rp.start1, rp.end2
                    else:
                        cp.start, cp.end = rp.start2, rp.end1
                    retloop.connections.append(cp)

                    cp2 = _Connection()
                    cp2.loop = retloop
                    cp2.region = rp
                    if i == rp.start1:
                        cp2.start, cp2.end = rp.start2, rp.end1
                    else:
                        cp2.start, cp2.end = rp.start1, rp.end2
                    lp.connections.append(cp2)

                i = mate
            i += 1
            if i > nbase:
                i = 0
            if i == ibase:
                break
        return retloop

    # -- step 4: pick the root loop --------------------------------------

    def _depth(self, lp):
        if lp.nconnection <= 1:
            return 0
        if lp.mark:
            return -1
        lp.mark = True
        count = 0
        ret = 0
        for cp in lp.connections:
            d = self._depth(cp.loop)
            if d >= 0:
                count += 1
                if count == 1:
                    ret = d
                elif ret > d:
                    ret = d
        lp.mark = False
        return ret + 1

    def _determine_depths(self):
        for lp in self.loops:
            for other in self.loops:
                other.mark = False
            lp.depth = self._depth(lp)

    def _find_central_loop(self):
        self._determine_depths()
        maxconn = 0
        maxdepth = -1
        root = None
        for lp in self.loops:
            if lp.nconnection > maxconn:
                maxdepth = lp.depth
                maxconn = lp.nconnection
                root = lp
            elif lp.depth > maxdepth and lp.nconnection == maxconn:
                maxdepth = lp.depth
                root = lp
        if root is None:
            root = self.loops[0]
        self.root = root

    # -- step 5: radii ---------------------------------------------------

    def _even_connection_angles(self, lp):
        """Spread the connections of *lp* so all its backbone bonds are equal.

        Reference NAView gives each connection the outward normal of its chord
        in the "circle diagram"; the angular width a gap receives that way has
        nothing to do with how many bases the gap actually contains.  With a
        long dangling end next to a short three-base gap this shows up as a
        few bases splayed far apart while the dangling end is squeezed.

        This helper re-assigns the angles so that every gap gets a share of
        the loop's circle proportional to its step count, which makes the
        spacing uniform.  It is only used when ``even_loops`` is enabled; the
        default path stays bit-for-bit identical to the reference.
        """
        conns = lp.connections
        nconn = len(conns)
        if nconn < 2:
            return
        radius = lp.radius if lp.radius > 0 else 1.0
        alpha = math.asin(min(0.99, 0.5 / radius))   # half a base pair's span

        steps = []
        for i in range(nconn):
            cp = conns[i]
            cpnext = conns[(i + 1) % nconn]
            c = cpnext.start - cp.end
            if c < 0:
                c += self.nbase + 1
            steps.append(c)
        if max(steps) - 1 < EVEN_LOOPS_MIN_GAP:
            return          # nothing long enough here to be worth moving
        total = sum(steps)
        avail = 2.0 * PI - 2.0 * nconn * alpha
        if total <= 0 or avail <= 0.0:
            return

        a = conns[0].angle
        for i in range(nconn):
            cp = conns[i]
            cp.angle = a % (2.0 * PI)
            cp.xrad = math.cos(cp.angle)
            cp.yrad = math.sin(cp.angle)
            a += 2.0 * alpha + avail * steps[i] / total

    def _determine_radius(self, lp, lencut):
        conns = lp.connections
        nconn = len(conns)
        nbase = self.nbase
        radius = RT2_2
        guard = 0
        while True:
            guard += 1
            if guard > nconn + 4:
                self._warn('determine_radius: giving up after %d tries' % guard)
                break
            mindit = 1.0e10
            sumd = 0.0
            sumn = 0.0
            imindit = 0
            for i in range(nconn):
                cp = conns[i]
                j = i + 1
                if j >= nconn:
                    j = 0
                cpnext = conns[j]
                end = cp.end
                start = cpnext.start
                if start < end:
                    start += nbase + 1
                dt = cpnext.angle - cp.angle
                if dt <= 0.0:
                    dt += 2 * PI
                if not cp.extruded:
                    ci = start - end
                    if ci == 0:               # defensive; impossible for valid input
                        ci = 1.0
                else:
                    ci = 2.0 if dt <= PI / 2 else 1.5
                sumn += dt * (1.0 / ci + 1.0)
                sumd += dt * dt / ci
                dit = dt / ci
                if dit < mindit and not cp.extruded and ci > 1.0:
                    mindit = dit
                    imindit = i
            if sumd == 0.0:
                break
            radius = sumn / sumd
            if radius < RT2_2:
                radius = RT2_2
            if mindit * radius < lencut:
                conns[imindit].extruded = True
            else:
                break
        if lp.radius > 0.0:
            radius = lp.radius
        else:
            lp.radius = radius

    # -- step 6: helpers used while traversing ---------------------------

    @staticmethod
    def _connected(cp, cpnext):
        if cp.extruded:
            return True
        return cp.end + 1 == cpnext.start

    @staticmethod
    def _find_ic_middle(icstart, icend, anchor_connection, acp, lp):
        conns = lp.connections
        nconn = len(conns)
        count = 0
        ret = -1
        ic = icstart
        while True:
            if count > nconn * 2:
                return ret
            count += 1
            if anchor_connection is not None and conns[ic] is acp:
                ret = ic
            if ic == icend:
                break
            ic += 1
            if ic >= nconn:
                ic = 0
        if ret == -1:
            ic = icstart
            for _ in range(1, (count + 1) // 2):
                ic += 1
                if ic >= nconn:
                    ic = 0
            ret = ic
        return ret

    def _generate_region(self, cp):
        """Lay out the base pairs of a stacked region as a straight ladder."""
        bases = self.bases
        rp = cp.region
        if cp.start == rp.start1:
            start, end = rp.start1, rp.end1
        else:
            start, end = rp.start2, rp.end2
        if (bases[cp.start].x > ANUM - 100.0
                or bases[cp.end].x > ANUM - 100.0):
            self._warn('generate_region called before its anchor was placed')
            return
        l = 0
        for i in range(start + 1, end + 1):
            l += 1
            bases[i].x = bases[cp.start].x + l * cp.xrad
            bases[i].y = bases[cp.start].y + l * cp.yrad
            mate = bases[i].mate
            bases[mate].x = bases[cp.end].x + l * cp.xrad
            bases[mate].y = bases[cp.end].y + l * cp.yrad

    # -- step 7: extruded segments and circular arcs ---------------------

    @staticmethod
    def _find_center_for_arc(n, b):
        """Distance h from the chord midpoint to the polygon centre, and the
        radial angle theta of one side (bisection, exactly as in the C code)."""
        maxiter = 500
        hhi = (n + 1) / PI
        hlow = -hhi - b / (n + 1.000001 - b)
        if b < 1:
            hlow = 0.0
        h = 0.0
        theta = 0.0
        it = 0
        while True:
            it += 1
            h = (hhi + hlow) / 2.0
            r = math.sqrt(h * h + b * b / 4.0)
            if r == 0.0:
                return 0.0, 0.0
            disc = 1.0 - 0.5 / (r * r)
            if abs(disc) > 1.0:
                return 0.0, 0.0
            theta = math.acos(disc)
            phi = math.acos(max(-1.0, min(1.0, h / r)))
            e = theta * (n + 1) + 2 * phi - 2 * PI
            if e > 0.0:
                hlow = h
            else:
                hhi = h
            if abs(e) <= 0.0001 or it >= maxiter:
                break
        return h, theta

    def _construct_circle_segment(self, start, end):
        bases = self.bases
        nbase = self.nbase
        dx = bases[end].x - bases[start].x
        dy = bases[end].y - bases[start].y
        rr = math.sqrt(dx * dx + dy * dy)
        l = end - start
        if l < 0:
            l += nbase + 1
        if l <= 0:
            return
        if rr >= l:
            dx /= rr
            dy /= rr
            for j in range(1, l):
                i = start + j
                if i > nbase:
                    i -= nbase + 1
                bases[i].x = bases[start].x + dx * j / l
                bases[i].y = bases[start].y + dy * j / l
        else:
            h, angleinc = self._find_center_for_arc(l - 1, rr)
            dx /= rr
            dy /= rr
            midx = bases[start].x + dx * rr / 2.0
            midy = bases[start].y + dy * rr / 2.0
            xn = dy
            yn = -dx
            nrx = midx + h * xn
            nry = midy + h * yn
            mx = bases[start].x - nrx
            my = bases[start].y - nry
            rr2 = math.sqrt(mx * mx + my * my)
            a = math.atan2(my, mx)
            for j in range(1, l):
                i = start + j
                if i > nbase:
                    i -= nbase + 1
                bases[i].x = nrx + rr2 * math.cos(a + j * angleinc)
                bases[i].y = nry + rr2 * math.sin(a + j * angleinc)

    def _construct_extruded_segment(self, cp, cpnext):
        bases = self.bases
        nbase = self.nbase

        astart = cp.angle
        aend2 = aend1 = cpnext.angle
        if aend2 < astart:
            aend2 += 2 * PI
        aave = (astart + aend2) / 2.0
        start = cp.end
        end = cpnext.start
        n = end - start
        if n < 0:
            n += nbase + 1
        da = cpnext.angle - cp.angle
        if da < 0.0:
            da += 2 * PI

        if n == 2:
            self._construct_circle_segment(start, end)
            return

        dx = bases[end].x - bases[start].x
        dy = bases[end].y - bases[start].y
        rr = math.sqrt(dx * dx + dy * dy)
        if rr == 0.0:
            return
        dx /= rr
        dy /= rr
        if rr >= 1.5 and da <= PI / 2:
            nstart = start + 1
            if nstart > nbase:
                nstart -= nbase + 1
            nend = end - 1
            if nend < 0:
                nend += nbase + 1
            bases[nstart].x = bases[start].x + 0.5 * dx
            bases[nstart].y = bases[start].y + 0.5 * dy
            bases[nend].x = bases[end].x - 0.5 * dx
            bases[nend].y = bases[end].y - 0.5 * dy
            start = nstart
            end = nend

        guard = 0
        while True:
            guard += 1
            if guard > nbase + 4:
                break
            collision = False
            self._construct_circle_segment(start, end)
            nstart = start + 1
            if nstart > nbase:
                nstart -= nbase + 1
            dx = bases[nstart].x - bases[start].x
            dy = bases[nstart].y - bases[start].y
            a1 = math.atan2(dy, dx)
            if a1 < 0.0:
                a1 += 2 * PI
            dac = a1 - astart
            if dac < 0.0:
                dac += 2 * PI
            if dac > PI:
                collision = True
            nend = end - 1
            if nend < 0:
                nend += nbase + 1
            dx = bases[nend].x - bases[end].x
            dy = bases[nend].y - bases[end].y
            a2 = math.atan2(dy, dx)
            if a2 < 0.0:
                a2 += 2 * PI
            dac = aend1 - a2
            if dac < 0.0:
                dac += 2 * PI
            if dac > PI:
                collision = True
            if not collision:
                break
            ac = min(aave, astart + 0.5)
            bases[nstart].x = bases[start].x + math.cos(ac)
            bases[nstart].y = bases[start].y + math.sin(ac)
            start = nstart
            ac = max(aave, aend2 - 0.5)
            bases[nend].x = bases[end].x + math.cos(ac)
            bases[nend].y = bases[end].y + math.sin(ac)
            end = nend
            n -= 2
            if n <= 1:
                break

    # -- step 8: the workhorse -------------------------------------------

    def _traverse_loop(self, lp, anchor_connection):
        nbase = self.nbase
        bases = self.bases
        conns = lp.connections
        nconn = len(conns)
        if nconn == 0:
            return

        angleinc = 2 * PI / (nbase + 1)
        acp = None
        icroot = -1
        for ic in range(nconn):
            cp = conns[ic]
            xs = -math.sin(angleinc * cp.start)
            ys = math.cos(angleinc * cp.start)
            xe = -math.sin(angleinc * cp.end)
            ye = math.cos(angleinc * cp.end)
            xn = ye - ys
            yn = xs - xe
            r = math.sqrt(xn * xn + yn * yn)
            if r == 0.0:
                r = 1e-12
            cp.xrad = xn / r
            cp.yrad = yn / r
            cp.angle = math.atan2(yn, xn)
            if cp.angle < 0.0:
                cp.angle += 2 * PI
            if (anchor_connection is not None
                    and anchor_connection.region is cp.region):
                acp = cp
                icroot = ic

        if self.even_loops and nconn >= 2:
            # A radius estimate is needed to know how much of the circle one
            # base pair occupies; after re-spacing the gaps, lp.radius is reset
            # so the main loop below re-fits it for the new angles.
            self._determine_radius(lp, LENCUT)
            self._even_connection_angles(lp)
            lp.radius = 0.0

        # 'set_radius' is a goto target in the C original; here the whole
        # body lives in a loop that we restart when a crossing is found.
        restart = True
        guard = 0
        while restart:
            restart = False
            guard += 1
            if guard > 3 * (nconn + 1):
                self._warn('traverse_loop: too many radius restarts, giving up')
                break

            self._determine_radius(lp, LENCUT)
            radius = lp.radius
            if anchor_connection is None:
                xc = yc = 0.0
            else:
                xo = (bases[acp.start].x + bases[acp.end].x) / 2.0
                yo = (bases[acp.start].y + bases[acp.end].y) / 2.0
                xc = xo - radius * acp.xrad
                yc = yo - radius * acp.yrad

            # ---- find the start of a block of connected connectors ----
            icstart = 0 if icroot == -1 else icroot
            cp = conns[icstart]
            count = 0
            while True:
                j = icstart - 1
                if j < 0:
                    j = nconn - 1
                cpprev = conns[j]
                if not self._connected(cpprev, cp):
                    break
                icstart = j
                cp = cpprev
                count += 1
                if count > nconn:
                    # everything is connected: break at the widest angular gap
                    maxang = -1.0
                    imaxloop = 0
                    for ic in range(nconn):
                        j = ic + 1
                        if j >= nconn:
                            j = 0
                        c1 = conns[ic]
                        c2 = conns[j]
                        ac = c2.angle - c1.angle
                        if ac < 0.0:
                            ac += 2 * PI
                        if ac > maxang:
                            maxang = ac
                            imaxloop = ic
                    icend = imaxloop
                    icstart = imaxloop + 1
                    if icstart >= nconn:
                        icstart = 0
                    conns[icend].broken = True
                    break

            # ---- walk the blocks of connected connectors ----
            done_all_connections = False
            icstart1 = icstart
            block_guard = 0
            while not done_all_connections:
                block_guard += 1
                if block_guard > 4 * (nconn + 1):
                    self._warn('traverse_loop: block walk did not converge')
                    break

                count = 0
                icend = icstart
                rooted = False
                while True:
                    cp = conns[icend]
                    if icend == icroot:
                        rooted = True
                    j = icend + 1
                    if j >= nconn:
                        j = 0
                    cpnext = conns[j]
                    if self._connected(cp, cpnext):
                        count += 1
                        if count >= nconn:
                            break
                        icend = j
                    else:
                        break

                icmiddle = self._find_ic_middle(
                    icstart, icend, anchor_connection, acp, lp)
                ic = icup = icdown = icmiddle
                direction = 0
                spin_guard = 0
                while True:
                    spin_guard += 1
                    if spin_guard > 8 * (nconn + 1):
                        self._warn('traverse_loop: connector walk did not converge')
                        break
                    if direction < 0:
                        ic = icup
                    elif direction == 0:
                        ic = icmiddle
                    else:
                        ic = icdown
                    if ic >= 0:
                        cp = conns[ic]
                        if anchor_connection is None or acp is not cp:
                            if direction == 0:
                                astart = cp.angle - math.asin(1.0 / 2.0 / radius)
                                aend = cp.angle + math.asin(1.0 / 2.0 / radius)
                                bases[cp.start].x = xc + radius * math.cos(astart)
                                bases[cp.start].y = yc + radius * math.sin(astart)
                                bases[cp.end].x = xc + radius * math.cos(aend)
                                bases[cp.end].y = yc + radius * math.sin(aend)
                            elif direction < 0:
                                j = ic + 1
                                if j >= nconn:
                                    j = 0
                                cpx = cp.xrad
                                cpy = cp.yrad
                                cpnext = conns[j]
                                ac = (cp.angle + cpnext.angle) / 2.0
                                if cp.angle > cpnext.angle:
                                    ac -= PI
                                cnx = math.cos(ac)
                                cny = math.sin(ac)
                                lnx = cny
                                lny = -cnx
                                da = cpnext.angle - cp.angle
                                if da < 0.0:
                                    da += 2 * PI
                                if cp.extruded:
                                    rl = 2.0 if da <= PI / 2 else 1.5
                                else:
                                    rl = 1.0
                                bases[cp.end].x = bases[cpnext.start].x + rl * lnx
                                bases[cp.end].y = bases[cpnext.start].y + rl * lny
                                bases[cp.start].x = bases[cp.end].x + cpy
                                bases[cp.start].y = bases[cp.end].y - cpx
                            else:
                                j = ic - 1
                                if j < 0:
                                    j = nconn - 1
                                cp = conns[j]
                                cpnext = conns[ic]
                                cpnextx = cpnext.xrad
                                cpnexty = cpnext.yrad
                                ac = (cp.angle + cpnext.angle) / 2.0
                                if cp.angle > cpnext.angle:
                                    ac -= PI
                                cnx = math.cos(ac)
                                cny = math.sin(ac)
                                lnx = -cny
                                lny = cnx
                                da = cpnext.angle - cp.angle
                                if da < 0.0:
                                    da += 2 * PI
                                if cp.extruded:
                                    rl = 2.0 if da <= PI / 2 else 1.5
                                else:
                                    rl = 1.0
                                bases[cpnext.start].x = bases[cp.end].x + rl * lnx
                                bases[cpnext.start].y = bases[cp.end].y + rl * lny
                                bases[cpnext.end].x = bases[cpnext.start].x - cpnexty
                                bases[cpnext.end].y = bases[cpnext.start].y + cpnextx
                    if direction < 0:
                        if icdown == icend:
                            icdown = -1
                        elif icdown >= 0:
                            icdown += 1
                            if icdown >= nconn:
                                icdown = 0
                        direction = 1
                    else:
                        if icup == icstart:
                            icup = -1
                        elif icup >= 0:
                            icup -= 1
                            if icup < 0:
                                icup = nconn - 1
                        direction = -1
                    if icup == -1 and icdown == -1:
                        break

                icnext = icend + 1
                if icnext >= nconn:
                    icnext = 0
                if icend != icstart and not (icstart == icstart1
                                             and icnext == icstart1):
                    cp = conns[icstart]
                    cpnext = conns[icend]
                    dx = bases[cpnext.end].x - bases[cp.start].x
                    dy = bases[cpnext.end].y - bases[cp.start].y
                    midx = bases[cp.start].x + dx / 2.0
                    midy = bases[cp.start].y + dy / 2.0
                    rr = math.sqrt(dx * dx + dy * dy)
                    if rr == 0.0:
                        rr = 1e-12
                    mx = dx / rr
                    my = dy / rr
                    vx = xc - midx
                    vy = yc - midy
                    # NOTE: the original recomputes the *chord* length here
                    # rather than |v|; reproduced deliberately.
                    rr = math.sqrt(dx * dx + dy * dy)
                    if rr == 0.0:
                        rr = 1e-12
                    vx /= rr
                    vy /= rr
                    dotmv = vx * mx + vy * my
                    nrx = dotmv * mx - vx
                    nry = dotmv * my - vy
                    rr = math.sqrt(nrx * nrx + nry * nry)
                    if rr == 0.0:
                        rr = 1e-12
                    nrx /= rr
                    nry /= rr

                    dx = bases[cp.start].x - xc
                    dy = bases[cp.start].y - yc
                    ac = math.atan2(dy, dx)
                    if ac < 0.0:
                        ac += 2 * PI
                    dx = bases[cpnext.end].x - xc
                    dy = bases[cpnext.end].y - yc
                    acn = math.atan2(dy, dx)
                    if acn < 0.0:
                        acn += 2 * PI
                    if acn < ac:
                        acn += 2 * PI
                    sign = -1 if (acn - ac) > PI else 1
                    nmidx = xc + sign * radius * nrx
                    nmidy = yc + sign * radius * nry
                    if rooted:
                        xc -= nmidx - midx
                        yc -= nmidy - midy
                    else:
                        ic = icstart
                        shift_guard = 0
                        while True:
                            shift_guard += 1
                            if shift_guard > nconn + 2:
                                break
                            c2 = conns[ic]
                            i = c2.start
                            bases[i].x += nmidx - midx
                            bases[i].y += nmidy - midy
                            i = c2.end
                            bases[i].x += nmidx - midx
                            bases[i].y += nmidy - midy
                            if ic == icend:
                                break
                            ic += 1
                            if ic >= nconn:
                                ic = 0
                icstart = icnext
                done_all_connections = (icstart == icstart1)

            # ---- place unpaired stretches / extruded segments ----
            for ic in range(nconn):
                cp = conns[ic]
                j = ic + 1
                if j >= nconn:
                    j = 0
                cpnext = conns[j]
                dx = bases[cp.end].x - xc
                dy = bases[cp.end].y - yc
                rc = math.sqrt(dx * dx + dy * dy)
                ac = math.atan2(dy, dx)
                if ac < 0.0:
                    ac += 2 * PI
                dx = bases[cpnext.start].x - xc
                dy = bases[cpnext.start].y - yc
                rcn = math.sqrt(dx * dx + dy * dy)
                acn = math.atan2(dy, dx)
                if acn < 0.0:
                    acn += 2 * PI
                if acn < ac:
                    acn += 2 * PI
                dan = acn - ac
                dcp = cpnext.angle - cp.angle
                if dcp <= 0.0:
                    dcp += 2 * PI
                if abs(dan - dcp) > PI:
                    if cp.extruded:
                        self._warn(
                            'loop %d has crossed regions' % lp.number)
                    elif (cpnext.start - cp.end) != 1:
                        cp.extruded = True
                        restart = True
                        break
                if cp.extruded:
                    self._construct_extruded_segment(cp, cpnext)
                else:
                    n = cpnext.start - cp.end
                    if n < 0:
                        n += nbase + 1
                    if n <= 0 or dan == 0.0:
                        continue
                    angleinc = dan / n
                    for jj in range(1, n):
                        i = cp.end + jj
                        if i > nbase:
                            i -= nbase + 1
                        a = ac + jj * angleinc
                        rr = rc + (rcn - rc) * (a - ac) / dan
                        bases[i].x = xc + rr * math.cos(a)
                        bases[i].y = yc + rr * math.sin(a)
            if restart:
                continue

            # ---- recurse into child loops ----
            for ic in range(nconn):
                if icroot != ic:
                    cp = conns[ic]
                    self._generate_region(cp)
                    self._traverse_loop(cp.loop, cp)

            # ---- centroid of the loop (unused by the drawing itself) ----
            n = 0
            sx = 0.0
            sy = 0.0
            for ic in range(nconn):
                j = ic + 1
                if j >= nconn:
                    j = 0
                cp = conns[ic]
                cpnext = conns[j]
                n += 2
                sx += bases[cp.start].x + bases[cp.end].x
                sy += bases[cp.start].y + bases[cp.end].y
                if not cp.extruded:
                    jj = cp.end + 1
                    g = 0
                    while jj != cpnext.start:
                        if jj > nbase:
                            jj -= nbase + 1
                        n += 1
                        sx += bases[jj].x
                        sy += bases[jj].y
                        jj += 1
                        g += 1
                        if g > nbase + 2:
                            break
            lp.x = sx / n if n else 0.0
            lp.y = sy / n if n else 0.0
            break

    # -- driver ----------------------------------------------------------

    @staticmethod
    def _arc_chain(nchords, d):
        """Radius and half-angle for an arc of *nchords* unit chords with
        chord *d*.

        The reference ``find_center_for_arc`` only works when ``d >= 1`` (its
        bisection evaluates ``acos`` outside its domain and gives up
        otherwise), which is exactly the case that matters for a squeezed
        bulge.  Solving it directly is easy: with ``nchords`` equal chords of
        length 1 spanning a total angle ``2 * nchords * alpha``,

            1 = 2 R sin(alpha)      d = 2 R sin(nchords * alpha)

        so ``d = sin(nchords*alpha) / sin(alpha)``, which is strictly
        decreasing in alpha on ``(0, pi/nchords)``.  Returns ``(R, alpha)``
        or ``None`` when no arc fits.
        """
        if d <= 0.0 or d >= nchords or nchords < 2:
            return None
        lo, hi = 1e-12, math.pi / nchords
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if math.sin(nchords * mid) / math.sin(mid) > d:
                lo = mid
            else:
                hi = mid
        alpha = 0.5 * (lo + hi)
        if math.sin(alpha) < 1e-12:
            return None
        return 1.0 / (2.0 * math.sin(alpha)), alpha

    def _even_bond_lengths(self):
        """Give every unpaired stretch a well-shaped backbone chain.

        NAView lays the unpaired bases of a loop on the arc between the two
        bases that flank the stretch.  When those two anchors sit closer than
        the number of bonds between them the arc is too short, and the bases
        end up squashed onto the straight line joining them -- a single-base
        bulge collapses to under half a bond length and its letter overlaps
        its neighbours.

        This pass rebuilds such a stretch as either

        * a straight chain of equal bonds, when the anchors are far enough
          apart, or
        * a circular arc whose chords are exactly one unit, when they are not
          -- the bases then bulge out of the line, which is what a real bulge
          looks like.

        Two guards keep it from doing harm:

        * a stretch is only touched when its worst bond is below ``MIN_BOND``,
          so a healthy hairpin loop is left exactly as NAView drew it;
        * the new positions are kept only when the worst bond actually
          improves, otherwise the original coordinates stay.

        The anchors are never moved, so helices stay intact.
        """
        bases = self.bases
        nbase = self.nbase
        touched = 0
        for lp in self.loops:
            conns = lp.connections
            nconn = len(conns)
            if nconn == 0:
                continue
            for ic in range(nconn):
                cp = conns[ic]
                cpnext = conns[(ic + 1) % nconn]
                start = cp.end
                end = cpnext.start
                steps = end - start
                if steps < 0:
                    steps += nbase + 1
                if steps <= 1:
                    continue                      # no unpaired base in between

                idx = []
                for j in range(steps + 1):
                    i = start + j
                    if i > nbase:
                        i -= nbase + 1
                    idx.append(i)
                if any(bases[i].x > ANUM - 100.0 for i in idx):
                    continue                      # not placed yet
                idx_set = set(i for i in idx if i > 0)

                old = [math.hypot(bases[idx[j + 1]].x - bases[idx[j]].x,
                                  bases[idx[j + 1]].y - bases[idx[j]].y)
                       for j in range(steps)]
                if min(old) >= MIN_BOND:
                    continue                      # already fine, leave it

                ax, ay = bases[start].x, bases[start].y
                bx, by = bases[end].x, bases[end].y
                dx = bx - ax
                dy = by - ay
                d = math.hypot(dx, dy)
                if d < 1e-9:
                    continue

                new = [(ax, ay)]
                if d >= steps:
                    for j in range(1, steps):     # straight chain, bonds >= 1
                        t = j / float(steps)
                        new.append((ax + dx * t, ay + dy * t))
                else:
                    arc = self._arc_chain(steps, d)
                    if arc is None:
                        continue
                    radius, alpha = arc
                    ux, uy = dx / d, dy / d
                    nx_u, ny_u = -uy, ux
                    midx = ax + dx * 0.5
                    midy = ay + dy * 0.5
                    half = math.sqrt(max(0.0, radius * radius - (d * 0.5) ** 2))
                    span = 2.0 * alpha
                    # The arc's centre may sit on either side of the anchor
                    # chord, giving two mirror-image bumps.  Build both and
                    # keep the one that stays furthest from every other base
                    # -- that is what stops a bulge from being drawn straight
                    # into the helix next to it.
                    others = [(bases[i].x, bases[i].y)
                              for i in range(1, nbase + 1) if i not in idx_set]
                    best = None
                    for sn in (1.0, -1.0):
                        cx = midx + sn * half * nx_u
                        cy = midy + sn * half * ny_u
                        if math.hypot(ax - cx, ay - cy) < 1e-9:
                            continue
                        a0 = math.atan2(ay - cy, ax - cx)
                        a1 = math.atan2(by - cy, bx - cx)
                        sgn = (1.0 if _angdiff(a0 + steps * span, a1)
                               < _angdiff(a0 - steps * span, a1) else -1.0)
                        pts = []
                        for j in range(1, steps):
                            a = a0 + sgn * j * span
                            pts.append((cx + radius * math.cos(a),
                                        cy + radius * math.sin(a)))
                        if others:
                            clear = min(math.hypot(px - ox, py - oy)
                                        for px, py in pts for ox, oy in others)
                        else:
                            clear = float('inf')
                        if best is None or clear > best[0]:
                            best = (clear, pts)
                    if best is None:
                        continue
                    new.extend(best[1])
                new.append((bx, by))

                spread = [math.hypot(new[j + 1][0] - new[j][0],
                                     new[j + 1][1] - new[j][1])
                          for j in range(steps)]
                if min(spread) <= min(old):
                    continue                      # not an improvement
                for j in range(1, steps):
                    bases[idx[j]].x = new[j][0]
                    bases[idx[j]].y = new[j][1]
                touched += steps - 1
        return touched

    def solve(self):
        if self.nbase == 0:
            return Layout([], [], self.st, [], None, [])
        old_limit = sys.getrecursionlimit()
        need = max(old_limit, 100 + 40 * self.nbase)
        sys.setrecursionlimit(need)
        try:
            self._read_in_bases()
            self._find_regions()
            self._construct_loop(0)
            self._find_central_loop()
            self._traverse_loop(self.root, None)
            if self.even_bonds:
                self._even_bond_lengths()
        finally:
            sys.setrecursionlimit(old_limit)

        xs = [0.0] * self.nbase
        ys = [0.0] * self.nbase
        for i in range(1, self.nbase + 1):
            xs[i - 1] = self.bases[i].x
            ys[i - 1] = self.bases[i].y
        return Layout(xs, ys, self.st, self.loops, self.root, self.warnings)


# --------------------------------------------------------------------------
#  Public functions
# --------------------------------------------------------------------------

CONTACT_DISTANCE = 0.6      # below this two base letters would collide


def layout_cost(layout, contact=CONTACT_DISTANCE):
    """How bad a layout is: ``(crowded_pairs, bond_spread)``, lower is better.

    ``crowded_pairs`` counts pairs of bases that are close on the figure but
    are not neighbours on the backbone -- those are the ones whose letters
    visibly overlap, which matters much more than even spacing.
    """
    xs, ys = layout.xs, layout.ys
    n = len(xs)
    if n < 2:
        return (0, 1.0)
    bonds = [math.hypot(xs[i + 1] - xs[i], ys[i + 1] - ys[i])
             for i in range(n - 1)]
    lo = min(bonds)
    spread = (max(bonds) / lo) if lo > 1e-12 else float('inf')
    crowded = 0
    for a in range(n):
        for b in range(a + 2, n):
            if math.hypot(xs[a] - xs[b], ys[a] - ys[b]) < contact:
                crowded += 1
    return (crowded, spread)


def naview_layout(structure, even_loops='auto', even_bonds=True):
    """Run NAView on a :class:`Structure` and return a :class:`Layout`.

    ``even_bonds=True`` (the default) adds a post-step that re-shapes any
    unpaired stretch whose bonds are too short, so a lone base in a bulge
    bulges out instead of being squashed between its neighbours (see
    :meth:`_NAView._even_bond_lengths`).

    ``even_loops`` controls the other post-step, which re-spaces the angles
    around a loop so a long dangling end is not squeezed while a short gap is
    stretched (:meth:`_NAView._even_connection_angles`).  It helps structures
    with a long dangling end a lot, but it moves the whole figure and can
    crowd a small bulge, so the default ``'auto'`` lays the structure out both
    ways and keeps whichever scores better on :func:`layout_cost`.

    ``even_loops=False, even_bonds=False`` gives the reference NAView output,
    bit for bit.  That is the mode ``tests/compare_vienna.py`` validates
    against ViennaRNA, and the mode to use when you need to match another
    NAView implementation.
    """
    if not isinstance(structure, Structure):
        raise TypeError('expected a Structure, got %r' % type(structure))
    if even_loops == 'auto':
        plain = _NAView(structure, even_loops=False, even_bonds=even_bonds)
        plain = plain.solve()
        evened = _NAView(structure, even_loops=True, even_bonds=even_bonds)
        evened = evened.solve()
        if layout_cost(evened) < layout_cost(plain):
            return evened
        return plain
    return _NAView(structure, even_loops=bool(even_loops),
                   even_bonds=even_bonds).solve()


def naview_coords(ss, even_loops='auto', even_bonds=True):
    """Convenience wrapper: dot-bracket string -> ``(xs, ys)``.

    >>> xs, ys = naview_coords('((((....))))')
    >>> len(xs), len(ys)
    (12, 12)
    """
    return naview_layout(parse_dot_bracket(ss), even_loops=even_loops,
                         even_bonds=even_bonds).as_coords()


# --------------------------------------------------------------------------
#  Geometry helpers (for tests and for comparing with other tools)
# --------------------------------------------------------------------------

def _centre(pts):
    n = len(pts)
    return sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n


def similarity_transform(moving, target, allow_scale=True):
    """Best rotation (+ optional uniform scale) + translation mapping
    *moving* onto *target*.

    Both point sets are 2-D, so the optimal rotation angle is available in
    closed form and no SVD is needed.

    Returns ``(scale, cos_a, sin_a, tx, ty)``.
    """
    if len(moving) != len(target):
        raise ValueError('point sets must have the same length')
    if not moving:
        return 1.0, 1.0, 0.0, 0.0, 0.0

    mcx, mcy = _centre(moving)
    tcx, tcy = _centre(target)

    sxx = sxy = syx = syy = 0.0
    for (mx, my), (tx, ty) in zip(moving, target):
        mx -= mcx
        my -= mcy
        tx -= tcx
        ty -= tcy
        sxx += mx * tx
        sxy += mx * ty
        syx += my * tx
        syy += my * ty

    # H = [[sxx, sxy], [syx, syy]]; the rotation maximising trace(R H)
    # has angle atan2(sxy - syx, sxx + syy).
    theta = math.atan2(sxy - syx, sxx + syy)
    cos_a = math.cos(theta)
    sin_a = math.sin(theta)

    if allow_scale:
        num = den = 0.0
        for (mx, my), (tx, ty) in zip(moving, target):
            mx -= mcx
            my -= mcy
            rx = cos_a * mx - sin_a * my
            ry = sin_a * mx + cos_a * my
            num += rx * (tx - tcx) + ry * (ty - tcy)
            den += mx * mx + my * my
        scale = num / den if den else 1.0
    else:
        scale = 1.0

    tx = tcx - scale * (cos_a * mcx - sin_a * mcy)
    ty = tcy - scale * (sin_a * mcx + cos_a * mcy)
    return scale, cos_a, sin_a, tx, ty


def rmsd(moving, target, allow_scale=True):
    """Root-mean-square deviation after optimal superposition."""
    if len(moving) != len(target):
        raise ValueError('point sets must have the same length')
    if not moving:
        return 0.0
    scale, cos_a, sin_a, tx, ty = similarity_transform(
        moving, target, allow_scale=allow_scale)
    total = 0.0
    for (mx, my), (txx, tyy) in zip(moving, target):
        rx = scale * (cos_a * mx - sin_a * my) + tx
        ry = scale * (sin_a * mx + cos_a * my) + ty
        total += (rx - txx) ** 2 + (ry - tyy) ** 2
    return math.sqrt(total / len(moving))
