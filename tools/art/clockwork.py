"""Clockwork: walnut, brass, porcelain and a clock that keeps time."""
import sys
from metals import *
from pack import Pack

P = Pack('clockwork', sys.argv)
ST = WARM


def plate():
    c = Canvas(P.px(1100), P.ss(2), 1.0)
    wcol, wh = wood(c, 11, 1.25, '#7A4A28', '#2A160B', 6.5, rot=0.35, ring=7.0)
    field = (c.R > 0.40) & (c.R < 0.865)
    H = np.zeros(c.shape, F)
    H = H + wh * 0.0016 * field
    # brass rim: outer torus, flat degree scale, inner bead
    H = np.maximum(H, bevel(np.abs(c.R - 0.962) - 0.034, 0.034, 0.040))
    H = np.maximum(H, np.where((c.R > 0.865) & (c.R < 0.935), 0.016, 0))
    H = np.maximum(H, bevel(np.abs(c.R - 0.874) - 0.011, 0.011, 0.024))
    # engraved degree scale
    eng = np.zeros(c.shape, F)
    for n, w, r0, r1 in ((120, 0.0016, 0.893, 0.915), (24, 0.0026, 0.889, 0.926)):
        a = c.A + math.pi / n
        q = np.abs((a % (TAU / n)) - math.pi / n) * c.R
        eng = np.maximum(eng, clamp((w - q) / c.px + 0.5) * (c.R > r0) * (c.R < r1))
    H = H - 0.010 * blur(eng, 0.6 * c.ss)
    H = rivets(c, H, 24, 0.962, 0.0135, 0.038, phase=TAU / 48)
    # inlaid brass lines in the wood
    inlay = np.minimum(np.abs(c.R - 0.835), np.abs(c.R - 0.455)) - 0.0045
    star = np.full(c.shape, 9, F)
    inl = c.cover(inlay)
    H = H + 0.003 * inl
    H = np.maximum(H, bevel(np.abs(c.R - 0.415) - 0.022, 0.022, 0.030))
    lathe = circular_streaks(c, 4, 1800)
    metal_mask = ((c.R >= 0.863) | (c.R <= 0.437)).astype(F)
    metal_mask = np.maximum(blur(metal_mask, 0.7), inl)
    H = H + 0.00045 * lathe * metal_mask
    alb = mix(wcol * 1.0, np.broadcast_to(BRASS, c.shape + (3,)), metal_mask[..., None])
    nx, ny, nz = normals(H, c.px)
    ao = occlusion(H, c.px, (0.006, 0.02, 0.05), 1.3)
    sh = cast(H, c.px, reach=0.14, slope=0.7)
    g = fbm(c.shape, 8, 5, 5)
    cav = clamp((1 - ao) * 1.8 + 0.12 * clamp(g))
    alb = mix(alb, rgb('#170D05'), clamp(0.62 * cav * (0.35 + 0.65 * metal_mask))[..., None])
    alb = mix(alb, rgb('#1E1208'), (0.75 * eng)[..., None])
    tx, ty = np.cos(c.A), np.sin(c.A)
    m = metal_mask
    gold = shade(ST, nx, ny, nz, alb, metal=0.97, rough=0.24, ao=ao, sh=sh, aniso=(tx, ty, (0.42 * m)[..., None]))
    lacq = shade(ST, nx, ny, nz, alb * 1.5, metal=0.0, rough=0.35, spec=0.04, ao=ao, sh=sh, clear=0.55)
    col = mix(lacq, gold, m[..., None])
    s = scratches(c.shape, 8, 150, width=1.2)
    col = col * (1 - 0.10 * s[..., None])
    # vignette toward the hub: the hub casts a soft shadow
    c.put(col, c.cover(c.R - 0.995), H)
    P.save(c.image(exposure=0.98), 'plate')


