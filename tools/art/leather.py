"""Leather Atelier: stitched saddle leather with brass rivets; apps sit on stitched leather patches."""
from lineup import *

K = Kit('leather', 'Leather Atelier', 'Stitched saddle leather with brass rivets; apps sit on leather patches sewn with cream thread', ['craft', 'warm', 'brown'])
K.flag(halo='light')
BRASS = '#C8964A'


def grain(c, seed):
    return 0.6 * fbm(c.shape, 60, seed, 3) + 0.4 * fbm(c.shape, 160, seed + 1, 2)


def stitches(c, r, n, length=0.5, w=0.006):
    on = np.abs(((c.A / TAU * n) % 1) - 0.5) < length * 0.5
    return gauss(c.R - r, w) * on


def hide():
    c = K.canvas(1080, 2)
    d = c.R - 0.99
    g = grain(c, 3)
    alb = mix(flat('#8A5428', c.shape), flat('#B8783A', c.shape), clamp(0.5 + 0.6 * fbm(c.shape, 4, 4, 4))[..., None]) * (0.9 + 0.15 * g)[..., None]
    alb = alb * (1 - 0.35 * smooth(0.80, 1.0, c.R))[..., None]
    groove = gauss(c.R - 0.90, 0.006) + gauss(c.R - 0.52, 0.005)
    H = 0.004 * g - 0.008 * groove + 0.02 * np.sqrt(clamp(1 - c.R ** 8))
    thread = clamp(stitches(c, 0.935, 160) + stitches(c, 0.875, 140) * 0.0)
    col = surface(c, H, alb, WARM, rough=0.5, reach=0.08, sheen=0.2)
    col = mix(col, flat('#F2E2C0', c.shape), thread[..., None])
    rv = np.zeros(c.shape, F)
    for k in range(12):
        x, y = c.polar(k * TAU / 12 + TAU / 24, 0.965)
        rv = np.maximum(rv, smooth(0.020, 0.016, np.hypot(c.X - x, c.Y - y)))
    col = mix(col, metal(c, 0.02 * rv, flat(BRASS, c.shape), rough=0.25, grime=0.3, seed=5, studio=WARM), rv[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'hide')


def patches():
    tones = ['#4A2A14', '#6A3A1A', '#2A1A10', '#8A4A22']
    def one(c, k):
        d = c.R - 0.86
        g = grain(c, 10 + k)
        H = 0.05 * clamp(-d / 0.06) + 0.004 * g - 0.006 * gauss(c.R - 0.74, 0.008)
        alb = flat(tones[k], c.shape) * (0.9 + 0.15 * g)[..., None]
        col = surface(c, H, alb, WARM, rough=0.5, reach=0.06, sheen=0.2)
        col = mix(col, flat('#F2E2C0', c.shape), clamp(stitches(c, 0.76, 36, 0.55, 0.012))[..., None])
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'patches', 4, one)


def medal():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    g = grain(c, 30)
    H = 0.05 * clamp(-d / 0.05) + 0.004 * g - 0.008 * gauss(c.R - 0.84, 0.008)
    alb = flat('#3A2010', c.shape) * (0.9 + 0.15 * g)[..., None]
    col = surface(c, H, alb, WARM, rough=0.5, reach=0.06, sheen=0.2)
    col = mix(col, flat('#F2E2C0', c.shape), clamp(stitches(c, 0.88, 60, 0.55, 0.008))[..., None])
    rv = np.zeros(c.shape, F)
    for k in range(4):
        x, y = c.polar(k * TAU / 4 + TAU / 8, 0.74)
        rv = np.maximum(rv, smooth(0.05, 0.04, np.hypot(c.X - x, c.Y - y)))
    col = mix(col, metal(c, 0.03 * rv, flat(BRASS, c.shape), rough=0.25, grime=0.3, seed=6, studio=WARM), rv[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'medal')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFE0B0')
    c = K.canvas(40, 4, 1.0, 1.6)
    nd = c.taper(0, 1.5, 0.12, 0, -1.5, 0.02)
    eye = c.capsule(0, 1.1, 0, 1.3, 0.04)
    c.put(metal(c, 0.1 * clamp(-nd / 0.12), flat('#C8CCD2', c.shape), rough=0.2, grime=0.1, seed=2, studio=COOL), c.cover(np.maximum(nd, -eye)))
    K.put(c, 'needle', how='png')


K.run([hide, patches, medal])
P = dict(base='#3A2414', accent=BRASS, accent2='#F2E2C0', text='#F6EAD0', sub='#D8C09A', panel=('#5A3A20', '#3A2414'), stroke=BRASS, tile=('#E8D2A8', '#C8A878'), tilestroke='#8A5A28',
         ink='#3A2414', dim=0.36, font='Constantia, Georgia', badge=BRASS, badgeink='#3A2414')
finish(K, P, sounds='wood',
       back=[soft(1.10, 0.04, 60), img('hide', 1.0, intro=intro(0.45, 'out', scale=0.94))],
       under=[img('halo', '1.5*hot', opacity='hot*0.5', when='hot>0.02'), soft(0.96, 0.06, 45), img('patches', '1.0*(1+0.04*hot-0.04*press)', frame='(i+ring)%4', rotate='seed*360')],
       icon=dict(size=0.56, zoom=1.14, tone='engrave', shadow=dict(x=0, y=1, blur=2, color='black/50')),
       hub=[img('medal', 1.0, intro=intro(0.45, 'back', scale=0.7))],
       over=[img('needle', [0.04, 0.064], **{'in': 'hub'}, angle='sel', radius=1.10, rotate='sel', opacity='on')],
       words_kw=dict(shadow=dict(x=0, y=1, blur=3, color='black/80')),
       style=dict(open='bloom', speed=0.9, tilt=0.3),
       onlaunch=[dict(color='#F2E2C0', count=14, area='slot', life=[0.4, 0.8], size=[1.2, 2.4], speed=[50, 180], outward=True, dir=[-90, 90], drag=2, fadein=0, fadeout=0.5)])
