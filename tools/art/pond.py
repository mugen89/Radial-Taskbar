"""Koi Pond: a garden pond seen from above. Stones, moss, clear water, lily pads, lotus flowers and koi."""
import sys
from metals import *
from pack import Pack

P = Pack('pond', sys.argv)
# late morning in a garden: warm sun from the upper left, blue sky, green bounce from below
SUN = Studio(lights=[((-0.46, -0.70, 0.60), 0.36, '#FFEFCF', 4.4), ((0.80, -0.25, 0.50), 0.32, '#CFE3FF', 1.3), ((0.15, 0.85, 0.45), 0.42, '#C4DCB4', 0.7),
                     ((-0.90, 0.25, 0.25), 0.22, '#DDEBFF', 0.7)], sky='#BFD6EA', floor='#2C3526', ambient=0.55)
DEEP = rgb('#06303C')
LIGHT_DIR = (-0.5, -0.7)


# ------------------------------------------------------------------ helpers
class Win:
    """A square part of a canvas around a point, with its own coordinates."""
    def __init__(self, c, x, y, r):
        e, h = c.extent, c.extent * c.aspect
        x0, x1 = int((x - r + e) / c.px) - 1, int((x + r + e) / c.px) + 2
        y0, y1 = int((y - r + h) / c.px) - 1, int((y + r + h) / c.px) + 2
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(c.w, x1), min(c.h, y1)
        self.ok = x1 > x0 + 1 and y1 > y0 + 1
        self.s = (slice(y0, y1), slice(x0, x1))
        self.X = c.X[self.s] - x
        self.Y = c.Y[self.s] - y


class Rocks:
    """Stones in one height field; the higher one wins, so they lean on each other."""
    TONES = ['#93897A', '#7F8488', '#8C7660', '#62676B', '#ABA08A', '#86705F', '#74797A', '#9A9283']

    def __init__(self, c, seed=1, tones=None):
        self.c, self.r = c, rng(seed)
        self.H = np.zeros(c.shape, F)
        self.alb = np.zeros(c.shape + (3,), F)
        self.cov = np.zeros(c.shape, F)
        self.top = np.zeros(c.shape, F)          # 0 at a stone's edge, 1 on its top
        self.n1 = fbm(c.shape, 10 * c.extent, seed + 1, 4)
        self.n2 = fbm(c.shape, 26 * c.extent, seed + 2, 5)
        self.n3 = fbm(c.shape, 5 * c.extent, seed + 3, 3)
        self.sp = blur(white(c.shape, seed + 4), 0.8 * c.ss)
        self.tones = [rgb(t) for t in (tones or self.TONES)]

    def add(self, x, y, a, b, rot=0.0, h=0.09, base=0.0, p=2.5, facets=3, tone=None, wob=0.045, rough=0.06, flat=2.4, vary=0.22, sink=0.0):
        c, r = self.c, self.r
        w = Win(c, x, y, 1.32 * max(a, b))
        if not w.ok:
            return
        cs, sn = math.cos(rot), math.sin(rot)
        u, v = (w.X * cs + w.Y * sn) / a, (-w.X * sn + w.Y * cs) / b
        ph = np.arctan2(v, u)
        rad = (np.abs(u) ** p + np.abs(v) ** p) ** (1 / p)
        m = 1 + self.n1[w.s] * wob
        for k in (2, 3, 4, 5, 7):
            m = m + (0.10 / k) * r.uniform(0.3, 1.0) * np.cos(k * ph + r.random() * TAU)
        rad = rad * m
        inside = rad < 1
        t = clamp(1 - rad)
        hh = h * (1 - (1 - t) ** flat) ** 0.5
        for _ in range(facets):
            q, tilt, off = r.random() * TAU, r.uniform(0.15, 0.50), r.uniform(0.80, 1.02)
            hh = smin(hh, h * (off + tilt * (u * math.cos(q) + v * math.sin(q))), 0.10 * h)
        # grain: broad lumps, then fine pits, less of it on the steep flank
        k = smooth(0.0, 0.25, t)
        hh = hh + h * k * (0.07 * self.n1[w.s] + rough * self.n2[w.s]) + h * 0.010 * self.sp[w.s] * k
        hh = np.maximum(hh, 0.002) + base - sink
        win = inside & (hh > self.H[w.s])
        tone = self.tones[int(r.integers(len(self.tones)))] if tone is None else tone
        f = 1 + vary * r.uniform(-1, 1)
        col = tone * f * (1 + 0.30 * self.n2[w.s] + 0.22 * self.n3[w.s] + 0.13 * self.sp[w.s])[..., None]
        if r.random() < 0.45:                    # layers in the rock
            q = r.random() * TAU
            lay = np.sin((u * math.cos(q) + v * math.sin(q)) * r.uniform(7, 15) + 2.2 * self.n1[w.s] * 3)
            col = col * (1 + 0.10 * lay)[..., None]
        if r.random() < 0.25:                    # a vein of quartz
            q, o = r.random() * TAU, r.uniform(-0.4, 0.4)
            d = np.abs(u * math.cos(q) + v * math.sin(q) - o + 0.22 * self.n1[w.s])
            col = mix(col, rgb('#E6E0D2'), (0.65 * smooth(0.045, 0.012, d) * smooth(-0.6, 0.4, self.n2[w.s] + 0.4))[..., None])
        col = np.maximum(col, 0.004)
        self.H[w.s] = np.where(win, hh, self.H[w.s])
        self.alb[w.s] = np.where(win[..., None], col, self.alb[w.s])
        self.top[w.s] = np.where(win, t, self.top[w.s])
        self.cov[w.s] = np.maximum(self.cov[w.s], inside.astype(F))


def tint_by_depth(col, depth, k=(2.3, 0.62, 0.52), scatter='#0E6A72', amount=0.9):
    """What water of this depth leaves of a colour."""
    d = depth[..., None]
    tr = np.exp(-V(k) * d)
    return col * tr + rgb(scatter) * amount * (1 - np.exp(-0.62 * d))


# ------------------------------------------------------------------ the pond
def edge(name, inner, big, seed, size=1060, ext=1.10):
    """Ring of garden stones: they stand in the water and throw their shadow on it."""
    c = Canvas(P.px(size), 2, ext)
    S = Rocks(c, seed)
    r = rng(seed + 50)
    # foot of the wall: small stones under water and outside, seen between the big ones
    mid = (inner + 0.985) / 2
    half = (0.985 - inner) / 2
    n = int(TAU * mid / (half * 1.05))
    for i in range(n):                           # an inner row, half sunk
        a = (i + r.uniform(-0.3, 0.3)) / n * TAU
        q = half * r.uniform(0.40, 0.62)
        x, y = c.polar(a, inner + half * r.uniform(0.20, 0.42))
        S.add(x, y, q * r.uniform(0.9, 1.4), q * r.uniform(0.75, 1.0), a + r.uniform(-0.5, 0.5), h=half * 0.42, facets=2)
    for i in range(n):                           # an outer row
        a = (i + 0.5 + r.uniform(-0.3, 0.3)) / n * TAU
        q = half * r.uniform(0.34, 0.60)
        x, y = c.polar(a, 0.985 - half * r.uniform(0.22, 0.50))
        S.add(x, y, q * r.uniform(0.9, 1.5), q * r.uniform(0.7, 1.0), a + r.uniform(-0.5, 0.5), h=half * 0.50, facets=3)
    # the main stones
    ws = r.uniform(0.72, 1.32, big)
    ws = ws / ws.sum() * TAU
    at = r.random()
    joints = []
    for w in ws:
        a = at + w / 2
        at += w
        joints.append(at)
        lng = w * mid * 0.5 * r.uniform(1.03, 1.14)
        rad = half * r.uniform(0.78, 1.04)
        x, y = c.polar(a, mid + half * r.uniform(-0.10, 0.14))
        S.add(x, y, lng, rad, a + r.uniform(-0.16, 0.16), h=half * r.uniform(0.80, 1.10), facets=int(r.integers(2, 5)), p=r.uniform(2.2, 3.0))
    # moss settles low, on the outside and in the joints
    H, alb, cov = S.H, S.alb, S.cov
    band = smooth(inner + half * 0.55, inner + half * 1.2, c.R) * smooth(1.0, 0.97, c.R + 0.018 * S.n1)
    patch = fbm(c.shape, 7 * ext, seed + 70, 4)
    low = 1 - smooth(0.15, 0.62, H / half)
    moss = clamp(smooth(0.05, 0.75, 0.62 * low + 0.75 * patch + 0.10 * S.n2) * band)
    moss = moss * smooth(-0.35, 0.15, patch + 0.15 + 0.4 * low)
    d1 = worley(c.X + 0.01 * S.n1, c.Y + 0.01 * S.n2, 46 / half * 0.085, seed + 71)
    cush = (1 - clamp(d1) ** 2) * 0.5 + 0.25 * S.n2 + 0.25 * S.sp
    ground = ((c.R > inner + half * 0.5) & (c.R < 0.965 + 0.012 * S.n1)).astype(F)
    moss = np.maximum(moss, ground * (cov < 0.5))
    H = np.maximum(H, ground * half * 0.12) + moss * half * (0.10 * cush + 0.04)
    gcol = mix(np.broadcast_to(rgb('#2E4718'), c.shape + (3,)), np.broadcast_to(rgb('#86A03A'), c.shape + (3,)), clamp(0.40 + 0.35 * cush + 0.30 * S.n1 + 0.15 * S.sp)[..., None])
    alb = mix(alb, gcol, moss[..., None])
    # lichen: pale spots on dry tops
    l1 = worley(c.X + 0.016 * S.n2, c.Y + 0.016 * S.n1, 17, seed + 80)
    lich = smooth(0.27, 0.18, l1 + 0.10 * S.n2) * smooth(0.2, 0.7, fbm(c.shape, 5 * ext, seed + 81, 3) + 0.35) * smooth(0.3, 0.6, S.top) * (1 - moss)
    alb = mix(alb, rgb('#B9BC96'), (0.50 * lich)[..., None])
    # the side that stands in the water is wet
    line = inner + half * (0.34 + 0.16 * S.n1)
    wet = smooth(line + half * 0.30, line - half * 0.10, c.R) * (1 - 0.5 * moss)
    alb = alb * (1 - 0.48 * wet)[..., None]
    algae = smooth(line - half * 0.05, line - half * 0.45, c.R) * (1 - moss)
    alb = mix(alb, rgb('#27401F'), (0.42 * algae)[..., None])
    nx, ny, nz = normals(H, c.px, 1.0)
    ao = occlusion(H, c.px, (half * 0.10, half * 0.30, half * 0.8), 1.25)
    sh = cast(H, c.px, LIGHT_DIR, slope=0.62, reach=half * 2.0)
    col = shade(SUN, nx, ny, nz, alb, metal=0, rough=0.75, spec=0.03, ao=ao, sh=sh)
    gl = shade(SUN, nx, ny, nz, alb, metal=0, rough=0.30, spec=0.05, ao=ao, sh=sh, clear=0.55)
    col = mix(col, gl, wet[..., None])
    a = np.maximum(S.cov, ground)
    a = blur(a, 0.5 * c.ss)
    # below the stones: shadow on the water and on whatever lies outside
    inside = smooth(inner + half, inner + half * 0.4, c.R)
    s = half
    shd = shift(a, int(0.22 * s / c.px), int(0.32 * s / c.px))
    sw = np.maximum(blur(shd, 0.12 * s / c.px) * 0.80, blur(shift(a, int(0.45 * s / c.px), int(0.62 * s / c.px)), 0.34 * s / c.px) * 0.70) * inside
    out = np.maximum(blur(shift(a, int(0.06 * s / c.px), int(0.14 * s / c.px)), 0.16 * s / c.px) * 0.75, blur(shift(a, int(0.12 * s / c.px), int(0.26 * s / c.px)), 0.42 * s / c.px) * 0.55) * (1 - inside)
    out = out * smooth(ext, ext - 0.05, c.R)
    c.put(rgb('#021A20'), clamp(sw).astype(F))
    c.put(rgb('#000000'), clamp(out).astype(F))
    # waterline: a thin bright rim of the water climbing up the stone
    near = blur(a, 0.045 * s / c.px)
    rim = smooth(0.04, 0.30, near) * (1 - a) * inside * clamp(0.55 + 0.7 * S.n2)
    c.put(rgb('#CFF3E6'), clamp(rim * 0.42).astype(F))
    c.put(col, a, H)
    t = rng(seed + 91)
    spots = []
    for a in joints:
        if t.random() < 0.50:
            x, y = c.polar(a + t.normal() * 0.012, mid + half * t.uniform(-0.15, 0.65))
            spots.append((x, y, t.uniform(0.75, 1.30)))
    tufts(c, seed + 90, half, spots)
    small(c.image(exposure=1.0), name, 84)


