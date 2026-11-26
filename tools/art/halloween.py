"""Halloween: a spider's web across the night, jack-o'-lanterns that hold the apps, a full moon, and bats."""
from lineup import *

K = Kit('halloween', 'Halloween', "A spider's web across the night, grinning jack-o'-lanterns, a full moon and bats", ['halloween', 'dark', 'orange'])
K.flag(halo='light', flicker='light')


def web():
    c = K.canvas(1080, 2)
    night = mix(flat('#1E1228', c.shape), flat('#07040C', c.shape), smooth(0.0, 1.0, c.R)[..., None])
    n = 16
    a = (c.A % (TAU / n)) - TAU / n / 2
    spokes = gauss(c.R * np.abs(a), 0.0025) * smooth(0.04, 0.08, c.R)
    sag = (a / (TAU / n / 2)) ** 2
    rings = np.zeros(c.shape, F)
    for r in np.arange(0.16, 0.97, 0.075):
        rings = np.maximum(rings, gauss(c.R - (r - 0.018 * sag * (0.6 + r)), 0.0022))
    silk = clamp(spokes + rings * 0.9) * clamp(0.55 + 0.5 * fbm(c.shape, 60, 3, 2))
    col = night + V([0.85, 0.85, 0.95]) * (0.75 * silk)[..., None] + V([0.6, 0.6, 0.8]) * (0.12 * blur(silk, 3 * c.ss))[..., None]
    col = col + V([1, 0.9, 0.7]) * stars(c, 50, 4, 0.2, 0.98, 0.004, 0.6)[..., None]
    c.put(col, c.cover(c.R - 0.995))
    K.put(c, 'web')


def lanterns():
    def one(c, k):
        e = np.hypot(c.X / 0.92, c.Y / 0.80) - 1
        rib = 0.5 + 0.5 * np.cos(c.X * 13 / (0.4 + 0.6 * np.sqrt(clamp(1 - (c.Y / 0.85) ** 2))))
        H = 0.25 * np.sqrt(clamp(-e)) + 0.015 * rib
        alb = mix(flat('#B24A08', c.shape), flat('#E87E1C', c.shape), clamp(0.3 + 0.5 * rib + 0.2 * fbm(c.shape, 10, 3 + k, 3))[..., None])
        col = surface(c, H, alb, WARM, rough=0.45, clear=0.3, reach=0.08)
        g = rng(60 + k)
        tilt = (g.random() - 0.5) * 0.3
        eyes = np.minimum(c.poly([(-0.46, -0.30), (-0.16, -0.30), (-0.31, -0.58)]), c.poly([(0.16, -0.30), (0.46, -0.30), (0.31, -0.58)]))
        if k % 2:
            eyes = np.minimum(c.circle(0.12, -0.30, -0.42), c.circle(0.12, 0.30, -0.42))
        xs = np.linspace(-0.45, 0.45, 9)
        top = [(x, 0.36 + (0.07 if i % 2 else 0) + tilt * x) for i, x in enumerate(xs)]
        mouth = c.poly(top + [(0.40, 0.48), (0.2, 0.62), (-0.2, 0.62), (-0.40, 0.48)])
        cut = c.cover(np.minimum(eyes, mouth))
        glow = rgb('#FFD25A') * 1.6
        col = mix(col, flat('#FFB030', c.shape) * 1.3, cut[..., None])
        col = col + rgb('#FF8A1E') * (0.6 * blur(cut, 6 * c.ss))[..., None] * (1 - cut[..., None])
        stem = c.capsule(0, -0.80, 0.06, -0.96, 0.07)
        c.put(col, c.cover(e * 0.8), H)
        c.put(surface(c, 0.05 * clamp(-stem / 0.07), flat('#4A5A22', c.shape), WARM, rough=0.7), c.cover(stem))
        return c
    plate(K, 'lanterns', 4, one)


