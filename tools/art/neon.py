"""Neon: a bar sign at night. Bent glass tubes on a round brick wall; every lit tube is its own picture, so it can flicker.

    python neon.py --draft             half size, quick
    python neon.py                     final
    python neon.py wall tubes          only these parts

The tubes are drawn twice: as cold glass with electrodes, black paint and clips, and as light that is added on top.
The light that falls on the bricks is worked out from where the tubes are, so the relief of the wall lights up with them.
"""
import os
import struct
import sys

from metals import *
from pack import Pack

P = Pack('neon', sys.argv)
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')

# Moonlight from the upper left, a street lamp far away on the right.
NIGHT = Studio(lights=[((-0.48, -0.70, 0.56), 0.36, '#C8D6FF', 1.75), ((0.82, -0.18, 0.46), 0.22, '#FFCFA6', 0.45), ((0.10, 0.90, 0.40), 0.34, '#8FA4FF', 0.28)],
               sky='#46567C', floor='#07070B', horizon=0.35, ambient=0.30)

PINK, MAGENTA, CYAN, VIOLET, YELLOW, MINT = '#FF2D86', '#D81CFF', '#18E6FF', '#7C4DFF', '#FFC42E', '#3BFFB0'
RT = 0.0165                 # radius of the big tube, in wheel radii
R0 = 0.924                  # radius of the ring it is bent to
JOINTS = (60, 180, 300)     # where its three pieces meet
EXT = 1.09                  # half size of the wall's picture


def flat(col, shape):
    return np.broadcast_to(rgb(col) if isinstance(col, str) else V(col), shape + (3,))


# ---------------------------------------------------------------- brick
def bricks(c, seed=7):
    """Height, colour and the distance to the nearest mortar joint."""
    bh, bl, mo = 0.100, 0.290, 0.0135
    sh = c.shape
    wx, wy = 0.0035 * fbm(sh, 9, seed + 1, 3), 0.0030 * fbm(sh, 9, seed + 2, 3)
    X, Y = c.X + wx, c.Y + wy + 0.05
    row = np.floor((Y + 3) / bh).astype(np.int32)
    g = rng(seed)
    shiftrow = (g.random(128) * 0.05).astype(F)[row % 128]
    u = (X + 4 + (row % 2) * 0.5 * bl + shiftrow) / bl
    col = np.floor(u).astype(np.int32)
    fx, fy = (u - col - 0.5) * bl, ((Y + 3) / bh - row - 0.5) * bh
    tab = g.random((6, 4096)).astype(F)
    i = (row * 97 + col * 31) % 4096
    v = [tab[k][i] for k in range(6)]
    rag = 0.0028 * fbm(sh, 60, seed + 3, 3) + 0.0016 * fbm(sh, 160, seed + 4, 2)
    hx, hy, r = bl / 2 - mo / 2, bh / 2 - mo / 2, 0.011
    qx, qy = np.abs(fx) - hx + r, np.abs(fy) - hy + r
    d = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r + rag
    H = bevel(d, 0.013, 0.021)
    inb = clamp(-d / 0.006)
    H = H + inb * (0.0030 * (v[0] - 0.5) + fx * 0.030 * (v[1] - 0.5) + fy * 0.07 * (v[2] - 0.5))
    H = H + inb * (0.0012 * fbm(sh, 26, seed + 5, 4) + 0.0007 * fbm(sh, 130, seed + 6, 3))
    pits = clamp((fbm(sh, 150, seed + 7, 2) - 1.0) * 2.0)
    H = H - 0.0032 * pits * inb
    H = H + (1 - inb) * 0.0016 * fbm(sh, 120, seed + 8, 3)
    reds = [rgb(x) for x in ('#5C2B27', '#6B352B', '#4B2527', '#3A2429', '#57302C', '#46282C')]
    base = np.zeros(sh + (3,), F)
    pick = (v[3] * len(reds)).astype(np.int32)
    for k, q in enumerate(reds):
        base = np.where((pick == k)[..., None], q, base)
    base = base * (0.80 + 0.40 * v[4])[..., None] * (1 + 0.16 * fbm(sh, 30, seed + 9, 4))[..., None]
    soot = clamp(0.35 + 0.5 * fbm(sh, 3.2, seed + 10, 4))
    base = base * (1 - 0.38 * soot)[..., None]
    alb = mix(flat('#6A625C', sh) * (0.75 + 0.18 * fbm(sh, 90, seed + 11, 3))[..., None], base, inb[..., None])
    return H, alb, d