def blade(d, x, y, ang, length, width, bend, shade_):
    """One leaf of grass as a filled outline."""
    L, Rr = [], []
    for k in range(9):
        t = k / 8
        q = ang + bend * t * t
        px, py = x + math.sin(q) * length * t, y - math.cos(q) * length * t
        w = width * (1 - t) ** 0.7 * (0.55 + 0.45 * math.sin(math.pi * min(1, t * 1.4 + 0.2)))
        L.append((px - math.cos(q) * w, py - math.sin(q) * w))
        Rr.append((px + math.cos(q) * w, py + math.sin(q) * w))
    d.polygon(L + Rr[::-1], fill=shade_)


def tufts(c, seed, half, spots):
    """Grass that has taken root between the stones, and a few small flowers in the moss."""
    r = rng(seed)
    k = 1 / c.px

    def xy(x, y):
        return (x / c.extent + 1) * c.w / 2, (y / c.extent + 1) * c.h / 2
    shadow, mask = Image.new('L', (c.w, c.h), 0), Image.new('L', (c.w, c.h), 0)
    col = Image.new('RGB', (c.w, c.h), (40, 60, 20))
    sd, cd, md = ImageDraw.Draw(shadow), ImageDraw.Draw(col), ImageDraw.Draw(mask)
    for x0, y0, size in spots:
        n = int(r.integers(12, 24))
        for j in range(n):
            x, y = x0 + r.normal() * half * 0.09, y0 + r.normal() * half * 0.09
            q = (j + r.uniform(-0.6, 0.6)) / n * TAU
            ln, wd, bd = half * size * r.uniform(0.40, 0.95), half * r.uniform(0.026, 0.048), r.normal() * 0.7
            px, py = xy(x, y)
            g = r.random()
            tone = np.array([44 + 58 * g, 74 + 58 * g, 22 + 22 * g])
            blade(sd, px + 0.10 * half * k, py + 0.16 * half * k, q, ln * k, wd * k, bd, 190)
            blade(cd, px, py, q, ln * k, wd * k, bd, tuple(int(v * 0.8) for v in tone))
            blade(md, px, py, q, ln * k, wd * k, bd, 255)
            blade(cd, px - 0.35 * wd * k, py - 0.35 * wd * k, q, ln * k * 0.94, wd * k * 0.45, bd, tuple(int(min(255, v * 1.28)) for v in tone))
        if r.random() < 0.65:
            for j in range(int(r.integers(2, 5))):
                fx, fy = xy(x0 + r.normal() * half * 0.34, y0 + r.normal() * half * 0.34)
                q, f = r.random() * TAU, half * r.uniform(0.050, 0.075) * k
                sd.ellipse([fx - f + 0.05 * half * k, fy - f + 0.09 * half * k, fx + f + 0.05 * half * k, fy + f + 0.09 * half * k], fill=170)
                for e in range(5):
                    ex, ey = fx + math.sin(q + e * TAU / 5) * f, fy - math.cos(q + e * TAU / 5) * f
                    for d_, t_ in ((md, 255), (cd, (246, 240, 232) if e % 2 else (232, 224, 222))):
                        d_.ellipse([ex - f * 0.62, ey - f * 0.62, ex + f * 0.62, ey + f * 0.62], fill=t_)
                cd.ellipse([fx - f * 0.45, fy - f * 0.45, fx + f * 0.45, fy + f * 0.45], fill=(240, 190, 60))
    s = blur(np.asarray(shadow, F) / 255, 0.035 * half / c.px + 0.6)
    c.put(rgb('#050A04'), s * 0.60)
    c.put(from_srgb(np.asarray(col, F) / 255), np.asarray(mask, F) / 255)


def bed():
    """Bottom of the pond under clear water: sand and pebbles, shallow at the rim, deep in the middle."""
    c = Canvas(P.px(840), 2, 1.0)
    n1, n2, n3 = fbm(c.shape, 5, 21, 4), fbm(c.shape, 22, 22, 4), fbm(c.shape, 110, 23, 2)
    rip = np.sin((c.X * 0.8 + c.Y * 0.6 + 0.05 * n1) * 95 + 5 * n1)
    H = 0.0018 * rip + 0.004 * n2 + 0.0016 * n3
    alb = mix(np.broadcast_to(rgb('#8C7F62'), c.shape + (3,)), np.broadcast_to(rgb('#B9A984'), c.shape + (3,)), clamp(0.5 + 0.5 * n1)[..., None]) * (1 + 0.16 * n3 + 0.12 * n2)[..., None]
    S = Rocks(c, 33, ['#A79B82', '#8B8577', '#6C6F6C', '#C4B99F', '#8E6F57', '#59605E', '#B9A07E', '#7C6A58', '#D2C8B0', '#4E5350'])
    r = rng(8)
    for i in range(int(2400 * (0.6 if P.draft < 1 else 1))):
        a, q = r.random() * TAU, math.sqrt(r.random()) * 0.985
        x, y = c.polar(a, q)
        dens = float(n1[min(c.h - 1, max(0, int((y + 1) * c.h / 2))), min(c.w - 1, max(0, int((x + 1) * c.w / 2)))])
        if r.random() > 0.55 + 0.6 * dens:
            continue
        s = 0.008 + 0.030 * r.random() ** 3.0
        S.add(x, y, s * r.uniform(1.0, 1.35), s, r.random() * TAU, h=s * 0.85, facets=0, wob=0.03, rough=0.02, flat=2.0)
    for _ in range(26):
        a, q = r.random() * TAU, r.uniform(0.45, 0.95)
        x, y = c.polar(a, q)
        s = r.uniform(0.036, 0.070)
        S.add(x, y, s * r.uniform(1.0, 1.4), s, r.random() * TAU, h=s * 0.8, facets=2, flat=2.0)
    for i in range(46):                          # foot of the wall
        a = (i + r.uniform(-0.3, 0.3)) / 46 * TAU
        x, y = c.polar(a, r.uniform(0.90, 0.99))
        s = r.uniform(0.045, 0.08)
        S.add(x, y, s * 1.3, s, a, h=s * 0.9, facets=2)
    k = blur(S.cov, 0.5 * c.ss)[..., None]
    alb = mix(alb, S.alb, k)
    H = np.maximum(H, S.H)
    nx, ny, nz = normals(H, c.px, 0.9)
    ao = occlusion(H, c.px, (0.006, 0.02, 0.05), 1.2)
    sh = cast(H, c.px, LIGHT_DIR, slope=0.55, reach=0.10)
    col = shade(SUN, nx, ny, nz, alb, metal=0, rough=0.8, spec=0.02, ao=ao, sh=sh)
    # silt and algae gather in patches
    silt = smooth(0.1, 0.9, fbm(c.shape, 4, 41, 4) + 0.25)
    col = mix(col, rgb('#4E5B34') * 0.55, (0.30 * silt)[..., None])
    # depth: shallow shelf at the rim, then falling away
    depth = 0.30 + 2.6 * smooth(0.99, 0.22, c.R + 0.035 * n1)
    # what lies deeper is less sharp
    soft = blur(col, 3.0 * c.ss * P.draft)
    col = mix(col, soft, (0.70 * smooth(0.75, 0.40, c.R))[..., None])
    col = tint_by_depth(col * 1.25, depth, scatter='#0A5058', amount=0.95)
    # light falls in from the upper left, so the far side is brighter
    lx = clamp(0.5 + 0.5 * (c.X * 0.55 + c.Y * 0.75))
    col = col * (0.84 + 0.32 * lx)[..., None]
    c.put(col, np.ones(c.shape, F))
    P.save(c.image(exposure=1.10), 'bed', quality=84)


