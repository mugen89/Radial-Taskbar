"""Reactor: a machined weapon-wheel console of gunmetal and titanium around a plasma core."""
import os
import shutil
import sys

from metals import *
from pack import Pack, ROOT

P = Pack('reactor', sys.argv)
FONT = os.path.join(ROOT, 'tools', 'art', 'fonts', 'rajdhani', 'Rajdhani-SemiBold.ttf')

ST = Studio(lights=[((-0.46, -0.70, 0.58), 0.36, '#F2F7FF', 5.4), ((0.84, -0.12, 0.42), 0.20, '#A9D8FF', 1.9),
                    ((0.18, 0.88, 0.38), 0.30, '#5F8CFF', 0.8), ((-0.92, 0.28, 0.26), 0.16, '#FFE6C8', 0.8)], sky='#AFC0DA', floor='#080B11', ambient=0.42)
GUN = V([0.150, 0.160, 0.178])
TRAY = V([0.062, 0.069, 0.080])
TITAN = V([0.44, 0.445, 0.455])
STEEL2 = V([0.62, 0.64, 0.67])


# ------------------------------------------------------------------ helpers
def rep(a, n, phase=0.0):
    """Angle from the nearest of n evenly spaced directions, and which one that is."""
    p = TAU / n
    k = np.round((a - phase) / p)
    return a - phase - k * p, (k % n).astype(np.int32)


def near(a, mid):
    """Signed angle from a direction."""
    return (a - mid + math.pi) % TAU - math.pi


class Local:
    """A window of a canvas around a point, so that bolts need not touch millions of samples."""

    def __init__(self, c, x, y, r):
        x0 = int((x - r + c.extent) / c.px)
        y0 = int((y - r + c.extent * c.aspect) / c.px)
        x1, y1 = int((x + r + c.extent) / c.px) + 2, int((y + r + c.extent * c.aspect) / c.px) + 2
        self.s = (slice(max(0, y0), min(c.h, y1)), slice(max(0, x0), min(c.w, x1)))
        self.X, self.Y = c.X[self.s] - x, c.Y[self.s] - y
        self.R = np.hypot(self.X, self.Y)


def hexd(X, Y, rot=0.0):
    """Measure of a regular hexagon with a corner at `rot`: equals the circumradius on its edge."""
    a = np.arctan2(X, -Y) - rot
    q = np.abs((a % (TAU / 6)) - math.pi / 6)
    return np.hypot(X, Y) * np.cos(q) / math.cos(math.pi / 6)


def hexgrid(X, Y, s):
    """Distance from the middle of the hexagonal cell (0.5 on its border) and the cell's centre."""
    x, y = X / s, Y / s
    rx, ry = 1.0, math.sqrt(3)
    ax, ay = x % rx - rx / 2, y % ry - ry / 2
    bx, by = (x - rx / 2) % rx - rx / 2, (y - ry / 2) % ry - ry / 2
    first = ax * ax + ay * ay < bx * bx + by * by
    gx, gy = np.where(first, ax, bx), np.where(first, ay, by)
    d = np.maximum(np.abs(gx) * 0.5 + np.abs(gy) * 0.8660254, np.abs(gx))
    return d, (x - gx) * s, (y - gy) * s


def allen(c, H, x, y, size, rise=0.6, rot=0.3, sink=0.0):
    """A socket head screw standing on the surface (or sunk into a counterbore)."""
    L = Local(c, x, y, size * 1.8)
    h = H[L.s]
    mid = h[h.shape[0] // 2, h.shape[1] // 2]
    if sink:
        h = np.where(L.R < size * 1.28, mid - sink * smooth(size * 1.28, size * 1.18, L.R), h)
        mid = mid - sink
    head = L.R - size
    top = mid + bevel(head, size * 0.22, size * rise, 'round')
    h = np.where(head < 0, np.maximum(h, top), h)
    sock = hexd(L.X, L.Y, rot) - size * 0.55
    h = np.where(sock < 0, mid + size * rise - size * 0.55 * smooth(0, -size * 0.10, sock), h)
    H[L.s] = h


def streaks1(s, seed):
    """Straight machining marks across the coordinate s."""
    n = 1600
    prof = rng(seed).standard_normal(n).astype(F)
    idx = np.clip((s + 2.0) / 4.0 * (n - 2), 0, n - 2)
    i0 = np.floor(idx).astype(np.int32)
    f = idx - i0
    return (prof[i0] * (1 - f) + prof[i0 + 1] * f).astype(F)


def look(c, H, parts, reach=0.10, slope=0.8, ao_r=(0.006, 0.018, 0.05), wear=0.5, seed=3, grime=0.6, fine=0.0045):
    """Shades several metals at once. parts: (mask, albedo, roughness, brushing or None, metalness)."""
    nx, ny, nz = normals(H, c.px)
    ao = occlusion(H, c.px, ao_r, 1.15)
    sh = cast(H, c.px, reach=reach, slope=slope)
    g = fbm(c.shape, 6, seed, 5)
    g2 = fbm(c.shape, 34, seed + 7, 3)
    cav = clamp((1 - ao) * 1.6 + 0.14 * clamp(g + 0.2))
    edge = clamp((H - blur(H, fine / c.px)) / (fine * 0.5))              # convex edges lose their finish first
    worn = clamp(edge * 1.25 - 0.45 + 0.55 * g2 + 0.25 * g) * clamp(edge * 3) * wear
    out = np.zeros(c.shape + (3,), F)
    for mask, alb, rough, brush, met in parts:
        if np.max(mask) <= 0.001:
            continue
        a = np.broadcast_to(V(alb), c.shape + (3,)) if np.ndim(alb) < 3 else alb
        a = a * (1 + 0.10 * g + 0.05 * g2)[..., None]
        a = mix(a, STEEL2, (worn * 0.75)[..., None])
        a = mix(a, rgb('#06080B'), (clamp(grime * cav))[..., None])
        an = None
        if brush == 'round':
            an = (np.cos(c.A), np.sin(c.A), V(0.45))
        elif brush == 'across':
            an = (V(1.0), V(0.0), V(0.40))
        out += shade(ST, nx, ny, nz, a, metal=met, rough=rough, ao=ao, sh=sh, aniso=an) * mask[..., None]
    return out, ao, sh, (nx, ny, nz)


def light_jpg(im, name, quality=88):
    """Pictures that add light: black is nothing, so no mask is needed."""
    bg = Image.new('RGB', im.size, (0, 0, 0))
    bg.paste(im.convert('RGB'))
    p = os.path.join(P.dir, name + '.jpg')
    bg.save(p, quality=quality, subsampling=0, optimize=True)
    print('%-14s %4dx%-4d %6.1f KB  (light)' % (name, bg.size[0], bg.size[1], os.path.getsize(p) / 1024), flush=True)


def glow_image(c, col, name, quality=88, crop=None):
    c.col = col.astype(F)
    c.alpha[:] = 1
    im = c.image(tone=False)
    if crop:
        w, h = im.size
        im = im.crop((int(w * crop[0]), int(h * crop[1]), int(w * crop[2]), int(h * crop[3])))
    light_jpg(im, name, quality)


def finish(c, body, exposure=1.0):
    """For canvases with a contact shadow: c.col is the lit body times its coverage, c.alpha body and shadow."""
    col = film(np.where(body[..., None] > 1e-3, c.col / np.maximum(body, 1e-3)[..., None], 0) * exposure) * body[..., None]
    s = c.ss
    h, w = c.h // s, c.w // s
    pm = col.reshape(h, s, w, s, 3).mean(axis=(1, 3))
    al = c.alpha.reshape(h, s, w, s).mean(axis=(1, 3))
    out = to_srgb(pm / np.maximum(al, 1e-4)[..., None])
    rgba = np.concatenate([clamp(out), clamp(al)[..., None]], axis=2)
    return Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), 'RGBA')