def cable_points():
    """The main cable: from under the hub's plate down to the frame."""
    key = [(-0.06, 0.10), (-0.10, 0.30), (-0.235, 0.52), (-0.255, 0.70), (-0.31, 0.86), (-0.38, 0.95)]
    out = []
    for i in range(len(key) - 1):
        p0, p1, p2, p3 = key[max(0, i - 1)], key[i], key[i + 1], key[min(len(key) - 1, i + 2)]
        for s in range(8):
            t = s / 8
            out.append(tuple(0.5 * (2 * p1[k] + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t * t + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t ** 3) for k in (0, 1)))
    return out + [key[-1]]


def scene(c):
    """The wall with its frame, lugs and cables: height, colour, and masks for painted steel and rubber."""
    sh = c.shape
    H, alb, _ = bricks(c)
    wall = smooth(0.962, 0.955, c.R)
    H = H * wall
    # steel channel around it
    ring = np.maximum(c.R - 1.0, 0.953 - c.R)
    Hf = 0.018 + bevel(ring, 0.012, 0.034)
    steel = c.cover(ring)
    H = np.where(ring < 0, np.maximum(H, Hf), H)
    for k in range(4):                                                        # lugs that hold it
        a = math.radians(45 + 90 * k)
        x, y = c.polar(a, 1.012)
        lug = c.box(0.052, 0.062, x, y, rot=a, r=0.030)
        H = np.where(lug < 0, np.maximum(H, 0.010 + bevel(lug, 0.010, 0.020)), H)
        steel = np.maximum(steel, c.cover(lug))
        bx, by = c.polar(a, 1.040)
        q = np.hypot(c.X - bx, c.Y - by)
        hexa = c.regular(6, 0.0200, rot=a, x=bx, y=by)
        H = np.where(q < 0.027, np.maximum(H, 0.034), H)
        H = np.where(hexa < 0, np.maximum(H, 0.036 + bevel(hexa, 0.005, 0.012)), H)
    H = rivets(c, H, 24, 0.977, 0.0080, 0.050, phase=TAU / 48)
    # cables
    rub = np.zeros(sh, F)

    def wire(pts, r):
        nonlocal H, rub
        d = np.full(sh, 9, F)
        for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
            d = np.minimum(d, c.capsule(x0, y0, x1, y1, 0.0))
        H = np.where(d < r, np.maximum(H, 0.024 + np.sqrt(clamp(r * r - d * d))), H)
        rub = np.maximum(rub, c.cover(d - r))
    wire(cable_points(), 0.0090)
    for j in JOINTS:
        a = math.radians(j)
        for s in (-1, 1):
            a0 = a + s * 0.022
            p = [c.polar(a0, R0), c.polar(a + s * 0.012, R0 + 0.012), c.polar(a + s * 0.008, 0.956)]
            wire(p, 0.0062)
        gx, gy = c.polar(a, 0.950)
        q = np.hypot(c.X - gx, c.Y - gy) - 0.020
        H = np.where(q < 0, np.maximum(H, 0.030 + bevel(q, 0.008, 0.016)), H)
        rub = np.maximum(rub, c.cover(q))
    for i in (12, 25):                                                        # saddle clips on the main cable
        x, y = cable_points()[i]
        x1, y1 = cable_points()[i + 1]
        a = math.atan2(x1 - x, -(y1 - y))
        b = c.box(0.022, 0.0075, x, y, rot=a, r=0.004)
        H = np.where(b < 0, np.maximum(H, 0.036 + bevel(b, 0.003, 0.004)), H)
        steel = np.maximum(steel, c.cover(b))
        rub = rub * (1 - c.cover(b))
    alb = mix(alb, flat('#15161B', sh), steel[..., None])
    alb = mix(alb, flat('#101013', sh), rub[..., None])
    inside = np.maximum(steel, c.cover(c.R - 0.999))
    return H, alb, steel, rub, inside


