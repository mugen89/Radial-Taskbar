"""Ship's Wheel: a mahogany helm over the deep sea, gold and silver coins for the apps, a brass compass in the middle."""
from lineup import *

K = Kit('pirate', "Ship's Wheel", 'A mahogany helm over the deep sea; apps ride on gold coins, a brass compass sits in the middle', ['sea', 'adventure', 'warm'])
K.flag(halo='light')
BRASS = '#D9A441'


def sea():
    c = K.canvas(1080, 2)
    w = fbm(c.shape, 6, 3, 4)
    waves = 0.5 + 0.5 * np.sin(c.X * 30 + c.Y * 12 + 4 * w)
    col = mix(flat('#0A2E44', c.shape), flat('#155A78', c.shape), clamp(0.3 + 0.5 * waves * (0.5 + 0.5 * w))[..., None])
    foam = clamp((waves - 0.9) * 8) * clamp(fbm(c.shape, 30, 4, 2) + 0.3)
    col = col + V([0.8, 0.9, 0.95]) * (0.35 * foam)[..., None]
    col = col * (1 - 0.35 * smooth(0.6, 1.0, c.R))[..., None]
    c.put(col, c.cover(c.R - 0.98))
    K.put(c, 'sea')


def helm():
    c = K.canvas(1180, 2, 1.12)
    wd, wh = wood(c, 5, scale=1.6, light='#9A4E2A', dark='#3E1A0C', ring=8, rot=0.3)
    rim = np.abs(c.R - 0.84) - 0.06
    spokes = np.full(c.shape, 9.0, F)
    handles = np.full(c.shape, 9.0, F)
    for i in range(8):
        a = i * TAU / 8 + TAU / 16
        x1, y1 = c.polar(a, 1.02)
        spokes = np.minimum(spokes, c.capsule(0, 0, x1, y1, 0.03))
        hx, hy = c.polar(a, 0.99)
        hx2, hy2 = c.polar(a, 1.09)
        handles = np.minimum(handles, c.taper(hx, hy, 0.040, hx2, hy2, 0.028))
    d = np.minimum(np.minimum(rim, spokes), handles)
    band = (np.abs(c.R - 0.84) < 0.065) & ((np.abs(((c.A / TAU * 8) % 1) - 0.5) < 0.04))
    H = 0.06 * clamp(-d / 0.04) + 0.004 * wh
    alb = np.where(band[..., None], rgb(BRASS), wd)
    col = surface(c, H, alb, WARM, rough=0.3, clear=0.8, reach=0.1, metal=0.0)
    col = np.where(band[..., None], metal(c, H, flat(BRASS, c.shape), rough=0.25, grime=0.4, seed=4, studio=WARM), col)
    c.put(col, c.cover(d), H)
    K.put(c, 'helm')


def coins():
    def one(c, k):
        d = c.R - 0.90
        rimz = smooth(0.76, 0.78, c.R)
        beads = 0.5 + 0.5 * np.cos(c.A * 40)
        H = 0.08 * clamp(-d / 0.1) + 0.02 * rimz * beads - 0.015 * (1 - rimz)
        cross = np.minimum(c.box(0.06, 0.45), c.box(0.45, 0.06))
        H = H + 0.01 * c.cover(np.abs(cross) - 0.01) * (1 - rimz)
        alb = flat('#E0B44A' if k == 0 else '#C9CCD2', c.shape)
        col = metal(c, H, alb, rough=0.22, grime=0.5, seed=40 + k, studio=WARM)
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'coins', 2, one)


def compass():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    rimz = smooth(0.78, 0.80, c.R)
    H = 0.08 * np.sqrt(clamp(1 - ((c.R - 0.88) / 0.09) ** 2)) * rimz
    face = mix(flat('#F2E2BC', c.shape), flat('#D9C08A', c.shape), smooth(0.0, 0.8, c.R)[..., None])
    rose = c.cover(c.star(8, 0.72, 0.16))
    face = mix(face, flat('#C9A55E', c.shape), (0.35 * rose)[..., None])
    col = metal(c, H, flat(BRASS, c.shape), rough=0.25, grime=0.5, seed=3, studio=WARM)
    col = mix(face, col, rimz[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'compass')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFE09A')
    c = K.canvas(40, 4, 1.0, 2.6)  # the compass needle
    nd = c.poly([(0, -2.5), (0.5, 0), (0, 2.5), (-0.5, 0)])
    col = np.where((c.Y < 0)[..., None], rgb('#B3242A'), rgb('#F2EDE2')) * np.ones(c.shape + (3,), F)
    c.put(surface(c, 0.1 * clamp(-nd / 0.4), col.astype(F), SOFT, rough=0.4), c.cover(nd))
    K.put(c, 'needle', how='png')


K.run([sea, helm, coins, compass])
P = dict(base='#0E2A38', accent=BRASS, accent2='#F2D58A', text='#3A2410', sub='#6A4A20', panel=('#5A2E18', '#341A0C'), stroke=BRASS, tile=('#F2E2BC', '#D9C08A'), tilestroke='#8A6430',
         ink='#3A2410', paneltext='#F6E6C4', dim=0.36, font='Constantia, Georgia', badge=BRASS, badgeink='#341A0C')
finish(K, P, sounds='wood',
       back=[soft(1.16, 0.03, 60), img('sea', 1.0, intro=intro(0.35, 'out', scale=0.94)), img('helm', 1.12, rotate='(1-open)*-200+2*sin(time*0.8)', intro=intro(0.6, 'out', scale=0.9))],
       under=[img('halo', '1.6*hot', opacity='hot*0.7', when='hot>0.02'), soft(1.0, 0.06, 45), img('coins', '0.98*(1+0.05*hot-0.04*press)', frame='ring>0 ? 1 : 0', rotate='seed*360')],
       icon=dict(size=0.62, zoom=1.16, shadow=dict(x=0, y=1, blur=2, color='black/50')),
       hub=[img('compass', 1.0, intro=intro(0.45, 'back', scale=0.6))],
       over=[img('needle', [0.05, 0.13], **{'in': 'hub'}, angle='sel', radius=1.12, rotate='sel', opacity='on')],
       words_kw=dict(shadow=dict(x=0, y=0, blur=3, color='#F2E2BC')),
       tabs=dict(inset=13, text='#F6E6C4', fill='#FFFFFF/14', on='#D9A441/85'),
       style=dict(open='spin', tilt=0.35),
       onlaunch=[dict(color='#FFD86A', count=24, area='slot', life=[0.4, 0.9], size=[1.5, 3.5], speed=[80, 300], outward=True, dir=[-90, 90], gravity=300, fadein=0, fadeout=0.5)])
