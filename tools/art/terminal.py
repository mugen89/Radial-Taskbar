"""Phosphor: a round terminal screen in a cream plastic housing."""
import shutil
import sys
from metals import *
from pack import Pack, ROOT

P = Pack('terminal', sys.argv)
ST = SOFT


def housing():
    c = Canvas(P.px(1100), P.ss(2), 1.0)
    X, Y = np.abs(c.X), np.abs(c.Y)
    # a squarish moulded box with big round corners
    d = c.box(0.985, 0.985, r=0.40)
    H = bevel(d, 0.07, 0.075, 'ogee')
    rim = np.abs(c.R - 0.895) - 0.055
    H = np.where(rim < 0, np.maximum(H, 0.075 + bevel(rim, 0.055, 0.030)), H)          # raised ring round the glass
    H = np.where(c.R < 0.845, 0.02, H)
    # vents: four straight slots across two of the corners
    vents = np.full(c.shape, 9.0, F)
    for sx, sy in ((-1, -1), (1, 1)):
        u, t = (sx / math.sqrt(2), sy / math.sqrt(2)), (-sy / math.sqrt(2), sx / math.sqrt(2))
        for dist, half in ((1.005, 0.150), (1.050, 0.135), (1.095, 0.115), (1.140, 0.088)):
            x, y = u[0] * dist, u[1] * dist
            vents = np.minimum(vents, c.capsule(x - t[0] * half, y - t[1] * half, x + t[0] * half, y + t[1] * half, 0.0125))
    H = H - 0.030 * smooth(0.005, -0.007, vents)
    # screws
    for sx, sy in ((1, -1), (-1, 1)):
        x, y = sx * 0.80, sy * 0.80
        r = np.hypot(c.X - x, c.Y - y)
        H = np.where(r < 0.040, 0.060 + dome(r, 0.044, 0.012), H)
        slot = np.minimum(np.abs((c.X - x) * 0.8 + (c.Y - y) * 0.6), np.abs((c.X - x) * 0.6 - (c.Y - y) * 0.8))
        H = np.where((r < 0.032) & (slot < 0.0052), H - 0.016, H)
    grain = fbm(c.shape, 260, 4, 2)
    H = H + 0.0006 * grain
    nx, ny, nz = normals(H, c.px)
    ao = occlusion(H, c.px, (0.008, 0.025, 0.06), 1.2)
    sh = cast(H, c.px, reach=0.18, slope=0.6)
    age = clamp(fbm(c.shape, 3, 8, 4) * 0.5 + 0.5)
    alb = mix(np.broadcast_to(rgb('#D9D0B8'), c.shape + (3,)), np.broadcast_to(rgb('#C2B48F'), c.shape + (3,)), (0.45 * age)[..., None])
    alb = alb * (1 + 0.03 * grain)[..., None]
    inner = smooth(0.845, 0.838, c.R)
    alb = mix(alb, np.broadcast_to(rgb('#0B0E0C'), c.shape + (3,)), inner[..., None])
    for sx, sy in ((1, -1), (-1, 1)):
        r = np.hypot(c.X - sx * 0.80, c.Y - sy * 0.80)
        alb = np.where((r < 0.040)[..., None], rgb('#8E8B84'), alb)
    alb = alb * (1 - 0.80 * smooth(0.002, -0.006, vents))[..., None]
    grime = clamp((1 - ao) * 1.1)
    alb = alb * (1 - 0.30 * grime)[..., None]
    col = shade(ST, nx, ny, nz, alb, metal=0.0, rough=0.5, ao=ao, sh=sh, clear=0.18)
    c.put(col, c.cover(d), H)
    P.save(c.image(exposure=0.92), 'housing', 88)
    # the shadow it throws on the desktop, blurred for good: a drawn one would be cut off at the edge of what is drawn
    c = Canvas(192, 1, 1.22)
    c.col[:] = 0
    c.alpha = (0.62 * blur(c.cover(c.box(0.955, 0.955, r=0.40)), 0.085 / c.px)).astype(F)
    P.save(c.image(tone=False, dither=False), 'shadow', how='png')


