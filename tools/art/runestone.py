"""Runestone: a broken granite disc, held together by iron and by what was carved into it."""
import sys

from metals import *
from pack import Pack

P = Pack('runestone', sys.argv)

# low daylight from the upper left, a little fire from below, cold shadows
ST = Studio(lights=[((-0.55, -0.70, 0.46), 0.46, '#FFEBCF', 5.0), ((0.80, -0.35, 0.45), 0.30, '#A9CBEA', 1.3),
                    ((0.15, 0.88, 0.42), 0.40, '#FFA35A', 0.8), ((-0.95, 0.25, 0.25), 0.22, '#BFD6F5', 0.9)], sky='#A7B8C9', floor='#16110D', ambient=0.46)
# the same from all sides: for things that turn
ROUND = Studio(lights=[((math.sin(i * TAU / 6) * 0.75, -math.cos(i * TAU / 6) * 0.75, 0.50), 0.40, '#F3F0EA', 1.15) for i in range(6)], sky='#9AA6B2', floor='#9AA6B2', ambient=0.34)

TEAL, TEAL_HOT, AMBER = '#14E6C6', '#E4FFF8', '#FF9A2E'
GREY = ('#53575A', '#9A9890', '#9C8767')
SLATE = ('#2E343B', '#626C74', '#5E5A50')


# ------------------------------------------------------------------ small helpers
def polar_noise(c, na, nr, seed, r0=0.0, r1=1.2, octaves=1, gain=0.5, A=None, R=None):
    """Smooth random field on a polar grid (na cells around, nr cells outward), without a seam."""
    A, R = c.A if A is None else A, c.R if R is None else R
    out, amp, tot = np.zeros(c.shape, F), 1.0, 0.0
    for o in range(octaves):
        n, m = na * 2 ** o, nr * 2 ** o
        g = rng(seed + 31 * o).standard_normal((m + 2, n)).astype(F)
        u = (A / TAU + 2.0) % 1.0 * n
        v = clamp((R - r0) / (r1 - r0), 0, 0.9999) * m
        iu, iv = np.floor(u).astype(np.int32), np.floor(v).astype(np.int32)
        fu, fv = (u - iu).astype(F), (v - iv).astype(F)
        fu, fv = fu * fu * (3 - 2 * fu), fv * fv * (3 - 2 * fv)
        iu %= n
        ju = (iu + 1) % n
        a = g[iv, iu] * (1 - fu) + g[iv, ju] * fu
        b = g[iv + 1, iu] * (1 - fu) + g[iv + 1, ju] * fu
        out += amp * (a * (1 - fv) + b * fv)
        tot += amp
        amp *= gain
    return (out / tot).astype(F)


def line_noise(x, seed, n=256):
    """Smooth random numbers along one coordinate."""
    g = rng(seed).standard_normal(n).astype(F)
    i = np.floor(x).astype(np.int32)
    f = (x - i).astype(F)
    f = f * f * (3 - 2 * f)
    return g[i % n] * (1 - f) + g[(i + 1) % n] * f


def rock(c, seed, wide, rough=1.0, tones=GREY):
    """Weathered granite. wide: how many pixels on screen the picture covers. Gives height (canvas units) and colour."""
    k = 2 * c.extent / wide
    sh = c.shape
    broad, mid, fine = fbm(sh, wide / 75, seed, 4), fbm(sh, wide / 22, seed + 2, 4), fbm(sh, wide / 7, seed + 4, 3)
    H = k * rough * (2.2 * broad + 1.05 * mid + 0.34 * fine)
    # flakes: the surface has come away in thin layers
    fl = 0.8 * fbm(sh, wide / 40, seed + 5, 5) + 0.2 * mid
    for lvl, dep in ((0.22, 1.1), (0.55, 1.3)):
        H = H - k * rough * dep * smooth(lvl, lvl + 0.05, fl)
    qx, qy = c.X + 1.6 * k * fbm(sh, wide / 9, seed + 6, 2), c.Y + 1.6 * k * fbm(sh, wide / 9, seed + 7, 2)
    d1, _, v = worley(qx, qy, 1 / (13 * k), seed + 8, second=True)
    pit = smooth(0.05 + 0.40 * (v - 0.86) / 0.14, 0.0, d1) * (v > 0.86)
    e1, _, w = worley(qx, qy, 1 / (5.5 * k), seed + 9, second=True)
    pit2 = smooth(0.42, 0.10, e1) * (w > 0.88)
    H = H - k * rough * (2.2 * pit + 0.9 * pit2)
    # colour: big stains, mineral grains
    t = clamp(0.5 + 0.36 * fbm(sh, wide / 60, seed + 11, 5) + 0.10 * fine)
    col = mix(rgb(tones[0]), rgb(tones[1]), t[..., None])
    warm = smooth(0.0, 1.0, fbm(sh, wide / 95, seed + 13, 4))
    col = mix(col, rgb(tones[2]), (0.42 * warm)[..., None])
    col = mix(col, rgb('#4A5662'), (0.35 * smooth(0.0, 1.0, fbm(sh, wide / 80, seed + 17, 4)))[..., None])
    g1, _, gv = worley(c.X, c.Y, 1 / (2.6 * k), seed + 14, second=True)
    grain = smooth(0.62, 0.25, g1)
    col = mix(col, rgb('#D6D3CA'), ((0.20 if tones is GREY else 0.07) * grain * (gv > 0.84))[..., None])
    col = mix(col, rgb('#1C1D20'), (0.34 * grain * (gv < 0.13))[..., None])
    col = mix(col, rgb('#2A2A2A'), (0.5 * pit + 0.35 * pit2)[..., None])
    return H.astype(F), col.astype(F)


def cracks(c, seed, wide, spacing=64, width=0.9, some=0.25):
    """Thin broken lines of a split surface, 0 to 1."""
    k = 2 * c.extent / wide
    wx, wy = 5 * k * fbm(c.shape, wide / 22, seed, 4), 5 * k * fbm(c.shape, wide / 22, seed + 1, 4)
    d1, d2, _ = worley(c.X + wx, c.Y + wy, 1 / (spacing * k), seed + 2, second=True)
    gate = smooth(some, some + 0.5, fbm(c.shape, wide / 70, seed + 3, 3))
    return (clamp(1 - (d2 - d1) * spacing / width) * gate).astype(F)


def moss_on(c, H, ao, seed, wide, amount=0.0, bias=0.0):
    """Where moss has settled, 0 to 1, and its fluff as height."""
    k = 2 * c.extent / wide
    n = 0.55 * fbm(c.shape, wide / 48, seed, 5) + 0.30 * fbm(c.shape, wide / 11, seed + 1, 4)
    low = blur(H, 9 * k / c.px) - H
    m = smooth(0.30, 0.62, n + 0.75 * (1 - ao) + clamp(low / (3 * k), -0.4, 0.8) * 0.35 + amount + bias)
    fl = fbm(c.shape, wide / 3.2, seed + 2, 3)
    return m.astype(F), (m * k * (0.9 + 0.7 * fl)).astype(F), fl


def moss_color(c, fl, seed, wide):
    t = clamp(0.5 + 0.35 * fl + 0.30 * fbm(c.shape, wide / 30, seed + 5, 3))
    return mix(rgb('#232C10'), rgb('#7C8C34'), t[..., None])


def rust(c, seed, wide):
    """Old iron: colour and how metallic it still is."""
    a = fbm(c.shape, wide / 34, seed, 5)
    b = fbm(c.shape, wide / 7, seed + 1, 4)
    r = smooth(-0.55, 0.55, a + 0.5 * b)
    s = smooth(0.30, 0.90, 0.7 * a + 0.7 * fbm(c.shape, wide / 10, seed + 2, 3))
    col = mix(rgb('#5A5C60'), rgb('#4E3324'), r[..., None])
    col = mix(col, rgb('#8A5230'), (0.65 * s)[..., None])
    col = mix(col, rgb('#241A14'), (0.50 * smooth(0.2, 0.8, -b))[..., None])
    return col.astype(F), (1 - 0.70 * r).astype(F), b


