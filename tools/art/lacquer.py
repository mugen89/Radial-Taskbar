"""Lacquer Box: deep red and black lacquer with gold dust pictures; apps rest on black lacquer with gold rims."""
from lineup import *

K = Kit('lacquer', 'Lacquer Box', 'Deep red and black lacquer sprinkled with gold dust; apps rest on black lacquer framed in gold', ['elegant', 'red', 'gold'])
K.flag(halo='light')
GOLD = '#D4AF5A'


def dust(c, seed, amount):
    sp = clamp(white(c.shape, seed) - 2.0) * 0.6
    return clamp(sp * amount)


def box():
    c = K.canvas(1080, 2)
    d = c.R - 0.995
    red = smooth(0.86, 0.87, c.R)
    base = mix(flat('#0C0606', c.shape), flat('#6A0A10', c.shape), red[..., None])
    waves = np.zeros(c.shape, F)
    for k in range(5):
        r = 0.20 + k * 0.13
        waves = np.maximum(waves, gauss(c.R - r - 0.03 * np.sin(c.A * (5 + k) + k), 0.006))
    cloud = clamp(fbm(c.shape, 3, 5, 4) * 1.5) * (1 - red)
    gold = clamp(waves * 0.8 * (1 - red) + dust(c, 7, 1.0) * (0.25 + 0.75 * cloud) + gauss(c.R - 0.865, 0.004) + gauss(c.R - 0.975, 0.004))
    H = 0.002 * gold
    col = surface(c, H, base, SOFT, rough=0.06, clear=1.0, reach=0.05)
    col = mix(col, metal(c, H, flat(GOLD, c.shape), rough=0.25, grime=0.1, seed=4, studio=WARM), gold[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'box')


def trays():
    def one(c, k):
        d = c.box(0.80, 0.80, r=0.22)
        rimz = smooth(-0.10, -0.08, d)
        H = 0.04 * rimz + 0.01 * clamp(-d / 0.3)
        base = flat('#0C0606' if k == 0 else '#6A0A10', c.shape)
        gold = clamp(rimz + dust(c, 20 + k, 0.6) * smooth(-0.1, -0.4, d) * 0.6)
        col = surface(c, H, base, SOFT, rough=0.06, clear=1.0, reach=0.05)
        col = mix(col, metal(c, H, flat(GOLD, c.shape), rough=0.22, grime=0.1, seed=8 + k, studio=WARM), gold[..., None])
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'trays', 2, one)


def crest():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    base = flat('#7A0E14', c.shape)
    flower = np.zeros(c.shape, F)
    for k in range(5):
        a = k * TAU / 5
        x, y = c.polar(a, 0.80)
        flower = np.maximum(flower, gauss(np.hypot(c.X - x, c.Y - y) - 0.09, 0.008))
    gold = clamp(flower + gauss(c.R - 0.93, 0.008) + gauss(c.R - 0.68, 0.004) + dust(c, 30, 0.5) * smooth(0.6, 0.9, c.R))
    col = surface(c, 0.003 * gold, base, SOFT, rough=0.06, clear=1.0)
    col = mix(col, metal(c, 0.003 * gold, flat(GOLD, c.shape), rough=0.22, grime=0.1, seed=6, studio=WARM), gold[..., None])
    col = col * (1 - 0.3 * smooth(0.6, 0.0, c.R))[..., None]
    c.put(col, c.cover(d))
    K.put(c, 'crest')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFE0A0')
    c = K.canvas(40, 4)
    c.col[:] = rgb('#F2D88A')
    c.alpha = c.cover(c.star(4, 0.95, 0.3))
    K.put(c, 'fleck', how='png', tone=False)


K.run([box, trays, crest])
P = dict(base='#140606', accent=GOLD, accent2='#B8202A', text='#F2E2B8', sub='#C8B07A', panel=('#2A0A0C', '#140606'), stroke=GOLD, tile=('#F2E2B8', '#D8C08A'), tilestroke='#8A6A2A',
         ink='#140606', dim=0.42, font='Constantia, Georgia', badge=GOLD, badgeink='#140606')
finish(K, P, sounds='wood',
       back=[soft(1.08, 0.03, 65), img('box', 1.0, intro=intro(0.5, 'out', scale=0.94))],
       under=[img('halo', '1.5*hot', opacity='hot*0.5', when='hot>0.02'), img('trays', '0.94*(1+0.04*hot-0.03*press)', frame='(i+ring)%2', rotate='a')],
       icon=dict(size=0.58, zoom=1.14, shadow=dict(x=0, y=1, blur=3, color='black/60')),
       hub=[img('crest', 1.0, intro=intro(0.5, 'back', scale=0.7))],
       over=[img('fleck', '0.07*(1+0.2*sin(time*4))', **{'in': 'hub'}, angle='sel', radius=1.10, rotate='time*30', opacity='on')],
       words_kw=dict(shadow=dict(x=0, y=1, blur=3, color='black/80')),
       style=dict(open='fade', speed=0.85, tilt=0.3),
       onlaunch=[dict(image='fleck', count=20, area='slot', life=[0.5, 1.0], size=[3, 6], speed=[40, 180], outward=True, dir=[-90, 90], drag=2, spin=[-300, 300], fadein=0, fadeout=0.5)])
