"""Poker Table: green felt inside a padded rail; chips carry the apps, the dealer button sits in the middle,
cards slide out on launch."""
from lineup import *

K = Kit('poker', 'Poker Table', 'Green felt inside a padded rail; chips carry the apps, the dealer button sits in the middle', ['casino', 'green', 'game'])
K.flag(halo='light')
CHIPS = ['#C8282A', '#2A5AC8', '#1A1A1E', '#2A9A4A']


def table():
    c = K.canvas(1080, 2)
    d = c.R - 0.99
    felt = mix(flat('#0E5A34', c.shape), flat('#08361E', c.shape), smooth(0.0, 0.9, c.R)[..., None]) * (0.92 + 0.08 * fbm(c.shape, 160, 3, 2))[..., None]
    felt = felt + rgb('#D9B45A') * (0.7 * gauss(c.R - 0.50, 0.003))[..., None]
    rail = smooth(0.86, 0.87, c.R)
    H = 0.07 * np.sqrt(clamp(1 - ((c.R - 0.93) / 0.065) ** 2)) * rail
    leather = surface(c, H, flat('#2A1A12', c.shape) * (0.9 + 0.1 * fbm(c.shape, 50, 4, 2))[..., None], WARM, rough=0.4, clear=0.6, reach=0.1)
    col = mix(felt * (1 - 0.35 * gauss(c.R - 0.86, 0.02))[..., None], leather, rail[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'table')


def chips():
    def one(c, k):
        d = c.R - 0.90
        spots = (np.abs(((c.A / TAU * 8) % 1) - 0.5) < 0.16) & (c.R > 0.70)
        H = 0.08 * clamp(-d / 0.06) - 0.012 * gauss(c.R - 0.66, 0.012)
        alb = np.where(spots[..., None], rgb('#F4F2EC'), rgb(CHIPS[k])) * np.ones(c.shape + (3,), F)
        alb = mix(alb, flat('#F4F2EC', c.shape), (0.9 * gauss(c.R - 0.60, 0.006))[..., None])
        col = surface(c, H, alb, WARM, rough=0.35, clear=0.4, reach=0.08)
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'chips', 4, one)


def dealer():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    H = 0.08 * clamp(-d / 0.08) - 0.01 * gauss(c.R - 0.84, 0.01)
    alb = flat('#F6F4EE', c.shape) * (0.96 + 0.04 * fbm(c.shape, 30, 3, 2))[..., None]
    alb = mix(alb, flat('#1A1A1E', c.shape), (0.95 * gauss(c.R - 0.84, 0.012))[..., None])
    col = surface(c, H, alb, WARM, rough=0.3, clear=0.6, reach=0.08)
    c.put(col, c.cover(d), H)
    K.put(c, 'dealer')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFF2C8')
    c = K.canvas(48, 3, 1.0, 1.4)  # a card for the launch
    d = c.box(0.70, 1.0, r=0.10)
    pat = 0.5 + 0.5 * np.sin((c.X + c.Y) * 30) * np.sin((c.X - c.Y) * 30)
    back = mix(flat('#B8202A', c.shape), flat('#E8505A', c.shape), pat[..., None])
    col = mix(flat('#F6F4EE', c.shape), back, smooth(-0.10, -0.12, d)[..., None])
    c.put(col, c.cover(d))
    K.put(c, 'card', how='png')
    c = K.canvas(40, 4, 1.0, 1.3)
    d = c.poly([(0, -1.2), (0.75, 1.0), (-0.75, 1.0)])
    c.col[:] = rgb('#D9B45A')
    c.alpha = c.cover(d)
    K.put(c, 'arrow', how='png', tone=False)


K.run([table, chips, dealer])
P = dict(base='#0A3A22', accent='#D9B45A', accent2='#FFFFFF', text='#1A1A1E', sub='#4A4A4E', panel=('#0E5A34', '#08361E'), stroke='#D9B45A', tile=('#F6F4EE', '#DCD8CC'), tilestroke='#8A6A2A',
         ink='#1A1A1E', paneltext='#F6F4EE', dim=0.38, font='Bahnschrift, Segoe UI', badge='#D9B45A', badgeink='#08361E')
finish(K, P, sounds='casino',
       back=[soft(1.10, 0.04, 65), img('table', 1.0, intro=intro(0.35, 'out', scale=0.94))],
       under=[img('halo', '1.6*hot', opacity='hot*0.5', when='hot>0.02'), soft(0.98, 0.07, 45), img('chips', '0.98*(1+0.05*hot-0.06*press)', frame='(i+ring)%4', rotate='seed*360+time*40*hot')],
       icon=dict(size=0.52, zoom=1.18, shadow=dict(x=0, y=1, blur=2, color='black/40')),
       hub=[img('dealer', 1.0, intro=intro(0.4, 'back', scale=0.6))],
       over=[img('arrow', [0.06, 0.078], **{'in': 'hub'}, angle='sel', radius=1.12, rotate='sel', opacity='on')],
       words_kw=dict(shadow=dict(x=0, y=0, blur=2, color='#F6F4EE')),
       tabs=dict(inset=13, text='#F6F4EE', fill='#FFFFFF/12', on='#D9B45A/85'),
       style=dict(open='bloom', tilt=0.3),
       onlaunch=[dict(image='card', count=5, area='slot', life=[0.6, 1.0], size=[16, 22], speed=[200, 420], outward=True, dir=[-50, 50], drag=2.2, spin=[-260, 260], fadein=0, fadeout=0.35)])
