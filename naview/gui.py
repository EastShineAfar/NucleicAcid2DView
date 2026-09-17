#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NAView structure drawing GUI (tkinter, standard library only).

Layout: the drawing preview fills the left side, all controls live in a
fixed-width sidebar on the right.

Type a sequence and a dot-bracket structure, press 预览, and the drawing
appears in the window; 保存 SVG writes exactly the same figure to a file.

Everything here relies only on the Python standard library, so the whole
``naview`` folder can be copied to another computer and run as-is
(needs Python 3.8+ with tkinter, which the official Windows installer
includes by default).

    python gui.py
"""

from __future__ import print_function

import os
import sys
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

try:
    import tkinter as tk
    from tkinter import colorchooser, filedialog, messagebox, ttk
except ImportError:                                   # pragma: no cover
    sys.stderr.write(
        "错误: 这个 Python 没有 tkinter，无法显示图形界面。\n"
        "Windows 请重新运行官方安装包并勾选 \"tcl/tk and IDLE\"；\n"
        "Ubuntu/Debian 请执行: sudo apt install python3-tk\n")
    raise SystemExit(2)

from naview import clean_sequence, naview_layout, parse_dot_bracket   # noqa: E402
from render_svg import (                                              # noqa: E402
    BACKBONE_COLOR, BASE_ORDER, DEFAULT_LETTER_COLORS, DEFAULT_RING_COLORS,
    PAIR_COLOR, RING_STROKE, build_primitives, render_svg,
)
import settings                                                       # noqa: E402

APP_TITLE = 'NAView 二级结构绘图'
APP_VERSION = '1.3.0'
ICON_NAME = 'appicon.ico'


def find_icon():
    """Path of the window icon, both from source and from a PyInstaller exe."""
    folders = [_HERE]
    bundled = getattr(sys, '_MEIPASS', None)
    if bundled:
        folders.insert(0, bundled)
    for folder in folders:
        path = os.path.join(folder, ICON_NAME)
        if os.path.exists(path):
            return path
    return None

# figure pixels at the default base_distance of 20, derived from the renderer
DEFAULT_FONT_SIZE = settings.FONT_PX
DEFAULT_RING_RADIUS = settings.RING_PX
DEFAULT_LINE_WIDTH = settings.LINE_PX

PANEL_WIDTH = 366          # sidebar width in pixels

SAMPLES = [
    ('发夹 hairpin',
     'GCGCAAAAGCGC', '((((....))))'),
    ('凸环 bulge',
     'GGGGAGGGGAAAACCCCCCCC', '((((.((((....))))))))'),
    ('双茎 two stems',
     'GGGAAAACCCUUUGGGAAAACCC', '(((....)))...(((....)))'),
    ('多分支 multiloop',
     'GGGGAAAACCCCUUUUGGGGAAAACCCC', '((((....))))....((((....))))'),
    ('60 nt 测试序列',
     'TTAGCTTATGCGTTGGCCGGGATAAGGATCCAGCCGTTGTAGATTTGCGTTCTAACTCTC',
     '...((....))...(((..((((....)))).))).........................'),
]

FIELD_LABELS = {'ring': '圆环填充', 'letter': '字母',
                'stroke': '圆环描边', 'backbone': '骨架线', 'pair': '配对线'}


def _enable_dpi_awareness():
    """Ask Windows for a crisp (non-blurred) window on HiDPI screens."""
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class DrawApp(tk.Tk):

    def __init__(self):
        tk.Tk.__init__(self)
        self.title('%s  v%s' % (APP_TITLE, APP_VERSION))
        self._set_window_icon()
        # Centre a window that fits the screen even on a small laptop panel.
        w, h = 1280, 820
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w = max(1000, min(w, sw - 80))
        h = max(640, min(h, sh - 90))
        self.geometry('%dx%d+%d+%d' % (w, h, max(0, (sw - w) // 2),
                                       max(0, (sh - h) // 3)))
        self.minsize(1000, 620)

        # ---- state ---------------------------------------------------
        self.defaults = settings.load()
        self.style = {
            'ring': dict(DEFAULT_RING_COLORS),
            'letter': dict(DEFAULT_LETTER_COLORS),
            'stroke': RING_STROKE,
            'backbone': BACKBONE_COLOR,
            'pair': PAIR_COLOR,
        }
        self.swatches = {}          # (kind, base) -> tk.Button
        self.layout = None
        self.sequence = ''
        self.prims = []
        self.fig_w = 1.0
        self.fig_h = 1.0
        self.zoom = 1.0
        self.panx = 0.0
        self.pany = 0.0
        self._drag = None
        self._autofit = True     # re-fit while the user has not zoomed/panned
        self._last_canvas = (0, 0)

        self._build_ui()
        self._apply_settings(self.defaults)
        self.after(60, self.do_preview)

    def _set_window_icon(self):
        """Use appicon.ico for the title bar, from source or from a bundle."""
        icon = find_icon()
        if not icon:
            return
        try:
            self.iconbitmap(default=icon)
        except Exception:                                 # pragma: no cover
            pass

    # ---------------------------------------------------------- helpers --

    def _status(self, text, error=False):
        self.status_var.set(text)
        self.status_label.configure(foreground='#b00000' if error else '#204020')

    def _get_color(self, kind, base=None):
        if base is None:
            return self.style[kind]
        return self.style[kind].get(base, '#ffffff')

    def _set_color(self, kind, base, value):
        if base is None:
            self.style[kind] = value
        else:
            self.style[kind][base] = value

    def _rotation(self):
        """Current rotation in degrees, 0..360, tolerant of half-typed input."""
        try:
            value = float(self.rotation_var.get())
        except Exception:
            return 0.0
        return value % 360.0

    def _on_rotate(self, _value=None):
        """Rotation only moves coordinates, so no re-layout is needed."""
        self.rotation_var.set(round(self._rotation(), 1))
        self._refresh_prims()
        if self._autofit:
            self._fit()
        else:
            self._redraw()

    @staticmethod
    def _num(var, fallback):
        """Read a Spinbox-backed variable, tolerating half-typed input."""
        try:
            value = float(var.get())
        except Exception:
            return fallback
        return value if value > 0 else fallback

    def _make_spin(self, parent, var, row, col, lo=0.1, hi=60.0, step=0.5):
        spin = ttk.Spinbox(parent, from_=lo, to=hi, increment=step, width=5,
                           textvariable=var, command=self._on_style_change)
        spin.grid(row=row, column=col, padx=(2, 10), pady=1, sticky='w')
        spin.bind('<Return>', lambda e: self._on_style_change())
        spin.bind('<FocusOut>', lambda e: self._on_style_change())
        return spin

    # ------------------------------------------------------------- UI ----

    def _build_ui(self):
        # ---- status bar (packed before the body so it keeps its row) ----
        self.status_var = tk.StringVar(value='就绪')
        self.status_label = ttk.Label(self, textvariable=self.status_var,
                                      anchor='w', foreground='#204020')
        self.status_label.pack(side='bottom', fill='x', padx=8, pady=(0, 6))

        body = ttk.Frame(self)
        body.pack(side='top', fill='both', expand=True, padx=8, pady=(8, 4))

        # The sidebar is packed FIRST (side='right') and keeps its width, so
        # the expanding preview cannot squeeze it out on a narrow window.
        self.panel = ttk.Frame(body, width=PANEL_WIDTH)
        self.panel.pack(side='right', fill='y', padx=(8, 0))
        self.panel.pack_propagate(False)

        left = ttk.Frame(body)
        left.pack(side='left', fill='both', expand=True)

        self._build_sidebar(self.panel)

        # ---- preview + action buttons (left column) -------------------
        self.canvas = tk.Canvas(left, background='white',
                                highlightthickness=1,
                                highlightbackground='#c0c0c0')
        self.canvas.pack(side='top', fill='both', expand=True)

        bar = ttk.Frame(left)
        bar.pack(side='bottom', fill='x', pady=(6, 0))
        ttk.Button(bar, text='预览  (Ctrl+Enter)',
                   command=self.do_preview).pack(side='left')
        ttk.Button(bar, text='保存 SVG …',
                   command=self.do_save_svg).pack(side='left', padx=6)
        ttk.Button(bar, text='适应窗口', command=self._fit).pack(side='left')
        ttk.Label(bar, text='滚轮缩放 / 按住左键拖动',
                  foreground='#777777').pack(side='left', padx=12)

        self.canvas.bind('<Configure>', self._on_canvas_resize)
        self.canvas.bind('<ButtonPress-1>', self._on_press)
        self.canvas.bind('<B1-Motion>', self._on_drag)
        self.canvas.bind('<ButtonRelease-1>',
                         lambda e: setattr(self, '_drag', None))
        self.canvas.bind('<MouseWheel>', self._on_wheel)       # Windows/macOS
        self.canvas.bind('<Button-4>', lambda e: self._zoom_at(e.x, e.y, 1.12))
        self.canvas.bind('<Button-5>', lambda e: self._zoom_at(e.x, e.y, 1 / 1.12))

        self.bind('<Control-Return>', lambda e: self.do_preview())
        self.bind('<F5>', lambda e: self.do_preview())

        self._sync_swatches()

    # --------------------------------------------------------- sidebar ----

    def _build_sidebar(self, panel):
        pad = dict(padx=6, pady=2)

        # ============ 输入 ============
        inp = ttk.LabelFrame(panel, text=' 输入 ')
        inp.pack(side='top', fill='x')
        self.seq_var = tk.StringVar(value=SAMPLES[0][1])
        self.ss_var = tk.StringVar(value=SAMPLES[0][2])

        ttk.Label(inp, text='序列').grid(row=0, column=0, sticky='e', **pad)
        ttk.Entry(inp, textvariable=self.seq_var,
                  font=('Consolas', 9)).grid(row=0, column=1, sticky='ew', **pad)
        ttk.Label(inp, text='结构').grid(row=1, column=0, sticky='e', **pad)
        ttk.Entry(inp, textvariable=self.ss_var,
                  font=('Consolas', 9)).grid(row=1, column=1, sticky='ew', **pad)
        ttk.Label(inp, text='示例').grid(row=2, column=0, sticky='e', **pad)
        self.sample_box = ttk.Combobox(inp, state='readonly', width=18,
                                       values=[s[0] for s in SAMPLES])
        self.sample_box.current(0)
        self.sample_box.grid(row=2, column=1, sticky='w', **pad)
        self.sample_box.bind('<<ComboboxSelected>>', self._on_sample)
        ttk.Label(inp, text='+ 或 & 分隔不同链',
                  foreground='#777777').grid(row=3, column=1, sticky='w',
                                             padx=6, pady=(0, 4))
        inp.columnconfigure(1, weight=1)

        # ============ 配色 ============
        col = ttk.LabelFrame(panel, text=' 配色 ')
        col.pack(side='top', fill='x', pady=(6, 0))

        bases = ttk.Frame(col)
        bases.pack(fill='x', padx=6, pady=(4, 2))
        ttk.Label(bases, text='碱基', foreground='#555555').grid(
            row=0, column=0, sticky='w')
        ttk.Label(bases, text='圆环填充', foreground='#555555').grid(
            row=0, column=1, padx=3)
        ttk.Label(bases, text='字母颜色', foreground='#555555').grid(
            row=0, column=2, padx=3)
        for r, base in enumerate(BASE_ORDER, start=1):
            label = 'T / U' if base == 'T' else base
            ttk.Label(bases, text=label, font=('Segoe UI', 9, 'bold'),
                      anchor='e').grid(row=r, column=0, sticky='e', padx=(0, 8),
                                       pady=1)
            for c, kind in enumerate(('ring', 'letter'), start=1):
                b = tk.Button(bases, width=3, relief='raised', borderwidth=1,
                              command=lambda k=kind, s=base: self._pick(k, s))
                b.grid(row=r, column=c, padx=3, pady=1)
                self.swatches[(kind, base)] = b

        others = ttk.Frame(col)
        others.pack(fill='x', padx=6, pady=(4, 6))
        for c, kind in enumerate(('stroke', 'backbone', 'pair')):
            ttk.Label(others, text=FIELD_LABELS[kind],
                      foreground='#555555').grid(row=0, column=c, padx=3)
            b = tk.Button(others, width=3, relief='raised', borderwidth=1,
                          command=lambda k=kind: self._pick(k, None))
            b.grid(row=1, column=c, padx=3, pady=1)
            self.swatches[(kind, None)] = b

        # ============ 尺寸与线宽 ============
        size = ttk.LabelFrame(panel, text=' 尺寸与线宽 ')
        size.pack(side='top', fill='x', pady=(6, 0))
        grid = ttk.Frame(size)
        grid.pack(fill='x', padx=6, pady=4)

        self.font_size_var = tk.DoubleVar(value=DEFAULT_FONT_SIZE)
        self.ring_radius_var = tk.DoubleVar(value=DEFAULT_RING_RADIUS)
        self.backbone_w_var = tk.DoubleVar(value=DEFAULT_LINE_WIDTH)
        self.pair_w_var = tk.DoubleVar(value=DEFAULT_LINE_WIDTH)
        self.ring_w_var = tk.DoubleVar(value=DEFAULT_LINE_WIDTH)

        fields = [
            ('字号', self.font_size_var, 0.5, 60.0),
            ('圈径', self.ring_radius_var, 0.5, 60.0),
            ('骨架线', self.backbone_w_var, 0.1, 12.0),
            ('配对线', self.pair_w_var, 0.1, 12.0),
            ('环描边', self.ring_w_var, 0.1, 12.0),
        ]
        for i, (label, var, step, hi) in enumerate(fields):
            r, c = divmod(i, 2)
            ttk.Label(grid, text=label, width=6, anchor='e').grid(
                row=r, column=c * 2, sticky='e', pady=1)
            self._make_spin(grid, var, r, c * 2 + 1, lo=0.1, hi=hi, step=step)

        # ============ 样式 ============
        style = ttk.LabelFrame(panel, text=' 样式 ')
        style.pack(side='top', fill='x', pady=(6, 0))
        box = ttk.Frame(style)
        box.pack(fill='x', padx=6, pady=4)

        self.pair_style = tk.StringVar(value='single')
        ttk.Radiobutton(box, text='单横线', value='single',
                        variable=self.pair_style,
                        command=self._on_style_change).grid(
            row=0, column=0, sticky='w')
        ttk.Radiobutton(box, text='双横线', value='double',
                        variable=self.pair_style,
                        command=self._on_style_change).grid(
            row=0, column=1, sticky='w', padx=(10, 0))

        self.show_seq_var = tk.BooleanVar(value=True)
        self.show_pairs_var = tk.BooleanVar(value=True)
        self.show_bb_var = tk.BooleanVar(value=True)
        self.flip_var = tk.BooleanVar(value=True)
        self.even_var = tk.BooleanVar(value=True)
        checks = [
            ('显示碱基字母', self.show_seq_var, 1, 0),
            ('显示配对线', self.show_pairs_var, 1, 1),
            ('显示骨架线', self.show_bb_var, 2, 0),
            ('起点在下方', self.flip_var, 2, 1),
            ('自动优化间距', self.even_var, 3, 0),
        ]
        for text, var, r, c in checks:
            cmd = self.do_preview if var is self.even_var else self._on_style_change
            ttk.Checkbutton(box, text=text, variable=var,
                            command=cmd).grid(
                row=r, column=c, sticky='w', pady=(4 if r >= 1 else 0, 0),
                padx=(10 if c else 0, 0))

        # ---- rotation (rendering only: no re-layout needed) ----
        rot = ttk.Frame(box)
        rot.grid(row=4, column=0, columnspan=2, sticky='ew', pady=(6, 0))
        ttk.Label(rot, text='旋转').grid(row=0, column=0, sticky='w')
        self.rotation_var = tk.DoubleVar(value=0.0)
        self.rotation_scale = ttk.Scale(rot, from_=0.0, to=359.0,
                                        orient='horizontal',
                                        variable=self.rotation_var,
                                        command=self._on_rotate)
        self.rotation_scale.grid(row=0, column=1, sticky='ew', padx=(6, 4))
        self.rotation_spin = ttk.Spinbox(rot, from_=0.0, to=359.0,
                                         increment=15.0, width=5,
                                         textvariable=self.rotation_var,
                                         command=self._on_rotate)
        self.rotation_spin.grid(row=0, column=2)
        for widget in (self.rotation_spin,):
            widget.bind('<Return>', lambda e: self._on_rotate())
            widget.bind('<FocusOut>', lambda e: self._on_rotate())
        ttk.Label(rot, text='度').grid(row=0, column=3, padx=(3, 0))
        rot.columnconfigure(1, weight=1)

        ttk.Button(box, text='恢复出厂',
                   command=self._reset_defaults).grid(
            row=5, column=1, sticky='w', padx=(10, 0), pady=(8, 0))
        ttk.Button(box, text='保存为默认',
                   command=self._save_defaults).grid(
            row=5, column=0, sticky='w', pady=(8, 0))

    # ------------------------------------------------------- colour UI ----

    def _sync_swatches(self):
        for (kind, base), button in self.swatches.items():
            button.configure(background=self._get_color(kind, base))

    def _pick(self, kind, base):
        current = self._get_color(kind, base)
        title = '选择%s颜色%s' % (
            FIELD_LABELS[kind], '' if base is None else ' (%s)' % base)
        _, hexcolor = colorchooser.askcolor(color=current, title=title)
        if not hexcolor:
            return
        self._set_color(kind, base, hexcolor)
        self._sync_swatches()
        self._refresh_prims()
        self._redraw()

    def _reset_defaults(self):
        """Load the built-in factory values into the UI (does not save)."""
        self._apply_settings(settings.default_settings())
        self._status('已恢复出厂设置（未保存；要保留请点「保存为默认」）')

    def _current_settings(self):
        """The style/size/orientation state as a plain dict."""
        return {
            'ring_colors': dict(self.style['ring']),
            'letter_colors': dict(self.style['letter']),
            'ring_stroke': self.style['stroke'],
            'backbone_color': self.style['backbone'],
            'pair_color': self.style['pair'],
            'font_size': self._num(self.font_size_var, DEFAULT_FONT_SIZE),
            'ring_radius': self._num(self.ring_radius_var, DEFAULT_RING_RADIUS),
            'backbone_width': self._num(self.backbone_w_var, DEFAULT_LINE_WIDTH),
            'pair_width': self._num(self.pair_w_var, DEFAULT_LINE_WIDTH),
            'ring_width': self._num(self.ring_w_var, DEFAULT_LINE_WIDTH),
            'pair_style': self.pair_style.get(),
            'flip_y': bool(self.flip_var.get()),
            'rotation': self._rotation(),
            'even_loops': bool(self.even_var.get()),
            'show_bases': bool(self.show_seq_var.get()),
            'show_pair_lines': bool(self.show_pairs_var.get()),
            'show_backbone': bool(self.show_bb_var.get()),
        }

    def _apply_settings(self, data):
        """Push a settings dict into every widget and refresh the preview."""
        self.style = {
            'ring': dict(data['ring_colors']),
            'letter': dict(data['letter_colors']),
            'stroke': data['ring_stroke'],
            'backbone': data['backbone_color'],
            'pair': data['pair_color'],
        }
        self.font_size_var.set(data['font_size'])
        self.ring_radius_var.set(data['ring_radius'])
        self.backbone_w_var.set(data['backbone_width'])
        self.pair_w_var.set(data['pair_width'])
        self.ring_w_var.set(data['ring_width'])
        self.pair_style.set(data['pair_style'])
        self.flip_var.set(bool(data['flip_y']))
        self.rotation_var.set(float(data.get('rotation') or 0.0) % 360.0)
        self.even_var.set(bool(data['even_loops']))
        self.show_seq_var.set(bool(data['show_bases']))
        self.show_pairs_var.set(bool(data['show_pair_lines']))
        self.show_bb_var.set(bool(data['show_backbone']))
        self._sync_swatches()
        if self.layout is not None:
            self.layout = naview_layout(
                self.layout.structure,
                even_loops='auto' if data['even_loops'] else False)
        self._refresh_prims()
        self._redraw()

    def _save_defaults(self):
        """Store the current parameters as the ones to start with next time."""
        try:
            path = settings.save(self._current_settings())
        except OSError as exc:
            messagebox.showerror(APP_TITLE, '保存默认设置失败:\n%s' % exc)
            return
        self.defaults = settings.load()
        self._status('已保存为默认参数，下次启动生效: %s' % path)

    def _on_style_change(self):
        self._refresh_prims()
        self._redraw()

    def _on_sample(self, _event=None):
        idx = self.sample_box.current()
        if 0 <= idx < len(SAMPLES):
            _, seq, ss = SAMPLES[idx]
            self.seq_var.set(seq)
            self.ss_var.set(ss)
            self.do_preview()

    # -------------------------------------------------------- rendering ---

    def _render_options(self):
        return dict(
            base_distance=20.0,
            font_size=self._num(self.font_size_var, DEFAULT_FONT_SIZE),
            ring_radius=self._num(self.ring_radius_var, DEFAULT_RING_RADIUS),
            backbone_width=self._num(self.backbone_w_var, DEFAULT_LINE_WIDTH),
            pair_width=self._num(self.pair_w_var, DEFAULT_LINE_WIDTH),
            ring_width=self._num(self.ring_w_var, DEFAULT_LINE_WIDTH),
            flip_y=bool(self.flip_var.get()),
            rotation=self._rotation(),
            ring_colors=self.style['ring'],
            letter_colors=self.style['letter'],
            ring_stroke=self.style['stroke'],
            backbone_color=self.style['backbone'],
            pair_color=self.style['pair'],
            pair_style=self.pair_style.get(),
            show_bases=self.show_seq_var.get(),
            show_pair_lines=self.show_pairs_var.get(),
            show_backbone=self.show_bb_var.get(),
        )

    def _refresh_prims(self):
        if self.layout is None:
            return
        self.prims, self.fig_w, self.fig_h = build_primitives(
            self.layout, self.sequence, **self._render_options())

    def _redraw(self):
        c = self.canvas
        c.delete('all')
        if not self.prims:
            return
        s = self.zoom
        ox, oy = self.panx, self.pany
        for p in self.prims:
            kind = p['kind']
            if kind == 'line':
                c.create_line(ox + p['x1'] * s, oy + p['y1'] * s,
                              ox + p['x2'] * s, oy + p['y2'] * s,
                              fill=p['stroke'],
                              width=max(1, int(round(p['width'] * s))),
                              capstyle='round')
            elif kind == 'circle':
                stroke = p['stroke']
                outline = stroke if (stroke and stroke != 'none') else ''
                width = max(1, int(round(p['width'] * s))) if outline else 1
                c.create_oval(ox + (p['cx'] - p['r']) * s,
                              oy + (p['cy'] - p['r']) * s,
                              ox + (p['cx'] + p['r']) * s,
                              oy + (p['cy'] + p['r']) * s,
                              fill=p['fill'], outline=outline, width=width)
            else:                                    # text
                size = max(4, int(round(p['size'] * s)))
                c.create_text(ox + p['cx'] * s, oy + p['cy'] * s,
                              text=p['text'], fill=p['fill'],
                              font=(p['family'], size), anchor='center')

    def _fit(self):
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        # The canvas reports 1x1 until the window is mapped; fall back to a
        # sensible size so a preview requested at startup still draws.
        if cw < 10:
            cw = 800
        if ch < 10:
            ch = 560
        if self.fig_w > 0 and self.fig_h > 0:
            self.zoom = max(0.05, min(cw / self.fig_w, ch / self.fig_h) * 0.96)
            self.panx = (cw - self.fig_w * self.zoom) / 2.0
            self.pany = (ch - self.fig_h * self.zoom) / 2.0
        self._autofit = True
        self._redraw()

    def _on_canvas_resize(self, event):
        """Keep the figure fitted until the user takes manual control."""
        size = (event.width, event.height)
        if size == self._last_canvas:
            return
        self._last_canvas = size
        if self._autofit and self.prims:
            self._fit()

    def _zoom_at(self, x, y, factor):
        new = max(0.05, min(40.0, self.zoom * factor))
        if new == self.zoom:
            return
        k = new / self.zoom
        self.panx = x - (x - self.panx) * k
        self.pany = y - (y - self.pany) * k
        self.zoom = new
        self._autofit = False
        self._redraw()

    def _on_wheel(self, event):
        self._zoom_at(event.x, event.y, 1.12 if event.delta > 0 else 1 / 1.12)

    def _on_press(self, event):
        self._drag = (event.x, event.y)
        self.canvas.configure(cursor='fleur')

    def _on_drag(self, event):
        if not self._drag:
            return
        dx = event.x - self._drag[0]
        dy = event.y - self._drag[1]
        self._drag = (event.x, event.y)
        self.panx += dx
        self.pany += dy
        self._autofit = False
        self._redraw()

    # ----------------------------------------------------------- actions --

    def do_preview(self):
        ss_text = self.ss_var.get().strip()
        if not ss_text:
            self._status('请先填写结构串，例如 ((((....))))', error=True)
            return
        try:
            structure = parse_dot_bracket(ss_text)
        except ValueError as exc:
            self.layout = None
            self.prims = []
            self._redraw()
            self._status('结构串有误: %s' % exc, error=True)
            return

        seq = clean_sequence(self.seq_var.get()) or ''
        if seq and len(seq) != structure.n:
            self.layout = None
            self.prims = []
            self._redraw()
            self._status('序列长度 %d 与结构长度 %d 不一致'
                         % (len(seq), structure.n), error=True)
            return

        # the checkbox means "optimise spacing automatically"; the layout
        # engine then lays the structure out both ways and keeps the better
        self.layout = naview_layout(
            structure, even_loops='auto' if self.even_var.get() else False)
        self.sequence = seq
        self._refresh_prims()
        self._fit()

        msg = '预览已更新：%d 个碱基 / %d 对配对 / %d 条链 / %d 个环' % (
            structure.n, len(structure.pairs), len(structure.breaks),
            len(self.layout.loops))
        if self.layout.warnings:
            msg += '   ⚠ %d 条算法告警' % len(self.layout.warnings)
            print('\n'.join(self.layout.warnings), file=sys.stderr)
        self._status(msg)

    def do_save_svg(self):
        if self.layout is None:
            self.do_preview()
            if self.layout is None:
                return
        path = filedialog.asksaveasfilename(
            title='保存为 SVG',
            defaultextension='.svg',
            initialfile='structure.svg',
            filetypes=[('SVG 矢量图', '*.svg'), ('所有文件', '*.*')])
        if not path:
            return
        svg = render_svg(self.layout, self.sequence, **self._render_options())
        try:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(svg)
        except OSError as exc:
            messagebox.showerror(APP_TITLE, '保存失败:\n%s' % exc)
            return
        self._status('已保存: %s  (%.1f KB)'
                     % (path, os.path.getsize(path) / 1024.0))


def main():
    _enable_dpi_awareness()
    try:
        app = DrawApp()
    except Exception:
        traceback.print_exc()
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(APP_TITLE, '启动失败:\n\n%s' % traceback.format_exc())
            root.destroy()
        except Exception:
            pass
        return 1
    app.mainloop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
