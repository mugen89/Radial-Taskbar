"""Billiards: blue cloth inside a cherry-wood rail with pockets; polished balls carry the apps and nudge
each other, the cue ball in the middle."""
from lineup import *

K = Kit('billiards', 'Billiards', 'Blue cloth in a cherry-wood rail with pockets; polished balls carry the apps, the cue ball sits in the middle', ['game', 'pub', 'blue'])
K.flag(halo='light')
BALLS = [('#F2C21E', False), ('#2A4AC8', False), ('#D2282A', True), ('#6A2A9A', False), ('#F27A1E', True), ('#1E8A4A', False), ('#8A1E2A', True), ('#141414', False)]


def table():
    c = K.canvas(1080, 2)
    d = c.R - 0.99
    cloth = mix(flat('#1E6AA8', c.shape), flat('#0E3E6E', c.shape), smooth(0.0, 0.9, c.R)[..., None]) * (0.93 + 0.07 * fbm(c.shape, 160, 3, 2))[..., None]
    rail = smooth(0.86, 0.87, c.R)
    wd, wh = wood(c, 6, scale=1.4, light='#9A3A22', dark='#4A1608', ring=7)
    H = 0.06 * np.sqrt(clamp(1 - ((c.R - 0.93) / 0.065) ** 2)) * rail + 0.003 * wh * rail
    col = mix(cloth * (1 - 0.35 * gauss(c.R - 0.86, 0.02))[..., None], surface(c, H, wd, WARM, rough=0.25, clear=0.9, reach=0.1), rail[..., None])
    sights = np.zeros(c.shape, F)
    for k in range(18):
        x, y = c.polar(k * TAU / 18 + TAU / 36, 0.93)
        sights = np.maximum(sights, c.cover(c.regular(4, 0.012, x=x, y=y)))
    col = mix(col, flat('#F2EAD8', c.shape), sights[..., None])
    pockets = np.zeros(c.shape, F)
    for k in range(6):
        x, y = c.polar(k * TAU / 6, 0.885)
        pockets = np.maximum(pockets, c.cover(c.circle(0.055, x, y)))
    col = mix(col, flat('#060606', c.shape), pockets[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'table')


def balls():
    def one(c, k):
        colr, stripe = BALLS[k]
        d = c.R - 0.88
        H = lens(clamp(-d / 0.88), 0.45, 2.0)
        alb = rgb(colr) * np.ones(c.shape + (3,), F)
        if stripe:
            alb = np.where((np.abs(c.Y) > 0.42)[..., None], rgb('#F6F2E8'), alb) * np.ones(c.shape + (3,), F)
        alb = mix(alb, flat('#F6F2E8', c.shape), c.cover(c.R - 0.46)[..., None])
        col = surface(c, H, alb.astype(F), WARM, rough=0.12, clear=1.0, reach=0.1)
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'balls', 8, one)


def cue():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    H = lens(clamp(-d / 0.96), 0.4, 2.0)
    col = surface(c, H, flat('#F6F2E8', c.shape), WARM, rough=0.1, clear=1.0, reach=0.1)
    c.put(col, c.cover(d), H)
    K.put(c, 'cue')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFFFFF')
    c = K.canvas(40, 4, 1.0, 3.2)  # the tip of a cue, toward the middle
    stick = c.taper(0, -3.2, 0.42, 0, 2.6, 0.22)
    tip = c.capsule(0, 2.6, 0, 3.0, 0.22)
    alb = np.where((tip < 0)[..., None], rgb('#3A7AC8'), np.where((c.Y > 2.2)[..., None], rgb('#F2EAD8'), rgb('#C8964A'))) * np.ones(c.shape + (3,), F)
    H = 0.2 * np.sqrt(clamp(1 - (c.X / 0.42) ** 2))
    c.put(surface(c, H, alb.astype(F), WARM, rough=0.3, clear=0.6), c.cover(np.minimum(stick, tip)), H)
    K.put(c, 'stick', how='png')


K.run([table, balls, cue])
P = dict(base='#0A2A3A', accent='#D9B45A', accent2='#FFFFFF', text='#1A1A1E', sub='#4A4A4E', panel=('#1E6AA8', '#0E3E6E'), stroke='#9A3A22', tile=('#F6F2E8', '#DCD6C8'), tilestroke='#6A2A12',
         ink='#1A1A1E', paneltext='#F6F2E8', dim=0.38, font='Bahnschrift, Segoe UI', badge='#141414', badgeink='#F6F2E8')
nudge = '0.04*sin(time*14+seed*9)*hot'
finish(K, P, sounds='billiard',
       back=[soft(1.10, 0.04, 65), img('table', 1.0, intro=intro(0.35, 'out', scale=0.94))],
       under=[img('halo', '1.6*hot', opacity='hot*0.45', when='hot>0.02'), soft(0.95, 0.07, 50), img('balls', '0.94*(1+0.05*hot-0.04*press)', frame='(i+ring)%8', x=nudge, rotate='seed*40-20')],
       icon=dict(size=0.42, zoom=1.2, shadow=dict(x=0, y=1, blur=1, color='black/30')),
       hub=[soft(1.0, 0.06, 45), img('cue', 1.0, intro=intro(0.4, 'back', scale=0.6))],
       over=[img('stick', [0.05, 0.16], **{'in': 'hub'}, angle='sel', radius=1.22, rotate='sel+180', opacity='on')],
       words_kw=dict(shadow=dict(x=0, y=0, blur=2, color='#F6F2E8')),
       tabs=dict(inset=13, text='#F6F2E8', fill='#FFFFFF/12', on='#D9B45A/85'),
       style=dict(open='bloom', tilt=0.3),
       onlaunch=[dict(color='#F6F2E8', count=14, area='slot', life=[0.3, 0.6], size=[1.5, 3], speed=[100, 300], outward=True, dir=[-80, 80], drag=2.2, fadein=0, fadeout=0.5)])
