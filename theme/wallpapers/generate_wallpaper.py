#!/usr/bin/env python3
"""Generate the default Axon OS aurora wallpaper (axon-aurora.png).

Renders flowing violet/cyan aurora bands over a near-black backdrop at
2560x1440. Run once and commit the output:

    python3 generate_wallpaper.py
"""

import math
import os

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 2560, 1440


def main():
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)

    # Vertical base gradient: deep space black -> dark indigo
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(7 + 12 * t), int(7 + 6 * t), int(12 + 28 * t)))

    # Aurora bands drawn at quarter resolution, blurred, then composited
    bands = [
        ((139, 92, 246), 0.34, 230, 90),   # violet
        ((76, 29, 149), 0.52, 320, 60),    # deep purple
        ((34, 211, 238), 0.30, 130, 38),   # cyan accent
        ((167, 139, 250), 0.62, 180, 46),  # light violet
    ]
    sw, sh = W // 4, H // 4
    overlay = Image.new("RGB", (sw, sh), (0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for color, base, thickness, alpha in bands:
        pts = []
        for x in range(sw):
            y = base * sh
            y += math.sin(x / sw * 3.1 + base * 9) * sh * 0.10
            y += math.sin(x / sw * 7.3 + base * 4) * sh * 0.05
            pts.append((x, y))
        col = tuple(int(c * alpha / 255) for c in color)
        for x, y in pts:
            od.line([(x, y - thickness / 8), (x, y + thickness / 8)], fill=col)
    overlay = overlay.filter(ImageFilter.GaussianBlur(sh * 0.07))
    overlay = overlay.resize((W, H), Image.LANCZOS)

    img = Image.blend(img, Image.composite(overlay, img, overlay.convert("L")), 0.85)

    # Subtle star field
    import random

    rnd = random.Random(42)
    sd = ImageDraw.Draw(img)
    for _ in range(420):
        x, y = rnd.randrange(W), rnd.randrange(int(H * 0.7))
        b = rnd.randint(70, 200)
        sd.point((x, y), fill=(b, b, min(255, b + 25)))

    out = os.path.join(HERE, "axon-aurora.png")
    img.save(out, optimize=True)
    print(f"Wallpaper written to {out} ({os.path.getsize(out) // 1024} KiB)")


if __name__ == "__main__":
    main()
