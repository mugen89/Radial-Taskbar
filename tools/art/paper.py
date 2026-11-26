"""Papercut: layers of cut coloured paper with soft shadows between them."""
import sys
from metals import *
from pack import Pack

P = Pack('paper', sys.argv)


def fibres(c, seed, amount=1.0):
    n = fbm(c.shape, 90, seed, 3) * 0.6 + fbm(c.shape, 14, seed + 1, 3) * 0.4
    s = blur1(white(c.shape, seed + 2), 5 * c.ss, 1) * 2.2 + blur1(white(c.shape, seed + 3), 5 * c.ss, 0) * 2.2
    return (n * 0.6 + s * 0.4) * amount


def sheet(c, d, color, seed=1, thick=0.010, shadow=0.030, dark=0.42, tone=None):
    """One piece of paper: d is its outline (negative inside). Baked with its own soft shadow below and to the right."""
    cov = c.cover(d)
    f = fibres(c, seed)
    H = -thick * 0.0 + thick * smooth(0.0, 0.010, -d) + 0.0011 * f
    nx, ny, nz = normals(H, c.px)
    lit = 0.80 + 0.20 * nz + 0.55 * (-(nx * 0.5 + ny * 0.8))
    base = rgb(color) if isinstance(color, str) else color
    col = np.broadcast_to(base, c.shape + (3,)) if np.ndim(base) < 3 else base
    # a very gentle light across the whole sheet
    grad = 1.03 - 0.05 * (c.X + c.Y * 1.4) / c.extent
    col = col * (lit * grad * (1 + 0.035 * f))[..., None]
    edge = smooth(0.012, 0.0, -d) * cov
    col = col + (edge * 0.10)[..., None]
    if shadow:
        s1 = shift(blur(cov, shadow / c.px), int(shadow * 0.45 / c.px), int(shadow * 0.8 / c.px)) * dark
        s2 = shift(blur(cov, shadow * 0.28 / c.px), int(shadow * 0.12 / c.px), int(shadow * 0.2 / c.px)) * dark * 0.55
        sh = clamp(1 - (1 - s1) * (1 - s2))
        c.put(rgb('#1B1420'), sh * (1 - c.alpha) + sh * c.alpha)
    c.put(clamp(col, 0, 1.2), cov)


def scallop(c, n, r, depth, rot=0.0, sharp=1.0):
    a = c.A * n / 2 + rot
    return (c.R - r - depth * (np.abs(np.cos(a)) ** sharp - 0.5)) * 0.9


def leaf(c, x, y, L, w, rot):
    """Pointed leaf standing outward at (x, y)."""
    px, py = c.X - x, c.Y - y
    cs, sn = math.cos(rot), math.sin(rot)
    u, v = px * cs + py * sn, px * sn - py * cs        # v outward
    t = clamp(v / L * 0.5 + 0.5)
    half = w * np.maximum(0, np.sin(np.pi * t)) ** 0.8
    return np.maximum(np.abs(u) - half, np.abs(v) - L) * 0.85


def discs():
    c = Canvas(P.px(900), P.ss(2), 1.12)
    sheet(c, scallop(c, 26, 1.0, 0.055, 0.0, 0.9), '#1F5A66', 1, shadow=0.05, dark=0.5)
    P.save(c.image(tone=False), 'disc1', 88)
    c = Canvas(P.px(900), P.ss(2), 1.12)
    sheet(c, scallop(c, 18, 1.0, 0.085, 0.4, 1.4), '#F0715C', 5, shadow=0.045)
    P.save(c.image(tone=False), 'disc2', 88)


def plate():
    c = Canvas(P.px(1000), P.ss(2), 1.06)
    d = c.R - 1.0
    # a lace border: leaves, dots and small arches cut out of the sheet
    n = 40
    cut = np.full(c.shape, 9, F)
    k = (c.A % (TAU / n)) - math.pi / n                # repeat one sector
    u, v = np.sin(k) * c.R, c.R
    t = clamp((v - 0.875) / 0.085)
    lf = np.maximum(np.abs(u) - 0.026 * np.maximum(0, np.sin(np.pi * t)) ** 0.9, np.abs(v - 0.9175) - 0.0425)
    cut = np.minimum(cut, lf)
    k2 = ((c.A + math.pi / n) % (TAU / n)) - math.pi / n
    u2 = np.sin(k2) * c.R
    cut = np.minimum(cut, np.hypot(u2, v - 0.945) - 0.013)
    cut = np.minimum(cut, np.hypot(u2, v - 0.893) - 0.008)
    d = np.maximum(d, -cut)
    slit = np.abs(c.R - 0.845) - 0.0035                 # a slit, held together by little bridges
    d = np.maximum(d, -np.where(np.abs(k) < 0.016, 9, slit))
    sheet(c, d, '#FFF4E2', 9, shadow=0.028, dark=0.40)
    P.save(c.image(tone=False), 'plate', 90)