def sheet(frames, cols):
    w, h = frames[0].size
    rows = (len(frames) + cols - 1) // cols
    s = Image.new('RGBA', (w * cols, h * rows), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        s.paste(f, ((i % cols) * w, (i // cols) * h))
    return s


# ------------------------------------------------------------------ the console
def armour(c):
    """Distances of the six wide plates and the six titanium couplings that lock into them."""
    r = c.R
    t = clamp((r - 0.914) / 0.026)
    dl, k = rep(c.A, 6, 0.0)
    e = (np.abs(dl) - mix(math.radians(24.3), math.radians(20.0), t)) * r
    dM = np.maximum(np.maximum(e * 0.95 + 0.0040, 0.874 - r), r - 0.984)
    dM = np.maximum(dM, (e + (r - 0.984) + 0.034) * 0.7071)
    dM = np.maximum(dM, (e + (0.874 - r) + 0.012) * 0.7071)
    dc, kc = rep(c.A, 6, math.pi / 6)
    e2 = (np.abs(dc) - mix(math.radians(5.7), math.radians(10.0), t)) * r
    dC = np.maximum(np.maximum(e2 * 0.95 + 0.0040, 0.866 - r), r - 1.0)
    dC = np.maximum(dC, (e2 + (r - 1.0) + 0.020) * 0.7071)
    dC = np.maximum(dC, (e2 + (0.866 - r) + 0.010) * 0.7071)
    return dM, dC, dl, k, dc, kc


def plate():
    c = Canvas(P.px(1080), P.ss(2), 1.0)
    r = c.R
    dM, dC, dl, k, dc, kc = armour(c)

    # ---- the tray the bays sit in
    H = np.zeros(c.shape, F) - 0.030
    H = np.maximum(H, np.where(r > 0.842, -0.004, -1))                     # the ledge under the armour
    H = np.where((r > 0.790) & (r <= 0.842), -0.030 + 0.026 * smooth(0.795, 0.838, r), H)
    H = np.where((r > 0.8445) & (r < 0.8575), -0.020, H)                   # light channel
    H = np.maximum(H, np.where((r > 0.856) & (r < 0.872), -0.004 + bevel(np.abs(r - 0.864) - 0.007, 0.004, 0.012, 'chamfer'), -1))
    for rr, w, d in ((0.772, 0.0022, 0.006), (0.500, 0.0022, 0.006), (0.470, 0.010, 0.008)):
        H = H - d * smooth(w, w * 0.4, np.abs(r - rr))
    # spokes in line with the couplings, a honeycomb between them
    ds, _ = rep(c.A, 6, math.pi / 6)
    su = np.abs(ds * r)
    spoke = np.maximum(np.maximum(su - 0.026 - 0.012 * smooth(0.62, 0.78, r), 0.515 - r), r - 0.762)
    H = np.maximum(H, -0.030 + bevel(spoke, 0.006, 0.010, 'chamfer'))
    hd, hx, hy = hexgrid(c.X, c.Y, 0.036)
    hr, ha = np.hypot(hx, hy), np.arctan2(hx, -hy)
    hs, _ = rep(ha, 6, math.pi / 6)
    cells = (hr > 0.535) & (hr < 0.735) & (np.abs(hs * hr) > 0.062)
    hole = np.where(cells, (hd - 0.40) * 0.036, 1.0)
    H = H - 0.014 * smooth(0.0006, -0.0028, hole)
    # scale engraved on the slope
    eng = np.zeros(c.shape, F)
    for n, w, r0, r1 in ((180, 0.0013, 0.812, 0.826), (36, 0.0020, 0.806, 0.830)):
        q = np.abs(rep(c.A, n)[0]) * r
        eng = np.maximum(eng, clamp((w - q) / c.px + 0.5) * (r > r0) * (r < r1))
    for i in range(12):
        low = 3 < i < 9
        eng = np.maximum(eng, c.ring_text('%03d' % (i * 30), 0.026, 0.789, i * TAU / 12, font=FONT, spacing=1.08, inside=low))
    base = H.copy()

    # ---- armour
    HM = np.where(dM < 0, bevel(dM, 0.0085, 0.026, 'chamfer'), -1)
    v = r - 0.930
    u = dl * r
    # a sunken field on every wide plate, with louvres left and right of the middle
    inset = np.maximum(np.maximum(np.abs(u) - 0.292 + 1.9 * clamp(v, 0, 1), np.abs(v) - 0.034), (np.abs(u) + np.abs(v) - 0.300) * 0.7071)
    HM = HM - 0.0065 * smooth(0.0015, -0.0035, inset) * (dM < 0)
    slot = np.full(c.shape, 9, F)
    for side in (-1, 1):
        for i in range(6):
            uu = u - side * (0.150 + i * 0.0215)
            q = uu * 0.94 - side * v * 0.34
            p = side * uu * 0.34 + v * 0.94
            slot = np.minimum(slot, np.hypot(q, np.maximum(np.abs(p) - 0.016, 0)) - 0.0052)
    HM = HM - 0.024 * smooth(0.0008, -0.0030, slot) * (dM < 0)
    # raised middle block on every other plate (the stencilled ones), painted stripes on the rest
    block = np.maximum(np.abs(u) - 0.098 - v * 0.4, np.abs(v) - 0.024)
    HM = np.where((dM < 0) & (k % 2 == 0), np.maximum(HM, 0.0195 + bevel(block, 0.004, 0.0085, 'chamfer') * (block < 0)), HM)
    HC = np.where(dC < 0, 0.010 + bevel(dC, 0.0095, 0.030, 'chamfer'), -1)
    # couplings: a stepped centre, a lamp slot, two scribed lines
    uc = np.abs(dc * r)
    step = np.maximum(uc - 0.052 - 0.35 * clamp(r - 0.93, 0, 1), np.abs(r - 0.944) - 0.040)
    HC = HC + 0.0075 * smooth(0.0015, -0.0045, np.maximum(step, dC + 0.012)) * (dC < 0)
    HC = HC - 0.004 * smooth(0.0016, 0.0004, np.abs(uc - 0.105 - 0.2 * (r - 0.95))) * (dC < -0.010) * (r > 0.945)
    lamp = np.maximum(uc - 0.0075, np.abs(r - 0.893) - 0.0125)
    HC = HC - 0.016 * smooth(0.001, -0.002, lamp) * (dC < 0)
    H = np.maximum(H, np.maximum(HM, HC))
    for i in range(6):
        a = i * TAU / 6
        for da in (-21.2, 21.2):
            x, y = c.polar(a + math.radians(da), 0.8925)
            allen(c, H, x, y, 0.0088, 0.55, a, sink=0.004)
        x, y = c.polar(a + math.pi / 6, 0.948)
        allen(c, H, x, y, 0.0185, 0.45, a + math.pi / 6, sink=0.006)
        for da in (-7.4, 7.4):
            x, y = c.polar(a + math.pi / 6 + math.radians(da), 0.974)
            allen(c, H, x, y, 0.0066, 0.5, 0.2)
        for rr in (0.540, 0.735):
            x, y = c.polar(a + math.pi / 6, rr)
            allen(c, base, x, y, 0.0105, 0.5, a)
            allen(c, H, x, y, 0.0105, 0.5, a)
    lathe = circular_streaks(c, 21, 2000)

    # ---- stripes and stencils (paint)
    chip = fbm(c.shape, 46, 91, 4) + 0.55 * fbm(c.shape, 9, 92, 3)
    ok = smooth(0.95, 0.55, chip)
    band = np.maximum(np.abs(u) - 0.104 + v * 0.5 * np.sign(u), np.abs(v) - 0.0235)
    odd = (k % 2 == 1) & (dM < 0)
    stripe = np.where(((u + v) / 0.034) % 1.0 < 0.5, 1.0, 0.0).astype(F)
    stripe = blur(stripe, 0.6 * c.ss)
    paint = c.cover(band) * odd * ok
    sten = np.zeros(c.shape, F)
    for i, w, sz in ((0, 'SECTOR 1', 0.037), (2, 'LOOP 3', 0.037), (4, 'CORE R6', 0.037)):
        sten = np.maximum(sten, c.ring_text(w, sz, 0.930, i * TAU / 6, font=FONT, spacing=1.10, inside=i > 0))
    sten = sten * smooth(1.1, 0.7, chip)

    # ---- colour
    mM, mC = c.cover(dM), c.cover(dC)
    lip = c.cover(np.abs(r - 0.864) - 0.0075) * (1 - mM) * (1 - mC)
    mT = clamp(1 - mM - mC - lip)
    dark = mix(np.broadcast_to(TRAY, c.shape + (3,)), V([0.016, 0.018, 0.022]), (c.cover(hole) * cells)[..., None])
    dark = mix(dark, np.broadcast_to(V([0.115, 0.122, 0.136]), c.shape + (3,)), c.cover(spoke)[..., None])
    dark = mix(dark, V([0.36, 0.40, 0.44]), (0.60 * eng)[..., None])
    gun = mix(np.broadcast_to(GUN, c.shape + (3,)), V([0.020, 0.022, 0.026]), (c.cover(slot))[..., None])
    gun = mix(gun, GUN * 0.62, (c.cover(inset) * (1 - c.cover(slot)) * 0.75)[..., None])
    tit = mix(np.broadcast_to(TITAN, c.shape + (3,)), V([0.02, 0.05, 0.06]), (c.cover(lamp))[..., None])
    tit = mix(tit, TITAN * 0.72, (c.cover(np.maximum(step, dC + 0.012)) * (1 - c.cover(lamp)) * 0.6)[..., None])
    Hs = H + 0.00042 * lathe * (mT + mM * 0.5 + lip)
    col, ao, sh, nn = look(c, Hs, [(mT, dark, 0.42, 'round', 0.92), (mM * (1 - paint), gun, 0.32, 'round', 0.95), (lip, STEEL2 * 0.8, 0.26, 'round', 0.97), (mC, tit, 0.28, 'round', 0.97)],
                           reach=0.12, slope=0.75, seed=5)
    yel = mix(np.broadcast_to(rgb('#15171A'), c.shape + (3,)), rgb('#E9A60C'), stripe[..., None])
    pcol = shade(ST, *nn, yel * (1 - 0.35 * clamp((1 - ao) * 1.4))[..., None], metal=0.0, rough=0.45, ao=ao, sh=sh, clear=0.10)
    col = col + pcol * paint[..., None]
    wht = shade(ST, *nn, rgb('#C9D4DC'), metal=0.0, rough=0.5, ao=ao, sh=sh)
    col = mix(col, wht, (0.85 * sten * (dM < 0))[..., None])
    s = scratches(c.shape, 12, 190, width=max(1, 0.55 * c.ss), length=(0.02, 0.12))
    col = col * (1 - 0.10 * s[..., None]) + 0.030 * (s * (mM + mC))[..., None]
    hubshade = (0.55 + 0.45 * smooth(0.40, 0.56, r))[..., None]            # the hub stands above the tray
    col = col * hubshade

    # the tray without its armour, for the moment before the plates arrive
    bcol, _, _, _ = look(c, base + 0.00042 * lathe, [(clamp(1 - lip), dark, 0.42, 'round', 0.92), (lip, STEEL2 * 0.8, 0.26, 'round', 0.97)], reach=0.10, slope=0.75, seed=5)
    tcol = mix(bcol * hubshade * 0.55, col, smooth(0.870, 0.866, r)[..., None])
    c.put(tcol, c.cover(r - 0.972))
    P.save(c.image(), 'tray', quality=88)
    for name, d in (('armour', dM), ('coupling', dC)):
        c.col = np.zeros(c.shape + (3,), F)
        c.alpha = np.zeros(c.shape, F)
        c.put(col, c.cover(d))
        P.save(c.image(exposure=1.10), name, quality=88)


# ------------------------------------------------------------------ bays
BAYS, STEP = 20, 3.0        # the same bay turned by 3 degrees each, so the light always comes from the upper left


def bay_one(rot, size, kid=False):
    c = Canvas(size, P.ss(3), 1.0)
    q = hexd(c.X, c.Y, rot)
    e = 0.8660254                                        # measure to true distance
    d = (q - 0.93) * e
    dm, _ = rep(c.A, 6, rot + math.pi / 6)               # from the nearest side's middle
    u = np.abs(c.R * np.sin(dm))                         # along the side
    H = bevel(d, 0.036, 0.060, 'chamfer')
    g0, f0r, f1r = (0.850, 0.800, 0.745) if kid else (0.782, 0.722, 0.654)
    cap = np.maximum(((0.31 if kid else 0.275) - u) * 0.95, (g0 + 0.023 - q) * e)  # negative at the corners
    H = H + 0.022 * smooth(0.0, -0.024, cap) * smooth(0, -0.014, d)
    groove = (np.abs(q - g0) - (0.018 if kid else 0.0145)) * e
    H = np.where(q < g0 - 0.014, 0.050, H)
    H = np.where(groove < 0, 0.026, H)
    H = np.where(q < f0r, 0.050 - (0.085 if kid else 0.130) * clamp((f0r - q) / (f0r - f1r)), H)
    bar = np.maximum(u - 0.085, (np.abs(q - 0.858) - 0.013) * e) if not kid else np.full(c.shape, 9, F)   # light bar in the middle of each side
    H = H - 0.020 * smooth(0.004, -0.004, bar)
    Hs = H + 0.0009 * circular_streaks(c, 8, 900) * (q > f0r)
    floor = smooth(f1r + 0.006, f1r - 0.002, q)
    mCap = c.cover(cap) * c.cover(d)
    mBez = clamp(c.cover(d) - mCap - floor)
    gun = mix(np.broadcast_to(V([0.21, 0.22, 0.245]), c.shape + (3,)), V([0.010, 0.030, 0.036]), clamp(c.cover(groove) + c.cover(bar))[..., None])
    col, ao, sh, nn = look(c, Hs, [(mBez, gun, 0.30, 'round', 0.96), (mCap, TITAN * 1.15, 0.26, 'round', 0.97)], reach=0.34, slope=0.62, ao_r=(0.02, 0.06, 0.14), wear=0.35, seed=31, grime=0.45, fine=0.012)
    # the floor: smoked glass over a dark well
    f0 = mix(np.broadcast_to(rgb('#070C13'), c.shape + (3,)), rgb('#152434'), smooth(0.65, 0.1, c.R)[..., None])
    f0 = f0 * (0.50 + 0.50 * sh)[..., None] * (0.55 + 0.45 * ao)[..., None]
    sheen = smooth(0.12, 0.72, -(c.X * 0.55 + c.Y * 0.83))
    col = col + (f0 + rgb('#7FA6CC') * (0.030 * sheen)[..., None]) * floor[..., None]
    body = c.cover(d)
    sd = blur(shift(body, int(0.022 / c.px), int(0.038 / c.px)), 0.028 / c.px)
    c.col = col * body[..., None]
    c.alpha = np.maximum(body, 0.62 * sd * (1 - body) * smooth(1.0, 0.95, c.R)).astype(F)
    return finish(c, body)


def bays():
    size = P.px(208)
    P.save(sheet([bay_one(math.radians(i * STEP), size) for i in range(BAYS)], 5), 'bay', quality=88, how='jpg')
    size = P.px(136)
    P.save(sheet([bay_one(math.radians(i * STEP), size, True) for i in range(BAYS)], 5), 'cell', quality=88, how='jpg')


def bay_lights():
    """What burns in a bay. None of it depends on where light comes from, so it may simply be turned."""
    size = P.px(256)
    c = Canvas(size, 2, 1.0)
    q = hexd(c.X, c.Y, 0)
    dm, _ = rep(c.A, 6, math.pi / 6)
    u = np.abs(c.R * np.sin(dm))
    bar = np.maximum(u - 0.080, (np.abs(q - 0.858) - 0.004) * 0.866)
    d = np.maximum(np.minimum(np.abs(q - 0.782) * 0.866 - 0.004, bar), 0)
    core = clamp(1 - d / 0.010)
    fade = smooth(1.0, 0.82, c.R)
    glow = gauss(d, 0.030) * 0.75 + gauss(d, 0.085) * 0.30 * fade
    col = rgb('#E9FDFF') * (0.95 * core ** 1.5)[..., None] + rgb('#19D8FF') * (0.85 * glow)[..., None] + rgb('#0B5BFF') * (0.18 * gauss(d, 0.13) * fade)[..., None]
    glow_image(c, col * smooth(1.0, 0.96, c.R)[..., None], 'seam')
    # hologram on the floor
    c = Canvas(size, 2, 1.0)
    q = hexd(c.X, c.Y, 0)
    ins = smooth(0.655, 0.640, q)
    hd, _, _ = hexgrid(c.X, c.Y, 0.150)
    g = 0.55 * clamp((hd - 0.5) / 0.030 + 1.0)
    for rr, w in ((0.62, 0.006), (0.46, 0.004)):
        g = np.maximum(g, clamp((w - np.abs(q - rr)) / c.px + 0.5) * 0.9)
    ax, _ = rep(c.A, 6, 0)
    g = np.maximum(g, clamp((0.004 - np.abs(ax * c.R)) / c.px + 0.5) * (c.R > 0.50) * 0.9)
    soft = blur(g, 2.2 * c.ss)
    fade = smooth(0.05, 0.60, c.R) * 0.75 + 0.25
    glow_image(c, rgb('#58EBFF') * ((g * 0.75 + soft * 0.9) * fade * ins)[..., None], 'holo')
    # a ring of light that runs out over the floor
    c = Canvas(P.px(160), 2, 1.0)
    q = hexd(c.X, c.Y, 0)
    dd = np.abs(q - 0.88) * 0.866
    glow_image(c, (rgb('#4FE6FF') * (gauss(dd, 0.02) * 0.9 + gauss(dd, 0.06) * 0.3)[..., None]) * smooth(1.0, 0.95, c.R)[..., None], 'pulse')
    # the column: standing on the middle of the floor
    c = Canvas(P.px(160), 2, 1.0, aspect=2.0)
    y = (c.Y + 2.0) / 4.0                               # 0 top .. 1 bottom
    foot_y = 0.80
    up = clamp((foot_y - y) / foot_y)
    rays = 0.72 + 0.28 * np.cos(c.X * 23 + 2.0 * np.sin(c.X * 7))
    width = 0.56 + 0.10 * up
    body = np.exp(-(np.abs(c.X) / width) ** 4) * (1 - smooth(0.0, 1.0, up)) ** 1.25 * (y < foot_y) * rays * smooth(1.0, 0.8, np.abs(c.X))
    el = np.hypot(c.X / 0.62, (c.Y - (foot_y * 4 - 2)) / 0.26)
    foot = (gauss(el, 0.85) + 1.2 * gauss(el - 0.95, 0.10)) * smooth(1.0, 0.86, np.abs(c.X))
    k = body * 0.62 + foot * 0.75
    glow_image(c, rgb('#12B8FF') * (k * 0.95)[..., None] + rgb('#C8FBFF') * (0.55 * k ** 2.2)[..., None], 'column')
    c = Canvas(P.px(200), 1, 1.0)
    glow_image(c, rgb('#1AA7FF') * (0.8 * gauss(c.R, 0.50) * smooth(1.0, 0.7, c.R))[..., None], 'halo')


# ------------------------------------------------------------------ hub
R_CH = 0.705           # radius of the reactor chamber, in hub radii


def collar():
    """The ring around the core: emitter track outside, sunken band for readouts, titanium seat for the glass."""
    c = Canvas(P.px(620), P.ss(3), 1.03)
    r = c.R
    H = np.zeros(c.shape, F)
    # outer ring: twelve segments with the track cut into them
    H = np.maximum(H, bevel(np.maximum(r - 0.998, 0.898 - r), 0.012, 0.046, 'chamfer'))
    seg = np.abs(rep(c.A, 12, math.radians(15))[0] * r) - 0.0045
    H = H - 0.014 * smooth(0.003, -0.002, seg) * (r > 0.898)
    track = np.abs(r - 0.9620) - 0.0135
    H = np.where(track < 0, 0.014, H)
    pad = np.maximum(np.abs(rep(c.A, 12)[0] * r) - 0.085, np.abs(r - 0.922) - 0.0125)
    H = H + 0.008 * smooth(0.003, -0.005, pad)
    for i in range(12):
        x, y = c.polar(i * TAU / 12 + math.radians(15 - 5.4), 0.922)
        allen(c, H, x, y, 0.0115, 0.5, 0.3)
        x, y = c.polar(i * TAU / 12 - math.radians(15 - 5.4), 0.922)
        allen(c, H, x, y, 0.0115, 0.5, 0.8)
    band = (r < 0.898) & (r > 0.772)
    H = np.where(band, 0.004, H)
    H = np.where(r <= 0.772, np.maximum(0.0, bevel(np.maximum(r - 0.772, R_CH - r), 0.018, 0.042, 'chamfer')), H)
    notch = np.maximum(np.abs(rep(c.A, 36)[0] * r) - 0.0075, np.abs(r - 0.742) - 0.011)
    H = H - 0.016 * smooth(0.002, -0.004, notch)
    eng = np.zeros(c.shape, F)
    for n, w, r0, r1 in ((120, 0.0017, 0.866, 0.884), (24, 0.0030, 0.858, 0.886)):
        q = np.abs(rep(c.A, n)[0]) * r
        eng = np.maximum(eng, clamp((w - q) / c.px + 0.5) * (r > r0) * (r < r1))
    gauge = np.full(c.shape, 9, F)
    for mid in (math.radians(147), math.radians(-147)):
        gauge = np.minimum(gauge, np.maximum((np.abs(near(c.A, mid)) - math.radians(19.0)) * r, np.abs(r - 0.826) - 0.020))
    H = H - 0.012 * smooth(0.002, -0.004, gauge)
    txt = np.maximum(c.ring_text('CPU', 0.078, 0.826, math.radians(187.0), font=FONT, inside=True), c.ring_text('RAM', 0.078, 0.826, math.radians(173.0), font=FONT, inside=True))
    Hs = H + 0.0007 * circular_streaks(c, 63, 1400)
    mBand = band.astype(F)
    mSeat = ((r <= 0.772) & (notch > 0)).astype(F)
    mRest = clamp(1 - mBand - mSeat)
    bandc = mix(np.broadcast_to(V([0.048, 0.055, 0.066]), c.shape + (3,)), V([0.42, 0.47, 0.52]), (0.60 * eng)[..., None])
    bandc = mix(bandc, V([0.006, 0.010, 0.014]), c.cover(gauge)[..., None])
    gun = mix(np.broadcast_to(V([0.235, 0.245, 0.270]), c.shape + (3,)), V([0.36, 0.365, 0.38]), c.cover(pad)[..., None])
    gun = mix(gun, V([0.010, 0.016, 0.020]), clamp(c.cover(track) + (notch <= 0) * (r <= 0.772))[..., None])
    col, ao, sh, nn = look(c, Hs, [(mBand, bandc, 0.45, 'round', 0.85), (mSeat, TITAN, 0.26, 'round', 0.97), (mRest, gun, 0.30, 'round', 0.96)], reach=0.16, slope=0.8,
                           ao_r=(0.010, 0.03, 0.08), seed=44, wear=0.30, grime=0.5, fine=0.008)
    col = mix(col, rgb('#A9D2E6') * 0.75, (0.9 * txt)[..., None])
    c.put(col, c.cover(np.maximum(r - 0.998, R_CH - r)), H)
    P.save(c.image(exposure=1.08), 'collar', quality=90)


def blade(i, size):
    """One of six shutters that slide apart to a hexagon; drawn where it stands at aperture 0.28."""
    r0 = 0.28
    c = Canvas(size, P.ss(3), 1.0)
    a = math.radians(i * 60 + 90)                        # direction of its corner of the opening
    vx, vy = c.polar(a, r0)
    x, y = c.X - vx, c.Y - vy
    inward = c.polar(a - math.radians(90), 1.0)          # the blade leaves its corner this way

    def outside(deg):
        ex, ey = c.polar(a - math.radians(deg), 1.0)
        nx_, ny_ = ey, -ex
        if inward[0] * nx_ + inward[1] * ny_ > 0:
            nx_, ny_ = -nx_, -ny_
        return x * nx_ + y * ny_, x * ex + y * ey
    s1, _ = outside(60)                                  # distance outside the edge that butts under the neighbour
    s2, along = outside(120)                             # ... outside the free edge, and the way along it
    d = np.maximum(np.maximum(s1, s2), c.R - 0.735)
    H = np.zeros(c.shape, F) + 0.030
    H = H - 0.026 * smooth(-0.046, 0.0, s2) ** 1.4       # sharpened toward the opening
    H = H - 0.006 * smooth(0.004, -0.003, np.abs(s2 + 0.066) - 0.0035)
    rib = np.maximum(np.abs(s2 + 0.150) - 0.028, np.abs(along - 0.50) - 0.24)
    H = H - 0.012 * smooth(0.003, -0.005, rib)
    for k in range(3):
        H = H - 0.010 * smooth(0.002, -0.003, np.abs(s2 + 0.150) - 0.006) * (np.abs(along - 0.36 - 0.14 * k) < 0.045)
    under = smooth(0.0, -0.10, s1)                       # shadow of the neighbour lying over this blade
    Hs = H + 0.0004 * streaks1(s2, 5 + i)
    alb = mix(np.broadcast_to(V([0.30, 0.31, 0.335]), c.shape + (3,)), V([0.10, 0.105, 0.120]), c.cover(rib)[..., None])
    col, ao, sh, nn = look(c, Hs, [(np.ones(c.shape, F), alb, 0.30, None, 0.97)], reach=0.10, slope=0.8, ao_r=(0.012, 0.04), seed=70, wear=0.10, grime=0.30, fine=0.010)
    col = col * (0.22 + 0.78 * under)[..., None]
    lip = smooth(-0.012, -0.004, s2) * smooth(0.002, -0.002, s2)
    col = col + rgb('#9FE8FF') * (0.30 * lip * smooth(-0.1, 0.1, along))[..., None]
    c.put(col, c.cover(d), H)
    return c.image(exposure=1.15)


def iris():
    size = P.px(300)
    P.save(sheet([blade(i, size) for i in range(6)], 3), 'iris', quality=88, how='jpg')


def value2(x, y, seed):
    g = rng(seed).standard_normal((128, 128)).astype(F)
    xi, yi = np.floor(x).astype(np.int32), np.floor(y).astype(np.int32)
    fx, fy = x - xi, y - yi
    fx, fy = fx * fx * fx * (fx * (fx * 6 - 15) + 10), fy * fy * fy * (fy * (fy * 6 - 15) + 10)

    def at(i, j):
        return g[(yi + j) % 128, (xi + i) % 128]
    return (at(0, 0) * (1 - fx) + at(1, 0) * fx) * (1 - fy) + (at(0, 1) * (1 - fx) + at(1, 1) * fx) * fy


def stirred(c, seed, freq=3, twist=2.2, octaves=5):
    """Noise wound around the centre like something stirred."""
    a = c.A + twist * np.log(np.maximum(c.R, 0.02))
    x, y = np.sin(a) * c.R, -np.cos(a) * c.R
    out = np.zeros(c.shape, F)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        s = freq * 2 ** o
        out += amp * value2(x * s + 31.7 * o, y * s - 12.3 * o, seed + o)
        tot += amp
        amp *= 0.55
    return out / tot


def plasma():
    size = P.px(330)
    c = Canvas(size, 2, 1.0)
    k = smooth(-0.35, 0.85, stirred(c, 11, 2.2, 1.7, 5) + 0.45 * stirred(c, 47, 3.4, -1.1, 4))
    lum = (0.10 + 0.95 * k ** 1.7) * (0.30 + 0.95 * gauss(c.R, 0.46)) * smooth(1.0, 0.82, c.R)
    glow_image(c, rgb('#0B4BFF') * (0.85 * lum)[..., None] + rgb('#10C8FF') * (0.85 * lum ** 1.6)[..., None] + rgb('#DFFBFF') * (0.60 * lum ** 3.2)[..., None], 'plasma', 86)
    c = Canvas(size, 2, 1.0)
    k = clamp(1 - np.abs(stirred(c, 83, 2.6, -2.6, 5)) / 0.17) ** 3.0 + 0.55 * clamp(1 - np.abs(stirred(c, 129, 4.6, -1.9, 4)) / 0.13) ** 3.0
    k = k * smooth(1.0, 0.70, c.R) * smooth(0.02, 0.30, c.R)
    glow_image(c, rgb('#1AB4FF') * (0.62 * k)[..., None] + rgb('#D8FBFF') * (0.55 * k ** 2)[..., None], 'filament', 86)
    c = Canvas(P.px(260), 1, 1.0)
    k = (gauss(c.R, 0.22) * 0.9 + gauss(c.R, 0.52) * 0.42) * smooth(1.0, 0.75, c.R)
    glow_image(c, rgb('#1B9DFF') * (k * 0.9)[..., None] + rgb('#E8FDFF') * (0.95 * k ** 2)[..., None], 'heart')


def dome_glass():
    """Thick glass over the chamber: a dark rim, a window reflected at the upper left, a thin bounce at the lower right."""
    c = Canvas(P.px(380), 2, 1.0)
    r = c.R
    ins = smooth(1.0, 0.985, r)
    ax, ay = c.X + 0.07, c.Y + 0.10
    rr, ang = np.hypot(ax, ay), np.arctan2(ax, -ay)
    win = smooth(0.62, 0.70, rr) * (1 - smooth(0.86, 0.93, rr)) * smooth(1.05, 0.55, np.abs(near(ang, -0.62)))
    bar = 1 - 0.7 * gauss(ang + 0.50, 0.035)
    thin = gauss(r - 0.955, 0.018) * smooth(1.3, 0.4, np.abs(near(c.A, 2.40))) * 0.55 + gauss(r - 0.965, 0.012) * smooth(1.6, 0.5, np.abs(near(c.A, -0.72))) * 0.5
    light = win * bar * 0.26 + thin
    dark = (smooth(0.62, 1.0, r) ** 2.2) * 0.72
    tot = np.maximum(light + dark * (1 - light), 1e-4)
    c.col = from_srgb(np.ones(c.shape + (3,), F) * (light / tot)[..., None] * np.array([0.88, 0.96, 1.0], F))
    c.alpha = (clamp(light + dark * (1 - light)) * ins).astype(F)
    P.save(c.image(tone=False), 'dome', how='png')


def emitter():
    """The carriage that runs on the collar's track: 24 directions, so it keeps its light."""
    out = []
    for i in range(24):
        c = Canvas(P.px(84), P.ss(4), 1.0)
        a = i * TAU / 24
        cs, sn = math.cos(-a), math.sin(-a)
        x, y = c.X * cs - c.Y * sn, c.X * sn + c.Y * cs   # y: -1 is outward
        body = np.maximum(np.abs(x) - 0.62 + 0.28 * clamp(-(y + 0.10), 0, 1), np.abs(y + 0.02) - 0.40)
        body = np.maximum(body, (np.abs(x) + np.abs(y) - 0.88) * 0.7071)
        nose = np.maximum(np.abs(x) - 0.26 - 0.30 * clamp(y + 0.75, 0, 1), np.maximum(-y - 0.86, y + 0.30))
        d = np.minimum(body, nose)
        H = bevel(d, 0.13, 0.16, 'chamfer')
        H = np.maximum(H, np.where(body < 0, bevel(body, 0.13, 0.20, 'chamfer'), 0))
        ll = np.hypot(x, y + 0.02)
        lens = ll - 0.205
        H = np.where(lens < 0.055, 0.16, H)
        H = np.where(lens < 0, 0.10 + dome(ll, 0.205, 0.10), H)
        slit = np.maximum(np.abs(x) - 0.07, np.abs(y + 0.66) - 0.13)
        H = H - 0.07 * smooth(0.02, -0.03, slit)
        mL = c.cover(lens)
        alb = mix(np.broadcast_to(TITAN, c.shape + (3,)), V([0.02, 0.10, 0.13]), clamp(mL + c.cover(slit))[..., None])
        col, ao, sh, nn = look(c, H, [(1 - mL, alb, 0.28, None, 0.97), (mL, alb, 0.12, None, 0.3)], reach=0.4, slope=0.7, ao_r=(0.04, 0.12), wear=0.3, seed=19, grime=0.15, fine=0.03)
        col = col + rgb('#26DFFF') * (0.9 * mL * (0.25 + 0.9 * gauss(ll, 0.13)))[..., None]
        bodyc = c.cover(d)
        sd = blur(shift(bodyc, int(0.05 / c.px), int(0.09 / c.px)), 0.06 / c.px)
        c.col = col * bodyc[..., None]
        c.alpha = np.maximum(bodyc, 0.55 * sd * (1 - bodyc)).astype(F)
        out.append(finish(c, bodyc, 1.9))
    P.save(sheet(out, 6), 'emitter', quality=90, how='jpg')


def badges():
    """Small parts that are turned with their bay, so they are lit from everywhere alike."""
    # group: an amber double arrow on a dark tab
    c = Canvas(P.px(72), 4, 1.0)
    d = np.maximum(np.maximum(np.abs(c.X) - 0.80 + 0.42 * clamp(0.1 - c.Y, 0, 1), np.abs(c.Y) - 0.74), (np.abs(c.X) + np.abs(c.Y) - 1.16) * 0.7071)
    body = c.cover(d)
    rim = c.cover(np.abs(d + 0.07) - 0.055)
    col = mix(np.broadcast_to(rgb('#0B1118'), c.shape + (3,)), rgb('#8496A6'), rim[..., None])
    ch = np.full(c.shape, 9, F)
    for y0 in (-0.36, 0.06):
        ch = np.minimum(ch, np.maximum(np.abs(c.Y - y0 - 0.62 * np.abs(c.X) - 0.02) - 0.115, np.abs(c.X) - 0.40))
    k = c.cover(ch)
    glow = gauss(np.maximum(ch, 0), 0.16) * (d < -0.1)
    col = mix(col, rgb('#FFC14A'), k[..., None]) + rgb('#FF9A10') * (0.35 * glow)[..., None]
    c.put(col, body)
    P.save(c.image(tone=False), 'arrow', how='png')
    # number plate
    c = Canvas(P.px(72), 4, 1.0)
    q = hexd(c.X, c.Y, math.pi / 6)
    d = (q - 0.92) * 0.866
    rim = c.cover(np.abs(d + 0.075) - 0.060)
    col = mix(np.broadcast_to(rgb('#0A121B'), c.shape + (3,)), rgb('#35CFE6'), rim[..., None])
    c.put(col, c.cover(d))
    P.save(c.image(tone=False), 'plate9', how='png')
    # pilot lamps
    for name, base in (('led', '#2BDDF5'), ('led_on', '#FFB020')):
        c = Canvas(P.px(48), 4, 1.0)
        col = np.broadcast_to(rgb('#06090D'), c.shape + (3,))
        rim = c.cover(np.abs(c.R - 0.76) - 0.11)
        col = mix(col, rgb('#6F7F8D'), rim[..., None])
        lens = c.cover(c.R - 0.60)
        lit = 0.55 + 0.9 * gauss(np.hypot(c.X + 0.14, c.Y + 0.14), 0.32)
        col = mix(col, rgb(base) * lit[..., None] + 0.35 * gauss(np.hypot(c.X + 0.2, c.Y + 0.2), 0.16)[..., None], lens[..., None])
        c.put(col, c.cover(c.R - 0.90))
        P.save(c.image(tone=False), name, how='png')


def panels():
    """A frame to be cut in nine: cut corners with bolted titanium caps, a thin light all around, dark glass inside."""
    M = 0.10                                              # room for the shadow
    c = Canvas(P.px(256), P.ss(3), 1.0)
    ax, ay = np.abs(c.X), np.abs(c.Y)
    d = np.maximum(np.maximum(ax, ay) - (1 - M), (ax + ay - (2 - 2 * M - 0.20)) * 0.7071)
    H = bevel(d, 0.030, 0.045, 'chamfer')
    cap = np.maximum((1.42 - (ax + ay)) * 0.7071, d + 0.022)
    H = H + 0.020 * smooth(0.0, -0.020, cap)
    inner = d + 0.150
    groove = np.abs(d + 0.122) - 0.007
    H = np.where(groove < 0, 0.022, H)
    H = np.where(inner < 0, 0.045 - 0.030 * clamp(-inner / 0.030), H)
    for sx in (-1, 1):
        for sy in (-1, 1):
            allen(c, H, sx * 0.752, sy * 0.752, 0.030, 0.5, 0.2 + sx)
    glass = c.cover(inner + 0.030)
    mCap = c.cover(cap) * (1 - glass)
    mF = clamp(c.cover(d) - mCap - glass)
    gun = mix(np.broadcast_to(V([0.17, 0.18, 0.205]), c.shape + (3,)), V([0.01, 0.04, 0.05]), c.cover(groove)[..., None])
    col, ao, sh, nn = look(c, H, [(mF, gun, 0.32, None, 0.96), (mCap, TITAN, 0.28, None, 0.97)], reach=0.16, slope=0.7, ao_r=(0.015, 0.05), seed=52, wear=0.25, grime=0.4, fine=0.012)
    t = clamp(c.Y * 0.5 + 0.5)[..., None]
    col = col + (rgb('#1D2A38') * (1 - t) + rgb('#0C131B') * t) * (glass * (0.55 + 0.45 * smooth(0.0, 0.10, -(inner + 0.03))))[..., None]
    gl = gauss(np.maximum(groove + 0.003, 0), 0.009) * 0.9 + gauss(np.maximum(groove, 0), 0.030) * 0.16
    col = col + rgb('#1CCBEF') * (gl * smooth(1.42, 1.30, ax + ay))[..., None]
    body = c.cover(d)
    sd = blur(shift(body, int(0.012 / c.px), int(0.030 / c.px)), 0.040 / c.px)
    c.col = col * body[..., None]
    c.alpha = np.maximum(body, 0.60 * sd * (1 - body)).astype(F)
    P.save(finish(c, body, 1.1), 'panel', quality=88, how='jpg')


def cursor():
    c = Canvas(64, P.ss(4), 1.0)
    pts = [(-0.80, -0.88), (-0.80, 0.52), (-0.42, 0.24), (-0.16, 0.86), (0.16, 0.73), (-0.09, 0.14), (0.40, 0.10)]
    d = c.poly(pts)
    H = bevel(d, 0.10, 0.12, 'chamfer')
    col, ao, sh, nn = look(c, H, [(np.ones(c.shape, F), TITAN * 1.2, 0.26, None, 0.97)], reach=0.2, slope=0.8, ao_r=(0.04,), wear=0.2, seed=9, grime=0.2, fine=0.03)
    core = c.cover(np.maximum(d + 0.155, np.abs(c.X + 0.48 + 0.0 * c.Y) - 0.6))
    col = mix(col, rgb('#28E0FF') * 1.2, (0.95 * core)[..., None])
    body = c.cover(d - 0.035)
    edge = c.cover(d)
    col = col * edge[..., None] + rgb('#05080C') * (1 - edge)[..., None]
    sd = blur(shift(body, int(0.05 / c.px), int(0.08 / c.px)), 0.06 / c.px)
    c.col = col * body[..., None]
    c.alpha = np.maximum(body, 0.5 * sd * (1 - body)).astype(F)
    P.save(finish(c, body, 1.2), 'cursor', how='png')


def subset(src, dst, keep):
    """Writes a TrueType font with only the wanted characters (its licence allows that; it has no reserved name)."""
    import struct
    d = open(src, 'rb').read()
    n = struct.unpack('>H', d[4:6])[0]
    T = {}
    for i in range(n):
        tag, _, off, ln = struct.unpack('>4sIII', d[12 + 16 * i:28 + 16 * i])
        T[tag] = d[off:off + ln]
    nglyph = struct.unpack('>H', T[b'maxp'][4:6])[0]
    longloc = struct.unpack('>h', T[b'head'][50:52])[0]
    loca = list(struct.unpack('>%dI' % (nglyph + 1), T[b'loca'][:4 * (nglyph + 1)])) if longloc else [2 * v for v in struct.unpack('>%dH' % (nglyph + 1), T[b'loca'][:2 * (nglyph + 1)])]
    cm = T[b'cmap']
    chars = {}
    for i in range(struct.unpack('>H', cm[2:4])[0]):
        pid, eid, off = struct.unpack('>HHI', cm[4 + 8 * i:12 + 8 * i])
        if struct.unpack('>H', cm[off:off + 2])[0] != 4:
            continue
        seg = struct.unpack('>H', cm[off + 6:off + 8])[0] // 2
        rd = lambda at: struct.unpack('>%dH' % seg, cm[at:at + 2 * seg])
        end, start, delta, ro = rd(off + 14), rd(off + 16 + 2 * seg), rd(off + 16 + 4 * seg), rd(off + 16 + 6 * seg)
        for k in range(seg):
            for ch in range(start[k], end[k] + 1):
                if ch == 0xFFFF:
                    continue
                if ro[k] == 0:
                    g = (ch + delta[k]) & 0xFFFF
                else:
                    at = off + 16 + 6 * seg + 2 * k + ro[k] + 2 * (ch - start[k])
                    g = struct.unpack('>H', cm[at:at + 2])[0]
                    g = (g + delta[k]) & 0xFFFF if g else 0
                if g:
                    chars[ch] = g
    chars = {c: g for c, g in chars.items() if keep(c)}
    need, todo = {0}, list(set(chars.values()))
    while todo:
        g = todo.pop()
        if g in need:
            continue
        need.add(g)
        b = T[b'glyf'][loca[g]:loca[g + 1]]
        if len(b) > 10 and struct.unpack('>h', b[:2])[0] < 0:    # made of other glyphs
            at = 10
            while True:
                fl, sub = struct.unpack('>HH', b[at:at + 4])
                todo.append(sub)
                at += 4 + (4 if fl & 1 else 2) + (2 if fl & 8 else 4 if fl & 0x40 else 8 if fl & 0x80 else 0)
                if not fl & 0x20:
                    break
    glyf, off = b'', [0]
    for g in range(nglyph):
        if g in need:
            b = T[b'glyf'][loca[g]:loca[g + 1]]
            glyf += b + b'\0' * (-len(b) % 4)
        off.append(len(glyf))
    T[b'glyf'], T[b'loca'] = glyf, struct.pack('>%dI' % len(off), *off)
    T[b'head'] = T[b'head'][:8] + b'\0\0\0\0' + T[b'head'][12:50] + struct.pack('>h', 1) + T[b'head'][52:]
    T[b'post'] = struct.pack('>I', 0x00030000) + T[b'post'][4:32]
    cs = sorted(chars)
    runs = []
    for ch in cs:
        if runs and ch == runs[-1][1] + 1 and chars[ch] - chars[runs[-1][0]] == ch - runs[-1][0]:
            runs[-1][1] = ch
        else:
            runs.append([ch, ch])
    runs.append([0xFFFF, 0xFFFF])
    m = len(runs)
    lg = int(math.log2(m))
    body = struct.pack('>HHHH', m * 2, 2 * 2 ** lg, lg, 2 * m - 2 * 2 ** lg) + struct.pack('>%dH' % m, *[r[1] for r in runs]) + b'\0\0' + struct.pack('>%dH' % m, *[r[0] for r in runs])
    body += struct.pack('>%dH' % m, *[((chars[r[0]] - r[0]) & 0xFFFF) if r[0] != 0xFFFF else 1 for r in runs]) + b'\0\0' * m
    T[b'cmap'] = struct.pack('>HHHHI', 0, 1, 3, 1, 12) + struct.pack('>HHH', 4, len(body) + 6, 0) + body
    for t in (b'DSIG', b'FFTM', b'GDEF', b'GPOS', b'GSUB'):
        T.pop(t, None)

    def csum(b):
        b += b'\0' * (-len(b) % 4)
        return sum(struct.unpack('>%dI' % (len(b) // 4), b)) & 0xFFFFFFFF
    tags = sorted(T)
    k = int(math.log2(len(tags)))
    out = struct.pack('>IHHHH', 0x00010000, len(tags), 16 * 2 ** k, k, 16 * len(tags) - 16 * 2 ** k)
    at, data = 12 + 16 * len(tags), b''
    for t in tags:
        out += struct.pack('>4sIII', t, csum(T[t]), at + len(data), len(T[t]))
        data += T[t] + b'\0' * (-len(T[t]) % 4)
    whole = bytearray(out + data)
    h = [struct.unpack('>4sIII', out[12 + 16 * i:28 + 16 * i]) for i in range(len(tags))]
    hoff = [x[2] for x in h if x[0] == b'head'][0]
    whole[hoff + 8:hoff + 12] = struct.pack('>I', (0xB1B0AFBA - csum(bytes(whole))) & 0xFFFFFFFF)
    open(dst, 'wb').write(bytes(whole))
    print('%-14s %d characters %6.1f KB' % (os.path.basename(dst), len(chars), len(whole) / 1024))


def font():
    subset(FONT, os.path.join(P.dir, 'Rajdhani-SemiBold.ttf'), lambda c: c < 0x250 or 0x2010 <= c <= 0x2044 or c in (0x20AC, 0x2122, 0x2190, 0x2192, 0x2212))
    shutil.copy(os.path.join(os.path.dirname(FONT), 'OFL.txt'), os.path.join(P.dir, 'OFL.txt'))


# ------------------------------------------------------------------ light
def lights():
    # seams of the armour: the channel inside it, gaps between the plates, lamps in the couplings
    c = Canvas(P.px(860), 2, 1.0)
    dM, dC, dl, k, dc, kc = armour(c)
    r = c.R
    ch = np.maximum(np.maximum(np.abs(r - 0.851) - 0.0030, (math.radians(7.2) - np.abs(dc)) * r), 0)
    la = np.maximum(np.maximum(np.abs(dc * r) - 0.0042, np.abs(r - 0.893) - 0.0095), 0)
    between = np.minimum(dM, dC)                          # positive in the gaps
    ga = np.maximum(np.maximum(0.0012 - between, np.maximum(0.882 - r, r - 0.972)), 0)
    core = clamp(1 - ch / 0.004) + clamp(1 - la / 0.004) + 0.40 * clamp(1 - ga / 0.003)
    glow = gauss(ch, 0.010) * 0.75 + gauss(ch, 0.030) * 0.17 + gauss(la, 0.012) * 0.9 + gauss(la, 0.030) * 0.24 + gauss(ga, 0.008) * 0.36
    glow_image(c, rgb('#DFFBFF') * (0.80 * clamp(core))[..., None] + rgb('#16CFFF') * (0.80 * clamp(glow, 0, 1.4))[..., None], 'seams', 86)
    # a stretch of the channel burning brighter, turned toward the selection
    c = Canvas(P.px(520), 2, 1.0)
    r = c.R
    w = np.exp(-(c.A / math.radians(17)) ** 2)
    ch = np.maximum(np.abs(r - 0.851) - 0.003, 0)
    k = (gauss(ch, 0.008) + gauss(ch, 0.028) * 0.55 + gauss(ch, 0.075) * 0.30) * w
    glow_image(c, rgb('#1FC9FF') * k[..., None] + rgb('#E6FCFF') * (0.8 * clamp(1 - ch / 0.004) * w)[..., None], 'sector', 88, crop=(0.18, 0.0, 0.82, 0.22))
    # sweep: a slow radar fan on the tray
    c = Canvas(P.px(420), 1, 1.0)
    a = (c.A % TAU) / TAU
    zone = smooth(0.985, 0.97, c.R) * smooth(0.50, 0.56, c.R)
    glow_image(c, rgb('#18B8FF') * ((0.34 * clamp((a - 0.80) / 0.20) ** 2.2 + 0.5 * gauss((1 - a) * TAU * c.R, 0.008)) * zone)[..., None], 'sweep', 84)
    # beam from the emitter into the bay
    c = Canvas(P.px(64), 2, 1.0, aspect=3.0)
    y = (c.Y + 3.0) / 6.0
    k = (gauss(c.X, 0.07) + 0.5 * gauss(c.X, 0.22) + 0.22 * gauss(c.X, 0.45)) * smooth(0.0, 0.45, y) * smooth(1.0, 0.985, y) * smooth(1, 0.8, np.abs(c.X))
    glow_image(c, rgb('#22D4FF') * (0.9 * k)[..., None] + rgb('#FFFFFF') * (0.7 * gauss(c.X, 0.06) * smooth(0.2, 0.9, y))[..., None], 'beam')
    # shock wave and flash of a launch
    c = Canvas(P.px(420), 1, 1.0)
    d = c.R - 0.86
    k = (gauss(d, 0.020) * 0.9 + gauss(d, 0.07) * 0.5 + np.where(d < 0, np.exp(np.minimum(d, 0) / 0.16) * 0.28, 0)) * smooth(1.0, 0.94, c.R)
    glow_image(c, rgb('#1FBEFF') * k[..., None] + rgb('#F0FDFF') * (0.8 * gauss(d, 0.014))[..., None], 'shock', 86)
    c = Canvas(P.px(220), 1, 1.0)
    k = (gauss(c.R, 0.20) + 0.45 * gauss(c.R, 0.48) + 0.5 * gauss(c.Y, 0.018) * gauss(c.X, 0.55)) * smooth(1.0, 0.8, c.R)
    glow_image(c, rgb('#2FB8FF') * k[..., None] + rgb('#FFFFFF') * (0.9 * k ** 2)[..., None], 'flash')
    c = Canvas(P.px(40), 2, 1.0)
    k = (gauss(c.R, 0.22) + 0.35 * gauss(c.R, 0.5)) * smooth(1, 0.7, c.R)
    glow_image(c, rgb('#36D6FF') * k[..., None] + rgb('#FFFFFF') * (gauss(c.R, 0.16) * 0.9)[..., None], 'spark', 90)
    # running data around the core: short dashes
    c = Canvas(P.px(420), 2, 1.0)
    r = c.R
    k = np.zeros(c.shape, F)
    rr = rng(5)
    for ring, n in ((0.955, 90), (0.905, 60)):
        d, i = rep(c.A, n)
        on = rr.random(n) > 0.45
        w = np.where(rr.random(n) > 0.8, 0.40, 0.26)[i]
        bit = np.maximum((np.abs(d) / (TAU / n) - w) * (TAU / n) * r, np.abs(r - ring) - 0.011)
        k = np.maximum(k, clamp(0.5 - bit / c.px) * on[i] * (0.45 + 0.55 * rr.random(n)[i]))
    glow_image(c, rgb('#4DE3FF') * (0.75 * k + 0.5 * blur(k, 2.5 * c.ss))[..., None], 'data', 86)


P.run([plate, bays, bay_lights, collar, iris, plasma, dome_glass, emitter, badges, panels, cursor, font, lights])
P.sounds('reactor')
P.finish()
