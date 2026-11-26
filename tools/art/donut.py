"""Doughnuts: iced doughnuts with sprinkles on a cake plate; the app shows through the hole, and the doughnut
loses a bite on launch."""
from lineup import *

K = Kit('donut', 'Doughnuts', 'Iced doughnuts with sprinkles on a cake plate; the app sits in the hole and a bite goes on launch', ['sweet', 'playful', 'pastel'])
K.flag(halo='light', sprinkles=dict(cols=6))
ICING = ['#FF7AA8', '#6A3A22', '#F6EEDC', '#9AD07A']
SPR = ['#FF4A6A', '#FFD23A', '#4AB8FF', '#7AE07A', '#FFFFFF', '#B87AFF']


def plate_():
    c = K.canvas(1080, 2)
    d = c.R - 0.99
    H = lathe(c, [(0, 0.0), (0.80, 0.0), (0.90, 0.03), (0.97, 0.05), (1.0, 0.0)], 0.01)
    alb = mix(flat('#FFFFFF', c.shape), flat('#F2F6FA', c.shape), smooth(0.0, 0.9, c.R)[..., None])
    scal = 0.5 + 0.5 * np.cos(c.A * 36)
    alb = mix(alb, flat('#8AD8E8', c.shape), (smooth(0.92, 0.93, c.R + 0.01 * scal) * 0.85)[..., None])
    col = surface(c, H, alb, SOFT, rough=0.15, clear=1.0, reach=0.08)
    c.put(col, c.cover(d), H)
    K.put(c, 'plate')


def donuts():
    ims = []
    for bite in (False, True):
        for k in range(4):
            c = K.canvas(230, 3)
            torus = np.abs(c.R - 0.58) - 0.34
            if bite:
                b = np.full(c.shape, 9.0, F)
                for j in range(3):
                    x, y = c.polar(1.0 + j * 0.28, 0.92)
                    b = np.minimum(b, c.circle(0.20, x, y))
                torus = np.maximum(torus, -b)
            t = clamp(-torus / 0.34)
            H = 0.30 * np.sqrt(t)
            dough = surface(c, H, flat('#D89A5A', c.shape), WARM, rough=0.6, reach=0.08)
            ice_r = 0.30 + 0.025 * np.sin(c.A * 7 + k)
            icing = (np.abs(c.R - 0.58) < ice_r)
            Hi = H + 0.03 * icing
            icol = surface(c, Hi, flat(ICING[k], c.shape), SOFT, rough=0.25, clear=0.8, reach=0.08)
            col = np.where(icing[..., None], icol, dough)
            g = rng(40 + k)
            for _ in range(28):
                a, r = g.random() * TAU, g.uniform(0.38, 0.80)
                x, y = c.polar(a, r)
                rot = g.random() * 3
                sp = c.capsule(x - 0.04 * math.cos(rot), y - 0.04 * math.sin(rot), x + 0.04 * math.cos(rot), y + 0.04 * math.sin(rot), 0.016)
                col = mix(col, flat(SPR[int(g.random() * 6)], c.shape), (c.cover(sp) * icing)[..., None])
            c.put(col, c.cover(torus), Hi)
            ims.append(c.image())
    K.sheet(ims, 8, 'donuts')
    K.flags['donuts'] = dict(cols=8)
    ims = []
    for k, s in enumerate(SPR):
        c = K.canvas(24, 4, 1.0, 1.0)
        c.col[:] = rgb(s)
        c.alpha = c.cover(c.capsule(-0.6, 0, 0.6, 0, 0.28))
        ims.append(c.image(tone=False))
    K.sheet(ims, 6, 'sprinkles', how='png')


def lid():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    H = 0.04 * clamp(-d / 0.04)
    stripes = (np.floor((c.A / TAU) * 24) % 2) * smooth(0.80, 0.82, c.R)
    alb = mix(flat('#FFD6E4', c.shape), flat('#FFFFFF', c.shape), stripes[..., None])
    alb = mix(alb, flat('#FF7AA8', c.shape), (0.9 * gauss(c.R - 0.80, 0.008))[..., None])
    col = surface(c, H, alb, SOFT, rough=0.5, reach=0.06)
    c.put(col, c.cover(d), H)
    K.put(c, 'lid')
    halo(K, 'halo', 220, 2.0, 0.2, tint='#FFE8F0')


K.run([plate_, donuts, lid])
P = dict(base='#F6E8EE', accent='#FF6A9A', accent2='#7AD8E8', text='#5A2A3A', sub='#8A5A6A', panel=('#FFF4F8', '#FFE0EC'), stroke='#FF6A9A', tile=('#FFFFFF', '#F2F6FA'), tilestroke='#8AD8E8',
         ink='#5A2A3A', paneltext='#5A2A3A', dim=0.22, font='Segoe UI Black, Segoe UI', badge='#FF6A9A', badgeink='#FFFFFF')
finish(K, P, sounds='jelly',
       back=[soft(1.08, 0.04, 45), img('plate', 1.0, intro=intro(0.4, 'back', scale=0.9))],
       under=[img('halo', '1.5*hot', opacity='hot*0.5', when='hot>0.02'), soft(1.0, 0.06, 40),
              img('donuts', '1.04*(1+0.05*hot-0.06*press)', frame='launch>0.02 ? 4+(i+ring)%4 : (i+ring)%4', rotate='seed*360+6*sin(time*5)*hot')],
       icon=dict(size=0.40, zoom=1.26, shadow=dict(x=0, y=1, blur=2, color='black/35')),
       hub=[soft(1.0, 0.05, 35), img('lid', 1.0, intro=intro(0.45, 'back', scale=0.6))],
       over=[img('sprinkles', [0.05, 0.05], **{'in': 'hub'}, frame='floor(time*2)%6', angle='sel', radius=1.10, rotate='time*90', opacity='on')],
       words_kw=dict(shadow=dict(x=0, y=0, blur=2, color='#FFFFFF')),
       tabs=dict(inset=13, text='#5A2A3A', fill='#FFFFFF/55', on='#FF6A9A/85'),
       style=dict(open='bloom', speed=1.05, tilt=0.35),
       onlaunch=[dict(image='sprinkles', count=36, area='slot', life=[0.5, 1.0], size=[4, 7], speed=[120, 360], outward=True, dir=[-100, 100], gravity=800, spin=[-500, 500], fadein=0, fadeout=0.3)])