def caustic():
    """Light gathered by the waves, worked out by bending a fine grid of rays; seamless in both directions."""
    n = P.px(420)
    m = n * 5
    g = (np.arange(m, dtype=F) + 0.5) / m
    X, Y = np.meshgrid(g, g)
    r = rng(12)
    gx, gy = np.zeros((m, m), F), np.zeros((m, m), F)
    count = 0
    while count < 34:
        kx, ky = int(r.integers(-9, 10)), int(r.integers(-9, 10))
        q = math.hypot(kx, ky)
        if not 2.8 < q < 9.4:
            continue
        count += 1
        a, p = q ** -1.25 * r.uniform(0.6, 1.2), r.random() * TAU
        s = np.cos(TAU * (kx * X + ky * Y) + p) * a
        gx += s * kx
        gy += s * ky
    k = 0.0185 / float(np.std(gx))
    x, y = (X + gx * k) % 1.0 * n, (Y + gy * k) % 1.0 * n
    ix, iy = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    fx, fy = x - ix, y - iy
    img = np.zeros(n * n)
    for ox, oy, wgt in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        img += np.bincount(((iy + oy) % n * n + (ix + ox) % n).ravel(), wgt.ravel(), n * n)
    img = (img.reshape(n, n) / (m * m / (n * n))).astype(F)
    z = n / 420
    img = 0.62 * wrapblur(img, 0.9 * z) + 0.38 * wrapblur(img, 3.0 * z)
    v = clamp(0.40 * np.log1p(np.maximum(img - 0.55, 0) * 1.6))
    c = Canvas(n, 1, 1.0)
    c.col = (v[..., None] * mix(rgb('#8FF0DC'), rgb('#FFFFF0'), clamp(v * 1.6)[..., None])).astype(F)
    c.alpha[:] = 1
    P.save(c.image(tone=False), 'caustic', how='jpg', quality=84)


def wrapblur(a, s):
    pad = 48
    return blur(np.pad(a, pad, mode='wrap'), s)[pad:-pad, pad:-pad]


def leaf(size, seed, notch, gap, ext=1.14):
    """One lily pad: notch, veins, a lifted rim, drops of water."""
    c = Canvas(size, 3, ext)
    r = rng(seed)
    da = (c.A - notch + math.pi) % TAU - math.pi
    rad = 0.955
    for k in (2, 3, 5, 8, 13):
        rad = rad + r.uniform(0.3, 1) * 0.030 / k * np.cos(k * c.A + r.random() * TAU)
    d_out = c.R - rad
    px, py = c.R * np.sin(da), c.R * np.cos(da)
    bend = r.uniform(-0.10, 0.10)
    q = px - bend * py * py
    half = 0.012 + np.maximum(py - 0.02, 0) * math.tan(math.radians(gap)) + 0.05 * np.maximum(py - 0.45, 0) ** 1.5
    d_notch = np.where(py > -0.1, half - np.abs(q), -1.0) * 0.97
    d_notch = np.where(py < 0.02, -np.hypot(px, py - 0.02), d_notch)
    d = smax(d_out, d_notch, 0.085)
    n1, n2, n3 = fbm(c.shape, 4, seed + 1, 4), fbm(c.shape, 14, seed + 2, 4), fbm(c.shape, 46, seed + 3, 3)
    # veins: from the stalk to the rim, each forking once
    many = int(r.integers(13, 17))
    free = TAU - 0.30
    vein = np.zeros(c.shape, F)
    dist = np.full(c.shape, 9.0, F)
    wave = 0.030 * n1
    for i in range(many):
        t0 = 0.15 + (i + 0.5 + r.uniform(-0.18, 0.18)) / many * free
        for s in (-1, 1):
            spl = s * np.maximum(c.R - r.uniform(0.42, 0.60), 0) * 0.23
            e = np.abs((da - t0 - spl + wave + math.pi) % TAU - math.pi) * c.R
            dist = np.minimum(dist, e)
            w = 0.017 * (1 - 0.62 * clamp(c.R))
            vein = np.maximum(vein, smooth(w, w * 0.25, e) * smooth(0.99, 0.80, c.R))
    d1, d2, _ = worley(c.X + 0.05 * n2, c.Y + 0.05 * n2, 9.5, seed + 9, second=True)
    net = smooth(0.07, 0.015, d2 - d1) * smooth(0.10, 0.35, c.R)
    quilt = 1 - np.exp(-(dist / 0.065) ** 2)
    H = 0.05 + 0.017 * quilt - 0.004 * net + 0.030 * n1 + 0.0035 * n3
    H = H + 0.052 * gauss(d + 0.012, 0.050) * (0.65 + 0.5 * n1) - 0.035 * smooth(0.5, 0.0, c.R)
    H = np.where(d < 0, H, 0) * smooth(0.004, -0.030, d)
    # colour
    tones = [('#1F5A28', '#4F9A34', '#8DB84A'), ('#24632C', '#58A53C', '#9BC04E'), ('#1E5530', '#458F3E', '#7FAF4A'), ('#2B6324', '#68A434', '#A9BF4C')]
    dk, md, lt = [rgb(t) for t in tones[int(r.integers(len(tones)))]]
    t = clamp(0.42 + 0.30 * n1 + 0.20 * n2 + 0.20 * (quilt - 0.6))
    alb = dk * (1 - t[..., None]) + md * t[..., None]
    alb = mix(alb, lt, (0.50 * smooth(0.45, 1.0, c.R + 0.06 * n2) * (0.65 + 0.5 * n1))[..., None])
    alb = mix(alb, rgb('#B9D27E'), (0.62 * vein)[..., None])
    alb = mix(alb, lt, (0.22 * net)[..., None])
    alb = mix(alb, rgb('#C9DB8E'), (0.5 * gauss(np.hypot(c.X, c.Y), 0.055))[..., None])
    rim = smooth(-0.050, -0.004, d)
    alb = mix(alb, rgb('#9A5A2E'), (rim * clamp(0.30 + 0.6 * fbm(c.shape, 5, seed + 6, 3)))[..., None])
    age = smooth(0.55, 0.85, n2 + 0.45 * smooth(0.6, 1, c.R) + 0.15)
    alb = mix(alb, rgb('#9C8A34'), (0.24 * age)[..., None])
    spots = smooth(0.15, 0.10, worley(c.X, c.Y, 4.2, seed + 12)) * (fbm(c.shape, 3, seed + 13, 2) > 0.45)
    alb = mix(alb, rgb('#5A4A1E'), (0.35 * spots)[..., None])
    # drops
    drops = np.zeros(c.shape, F)
    pts = []
    for _ in range(int(r.integers(3, 6))):
        a, p0 = r.random() * TAU, r.uniform(0.50, 0.84)
        s = r.uniform(0.026, 0.056)
        x, y = c.polar(a, p0)
        if abs(((a - notch + math.pi) % TAU) - math.pi) < 0.35:
            continue
        pts.append((x, y, s))
        drops = np.maximum(drops, np.sqrt(clamp(1 - ((c.X - x) ** 2 + (c.Y - y) ** 2) / (s * s))))
    nx, ny, nz = normals(H, c.px, 1.0)
    ao = occlusion(H, c.px, (0.02, 0.06, 0.15), 0.8)
    sh = cast(H, c.px, LIGHT_DIR, slope=0.55, reach=0.16)
    col = shade(SUN, nx, ny, nz, alb, metal=0, rough=0.42, spec=0.05, ao=ao, sh=sh, clear=0.16)
    # light that shines through the raised rim
    col = col + alb * (0.30 * gauss(d + 0.03, 0.06) * clamp(0.5 - 0.5 * (nx * 0.5 + ny * 0.7)))[..., None]
    face = -(c.X * 0.55 + c.Y * 0.83) / np.maximum(c.R, 1e-3)
    col = col + rgb('#F2FFD0') * (0.30 * gauss(d + 0.026, 0.016) * clamp(face) + 0.10 * gauss(d + 0.085, 0.030) * clamp(-face))[..., None]
    for x, y, s in pts:
        e = np.hypot(c.X - x, c.Y - y)
        col = col * (1 - 0.40 * gauss(np.hypot(c.X - x - s * 0.35, c.Y - y - s * 0.5) , s * 1.05) * (e > s))[..., None]
        ins = smooth(s, s * 0.88, e)
        lo = clamp(0.5 + 0.5 * ((c.X - x) * 0.55 + (c.Y - y) * 0.83) / s)
        col = mix(col, col * (0.55 + 1.15 * lo ** 2)[..., None] + 0.03, ins[..., None])
        col = col + (1.5 * gauss(np.hypot(c.X - x + s * 0.36, c.Y - y + s * 0.42), s * 0.20) * ins)[..., None]
        col = col + (0.30 * gauss(e - s * 0.92, s * 0.10) * clamp((-(c.X - x) * 0.5 - (c.Y - y) * 0.8) / s) * ins)[..., None]
    cov = c.cover(d)
    # meniscus: water pulled up along the edge
    men = gauss(d - 0.012, 0.018) * (1 - cov)
    c.put(rgb('#D6F5EA'), clamp(men * (0.16 + 0.24 * clamp(-(c.X * 0.5 + c.Y * 0.8)))).astype(F))
    c.put(col, cov, H)
    return c, cov


def small(im, name, quality=84, levels=24):
    """Colour JPEG plus a mask of few steps, which packs far better."""
    a = np.asarray(im.getchannel('A'), F) / 255
    im.putalpha(Image.fromarray((np.round(a * levels) / levels * 255 + 0.5).astype(np.uint8), 'L'))
    P.save(im, name, quality=quality, how='jpg')


