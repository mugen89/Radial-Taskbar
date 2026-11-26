"""Materials shared by several skins. Reflectances are linear, close to measured ones."""
from artkit import *

GOLD = V([1.00, 0.71, 0.29])
BRASS = V([0.89, 0.68, 0.34])
OLD_BRASS = V([0.66, 0.47, 0.21])
COPPER = V([0.93, 0.50, 0.35])
BRONZE = V([0.58, 0.38, 0.19])
STEEL = V([0.56, 0.57, 0.58])
DARK_STEEL = V([0.20, 0.21, 0.23])
IRON = V([0.36, 0.34, 0.32])
CHROME = V([0.86, 0.87, 0.89])
ALU = V([0.78, 0.79, 0.80])

WARM = Studio(lights=[((-0.45, -0.72, 0.58), 0.40, '#FFF1DC', 4.6), ((0.80, -0.30, 0.50), 0.24, '#FFE2B8', 1.7),
                      ((0.20, 0.86, 0.40), 0.36, '#FFB777', 0.9), ((-0.92, 0.20, 0.28), 0.18, '#CFDDFF', 1.1)], sky='#D9C7A8', floor='#150D07', ambient=0.42)
COOL = Studio(lights=[((-0.42, -0.74, 0.58), 0.38, '#F4F8FF', 4.8), ((0.82, -0.22, 0.48), 0.22, '#BFD6FF', 2.0),
                      ((0.10, 0.88, 0.42), 0.34, '#8FB0FF', 0.8), ((-0.92, 0.25, 0.25), 0.18, '#FFE9CF', 0.9)], sky='#B9C8E0', floor='#0B0E14', ambient=0.40)
SOFT = Studio(lights=[((-0.40, -0.70, 0.65), 0.70, '#FFFFFF', 3.4), ((0.70, -0.40, 0.55), 0.45, '#E8F0FF', 1.5),
                      ((0.10, 0.80, 0.50), 0.60, '#FFEBD6', 0.9)], sky='#E6ECF6', floor='#4A4C55', ambient=0.65)


def metal(c, H, albedo, rough=0.25, aniso=None, grime=0.5, seed=3, reach=0.12, slope=0.75, studio=WARM, scratch=0, strength=1.0, dirt='#1A1108', ao_r=(0.008, 0.02, 0.05), met=0.97):
    """Lit metal with dirt in its corners and a few scratches."""
    nx, ny, nz = normals(H, c.px, strength)
    ao = occlusion(H, c.px, ao_r, 1.2)
    sh = cast(H, c.px, reach=reach, slope=slope)
    g = fbm(c.shape, 7, seed, 5)
    cav = clamp((1 - ao) * 1.7 + 0.16 * clamp(g + 0.15))
    alb = np.broadcast_to(V(albedo), c.shape + (3,)) if np.ndim(albedo) < 3 else albedo
    alb = mix(alb, rgb(dirt), (clamp(grime * cav))[..., None])
    alb = alb * (1 + 0.06 * g)[..., None]
    col = shade(studio, nx, ny, nz, alb, metal=met, rough=rough, ao=ao, sh=sh, aniso=aniso)
    if scratch:
        s = scratches(c.shape, seed + 40, scratch, width=max(1, c.ss * 0.6))
        col = col * (1 - 0.10 * s[..., None]) + 0.05 * s[..., None] * alb
    return col


def rivets(c, H, n, radius, size, base, phase=0.0, depth=None):
    depth = depth or size * 0.75
    for i in range(n):
        x, y = c.polar(i * TAU / n + phase, radius)
        d = np.hypot(c.X - x, c.Y - y)
        H = np.where(d < size * 1.35, np.maximum(H, base + dome(d, size, depth)), H)
        H = np.where((d >= size) & (d < size * 1.35), H - depth * 0.25 * (1 - (d - size) / (size * 0.35)), H)
    return H


def glass_dome(size, ss=3, tint=None, strength=1.0):
    """A clear dome lit by two windows, to be drawn over an icon. Only light and a soft rim, no colour of its own."""
    c = Canvas(size, ss, 1.0)
    r = c.R
    inside = smooth(1.0, 0.985, r)
    # window reflection, upper left, bent along the dome
    ax, ay = c.X + 0.10, c.Y + 0.14
    rr = np.hypot(ax, ay)
    win = smooth(0.50, 0.60, rr) * (1 - smooth(0.76, 0.86, rr)) * smooth(0.25, 0.9, -(ax * 0.55 + ay * 0.84) / np.maximum(rr, 1e-4))
    bars = 1 - 0.55 * gauss(ax * 0.84 - ay * 0.55, 0.018)
    spot = gauss(np.hypot(c.X + 0.40, c.Y + 0.50), 0.10) * 0.9
    rim = smooth(0.80, 1.0, r) ** 2 * 0.30
    low = smooth(0.55, 0.95, r) * smooth(0.2, 1.0, (c.X * 0.5 + c.Y * 0.86) / np.maximum(r, 1e-4)) * (1 - smooth(0.95, 1.0, r)) * 0.40
    light = (win * 0.62 * bars + spot * 0.6 + low * 0.8) * strength
    dark = rim * 0.75
    a = clamp(light + dark * (1 - light)) * inside
    col = np.ones(c.shape + (3,), F) * (light / np.maximum(light + dark * (1 - light), 1e-4))[..., None]
    if tint is not None:
        col = col * mix(V([1, 1, 1]), rgb(tint), 0.5)
    c.col = from_srgb(col)
    c.alpha = a.astype(F)
    return c.image(tone=False)


def soft_disc(size, power=2.0, inner=0.0):
    """White glow for tinting."""
    c = Canvas(size, 1, 1.0)
    t = clamp((c.R - inner) / (1 - inner))
    a = (1 - smooth(0, 1, t)) ** power
    c.col[:] = 1
    c.alpha = a.astype(F)
    return c.image(tone=False)