def screen():
    c = Canvas(P.px(900), 2, 1.0)
    v = smooth(1.02, 0.15, c.R)
    col = rgb('#02140A') * (0.6 + 0.9 * v)[..., None] + rgb('#0B5A2E') * (0.22 * v ** 2)[..., None]
    # a faint polar grid burnt into the phosphor
    g = np.zeros(c.shape, F)
    for r in (0.36, 0.62, 0.88):
        g = np.maximum(g, gauss(c.R - r, 0.0022))
    for i in range(24):
        a = (c.A - i * TAU / 24 + math.pi) % TAU - math.pi
        g = np.maximum(g, gauss(np.sin(a) * c.R, 0.0016) * (np.abs(a) < 1) * (c.R > 0.36) * (c.R < 0.88) * 0.6)
    col = col + rgb('#2CFF86') * (0.07 * g)[..., None]
    noise = white(c.shape, 3)
    col = col * (1 + 0.05 * blur(noise, 0.8 * c.ss))[..., None]
    c.put(clamp(col), c.cover(c.R - 0.998))
    P.save(c.image(tone=False), 'screen', 86)
    # scan lines, tiled
    im = Image.new('RGBA', (8, 8), (0, 0, 0, 0))
    for y in range(8):
        a = [70, 20, 0, 20, 70, 20, 0, 20][y]
        for x in range(8):
            im.putpixel((x, y), (0, 0, 0, a))
    im.save(os.path.join(P.dir, 'lines.png'))
    # glass in front: a window's reflection and a dark edge
    c = Canvas(P.px(700), 2, 1.0)
    ax, ay = c.X + 0.06, c.Y + 0.10
    rr = np.hypot(ax, ay)
    win = smooth(0.60, 0.72, rr) * (1 - smooth(0.84, 0.95, rr)) * smooth(0.35, 0.95, -(ax * 0.55 + ay * 0.84) / np.maximum(rr, 1e-4))
    edge = smooth(0.78, 1.0, c.R) ** 2 * 0.65
    light = win * 0.20
    a = clamp(light + edge * (1 - light)) * c.cover(c.R - 0.998)
    c.col = from_srgb(np.ones(c.shape + (3,), F) * (light / np.maximum(light + edge * (1 - light), 1e-4))[..., None])
    c.alpha = a.astype(F)
    P.save(c.image(tone=False), 'glass', how='png')
    # sweep of a radar beam
    c = Canvas(P.px(600), 1, 1.0)
    a = (-c.A) % TAU
    k = np.exp(-a / 0.55) * smooth(1.0, 0.96, c.R) * smooth(0.0, 0.05, c.R)
    c.col[:] = rgb('#37FF8C')
    c.alpha = clamp(k * 0.42).astype(F)
    P.save(c.image(tone=False), 'sweep', how='png')
    c = Canvas(P.px(256), 1, 1.0)
    c.col[:] = rgb('#37FF8C')
    c.alpha = (gauss(c.R, 0.42) * smooth(1.0, 0.75, c.R)).astype(F)
    P.save(c.image(tone=False), 'glow', how='png')


def led():
    for name, base, g in (('led', '#3A0A08', 0), ('led_on', '#FF3B2A', 1)):
        c = Canvas(P.px(64), 4, 1.0)
        H = bevel(np.maximum(c.R - 0.95, 0.66 - c.R), 0.14, 0.14)
        H = np.where(c.R < 0.68, 0.03 + dome(c.R, 0.68, 0.30), H)
        inner = smooth(0.68, 0.64, c.R)
        alb = mix(np.broadcast_to(rgb('#3B3A36'), c.shape + (3,)), np.broadcast_to(rgb(base), c.shape + (3,)), inner[..., None])
        nx, ny, nz = normals(H, c.px)
        col = shade(ST, nx, ny, nz, alb, metal=0.0, rough=0.25, ao=occlusion(H, c.px, (0.05, 0.15), 1), clear=0.9)
        if g:
            col = col + rgb(base) * (inner * (0.7 + 1.2 * gauss(np.hypot(c.X + 0.1, c.Y + 0.1), 0.45)))[..., None]
        c.put(col, c.cover(c.R - 0.95), H)
        P.save(c.image(), name, how='png')


P.run([housing, screen, led])
for f in ('VT323-Regular.ttf', 'OFL.txt'):
    shutil.copy(os.path.join(ROOT, 'tools', 'art', 'fonts', 'vt323', f), os.path.join(P.dir, f))
P.sounds('term')
P.finish()