def sheet(cells, cols):
    """Frames side by side as one RGBA picture."""
    w, h = cells[0].size
    rows = (len(cells) + cols - 1) // cols
    s = Image.new('RGBA', (w * cols, h * rows), (0, 0, 0, 0))
    for i, im in enumerate(cells):
        s.paste(im, ((i % cols) * w, (i // cols) * h))
    return s


def pads():
    """Eight lily pads and their soft shadows."""
    out, dark = [], []
    for i, (seed, notch, gap) in enumerate(((101, 2.10, 11), (123, 3.75, 15), (145, 1.30, 8), (167, 2.85, 18), (189, 4.35, 10), (211, 1.75, 14), (233, 3.20, 7), (255, 2.45, 20))):
        c, cov = leaf(P.px(216), seed, notch, gap)
        out.append(c.image(exposure=1.0))
        s = Canvas(P.px(108), 1, 1.14)
        m = np.asarray(Image.fromarray(cov, 'F').resize((s.w, s.h), Image.BOX), F)
        s.alpha = (blur(m, 0.085 / s.px) * 0.9).astype(F)
        s.col[:] = rgb('#01161C')
        dark.append(s.image(tone=False, dither=False))
    small(sheet(out, 4), 'pad', 84)
    P.save(sheet(dark, 4), 'padshade', how='png')


def stones():
    edge('edge', 0.835, 29, 3)


def stones2():
    edge('edge2', 0.885, 42, 4, 1120)


def petal(c, ang, length, width, up, tone, seed, x0=0.0, y0=0.0, base=0.0, shadow=0.38, reach=0.10):
    """One petal from (x0, y0) outward. up: how steeply it stands, 0 flat to 1 upright."""
    r = rng(seed)
    X, Y = c.X - x0, c.Y - y0
    s, k = math.sin(ang), -math.cos(ang)
    u = (X * s + Y * k) / length
    v = -X * k + Y * s
    v = v - 0.05 * r.uniform(-1, 1) * length * u * u
    t = clamp((u - 0.52) / 0.48)
    w = width * np.where(u < 0.52, 0.30 + 0.70 * np.sin(clamp(u / 0.52) * math.pi / 2), 1 - t ** 1.75) * (1 + 0.03 * np.sin(u * 17 + r.random() * 6))
    d = np.where(u < base, 1.0, np.where(u > 1.02, (u - 1.02) * length + 0.02, (np.abs(v) - w) * 0.88))
    cov = c.cover(d)
    e = v / np.maximum(w, 0.02)
    cup = 0.50 + 0.9 * up
    gu = (0.55 * up + 0.9 * (u - 0.55) * (1 - up)) * 0.9     # slope along the petal: rises, then bends down
    gv = cup * e * 0.75 + 0.10 * np.sign(e) * gauss(e, 0.10)
    gx, gy = gu * s + gv * -k, gu * k + gv * s
    inv = 1 / np.sqrt(gx * gx + gy * gy + 1)
    nx, ny, nz = -gx * inv, -gy * inv, inv
    lit = clamp(nx * -0.46 + ny * -0.70 + nz * 0.60 + 0.10)
    sky = 0.5 - 0.5 * ny
    white_, pink, deep, cream = [rgb(q) for q in tone]
    uu = clamp(u)
    col = mix(np.broadcast_to(cream, c.shape + (3,)), np.broadcast_to(white_, c.shape + (3,)), smooth(0.02, 0.34, uu)[..., None])
    col = mix(col, pink, (0.85 * smooth(0.30, 0.95, uu + 0.12 * np.abs(e)))[..., None])
    col = mix(col, deep, (0.75 * smooth(0.70, 1.02, uu + 0.10 * e * e))[..., None])
    vein = 0.5 + 0.5 * np.cos(e * 15 * (1 - 0.35 * uu) + 0.6 * np.sin(u * 5))
    col = col * (1 - 0.12 * (vein ** 3) * smooth(0.1, 0.7, uu))[..., None]
    col = col * (1 - 0.16 * gauss(e, 0.07) * smooth(0.0, 0.3, uu) * (1 - uu))[..., None]
    f = 0.27 + 1.06 * lit + 0.16 * sky
    out = col * f[..., None] * V([1.0, 0.985, 0.96])
    out = out + (0.16 * np.power(lit, 10))[..., None]
    out = out + col * (0.18 * smooth(0.75, 1.0, np.abs(e)) * clamp(0.5 - e * 0.5 * (s * 0.7 + k * -0.46)))[..., None]
    if shadow > 0:
        sh = shift(cov, int(0.22 * reach / c.px), int(0.34 * reach / c.px))
        sh = blur(sh, 0.34 * reach / c.px) * shadow
        c.col = c.col * (1 - sh * (c.alpha > 0.02))[..., None]
    c.put(out, cov)


PINK = ('#FFF6F2', '#F7B6CB', '#D9568C', '#FFF3CF')
WHITE = ('#FFFDF6', '#F6EEE4', '#E9C9CF', '#FFF0C0')


def lotus(c, t, tone=PINK, seed=1, size=1.0, heart=True, whorls=((9, 1.00, 0.250, 0.0), (9, 0.82, 0.228, 0.5), (8, 0.62, 0.190, 0.2)), x0=0.0, y0=0.0, rot=0.0):
    """A water lily from above, t: 0 closed to 1 open."""
    r = rng(seed)
    for k, (n, ln, wd, ph) in enumerate(whorls):
        b = clamp(t * 1.45 - 0.16 * k, 0.0, 1.0)
        b = b * b * (3 - 2 * b)
        q = 0.30 + 0.70 * b
        order = list(range(n))
        for i in order[::2] + order[1::2]:
            a = rot + (i + ph) / n * TAU + r.uniform(-0.07, 0.07)
            j = r.uniform(0.94, 1.05)
            petal(c, a, size * ln * q * j, size * wd * (0.55 + 0.45 * b), 0.85 - 0.62 * b + 0.10 * k, tone, seed * 100 + k * 20 + i, x0, y0, shadow=0.46 + 0.06 * k, reach=0.11 * size)
    if heart:
        z = size * (0.25 + 0.75 * clamp(t * 1.4))
        n = 30
        for ring_, r0, r1 in ((0, 0.10, 0.275), (1, 0.06, 0.215)):
            for i in range(n):
                a = (i + 0.5 * ring_ + r.uniform(-0.25, 0.25)) / n * TAU
                ln = r1 * r.uniform(0.86, 1.06) * z
                x1, y1 = x0 + math.sin(a) * ln, y0 - math.cos(a) * ln
                d = c.taper(x0 + math.sin(a) * r0 * z, y0 - math.cos(a) * r0 * z, 0.010 * z, x1, y1, 0.012 * z)
                tip = np.hypot(c.X - x1, c.Y - y1) - 0.022 * z
                sh = c.cover(np.hypot(c.X - x1 - 0.02 * z, c.Y - y1 - 0.03 * z) - 0.03 * z, 4)
                c.col = c.col * (1 - 0.22 * sh)[..., None]
                c.put(rgb('#F2B93A') * r.uniform(0.75, 1.1), c.cover(d))
                c.put(rgb('#FFE27A') * r.uniform(0.8, 1.15), c.cover(tip))
        pod = np.hypot(c.X - x0, c.Y - y0) / (0.120 * z)
        lit = clamp(0.75 - 0.35 * ((c.X - x0) * 0.5 + (c.Y - y0) * 0.75) / (0.12 * z))
        c.put((rgb('#C9C24A') * lit[..., None]), c.cover((pod - 1) * 0.12 * z))
        for i in range(7):
            a, q = i * TAU / 6, 0.0 if i == 6 else 0.072 * z
            c.put(rgb('#7C7A22'), c.cover(np.hypot(c.X - x0 - math.sin(a) * q, c.Y - y0 + math.cos(a) * q) - 0.016 * z))


def flowers():
    """The lotus that opens behind a chosen icon, the open flower and the bud of running programs."""
    out = []
    for i in range(12):
        c = Canvas(P.px(208), P.ss(3), 1.06)
        lotus(c, i / 11, seed=4, heart=False)
        # the middle is a glow of yellow light; the icon lies on it
        g = gauss(c.R, 0.34 * (0.4 + 0.6 * i / 11))
        c.col = mix(c.col, rgb('#FFF2C4'), (0.50 * g * (c.alpha > 0))[..., None])
        out.append(c.image(tone=False))
    small(sheet(out, 4), 'lotus', 84)
    c = Canvas(P.px(96), 4, 1.08)
    lotus(c, 1.0, seed=9, whorls=((7, 1.00, 0.34, 0.0), (7, 0.76, 0.30, 0.5)))
    P.save(c.image(tone=False), 'bloom', how='png')
    c = Canvas(P.px(64), 4, 1.0)
    for a in (-0.95, 0.95, 0.0):
        petal(c, a * 0.85, 1.20, 0.34, 0.7, ('#A9C06A', '#7C9A44', '#4C6B2A', '#C2CF86'), 50 + int(a * 10), 0.0, 0.80, shadow=0.3)
    for a, l in ((-0.42, 1.50), (0.42, 1.50), (-0.18, 1.62), (0.20, 1.60), (0.0, 1.66)):
        petal(c, a, l, 0.40, 0.8, PINK, 130 + int(a * 100), 0.0, 0.78, shadow=0.50, reach=0.2)
    P.save(c.image(tone=False), 'bud', how='png')


class Swim:
    """A fish seen from above, bent by the wave that runs down its body. Head up; s runs 0 at the nose to 1 at the tail."""
    LEN = 1.84

    def __init__(self, size, phase, ss=3):
        c = self.c = Canvas(size, ss, 0.5, aspect=2.0)
        n = 190
        s = np.linspace(0, 1, n)
        amp = 0.016 + 0.015 * s + 0.135 * s * s
        x = amp * np.sin(TAU * 0.86 * s - phase) + 0.010 * np.sin(-phase + 0.6) * (1 - s)
        dx = np.gradient(x, s)
        dy = np.sqrt(np.maximum(self.LEN ** 2 - dx * dx, 0.5))
        y = np.concatenate([[0], np.cumsum((dy[1:] + dy[:-1]) / 2 * np.diff(s))]) - 0.915
        self.tx, self.ty = dx / np.hypot(dx, dy), dy / np.hypot(dx, dy)
        self.px, self.py = x, y
        best = np.full(c.shape, 9.0, F)
        idx = np.zeros(c.shape, np.int32)
        for i in range(n):
            d = (c.X - float(x[i])) ** 2 + (c.Y - float(y[i])) ** 2
            m = d < best
            best = np.where(m, d, best)
            idx = np.where(m, i, idx)
        qx, qy = c.X - x[idx].astype(F), c.Y - y[idx].astype(F)
        tx, ty = self.tx[idx].astype(F), self.ty[idx].astype(F)
        self.s = (idx / (n - 1) + (qx * tx + qy * ty) / self.LEN).astype(F)
        self.d = (qx * ty - qy * tx).astype(F)          # to the fish's right is negative
        self.phase = phase

    def at(self, s):
        i = int(round(s * (len(self.px) - 1)))
        return float(self.px[i]), float(self.py[i]), float(self.tx[i]), float(self.ty[i])


BODY = ([0, 0.006, 0.015, 0.03, 0.055, 0.09, 0.13, 0.18, 0.24, 0.31, 0.40, 0.50, 0.60, 0.70, 0.78, 0.84, 1.0],
        [0, 0.055, 0.084, 0.112, 0.138, 0.160, 0.176, 0.188, 0.196, 0.197, 0.186, 0.162, 0.128, 0.088, 0.060, 0.048, 0.040])


def blob(s, v, at, n):
    """Patches with soft, ragged edges, in body coordinates."""
    m = np.zeros(s.shape, F)
    for s0, v0, rs, rv in at:
        d = np.hypot((s - s0) / rs, (v - v0) / rv) + 0.55 * n
        m = np.maximum(m, smooth(1.08, 0.94, d))
    return m


def fin(f, where, side, alpha_, ang, length, width, spread=0.62):
    """A fan of rays at a place on the body; returns coverage and a ray pattern."""
    c = f.c
    w = float(np.interp(where, *BODY))
    x, y, tx, ty = f.at(where)
    nx, ny = ty, -tx                              # to the side
    ax, ay = x + nx * side * w * 0.86, y + ny * side * w * 0.86
    ca, sa = math.cos(ang), math.sin(ang)
    dx, dy = tx * ca + nx * side * sa, ty * ca + ny * side * sa
    qx, qy = c.X - ax, c.Y - ay
    u = (qx * dx + qy * dy) / length
    v = (-qx * dy + qy * dx) / width * side
    v = v + 0.22 * u * u
    t = clamp((u - spread) / (1 - spread))
    prof = np.where(u < spread, 0.26 + 0.74 * np.sin(clamp(u / spread) * math.pi / 2) ** 0.9, np.sqrt(clamp(1 - t * t)))
    d = np.where(u < -0.05, 1, np.where(u > 1, (u - 1) * length + 0.01, (np.abs(v) - prof) * width * 0.9))
    cov = c.cover(d, 1.5)
    rays = 0.5 + 0.5 * np.cos(v / np.maximum(0.25 + 0.75 * clamp(u / spread), 0.2) * 13)
    return cov * alpha_, rays, clamp(u)


def koi(kind, fr, frames, size):
    f = frames[fr]
    c = Canvas(size, f.c.ss, 0.5, aspect=2.0)
    s, d = f.s, f.d
    w = np.interp(s, *BODY).astype(F)
    v = d / np.maximum(w, 0.004)
    tex = kind['tex']
    h, wd = tex.shape
    ti = (clamp(s) * (wd - 2)).astype(int), (clamp(v * 0.5 + 0.5) * (h - 2)).astype(int)
    n = tex[ti[1], ti[0]]
    n2 = kind['tex2'][ti[1], ti[0]]
    base, red, black, finc = kind['base'], kind['red'], kind['black'], kind['fin']
    ph = f.phase
    # fins first; they are half clear
    flap = 0.16 * math.sin(ph + 0.9)
    parts = []
    for side in (-1, 1):
        parts.append(fin(f, 0.235, side, 0.86, 1.02 + flap * side * 0.6 + 0.10 * math.sin(2 * ph), 0.285, 0.118) + (kind['fintip'],))
        parts.append(fin(f, 0.50, side, 0.80, 0.62 - flap * side * 0.4, 0.165, 0.062) + (kind['fintip'],))
    for cov, rays, u, tip in parts:
        col = mix(np.broadcast_to(rgb(kind['finbase']), c.shape + (3,)), np.broadcast_to(rgb(finc), c.shape + (3,)), smooth(0.05, 0.45, u)[..., None])
        col = mix(col, rgb(tip), (0.6 * smooth(0.6, 1.0, u))[..., None])
        col = col * (0.72 + 0.28 * rays)[..., None]
        c.put(col, cov * (0.60 + 0.25 * rays))
    # tail fin
    ts = clamp((s - 0.80) / 0.20)
    half = 0.044 + 0.185 * ts ** 0.85
    end = 0.915 + 0.085 * clamp(np.abs(d) / 0.19) ** 0.75
    dt = np.maximum((np.abs(d) - half) * 0.9, (s - end) * f.LEN * 0.85)
    dt = np.where(s < 0.79, 1.0, dt)
    cov = c.cover(dt, 1.5)
    rays = 0.5 + 0.5 * np.cos(d / np.maximum(0.05 + 0.185 * ts, 0.04) * 15)
    col = mix(np.broadcast_to(rgb(kind['finbase']), c.shape + (3,)), np.broadcast_to(rgb(finc), c.shape + (3,)), smooth(0.05, 0.40, ts)[..., None]) * (0.70 + 0.30 * rays)[..., None]
    col = mix(col, rgb(kind['fintip']), (0.6 * smooth(0.55, 1.0, ts))[..., None])
    c.put(col, cov * (0.92 - 0.30 * ts + 0.14 * rays) * 0.92)
    # body
    body = np.where(s > 0.90, 1.0, np.where(s < 0, np.hypot(d, s * f.LEN) - 0.001, np.abs(d) - w * smooth(0.90, 0.84, s)))
    cov = c.cover(body * 0.95, 1.2)
    alb = np.broadcast_to(rgb(base), c.shape + (3,)) * (1 + 0.06 * n2)[..., None]
    if kind['redat']:
        m = blob(s, v, kind['redat'], n)
        alb = mix(alb, rgb(red) * (1 + 0.10 * n2)[..., None], m[..., None])
    if kind['blackat']:
        m = blob(s, v, kind['blackat'], n2)
        alb = mix(alb, rgb(black), (0.96 * m)[..., None])
    # scales
    a = np.arcsin(clamp(v, -1, 1)) / (math.pi / 2) * 5.0
    u = s * 40
    net = np.abs(np.cos(math.pi * (u + a) / 2) * np.cos(math.pi * (u - a) / 2))
    scale = smooth(0.0, 0.30, net)
    zone = smooth(0.20, 0.25, s) * smooth(0.83, 0.76, s)
    alb = alb * (1 - kind['net'] * (1 - scale) * zone)[..., None]
    nz = np.sqrt(clamp(1 - 0.94 * v * v))
    sh = 0.30 + 0.78 * nz ** 0.9
    out = alb * sh[..., None]
    out = out + (0.16 * gauss(v, 0.24) * (0.55 + 0.45 * scale * zone + 0.45 * (1 - zone)) * smooth(0.0, 0.10, s) * smooth(0.86, 0.6, s))[..., None] * rgb('#EAF6FF')
    if kind.get('metal'):
        out = out + alb * (0.55 * gauss(v, 0.30) * (0.5 + 0.5 * scale))[..., None]
    # gill covers, nostrils, mouth
    gill = gauss(s - 0.178 - 0.018 * v * v + 0.02 * (1 - np.abs(v)), 0.006) * smooth(0.25, 0.5, np.abs(v))
    out = out * (1 - 0.40 * gill)[..., None]
    out = out * (1 - 0.30 * gauss(np.hypot((s - 0.045) * 1.84, np.abs(d) - 0.040), 0.013))[..., None]
    c.put(out, cov)
    # dorsal fin: a narrow sail along the back, leaning with the wave
    lean = 0.020 * math.sin(ph + 2.2)
    dz = smooth(0.34, 0.40, s) * smooth(0.64, 0.52, s)
    strip = np.abs(d - lean * dz) - 0.017 * dz
    sc = c.cover(np.where(dz > 0.02, strip, 1.0), 1.2)
    c.put(mix(np.broadcast_to(rgb(finc), c.shape + (3,)), rgb(kind['finbase']), (0.45 * (0.5 + 0.5 * np.cos(s * 190)))[..., None]), sc * 0.75)
    c.col = c.col * (1 - 0.35 * gauss(d - lean * dz - 0.024, 0.010) * dz)[..., None]
    # eyes
    for side in (-1, 1):
        x, y, tx, ty = f.at(0.085)
        ex, ey = x + ty * side * 0.128, y - tx * side * 0.128
        e = np.hypot(c.X - ex, c.Y - ey)
        c.put(rgb('#0B0B10'), c.cover(e - 0.022))
        c.put(rgb('#FFFFFF'), c.cover(np.hypot(c.X - ex + 0.007, c.Y - ey + 0.008) - 0.006) * 0.9)
        # barbels
        x, y, tx, ty = f.at(0.012)
        ax, ay = x + ty * side * 0.055, y - tx * side * 0.055
        bx, by = ax + ty * side * 0.055 - tx * 0.030, ay - tx * side * 0.055 - ty * 0.030
        c.put(rgb(base), c.cover(c.taper(ax, ay, 0.010, bx, by, 0.003)) * 0.8)
    return c


def fish():
    """Four koi, each a cycle of twelve frames, and one soft shadow for all."""
    size = P.px(104)
    frames = [Swim(size, k * TAU / 12) for k in range(12)]
    sh = (96, 256)
    kinds = {
        'koi1': dict(base='#F7F1E4', red='#E4521B', black='#15151B', fin='#F5F1EA', finbase='#F0D9C6', fintip='#FFFFFF', net=0.10,
                     redat=[(0.115, 0.0, 0.062, 0.62), (0.335, 0.1, 0.095, 0.95), (0.53, -0.15, 0.060, 0.85), (0.71, 0.1, 0.050, 0.9)], blackat=[]),
        'koi2': dict(base='#F4EFE6', red='#DD431A', black='#14141A', fin='#F2EEE8', finbase='#C9C4C0', fintip='#FFFFFF', net=0.12,
                     redat=[(0.27, -0.35, 0.10, 0.60), (0.48, 0.3, 0.08, 0.65), (0.66, -0.1, 0.05, 0.8), (0.10, 0.0, 0.045, 0.45)],
                     blackat=[(0.335, 0.55, 0.045, 0.36), (0.43, -0.55, 0.035, 0.32), (0.575, 0.2, 0.034, 0.30), (0.62, -0.5, 0.03, 0.4), (0.76, 0.2, 0.03, 0.5)]),
        'koi3': dict(base='#E7A21C', red='#F2B93A', black='#14141A', fin='#F3C65A', finbase='#D98F18', fintip='#FFE9A8', net=0.26, redat=[(0.10, 0, 0.10, 1.2)], blackat=[], metal=True),
        'koi4': dict(base='#1B1C24', red='#E25A1E', black='#F2ECE0', fin='#3A3C48', finbase='#16171E', fintip='#E9E6E0', net=0.30,
                     redat=[(0.125, 0.0, 0.055, 0.55), (0.40, 0.45, 0.085, 0.55), (0.63, -0.35, 0.060, 0.6)], blackat=[(0.29, -0.55, 0.055, 0.50), (0.52, 0.55, 0.040, 0.45), (0.76, 0.1, 0.030, 0.7)]),
    }
    for k, (name, kd) in enumerate(kinds.items()):
        if P.only and name not in P.only and 'fish' not in P.only:
            continue
        kd['tex'], kd['tex2'] = fbm(sh, 22, 60 + k, 3), fbm(sh, 34, 80 + k, 3)
        cells = [koi(kd, i, frames, size) for i in range(12)]
        small(sheet([c.image(tone=False, exposure=0.98) for c in cells], 6), name, 80)
        if k:                                    # all four have the same outline
            os.remove(os.path.join(P.dir, name + '-mask.png'))
        else:
            dark = []
            for c in cells:
                m = np.asarray(Image.fromarray(c.alpha.astype(F), 'F').resize((size // 2, size), Image.BOX), F)
                q = Canvas(size // 2, 1, 0.5, aspect=2.0)
                q.alpha = (clamp(blur(m, 2.2 * P.draft)) * 0.95).astype(F)
                q.col[:] = rgb('#01161C')
                dark.append(q.image(tone=False, dither=False))
            P.save(sheet(dark, 6), 'koishade', how='png')


def island():
    """The smooth dark stone in the middle: worn by water, wet at its foot, moss on one shoulder."""
    c = Canvas(P.px(470), 2, 1.14)
    n1, n2, n3 = fbm(c.shape, 4, 301, 4), fbm(c.shape, 16, 302, 5), fbm(c.shape, 60, 303, 3)
    rad = 0.955 + 0.007 * np.cos(2 * c.A + 0.7) + 0.004 * np.cos(3 * c.A + 2.0) + 0.003 * np.cos(5 * c.A + 1.0) + 0.004 * n1
    d = c.R - rad
    t = clamp(-d / 0.955)
    H = 0.20 * (1 - (1 - clamp(t / 0.42)) ** 2.3) ** 0.60 + 0.045 * np.sqrt(clamp(1 - (c.R / 0.95) ** 2))
    H = H + 0.0040 * n2 + 0.0011 * n3 * smooth(0, 0.1, t)
    # a shallow worn groove near the edge, as on a mill stone
    H = H - 0.008 * gauss(c.R - 0.845, 0.010)
    alb = mix(np.broadcast_to(rgb('#33393E'), c.shape + (3,)), np.broadcast_to(rgb('#545B5E'), c.shape + (3,)), clamp(0.45 + 0.35 * n1 + 0.25 * n2)[..., None])
    alb = alb * (1 + 0.16 * n3)[..., None]
    alb = mix(alb, rgb('#1E2428'), (0.55 * smooth(0.62, 0.15, c.R + 0.05 * n1))[..., None])
    speck = smooth(0.12, 0.06, worley(c.X, c.Y, 30, 304)) * (fbm(c.shape, 9, 305, 2) > 0.15)
    alb = mix(alb, rgb('#A7AFAF'), (0.30 * speck)[..., None])
    for q, o, w in ((0.9, 0.62, 0.012), (1.02, 0.70, 0.005), (2.6, -0.74, 0.008)):
        e = np.abs(c.X * math.cos(q) + c.Y * math.sin(q) - o + 0.06 * n1 + 0.015 * n2)
        alb = mix(alb, rgb('#C9CCC4'), (0.62 * smooth(w * 1.6, w * 0.3, e) * smooth(-0.4, 0.5, n2 + 0.25))[..., None])
    wet = smooth(0.89, 0.945, c.R + 0.010 * n2)
    alb = alb * (1 - 0.35 * wet)[..., None]
    nx, ny, nz = normals(H, c.px)
    ao = occlusion(H, c.px, (0.02, 0.06), 0.7)
    col = shade(SUN, nx, ny, nz, alb, metal=0, rough=0.45, spec=0.045, ao=ao, clear=0.10)
    gl = shade(SUN, nx, ny, nz, alb, metal=0, rough=0.22, spec=0.05, ao=ao, clear=0.65)
    col = mix(col, gl, wet[..., None])
    # moss on the lower left shoulder and a little at the top right
    side = smooth(0.35, 1.0, (c.X * -0.62 + c.Y * 0.78)) * smooth(0.60, 0.92, c.R) + 0.55 * smooth(0.72, 1.0, (c.X * 0.80 - c.Y * 0.60)) * smooth(0.80, 0.95, c.R)
    patch = fbm(c.shape, 8, 310, 4)
    moss = smooth(0.30, 0.75, side + 0.35 * patch) * (d < -0.004)
    d1 = worley(c.X + 0.01 * n2, c.Y + 0.01 * n1, 36, 311)
    cush = (1 - clamp(d1) ** 2) * 0.6 + 0.30 * n3
    Hm = H + 0.030 * moss * (0.5 + cush) + 0.004 * white(c.shape, 5) * moss
    mx, my, mz = normals(blur(Hm, 0.6 * c.ss), c.px)
    mcol = mix(np.broadcast_to(rgb('#2A4218'), c.shape + (3,)), np.broadcast_to(rgb('#7C9440'), c.shape + (3,)), clamp(0.35 + 0.45 * cush + 0.2 * n2)[..., None])
    mshade = shade(SUN, mx, my, mz, mcol, metal=0, rough=0.9, spec=0.01, ao=occlusion(Hm, c.px, (0.01, 0.03), 1.0))
    col = mix(col, mshade, moss[..., None])
    cov = c.cover(d)
    # what it does to the water around it: shadow, reflection, a bright waterline
    sh = np.maximum(blur(shift(cov, int(0.035 / c.px), int(0.055 / c.px)), 0.030 / c.px) * 0.75, blur(shift(cov, int(0.07 / c.px), int(0.10 / c.px)), 0.055 / c.px) * 0.55)
    c.put(rgb('#011418'), (sh * smooth(1.14, 1.08, c.R)).astype(F))
    near = blur(cov, 0.016 / c.px)
    c.put(rgb('#D6F5EA'), (smooth(0.06, 0.32, near) * (1 - cov) * 0.36 * clamp(0.6 + 0.7 * n2)).astype(F))
    c.put(col, cov, H)
    small(c.image(exposure=1.0), 'island', 86)


def bits():
    """Ripples, petals, drops, glows."""
    c = Canvas(P.px(220), 2, 1.0)
    prof = np.zeros(c.shape, F)
    slope = np.zeros(c.shape, F)
    for r0, w, a in ((0.90, 0.040, 1.0), (0.74, 0.050, 0.62), (0.56, 0.055, 0.34)):
        prof += a * gauss(c.R - r0, w)
        slope += a * -(c.R - r0) / w * gauss(c.R - r0, w) * 2.3
    nxr, nyr = c.X / np.maximum(c.R, 1e-3), c.Y / np.maximum(c.R, 1e-3)
    lit = slope * (nxr * -0.55 + nyr * -0.83)
    lit = lit + 0.30 * prof
    c.col = np.where(lit[..., None] > 0, rgb('#E9FFF6'), rgb('#02222A')).astype(F)
    c.alpha = (clamp(np.abs(lit)) * 0.80 * smooth(1.0, 0.95, c.R)).astype(F)
    small(c.image(tone=False), 'ripple', 84)
    cells = []
    for i in range(4):
        c = Canvas(P.px(52), 4, 1.0)
        petal(c, 0.0, 1.62, (0.42, 0.50, 0.36, 0.46)[i], 0.30, PINK, 700 + i, 0.0, 0.82, shadow=0)
        cells.append(c.image(tone=False))
    P.save(sheet(cells, 4), 'petal', how='png')
    c = Canvas(P.px(40), 4, 1.0)
    e = c.R / 0.86
    body = clamp(0.35 + 0.65 * (c.X * 0.5 + c.Y * 0.8))
    c.col = (mix(np.broadcast_to(rgb('#5FB7B4'), c.shape + (3,)), np.broadcast_to(rgb('#F2FFFB'), c.shape + (3,)), body[..., None])).astype(F)
    c.alpha = (smooth(1.0, 0.92, e) * (0.40 + 0.45 * smooth(0.5, 1.0, e))).astype(F)
    hl = gauss(np.hypot(c.X + 0.34, c.Y + 0.40), 0.20)
    c.put(rgb('#FFFFFF'), (hl * (e < 1)).astype(F))
    P.save(c.image(tone=False), 'drop', how='png')
    c = Canvas(P.px(128), 1, 1.0)
    c.col[:] = rgb('#FFF6C8')
    c.alpha = ((gauss(c.R, 0.20) * 0.95 + gauss(c.R, 0.42) * 0.40) * smooth(1.0, 0.75, c.R)).astype(F)
    P.save(c.image(tone=False), 'glow', how='png')


def steps():
    """Stepping stones for the members of a group."""
    cells = []
    for i in range(6):
        c = Canvas(P.px(176), 3, 1.18)
        S = Rocks(c, 400 + i, ['#8D8A82', '#7B8083', '#97907F', '#6F7375', '#8A8073', '#A09A8C'])
        r = rng(420 + i)
        S.add(0, 0, 0.97, r.uniform(0.88, 0.95), r.random() * TAU, h=0.17, facets=0, wob=0.035, rough=0.030, flat=5.0, p=2.25, vary=0.12)
        H = S.H
        alb = S.alb * (0.66 + 0.34 * smooth(0.25, 0.85, c.R))[..., None]     # worn and damp in the middle, where the icon lies
        m = smooth(0.45, 0.85, fbm(c.shape, 5, 440 + i, 4) + smooth(0.62, 0.98, c.R)) * S.cov
        n = fbm(c.shape, 40, 450 + i, 3)
        gcol = mix(np.broadcast_to(rgb('#33501B'), c.shape + (3,)), np.broadcast_to(rgb('#869E3C'), c.shape + (3,)), clamp(0.45 + 0.5 * n)[..., None])
        alb = mix(alb, gcol, (0.80 * m)[..., None])
        H = H + 0.016 * m * (0.6 + 0.6 * n)
        nx, ny, nz = normals(H, c.px)
        col = shade(SUN, nx, ny, nz, alb, metal=0, rough=0.7, spec=0.035, ao=occlusion(H, c.px, (0.03, 0.09), 0.8), sh=cast(H, c.px, LIGHT_DIR, slope=0.6, reach=0.3))
        cov = blur(S.cov, 0.7 * c.ss)
        sh = np.maximum(blur(shift(cov, int(0.05 / c.px), int(0.08 / c.px)), 0.05 / c.px) * 0.7, blur(cov, 0.05 / c.px) * 0.6)
        c.put(rgb('#030803'), (sh * smooth(1.18, 1.08, c.R)).astype(F))
        c.put(col, cov, H)
        cells.append(c.image(exposure=1.0))
    small(sheet(cells, 3), 'step', 84)


def pole(c, x0, y0, x1, y1, r, seed, nodes=(), tone=('#8C7636', '#C9B36B')):
    """A bamboo cane between two points: distance, height, colour."""
    L = math.hypot(x1 - x0, y1 - y0)
    tx, ty = (x1 - x0) / L, (y1 - y0) / L
    u = (c.X - x0) * tx + (c.Y - y0) * ty
    v = -(c.X - x0) * ty + (c.Y - y0) * tx
    rr = np.full(c.shape, r, F)
    for k in nodes:
        rr = rr + r * 0.11 * gauss(u - k, r * 0.16) - r * 0.05 * gauss(u - k - r * 0.34, r * 0.16)
    d = np.maximum(np.abs(v) - rr, np.maximum(-u, u - L))
    H = np.sqrt(np.maximum(rr * rr - v * v, 0))
    g = rng(seed)
    prof = np.interp(v.ravel(), np.linspace(-r * 1.3, r * 1.3, 60), blur1(g.standard_normal((1, 60)).astype(F), 0.8, 1)[0]).reshape(c.shape).astype(F)
    n = fbm(c.shape, 9, seed + 3, 4)
    alb = mix(np.broadcast_to(rgb(tone[0]), c.shape + (3,)), np.broadcast_to(rgb(tone[1]), c.shape + (3,)), clamp(0.52 + 0.20 * prof + 0.18 * n)[..., None])
    for k in nodes:
        alb = mix(alb, rgb('#5A4520'), (0.75 * gauss(u - k - r * 0.13, r * 0.075))[..., None])
        alb = mix(alb, rgb('#E6D9A0'), (0.45 * gauss(u - k + r * 0.16, r * 0.14))[..., None])
        alb = mix(alb, rgb('#6B5A26'), (0.35 * smooth(r * 1.3, 0, np.abs(u - k - r * 0.5)))[..., None])
    return d.astype(F), H.astype(F), alb.astype(F)


def panel():
    """A frame of bamboo canes lashed with cord, around dark water. Cut in nine by the program."""
    n = 320
    c = Canvas(P.px(n), 3, 1.0)
    unit = 2.0 / n                                 # one picture point
    m, r = 1 - 26 * unit, 11 * unit
    e = 1 - 8 * unit
    inner = c.box(m, m, r=4 * unit)
    n1 = fbm(c.shape, 3, 501, 3)
    sh = np.maximum(blur(c.cover(c.box(m + r * 0.9, m + r * 0.9, x=3 * unit, y=6 * unit, r=6 * unit)), 5 * unit / c.px) * 0.62, 0)
    c.put(rgb('#020807'), (sh * smooth(1.0, 1 - 7 * unit, np.maximum(np.abs(c.X), np.abs(c.Y)))).astype(F))
    t = clamp(0.5 + 0.5 * c.Y / m)
    water = mix(np.broadcast_to(rgb('#17626A'), c.shape + (3,)), np.broadcast_to(rgb('#07303B'), c.shape + (3,)), t[..., None])
    water = water * (1 + 0.16 * smooth(0.2, -0.9, c.X * 0.6 + c.Y * 0.8))[..., None]
    shade_in = blur(c.cover(np.maximum(np.abs(c.X) - m, np.abs(c.Y) - m) * -1 - r * 0.4), 9 * unit / c.px)
    water = water * (1 - 0.62 * np.maximum(shade_in, 0))[..., None]
    c.put(water, c.cover(inner))
    k = m - 34 * unit
    canes = [(-e, -m, e, -m, 61), (-e, m, e, m, 62), (-m, -e, -m, e, 63), (m, -e, m, e, 64)]
    for x0, y0, x1, y1, seed in canes:
        nodes = (e - k - 0 * unit, e + k) if True else ()
        d, H, alb = pole(c, x0, y0, x1, y1, r, seed, nodes)
        nx, ny, nz = normals(H, c.px)
        col = shade(SUN, nx, ny, nz, alb, metal=0, rough=0.38, spec=0.05, clear=0.22)
        cov = c.cover(d)
        s = blur(shift(cov, int(2.5 * unit / c.px), int(4.5 * unit / c.px)), 2.6 * unit / c.px) * 0.55
        c.col = c.col * (1 - s * (c.alpha > 0.3))[..., None]
        c.put(col, cov)
        # sawn ends
        for ex, ey in ((x0, y0), (x1, y1)):
            c.col = c.col * (1 - 0.45 * gauss(np.hypot((c.X - ex), (c.Y - ey)) - r * 0.2, r * 0.55) * cov)[..., None]
    # cord
    for sx in (-1, 1):
        for sy in (-1, 1):
            for q, o in ((1, -4.6), (1, 0), (1, 4.6), (-1, -4.6), (-1, 0), (-1, 4.6)):
                px, py = o * unit * q, -o * unit
                cx, cy = sx * m, sy * m
                a = 13.2 * unit
                x0, y0, x1, y1 = cx - a + px * 0.7, cy - q * a + py * 0.7, cx + a + px * 0.7, cy + q * a + py * 0.7
                d = c.capsule(x0, y0, x1, y1, 2.5 * unit)
                along = ((c.X - x0) * (x1 - x0) + (c.Y - y0) * (y1 - y0)) / math.hypot(x1 - x0, y1 - y0)
                tw = 0.5 + 0.5 * np.sin((along + d * 1.2) / unit * 2.0)
                H = np.sqrt(np.maximum((2.5 * unit) ** 2 - (d + 2.5 * unit) ** 2, 0)) + 0.25 * unit * tw
                nx, ny, nz = normals(H, c.px)
                col = shade(SUN, nx, ny, nz, mix(np.broadcast_to(rgb('#241A10'), c.shape + (3,)), np.broadcast_to(rgb('#6A5233'), c.shape + (3,)), tw[..., None]), metal=0, rough=0.8, spec=0.03)
                cov = c.cover(d)
                s = blur(shift(cov, int(1.2 * unit / c.px), int(2.0 * unit / c.px)), 1.2 * unit / c.px) * 0.55
                c.col = c.col * (1 - s)[..., None]
                c.put(col, cov)
    small(c.image(exposure=0.95), 'panel', 86)


def tag():
    """A tablet of wet slate for names."""
    w, h = 220, 120
    c = Canvas(P.px(w), 3, 1.0, aspect=h / w)
    unit = 2.0 / w
    n1, n2 = fbm(c.shape, 6, 520, 4), fbm(c.shape, 40, 521, 4)
    d = c.box(1 - 9 * unit, h / w - 9 * unit, r=20 * unit) + 0.9 * unit * n1
    H = bevel(d, 9 * unit, 7 * unit) + 0.35 * unit * n2
    alb = mix(np.broadcast_to(rgb('#2E3438'), c.shape + (3,)), np.broadcast_to(rgb('#454C50'), c.shape + (3,)), clamp(0.45 + 0.25 * n1 + 0.15 * n2)[..., None])
    nx, ny, nz = normals(H, c.px)
    col = shade(SUN, nx, ny, nz, alb, metal=0, rough=0.35, spec=0.05, clear=0.28)
    cov = c.cover(d)
    s = np.maximum(blur(shift(cov, int(1.5 * unit / c.px), int(4 * unit / c.px)), 3 * unit / c.px) * 0.7, blur(cov, 3 * unit / c.px) * 0.4)
    c.put(rgb('#010505'), s.astype(F))
    c.put(col, cov)
    small(c.image(exposure=0.95), 'tag', 86)


def dragonfly():
    """Points at what is chosen. Four frames of beating wings."""
    cells = []
    for i in range(4):
        c = Canvas(P.px(150), 4, 1.0)
        beat = (0.0, 0.10, 0.0, -0.12)[i]
        for side in (-1, 1):
            for k, (root, ang, ln, wd) in enumerate(((0.02, 1.80, 0.90, 0.135), (-0.11, 1.36, 0.93, 0.115))):
                a = side * (ang + beat * (1 if k else -0.8))
                ax, ay = side * 0.045, root
                s, q = math.sin(a), -math.cos(a)
                u = ((c.X - ax) * s + (c.Y - ay) * q) / ln
                v = (-(c.X - ax) * q + (c.Y - ay) * s) * side
                v = v + 0.10 * u * u * (0.5 if k else 1.0)
                w = wd * np.where(u < 0.62, 0.22 + 0.78 * np.sin(clamp(u / 0.62) * math.pi / 2), np.sqrt(clamp(1 - ((u - 0.62) / 0.38) ** 2)))
                d = np.where((u < 0) | (u > 1), np.maximum(-u, u - 1) * ln + 0.004, (np.abs(v) - w) * 0.9)
                cov = c.cover(d, 1.3)
                col = mix(np.broadcast_to(rgb('#DFF7F4'), c.shape + (3,)), np.broadcast_to(rgb('#9FD8E6'), c.shape + (3,)), smooth(0.1, 0.9, u)[..., None])
                vein = np.maximum(smooth(0.010, 0.003, np.abs(d + 0.006)), 0.75 * smooth(0.008, 0.002, np.abs(v + 0.25 * w)))
                cell = smooth(0.10, 0.03, np.abs((u * 24 + v * 30) % 1.0 - 0.5) * 0.4) * 0.30 + smooth(0.10, 0.03, np.abs((u * 24 - v * 30) % 1.0 - 0.5) * 0.4) * 0.30
                ink = clamp(vein + cell * smooth(0.05, 0.2, u))
                a_ = 0.42 + 0.40 * ink + 0.25 * gauss(v - w * 0.3, w * 0.25 + 1e-3)
                col = mix(col, rgb('#23515C'), (0.75 * ink)[..., None])
                spot = gauss(u - 0.86, 0.045) * smooth(0.0, 0.4, v / np.maximum(w, 1e-3) + 0.1)
                col = mix(col, rgb('#3A1F12'), clamp(spot)[..., None])
                c.put(col, cov * clamp(a_ + spot * 0.6))
        # body
        pts = [(-0.02, 0.10, 0.060), (0.0, 0.30, 0.048), (0.012, 0.52, 0.042), (0.010, 0.74, 0.044), (0.0, 0.90, 0.030)]
        for j in range(len(pts) - 1):
            x0, y0, r0 = pts[j]
            x1, y1, r1 = pts[j + 1]
            d = c.taper(x0, y0, r0, x1, y1, r1)
            nzv = clamp(-d / 0.045)
            seg = 0.5 + 0.5 * np.cos(c.Y * 62)
            col = mix(np.broadcast_to(rgb('#0E6E86'), c.shape + (3,)), np.broadcast_to(rgb('#52D8E0'), c.shape + (3,)), clamp(nzv * 0.9 - 0.25 * (c.X > 0))[..., None])
            col = mix(col, rgb('#07202A'), (0.75 * smooth(0.80, 0.97, seg))[..., None])
            c.put(col, c.cover(d))
        for x, y, r, dk, lt in ((0, -0.03, 0.120, '#0B5A6E', '#46C7CF'), (0, -0.16, 0.100, '#0F6476', '#5BDCE2')):
            e = np.hypot(c.X - x, (c.Y - y) * 0.85)
            li = clamp(1.05 - np.hypot(c.X - x + r * 0.35, c.Y - y + r * 0.4) / r)
            c.put(mix(np.broadcast_to(rgb(dk), c.shape + (3,)), np.broadcast_to(rgb(lt), c.shape + (3,)), li[..., None]), c.cover(e - r))
        for x in (-0.072, 0.072):
            e = np.hypot(c.X - x, c.Y + 0.275)
            li = clamp(1.1 - np.hypot(c.X - x + 0.03, c.Y + 0.305) / 0.085)
            c.put(mix(np.broadcast_to(rgb('#3A1410'), c.shape + (3,)), np.broadcast_to(rgb('#E2683A'), c.shape + (3,)), li[..., None]), c.cover(e - 0.083))
            c.put(rgb('#FFE9D0'), c.cover(np.hypot(c.X - x + 0.028, c.Y + 0.305) - 0.017) * 0.9)
        cells.append(c.image(tone=False))
    small(sheet(cells, 4), 'dragonfly', 86)


def maple_leaf(c, x, y, ang, size, tone, seed, noise, fold=0.22):
    """A Japanese maple leaf; (x, y) is where the stalk meets it. Returns its part of the canvas, colour and coverage."""
    r = rng(seed)
    p = Part(c, x, y, size * 1.15)
    X, Y = p.X - x, p.Y - y
    d = np.full(p.shape, 9.0, F)
    lit, veins = np.zeros(p.shape, F), np.zeros(p.shape, F)
    near = np.full(p.shape, 9.0, F)
    for a, ln, wd in ((0.0, 1.0, 0.150), (-0.62, 0.90, 0.140), (0.62, 0.90, 0.140), (-1.24, 0.66, 0.115), (1.24, 0.66, 0.115), (-1.95, 0.36, 0.075), (1.95, 0.36, 0.075)):
        a = ang + a + r.uniform(-0.06, 0.06)
        ln = size * ln * r.uniform(0.94, 1.05)
        s, k = math.sin(a), -math.cos(a)
        u = (X * s + Y * k) / ln
        v = -X * k + Y * s
        v = v - 0.06 * size * r.uniform(-1, 1) * u * u
        t = clamp((u - 0.42) / 0.58)
        w = size * wd * np.where(u < 0.42, 0.40 + 0.60 * np.sin(clamp(u / 0.42) * math.pi / 2), (1 - t) ** 0.95 * (1 + 0.35 * t))
        w = w + size * 0.010 * np.sin(u * 60 + r.random() * 6) * smooth(0.25, 0.45, u) * smooth(1.0, 0.8, u)
        e = np.where(u < -0.02, np.hypot(u * ln, v), np.where(u > 1, (u - 1) * ln + 0.01, np.abs(v) - w))
        side = clamp(0.5 + 0.5 * v / np.maximum(w, 1e-3))
        facing = (k * -0.46 + s * 0.70) * (side - 0.5) * 2 * fold
        use = e < d
        lit = np.where(use, 0.80 + facing * 1.6 + 0.10 * u, lit)
        veins = np.maximum(veins, smooth(size * 0.013, size * 0.004, np.abs(v)) * (u > 0) * (u < 0.93))
        near = np.where(use, u, near)
        d = np.minimum(d, e)
    n = noise[p.s]
    dark, mid, light = [rgb(q) for q in tone]
    col = mix(np.broadcast_to(mid, p.shape + (3,)), np.broadcast_to(light, p.shape + (3,)), clamp(0.62 - 0.85 * near + 0.35 * n)[..., None])
    col = mix(col, dark, clamp(0.55 * smooth(0.55, 1.0, near) + 0.25 * n)[..., None])
    col = mix(col, light, (0.55 * veins)[..., None])
    return p, col * clamp(lit, 0.35, 1.5)[..., None], p.cover(d, 1.2)


def maple():
    """A small maple that leans over the pond, seen from above."""
    c = Canvas(P.px(380), 3, 1.0, aspect=0.9)
    r = rng(91)
    noise = fbm(c.shape, 22, 79, 3)
    segs, spots = [], []

    def grow(x, y, a, ln, w, depth):
        n = 6
        for i in range(n):
            x1, y1 = x + math.sin(a) * ln / n, y - math.cos(a) * ln / n
            w1 = w * (1 - 0.6 * (i + 1) / n)
            segs.append((x, y, w * (1 - 0.6 * i / n), x1, y1, w1))
            x, y = x1, y1
            a += r.normal() * 0.12
            if i >= 2 or depth:
                spots.append((x, y, a + r.normal() * 0.5))
            if depth < 1 and i in (2, 4):
                grow(x, y, a + (1 if i % 4 else -1) * r.uniform(0.5, 0.9), ln * r.uniform(0.40, 0.55), w1 * 0.7, depth + 1)
        for j in (-0.8, 0.0, 0.8):
            spots.append((x, y, a + j + r.normal() * 0.2))
    for a, ln in ((-1.75, 0.80), (-2.55, 0.66), (-1.05, 0.52), (-3.4, 0.40), (2.2, 0.28), (0.3, 0.34), (1.2, 0.30)):
        grow(0.34, -0.22, a, ln, 0.026, 0)
    for j in range(8):
        spots.append((0.34 + r.normal() * 0.10, -0.22 + r.normal() * 0.10, r.random() * TAU))
    r.shuffle(spots)
    tones = [('#7A1216', '#C0281E', '#F07A3A'), ('#8A1A12', '#D2401E', '#F79A48'), ('#641018', '#A61C20', '#E2582E'), ('#9A3A12', '#E0701E', '#FFC25A'), ('#6E1420', '#B82A2A', '#F0884A')]
    leaves, mask = [], np.zeros(c.shape, F)
    for i, (x, y, a) in enumerate(spots):
        s = r.uniform(0.145, 0.215)
        if abs(x) > 0.95 - s * 0.9 or abs(y) > 0.85 - s * 0.9:
            continue
        q = maple_leaf(c, x, y, a, s, tones[int(r.integers(len(tones)))], 900 + i, noise, fold=r.uniform(0.12, 0.30))
        leaves.append(q)
        mask[q[0].s] = np.maximum(mask[q[0].s], q[2])
    wood_, H = np.zeros(c.shape, F), np.zeros(c.shape, F)
    for x0, y0, w0, x1, y1, w1 in segs:
        d = c.taper(x0, y0, w0, x1, y1, w1)
        wood_ = np.maximum(wood_, c.cover(d))
        H = np.maximum(H, np.sqrt(np.maximum(w0 * w0 - (d + w0) ** 2, 0)) * (d < 0))
    s = blur(shift(np.maximum(mask, wood_), int(0.055 / c.px), int(0.085 / c.px)), 0.028 / c.px) * 0.45
    c.put(rgb('#020A08'), (s * smooth(1.0, 0.95, np.abs(c.X)) * smooth(0.90, 0.85, np.abs(c.Y))).astype(F))
    nx, ny, nz = normals(blur(H, 1), c.px)
    c.put(shade(SUN, nx, ny, nz, rgb('#4A3A2C') * (1 + 0.4 * noise)[..., None], metal=0, rough=0.8, spec=0.03), wood_)
    k = max(2, int(0.02 / c.px))
    for p, col, cov in leaves:
        sh = blur(shift(np.pad(cov, 2 * k), k, int(1.6 * k)), 0.8 * k)[2 * k:-2 * k, 2 * k:-2 * k] * 0.45
        c.col[p.s] = c.col[p.s] * (1 - sh * (c.alpha[p.s] > 0.5))[..., None]
        lay(c, p, col, cov)
    small(c.image(tone=False, exposure=1.0), 'maple', 84)


class Part:
    """A rectangle of a canvas that can be drawn on with the same distance fields."""
    def __init__(self, c, x, y, r):
        w = Win(c, x, y, r)
        self.s, self.px, self.ok = w.s, c.px, w.ok
        self.X, self.Y = c.X[w.s], c.Y[w.s]
        self.shape = self.X.shape

    def cover(self, d, soft=1.0):
        return clamp(0.5 - d / (self.px * soft)).astype(F)


def lay(c, p, col, cov):
    """Puts a part of a picture on the canvas."""
    k, a = cov[..., None], c.alpha[p.s]
    out = cov + a * (1 - cov)
    c.col[p.s] = (col * k + c.col[p.s] * a[..., None] * (1 - k)) / np.maximum(out, 1e-6)[..., None]
    c.alpha[p.s] = out


def moss_cells():
    """Soft cushions of moss: many little domes, each a tuft."""
    cells = []
    for i in range(4):
        c = Canvas(P.px(150), 3, 1.12)
        n1, n2 = fbm(c.shape, 4, 460 + i, 3), fbm(c.shape, 22, 470 + i, 4)
        d = c.R - 0.88 - 0.10 * n1 - 0.03 * n2
        H = bevel(d, 0.55, 0.16)
        for sc, hh in ((9, 0.045), (21, 0.026)):
            e = worley(c.X + 0.02 * n2, c.Y + 0.02 * n1, sc, 480 + i + sc)
            H = H + hh * np.sqrt(clamp(1 - e * e))
        H = blur(H + 0.010 * white(c.shape, 490 + i) + 0.012 * n2, 0.55 * c.ss) * smooth(0.02, -0.05, d)
        t = clamp(0.34 + 0.30 * n2 + 0.25 * n1 + 2.2 * (H - blur(H, 0.05 / c.px)))
        alb = mix(np.broadcast_to(rgb('#2E4A18'), c.shape + (3,)), np.broadcast_to(rgb('#87A040'), c.shape + (3,)), t[..., None])
        nx, ny, nz = normals(H, c.px, 0.75)
        col = shade(SUN, nx, ny, nz, alb, metal=0, rough=0.95, spec=0.01, ao=occlusion(H, c.px, (0.02, 0.06), 0.8), sh=cast(H, c.px, LIGHT_DIR, slope=0.7, reach=0.14))
        cov = smooth(0.03, -0.05, d + 0.05 * n2)
        c.put(rgb('#020602'), (blur(cov, 0.06 / c.px) * 0.75 * smooth(1.12, 1.0, c.R)).astype(F))
        c.put(col, cov.astype(F), H)
        cells.append(c.image(exposure=0.95))
    small(sheet(cells, 4), 'moss', 82)


# ------------------------------------------------------------------ build
P.run([bed, caustic, stones, stones2, pads, flowers, fish, island, bits, steps, moss_cells, panel, tag, dragonfly, maple])
if P.want('sounds'):
    P.sounds('water')
P.finish()