def wall():
    c = Canvas(P.px(1040), P.ss(2), EXT)
    H, alb, steel, rub, inside = scene(c)
    nx, ny, nz = normals(H, c.px)
    ao = occlusion(H, c.px, (0.006, 0.018, 0.05), 1.3)
    sh = cast(H, c.px, reach=0.12, slope=0.6)
    br = shade(NIGHT, nx, ny, nz, alb * 1.9, metal=0, rough=0.45, spec=0.05, ao=ao, sh=sh, clear=0.16)
    st = shade(NIGHT, nx, ny, nz, alb * 1.6, metal=0.25, rough=0.28, spec=0.07, ao=ao, sh=sh, clear=0.75)
    col = mix(br, st, np.maximum(steel, rub * 0.6)[..., None])
    # the middle is darker: less of the sky reaches it
    c.put(col, inside, H)
    P.save(c.image(exposure=0.92), 'wall', quality=86)


# ---------------------------------------------------------------- light on the wall
def lit_by(c, H, alb, steel, sources, gloss=0.55):
    """Light of many small lamps on the relief, seen from above. sources: (x, y, z, colour)."""
    nx, ny, nz = normals(H, c.px)
    ao = occlusion(H, c.px, (0.006, 0.02), 1.2)
    dif = np.zeros(c.shape + (3,), F)
    spc = np.zeros(c.shape + (3,), F)
    for x, y, z, col in sources:
        dx, dy, dz = x - c.X, y - c.Y, z - H
        d2 = dx * dx + dy * dy + dz * dz + 1e-5
        inv = 1 / np.sqrt(d2)
        lx, ly, lz = dx * inv, dy * inv, dz * inv
        nl = clamp(nx * lx + ny * ly + nz * lz, 0, 1)
        dif += (nl / d2)[..., None] * col
        hl = 1 / np.sqrt(lx * lx + ly * ly + (lz + 1) ** 2)
        nh = clamp((nx * lx + ny * ly + nz * (lz + 1)) * hl, 0, 1)
        spc += ((nh ** 34) * nl ** 0.5 / d2 ** 0.75)[..., None] * col
    n = len(sources)
    k = (0.35 + 0.65 * ao)[..., None]
    return (dif / n * (alb * 1.6 + 0.004) + spc / n * gloss * (0.045 + 0.12 * steel[..., None])) * k


def ring_sources(radius, z, n, colour):
    out = []
    for i in range(n):
        a = (i + 0.5) / n * TAU
        x, y = math.sin(a) * radius, -math.cos(a) * radius
        out.append((x, y, z, colour(a, y / radius)))
    return out


def pinkish(a, t):
    """Hot pink at the top of the ring, magenta at the bottom."""
    k = smooth(-0.7, 0.9, t)
    return mix(rgb(PINK), rgb(MAGENTA), k)


def spill():
    """What the big ring and the ring around the hub throw on the bricks."""
    c = Canvas(P.px(900), 1, EXT)
    H, alb, steel, rub, inside = scene(c)
    src = ring_sources(R0, 0.050, 120, pinkish)
    col = lit_by(c, H, alb, steel, src) * 0.34
    # the tube hides the wall right under itself
    under = smooth(RT * 1.1, RT * 2.6, np.abs(c.R - R0))
    c.col = col * (0.45 + 0.55 * under)[..., None] * inside[..., None]
    c.alpha[:] = 1
    P.save(c.image(tone=True), 'spill', quality=86, how='jpg')
    c = Canvas(P.px(600), 1, 0.62)
    H, alb, steel, rub, inside = scene(c)
    src = ring_sources(0.382, 0.050, 72, lambda a, t: rgb(CYAN))
    col = lit_by(c, H, alb, steel, src) * 0.085
    c.col = col * (smooth(0.62, 0.50, c.R) * smooth(0.30, 0.36, c.R))[..., None]
    c.alpha[:] = 1
    P.save(c.image(tone=True), 'spillin', quality=86, how='jpg')