def stone(c, H, col, ao=None, studio=None, reach=0.1, slope=0.8, spec=0.03, rough=0.62, r=(0.01, 0.03, 0.07), k=1.15):
    nx, ny, nz = normals(H, c.px)
    Hs = blur(H, 0.8 * c.ss)
    ao = occlusion(Hs, c.px, r, k) if ao is None else ao
    sh = cast(Hs, c.px, reach=reach, slope=slope) if reach else None
    return shade(studio or ST, nx, ny, nz, col, metal=0, rough=rough, spec=spec, ao=ao, sh=sh)


def sheet(frames, cols, name, quality=90, how='auto'):
    w, h = frames[0].size
    s = Image.new('RGBA', (w * cols, h * ((len(frames) + cols - 1) // cols)), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        s.paste(f, ((i % cols) * w, (i // cols) * h))
    P.save(s, name, quality, how)


def lamp(c, col):
    """A picture of light on black: it only adds."""
    c.col = np.maximum(col, 0).astype(F)
    c.alpha = np.ones(c.shape, F)
    im = c.image(tone=False)
    return im.convert('RGB').convert('RGBA')


def teal_light(core, halo):
    """Colour of the magic from how strong it is."""
    a = clamp(core)[..., None]
    return rgb(TEAL_HOT) * a ** 1.2 * 0.95 + rgb(TEAL) * (clamp(core + halo)[..., None] * (1 - 0.5 * a))


# ------------------------------------------------------------------ runes: the old alphabet, as chisel strokes
# every rune is a list of strokes in a box from -0.5 to 0.5 across and -1 to 1 down
RUNES = [
    [(-.25, -1, -.25, 1), (-.25, -.30, .40, -1), (-.25, .22, .40, -.48)],
    [(-.36, -1, -.36, 1), (-.36, -1, .36, -.42), (.36, -.42, .36, 1)],
    [(-.26, -1, -.26, 1), (-.26, -.55, .36, 0), (.36, 0, -.26, .55)],
    [(-.26, -1, -.26, 1), (-.26, -1, .40, -.48), (-.26, -.42, .40, .10)],
    [(-.32, -1, -.32, 1), (-.32, -1, .32, -.52), (.32, -.52, -.32, -.04), (-.32, -.04, .38, 1)],
    [(.30, -.72, -.32, 0), (-.32, 0, .30, .72)],
    [(-.42, -.95, .42, .95), (.42, -.95, -.42, .95)],
    [(-.26, -1, -.26, 1), (-.26, -1, .36, -.52), (.36, -.52, -.26, -.04)],
    [(-.36, -1, -.36, 1), (.36, -1, .36, 1), (-.36, -.32, .36, .32)],
    [(0, -1, 0, 1), (-.36, -.34, .36, .34)],
    [(0, -1, 0, 1), (-.22, -1, .22, -1), (-.22, 1, .22, 1)],
    [(.10, -.82, -.36, -.36), (-.36, -.36, .10, .12), (-.10, -.12, .36, .36), (.36, .36, -.10, .82)],
    [(0, -1, 0, 1), (0, -1, .40, -.50), (0, 1, -.40, .50)],
    [(-.34, -1, -.34, 1), (-.34, -1, .12, -.56), (.12, -.56, .40, -.90), (-.34, 1, .12, .56), (.12, .56, .40, .90)],
    [(0, -1, 0, 1), (0, -.16, -.44, -.95), (0, -.16, .44, -.95)],
    [(.28, -1, -.28, -.34), (-.28, -.34, .28, .34), (.28, .34, -.28, 1)],
    [(0, -1, 0, 1), (0, -1, -.44, -.48), (0, -1, .44, -.48)],
    [(-.26, -1, -.26, 1), (-.26, -1, .34, -.50), (.34, -.50, -.26, 0), (-.26, 0, .34, .50), (.34, .50, -.26, 1)],
    [(-.40, -1, -.40, 1), (.40, -1, .40, 1), (-.40, -1, 0, -.48), (0, -.48, .40, -1)],
    [(-.40, -1, -.40, 1), (.40, -1, .40, 1), (-.40, -1, .40, -.10), (.40, -1, -.40, -.10)],
    [(-.18, -1, -.18, 1), (-.18, -1, .36, -.42)],
    [(0, -.80, .44, 0), (.44, 0, 0, .80), (0, .80, -.44, 0), (-.44, 0, 0, -.80)],
    [(-.42, -1, -.42, 1), (.42, -1, .42, 1), (-.42, -1, .42, 1), (.42, -1, -.42, 1)],
    [(0, -1, .40, -.42), (.40, -.42, -.38, 1), (0, -1, -.40, -.42), (-.40, -.42, .38, 1)],
]


def strokes_on(c, D, segs, x, y, s, rot, room=0.0):
    """Lowers the distance field D to the strokes of one rune: middle x, y, half height s, turned by rot."""
    cs, sn = math.cos(rot), math.sin(rot)
    reach = s * 1.25 + max(room, s * 0.5)
    j0, j1 = int((x - reach + c.extent) / c.px), int((x + reach + c.extent) / c.px) + 2
    i0, i1 = int((y - reach + c.extent * c.aspect) / c.px), int((y + reach + c.extent * c.aspect) / c.px) + 2
    j0, i0, j1, i1 = max(0, j0), max(0, i0), min(c.w, j1), min(c.h, i1)
    if j1 <= j0 or i1 <= i0:
        return
    X, Y = c.X[i0:i1, j0:j1], c.Y[i0:i1, j0:j1]
    best = D[i0:i1, j0:j1]
    for ax, ay, bx, by in segs:
        x0, y0 = x + (ax * cs - ay * sn) * s, y + (ax * sn + ay * cs) * s
        x1, y1 = x + (bx * cs - by * sn) * s, y + (bx * sn + by * cs) * s
        ex, ey = x1 - x0, y1 - y0
        t = clamp(((X - x0) * ex + (Y - y0) * ey) / (ex * ex + ey * ey))
        best = np.minimum(best, np.hypot(X - x0 - ex * t, Y - y0 - ey * t))
    D[i0:i1, j0:j1] = best


def rune_ring(c, n, radius, s, first=0, step=1, room=0.0):
    D = np.full(c.shape, 9.0, F)
    for i in range(n):
        a = i * TAU / n
        x, y = c.polar(a, radius)
        strokes_on(c, D, RUNES[(i * step + first) % len(RUNES)], x, y, s, a, room)
    return D


def braid(c, strands, waves, r0, half, ribbon, R=None):
    """A plait that runs around the centre: height 0..1 of its flat ribbons, each with a line cut along the middle."""
    R = c.R if R is None else R
    y = (R - r0) / half
    best = np.full(c.shape, -9.0, F)
    for q in range(strands):
        t = c.A * waves + q * TAU / strands
        s = np.sin(t)
        mid = 0.93 * np.sign(s) * np.abs(s) ** 0.9
        slope = 0.93 * np.cos(t) * waves * half / r0
        d = np.abs(y - mid) * half / np.sqrt(1 + slope * slope) / ribbon
        z = np.cos((strands - 1) * t) if strands % 2 == 0 else np.sin((strands - 1) * t)
        prof = (1 - smooth(0.62, 1.0, d)) - 0.42 * gauss(d, 0.26)
        best = np.maximum(best, np.where(d < 1, 0.42 + 0.34 * z + 0.36 * prof, -9.0))
    return np.maximum(best, 0.0).astype(F)


def key_line(A, R, rm, amp, n):
    """Distance to a running key pattern around the centre."""
    w = TAU * rm / n
    X, Y = ((A + TAU) * rm) % w / w, (R - rm) / amp
    D = np.full(A.shape, 9.0, F)
    for q in ([(0.0, 1), (0.82, 1), (0.82, -0.28), (0.36, -0.28), (0.36, 0.32), (0.56, 0.32)], [(0.0, 1), (0.0, -1), (1.0, -1), (1.0, 1)]):
        for (ax, ay), (bx, by) in zip(q, q[1:]):
            ex, ey = (bx - ax) * w, (by - ay) * amp
            px, py = (X - ax) * w, (Y - ay) * amp
            t = clamp((px * ex + py * ey) / max(1e-9, ex * ex + ey * ey))
            D = np.minimum(D, np.hypot(px - ex * t, py - ey * t))
    return D


# ------------------------------------------------------------------ the disc
SPLITS = [0.42, 1.60, 2.74, 4.05, 5.18]        # where it broke, as angles


def split_lines(c, seed=5):
    """Number of the piece every point belongs to, and the distance to the nearest break."""
    A = c.A % TAU
    lab = np.zeros(c.shape, np.int32)
    near = np.full(c.shape, 9.0, F)
    for i, a in enumerate(SPLITS):
        x = c.R * 13
        off = 0.085 * line_noise(x, seed + 7 * i) + 0.040 * line_noise(x * 2.7 + 3, seed + 7 * i + 1) + 0.016 * line_noise(x * 7.1, seed + 7 * i + 2)
        lab += (A > a + off)
        near = np.minimum(near, np.abs((A - a - off + math.pi) % TAU - math.pi) * c.R * 0.85)
    return lab % len(SPLITS), near


def chipped(c, seed, chips, rim=0.990, k=1.0):
    """Distance field of a disc with pieces knocked out of its edge, and the freshly broken area."""
    edge = rim + 0.0035 * k * polar_noise(c, 34, 1, seed, octaves=3)
    d = c.R - edge
    broken = np.zeros(c.shape, F)
    r = rng(seed)
    for a, w, deep in chips:
        n = 7
        pts = []
        for i in range(n):
            t = i / (n - 1) * 2 - 1
            aa = a + w * t * (1 + 0.15 * r.random())
            rr = 1.0 - deep * (1 - abs(t) ** 1.6) * (0.75 + 0.5 * r.random())
            pts.append(c.polar(aa, rr))
        pts += [c.polar(a + w * 1.3, 1.2), c.polar(a - w * 1.3, 1.2)]
        q = c.poly(pts)
        d = np.maximum(d, -q)
        n2 = 0.010 * k * fbm(c.shape, 60, seed + int(a * 100), 3)
        broken = np.maximum(broken, smooth(0.026 * k, 0.0, q + n2))
    return d, broken


class Disc:
    """The plate. bands: rune band (two radii) and hoop (two radii), as parts of the radius; runes: how many, radius, half height, half width."""

    def __init__(self, size, ss, wide, bands, seed, runes, chips, plait=None, split=False, key=None):
        c = self.c = Canvas(P.px(size), P.ss(ss), 1.0)
        u = self.u = 2.0 / wide                        # one pixel on screen
        r_run0, r_run1, r_hoop0, r_hoop1 = bands
        Hr, col = rock(c, seed, wide)
        # edges of the bands waver, and have broken away in places
        wob = u * (0.9 * fbm(c.shape, wide / 30, seed + 20, 3) + 0.4 * fbm(c.shape, wide / 8, seed + 21, 2))
        nick = smooth(0.55, 1.0, fbm(c.shape, wide / 13, seed + 27, 3) + 0.25 * fbm(c.shape, wide / 60, seed + 28, 2))
        R = c.R + wob
        d, broken = chipped(c, seed + 3, chips)
        worn = clamp(0.80 + 0.40 * fbm(c.shape, wide / 40, seed + 22, 3), 0.3, 1.15)   # carving is shallower where it has worn away

        def step(r, w, up):
            """0 inside r, 1 outside (or the other way round), over w pixels, with broken edges."""
            q = R + (u * 3.2 * nick if up else -u * 3.2 * nick)
            t = smooth(r - w * u * 0.5, r + w * u * 0.5, q)
            return t if up else 1 - t

        def groove(r, w, deep):
            return deep * u * clamp(1 - np.abs(R - r) / (w * u)) * worn

        dish = 14 * u * (1 - c.R ** 2)                                         # a little higher in the middle
        H = np.full(c.shape, 8.0 * u, F) + dish
        H = H + 4.0 * u * step(r_run1, 4.5, True)                              # the rim stands high
        H = H - 4.4 * u * step(r_run0, 4.0, True) * step(r_run1, 4.5, False)   # the rune band lies deep
        H = H - groove(r_run0 - 4.5 * u, 1.9, 2.6) - groove(r_run0 - 9.5 * u, 1.4, 1.5)
        H = H - 6.0 * u * smooth(r_hoop0 - 1.5 * u, r_hoop0 + 0.4 * u, R) * (1 - smooth(r_hoop1 - 0.4 * u, r_hoop1 + 1.5 * u, R))
        weave = np.zeros(c.shape, F)
        if plait:
            p0, p1 = plait
            H = H - 7.5 * u * step(p0, 3.6, True) * step(p1, 3.6, False)
            weave = braid(c, 4, 16, (p0 + p1) / 2, (p1 - p0) / 2 * 0.78, 3.6 * u, R) * smooth(p0, p0 + 2 * u, R) * (1 - smooth(p1 - 2 * u, p1, R))
            H = H + 9.5 * u * weave * clamp(worn + 0.2)
            for r, w, dd in ((p0 - 7 * u, 1.8, 2.4), (p1 + 7 * u, 1.8, 2.4), (p0 - 12 * u, 1.3, 1.4)):
                H = H - groove(r, w, dd)
        if key:
            k0, k1, kn = key
            H = H - 3.0 * u * step(k0 - 5 * u, 3.0, True) * step(k1 + 5 * u, 3.0, False)
            km, ka = (k0 + k1) / 2, (k1 - k0) / 2
            H = H + 3.6 * u * smooth(2.5 * u, 1.2 * u, key_line(c.A, R, km, ka, kn)) * clamp(worn + 0.1)
            for r, w, dd in ((k0 - 12 * u, 1.8, 2.4), (k0 - 17 * u, 1.3, 1.5), (k1 + 12 * u, 1.8, 2.4), (k1 + 17 * u, 1.3, 1.5)):
                H = H - groove(r, w, dd)
            for i in range(11):                                             # joints between the blocks
                a = i * TAU / 11 + 0.10 * math.sin(i * 5.1) + 0.2
                q = np.abs((c.A - a + math.pi) % TAU - math.pi) * c.R + wob * 0.8
                H = H - 3.4 * u * clamp(1 - q / (1.5 * u)) * (c.R < r_run0 - 3 * u) - 0.9 * u * smooth(5 * u, 0, q) * (c.R < r_run0 - 3 * u)
        H = np.minimum(H, bevel(d, 7 * u, 14.5 * u, 'round') + 1.0 * u)
        # tool marks: short strokes toward the middle, left by the mason
        H = H + 0.45 * u * polar_noise(c, 190, 10, seed + 30, octaves=2, gain=0.5) * smooth(0.30, 0.45, c.R)
        n, rr, s, w = runes
        D = self.D = rune_ring(c, n, rr, s)
        cut = clamp(1 - (D + 0.4 * u * fbm(c.shape, wide / 7, seed + 24, 2)) / w)
        H = H - 5.0 * u * np.power(cut, 0.7) * clamp(worn + 0.3)
        # weather
        cr = cracks(c, seed + 40, wide)
        H = H - 2.2 * u * cr
        H = H - 7.0 * u * broken * (0.75 + 0.45 * fbm(c.shape, wide / 10, seed + 25, 4, ridged=True))
        H = H + Hr
        self.lab, self.near = split_lines(c)
        if split:
            chipw = 1.0 + 1.8 * smooth(0.1, 0.9, fbm(c.shape, wide / 16, seed + 26, 3))
            H = H - 6.0 * u * clamp(1 - self.near / (0.9 * u * chipw)) ** 0.8
            H = H - 1.2 * u * smooth(4.5 * u, 0, self.near)

        # ---- the iron hoop
        hm = (r_hoop0 + r_hoop1) / 2
        hh = (r_hoop1 - r_hoop0) / 2 - 0.5 * u
        hd = np.abs(c.R - hm) - hh + 0.35 * u * polar_noise(c, 70, 1, seed + 52)
        icol, imet, ib = rust(c, seed + 50, wide)
        dent = worley(c.X, c.Y, 1 / (9 * u), seed + 51)
        Hi = 12.0 * u + dish + bevel(hd, 2.4 * u, 3.4 * u, 'chamfer') + 0.8 * u * smooth(0.1, 0.8, dent) + 0.35 * u * ib
        seam = np.abs((c.A - 2.2 + math.pi) % TAU - math.pi) * c.R        # where the ends of the hoop overlap
        Hi = Hi + 1.6 * u * smooth(12 * u, 10.5 * u, seam)
        nr = int(round(TAU * hm / (36 * u)))
        for i in range(nr):
            x, y = c.polar((i + 0.5) * TAU / nr, hm)
            q = np.hypot(c.X - x, c.Y - y)
            Hi = np.where(q < 3.6 * u, Hi + 3.4 * u * np.sqrt(clamp(1 - (q / (3.6 * u)) ** 2)), Hi - 0.8 * u * smooth(5.4 * u, 3.6 * u, q))
        hoop = self.hoop = c.cover(hd)
        Hf = np.where(hd < 0, Hi, H)

        ao = self.ao_of(Hf)
        # rust has run down the stone below the hoop
        run = clamp(fbm(c.shape, wide / 6, seed + 60, 3)) * blur(hoop, 2 * u / c.px)
        run = blur1(shift(run, 0, int(8 * u / c.px)), 9 * u / c.px, 0) * 1.5 + 0.45 * blur(hoop, 4 * u / c.px) * clamp(fbm(c.shape, wide / 30, seed + 61, 3) + 0.2)
        band = smooth(r_run0 - 1 * u, r_run0 + 2 * u, R) * (1 - smooth(r_run1 - 2 * u, r_run1 + 1 * u, R))
        col = col * (1 - 0.14 * band)[..., None]
        col = col * (1 - 0.24 * smooth(r_run0, r_run0 - 0.05, c.R) * smooth(0.0, 0.5, 1 - weave))[..., None]
        col = mix(col, rgb('#6B4022'), clamp(0.65 * run)[..., None])
        # dirt in the deep, fresh stone where it broke, lichen, moss
        cav = clamp((1 - ao) * 1.2) * (1 - hoop)
        col = mix(col, rgb('#17140F'), clamp(0.60 * cav + 0.80 * cut + 0.6 * cr)[..., None])
        col = mix(col, rgb('#B5AD9C'), (0.70 * broken * (1 - cav))[..., None])
        l1, _, lv = worley(c.X + 2.6 * u * fbm(c.shape, wide / 6, seed + 70, 3), c.Y + 2.6 * u * fbm(c.shape, wide / 6, seed + 71, 3), 1 / (30 * u), seed + 72, second=True)
        size_ = 0.12 + 0.36 * np.maximum(0, lv - 0.55)
        spot = smooth(size_ + 0.07, size_ - 0.07, l1) * (lv > 0.58) * smooth(-0.3, 0.3, fbm(c.shape, wide / 50, seed + 73, 3))
        ringed = 0.45 + 0.55 * smooth(0.2, 0.9, l1 / size_)
        lich = np.where((lv > 0.84)[..., None], rgb('#B98E3A'), rgb('#B4C0A6'))
        col = mix(col, lich, (0.55 * spot * ringed * (1 - cav))[..., None])
        mo, mh, fl = moss_on(c, blur(H, 0.8 * u / c.px), ao, seed + 80, wide, amount=-0.50, bias=0.22 * smooth(-0.2, 1.0, c.Y * 0.8 - c.X * 0.4))
        keep = 1 - 0.75 * band * smooth(7 * u, 3 * u, D)
        H = H + mh * keep * (1 - hoop)
        col = mix(col, moss_color(c, fl, seed + 80, wide), (0.90 * mo * keep)[..., None])

        self.d, self.Hi, self.hd = d, Hi, hd
        self.H, self.col = H, col
        self.Hf = np.where(hd < 0, Hi, H)
        self.icol, self.imet = icol, imet

    def ao_of(self, H):
        u = self.u
        return occlusion(blur(H, 0.8 * u / self.c.px), self.c.px, (2.5 * u, 6 * u, 15 * u), 1.10)

    def lit(self, H, iron):
        c, u = self.c, self.u
        ao = self.ao_of(H)
        nx, ny, nz = normals(H, c.px)
        sh = cast(blur(H, 0.8 * u / c.px), c.px, reach=26 * u, slope=0.82)
        if iron:
            return shade(ST, nx, ny, nz, mix(self.icol, rgb('#120B07'), clamp(0.8 * (1 - ao))[..., None]), metal=self.imet * 0.8, rough=0.36, ao=ao, sh=sh)
        return shade(ST, nx, ny, nz, self.col, metal=0, rough=0.62, spec=0.03, ao=ao, sh=sh)


EXPO = 1.42
CHIPS = [(0.62, 0.13, 0.050), (1.95, 0.07, 0.030), (2.62, 0.17, 0.062), (3.60, 0.06, 0.024), (4.72, 0.12, 0.046), (5.75, 0.08, 0.034)]
U0 = 2 / 482
RING0 = (24, 0.8505, 0.0335, 1.45 * U0)
# the five pieces: left, top, right, bottom (parts of the radius), so that the pictures fit together in skin.json
BOX = [None] * 5


def plate():
    """The inner disc in five pieces, its iron hoop, and the light in its cracks."""
    D = Disc(1000, 2, 482, (0.808, 0.893, 0.914, 0.959), 11, RING0, CHIPS, (0.545, 0.690), True)
    c = D.c
    bare = D.lit(D.H, False)
    c.put(bare, c.cover(D.d), D.H)
    whole = np.asarray(c.image(exposure=EXPO))
    n = whole.shape[0]
    s = c.ss
    for i in range(len(SPLITS)):
        cov = (D.lab == i).astype(F).reshape(n, s, n, s).mean(axis=(1, 3))
        a = whole[..., 3] / 255 * cov
        ys, xs = np.where(a > 0.02)
        g = 0.02
        x0, x1 = math.floor((xs.min() / n * 2 - 1) / g) * g, math.ceil(((xs.max() + 1) / n * 2 - 1) / g) * g
        y0, y1 = math.floor((ys.min() / n * 2 - 1) / g) * g, math.ceil(((ys.max() + 1) / n * 2 - 1) / g) * g
        x0, y0, x1, y1 = [max(-1.0, min(1.0, v)) for v in (x0, y0, x1, y1)]
        if BOX[i]:
            x0, y0, x1, y1 = BOX[i]
        px = lambda v: int(round((v + 1) / 2 * n))
        part = np.dstack([whole[..., :3], (a * 255 + 0.5).astype(np.uint8)])[px(y0):px(y1), px(x0):px(x1)]
        P.save(Image.fromarray(part, 'RGBA'), 'piece%d' % i, 90, 'jpg')
        print('   piece%d  x %.3f y %.3f size [%.3f, %.3f]' % (i, (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2))
    # the hoop, with the shadow it throws on the stone
    over = D.lit(D.Hf, False)
    dark = clamp(1 - over.mean(axis=2) / np.maximum(bare.mean(axis=2), 1e-4)) * smooth(0.075, 0.045, np.abs(c.R - 0.9365)) * c.cover(D.d)
    dark = np.where(dark < 0.04, 0, dark)
    c.col[:] = 0
    c.alpha = (clamp(dark) * 0.95).astype(F)
    c.put(D.lit(D.Hf, True), D.hoop)
    P.save(c.image(exposure=EXPO), 'hoop', 90)
    # light in the cracks
    gate = smooth(0.36, 0.48, c.R) * c.cover(D.d)
    glow = teal_light(0.9 * gauss(D.near, 1.3 * D.u) * gate, (0.75 * gauss(D.near, 2.2 * D.u) + 0.32 * gauss(D.near, 8 * D.u)) * gate)
    P.save(lamp(c, glow).resize((P.px(560), P.px(560)), Image.LANCZOS), 'cracklight', 88, 'jpg')


def outer():
    """The wider disc under it, for a second ring."""
    W = 752
    u = 2 / W
    chips = [(0.30, 0.07, 0.030), (1.30, 0.10, 0.040), (2.25, 0.05, 0.020), (3.35, 0.11, 0.042), (4.35, 0.05, 0.022), (5.30, 0.08, 0.032), (6.00, 0.05, 0.020)]
    D = Disc(1100, 2, W, (0.8765, 0.9315, 0.9450, 0.9740), 211, (38, 0.9040, 0.0215, 1.45 * u), chips, key=(0.742, 0.790, 46))
    c = D.c
    out = mix(D.lit(D.Hf, False), D.lit(D.Hf, True), D.hoop[..., None])
    out = out * (1 - 0.85 * smooth(0.62, 0.56, c.R))[..., None]
    c.put(out, c.cover(D.d), D.Hf)
    a = np.asarray(c.image(exposure=EXPO)).copy()
    n = a.shape[0]
    yy, xx = np.mgrid[0:n, 0:n]
    a[np.hypot(xx + 0.5 - n / 2, yy + 0.5 - n / 2) / (n / 2) < 0.55, :3] = (14, 13, 12)     # never seen: the inner disc lies on it
    P.save(Image.fromarray(a, 'RGBA'), 'outer', 88)


def runes():
    """Every rune as light."""
    fr = []
    for i in range(24):
        c = Canvas(P.px(72), P.ss(3), 0.0620)
        D = np.full(c.shape, 9.0, F)
        strokes_on(c, D, RUNES[i], 0, 0, RING0[2], 0, 0.1)
        w = RING0[3]
        fr.append(lamp(c, teal_light(smooth(1.15 * w, 0.40 * w, D), (0.34 * gauss(D, 2.3 * w) + 0.13 * gauss(D, 5.0 * w)) * smooth(0.060, 0.045, c.R))))
    sheet(fr, 8, 'runes', 92, 'jpg')


# ------------------------------------------------------------------ entries
def carving(c, kind, seed):
    """Distance to the carved lines on the rim of a boss."""
    rm, amp = 0.805, 0.074
    R = c.R + 0.006 * polar_noise(c, 26, 2, seed, octaves=2)
    if kind == 0:                                      # a zigzag
        n = 14
        t = np.abs((c.A / TAU * n + 100.25) % 1.0 * 2 - 1) * 2 - 1
        slope = 4 * amp * n / TAU / rm
        return np.abs(R - rm - amp * t) / math.sqrt(1 + slope * slope)
    if kind == 1:                                      # runes
        return rune_ring(c, 12, rm, 0.088, seed, 5)
    if kind == 2:
        return key_line(c.A, R, rm, amp, 11)
    n = 7                                              # two lines twisted around each other
    y = (R - rm) / amp
    D = np.full(c.shape, 9.0, F)
    for q in range(2):
        t = c.A * n + q * math.pi
        slope = np.cos(t) * n * amp / rm
        d = np.abs(y - np.sin(t)) * amp / np.sqrt(1 + slope * slope)
        D = np.minimum(D, np.where(np.cos(t) > -0.86, d, 9.0))
    return D


def boss():
    """Round stones the icons lie on: four carvings, and the light that fills them."""
    fr, gl = [], []
    W = 104.0
    for v in range(4):
        seed = 300 + 41 * v
        c = Canvas(P.px(232), P.ss(3), 1.0)
        Hr, col = rock(c, seed, W, 0.75, SLATE)
        chips = [[(0.9, 0.22, 0.10), (3.9, 0.14, 0.07)], [(2.2, 0.26, 0.11)], [(5.3, 0.20, 0.09), (1.7, 0.12, 0.06)], [(4.5, 0.24, 0.10), (0.2, 0.10, 0.05)]][v]
        d, broken = chipped(c, seed + 3, chips, 0.972, 2.4)
        D = carving(c, v, seed % 24)
        w = 0.031
        worn = clamp(0.85 + 0.35 * fbm(c.shape, 5, seed + 5, 3), 0.4, 1.1)
        H = bevel(d, 0.105, 0.17, 'round')
        rim = smooth(0.655, 0.700, c.R + 0.006 * polar_noise(c, 20, 2, seed + 6, octaves=2))
        H = np.where(c.R < 0.75, 0.005 + 0.165 * rim, H)
        for r in (0.705, 0.915):
            H = H - 0.030 * clamp(1 - np.abs(c.R - r) / 0.018) * worn
        cut = clamp(1 - D / w) * smooth(0.70, 0.72, c.R)
        H = H - 0.050 * np.power(cut, 0.7) * clamp(worn + 0.2)
        cr = cracks(c, seed + 9, W, 46, 1.0, 0.15) * rim
        H = H - 0.03 * cr - 0.10 * broken * (0.75 + 0.4 * fbm(c.shape, 12, seed + 8, 3, ridged=True)) + Hr * (0.15 + 0.85 * rim)
        ao = occlusion(blur(H, 0.8 * c.ss), c.px, (0.03, 0.08, 0.17), 1.1)
        cav = clamp((1 - ao) * 1.1)
        floor = 1 - smooth(0.645, 0.690, c.R)
        alb = mix(col, rgb('#0F1114'), clamp(0.55 * cav + 0.78 * cut + 0.5 * cr)[..., None])
        alb = mix(alb, rgb('#8F8C84'), (0.55 * broken * (1 - cav))[..., None])
        mo, mh, fl = moss_on(c, blur(H, 0.8 * c.ss), ao, seed + 80, W, amount=-0.62, bias=0.25 * smooth(0.0, 1.0, c.Y * 0.8 - c.X * 0.5))
        mo = mo * smooth(0.72, 0.80, c.R)
        H = H + mh * 0.8 * smooth(0.72, 0.80, c.R)
        alb = mix(alb, moss_color(c, fl, seed, W), (0.85 * mo)[..., None])
        alb = mix(alb, rgb('#14181C') * (1 + 0.25 * fbm(c.shape, 6, seed + 31, 4))[..., None], (0.94 * floor)[..., None])
        out = stone(c, H, alb, ao, reach=0.42, slope=0.72)
        # the recess is polished: it mirrors a little sky
        Hb = -0.22 * (1 - clamp(c.R / 0.66) ** 2)
        nx, ny, nz = normals(Hb, c.px)
        out = out * (1 - 0.45 * floor)[..., None] + (ST.reflect(nx, ny, nz, 0.30).mean(axis=2)[..., None] * rgb('#A9C6D6') * 0.016 + rgb('#6FA3B8') * (0.010 * smooth(0.1, 0.66, (c.Y * 0.8 + c.X * 0.5)))[..., None]) * floor[..., None]
        c.put(out, c.cover(d), H)
        fr.append(c.image(exposure=1.5))
        g = Canvas(P.px(232), P.ss(3), 1.0)
        core = smooth(1.15 * w, 0.30 * w, D) * smooth(0.70, 0.72, g.R)
        halo = 0.60 * gauss(D, 2.4 * w) * smooth(0.66, 0.72, g.R) + 0.55 * gauss(g.R - 0.705, 0.016) + 0.40 * gauss(g.R - 0.915, 0.014)
        inner = 0.34 * smooth(0.12, 0.655, g.R) ** 2 * smooth(0.70, 0.655, g.R) + 0.55 * gauss(g.R - 0.664, 0.022)
        around = 0.18 * gauss(g.R - 0.82, 0.12)
        gl.append(lamp(g, teal_light(0.92 * core, (halo + inner + around) * g.cover(g.R - 0.975))))
    sheet(fr, 2, 'boss', 90, 'jpg')
    sheet(gl, 2, 'bosslight', 90, 'jpg')
    c = Canvas(P.px(256), 1, 1.0)
    P.save(lamp(c, rgb(TEAL) * (gauss(c.R, 0.48) * smooth(1.0, 0.7, c.R) * 0.75)[..., None]), 'halo', 92, 'jpg')


def marks():
    """Glowing coals for running programs, a bronze knot for groups, an iron stud for buttons."""
    for name, lit in (('coal', 0), ('coal_on', 1)):
        c = Canvas(P.px(60), 4, 1.0)
        H = bevel(np.maximum(c.R - 0.95, 0.60 - c.R), 0.17, 0.20)
        n = fbm(c.shape, 5, 7, 4)
        H = np.where(c.R < 0.62, -0.05 + 0.12 * n, H)
        inner = smooth(0.64, 0.58, c.R)
        col, met, _ = rust(c, 9, 40)
        alb = mix(col, np.broadcast_to(rgb('#120A06'), c.shape + (3,)), inner[..., None])
        nx, ny, nz = normals(H, c.px)
        out = shade(ST, nx, ny, nz, alb, metal=met * 0.8 * (1 - inner), rough=0.35, ao=occlusion(H, c.px, (0.06, 0.16), 1)) * 1.3
        hot = clamp(0.55 + 0.55 * n + 0.35 * gauss(c.R, 0.4)) * inner
        ramp = mix(rgb('#8A1E04'), mix(rgb('#FF7A1A'), rgb('#FFE7A0'), smooth(0.55, 1.0, hot)[..., None]), smooth(0.2, 0.65, hot)[..., None])
        out = out * (1 - 0.6 * inner)[..., None] + ramp * (hot * (1.5 if lit else 0.10))[..., None]
        c.put(out, c.cover(c.R - 0.95), H)
        P.save(c.image(), name, how='png')
    c = Canvas(P.px(96), 1, 1.0)
    P.save(lamp(c, rgb(AMBER) * (gauss(c.R, 0.42) * smooth(1.0, 0.7, c.R) * 0.9)[..., None]), 'glow', 92, 'jpg')
    # three rings linked: more lies behind this one
    c = Canvas(P.px(72), 4, 1.0)
    H = np.full(c.shape, -1.0, F)
    for q in range(3):
        a = q * TAU / 3
        x, y = c.polar(a, 0.40)
        r = np.hypot(c.X - x, c.Y - y)
        ph = np.arctan2(c.X - x, -(c.Y - y)) - a
        d = np.abs(r - 0.40) - 0.125
        H = np.maximum(H, np.where(d < 0, 0.10 * np.sin(3 * ph) + 0.02 * q + bevel(d, 0.125, 0.16), -1))
    body = blur((H > -0.9).astype(F), 0.7)
    H = np.where(H > -0.9, H, 0)
    out = metal(c, H, V([0.50, 0.36, 0.18]), rough=0.30, grime=0.8, seed=5, studio=ST, dirt='#1C2A22', ao_r=(0.05, 0.12)) * 1.25
    c.put(out, body, H)
    P.save(c.image(), 'knot', how='png')
    c = Canvas(P.px(80), 4, 1.0)
    col, met, ib = rust(c, 19, 46)
    d = c.R - 0.93
    H = bevel(d, 0.22, 0.20) + 0.02 * ib
    H = np.where(c.R < 0.66, 0.16 - 0.06 * smooth(0.66, 0.60, c.R) + 0.012 * ib, H)
    nx, ny, nz = normals(H, c.px)
    out = shade(ST, nx, ny, nz, col * 0.8, metal=met * 0.7, rough=0.35, ao=occlusion(H, c.px, (0.05, 0.15), 1.2), sh=cast(H, c.px, reach=0.3, slope=0.8))
    c.put(out, c.cover(d), H)
    P.save(c.image(exposure=1.2), 'stud', how='png')


# ------------------------------------------------------------------ the basin in the middle
def basin():
    c = Canvas(P.px(540), P.ss(2), 1.12)
    W = 98 * 2.24
    u = 2.24 / W
    Hr, col = rock(c, 700, W, 0.8)
    Rw = c.R + u * (0.8 * polar_noise(c, 30, 3, 701, octaves=2) + 0.4 * fbm(c.shape, 30, 702, 3))
    d = Rw - 1.088
    for a, dp in ((0.9, 0.030), (2.5, 0.045), (4.4, 0.034), (5.6, 0.022)):
        x, y = c.polar(a, 1.115)
        d = np.maximum(d, -(np.hypot(c.X - x, c.Y - y) - dp - 0.030 + 0.012 * fbm(c.shape, 40, int(a * 10), 3)))
    H = bevel(d, 0.055, 0.115, 'round')
    H = np.where(Rw < 1.030, 0.115 - 0.085 * smooth(1.030, 1.008, Rw), H)              # the channel of the ring
    kerb = np.abs(Rw - 0.822) - 0.030
    H = np.where(Rw < 0.860, np.maximum(0.03, bevel(kerb, 0.024, 0.085) + 0.02), H)
    bowl = smooth(0.805, 0.790, Rw)
    Hb = -0.30 * (1 - clamp(Rw / 0.80) ** 2)
    H = np.where(Rw < 0.800, Hb + 0.02, H)
    ring = clamp(1 - np.abs(Rw - 0.56) / 0.010) + 0.8 * clamp(1 - np.abs(Rw - 0.505) / 0.007)
    H = H - 0.014 * ring * bowl + Hr * (1 - 0.6 * bowl)
    cr = cracks(c, 720, W, 50, 0.9, 0.2)
    H = H - 0.020 * cr
    ao = occlusion(blur(H, 0.8 * c.ss), c.px, (0.02, 0.06, 0.14), 1.15)
    cav = clamp((1 - ao) * 1.15)
    alb = mix(col, rgb('#12110F'), clamp(0.6 * cav + 0.5 * cr)[..., None])
    alb = mix(alb, rgb('#101A1E') * (1 + 0.35 * fbm(c.shape, 9, 731, 4))[..., None], (0.90 * bowl)[..., None])
    mo, mh, fl = moss_on(c, blur(H, 0.8 * c.ss), ao, 740, W, amount=-0.55, bias=0.2 * smooth(0, 1, c.Y - 0.4 * c.X))
    mo = mo * (1 - bowl)
    H = H + mh * 0.8 * (1 - bowl)
    alb = mix(alb, moss_color(c, fl, 740, W), (0.88 * mo)[..., None])
    out = stone(c, H, alb, ao, reach=0.30, slope=0.72)
    c.put(out, c.cover(d), H)
    P.save(c.image(exposure=1.42), 'basin', 88)


def dial():
    """The iron ring that turns, with runes and a spearhead, and the light that stays where it is when the ring turns."""
    c = Canvas(P.px(540), P.ss(2), 1.20)
    W = 98 * 2.4
    r0, r1 = 0.868, 0.998
    rm = (r0 + r1) / 2
    d = np.abs(c.R - rm) - (r1 - r0) / 2
    tip = c.poly([(0, -1.192), (0.115, -1.020), (0.058, -1.004), (0.072, -0.950), (-0.072, -0.950), (-0.058, -1.004), (-0.115, -1.020)])
    all_ = smin(d, tip, 0.015)
    icol, imet, ib = rust(c, 760, W)
    H = bevel(all_, 0.026, 0.040) + 0.006 * smooth(0.1, 0.8, worley(c.X, c.Y, 15, 761)) + 0.003 * ib
    H = np.maximum(H, np.where(tip < 0, bevel(tip, 0.075, 0.075, 'chamfer'), 0))
    n = 18
    D = np.full(c.shape, 9.0, F)
    for i in range(1, n):
        a = i * TAU / n
        x, y = c.polar(a, rm)
        strokes_on(c, D, RUNES[(i * 7 + 2) % 24], x, y, 0.044, a, 0.12)
    w = 0.0125
    cut = clamp(1 - D / w)
    for r in (r0 + 0.018, r1 - 0.018):
        H = H - 0.010 * clamp(1 - np.abs(c.R - r) / 0.007) * (all_ < 0)
    H = H - 0.022 * np.power(cut, 0.7)
    gem = np.hypot(c.X / 0.75, c.Y + 1.050) - 0.034
    H = np.where(gem < 0, 0.07 + dome(gem + 0.034, 0.034, 0.024), H)
    ao = occlusion(H, c.px, (0.012, 0.035, 0.08), 1.2)
    nx, ny, nz = normals(H, c.px)
    alb = mix(icol * 0.92, rgb('#0C0A09'), clamp(0.7 * (1 - ao) + 0.85 * cut)[..., None])
    alb = mix(alb, rgb('#0E5A52'), c.cover(gem)[..., None])
    out = shade(ROUND, nx, ny, nz, alb, metal=imet * 0.75 * (1 - c.cover(gem)), rough=0.4, ao=ao)
    c.put(out, c.cover(all_), H)
    P.save(c.image(exposure=1.25), 'dial', 90)
    core = smooth(1.2 * w, 0.3 * w, D) + c.cover(gem) * (0.35 + 0.65 * gauss(gem + 0.034, 0.024))
    halo = 0.36 * gauss(D, 2.2 * w) + 0.10 * gauss(D, 5.0 * w) + 0.55 * gauss(np.maximum(gem, 0), 0.035) + 0.18 * gauss(np.maximum(gem, 0), 0.09)
    P.save(lamp(c, teal_light(0.95 * core, halo)), 'diallight', 90, 'jpg')
    # shine and shadow of the ring, which do not turn
    c = Canvas(P.px(400), 2, 1.20)
    d = np.abs(c.R - rm) - (r1 - r0) / 2
    H = bevel(d, 0.030, 0.045)
    nx, ny, nz = normals(H, c.px)
    q = ST.reflect(nx, ny, nz, 0.30).mean(axis=2) * 0.5 + ST.diffuse(nx, ny, nz).mean(axis=2) * 0.5
    flat = float(q[(np.abs(c.R - rm) < 0.012)].mean())
    v = q / flat - 1
    sh = 1 - cast(np.where(d < 0, 0.03, 0.0) + np.where(np.abs(c.R - 1.06) < 0.032, 0.085, 0) + np.where(np.abs(c.R - 0.822) < 0.03, 0.06, 0), c.px, reach=0.25, slope=0.75)
    white, black = clamp(v * 0.30, 0, 0.55), clamp(-v * 0.85, 0, 0.6) + 0.45 * sh
    a = clamp(white + black * (1 - white))
    c.col = (np.ones(c.shape + (3,), F) * rgb('#FFE9C9')) * (white / np.maximum(a, 1e-4))[..., None]
    c.alpha = (a * c.cover(d)).astype(F)
    P.save(c.image(tone=False), 'dialshade', how='png')


def swirl():
    """Magic, churning slowly: two layers that turn against each other."""
    for name, seed, tw, na, p in (('swirl1', 41, 2.3, 5, 3.0), ('swirl2', 77, -1.5, 9, 2.4)):
        c = Canvas(P.px(380), 2, 1.0)
        lr = np.log(c.R + 0.10)
        w1 = polar_noise(c, 6, 6, seed, octaves=3, A=c.A + tw * lr, R=c.R)
        w2 = polar_noise(c, 7, 6, seed + 9, octaves=3, A=c.A + tw * lr, R=c.R)
        n = polar_noise(c, na, 5, seed + 21, octaves=5, gain=0.55, A=c.A + tw * lr + 0.30 * w1, R=c.R + 0.07 * w2)
        ridge = np.power(clamp(1 - np.abs(n) * 1.5), p)
        soft = smooth(-0.5, 1.0, n)
        env = smooth(0.10, 0.62, c.R) * smooth(1.0, 0.80, c.R)
        v = (0.75 * ridge + 0.30 * soft) * env
        col = rgb('#0BA890') * v[..., None] + rgb('#A8FFEF') * (np.power(ridge, 2.5) * env * 0.55)[..., None] + rgb('#1B5BA8') * (soft * env * 0.35)[..., None]
        P.save(lamp(c, col), name, 88, 'jpg')


# ------------------------------------------------------------------ fire
def tile_fbm(shape, cells, seed, octaves=4, gain=0.5):
    """Noise that repeats at the picture's border."""
    out, amp, tot = np.zeros(shape, F), 1.0, 0.0
    for o in range(octaves):
        out += amp * lattice(shape, cells * 2 ** o, seed + o * 17, tile=True)
        tot += amp
        amp *= gain
    return out / tot


def flame():
    """Sixteen frames of fire that run into each other: a few tongues, eaten away by noise that rises."""
    N, W, H_ = 16, 92, 150
    asp = H_ / W
    c = Canvas(P.px(W), 2, 1.0, aspect=asp)
    n1, n2 = tile_fbm(c.shape, 4, 5, 3), tile_fbm(c.shape, 9, 15, 3)
    v = (asp * 0.92 - c.Y) / (asp * 1.84)                              # 0 at the foot, 1 at the tip
    vv = clamp(v)
    fr = []
    for f in range(N):
        t = f / N
        a = np.roll(n1, -int(round(t * c.h)), axis=0)
        b = np.roll(np.roll(n2, -int(round(2 * t * c.h)), axis=0), int(0.13 * c.w), axis=1)
        x = c.X + (0.20 * a + 0.13 * b) * vv ** 0.7
        I = np.full(c.shape, -1.0, F)
        for off, wd, ht, ph, n in ((0.0, 0.62, 0.98, 0.0, 1), (-0.30, 0.36, 0.66, 0.37, 2), (0.32, 0.36, 0.72, 0.71, 1), (0.06, 0.34, 0.86, 0.2, 2)):
            top = ht * (1 + 0.13 * math.sin(TAU * (t * n + ph)))
            q = vv / top
            mid = off * (1 - 0.55 * q) + 0.16 * np.sin(TAU * (t * n + ph) - 3.2 * vv) * vv
            w = wd * np.power(q + 0.03, 0.30) * np.power(clamp(1 - q), 0.85) * np.sqrt(smooth(-0.03, 0.16, v)) + 1e-3
            I = np.maximum(I, np.where(q < 1, 1 - ((x - mid) / w) ** 2, -1))
        I = clamp(I - vv * (0.30 + 0.55 * b + 0.40 * a) + 0.04)
        hot = clamp(I * (1.12 - 0.72 * vv) - 0.22 * smooth(0.16, 0.0, v))
        c.col = np.zeros(c.shape + (3,), F)
        ramp = [(0.0, '#B01A02'), (0.16, '#E8480A'), (0.36, '#FF8A14'), (0.58, '#FFBE3A'), (0.78, '#FFE588'), (0.95, '#FFF8E0')]
        col = np.broadcast_to(rgb(ramp[0][1]), c.shape + (3,))
        for (q0, _), (q1, cc) in zip(ramp, ramp[1:]):
            col = mix(col, rgb(cc), smooth(q0, q1, hot)[..., None])
        c.col = col.astype(F)
        c.alpha = (smooth(0.0, 0.26, I) * (0.25 + 0.75 * smooth(-0.02, 0.20, v)) * 0.98).astype(F)
        fr.append(c.image(tone=False))
    sheet(fr, 4, 'flame', 90, 'jpg')


def torch():
    """Torches in iron brackets, for the left and the right."""
    fr = []
    for side in (1, -1):
        c = Canvas(P.px(84), P.ss(4), 1.0, aspect=2.30)
        X = c.X + 0.12 * side
        Y = c.Y
        # shaft
        t = clamp((Y + 0.55) / 2.6)
        rs = 0.235 - 0.085 * t
        shaft = np.maximum(np.abs(X) - rs, np.maximum(-Y - 0.75, Y - 2.02))
        Hs = np.sqrt(clamp(rs * rs - X * X, 0, 9))
        grain = linear_streaks((c.w, c.h), 5, 50 * c.ss).T
        wcol = mix(rgb('#2A1A10'), rgb('#6E4A2C'), clamp(0.5 + 0.35 * grain + 0.2 * fbm(c.shape, 10, 3, 3))[..., None])
        spike = c.taper(-0.12 * side, 2.0, 0.10, -0.12 * side, 2.27, 0.015)
        # arm to the disc
        ax = -0.12 * side
        arm = c.taper(ax, 0.62, 0.085, 0.97 * side, 0.36, 0.10)
        arm2 = c.taper(ax, 1.12, 0.055, 0.70 * side, 0.50, 0.050)
        foot = c.box(0.085, 0.30, x=0.92 * side, y=0.36, r=0.05)
        H = np.where(shaft < 0, Hs, -0.2)
        iron = np.full(c.shape, 9.0, F)
        Hi = np.full(c.shape, -0.2, F)
        parts = [(arm, 0.10 + bevel(arm, 0.08, 0.09)), (arm2, 0.06 + bevel(arm2, 0.05, 0.06)), (foot, 0.10 + bevel(foot, 0.05, 0.07))]
        for yb, rb, hb in ((0.62, 0.275, 0.10), (1.12, 0.250, 0.085), (-0.50, 0.30, 0.10), (1.88, 0.20, 0.09)):
            q = np.maximum(np.abs(X) - rb, np.abs(Y - yb) - hb)
            parts.append((q, np.sqrt(clamp(rb * rb - X * X, 0, 9)) + 0.06 * smooth(0, -0.05, np.abs(Y - yb) - hb)))
        parts.append((spike, np.sqrt(clamp(0.1 ** 2 - X * X, 0, 9))))
        # basket: bars that flare outward, and two hoops
        flare = lambda y: 0.27 + 0.46 * clamp((-y - 0.55) / 1.05) ** 0.8
        rb = flare(Y)
        inside = (Y < -0.50) & (Y > -1.62)
        for q in (-0.92, -0.50, 0.0, 0.50, 0.92):
            dd = np.maximum(np.abs(X - q * rb) - (0.070 - 0.022 * abs(q)), np.maximum(Y + 0.50, -Y - 1.62))
            parts.append((dd, rb * math.sqrt(max(0, 1 - q * q)) + 0.05 + bevel(dd, 0.05, 0.05)))
        for yb, hb in ((-1.56, 0.105), (-1.02, 0.07)):
            rr = float(flare(yb)) + 0.05
            bow = Y - yb - 0.09 * np.sqrt(clamp(1 - (X / rr) ** 2)) + 0.05
            dd = np.maximum(np.abs(X) - rr, np.abs(bow) - hb)
            parts.append((dd, np.sqrt(clamp(rr * rr - X * X, 0, 9)) + 0.10 + bevel(dd, 0.06, 0.05)))
        for dd, hh in parts:
            Hi = np.where(dd < 0, np.maximum(Hi, hh), Hi)
            iron = np.minimum(iron, dd)
        icol, imet, ib = rust(c, 41, 70)
        coal = np.where(inside, np.abs(X) - rb * 0.95, 9)
        cn = fbm(c.shape, 14, 7, 4)
        body = np.minimum(np.minimum(shaft, iron), coal)
        isiron = (iron < 0)
        H = np.where(isiron, Hi + 0.012 * ib, np.where(coal < 0, 0.10 + 0.08 * cn, H))
        nx, ny, nz = normals(H, c.px)
        ao = occlusion(H, c.px, (0.05, 0.14), 1.0)
        sh = cast(H, c.px, reach=0.5, slope=0.9)
        a = shade(ST, nx, ny, nz, wcol, metal=0, rough=0.5, ao=ao, sh=sh)
        b = shade(ST, nx, ny, nz, icol * 0.9, metal=imet * 0.75, rough=0.36, ao=ao, sh=sh)
        hot = clamp(0.5 + 0.8 * cn) * smooth(-0.5, -1.3, Y)
        e = mix(rgb('#3A0A02'), rgb('#FF9A30'), hot[..., None]) * (0.4 + 1.2 * hot)[..., None]
        out = np.where(isiron[..., None], b, np.where((coal < 0)[..., None], e, a))
        out = out + rgb('#FF8A2A') * (0.15 * smooth(0.2, -1.7, Y) * clamp(-ny * 0.8 + 0.25) * (isiron | (shaft < 0)))[..., None]
        c.put(out, c.cover(body), H)
        fr.append(c.image(exposure=1.35))
    sheet(fr, 2, 'torch', 92, 'jpg')
    c = Canvas(P.px(200), 1, 1.0)
    P.save(lamp(c, rgb('#FF9440') * (gauss(c.R, 0.46) * smooth(1.0, 0.65, c.R) * 0.8)[..., None]), 'firelight', 92, 'jpg')


# ------------------------------------------------------------------ small things
def bits():
    c = Canvas(P.px(48), 2, 1.0)
    P.save(lamp(c, rgb(TEAL) * (gauss(c.R, 0.40) * smooth(1, 0.7, c.R))[..., None] + rgb(TEAL_HOT) * gauss(c.R, 0.16)[..., None]), 'spark', how='png')
    P.save(lamp(c, rgb('#FF7A1A') * (gauss(c.R, 0.36) * smooth(1, 0.7, c.R))[..., None] + rgb('#FFF0C0') * gauss(c.R, 0.15)[..., None]), 'cinder', how='png')
    c = Canvas(P.px(96), 1, 1.0)
    n = fbm(c.shape, 3.0, 5, 4)
    r = c.R + 0.30 * n
    c.col[:] = rgb('#B8AC98') * (0.8 + 0.2 * smooth(-0.5, 0.5, n))[..., None]
    c.alpha = ((1 - smooth(0.15, 0.85, r)) * smooth(1.0, 0.75, c.R) * 0.6).astype(F)
    P.save(c.image(tone=False), 'dust', how='png')
    c = Canvas(P.px(44), 4, 1.0)
    d = c.poly([(-0.8, -0.2), (-0.2, -0.8), (0.6, -0.55), (0.85, 0.15), (0.3, 0.75), (-0.55, 0.6)])
    Hr, col = rock(c, 50, 30)
    H = bevel(d, 0.45, 0.4, 'chamfer') + 0.1 * fbm(c.shape, 5, 4, 3)
    c.put(stone(c, H, col), c.cover(d), H)
    P.save(c.image(exposure=1.4), 'chip', how='png')


# ------------------------------------------------------------------ other layouts
def slab():
    """Stone that repeats, for panels; a tablet for cards; a lintel for names."""
    n = P.px(360)
    pad = 48
    sh = (n, n)
    h = 1.6 * tile_fbm(sh, 4, 3, 5) + 0.5 * tile_fbm(sh, 20, 9, 3) + 0.22 * tile_fbm(sh, 60, 12, 2)
    pit = smooth(1.2, 2.0, tile_fbm(sh, 26, 21, 2, 0.4))
    h = h - 1.6 * pit
    t = clamp(0.5 + 0.32 * tile_fbm(sh, 5, 31, 4) + 0.12 * tile_fbm(sh, 40, 33, 2))
    col = mix(rgb('#2B2F33'), rgb('#4E5050'), t[..., None])
    col = mix(col, rgb('#57503F'), (0.4 * smooth(0, 1, tile_fbm(sh, 3, 41, 4)))[..., None])
    col = mix(col, rgb('#15150F'), (0.6 * pit)[..., None])
    moss = smooth(0.55, 1.0, tile_fbm(sh, 5, 51, 5, 0.6))
    col = mix(col, rgb('#3F4A1C'), (0.55 * moss)[..., None])
    W = lambda q: np.pad(q, ((pad, pad), (pad, pad)) + ((0, 0),) * (q.ndim - 2), mode='wrap')
    hh, cc = W(h).astype(F), W(col).astype(F)
    nx, ny, nz = normals(hh, 1.6)
    out = shade(ST, nx, ny, nz, cc, metal=0, rough=0.6, spec=0.03, ao=occlusion(hh, 1.0, (3, 9), 0.5))[pad:-pad, pad:-pad]
    im = to_srgb(film(out * 1.15))
    P.save(Image.fromarray((clamp(np.dstack([im, np.ones(sh)])) * 255 + 0.5).astype(np.uint8), 'RGBA'), 'slab', 84, 'jpg')

    def carved(w, aspect, name, wide):
        c = Canvas(P.px(w), P.ss(3), 1.0, aspect=aspect)
        u = 2 / wide
        Hr, col = rock(c, 900, wide, 0.8, SLATE)
        hx, hy = 1 - 2.2 * u, aspect - 2.2 * u
        d = c.box(hx, hy, r=7 * u) + u * (0.9 * fbm(c.shape, wide / 14, 901, 3))
        for x, y, r in ((hx, -hy, 8), (-hx, hy * 0.35, 5), (hx * 0.4, hy, 5), (-hx, -hy, 4)):
            d = np.maximum(d, -(np.hypot(c.X - x, c.Y - y) - r * u + 1.6 * u * fbm(c.shape, wide / 8, 903, 3)))
        H = bevel(d, 5 * u, 6 * u, 'round')
        q = c.box(hx - 9 * u, hy - 9 * u, r=4 * u)
        H = H - 2.6 * u * clamp(1 - np.abs(q) / (1.7 * u)) - 2.0 * u * smooth(0, -2.5 * u, q + 4 * u)
        H = H + Hr
        ao = occlusion(blur(H, 0.8 * c.ss), c.px, (2.5 * u, 6 * u), 1.1)
        alb = mix(col * 0.8, rgb('#0E0F10'), clamp(0.6 * (1 - ao) + 0.5 * clamp(1 - np.abs(q) / (1.7 * u)))[..., None])
        alb = alb * (1 - 0.35 * smooth(-3 * u, -7 * u, q))[..., None]
        mo, mh, fl = moss_on(c, H, ao, 905, wide, amount=-0.52, bias=0.25 * smooth(0, aspect, c.Y))
        mo = mo * smooth(-12 * u, -2 * u, q)
        alb = mix(alb, moss_color(c, fl, 905, wide), (0.85 * mo)[..., None])
        c.put(stone(c, H + mh * 0.6 * (mo > 0.3), alb, ao, reach=20 * u, slope=0.8), c.cover(d), H)
        P.save(c.image(exposure=1.3), name, 88, 'jpg')
    carved(240, 1.40, 'tablet', 104)
    carved(300, 0.36, 'lintel', 170)


P.run([plate, outer, runes, boss, marks, basin, dial, swirl, flame, torch, bits, slab])
P.sounds('stone')
P.finish()