def slot():
    c = Canvas(P.px(260), P.ss(3), 1.16)
    sheet(c, c.R - 0.98, '#FFFFFF', 21, thick=0.016, shadow=0.085, dark=0.36)
    ring = np.abs(c.R - 0.86) - 0.006
    c.shade_mul(1 - 0.10 * c.cover(ring))
    P.save(c.image(tone=False), 'slot', 92)
    # petals that unfold behind the hovered one
    for name, cols in (('petals', ('#FFC145', '#F0715C')), ('petals2', ('#7BC8A4', '#2F8F83'))):
        c = Canvas(P.px(320), P.ss(2), 1.12)
        for ringi, (col, m, L, w, r0) in enumerate(((cols[1], 10, 0.27, 0.15, 0.72), (cols[0], 10, 0.24, 0.13, 0.64))):
            d = np.full(c.shape, 9, F)
            for i in range(m):
                a = (i + 0.5 * ringi) * TAU / m
                x, y = c.polar(a, r0)
                d = np.minimum(d, leaf(c, x, y, L, w, a))
            d = np.minimum(d, c.R - 0.55)
            sheet(c, d, col, 30 + ringi, shadow=0.045, dark=0.34)
        P.save(c.image(tone=False), name, 90)
    c = Canvas(P.px(64), 4, 1.25)
    sheet(c, c.R - 0.9, '#2F8F83', 41, thick=0.03, shadow=0.16, dark=0.45)
    P.save(c.image(tone=False), 'dot', how='png')
    c = Canvas(P.px(64), 4, 1.25)
    sheet(c, c.star(5, 1.0, 0.52), '#F2A900', 42, thick=0.03, shadow=0.14, dark=0.45)
    P.save(c.image(tone=False), 'star', how='png')


def hub():
    c = Canvas(P.px(520), P.ss(2), 1.10)
    for i, (n, r, dep, col, rot) in enumerate(((14, 0.955, 0.10, '#F0715C', 0.0), (14, 0.88, 0.09, '#FFC145', math.pi / 2))):
        sheet(c, scallop(c, n, r, dep, rot, 0.8), col, 50 + i, shadow=0.045, dark=0.40)
    P.save(c.image(tone=False), 'flower', 90)
    c = Canvas(P.px(420), P.ss(2), 1.10)
    sheet(c, c.R - 0.98, '#FFF9EE', 60, shadow=0.045, dark=0.40)
    P.save(c.image(tone=False), 'face', 92)
    # the pointer: a folded arrow under the flower's rim
    c = Canvas(P.px(160), P.ss(3), 1.0)
    left = c.poly([(0, -0.86), (0, 0.30), (-0.62, 0.62)])
    right = c.poly([(0, -0.86), (0.62, 0.62), (0, 0.30)])
    whole = np.minimum(left, right)
    sheet(c, whole, '#E5533D', 70, shadow=0.09, dark=0.45)
    c.shade_mul(1 - 0.20 * c.cover(right))
    P.save(c.image(tone=False), 'arrow', how='png')


def bits():
    c = Canvas(P.px(256), 2, 1.0, aspect=0.25)
    cols = ['#F0715C', '#FFC145', '#2F8F83', '#7BC8A4']
    for i, col in enumerate(cols):
        cx = -0.75 + 0.5 * i
        d = c.box(0.15, 0.085, cx, 0, rot=0.35 * (i % 2 * 2 - 1), r=0.012) if i % 2 else c.circle(0.12, cx, 0)
        sheet(c, d, col, 80 + i, shadow=0)
    P.save(c.image(tone=False), 'confetti', how='png')


def panel():
    c = Canvas(P.px(300), P.ss(2), 1.0)
    sheet(c, c.box(0.86, 0.86, r=0.13), '#F0715C', 90, shadow=0.06, dark=0.40)
    sheet(c, c.box(0.80, 0.80, r=0.10), '#FFF6E6', 91, shadow=0.03, dark=0.35)
    P.save(c.image(tone=False), 'panel', 92)


P.run([discs, plate, slot, hub, bits, panel])
P.sounds('paper')
P.finish()
