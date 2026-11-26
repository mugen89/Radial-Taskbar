"""Elven Grove: a silver tree spreads its branches over a moonlit grove; apps ride on its leaves, fireflies gather."""
from lineup import *

K = Kit('elven', 'Elven Grove', 'A silver tree spreads over a moonlit grove; apps ride on its leaves while fireflies gather', ['fantasy', 'nature', 'calm'])
K.flag(halo='light')


def grove():
    c = K.canvas(1080, 2)
    d = c.R - 0.99
    moss = fbm(c.shape, 6, 3, 4)
    col = mix(flat('#0A2420', c.shape), flat('#1E4A3E', c.shape), clamp(0.4 + 0.6 * moss * smooth(1.0, 0.2, c.R))[..., None])
    ink = Ink(c)
    g = rng(8)
    def branch(x, y, a, length, w, depth):
        pts = [(x + math.sin(a + 0.15 * math.sin(t * 5)) * length * t, y - math.cos(a + 0.15 * math.sin(t * 5)) * length * t) for t in np.linspace(0, 1, 12)]
        ink.brush(pts, w, 255, 'tail')
        if depth:
            ex, ey = pts[-1]
            for s in (-1, 1):
                branch(ex, ey, a + s * g.uniform(0.35, 0.7), length * 0.62, w * 0.62, depth - 1)
    for k in range(7):
        branch(0, 0, k * TAU / 7 + 0.2, 0.42, 0.07, 3)
    silver = ink.arr(0.004)
    col = mix(col, flat('#DCE6EC', c.shape) * (0.75 + 0.25 * smooth(-0.5, 0.5, -c.Y - c.X))[..., None], silver[..., None])
    col = col + V([0.7, 0.9, 0.85]) * (0.2 * blur(silver, 8 * c.ss))[..., None]
    col = col + rgb('#E8E2A0') * (0.8 * stars(c, 70, 5, 0.1, 0.95, 0.004, 0.7))[..., None]
    c.put(col, c.cover(d))
    K.put(c, 'grove')


def leaves():
    tones = ['#8AC2A0', '#B8D8C4', '#D8C88A', '#9AB8D8']
    def one(c, k):
        pts = bez((0, 0.95), (0.85, 0.4), (0.62, -0.62), (0, -0.98), 20) + bez((0, -0.98), (-0.62, -0.62), (-0.85, 0.4), (0, 0.95), 20)
        d = c.poly(pts)
        t = clamp(-d / 0.4)
        vein = gauss(c.X, 0.012) * smooth(0.95, -0.9, c.Y) + 0.5 * gauss(np.abs(c.X) * 1.2 - (c.Y + 1) * 0.35 % 0.3, 0.01) * smooth(0.0, 0.3, np.abs(c.X))
        H = 0.08 * np.sqrt(t) - 0.01 * vein
        alb = mix(flat(tones[k], c.shape), flat('#F4F8F4', c.shape), (0.3 * vein + 0.25 * smooth(0, 1, -c.Y))[..., None])
        col = metal(c, H, alb, rough=0.25, grime=0.2, seed=20 + k, studio=COOL, met=0.75)
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'leaves', 4, one)


def moon():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    rimz = smooth(0.82, 0.84, c.R)
    knot = 0.5 + 0.5 * np.sin(c.A * 12 + np.sin(c.A * 36) * 0.8)
    H = (0.05 + 0.02 * knot) * np.sqrt(clamp(1 - ((c.R - 0.90) / 0.07) ** 2)) * rimz
    rim = metal(c, H, flat('#D0D8E0', c.shape), rough=0.22, grime=0.4, seed=5, studio=COOL)
    face = mix(flat('#1E3A36', c.shape), flat('#0C1E1C', c.shape), smooth(0.0, 0.82, c.R)[..., None])
    face = face + V([0.85, 0.9, 0.8]) * (0.15 * gauss(c.R - 0.74, 0.008))[..., None]
    col = mix(face, rim, rimz[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'moon')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#E8F0B0')
    c = K.canvas(40, 4)  # a firefly
    c.col[:] = rgb('#F4F0A0')
    c.alpha = ((1 - smooth(0.0, 1.0, c.R)) ** 2).astype(F)
    K.put(c, 'firefly', how='png', tone=False)


K.run([grove, leaves, moon])
P = dict(base='#0C1F1C', accent='#C9E6D8', accent2='#E8D58A', text='#EEF6F0', sub='#B8D0C4', panel=('#1A3430', '#0C1F1C'), stroke='#C9E6D8', tile=('#EEF6F0', '#CFE2D8'), tilestroke='#8AB8A4',
         ink='#0C1F1C', dim=0.48, font='Gabriola, Constantia', badge='#E8D58A', badgeink='#0C1F1C')
finish(K, P, sounds='celesta',
       back=[soft(1.08, 0.03, 60), img('grove', 1.0, rotate='(1-open)*-12', intro=intro(0.5, 'out', scale=0.9))],
       under=[img('halo', '1.6*hot', opacity='hot*0.5', when='hot>0.02'), img('leaves', '1.08*(1+0.05*hot-0.04*press)', frame='(i+ring)%4', rotate='a+4*sin(time*1.6+seed*6)')],
       icon=dict(size=0.56, zoom=1.18, shadow=dict(x=0, y=1, blur=3, color='black/50')),
       hub=[img('moon', 1.0, intro=intro(0.5, 'back', scale=0.6))],
       over=[img('firefly', '0.10*(1+0.3*sin(time*6))', **{'in': 'hub'}, angle='sel+8*sin(time*3)', radius='1.12+0.04*sin(time*2.3)', opacity='on')],
       words_kw=dict(px=20, clockpx=34, datepx=14),
       style=dict(open='bloom', speed=0.9, tilt=0.3),
       onhover=[dict(image='firefly', count=6, area='slot', life=[0.6, 1.2], size=[3, 6], speed=[10, 40], dir=[-180, 180], swirl=90, fadein=0.2, fadeout=0.5)],
       onlaunch=[dict(image='firefly', count=22, area='slot', life=[0.6, 1.3], size=[3, 7], speed=[60, 200], outward=True, dir=[-100, 100], drag=1.5, fadein=0, fadeout=0.5)],
       screen=dict(effect='fireflies', color='#C8F070', color2='#FFF6B0', density=1.0, speed=0.7, size=1.0))
