"""Morning Dew: a spider's web strung with dew in soft morning light; every app is a drop that magnifies it."""
from lineup import *

K = Kit('dew', 'Morning Dew', 'A web strung with dew in soft morning light; every app is a clear drop that magnifies it', ['nature', 'fresh', 'light'])
K.flag(halo='light', drop='png')


def morning():
    c = K.canvas(1080, 2)
    d = c.R - 0.99
    bok = mix(flat('#5A8A4A', c.shape), flat('#B8D08A', c.shape), clamp(0.5 + 0.7 * fbm(c.shape, 3, 4, 3))[..., None])
    g = rng(5)
    for _ in range(22):
        x, y, r = g.uniform(-1, 1), g.uniform(-1, 1), g.uniform(0.05, 0.16)
        bok = bok + rgb('#FFF6C8') * (0.25 * smooth(r, r * 0.8, np.hypot(c.X - x, c.Y - y)))[..., None]
    n = 14
    a = (c.A % (TAU / n)) - TAU / n / 2
    spokes = gauss(c.R * np.abs(a), 0.002) * smooth(0.03, 0.06, c.R)
    sag = (a / (TAU / n / 2)) ** 2
    rings = np.zeros(c.shape, F)
    for r in np.arange(0.12, 0.96, 0.07):
        rings = np.maximum(rings, gauss(c.R - (r - 0.014 * sag * (0.6 + r)), 0.0018))
    silk = clamp(spokes + rings)
    beads = clamp(white(c.shape, 8) - 2.2) * silk * 3
    col = bok + V([1, 1, 0.95]) * (0.5 * silk + 0.9 * clamp(blur(beads, 1.5 * c.ss) * 3))[..., None]
    c.put(col, c.cover(d))
    K.put(c, 'morning')


def drops():
    def one(c, k):
        d = c.R - 0.86
        z = np.sqrt(clamp(1 - (c.R / 0.86) ** 2))
        rim = np.power(clamp(1 - z), 1.6)
        hl = gauss(np.hypot(c.X + 0.30, c.Y + 0.36), 0.11) * 1.2 + 0.5 * gauss(np.hypot(c.X - 0.30, c.Y - 0.42), 0.14)
        low = smooth(0.1, 0.9, c.Y) * z * 0.35
        col = mix(flat('#F6FFF0', c.shape), flat('#1E3A22', c.shape), (0.75 * rim)[..., None])
        col = mix(col, flat('#FFFFFF', c.shape), clamp(hl)[..., None])
        a = clamp(0.16 + 0.85 * rim + 0.9 * hl + low)
        c.col, c.alpha = col.astype(F), (a * c.cover(d)).astype(F)
        return c
    plate(K, 'drops', 2, one)


def bigdrop():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    z = np.sqrt(clamp(1 - (c.R / 0.96) ** 2))
    body = mix(flat('#DCEED0', c.shape), flat('#9CC28A', c.shape), smooth(-0.6, 0.9, c.Y)[..., None])
    rim = np.power(clamp(1 - z), 2.5)
    col = mix(body, flat('#3A5A32', c.shape), (0.6 * rim)[..., None]) + V([1, 1, 1]) * (gauss(np.hypot(c.X + 0.32, c.Y + 0.38), 0.10) * 1.2)[..., None]
    c.put(col, c.cover(d))
    K.put(c, 'bigdrop')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFF6C8')
    c = K.canvas(40, 4)
    c.col[:] = 1
    c.alpha = ((1 - smooth(0.0, 1.0, c.R)) ** 3).astype(F)
    K.put(c, 'glint', how='png', tone=False)


K.run([morning, drops, bigdrop])
P = dict(base='#1E3A22', accent='#BFE8C8', accent2='#FFF6C8', text='#1E3A22', sub='#3A5A3E', panel=('#EEF6E4', '#D4E6C4'), stroke='#7AA86A', tile=('#F4FAEE', '#DCEACC'), tilestroke='#7AA86A',
         ink='#1E3A22', paneltext='#1E3A22', dim=0.25, font='Candara, Segoe UI', badge='#1E3A22', badgeink='#F4FAEE')
finish(K, P, sounds='water',
       back=[soft(1.06, 0.02, 45), img('morning', 1.0, intro=intro(0.5, 'out', scale=0.92))],
       under=[img('halo', '1.5*hot', opacity='hot*0.5', when='hot>0.02'), soft(0.92, 0.10, 40)],
       icon=dict(size=0.58, zoom=1.32, shadow=dict(x=0, y=2, blur=4, color='#1E3A22/45')),
       slot_over=[img('drops', '1.0*(1+0.05*hot-0.04*press)', frame='hot>0.5 ? 1 : 0')],
       hub=[img('bigdrop', 1.0, intro=intro(0.5, 'back', scale=0.6))],
       over=[img('glint', '0.10*(1+0.3*sin(time*4))', **{'in': 'hub'}, angle='sel', radius=1.10, opacity='on')],
       words_kw=dict(shadow=dict(x=0, y=0, blur=3, color='#F4FAEE')),
       tabs=dict(inset=13, text='#1E3A22', fill='#FFFFFF/40', on='#7AA86A/85'),
       style=dict(open='bloom', speed=0.9, tilt=0.3),
       onlaunch=[dict(image='glint', count=18, area='slot', life=[0.4, 0.8], size=[4, 9], speed=[60, 220], outward=True, dir=[-90, 90], gravity=300, fadein=0, fadeout=0.5)])