# ---------------------------------------------------------------- glass
def glass(nx, ny, nz, q, milk='#CFC6D4', body=0.42):
    """Cold tube, coated white inside. q: 0 in the middle, 1 at the edge. Returns colour and coverage."""
    dif = NIGHT.diffuse(nx, ny, nz) * rgb(milk) * body * 2.4 + rgb(milk) * 0.020
    fres = 0.06 + 0.94 * np.power(clamp(1 - nz), 4)
    ref = NIGHT.reflect(nx, ny, nz, 0.05)
    streak = NIGHT.reflect(nx, ny, nz, 0.20)
    rim = smooth(0.50, 1.0, q)
    col = dif * (1 - 0.50 * rim)[..., None] + ref * (fres * 2.6)[..., None] + streak * 0.10 + rgb('#9DB2E6') * (0.055 * rim)[..., None]
    a = 0.70 + 0.30 * smooth(0.35, 0.95, q)
    return col, a


def lit_profile(q, rt, core=1.0, near=0.55, wide=0.16, far=0.05, s1=1.6, s2=4.2, s3=12.0):
    """Brightness across a burning tube, q: distance from its middle. Returns white core, colour."""
    t = np.abs(q) / rt
    body = smooth(1.06, 0.86, t)
    white = np.exp(-(t / 0.50) ** 2) * core
    out = clamp(t - 0.95, 0, 1e6)
    glow = near * np.exp(-out / s1) + wide * np.exp(-out / s2) + far * np.exp(-out / s3)
    return white, body * 0.95 + glow * smooth(0.75, 1.0, t) + glow * 0.25 * body


# where things are along the tube next to a joint, in wheel radii from the middle of the gap
BOOT0, BOOT1, METAL1, BLACK1 = 0.014, 0.050, 0.088, 0.160


def along(A, R, joints=JOINTS, radius=R0):
    """Arc length to the nearest joint, and which piece of the ring a point belongs to."""
    best = np.full(A.shape, 9, F)
    for j in joints:
        d = (A - math.radians(j) + math.pi) % TAU - math.pi
        best = np.minimum(best, np.abs(d) * radius)
    return best


CLIPS = [j + o for j in JOINTS for o in (22, 41, 60, 79, 98)]


def clip_arc(A, radius=R0, clips=CLIPS):
    best = np.full(A.shape, 9, F)
    for j in clips:
        d = (A - math.radians(j) + math.pi) % TAU - math.pi
        best = np.minimum(best, np.abs(d) * radius)
    return best


def ring_tube(c, radius, rt, joints, clips, scale=1.0, milk='#CFC6D4', light=NIGHT):
    """A ring of cold glass with its electrodes, black paint and clips. scale: size of the fittings."""
    sh = c.shape
    s = along(c.A, c.R, joints, radius) / scale
    k = clip_arc(c.A, radius, clips) / scale
    q = c.R - radius
    ux, uy = np.sin(c.A), -np.cos(c.A)
    # soft shadow on the wall, down to the right
    qs = np.hypot(c.X - rt * 1.6, c.Y - rt * 2.2) - radius
    shade_ = np.exp(-(qs / (rt * 1.7)) ** 2) * 0.55 * (s > BOOT0)
    c.put(np.zeros(sh + (3,), F), shade_.astype(F))
    # posts under the clips
    post = np.maximum(k - 0.0095, (np.abs(q) - rt * 2.15) / scale)
    Hp = bevel(post * scale, 0.004 * scale, 0.006 * scale)
    nx, ny, nz = normals(Hp, c.px)
    pm = shade(light, nx, ny, nz, STEEL * 0.8, metal=0.9, rough=0.3)
    c.put(pm, clamp(0.5 - post * scale / c.px).astype(F))

    def tube(r, cov_s, colour):
        t = clamp(np.abs(q) / r)
        nzt = np.sqrt(clamp(1 - t * t * 0.985))
        n_r = q / r
        nxt, nyt = ux * n_r, uy * n_r
        l = np.sqrt(nxt * nxt + nyt * nyt + nzt * nzt)
        col, a = colour(nxt / l, nyt / l, nzt / l, t)
        cov = clamp(0.5 - (np.abs(q) - r) / c.px) * cov_s
        c.put(col, (cov * a).astype(F))
    soft = c.px / scale
    gate = lambda a, b: clamp((s - a) / soft + 0.5) * clamp((b - s) / soft + 0.5)
    tube(rt, gate(BLACK1 - 0.004, 9), lambda x, y, z, t: glass(x, y, z, t, milk))
    # clear end with the metal cup inside
    tube(rt, gate(BOOT1 - 0.004, METAL1 + 0.004), lambda x, y, z, t: (NIGHT.reflect(x, y, z, 0.05) * (0.10 + 0.9 * (1 - z)[..., None] ** 2) * 1.2 + 0.010, 0.55 + 0.45 * smooth(0.6, 1.0, t)))
    tube(rt * 0.62, gate(BOOT1 - 0.004, METAL1 - 0.010), lambda x, y, z, t: (shade(light, x, y, z, V([0.62, 0.60, 0.58]), metal=0.95, rough=0.25) * 1.25, np.ones_like(t)))
    # black paint
    tube(rt * 1.02, gate(METAL1, BLACK1), lambda x, y, z, t: (shade(light, x, y, z, V([0.010, 0.010, 0.012]), metal=0, rough=0.3, clear=0.8) * 1.2, np.ones_like(t)))
    # rubber boots
    tube(rt * 1.28, gate(BOOT0, BOOT1), lambda x, y, z, t: (shade(light, x, y, z, V([0.020, 0.020, 0.023]), metal=0, rough=0.5, clear=0.25) * (1 + 0.25 * np.cos(s * 620)[..., None]), np.ones_like(t)))
    # clips over the glass
    band = gate(BLACK1, 9) * clamp((0.0042 - k) / soft + 0.5)
    tube(rt * 1.10, band, lambda x, y, z, t: (shade(light, x, y, z, V([0.70, 0.70, 0.72]), metal=0.95, rough=0.22) * 1.2, np.ones_like(t)))
    return s, k, q


