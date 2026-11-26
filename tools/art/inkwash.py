"""Ink Wash: brush strokes and bleeding ink on rice paper; misty mountains, a red seal, apps in brushed circles."""
from lineup import *

K = Kit('inkwash', 'Ink Wash', 'Brush strokes and bleeding ink on rice paper: misty mountains, a red seal, apps in brushed circles', ['ink', 'calm', 'light'])
K.flag(halo='light', blot='light')


def paper(c):
    fibers = clamp(blur1(white(c.shape, 3), 6 * c.ss, 1) * 6) * 0.04
    return flat('#F2ECE0', c.shape) * (0.95 + 0.05 * fbm(c.shape, 20, 4, 3) - fibers)[..., None]


def enso(c, r, w, seed, gap=0.6):
    """A brushed circle that is left a little open."""
    g = rng(seed)
    a0 = g.random() * TAU
    pts = [c.polar(a0 + t * (TAU - gap), r * (1 + 0.02 * math.sin(t * 9 + seed))) for t in np.linspace(0, 1, 80)]
    cov = Ink(c).brush(pts, w, 255, 'tail', seed=seed, rough=0.2).arr(0.004)
    streak = 0.5 + 0.5 * np.sin(c.R * 260 + 2.5 * fbm(c.shape, 6, seed + 2, 2))
    dry = clamp(0.80 + 0.35 * fbm(c.shape, 22, seed + 1, 2) - 0.25 * streak * smooth(0.6, 1.0, cov))
    return clamp(cov * dry * 1.25)


def scroll():
    c = K.canvas(1080, 2)
    d = c.R - 0.99
    col = paper(c)
    ink = np.zeros(c.shape, F)
    for k, (base, amp, freq, tone) in enumerate(((0.30, 0.26, 2.6, 0.45), (0.52, 0.20, 4.1, 0.68), (0.74, 0.14, 6.3, 0.92))):
        ridge = base - amp * np.abs(np.sin(c.X * freq + k * 1.7)) * (0.6 + 0.4 * fbm(c.shape, 4, 10 + k, 3))
        m = smooth(ridge - 0.01, ridge + 0.04, c.Y) * smooth(1.0, 0.85, c.Y + 0.15 * k * 0)
        ink = np.maximum(ink, m * tone * (0.7 + 0.3 * smooth(ridge + 0.25, ridge, c.Y)))
    mist = smooth(0.95, 0.5, c.Y) * 0.0 + smooth(0.0, 0.5, fbm(c.shape, 3, 9, 3) + 0.2) * 0.18
    ink = ink * (1 - mist)
    col = col * (1 - 0.85 * ink)[..., None]
    rim = enso(c, 0.93, 0.05, 7, 0.4)
    col = mix(col, flat('#141414', c.shape), (0.9 * rim)[..., None])
    seal = c.box(0.06, 0.06, x=0.55, y=-0.60, r=0.01)
    col = mix(col, flat('#C8303A', c.shape), (c.cover(seal) * (0.8 + 0.2 * fbm(c.shape, 50, 5, 2)))[..., None])
    c.put(col, c.cover(d))
    K.put(c, 'scroll')


def circles():
    def one(c, k):
        cov = enso(c, 0.80, 0.16, 20 + k, 0.5 + 0.2 * k)
        c.col[:] = rgb('#141414')
        c.alpha = clamp(cov * 0.92)
        return c
    plate(K, 'circles', 4, one)


def middle():
    c = K.canvas(460, 2)
    d = c.R - 0.97
    col = paper(c)
    col = mix(col, flat('#141414', c.shape), (0.9 * enso(c, 0.88, 0.12, 40, 0.5))[..., None])
    c.put(col, c.cover(d))
    K.put(c, 'middle')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFFFFF')
    light(K, 'blot', 120, lambda c: (1 - smooth(0.0, 1.0, c.R + 0.1 * fbm(c.shape, 4, 3, 2))) ** 1.5, tint='#202020')
    c = K.canvas(40, 4, 1.0, 1.6)
    cov = Ink(c).brush([(0, -1.5), (0.05, 0), (0, 1.5)], 0.7, 255, 'tail').arr(0.02)
    c.col[:] = rgb('#C8303A')
    c.alpha = cov
    K.put(c, 'stroke', how='png', tone=False)


K.run([scroll, circles, middle])
P = dict(base='#F2ECE0', accent='#141414', accent2='#C8303A', text='#141414', sub='#4A4A4A', panel=('#F6F2E8', '#E8E0D0'), stroke='#141414', tile=('#F6F2E8', '#E8E0D0'), tilestroke='#141414',
         ink='#141414', paneltext='#141414', dim=0.2, font='Ink Free, Segoe Print', badge='#C8303A', badgeink='#F6F2E8')
finish(K, P, sounds='paper',
       back=[soft(1.06, 0.02, 40), img('scroll', 1.0, intro=intro(0.6, 'out', scale=0.96))],
       under=[img('halo', '1.5*hot', opacity='hot*0.6', when='hot>0.02'), img('circles', '1.04*(1+0.04*hot-0.03*press)', frame='(i+ring)%4', rotate='seed*360')],
       icon=dict(size=0.56, zoom=1.14, tone='ink', shadow=dict(x=0, y=1, blur=2, color='black/25')),
       hub=[img('middle', 1.0, intro=intro(0.5, 'back', scale=0.7))],
       over=[img('stroke', [0.05, 0.08], **{'in': 'hub'}, angle='sel', radius=1.10, rotate='sel', opacity='on')],
       words_kw=dict(px=19, clockpx=34, shadow=dict(x=0, y=0, blur=2, color='#F2ECE0')),
       tabs=dict(inset=13, text='#141414', fill='#00000010', on='#C8303A/80'),
       style=dict(open='fade', speed=0.8, tilt=0.2),
       onlaunch=[dict(image='blot', count=10, area='slot', life=[0.6, 1.2], size=[10, 24], grow=1.8, speed=[20, 90], outward=True, dir=[-90, 90], drag=2, opacity=0.35, fadein=0, fadeout=0.6)])
