"""Marble and Gold: polished white stone with inlaid gold, black marble medallions, very quiet."""
from lineup import *

K = Kit('marble', 'Marble and Gold', 'Polished white stone with inlaid gold lines and black marble medallions; very quiet', ['elegant', 'light', 'gold'])
K.flag(halo='light')
K.font('cinzel', 'Cinzel[wght].ttf')
GOLD = '#D4AF5A'


def veins(c, seed, scale=2.5):
    w = c.X * scale + 1.6 * fbm(c.shape, 3, seed, 5)
    v1 = gauss(np.sin(w * 2.2 + c.Y * scale * 0.8) * 0.5, 0.05)
    v2 = gauss(np.sin(w * 5.3 - c.Y * scale * 1.7 + 2) * 0.5, 0.03) * 0.5
    return clamp((v1 + v2) * (0.5 + 0.6 * fbm(c.shape, 8, seed + 1, 3)))


def slab():
    c = K.canvas(1080, 2)
    d = c.R - 0.995
    alb = mix(flat('#F4F2EE', c.shape), flat('#E4E0D8', c.shape), clamp(0.5 + 0.5 * fbm(c.shape, 4, 2, 4))[..., None])
    alb = mix(alb, flat('#8A8C92', c.shape), (0.55 * veins(c, 3))[..., None])
    gold = gauss(c.R - 0.955, 0.006) + gauss(c.R - 0.945, 0.002) + gauss(c.R - 0.47, 0.004)
    n = 12
    a = (c.A % (TAU / n)) - TAU / n / 2
    gold = gold + gauss(c.R * np.abs(a), 0.0025) * smooth(0.47, 0.50, c.R) * smooth(0.95, 0.92, c.R) * 0.7
    gold = clamp(gold)
    H = 0.004 * gold
    col = surface(c, H, alb, SOFT, rough=0.12, clear=1.0, reach=0.05)
    col = mix(col, metal(c, H, flat(GOLD, c.shape), rough=0.2, grime=0.1, seed=4, studio=WARM), gold[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'slab')


def medallions():
    def one(c, k):
        d = c.R - 0.90
        rimz = smooth(0.74, 0.76, c.R)
        H = 0.05 * np.sqrt(clamp(1 - ((c.R - 0.83) / 0.07) ** 2)) * rimz + 0.02 * (1 - rimz)
        stone = mix(flat('#16161A', c.shape), flat('#2A2A30', c.shape), clamp(0.5 + 0.5 * fbm(c.shape, 4, 10 + k, 3))[..., None]) if k == 0 else \
            mix(flat('#F2F0EC', c.shape), flat('#DCD8D0', c.shape), clamp(0.5 + 0.5 * fbm(c.shape, 4, 10 + k, 3))[..., None])
        stone = mix(stone, flat('#E8E6E2' if k == 0 else '#6A6C72', c.shape), (0.6 * veins(c, 20 + k, 3.5))[..., None])
        col = surface(c, H, stone, SOFT, rough=0.1, clear=1.0, reach=0.05)
        col = mix(col, metal(c, H, flat(GOLD, c.shape), rough=0.18, grime=0.1, seed=6 + k, studio=WARM), rimz[..., None])
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'medallions', 2, one)


def centre():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    rimz = smooth(0.82, 0.84, c.R)
    H = 0.05 * np.sqrt(clamp(1 - ((c.R - 0.90) / 0.07) ** 2)) * rimz
    stone = mix(flat('#121216', c.shape), flat('#26262C', c.shape), clamp(0.5 + 0.5 * fbm(c.shape, 4, 7, 3))[..., None])
    stone = mix(stone, flat('#D8D6D2', c.shape), (0.35 * veins(c, 30, 2.5))[..., None])
    col = surface(c, H, stone, SOFT, rough=0.1, clear=1.0, reach=0.05)
    col = mix(col, metal(c, H, flat(GOLD, c.shape), rough=0.18, grime=0.1, seed=3, studio=WARM), rimz[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'centre')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFE8B0')
    c = K.canvas(40, 4, 1.0, 1.0)
    dd = c.regular(4, 0.95)
    c.put(metal(c, 0.15 * clamp(-dd / 0.4), flat(GOLD, c.shape), rough=0.2, grime=0.1, seed=2, studio=WARM), c.cover(dd))
    K.put(c, 'gem', how='png')


K.run([slab, medallions, centre])
P = dict(base='#1A1A1E', accent=GOLD, accent2='#F4F0E8', text='#F4ECD8', sub='#C8B88A', panel=('#26262C', '#121216'), stroke=GOLD, tile=('#F4F2EE', '#E0DCD4'), tilestroke='#B8964A',
         ink='#1A1A1E', dim=0.32, font=dict(file='Cinzel[wght].ttf', family='Cinzel'), badge=GOLD, badgeink='#1A1A1E')
finish(K, P, sounds='celesta',
       back=[soft(1.08, 0.03, 55), img('slab', 1.0, intro=intro(0.5, 'out', scale=0.94))],
       under=[img('halo', '1.5*hot', opacity='hot*0.45', when='hot>0.02'), soft(0.98, 0.05, 40), img('medallions', '0.98*(1+0.04*hot-0.03*press)', frame='(i+ring)%2', rotate='seed*360')],
       icon=dict(size=0.56, zoom=1.14, shadow=dict(x=0, y=1, blur=3, color='black/40')),
       hub=[img('centre', 1.0, intro=intro(0.5, 'back', scale=0.7))],
       over=[img('gem', [0.05, 0.05], **{'in': 'hub'}, angle='sel', radius=1.10, rotate='sel+45', opacity='on')],
       words_kw=dict(px=16, clockpx=29),
       tabs=dict(inset=13, text='#3A3A40', fill='#00000012', on='#D4AF5A/85'),
       style=dict(open='fade', speed=0.8, tilt=0.25),
       onlaunch=[dict(color='#F2D88A', count=16, area='slot', life=[0.4, 0.9], size=[1.2, 2.6], speed=[40, 160], outward=True, dir=[-90, 90], drag=2, fadein=0, fadeout=0.5)])