def tubes():
    """The big ring, cold."""
    c = Canvas(P.px(1040), P.ss(3), EXT)
    ring_tube(c, R0, RT, JOINTS, CLIPS)
    P.save(c.image(tone=True), 'tubes', quality=88)


def arc_dist(c, radius, a0, a1):
    """Distance to a piece of a circle (degrees), ends included."""
    mid, half = math.radians((a0 + a1) / 2), math.radians((a1 - a0) / 2)
    da = (c.A - mid + math.pi) % TAU - math.pi
    d = np.abs(c.R - radius)
    for e in (a0, a1):
        x, y = c.polar(math.radians(e), radius)
        q = np.hypot(c.X - x, c.Y - y)
        d = np.where(np.abs(da) > half, np.where((da > 0) == (e == a1), q, d), d)
    return d


def lit_ring(c, radius, rt, pieces, clips, scale, colour, **kw):
    """Light of burning pieces of a ring, with the clips left dark."""
    d = np.full(c.shape, 9, F)
    trim = math.degrees((BLACK1 + 0.004) * scale / radius)
    for a0, a1 in pieces:
        d = np.minimum(d, arc_dist(c, radius, a0 + trim, a1 - trim))
    white, body = lit_profile(d, rt, **kw)
    k = clip_arc(c.A, radius, clips) / scale
    clip = 1 - 0.90 * clamp((0.0046 - k) / (c.px / scale) + 0.5) * (np.abs(c.R - radius) < rt * 1.14)
    return colour * (body * clip)[..., None] + (white * clip * 0.95)[..., None]


def lit():
    """The big ring, burning: one picture for each of its three pieces."""
    for n, (a0, a1) in enumerate(((-60, 60), (60, 180), (180, 300))):
        c = Canvas(P.px(900), P.ss(2), EXT)
        t = c.Y / np.maximum(c.R, 1e-4)
        colr = mix(flat(PINK, c.shape), flat(MAGENTA, c.shape), smooth(-0.7, 0.9, t)[..., None])
        c.col = lit_ring(c, R0, RT, [(a0, a1)], CLIPS, 1.0, colr, near=0.50, wide=0.17, far=0.050)
        c.col = c.col * smooth(EXT, EXT - 0.07, np.maximum(np.abs(c.X), np.abs(c.Y)))[..., None]
        c.alpha[:] = 1
        c.col = c.col * smooth(1.088, 0.985, c.R)[..., None]        # the picture is square, its light must not be
        P.save(c.image(tone=True), 'lit%d' % (n + 1), quality=88, how='jpg')


# ---------------------------------------------------------------- the hub: a black enamelled plate with a ring of its own
HR, HRT = 0.900, 0.0230
HJ = (180,)
HCLIPS = [22.5 + 45 * i for i in range(8)]


