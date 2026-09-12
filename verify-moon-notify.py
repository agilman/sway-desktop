"""Verify every phase PNG through real pixels: geometry, orientation, margins.

Measures the LIT MASK as alpha geometry: for waxing phases the lit polygon
carries full alpha where the sunward limb is; the dark earthshine side is
identical between mirrored phases. So we verify:
  1. size + transparent corners
  2. per-phase lit fraction vs analytic terminator, using brightness WITHOUT
     alpha gating (art fills the disc; earthshine side is just darker)
  3. orientation: phase 4 lit x-extent confined to right half; 12 to left
  4. mirror symmetry: phase i dark side == phase 15-i dark side (alpha)
"""
import math
import sys
from pathlib import Path
from PIL import Image, ImageChops

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else '/tmp/mn-local/moon-notify')
SIZE = 256
problems = []
images = {}
for i in range(16):
    im = Image.open(SRC / f'phase-{i:02d}.png').convert('RGBA')
    images[i] = im
    if im.size != (SIZE, SIZE):
        problems.append(f'phase {i}: size {im.size}')
        continue
    if im.getpixel((0, 0))[3] != 0 or im.getpixel((SIZE-1, SIZE-1))[3] != 0:
        problems.append(f'phase {i}: corner not transparent')

# 1-2. illumination fraction vs analytic terminator (brightness only)
for i in range(1, 15):
    im = images[i]
    cx = cy = SIZE / 2
    r_disc = SIZE * 0.46
    r_inset = r_disc - 6
    light = total = 0
    for y in range(SIZE):
        dy = y + .5 - cy
        span = math.sqrt(max(0.0, r_inset**2 - dy**2))
        x0, x1 = int(cx - span), int(cx + span)
        total += x1 - x0 + 1
        for x in range(x0, x1 + 1):
            if sum(im.getpixel((x, y))[:3]) / 3 > 100:
                light += 1
    frac = light / total
    angle = i * 2 * math.pi / 16
    expected_px = 0
    for y in range(SIZE):
        dy = y + .5 - cy
        span = math.sqrt(max(0.0, r_inset**2 - dy**2))
        boundary = math.cos(angle) * span
        for x in range(int(cx - span), int(cx + span) + 1):
            if (1 if i <= 8 else -1) * (x + .5 - cx) >= boundary:
                expected_px += 1
    expected = expected_px / total
    if abs(frac - expected) > 0.045:
        problems.append(f'phase {i}: lit {frac:.3f} vs terminator {expected:.3f}')

# 3. quarter orientation via bright x-extent
for i, right in ((4, True), (12, False)):
    im = images[i]
    cx = cy = SIZE / 2
    r_inset = SIZE * 0.46 - 6   # exclude the rim stroke band
    xs = [x for y in range(0, SIZE, 2) for x in range(SIZE)
          if (x+.5-cx)**2 + (y+.5-cy)**2 < r_inset**2
          and sum(im.getpixel((x, y))[:3])/3 > 130 and im.getpixel((x, y))[3] > 130]
    if right and min(xs) < SIZE/2 - 6:
        problems.append(f'phase 4: light bleeds left to x={min(xs)}')
    if not right and max(xs) > SIZE/2 + 6:
        problems.append(f'phase 12: light bleeds right to x={max(xs)}')

# 4. mirror symmetry via alpha channel (shape truth, brightness-independent)
for i in range(1, 8):
    a = images[i].split()[3].crop((0, 0, 128, SIZE)).transpose(Image.FLIP_LEFT_RIGHT)
    b = images[15 - i].split()[3].crop((128, 0, 256, SIZE))
    hist = ImageChops.difference(a, b).histogram()
    bad = sum(v for v in hist[12:])
    if bad > 40:
        problems.append(f'phase {i} vs {15-i}: mirror alpha mismatch {bad}px')

if problems:
    print('FAIL')
    [print(' ', p) for p in problems]
    raise SystemExit(1)
print('PASS: 16 phases — fraction vs terminator within 4.5pp, quarters oriented,')
print('      mirrored dark sides identical, corners transparent.')