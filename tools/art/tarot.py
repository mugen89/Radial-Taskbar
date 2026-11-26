"""Tarot: gold line art on midnight blue; every app is a card that turns over when you point at it, a sun in the middle,
gold stars drifting outside."""
from lineup import *

K = Kit('tarot', 'Tarot', 'Gold line art on midnight blue; cards turn over when you point at them, a sun shines in the middle', ['mystic', 'gold', 'dark'])
K.flag(halo='light')
K.font('cinzel', 'Cinzel[wght].ttf')
GOLD = '#D9B45A'


def lines(c, w):
    """Celestial line art as coverage."""
    ink = Ink(c)
    for r in (0.30, 0.46, 0.94, 0.975):
        ink.line(arcpts(r, 0, TAU, 220), w)
    for k in range(12):
        a = k * TAU / 12
        ink.line([c.polar(a, 0.46), c.polar(a, 0.94)], w * 0.6)
        x, y = c.polar(a + TAU / 24, 0.90)
        ink.dot(x, y, w * 2.2)
    for k in range(24):
        a = k * TAU / 24
        ink.line([c.polar(a, 0.30), c.polar(a, 0.40 if k % 2 else 0.44)], w * 0.7)
    g = rng(4)
    for _ in range(9):  # constellations
        a0, r0 = g.random() * TAU, g.uniform(0.55, 0.85)
        pts = [c.polar(a0 + g.uniform(-0.15, 0.15) * j, r0 + g.uniform(-0.06, 0.06)) for j in range(4)]
        ink.line(pts, w * 0.5)
        for p in pts:
            ink.dot(p[0], p[1], w * 1.6)
    return ink.arr(w * 0.25)


def sky():
    c = K.canvas(1080, 2)
    d = c.R - 0.995
    col = mix(flat('#1A2250', c.shape), flat('#0A0E24', c.shape), smooth(0.0, 1.0, c.R)[..., None])
    col = col + V([0.9, 0.9, 1.0]) * (0.5 * stars(c, 120, 3, 0.0, 0.99, 0.003, 0.6))[..., None]
    gold = lines(c, 0.0045)
    col = mix(col, flat(GOLD, c.shape) * (0.85 + 0.3 * smooth(-0.6, 0.6, -c.Y - c.X))[..., None], (gold * 0.9)[..., None])
    c.put(col, c.cover(d))
    K.put(c, 'sky')


def cards():
    def one(c, k):
        d = c.box(0.60, 0.92, r=0.07)
        col = mix(flat('#1C2658', c.shape), flat('#0E1434', c.shape), smooth(-0.9, 0.9, c.Y)[..., None]) if k == 0 else mix(flat('#F4EAD0', c.shape), flat('#E0D0A8', c.shape), smooth(-0.9, 0.9, c.Y)[..., None])
        ink = Ink(c)
        ink.line([(-0.52, -0.84), (0.52, -0.84), (0.52, 0.84), (-0.52, 0.84)], 0.02, closed=True)
        if k == 0:
            for r in (0.18, 0.30):
                ink.line(arcpts(r, 0, TAU, 60), 0.012)
            for j in range(8):
                a = j * TAU / 8
                ink.line([c.polar(a, 0.34), c.polar(a, 0.46)], 0.012)
        else:
            ink.line(arcpts(0.40, 0, TAU, 60), 0.014)
        cov = ink.arr(0.004)
        col = mix(col, flat(GOLD if k == 0 else '#8A6A2A', c.shape), cov[..., None])
        H = 0.02 * clamp(-d / 0.05)
        col = surface(c, H, col, WARM, rough=0.5, reach=0.05)
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'cards', 2, one)


def sun():
    c = K.canvas(460, 2)
    d = c.R - 0.97
    rays = np.abs(((c.A / TAU * 32) % 1) - 0.5)
    face = mix(flat('#1A2250', c.shape), flat('#0A0E24', c.shape), smooth(0.0, 0.9, c.R)[..., None])
    gold = gauss(c.R - 0.94, 0.008) + gauss(c.R - 0.70, 0.006) + smooth(0.30, 0.24, rays) * smooth(0.72, 0.74, c.R) * smooth(0.92, 0.90, c.R)
    col = mix(face, flat(GOLD, c.shape), clamp(gold)[..., None])
    c.put(col, c.cover(d))
    K.put(c, 'sun')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFE6A0')
    c = K.canvas(48, 4, 1.0, 1.0)
    st = c.star(4, 0.95, 0.25)
    c.col[:] = rgb('#F2DFA0')
    c.alpha = c.cover(st)
    K.put(c, 'spark', how='png', tone=False)


K.run([sky, cards, sun])
P = dict(base='#0E1430', accent=GOLD, accent2='#F2DFA0', text='#F6EBCF', sub='#D9C79A', panel=('#1C2658', '#0E1434'), stroke=GOLD, tile=('#F4EAD0', '#E0D0A8'), tilestroke='#8A6A2A',
         ink='#0E1430', dim=0.5, font=dict(file='Cinzel[wght].ttf', family='Cinzel'), badge=GOLD, badgeink='#0E1430')
flip = 'abs(cos(sat(hot)*3.14159))'
finish(K, P, sounds='celesta',
       back=[soft(1.08, 0.03, 60), img('sky', 1.0, rotate='time*0.6+(1-open)*-30', intro=intro(0.5, 'out', scale=0.9))],
       under=[img('halo', '1.6*hot', opacity='hot*0.5', when='hot>0.02'), soft(0.9, 0.06, 45),
              img('cards', '1.02*(1+0.06*hot-0.04*press)', frame='hot>0.5 ? 1 : 0', rotate='a', scale=['max(0.04,' + flip + ')', '1'])],
       icon=dict(size=0.52, zoom=1.12, opacity='hot>0.5 ? 1 : 0.9', shadow=dict(x=0, y=1, blur=3, color='black/50')),
       hub=[img('sun', 1.0, rotate='time*-2', intro=intro(0.5, 'back', scale=0.6))],
       over=[img('spark', '0.10*(1+0.2*sin(time*5))', **{'in': 'hub'}, angle='sel', radius=1.10, rotate='time*40', opacity='on')],
       words_kw=dict(px=16, clockpx=29),
       style=dict(open='fade', speed=0.9, tilt=0.3),
       onlaunch=[dict(image='spark', count=18, area='slot', life=[0.5, 1.0], size=[5, 10], speed=[60, 220], outward=True, dir=[-100, 100], drag=1.5, spin=[-200, 200], fadein=0, fadeout=0.5)],
       screen=dict(effect='stars', color='#F2DFA0', color2='#FFFFFF', density=0.6, speed=0.4, size=0.9))