def hubplate():
    c = Canvas(P.px(560), P.ss(3), 1.0)
    d = c.R - 0.985
    H = bevel(d, 0.030, 0.034) - 0.016 * smooth(0.955, 0.935, c.R)
    nx, ny, nz = normals(H, c.px)
    fx, fy = nx + 0.16 * c.X, ny + 0.16 * c.Y
    inv = 1 / np.sqrt(fx * fx + fy * fy + nz * nz)
    dark = shade(NIGHT, fx * inv, fy * inv, nz * inv, flat('#0B0B10', c.shape), metal=0, rough=0.3, clear=0.50, ao=occlusion(H, c.px, (0.02, 0.06), 1))
    rim = shade(NIGHT, nx, ny, nz, STEEL * 0.8, metal=0.95, rough=0.2)
    col = mix(dark, rim, (smooth(0.945, 0.955, c.R))[..., None])
    g = fbm(c.shape, 160, 3, 2)
    col = col * (1 + 0.05 * g)[..., None]
    c.put(col, c.cover(d), H)
    P.save(c.image(), 'hubplate', quality=88)
    c = Canvas(P.px(560), P.ss(3), 1.0)
    ring_tube(c, HR, HRT, HJ, HCLIPS, scale=1.25, milk='#C2D2D6')
    P.save(c.image(), 'hubtube', quality=88)
    c = Canvas(P.px(560), P.ss(2), 1.45)
    # its light fades into the plate inside and over the bricks outside
    c.col = lit_ring(c, HR, HRT, [(-180, 180)], HCLIPS, 1.25, flat(CYAN, c.shape), near=0.55, wide=0.20, far=0.040, s1=1.5, s2=3.6, s3=8.0)
    c.col = c.col * smooth(1.45, 1.20, c.R)[..., None]
    c.alpha[:] = 1
    P.save(c.image(tone=True), 'hublit', quality=90, how='jpg')


def polyline(c, pts):
    """Distance to a bent line, the direction across it and how far along a point is."""
    d = np.full(c.shape, 9, F)
    nx, ny = np.zeros(c.shape, F), np.zeros(c.shape, F)
    at = np.zeros(c.shape, F)
    total = 0.0
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        bx, by = x1 - x0, y1 - y0
        l = math.hypot(bx, by)
        t = clamp(((c.X - x0) * bx + (c.Y - y0) * by) / max(1e-9, l * l))
        ex, ey = c.X - x0 - bx * t, c.Y - y0 - by * t
        q = np.hypot(ex, ey)
        near = q < d
        inv = 1 / np.maximum(q, 1e-6)
        nx, ny = np.where(near, ex * inv, nx), np.where(near, ey * inv, ny)
        at = np.where(near, total + t * l, at)
        d = np.where(near, q, d)
        total += l
    return d, nx, ny, at, total


def curve(key, steps=12):
    out = []
    n = len(key)
    for i in range(n - 1):
        p0, p1, p2, p3 = key[max(0, i - 1)], key[i], key[i + 1], key[min(n - 1, i + 2)]
        for s in range(steps):
            t = s / steps
            out.append(tuple(0.5 * (2 * p1[k] + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t * t + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t ** 3) for k in (0, 1)))
    return out + [key[-1]]


SWOOSH = curve([(-0.50, 0.030), (-0.30, -0.018), (-0.05, -0.004), (0.18, 0.016), (0.40, -0.028), (0.50, -0.060)])
ARROW = [(-0.115, 0.105), (0.0, -0.035), (0.115, 0.105)]