def gear(name, teeth, spokes, seed, alb=BRASS, size=420, duty=0.50):
    c = Canvas(P.px(size), P.ss(2), 1.0)
    depth = 0.105 * 28 / teeth + 0.02
    r = 0.94 - depth * 0.5
    d = c.gear(teeth, r, depth, duty=duty)
    body = np.maximum(d, (r - depth - 0.15) - c.R)
    arms = np.full(c.shape, 9, F)
    for i in range(spokes):
        a = i * TAU / spokes
        x0, y0 = c.polar(a, 0.16)
        x1, y1 = c.polar(a, r - depth - 0.06)
        arms = np.minimum(arms, c.taper(x0, y0, 0.075, x1, y1, 0.045))
    hub = c.R - 0.235
    all_ = smin(smin(body, arms, 0.06), hub, 0.05)
    bore = 0.070 - c.R
    all_ = np.maximum(all_, bore)
    H = bevel(all_, 0.028, 0.050)
    H = np.maximum(H, np.where(c.R < 0.21, bevel(np.maximum(c.R - 0.20, bore), 0.03, 0.085), 0))
    H = H - 0.014 * smooth(0.016, 0.006, np.abs(c.R - (r - depth - 0.045)))
    H = H - 0.010 * smooth(0.012, 0.004, np.abs(c.R - 0.165))
    H = H + 0.0010 * circular_streaks(c, seed, 900)
    col = metal(c, H, alb, rough=0.26, aniso=(np.cos(c.A), np.sin(c.A), V(0.42)), grime=0.62, seed=seed, scratch=40)
    c.put(col, c.cover(all_), H)
    P.save(c.image(), name)


def socket():
    c = Canvas(P.px(256), P.ss(3), 1.0)
    H = np.zeros(c.shape, F)
    H = np.maximum(H, bevel(np.maximum(c.R - 0.985, 0.80 - c.R), 0.085, 0.095))
    H = np.where(c.R < 0.815, -0.10 + 0.10 * smooth(0.72, 0.815, c.R), H)
    kn = 0.5 + 0.5 * np.cos(c.A * 48)
    H = H + 0.020 * kn * gauss(c.R - 0.955, 0.026)
    H = H + 0.0012 * circular_streaks(c, 19, 600)
    inner = smooth(0.80, 0.78, c.R)
    alb = mix(np.broadcast_to(BRASS, c.shape + (3,)), np.broadcast_to(rgb('#1A110B'), c.shape + (3,)), inner[..., None])
    felt = fbm(c.shape, 60, 3, 3)
    alb = alb * (1 + 0.35 * felt * inner)[..., None]
    nx, ny, nz = normals(H, c.px)
    ao = occlusion(H, c.px, (0.03, 0.09, 0.18), 1.2)
    sh = cast(H, c.px, reach=0.45, slope=0.55)
    col = shade(ST, nx, ny, nz, alb, metal=0.97 * (1 - inner), rough=0.22, ao=ao, sh=sh, aniso=(np.cos(c.A), np.sin(c.A), V(0.35)))
    cav = clamp((1 - ao) * 1.2)
    c.put(col * (1 - 0.25 * cav * (1 - inner))[..., None], c.cover(c.R - 0.985), H)
    P.save(c.image(), 'socket')


def lamp():
    """Warm light rising inside a socket."""
    c = Canvas(P.px(256), 2, 1.0)
    inside = smooth(0.80, 0.76, c.R)
    k = (0.30 + 0.75 * smooth(0.2, 0.80, c.R)) * inside
    c.col[:] = rgb('#FFB347') * 1.0
    c.alpha = clamp(k * 0.85).astype(F)
    P.save(c.image(tone=False), 'lamp', how='png')
    c = Canvas(P.px(320), 1, 1.0)
    c.col[:] = rgb('#FFB957')
    c.alpha = (gauss(c.R, 0.46) * smooth(1.0, 0.7, c.R) * 0.75).astype(F)
    P.save(c.image(tone=False), 'halo', how='png')


def jewel():
    """A ruby pilot light in a brass seat, unlit; the lit one is laid over it."""
    for name, base, glow in (('jewel', '#4A0A10', 0.0), ('jewel_on', '#FF2B3A', 1.0)):
        c = Canvas(P.px(64), 4, 1.0)
        H = bevel(np.maximum(c.R - 0.95, 0.62 - c.R), 0.16, 0.20)
        H = np.where(c.R < 0.66, 0.05 + dome(c.R, 0.66, 0.34), H)
        inner = smooth(0.66, 0.62, c.R)
        alb = mix(np.broadcast_to(BRASS, c.shape + (3,)), np.broadcast_to(rgb(base), c.shape + (3,)), inner[..., None])
        nx, ny, nz = normals(H, c.px)
        col = shade(ST, nx, ny, nz, alb, metal=0.97 * (1 - inner), rough=0.2, ao=occlusion(H, c.px, (0.05, 0.15), 1), clear=0.9 * 1.0)
        if glow:
            col = col + rgb(base) * (inner * (0.5 + 1.3 * gauss(np.hypot(c.X + 0.1, c.Y + 0.1), 0.45)))[..., None]
        c.put(col, c.cover(c.R - 0.95), H)
        P.save(c.image(), name)


