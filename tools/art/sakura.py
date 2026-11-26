"""Cherry Blossom: a dark branch across a soft spring sky; apps sit in blossoms, pink petals ride the wind."""
from lineup import *

K = Kit('sakura', 'Cherry Blossom', 'A dark branch across a soft spring sky; apps sit in blossoms while pink petals ride the wind', ['nature', 'spring', 'pink'])
K.flag(halo='light')


def blossom(c, size, x=0.0, y=0.0, rot=0.0, tone='#FBC6D5'):
    """Coverage and colour of a five-petalled cherry blossom."""
    cov = np.zeros(c.shape, F)
    col = flat(tone, c.shape)
    for k in range(5):
        a = k * TAU / 5 + rot
        pts = turned(bez((0, 0), (0.42, -0.25), (0.46, -0.90), (0.07, -0.92), 12) + [(0, -0.80)] + bez((-0.07, -0.92), (-0.46, -0.90), (-0.42, -0.25), (0, 0), 12), a, size, x, y)
        p = Ink(c).poly(pts).arr(0.008)
        t = clamp(((c.X - x) * math.sin(a) - (c.Y - y) * math.cos(a)) / size)
        col = mix(col, ramp(t, '#D85A80', '#F4A2BC', '#FFE8F0'), p[..., None])
        cov = np.maximum(cov, p)
    return cov, col


def sky():
    c = K.canvas(1080, 2)
    d = c.R - 0.99
    col = mix(flat('#EAD0DC', c.shape), flat('#9CB4D8', c.shape), smooth(-0.9, 0.9, c.Y)[..., None])
    ink = Ink(c)
    trunk = bez((-1.1, 0.55), (-0.4, 0.35), (0.1, -0.1), (1.1, -0.55), 40)
    ink.brush(trunk, 0.09, 255, 'even', seed=4, rough=0.15)
    for (t0, a, l) in ((0.3, -1.2, 0.35), (0.55, 0.9, 0.3), (0.7, -1.4, 0.4), (0.45, 2.2, 0.25)):
        x, y = trunk[int(t0 * 40)]
        pts = [(x + math.sin(a) * l * s, y - math.cos(a) * l * s + 0.05 * math.sin(s * 3)) for s in np.linspace(0, 1, 12)]
        ink.brush(pts, 0.035, 255, 'tail')
    wood = ink.arr(0.004)
    col = mix(col, flat('#3A2420', c.shape) * (0.85 + 0.25 * fbm(c.shape, 30, 3, 2))[..., None], wood[..., None])
    g = rng(9)
    for _ in range(26):
        t = g.uniform(0.05, 0.95)
        x, y = trunk[int(t * 40)]
        x += g.uniform(-0.12, 0.12)
        y += g.uniform(-0.12, 0.12)
        cov, bc = blossom(c, g.uniform(0.035, 0.06), x, y, g.random())
        col = mix(col, bc, cov[..., None])
    c.put(col, c.cover(d))
    K.put(c, 'sky')


def flowers():
    def one(c, k):
        cov, col = blossom(c, 0.98, rot=k * 0.3, tone='#F4A2BC' if k == 0 else '#FFD0E0')
        ink = Ink(c)
        for j in range(14):
            a = j * TAU / 14
            ink.line([(0, 0), turned([(0, -0.34)], a)[0]], 0.022)
            ink.dot(*turned([(0, -0.36)], a)[0], 0.035)
        col = mix(col, flat('#C9304F', c.shape), (ink.arr(0.006) * 0.85)[..., None])
        c.col, c.alpha = col.astype(F), cov
        return c
    plate(K, 'flowers', 2, one)


def paper():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    alb = flat('#FBF4EA', c.shape) * (0.95 + 0.05 * fbm(c.shape, 60, 3, 2))[..., None]
    alb = mix(alb, flat('#C8303A', c.shape), (0.8 * gauss(c.R - 0.90, 0.006))[..., None])
    col = surface(c, 0.02 * clamp(-d / 0.05), alb, SOFT, rough=0.9)
    c.put(col, c.cover(d))
    K.put(c, 'paper')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFD8E4')
    ims = []
    for k in range(4):
        c = K.canvas(64, 4)
        a = k * 1.1
        pts = turned(bez((0, 0.9), (0.85, 0.3), (0.55, -0.85), (0.08, -0.78), 14) + [(0, -0.6)] + bez((-0.08, -0.78), (-0.55, -0.85), (-0.80, 0.3), (0, 0.9), 14), a, 0.92)
        cov = Ink(c).poly(pts).arr(0.02)
        t = clamp(0.5 + 0.5 * (c.X * math.sin(a) - c.Y * math.cos(a)))
        c.col = ramp(t, '#F3A9BE', '#FBD6E0', '#FFF3F6')
        c.alpha = cov
        ims.append(c.image(tone=False))
    K.sheet(ims, 4, 'petals')
    K.flags['petals'] = dict(cols=4)


K.run([sky, flowers, paper])
P = dict(base='#3A2A34', accent='#F2A6C0', accent2='#FFE6EE', text='#3A2A34', sub='#6A4A5A', panel=('#FBF4EA', '#F0E2D8'), stroke='#C8303A', tile=('#FBF4EA', '#F0E2D8'), tilestroke='#C89AA8',
         ink='#3A2A34', paneltext='#3A2A34', dim=0.22, font='Gabriola, Constantia', badge='#C8303A', badgeink='#FBF4EA')
finish(K, P, sounds='sand',
       back=[soft(1.06, 0.02, 40), img('sky', 1.0, intro=intro(0.5, 'out', scale=0.92))],
       under=[img('halo', '1.5*hot', opacity='hot*0.5', when='hot>0.02'), img('flowers', '1.22*(1+0.06*hot-0.04*press)', frame='hot>0.5 ? 1 : 0', rotate='seed*72+4*sin(time*1.5+seed*6)')],
       icon=dict(size=0.44, zoom=1.22, shadow=dict(x=0, y=1, blur=2, color='#3A2A34/40')),
       hub=[soft(1.0, 0.05, 35), img('paper', 1.0, intro=intro(0.5, 'back', scale=0.6))],
       over=[img('petals', [0.08, 0.08], **{'in': 'hub'}, frame='0', angle='sel', radius=1.10, rotate='sel+10*sin(time*3)', opacity='on')],
       words_kw=dict(px=20, clockpx=34, datepx=14, shadow=dict(x=0, y=0, blur=2, color='#FFFFFF')),
       tabs=dict(inset=13, text='#3A2A34', fill='#FFFFFF/45', on='#F2A6C0/85'),
       style=dict(open='bloom', speed=0.9, tilt=0.3),
       particles=[dict(image='petals', rate=1.2, max=10, area='stage', life=[3, 5.5], size=[6, 11], speed=[8, 18], dir=[110, 200], gravity=6, spin=[-70, 70], sway=24, swayhz=0.35, opacity=0.95, fadein=0.15, fadeout=0.3)],
       onlaunch=[dict(image='petals', count=30, area='slot', life=[0.6, 1.2], size=[7, 14], speed=[80, 300], outward=True, dir=[-120, 120], gravity=120, drag=2.2, sway=20, swayhz=0.8, spin=[-260, 260], fadein=0, fadeout=0.5)],
       screen=dict(effect='petals', color='#F2A6C0', color2='#FFE6EE', density=1.0, speed=0.8, size=1.0))