def bent(name, pts, rt, extent, aspect, size, colour, milk):
    """A short bent tube as three pictures: cold, burning, and the light it adds."""
    c = Canvas(P.px(size), P.ss(3), extent, aspect=aspect)
    d, ux, uy, at, total = polyline(c, pts)
    t = clamp(d / rt)
    nz = np.sqrt(clamp(1 - t * t * 0.985))
    col, a = glass(ux * t, uy * t, nz, t, milk)
    ends = np.minimum(at, total - at)
    qs = polyline(_moved(c, rt * 1.3, rt * 1.8), pts)[0]
    c.put(np.zeros(c.shape + (3,), F), (np.exp(-(qs / (rt * 1.6)) ** 2) * 0.5).astype(F))
    c.put(col, (clamp(0.5 - (d - rt) / c.px) * a).astype(F))
    blk = shade(NIGHT, ux * t, uy * t, nz, V([0.010, 0.010, 0.012]), metal=0, rough=0.3, clear=0.8) * 1.2
    c.put(blk, (clamp(0.5 - (d - rt * 1.04) / c.px) * clamp(0.5 - (ends - rt * 1.4) / c.px)).astype(F))
    P.save(c.image(), name, how='png')
    c = Canvas(P.px(size), P.ss(2), extent, aspect=aspect)
    d = polyline(c, trimmed(pts, rt * 1.5))[0]
    white, body = lit_profile(d, rt, near=0.50, wide=0.10, far=0.0, s1=1.2, s2=2.6)
    edge = smooth(extent, extent * 0.86, np.abs(c.X)) * smooth(extent * aspect, extent * aspect * 0.78, np.abs(c.Y))
    c.col = (rgb(colour) * body[..., None] + (white * 0.95)[..., None]) * edge[..., None]
    c.alpha[:] = 1
    P.save(c.image(tone=True), name + 'lit', quality=90, how='jpg')


def trimmed(pts, cut):
    """The same path without its first and last stretch."""
    def front(q):
        left, out = cut, list(q)
        while len(out) > 2:
            (x0, y0), (x1, y1) = out[0], out[1]
            l = math.hypot(x1 - x0, y1 - y0)
            if l > left:
                out[0] = (x0 + (x1 - x0) * left / l, y0 + (y1 - y0) * left / l)
                return out
            left -= l
            out.pop(0)
        (x0, y0), (x1, y1) = out
        l = math.hypot(x1 - x0, y1 - y0)
        return [(x0 + (x1 - x0) * left / l, y0 + (y1 - y0) * left / l), (x1, y1)]
    return front(front(pts)[::-1])[::-1]


class _moved:
    """A canvas seen from a little aside, for shadows."""

    def __init__(self, c, dx, dy):
        self.X, self.Y, self.shape, self.px = c.X - dx, c.Y - dy, c.shape, c.px


def swoosh():
    bent('swoosh', SWOOSH, 0.0210, 0.64, 0.24 / 0.64, 420, YELLOW, '#D8D2C0')


def arrow():
    bent('arrow', ARROW, 0.0240, 0.24, 1.0, 180, YELLOW, '#D8D2C0')


# ---------------------------------------------------------------- entries
SR, SRT = 0.905, 0.0430
SJ = (180,)


def cup():
    """A black acrylic disc on the wall with a cold ring of its own."""
    c = Canvas(P.px(280), P.ss(3), 1.06)
    d = c.R - 0.985
    H = bevel(d, 0.050, 0.050)
    nx, ny, nz = normals(H, c.px)
    fx, fy = nx + 0.22 * c.X, ny + 0.22 * c.Y
    inv = 1 / np.sqrt(fx * fx + fy * fy + nz * nz)
    body = shade(NIGHT, fx * inv, fy * inv, nz * inv, flat('#0A0A10', c.shape), metal=0, rough=0.3, clear=0.55)
    edge = shade(NIGHT, nx, ny, nz, flat('#14141C', c.shape), metal=0.2, rough=0.2, clear=0.9)
    c.put(mix(body, edge, smooth(0.93, 0.96, c.R)[..., None]), c.cover(d), H)
    ring_tube(c, SR, SRT, SJ, [60, 120, 240, 300], scale=2.1, milk='#C9C2DA')
    P.save(c.image(), 'cup', quality=92, how='jpg')


