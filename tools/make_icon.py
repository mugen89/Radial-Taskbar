"""Draws the application icon (a wheel with one lit segment) and writes res/app.ico.

Small sizes are drawn separately with fewer, fatter segments so the tray icon stays readable.
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

SS = 8  # supersampling
PALETTE = [(255, 196, 77), (255, 138, 76), (255, 92, 122), (196, 94, 240), (110, 110, 255), (56, 178, 255), (45, 214, 190), (132, 214, 92)]
PALETTE6 = [(255, 190, 70), (255, 110, 80), (214, 92, 230), (96, 120, 255), (45, 200, 220), (120, 210, 96)]


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(len(a)))


def wedge(draw, cx, cy, r0, r1, a0, a1, fill):
    pts = []
    steps = 48
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * i / steps
        pts.append((cx + math.sin(a) * r1, cy - math.cos(a) * r1))
    for i in range(steps, -1, -1):
        a = a0 + (a1 - a0) * i / steps
        pts.append((cx + math.sin(a) * r0, cy - math.cos(a) * r0))
    draw.polygon(pts, fill=fill)


def render(size):
    n = size * SS
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    small = size <= 24
    segs = 6 if small else 8
    c = n / 2
    r1 = n * (0.49 if small else 0.46)
    r0 = n * (0.20 if small else 0.215)
    gap = n * (0.055 if small else 0.030)

    if not small:
        # dark rounded plate
        plate = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        pd = ImageDraw.Draw(plate)
        grad = Image.new("RGBA", (1, n))
        for y in range(n):
            grad.putpixel((0, y), lerp((34, 42, 66, 255), (12, 15, 26, 255), y / n))
        grad = grad.resize((n, n))
        mask = Image.new("L", (n, n), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, n - 1, n - 1), radius=int(n * 0.235), fill=255)
        img.paste(grad, (0, 0), mask)
        pd.rounded_rectangle((n * 0.006, n * 0.006, n * 0.994, n * 0.994), radius=int(n * 0.23),
                             outline=(255, 255, 255, 46), width=max(1, int(n * 0.010)))
        img = Image.alpha_composite(img, plate)
        r1 = n * 0.405
        r0 = n * 0.185

    layer = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    step = 2 * math.pi / segs
    lit = 1
    for i in range(segs):
        mid = i * step
        rr1, rr0 = r1, r0
        if i == lit:
            rr1 = r1 * (1.0 if small else 1.10)
            rr0 = r0 * (1.0 if small else 1.04)
        pad = math.asin(min(0.9, gap / 2 / ((rr0 + rr1) / 2)))
        # every segment wears a skin of its own
        pal = PALETTE6 if small else PALETTE
        col = pal[i] + (255,)
        wedge(d, c, c, rr0, rr1, mid - step / 2 + pad, mid + step / 2 - pad, col)

    if not small:
        # two-colour sweep and glow on the lit segment
        sweep = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        px = Image.new("RGBA", (n, n))
        g = Image.new("RGBA", (n, 1))
        for x in range(n):
            g.putpixel((x, 0), lerp((45, 212, 255, 255), (128, 92, 255, 255), x / n))
        px = g.resize((n, n)).rotate(-45, resample=Image.BICUBIC)
        mask = Image.new("L", (n, n), 0)
        mid = lit * step
        rr0, rr1 = r0 * 1.04, r1 * 1.10
        pad = math.asin(min(0.9, gap / 2 / ((rr0 + rr1) / 2)))
        wedge(ImageDraw.Draw(mask), c, c, rr0, rr1, mid - step / 2 + pad, mid + step / 2 - pad, 255)
        sweep.paste(px, (0, 0), mask)
        glow = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        glow.paste((64, 170, 255, 190), (0, 0), mask)
        glow = glow.filter(ImageFilter.GaussianBlur(n * 0.045))
        img = Image.alpha_composite(img, glow)
        img = Image.alpha_composite(img, layer)
        img = Image.alpha_composite(img, sweep)
        hub = ImageDraw.Draw(img)
        rh = r0 * 0.56
        hub.ellipse((c - rh, c - rh, c + rh, c + rh), fill=(235, 242, 255, 255))
    else:
        img = Image.alpha_composite(img, layer)
        hub = ImageDraw.Draw(img)
        rh = r0 * 0.46
        hub.ellipse((c - rh, c - rh, c + rh, c + rh), fill=(122, 140, 182, 255))

    return img.resize((size, size), Image.LANCZOS)


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(root, "res", "app.ico")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    imgs = [render(s) for s in sizes]
    imgs[-1].save(out, format="ICO", sizes=[(s, s) for s in sizes], append_images=imgs[:-1])
    if len(sys.argv) > 1:
        imgs[-1].save(sys.argv[1])
    print("wrote", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
