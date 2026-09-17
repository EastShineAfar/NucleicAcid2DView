#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Headless-ish smoke test for the tkinter GUI.

Creates the real window, exercises preview / style switching / colour changes /
SVG export without entering the event loop, then tears it down.  Run it after
changing gui.py to catch wiring mistakes that a screenshot would not show.

    python tests/test_gui.py
"""

import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

# Keep the test deterministic: never read or write the user's real settings.
_TMPDIR = tempfile.mkdtemp(prefix='naview-gui-')
os.environ['NAVIEW_SETTINGS'] = os.path.join(_TMPDIR, 'gui-settings.json')

RESULTS = []


def check(cond, label, detail=''):
    RESULTS.append((bool(cond), label, detail))
    return bool(cond)


def main():
    try:
        import tkinter as tk
    except ImportError as exc:
        print('tkinter unavailable (%s) -- GUI test skipped' % exc)
        return 0

    try:
        root_probe = tk.Tk()
        root_probe.destroy()
    except Exception as exc:
        print('no display available (%s) -- GUI test skipped' % exc)
        return 0

    import gui
    from naview import parse_dot_bracket, naview_layout

    app = gui.DrawApp()
    try:
        app.update()              # map the window so widget sizes are real
        app.update_idletasks()

        # ---- 0. every panel must actually get space -----------------
        check(app.panel.winfo_width() > 200,
              'sidebar keeps its width (not squeezed by the preview)',
              'width=%d' % app.panel.winfo_width())
        check(app.canvas.winfo_width() > 100,
              'canvas has a usable width',
              'width=%d' % app.canvas.winfo_width())
        check(app.canvas.winfo_rootx() < app.panel.winfo_rootx(),
              'preview sits to the LEFT of the sidebar',
              'canvas x=%d, panel x=%d'
              % (app.canvas.winfo_rootx(), app.panel.winfo_rootx()))
        check(app.canvas.winfo_width() > app.panel.winfo_width(),
              'preview is wider than the sidebar',
              'canvas=%d, panel=%d'
              % (app.canvas.winfo_width(), app.panel.winfo_width()))
        check(app.status_label.winfo_height() > 5,
              'status bar is visible',
              'height=%d' % app.status_label.winfo_height())

        # ---- 1. startup preview -------------------------------------
        app.seq_var.set('GCGCAAAAGCGC')
        app.ss_var.set('((((....))))')
        app.do_preview()
        app.update_idletasks()
        check(app.layout is not None, 'preview produced a layout')
        check(len(app.layout.xs) == 12, 'layout has 12 bases',
              'got %d' % len(app.layout.xs))
        check(len(app.canvas.find_all()) > 0, 'canvas has drawn items',
              '%d items' % len(app.canvas.find_all()))

        n_items_single = len(app.canvas.find_all())

        # ---- 2. structure recorded in the status bar ----------------
        check('12 个碱基' in app.status_var.get(),
              'status reports 12 bases', app.status_var.get())

        # ---- 3. single vs double pair lines --------------------------
        app.pair_style.set('double')
        app._on_style_change()
        app.update_idletasks()
        n_items_double = len(app.canvas.find_all())
        check(n_items_double > n_items_single,
              'double pair style draws more lines',
              'single=%d double=%d' % (n_items_single, n_items_double))
        app.pair_style.set('single')
        app._on_style_change()
        app.update_idletasks()
        check(len(app.canvas.find_all()) == n_items_single,
              'back to single pair style restores the item count')

        # ---- 4. colour changes reach the primitives ------------------
        app._set_color('ring', 'A', '#123456')
        app._refresh_prims()
        fills = [p['fill'] for p in app.prims
                 if p['kind'] == 'circle' and p['fill'] == '#123456']
        check(len(fills) > 0, 'custom ring colour reaches the primitives',
              'found %d' % len(fills))

        app._set_color('letter', 'C', '#abcdef')
        app._refresh_prims()
        letters = [p['fill'] for p in app.prims
                   if p['kind'] == 'text' and p['fill'] == '#abcdef']
        check(len(letters) > 0, 'custom letter colour reaches the primitives',
              'found %d' % len(letters))

        # ---- 4b. font size / ring radius / orientation ----------------
        app.font_size_var.set(13.0)
        app.ring_radius_var.set(9.0)
        app._on_style_change()
        sizes = {p['size'] for p in app.prims if p['kind'] == 'text'}
        check(sizes == {13.0}, 'font size control reaches text primitives',
              'got %r' % sorted(sizes))
        radii = {p['r'] for p in app.prims if p['kind'] == 'circle'}
        check(9.0 in radii, 'ring radius control reaches circle primitives',
              'got %r' % sorted(radii))

        # ---- 4c. the three line widths are independent ---------------
        app.backbone_w_var.set(2.5)
        app.pair_w_var.set(3.5)
        app.ring_w_var.set(1.5)
        app._on_style_change()
        by_stroke = {}
        for p in app.prims:
            if p['kind'] == 'line':
                by_stroke.setdefault(p['stroke'], set()).add(p['width'])
        bb = by_stroke.get(app.style['backbone'], set())
        pr = by_stroke.get(app.style['pair'], set())
        ring_w = {p['width'] for p in app.prims if p['kind'] == 'circle'}
        check(bb == {2.5}, 'backbone line width is applied', 'got %r' % bb)
        check(pr == {3.5}, 'pair line width is applied', 'got %r' % pr)
        check(ring_w == {1.5}, 'ring stroke width is applied', 'got %r' % ring_w)
        check(len({bb and list(bb)[0], pr and list(pr)[0],
                   list(ring_w)[0]}) == 3,
              'the three line widths are independent of each other')

        def first_base_cy():
            texts = [p for p in app.prims if p['kind'] == 'text']
            return texts[0]['cy'] if texts else None

        app.flip_var.set(True)
        app._on_style_change()
        cy_bottom = first_base_cy()
        h1 = app.fig_h
        check(cy_bottom is not None and cy_bottom > h1 / 2.0,
              '起点在下方 puts the first base at the bottom',
              'cy=%.1f of height %.1f' % (cy_bottom or -1, h1))

        app.flip_var.set(False)
        app._on_style_change()
        cy_top = first_base_cy()
        h2 = app.fig_h
        check(cy_top is not None and cy_top < h2 / 2.0,
              'unchecking 起点在下方 puts the first base at the top',
              'cy=%.1f of height %.1f' % (cy_top or -1, h2))
        check(abs(h1 - h2) < 1e-6,
              'flipping does not change the figure size',
              '%.2f vs %.2f' % (h1, h2))
        app.flip_var.set(True)

        # ---- 4d. rotation turns the picture, not the letters ---------
        app.rotation_var.set(0.0)
        app._on_rotate()
        layout_before = app.layout
        texts0 = [(p['cx'], p['cy'], p['text'], p['size'])
                  for p in app.prims if p['kind'] == 'text']
        n_prims0 = len(app.prims)
        size0 = (app.fig_w, app.fig_h)

        app.rotation_var.set(90.0)
        app._on_rotate()
        texts90 = [(p['cx'], p['cy'], p['text'], p['size'])
                   for p in app.prims if p['kind'] == 'text']
        size90 = (app.fig_w, app.fig_h)

        check(app.layout is layout_before,
              'rotation does not trigger a re-layout')
        check([t[2] for t in texts0] == [t[2] for t in texts90],
              'rotation keeps the letters themselves')
        check([t[3] for t in texts0] == [t[3] for t in texts90],
              'rotation keeps the font size, so letters stay upright')
        check([(t[0], t[1]) for t in texts0] != [(t[0], t[1]) for t in texts90],
              'rotation actually moves the coordinates')
        check(abs(size0[0] - size90[1]) < 1e-6
              and abs(size0[1] - size90[0]) < 1e-6,
              'a 90 degree turn swaps the figure dimensions',
              '%.1fx%.1f -> %.1fx%.1f' % (size0 + size90))
        check(len(app.prims) == n_prims0,
              'rotation keeps the primitive count',
              '%d -> %d' % (n_prims0, len(app.prims)))

        app.rotation_var.set(360.0)
        app._on_rotate()
        check(app._rotation() == 0.0, '360 degrees normalises to 0',
              'got %r' % app._rotation())
        app.rotation_var.set(0.0)
        app._on_rotate()

        # ---- 5. ring stroke / backbone / pair colours ----------------
        app._set_color('pair', None, '#00aa00')
        app._refresh_prims()
        pair_lines = [p for p in app.prims
                      if p['kind'] == 'line' and p['stroke'] == '#00aa00']
        check(len(pair_lines) == 4, 'custom pair colour used for 4 pair lines',
              'got %d' % len(pair_lines))

        # ---- 6. hide toggles ----------------------------------------
        app.show_bb_var.set(False)
        app._on_style_change()
        check(not any(p['kind'] == 'line' and p['stroke'] == app.style['backbone']
                      for p in app.prims),
              'backbone toggle removes backbone lines')
        app.show_bb_var.set(True)

        # ---- 7. reset to factory defaults ---------------------------
        app._set_color('ring', 'A', '#ff00ff')
        app.font_size_var.set(22.0)
        app.ring_radius_var.set(3.0)
        app.backbone_w_var.set(4.0)
        app.pair_w_var.set(4.0)
        app.ring_w_var.set(4.0)
        app.flip_var.set(False)
        app._reset_defaults()
        check(app.style['ring']['A'] == gui.DEFAULT_RING_COLORS['A'],
              'reset restores default ring colour')
        check(app.style['letter']['C'] == gui.DEFAULT_LETTER_COLORS['C'],
              'reset restores default letter colour')
        check(app.font_size_var.get() == gui.DEFAULT_FONT_SIZE,
              'reset restores the default font size',
              'got %r' % app.font_size_var.get())
        check(app.ring_radius_var.get() == gui.DEFAULT_RING_RADIUS,
              'reset restores the default ring radius',
              'got %r' % app.ring_radius_var.get())
        check(app.backbone_w_var.get() == gui.DEFAULT_LINE_WIDTH
              and app.pair_w_var.get() == gui.DEFAULT_LINE_WIDTH
              and app.ring_w_var.get() == gui.DEFAULT_LINE_WIDTH,
              'reset restores the default line widths')
        check(app.flip_var.get() is True
              or app.flip_var.get() == True,                       # noqa: E712
              'reset restores the default orientation')

        # ---- 7b. 保存为默认 persists the parameters ----------------
        app._set_color('ring', 'G', '#112233')
        app._set_color('pair', None, '#445566')
        app.font_size_var.set(9.5)
        app.ring_radius_var.set(7.25)
        app.backbone_w_var.set(0.75)
        app.pair_w_var.set(2.5)
        app.ring_w_var.set(0.5)
        app.pair_style.set('double')
        app.flip_var.set(False)
        app.even_var.set(False)
        app.rotation_var.set(135.0)
        app._save_defaults()

        saved = gui.settings.load()
        check(saved['ring_colors']['G'] == '#112233',
              '保存为默认 stored the ring colour',
              'got %r' % saved['ring_colors'].get('G'))
        check(saved['pair_color'] == '#445566',
              '保存为默认 stored the line colour')
        check(saved['font_size'] == 9.5 and saved['ring_radius'] == 7.25,
              '保存为默认 stored the sizes')
        check(saved['backbone_width'] == 0.75 and saved['pair_width'] == 2.5
              and saved['ring_width'] == 0.5,
              '保存为默认 stored the three line widths')
        check(saved['pair_style'] == 'double', '保存为默认 stored 双横线')
        check(saved['flip_y'] is False, '保存为默认 stored 起点在上方')
        check(saved['even_loops'] is False, '保存为默认 stored 自动优化间距 off')
        check(saved['rotation'] == 135.0, '保存为默认 stored the rotation',
              'got %r' % saved.get('rotation'))

        # a fresh window must come up with exactly those parameters
        app.destroy()
        fresh = gui.DrawApp()
        app = fresh
        fresh.update()
        check(fresh.style['ring']['G'] == '#112233',
              'a new window starts from the saved ring colour')
        check(fresh._num(fresh.font_size_var, -1) == 9.5
              and fresh._num(fresh.ring_radius_var, -1) == 7.25,
              'a new window starts from the saved sizes')
        check(fresh._num(fresh.backbone_w_var, -1) == 0.75
              and fresh._num(fresh.pair_w_var, -1) == 2.5
              and fresh._num(fresh.ring_w_var, -1) == 0.5,
              'a new window starts from the saved line widths')
        check(fresh.pair_style.get() == 'double',
              'a new window starts with 双横线')
        check(fresh.flip_var.get() == False,                     # noqa: E712
              'a new window starts with 起点在上方')
        check(fresh._rotation() == 135.0,
              'a new window starts with the saved rotation',
              'got %r' % fresh._rotation())
        fresh.update_idletasks()

        # put factory settings back so the remaining checks are unaffected
        gui.settings.clear()
        app._apply_settings(gui.settings.default_settings())

        # ---- 8. SVG export ------------------------------------------
        out = os.path.join(tempfile.gettempdir(), 'gui_test_out.svg')
        if os.path.exists(out):
            os.remove(out)
        svg = gui.render_svg(app.layout, app.sequence, **app._render_options())
        with open(out, 'w', encoding='utf-8') as fh:
            fh.write(svg)
        import xml.etree.ElementTree as ET
        ET.parse(out)                                  # raises if malformed
        check(os.path.getsize(out) > 800, 'exported SVG is non-trivial',
              '%d bytes' % os.path.getsize(out))

        # ---- 9. zoom / fit ------------------------------------------
        app.zoom = 1.0
        app._zoom_at(100, 100, 1.5)
        check(abs(app.zoom - 1.5) < 1e-9, 'zoom factor applied',
              'zoom=%.3f' % app.zoom)
        app._autofit = True
        app._fit()
        check(app.zoom > 0, 'fit produced a positive zoom',
              'zoom=%.3f' % app.zoom)
        cw = max(app.canvas.winfo_width(), 1)
        ch = max(app.canvas.winfo_height(), 1)
        w_ratio = app.fig_w * app.zoom / cw
        h_ratio = app.fig_h * app.zoom / ch
        check(max(w_ratio, h_ratio) > 0.8,
              'fitted figure fills the canvas',
              'w=%.2f h=%.2f of canvas' % (w_ratio, h_ratio))
        check(w_ratio <= 1.001 and h_ratio <= 1.001,
              'fitted figure does not overflow the canvas',
              'w=%.2f h=%.2f' % (w_ratio, h_ratio))
        check(app._autofit, 'fit re-enables autofit')

        # ---- 10. error handling -------------------------------------
        app.ss_var.set('((((....')
        app.do_preview()
        app.update_idletasks()
        check(app.layout is None, 'bad structure clears the layout')
        check('结构串有误' in app.status_var.get(),
              'bad structure reported in the status bar', app.status_var.get())

        app.ss_var.set('((((....))))')
        app.seq_var.set('AAAA')
        app.do_preview()
        check('不一致' in app.status_var.get(),
              'length mismatch reported', app.status_var.get())

        # ---- 11. multi-strand ---------------------------------------
        app.seq_var.set('')
        app.ss_var.set('((((....))))+((((....))))')
        app.do_preview()
        app.update_idletasks()
        check(app.layout is not None and len(app.layout.xs) == 24,
              'multi-strand preview works',
              'n=%s' % (len(app.layout.xs) if app.layout else None))

    finally:
        try:
            app.destroy()
        except Exception:
            pass

    passed = sum(1 for ok, _, _ in RESULTS if ok)
    for ok, label, detail in RESULTS:
        if not ok:
            print('  [FAIL] %s%s' % (label, ('  -- ' + detail) if detail else ''))
    print('%d/%d GUI checks passed' % (passed, len(RESULTS)))
    return 0 if passed == len(RESULTS) else 1


if __name__ == '__main__':
    sys.exit(main())
