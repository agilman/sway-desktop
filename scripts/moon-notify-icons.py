#!/usr/bin/env python3
"""Generate 16 stylized moon-phase PNGs for the dunst popup (stdlib + gi).

Reuses the bar artwork's surface art (SURFACE/CRATERS) and terminator math by
importing moon-icons.py, renders 256px via GTK librsvg (proven engine), and
relies on dunst for scaling (max_icon_size=560, icon_position=top).
Output names: phase-00.png .. phase-15.png; index 0 = new moon, 4 = first
quarter, 8 = full, 12 = last quarter. North up; waxing lights the right.
"""
import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('moon_icons', Path(__file__).resolve().parent / 'moon-icons.py')
moon_icons = _ilu.module_from_spec(_spec); _spec.loader.exec_module(moon_icons)

import gi
gi.require_version('Rsvg', '2.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Rsvg, Gdk
import cairo


N = 16
SIZE = 256


def phase_svg(i):
    angle = 2 * math.pi * i / N
    waxing = i <= N // 2
    side = 1 if waxing else -1
    rows = [(-1 + j / 128) for j in range(257)]
    pts = [(50 + side * 46 * math.sqrt(max(0, 1 - y*y)), 50 + 46*y) for y in rows]
    pts += [(50 + side * math.cos(angle) * 46 * math.sqrt(max(0, 1 - y*y)), 50 + 46*y)
            for y in reversed(rows)]
    polygon = ' '.join(f'{x:.3f},{y:.3f}' for x, y in pts)
    # Larger surface features than the 24px bar set: the popup shows ~100-200px.
    surface = moon_icons.SURFACE
    craters = moon_icons.CRATERS.format(rim='#687180')
    lit_craters = moon_icons.CRATERS.format(rim='#fbfaf4')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
<title>Moon phase {i}/{N} (notify popup); north up</title>
<defs>
<clipPath id="disc"><circle cx="50" cy="50" r="46"/></clipPath>
<clipPath id="light"><polygon points="{' '.join(f'{x:.3f},{y:.3f}' for x, y in pts)}"/></clipPath>
<radialGradient id="silver" cx="42%" cy="35%" r="70%">
<stop offset="0" stop-color="#f0efea"/><stop offset=".72" stop-color="#d3d6d6"/>
<stop offset="1" stop-color="#9da6b1"/></radialGradient>
</defs>
<g clip-path="url(#disc)">
<circle cx="50" cy="50" r="46" fill="#424856"/>
<g fill="#303642" opacity=".7">{surface}</g>
{craters}
<g clip-path="url(#light)">
<circle cx="50" cy="50" r="46" fill="url(#silver)"/>
<g fill="#89939b" opacity=".62">{surface}</g>
{lit_craters}
</g></g>
<circle cx="50" cy="50" r="46" fill="none" stroke="#a6adbd" stroke-width="2"/>
</svg>'''


def render_all(output, renderer='gtk'):
    out = Path(output) / f'moon-notify'
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(N):
        svg = phase_svg(i).encode()
        handle = Rsvg.Loader() if False else None
        h = Rsvg.Handle.new_from_data(svg)
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, SIZE, SIZE)
        ctx = cairo.Context(surface)
        ctx.scale(SIZE / 100.0, SIZE / 100.0)
        rect = Rsvg.Rectangle(); rect.x = rect.y = 0; rect.width = rect.height = 100
        h.render_document(ctx, rect)
        target = out / f'phase-{i:02d}.png'
        surface.write_to_png(str(target))
        paths.append(target)
    return paths


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=Path.home() / '.config/wayland-plus/moon-notify')
    args = parser.parse_args()
    out = render_all(args.output)
    print(f'Rendered {len(out)} moon notify PNGs into {out.parent if False else out}')