def moon():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    t = clamp(-d / 0.96)
    H = lens(t, 0.06, 2.0)
    cr = np.zeros(c.shape, F)
    g = rng(7)
    for _ in range(14):
        x, y, r = g.uniform(-0.7, 0.7), g.uniform(-0.7, 0.7), g.uniform(0.05, 0.16)
        q = np.hypot(c.X - x, c.Y - y)
        cr = cr + 0.5 * smooth(r, r * 0.6, q) - 0.2 * gauss(q - r, 0.012)
    alb = mix(flat('#F3E7C2', c.shape), flat('#C9B98E', c.shape), clamp(0.4 * fbm(c.shape, 5, 4, 3) + 0.4 * cr)[..., None])
    col = surface(c, H - 0.01 * cr, alb, SOFT, rough=0.9, reach=0.05)
    col = col * (1 + 0.3 * smooth(0.6, 0.0, c.R))[..., None]
    c.put(col, c.cover(d), H)
    K.put(c, 'moon', exposure=1.05)
    halo(K, 'halo', 220, 2.0, 0.25, tint='#FF9A30')
    light(K, 'flicker', 200, lambda c: (1 - smooth(0.0, 1.0, c.R)) ** 2, tint='#FFB040')
    c = K.canvas(48, 4, 1.0, 1.4)  # candy corn
    tri = c.poly([(0, -1.25), (0.62, 1.0), (-0.62, 1.0)])
    band = np.where(c.Y < -0.35, 0, np.where(c.Y < 0.35, 1, 2))
    alb = np.stack([np.choose(band, [rgb('#FFF6E6')[i] * np.ones(c.shape, F), rgb('#FF8A1E')[i] * np.ones(c.shape, F), rgb('#FFC93A')[i] * np.ones(c.shape, F)]) for i in range(3)], axis=-1)
    col = surface(c, 0.2 * clamp(-tri / 0.4), alb.astype(F), SOFT, rough=0.4, clear=0.5)
    c.put(col, c.cover(tri))
    K.put(c, 'corn', how='png')
    c = K.canvas(64, 4, 1.0, 0.6)  # a bat for the launch
    pts = [(0, -0.18), (0.12, -0.34), (0.18, -0.18), (0.55, -0.55), (0.98, -0.34), (0.78, -0.14), (0.70, 0.08), (0.48, -0.02), (0.36, 0.18), (0.16, 0.10),
           (0, 0.30), (-0.16, 0.10), (-0.36, 0.18), (-0.48, -0.02), (-0.70, 0.08), (-0.78, -0.14), (-0.98, -0.34), (-0.55, -0.55), (-0.18, -0.18), (-0.12, -0.34)]
    c.col[:] = rgb('#140A18')
    c.alpha = c.cover(c.poly(pts))
    K.put(c, 'bat', how='png', tone=False)


K.run([web, lanterns, moon])
P = dict(base='#140C18', accent='#FF8A1E', accent2='#FFD27A', text='#2A1A12', sub='#5A4030', panel=('#2A1A30', '#140C18'), stroke='#FF8A1E', tile=('#3A2440', '#1E1228'), tilestroke='#FF8A1E',
         ink='#FFE7C2', paneltext='#FFE7C2', dim=0.6, font='Constantia, Georgia', badge='#FF8A1E', badgeink='#140C18')
finish(K, P, sounds='spooky',
       back=[soft(1.08, 0.03, 70), img('web', 1.0, rotate='(1-open)*-15', intro=intro(0.45, 'out', scale=0.9))],
       under=[img('flicker', '1.7*(1+0.08*sin(time*13+seed*9)+0.05*sin(time*7))', opacity='0.45+0.35*hot'), img('lanterns', '1.0*(1+0.05*hot-0.04*press)', frame='(i+ring)%4', rotate='6*sin(time*1.5+seed*6)')],
       icon=dict(size=0.46, zoom=1.2, shadow=dict(x=0, y=0, blur=5, color='#FFB030/70')),
       hub=[img('halo', 1.35, opacity='0.35'), img('moon', 1.0, intro=intro(0.45, 'back', scale=0.6))],
       over=[img('corn', [0.07, 0.098], **{'in': 'hub'}, angle='sel', radius=1.10, rotate='sel', opacity='on')],
       words_kw=dict(shadow=dict(x=0, y=0, blur=3, color='#F3E7C2')),
       tabs=dict(inset=13, text='#FFE7C2', fill='#FFFFFF/14', on='#FF8A1E/85'),
       style=dict(open='bloom', tilt=0.35),
       onlaunch=[dict(image='bat', count=7, area='slot', life=[0.7, 1.2], size=[14, 22], speed=[120, 300], outward=True, dir=[-70, 70], drag=1.2, sway=30, swayhz=3, fadein=0, fadeout=0.4),
                 dict(color='#FF9A30', count=16, area='slot', life=[0.4, 0.8], size=[1.5, 3], speed=[40, 160], outward=True, dir=[-90, 90], gravity=-40, fadein=0, fadeout=0.6)],
       screen=dict(effect='bats', color='#120814', color2='#2A1230', density=1.4, speed=1.0, size=1.1))
