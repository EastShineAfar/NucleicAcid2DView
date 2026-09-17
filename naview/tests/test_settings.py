#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the persisted GUI defaults (no display needed).

    python tests/test_settings.py
"""

import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

# point the module at a scratch file before it is used anywhere
_TMPDIR = tempfile.mkdtemp(prefix='naview-settings-')
os.environ['NAVIEW_SETTINGS'] = os.path.join(_TMPDIR, 'naview-settings.json')

import settings                                                   # noqa: E402

RESULTS = []


def check(cond, label, detail=''):
    RESULTS.append((bool(cond), label, detail))
    return bool(cond)


def main():
    settings.clear()

    # ---- 1. factory values are what the user asked for ---------------
    d = settings.default_settings()
    check(d['font_size'] == 6.0, 'factory font size is 6.0',
          'got %r' % d['font_size'])
    check(d['ring_radius'] == 6.2, 'factory ring radius is 6.2',
          'got %r' % d['ring_radius'])
    check(d['backbone_width'] == 2.0, 'factory backbone width is 2.0',
          'got %r' % d['backbone_width'])
    check(d['pair_width'] == 2.0, 'factory pair width is 2.0',
          'got %r' % d['pair_width'])
    check(d['ring_width'] == 2.0, 'factory ring stroke width is 2.0',
          'got %r' % d['ring_width'])
    check(d['rotation'] == 0.0, 'factory rotation is 0',
          'got %r' % d['rotation'])

    # ---- 2. with no file, load() == factory --------------------------
    check(not os.path.exists(settings.settings_file()),
          'no settings file before saving')
    check(settings.load() == d, 'load() matches factory when nothing saved')

    # ---- 3. save round-trip -----------------------------------------
    custom = dict(d)
    custom['font_size'] = 11.5
    custom['ring_radius'] = 9.25
    custom['backbone_width'] = 0.5
    custom['pair_width'] = 3.0
    custom['ring_width'] = 0.25
    custom['pair_style'] = 'double'
    custom['flip_y'] = False
    custom['even_loops'] = False
    custom['show_backbone'] = False
    custom['ring_colors'] = dict(d['ring_colors'])
    custom['ring_colors']['A'] = '#123456'
    custom['letter_colors'] = dict(d['letter_colors'])
    custom['letter_colors']['C'] = '#abcdef'
    custom['backbone_color'] = '#010203'
    custom['pair_color'] = '#040506'
    custom['ring_stroke'] = '#070809'
    custom['rotation'] = 275.0

    path = settings.save(custom)
    check(os.path.exists(path), 'save() created the file', path)

    with open(path, encoding='utf-8') as fh:
        raw = json.load(fh)
    check(raw['ring_colors']['A'] == '#123456',
          'colour stored in the file')

    back = settings.load()
    for key in ('font_size', 'ring_radius', 'backbone_width', 'pair_width',
                'ring_width', 'pair_style', 'flip_y', 'even_loops',
                'show_backbone', 'backbone_color', 'pair_color',
                'ring_stroke', 'rotation'):
        check(back[key] == custom[key], 'round-trip preserves %s' % key,
              '%r -> %r' % (custom[key], back[key]))
    check(back['ring_colors']['A'] == '#123456',
          'round-trip preserves ring colours')
    check(back['letter_colors']['C'] == '#abcdef',
          'round-trip preserves letter colours')

    # ---- 4. a partial / damaged file must not break the app ----------
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('{"font_size": "not a number", "ring_colors": 5,'
                 ' "pair_style": "nonsense", "ring_width": -3,'
                 ' "rotation": "sideways"}')
    merged = settings.load()
    check(merged['font_size'] == 6.0,
          'bad float falls back to the factory value',
          'got %r' % merged['font_size'])
    check(merged['ring_width'] == 2.0,
          'negative width falls back to the factory value',
          'got %r' % merged['ring_width'])
    check(merged['pair_style'] == 'single',
          'invalid pair style falls back to single',
          'got %r' % merged['pair_style'])
    check(merged['rotation'] == 0.0,
          'a bad rotation falls back to 0',
          'got %r' % merged['rotation'])
    check(isinstance(merged['ring_colors'], dict)
          and merged['ring_colors']['A'] == d['ring_colors']['A'],
          'non-dict colour map falls back to the factory palette')

    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('{ this is not json')
    check(settings.load() == d, 'unparsable file falls back to factory')

    # a byte-order mark (Notepad's "UTF-8 with BOM") must not lose the file
    with open(path, 'w', encoding='utf-8-sig') as fh:
        json.dump({'font_size': 9.5, 'ring_width': 1.5}, fh)
    bom = settings.load()
    check(bom['font_size'] == 9.5,
          'a settings file with a UTF-8 BOM is still read',
          'got %r' % bom['font_size'])
    check(bom['ring_width'] == 1.5,
          'a BOM does not drop the other entries either',
          'got %r' % bom['ring_width'])

    # ---- 5. clear() removes it --------------------------------------
    settings.clear()
    check(not os.path.exists(path), 'clear() removed the file')
    check(settings.load() == d, 'load() is back to factory after clear()')

    # ---- 6. the file is valid JSON with a trailing newline -----------
    settings.save(custom)
    with open(path, encoding='utf-8') as fh:
        body = fh.read()
    check(body.endswith('\n'), 'settings file ends with a newline')
    json.loads(body)
    check(True, 'settings file is valid JSON')

    # ---- 7. a frozen (PyInstaller) build saves beside the exe --------
    # the bundle unpacks its modules into a temp folder, so __file__ must not
    # be used there: the file the user copies around is the exe itself
    saved_env = os.environ.pop('NAVIEW_SETTINGS', None)
    had_frozen = hasattr(sys, 'frozen')
    old_frozen = getattr(sys, 'frozen', None)
    old_exe = sys.executable
    try:
        fake_exe = os.path.join(_TMPDIR, 'NAView.exe')
        sys.frozen = True
        sys.executable = fake_exe
        check(settings.app_dir() == _TMPDIR,
              'frozen build looks for settings beside the exe',
              'got %r' % settings.app_dir())
        check(settings.settings_file()
              == os.path.join(_TMPDIR, settings.FILENAME),
              'frozen build reads naview-settings.json beside the exe',
              'got %r' % settings.settings_file())
        written = settings.save(custom)
        check(written == os.path.join(_TMPDIR, settings.FILENAME),
              'frozen build writes the settings beside the exe',
              'got %r' % written)
        check(settings.load()['font_size'] == custom['font_size'],
              'frozen build can read its own settings back')
        os.remove(written)
    finally:
        sys.executable = old_exe
        if had_frozen:
            sys.frozen = old_frozen
        else:
            del sys.frozen
        if saved_env is not None:
            os.environ['NAVIEW_SETTINGS'] = saved_env
        else:
            settings.clear()

    settings.clear()
    try:
        os.rmdir(_TMPDIR)
    except OSError:
        pass

    passed = sum(1 for ok, _, _ in RESULTS if ok)
    for ok, label, detail in RESULTS:
        if not ok:
            print('  [FAIL] %s%s' % (label, ('  -- ' + detail) if detail else ''))
    print('%d/%d settings checks passed' % (passed, len(RESULTS)))
    return 0 if passed == len(RESULTS) else 1


if __name__ == '__main__':
    sys.exit(main())