def cuplit():
    for name, colour, kw in (('ringv', VIOLET, dict(near=0.55, wide=0.22, far=0.03, s1=1.3, s2=3.0, s3=6.0)),
                             ('ringy', YELLOW, dict(near=0.75, wide=0.34, far=0.10, s1=1.6, s2=4.0, s3=8.0))):
        c = Canvas(P.px(300), P.ss(2), 1.60)
        c.col = lit_ring(c, SR, SRT, [(-180, 180)], [60, 120, 240, 300], 2.1, flat(colour, c.shape), **kw)
        c.col = c.col * smooth(1.60, 1.25, c.R)[..., None]
        c.alpha[:] = 1
        P.save(c.image(tone=True), name, quality=90, how='jpg')
    # the little tube between the electrodes: somebody is in
    c = Canvas(P.px(120), 4, 0.36, aspect=0.5)
    for name, colour in (('dash', MINT), ('dashp', PINK)):
        c = Canvas(P.px(120), 4, 0.36, aspect=0.5)
        d = c.capsule(-0.085, 0, 0.085, 0, 0.0)
        white, body = lit_profile(d, 0.036, near=0.7, wide=0.28, far=0.05, s1=1.4, s2=3.2, s3=6)
        edge = smooth(0.36, 0.27, np.abs(c.X)) * smooth(0.18, 0.12, np.abs(c.Y))
        c.col = (rgb(colour) * body[..., None] + white[..., None]) * edge[..., None]
        c.alpha[:] = 1
        P.save(c.image(tone=True), name, quality=92, how='jpg')


def spark():
    c = Canvas(P.px(48), 2, 1.0)
    c.col = rgb('#FFFFFF') * gauss(c.R, 0.16)[..., None] + rgb('#FFD27A') * (0.8 * gauss(c.R, 0.40) * smooth(1.0, 0.7, c.R))[..., None]
    c.alpha[:] = 1
    P.save(c.image(tone=True), 'spark', how='png')


def fonts():
    """Pacifico as it is; Tilt Neon without the tables of its variations, which a sign does not need."""
    src = os.path.join(FONTS, 'pacifico', 'Pacifico-Regular.ttf')
    with open(src, 'rb') as f, open(os.path.join(P.dir, 'Pacifico-Regular.ttf'), 'wb') as g:
        g.write(f.read())
    d = os.path.join(FONTS, 'tiltneon')
    data = open(os.path.join(d, [x for x in os.listdir(d) if x.lower().endswith('.ttf')][0]), 'rb').read()
    n = struct.unpack('>H', data[4:6])[0]
    tabs = {}
    for i in range(n):
        tag, cs, off, ln = struct.unpack('>4sIII', data[12 + 16 * i:28 + 16 * i])
        tabs[tag] = data[off:off + ln]
    for t in (b'fvar', b'gvar', b'avar', b'HVAR', b'VVAR', b'MVAR', b'STAT', b'cvar', b'DSIG', b'GPOS', b'GDEF', b'GSUB', b'prep', b'fpgm', b'cvt '):
        tabs.pop(t, None)

    def total(b):
        b += b'\0' * (-len(b) % 4)
        return sum(struct.unpack('>%dI' % (len(b) // 4), b)) & 0xFFFFFFFF
    k = len(tabs)
    es = int(math.floor(math.log2(k)))
    out = struct.pack('>IHHHH', 0x00010000, k, 16 * 2 ** es, es, 16 * k - 16 * 2 ** es)
    at, body, head_at = 12 + 16 * k, b'', 0
    for tag in sorted(tabs):
        b = tabs[tag]
        if tag == b'head':
            b = b[:8] + b'\0\0\0\0' + b[12:]
            head_at = at + len(body)
        out += struct.pack('>4sIII', tag, total(b), at + len(body), len(b))
        body += b + b'\0' * (-len(b) % 4)
    out += body
    adj = (0xB1B0AFBA - total(out)) & 0xFFFFFFFF
    out = out[:head_at + 8] + struct.pack('>I', adj) + out[head_at + 12:]
    open(os.path.join(P.dir, 'TiltNeon.ttf'), 'wb').write(out)
    a = open(os.path.join(FONTS, 'pacifico', 'OFL.txt'), encoding='utf-8').read()
    b = open(os.path.join(FONTS, 'tiltneon', 'OFL.txt'), encoding='utf-8').read()
    open(os.path.join(P.dir, 'OFL.txt'), 'w', encoding='utf-8', newline='\n').write('Pacifico-Regular.ttf\n\n' + a.strip() + '\n\n\n' + '=' * 60 + '\n\nTiltNeon.ttf (the tables for variations were taken out)\n\n' + b.strip() + '\n')
    print('fonts', len(data), '->', len(out))


if __name__ == '__main__':
    P.run([fonts, wall, spill, tubes, lit, hubplate, swoosh, arrow, cup, cuplit, spark])
    P.sounds('neon')
    P.finish()
