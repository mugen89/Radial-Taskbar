"""Silken Caves: dark blue rock strung with silk, spools of thread for the apps, pale moths glowing in the dark."""
from lineup import *

K = Kit('silk', 'Silken Caves', 'Dark blue rock strung with silk threads; apps sit on spools of thread while pale moths glow', ['cave', 'dark', 'calm'])
K.flag(halo='light')


def cave():
    c = K.canvas(1080, 2)
    edge = 0.97 + 0.02 * fbm(c.shape, 7, 2, 3)
    d = c.R - edge
    H = 0.05 * fbm(c.shape, 5, 3, 5) + 0.02 * fbm(c.shape, 24, 4, 3, ridged=True)
    alb = mix(flat('#1A2236', c.shape), flat('#34405C', c.shape), clamp(0.5 + 0.6 * fbm(c.shape, 8, 5, 4))[..., None])
    col = surface(c, H, alb, COOL, rough=0.75, reach=0.12)
    silk = np.zeros(c.shape, F)
    g = rng(11)
    for _ in range(9):
        a0, a1 = g.random() * TAU, g.random() * TAU
        p0, p1 = c.polar(a0, 0.95), c.polar(a1, 0.95)
        mid = ((p0[0] + p1[0]) / 2 * 0.6, (p0[1] + p1[1]) / 2 * 0.6 + 0.12)
        pts = bez(p0, mid, mid, p1, 60)
        silk = np.maximum(silk, Ink(c).line(pts, 0.004).arr(0.002))
    moss = np.zeros(c.shape, F)
    for _ in range(18):
        x, y = c.polar(g.random() * TAU, g.uniform(0.2, 0.92))
        moss = moss + gauss(np.hypot(c.X - x, c.Y - y), 0.03)
    col = col + V([0.85, 0.9, 1.0]) * (0.7 * silk)[..., None] + rgb('#7FB8FF') * (0.35 * clamp(moss))[..., None]
    c.put(col, c.cover(d), H)
    K.put(c, 'cave')


def spools():
    threads = ['#EDE6D8', '#C98A9A', '#5FA3A6', '#B8C0CC']
    def one(c, k):
        d = c.R - 0.90
        flange = smooth(0.80, 0.82, c.R)
        wound = smooth(0.30, 0.32, c.R) * (1 - flange)
        lines = 0.5 + 0.5 * np.sin(c.R * 260 + 0.6 * np.sin(c.A * 3))
        H = 0.05 * flange + 0.03 * wound * (0.8 + 0.2 * lines) + 0.06 * (1 - wound - flange)
        wd, wh = wood(c, 12 + k, scale=1.0, light='#C9A27A', dark='#8A6440', ring=5)
        alb = mix(wd, flat(threads[k], c.shape) * (0.8 + 0.25 * lines)[..., None], wound[..., None])
        col = surface(c, H, alb, COOL, rough=0.6, reach=0.06, sheen=0.4)
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'spools', 4, one)


def nest():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    base = mix(flat('#1C2438', c.shape), flat('#0C1220', c.shape), smooth(0.0, 0.9, c.R)[..., None])
    sw = np.zeros(c.shape, F)
    for k in range(5):
        sw = np.maximum(sw, gauss(np.sin(c.A * 3 + c.R * (10 + k * 2) + k) * 0.02 + c.R - (0.80 + 0.03 * k), 0.006))
    col = base + V([0.85, 0.9, 1.0]) * (0.6 * sw)[..., None]
    c.put(col, c.cover(d))
    K.put(c, 'nest')
    halo(K, 'halo', 220, 2.0, 0.25, tint='#BFD4F2')
    c = K.canvas(64, 4, 1.0, 1.0)  # a moth
    wings = np.minimum(np.hypot((c.X - 0.38) / 0.42, (c.Y + 0.15) / 0.55) - 1, np.hypot((c.X + 0.38) / 0.42, (c.Y + 0.15) / 0.55) - 1)
    lower = np.minimum(np.hypot((c.X - 0.25) / 0.28, (c.Y - 0.45) / 0.35) - 1, np.hypot((c.X + 0.25) / 0.28, (c.Y - 0.45) / 0.35) - 1)
    body = c.capsule(0, -0.5, 0, 0.6, 0.08)
    sh = np.minimum(np.minimum(wings * 0.3, lower * 0.25), body)
    c.col = (rgb('#E8EEFA') * (0.8 + 0.2 * smooth(-0.6, 0.6, -c.Y))[..., None] * np.ones(c.shape + (3,), F)).astype(F)
    c.alpha = c.cover(sh)
    K.put(c, 'moth', how='png', tone=False)


K.run([cave, spools, nest])
P = dict(base='#121826', accent='#BFD4F2', accent2='#E8C8D2', text='#EEF2FA', sub='#AEBBD6', panel=('#1E2638', '#101622'), stroke='#8A9AB8', tile=('#E8ECF4', '#C8D0DE'), tilestroke='#6A7A98',
         ink='#121826', dim=0.55, font='Gabriola, Constantia', badge='#BFD4F2', badgeink='#121826')
finish(K, P, sounds='celesta',
       back=[soft(1.10, 0.03, 70), img('cave', 1.0, intro=intro(0.45, 'out', scale=0.92))],
       under=[img('halo', '1.6*hot', opacity='hot*0.5', when='hot>0.02'), img('spools', '1.0*(1+0.05*hot-0.04*press)', frame='(i+ring)%4', rotate='time*20*hot+seed*90')],
       icon=dict(size=0.52, zoom=1.2, shadow=dict(x=0, y=1, blur=3, color='black/50')),
       hub=[img('nest', 1.0, intro=intro(0.45, 'back', scale=0.6))],
       over=[img('moth', [0.10, 0.10], **{'in': 'hub'}, angle='sel', radius=1.12, rotate='sel+6*sin(time*14)', opacity='on')],
       words_kw=dict(px=20, clockpx=34, datepx=14),
       style=dict(open='fade', speed=0.9, tilt=0.3),
       particles=[dict(image='moth', rate=0.4, max=3, area='stage', life=[4, 6], size=[8, 12], speed=[10, 25], dir=[-180, 180], sway=30, swayhz=2.5, opacity=0.8, fadein=0.2, fadeout=0.3)],
       onlaunch=[dict(image='moth', count=8, area='slot', life=[0.8, 1.4], size=[8, 13], speed=[60, 180], outward=True, dir=[-80, 80], drag=1.2, sway=40, swayhz=4, fadein=0, fadeout=0.4)],
       screen=dict(effect='fireflies', color='#9FC4FF', color2='#EEF4FF', density=0.9, speed=0.6, size=0.9))
