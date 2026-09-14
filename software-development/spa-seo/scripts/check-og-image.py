#!/usr/bin/env python3
"""Verify a cropped OG image is not blank / not a solid color.

Usage: python3 check-og-image.py <image.png>
Prints: size, RGB stddev (per-channel), and per-band average colors.
A blank/solid image has stddev ~0; a real hero scene has stddev typically >20.

Also useful when the vision-analysis backend is unavailable — this is the
deterministic "is there actually content here" probe.
"""
import statistics
import sys
from PIL import Image

path = sys.argv[1]
im = Image.open(path).convert("RGB")
w, h = im.size
print("size", im.size)
px = [im.getpixel((x, y)) for y in range(0, h, 16) for x in range(0, w, 16)]
r = statistics.pstdev(p[0] for p in px)
g = statistics.pstdev(p[1] for p in px)
b = statistics.pstdev(p[2] for p in px)
print("stddev rgb: %.1f %.1f %.1f" % (r, g, b))
for band in range(4):
    y0, y1 = band * h // 4, (band + 1) * h // 4
    band_px = [im.getpixel((x, y)) for y in range(y0, y1, 12) for x in range(0, w, 12)]
    avg = tuple(round(sum(p[i] for p in band_px) / len(band_px)) for i in range(3))
    print("band %d avg rgb: %s" % (band, avg))
