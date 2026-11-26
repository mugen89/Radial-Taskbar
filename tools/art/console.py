"""Pocket Console: a grey handheld with a greenish dot screen in the middle and chunky coloured buttons round it."""
from lineup import *

K = Kit('console', 'Pocket Console', 'A grey handheld with a greenish dot screen in the middle and chunky coloured buttons round it', ['retro', 'game', 'pixel'])
K.flag(halo='light')
K.font('vt323', 'VT323-Regular.ttf')
BUTTONS = ['#C83A4A', '#3A6AC8', '#E8B83A', '#3AA85A']


def body():
    c = K.canvas(1080, 2)
    d = c.R - 0.99
    t = clamp(-d / 0.99)
    H = lens(t, 0.08, 4.0) - 0.012 * gauss(c.R - 0.52, 0.01) - 0.008 * gauss(c.R - 0.93, 0.006)
    grill = np.zeros(c.shape, F)
    for k in range(6):
        x0, y0 = 0.52 + k * 0.06, 0.66 - k * 0.06
        grill = np.maximum(grill, c.cover(c.capsule(x0 - 0.06, y0 - 0.06, x0 + 0.06, y0 + 0.06, 0.012)))
    H = H - 0.01 * grill
    alb = flat('#C8C4BC', c.shape) * (0.95 + 0.05 * fbm(c.shape, 80, 3, 2))[..., None]
    col = surface(c, H, alb, SOFT, rough=0.55, reach=0.08)
    led = gauss(np.hypot(c.X + 0.70, c.Y - 0.55), 0.016)
    col = col + rgb('#FF3A3A') * (1.5 * led)[..., None]
    c.put(col, c.cover(d), H)
    K.put(c, 'body')


def buttons():
    def one(c, k):
        d = c.R - 0.86
        t = clamp(-d / 0.86)
        H = lens(t, 0.22, 3.5) - 0.06 * smooth(0.86, 0.80, c.R) * 0
        well = gauss(c.R - 0.90, 0.03)
        col = surface(c, H, flat(BUTTONS[k], c.shape), SOFT, rough=0.35, clear=0.5, reach=0.1)
        c.put(flat('#8A867E', c.shape) * 0.6, c.cover(c.R - 0.94) * 0.6)
        c.put(col, c.cover(d), H)
        return c
    plate(K, 'buttons', 4, one)


def screen():
    c = K.canvas(460, 2)
    d = c.R - 0.97
    bez = smooth(0.80, 0.82, c.R)
    H = 0.04 * bez
    frame = surface(c, H, flat('#5A5A66', c.shape), SOFT, rough=0.5)
    cell = 0.022
    gx, gy = (c.X / cell) % 1, (c.Y / cell) % 1
    dots = smooth(0.92, 0.85, np.maximum(np.abs(gx - 0.5), np.abs(gy - 0.5)) * 2)
    lcd = mix(flat('#7E9A2E', c.shape), flat('#9CB83E', c.shape), dots[..., None])
    lcd = lcd * (0.85 + 0.15 * smooth(0.8, 0.0, c.R))[..., None]
    col = mix(lcd, frame, bez[..., None])
    c.put(col, c.cover(d), H)
    K.put(c, 'screen')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFF6D0')
    c = K.canvas(48, 4, 1.0, 1.0)  # a direction pad arm that points at the choice
    arm = np.minimum(c.box(0.30, 0.90, r=0.06), c.box(0.90, 0.30, r=0.06))
    H = 0.1 * clamp(-arm / 0.2)
    c.put(surface(c, H, flat('#2A2A30', c.shape), SOFT, rough=0.5), c.cover(arm), H)
    K.put(c, 'pad', how='png')
    c = K.canvas(24, 4)
    c.col[:] = rgb('#2E4A1E')
    c.alpha = c.cover(c.box(0.8, 0.8))
    K.put(c, 'pixel', how='png', tone=False)


K.run([body, buttons, screen])
P = dict(base='#C8C4BC', accent='#C83A4A', accent2='#9CB83E', text='#1E2E12', sub='#3A5A22', panel=('#D8D4CC', '#B8B4AC'), stroke='#7A766E', tile=('#E8E4DC', '#C8C4BC'), tilestroke='#7A766E',
         ink='#2A2A2A', paneltext='#2A2A2A', dim=0.3, font=dict(file='VT323-Regular.ttf', family='VT323'), badge='#2A2A30', badgeink='#E8E4DC')
finish(K, P, sounds='pixel',
       back=[soft(1.10, 0.05, 60), img('body', 1.0, intro=intro(0.35, 'back', scale=0.9))],
       under=[img('halo', '1.5*hot', opacity='hot*0.5', when='hot>0.02'), img('buttons', '0.92*(1+0.04*hot-0.10*press)', frame='(i+ring)%4')],
       icon=dict(size=0.58, zoom=1.16, tone='pixel', shadow=dict(x=0, y=1, blur=2, color='black/40')),
       hub=[img('screen', 1.0, intro=intro(0.35, 'back', scale=0.6))],
       over=[img('pad', [0.09, 0.09], **{'in': 'hub'}, angle='sel', radius=1.12, opacity='on')],
       words_kw=dict(px=24, clockpx=44, datepx=16, subpx=16, shadow=dict(x=1, y=1, blur=0, color='#6A8A2A')),
       tabs=dict(inset=13, text='#2A2A2A', fill='#000000/12', on='#C83A4A/85'),
       style=dict(open='zoom', speed=1.1, tilt=0.3),
       onlaunch=[dict(image='pixel', count=30, area='slot', life=[0.4, 0.8], size=[3, 6], speed=[100, 300], outward=True, dir=[-90, 90], gravity=600, fadein=0, fadeout=0.3)])
