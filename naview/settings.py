#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Persistent drawing defaults for the NAView GUI.

Press 保存为默认 in the GUI and the current colours, sizes, line widths and
toggles are written to ``naview-settings.json``; the file is read again on the
next start.

The file lives next to the application so that copying the ``naview`` folder
to another computer brings the settings along.  When the GUI runs as a
PyInstaller executable (``NAView.exe``) "next to the application" means next
to the *exe*, not the temporary folder the bundle is unpacked into.  If that
folder is read-only the user profile is used instead.  Set the
``NAVIEW_SETTINGS`` environment variable to point at an explicit path (the
test suite does this).

Public API
----------
    FACTORY                built-in defaults (a fresh dict copy per call via
                           default_settings())
    default_settings()     factory defaults
    load()                 factory defaults updated with the saved file
    save(values)           write a settings dict, returns the path used
    settings_file()        path that would be read
    clear()                delete the saved file
"""

import json
import os
import sys

from render_svg import (
    BACKBONE_COLOR, DEFAULT_LETTER_COLORS, DEFAULT_OPTIONS,
    DEFAULT_RING_COLORS, PAIR_COLOR, RING_STROKE,
    R_FONT, R_LINEWIDTH, R_RING,
)

__all__ = [
    'FILENAME', 'FONT_PX', 'RING_PX', 'LINE_PX',
    'default_settings', 'load', 'save', 'settings_file', 'clear',
]

BASE_DISTANCE = DEFAULT_OPTIONS['base_distance']

# defaults expressed in figure pixels, derived from the renderer's ratios so
# the GUI, the CLI and the library always agree
FONT_PX = round(R_FONT * BASE_DISTANCE, 3)          # 6.0
RING_PX = round(R_RING * BASE_DISTANCE, 3)          # 6.2
LINE_PX = round(R_LINEWIDTH * BASE_DISTANCE, 3)     # 2.0

FILENAME = 'naview-settings.json'


def app_dir():
    """The folder the application lives in.

    A PyInstaller bundle unpacks the modules into a temporary folder, so
    ``__file__`` points there rather than at the ``.exe``; the settings file
    has to sit beside the exe (that is the file the user copies around), so
    when frozen we use the executable's own folder instead.
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


_APP_DIR = app_dir()        # informational; the path is resolved per call

_FLOAT_KEYS = ('font_size', 'ring_radius', 'backbone_width', 'pair_width',
               'ring_width')
_BOOL_KEYS = ('flip_y', 'even_loops', 'show_bases', 'show_pair_lines',
              'show_backbone')
_STR_KEYS = ('ring_stroke', 'backbone_color', 'pair_color')
_COLOR_MAP_KEYS = ('ring_colors', 'letter_colors')


def default_settings():
    """The built-in factory defaults, as a fresh dict."""
    return {
        'ring_colors': dict(DEFAULT_RING_COLORS),
        'letter_colors': dict(DEFAULT_LETTER_COLORS),
        'ring_stroke': RING_STROKE,
        'backbone_color': BACKBONE_COLOR,
        'pair_color': PAIR_COLOR,
        'font_size': FONT_PX,
        'ring_radius': RING_PX,
        'backbone_width': LINE_PX,
        'pair_width': LINE_PX,
        'ring_width': LINE_PX,
        'pair_style': 'single',
        'flip_y': True,
        'rotation': 0.0,
        'even_loops': True,
        'show_bases': True,
        'show_pair_lines': True,
        'show_backbone': True,
    }


def _candidates():
    override = os.environ.get('NAVIEW_SETTINGS')
    if override:
        return [override]
    return [os.path.join(app_dir(), FILENAME),
            os.path.join(os.path.expanduser('~'), '.' + FILENAME)]


def settings_file():
    """The path that :func:`load` would read (existing file wins)."""
    paths = _candidates()
    for path in paths:
        if os.path.exists(path):
            return path
    return paths[0]


def _merge(base, saved):
    """Update *base* with the usable entries of *saved* (never raises)."""
    if not isinstance(saved, dict):
        return base

    for key in _FLOAT_KEYS:
        try:
            value = float(saved[key])
        except (KeyError, TypeError, ValueError):
            continue
        if value > 0.0:
            base[key] = value

    for key in _BOOL_KEYS:
        if key in saved:
            base[key] = bool(saved[key])

    for key in _STR_KEYS:
        value = saved.get(key)
        if isinstance(value, str) and value:
            base[key] = value

    for key in _COLOR_MAP_KEYS:
        mapping = saved.get(key)
        if isinstance(mapping, dict):
            for name, value in mapping.items():
                if isinstance(value, str) and value:
                    base[key][name] = value

    if saved.get('pair_style') in ('single', 'double'):
        base['pair_style'] = saved['pair_style']

    # rotation may legitimately be 0, so it is validated separately
    try:
        base['rotation'] = float(saved['rotation']) % 360.0
    except (KeyError, TypeError, ValueError):
        pass
    return base


def load():
    """Factory defaults overridden by whatever was saved last time."""
    data = default_settings()
    path = settings_file()
    if not os.path.exists(path):
        return data
    try:
        # utf-8-sig: a file saved by an editor that adds a byte-order mark
        # (Notepad's "UTF-8 with BOM") is still read instead of being ignored
        with open(path, 'r', encoding='utf-8-sig') as fh:
            saved = json.load(fh)
    except (OSError, ValueError):
        return data
    return _merge(data, saved)


def save(values):
    """Write *values*, falling back to the user profile.  Returns the path."""
    data = _merge(default_settings(), values)
    errors = []
    for path in _candidates():
        try:
            folder = os.path.dirname(path)
            if folder and not os.path.isdir(folder):
                os.makedirs(folder)
            with open(path, 'w', encoding='utf-8') as fh:
                json.dump(data, fh, indent=2, sort_keys=True)
                fh.write('\n')
            return path
        except OSError as exc:
            errors.append('%s: %s' % (path, exc))
    raise OSError('could not write the settings file:\n' + '\n'.join(errors))


def clear():
    """Delete any saved settings file (used by the tests)."""
    for path in _candidates():
        try:
            os.remove(path)
        except OSError:
            pass