def dial():
    """Porcelain clock face in a brass bezel."""
    c = Canvas(P.px(560), P.ss(3), 1.0)
    H = bevel(np.maximum(c.R - 0.995, 0.865 - c.R), 0.060, 0.060)
    H = np.maximum(H, bevel(np.abs(c.R - 0.862) - 0.016, 0.016, 0.030))
    H = np.where(c.R < 0.85, 0.012 * (1 - (c.R / 0.85) ** 2), H)
    H = H + 0.0008 * circular_streaks(c, 31, 900) * (c.R > 0.84)
    inner = smooth(0.852, 0.846, c.R)
    ink = np.zeros(c.shape, F)
    num = ['XII', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI']
    for i, t in enumerate(num):
        ink = np.maximum(ink, c.ring_text(t, 0.155, 0.640, i * TAU / 12, font='pala.ttf', spacing=0.86))
    a = (c.A + math.pi / 60) % (TAU / 60) - math.pi / 60
    q = np.abs(a) * c.R
    ink = np.maximum(ink, clamp((0.0035 - q) / c.px + 0.5) * (c.R > 0.775) * (c.R < 0.805))
    a5 = (c.A + math.pi / 12) % (TAU / 12) - math.pi / 12
    ink = np.maximum(ink, clamp((0.011 - np.abs(a5) * c.R) / c.px + 0.5) * (c.R > 0.770) * (c.R < 0.812))
    for r in (0.768, 0.812):
        ink = np.maximum(ink, clamp((0.0022 - np.abs(c.R - r)) / c.px + 0.5))
    # hairline crackle in the glaze
    d1, d2, _ = worley(c.X + 0.02 * fbm(c.shape, 6, 9, 3), c.Y + 0.02 * fbm(c.shape, 6, 10, 3), 3.2, 6, second=True)
    crack = clamp(1 - (d2 - d1) / 0.012) * smooth(0.2, 0.9, fbm(c.shape, 2.2, 14, 3) + 0.45)
    cream = mix(np.broadcast_to(rgb('#F4EAD3'), c.shape + (3,)), np.broadcast_to(rgb('#D8C59C'), c.shape + (3,)), (smooth(0.35, 0.85, c.R) * 0.55 + 0.20 * clamp(fbm(c.shape, 4, 3, 5)))[..., None])
    cream = cream * (1 - 0.30 * crack)[..., None]
    cream = mix(cream, rgb('#1C1712'), (ink * 0.93)[..., None])
    alb = mix(np.broadcast_to(BRASS, c.shape + (3,)), cream, inner[..., None])
    nx, ny, nz = normals(H, c.px)
    ao = occlusion(H, c.px, (0.015, 0.05, 0.10), 1.0)
    sh = cast(H, c.px, reach=0.22, slope=0.6)
    br = metal(c, H, BRASS, rough=0.22, aniso=(np.cos(c.A), np.sin(c.A), V(0.40)), grime=0.55, seed=23)
    po = shade(ST, nx, ny, nz, alb, metal=0.0, rough=0.4, ao=ao, sh=sh, clear=0.55)
    c.put(mix(br, po, inner[..., None]), c.cover(c.R - 0.995), H)
    P.save(c.image(exposure=0.95), 'dial')


def hands():
    def one(name, shape, col, h=1.0, size=96):
        c = Canvas(P.px(size), 4, 0.16, aspect=h / 0.16)
        d = shape(c)
        H = bevel(d, 0.012, 0.012)
        nx, ny, nz = normals(H, c.px)
        out = shade(ST, nx, ny, nz, rgb(col), metal=0.85, rough=0.28)
        c.put(out, c.cover(d), H)
        P.save(c.image(), name, how='png')

    def spade(L, w):
        def f(c):
            Y = c.Y
            d = c.taper(0, 0, w * 1.15, 0, -L * 0.60, w * 0.75)
            d = np.minimum(d, c.circle(w * 2.6, 0, -L * 0.60 - w * 1.6))
            d = np.maximum(d, -(c.circle(w * 1.35, 0, -L * 0.60 - w * 1.6)))
            d = np.minimum(d, c.taper(0, -L * 0.60 - w * 3.6, w * 1.2, 0, -L, w * 0.18))
            d = np.minimum(d, c.taper(0, 0, w * 1.15, 0, 0.16, w * 1.6))
            d = np.minimum(d, c.circle(0.052))
            return d
        return f

    one('hour', spade(0.46, 0.020), '#20242C')
    one('minute', spade(0.72, 0.016), '#20242C')

    def second(c):
        d = c.taper(0, 0.18, 0.016, 0, -0.76, 0.0045)
        d = np.minimum(d, np.abs(c.circle(0.030, 0, 0.235)) - 0.009)
        return np.minimum(d, c.circle(0.036))
    one('second', second, '#8A1620')
    c = Canvas(P.px(64), 4, 1.0)
    H = dome(c.R, 0.92, 0.5)
    c.put(metal(c, H, BRASS, rough=0.2, grime=0.2), c.cover(c.R - 0.92), H)
    P.save(c.image(), 'pin')


def pointer():
    """A toothed ring around the hub carrying an arrow."""
    c = Canvas(P.px(640), P.ss(2), 1.0)
    r0 = 0.80
    d = c.gear(72, 0.885, 0.035, duty=0.5)
    ring = np.maximum(d, (r0 + 0.005) - c.R)
    tip = c.poly([(0, -0.998), (0.060, -0.885), (0.026, -0.872), (0.020, -0.80), (-0.020, -0.80), (-0.026, -0.872), (-0.060, -0.885)])
    all_ = smin(ring, tip, 0.012)
    H = bevel(all_, 0.016, 0.026)
    H = np.maximum(H, bevel(tip, 0.028, 0.042))
    H = H + 0.0006 * circular_streaks(c, 77, 1200)
    col = metal(c, H, COPPER, rough=0.25, aniso=(np.cos(c.A), np.sin(c.A), V(0.40)), grime=0.55, seed=52, scratch=30)
    c.put(col, c.cover(all_), H)
    P.save(c.image(), 'pointer')


def cartouche():
    """Enamel name plate."""
    c = Canvas(P.px(420), P.ss(3), 1.0, aspect=0.36)
    d = c.box(0.965, 0.315, r=0.10)
    d = smax(d, -(np.hypot(np.abs(c.X) - 0.965, c.Y) - 0.085), 0.02)
    H = bevel(d, 0.045, 0.050)
    inn = c.box(0.885, 0.235, r=0.06)
    H = np.where(inn < 0, 0.020, H)
    inner = c.cover(inn)
    H = rivets_at(c, H, [(-0.925, -0.0), (0.925, 0.0)], 0.0001, 0.05)
    alb = mix(np.broadcast_to(BRASS, c.shape + (3,)), np.broadcast_to(rgb('#F2E6CB'), c.shape + (3,)), inner[..., None])
    nx, ny, nz = normals(H, c.px)
    ao = occlusion(H, c.px, (0.02, 0.06), 1.0)
    sh = cast(H, c.px, reach=0.15, slope=0.6)
    br = metal(c, H, BRASS, rough=0.22, grime=0.5, seed=61)
    po = shade(ST, nx, ny, nz, alb, metal=0, rough=0.4, ao=ao, sh=sh, clear=0.4)
    c.put(mix(br, po, inner[..., None]), c.cover(d), H)
    P.save(c.image(), 'cartouche')


def rivets_at(c, H, pts, size, base):
    return H


def steam():
    c = Canvas(P.px(128), 1, 1.0)
    n = fbm(c.shape, 3.0, 5, 4)
    r = c.R + 0.32 * n
    a = (1 - smooth(0.15, 0.85, r)) * smooth(1.0, 0.8, c.R)
    c.col[:] = rgb('#FFF4E4') * (0.75 + 0.25 * smooth(-0.5, 0.5, n))[..., None]
    c.alpha = (a * 0.55).astype(F)
    P.save(c.image(tone=False), 'steam')
    c = Canvas(P.px(48), 2, 1.0)
    c.col[:] = rgb('#FFD27A')
    c.alpha = (gauss(c.R, 0.34)).astype(F)
    P.save(c.image(tone=False), 'spark')


P.run([plate, lambda: gear('gear', 30, 6, 14), lambda: gear('gear2', 20, 5, 15, COPPER, 320), lambda: gear('gear3', 44, 8, 16, OLD_BRASS, 420), socket, lamp, jewel, dial, hands, pointer, cartouche, steam,
       lambda: P.save(glass_dome(P.px(256)), 'glass', how='png')])

# ------------------------------------------------------------------ sounds
P.sounds('clockwork')
P.finish()
