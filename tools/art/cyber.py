"""Cyber Alley: a wet street at night; neon smears across puddles, apps hang on holographic signs, rain streaks down."""
from lineup import *

K = Kit('cyber', 'Cyber Alley', 'A wet street at night: neon smears across the puddles, apps hang on holographic signs, rain streaks down', ['neon', 'city', 'dark'])
K.flag(halo='light', ringlight='light')
PINK, CYAN = '#FF3EA5', '#3EE8FF'


def street():
    c = K.canvas(1080, 2)
    d = c.R - 0.99
    asphalt = flat('#0C0C14', c.shape) * (0.8 + 0.4 * fbm(c.shape, 60, 3, 2))[..., None]
    wet = clamp(fbm(c.shape, 4, 5, 4) * 2.2 + 0.2)
    streak = np.zeros(c.shape + (3,), F)
    g = rng(6)
    for k in range(14):
        x = g.uniform(-0.9, 0.9)
        w = g.uniform(0.01, 0.05)
        colr = rgb(PINK if k % 3 == 0 else CYAN if k % 3 == 1 else '#FFB23E')
        streak = streak + colr * (gauss(c.X - x, w) * smooth(-1.0, 0.2, c.Y) * g.uniform(0.3, 0.9))[..., None]
    col = asphalt + streak * (0.25 + 0.75 * wet)[..., None] * 0.6
    col = col + V([0.3, 0.35, 0.5]) * (0.08 * clamp(white(c.shape, 9) - 2.4))[..., None]
    tube = gauss(c.R - 0.955, 0.006) + 0.35 * gauss(c.R - 0.955, 0.03)
    col = col + rgb(PINK) * (1.3 * tube)[..., None]
    c.put(col, c.cover(d))
    K.put(c, 'street')


def signs():
    def one(c, k):
        d = c.box(0.84, 0.66, r=0.12)
        lines = 0.5 + 0.5 * np.sin(c.Y * 110)
        colr = rgb(CYAN if k == 0 else PINK)
        body = colr * (0.12 + 0.06 * lines)[..., None] * np.ones(c.shape + (3,), F)
        edge = gauss(d + 0.02, 0.012)
        col = body + colr * (1.4 * edge)[..., None]
        c.put(col, c.cover(d) * (0.55 + 0.45 * edge))
        return c
    plate(K, 'signs', 2, one)


def hub():
    c = K.canvas(460, 2)
    d = c.R - 0.96
    col = mix(flat('#140A1C', c.shape), flat('#05040A', c.shape), smooth(0.0, 0.9, c.R)[..., None])
    tube = gauss(c.R - 0.88, 0.012)
    col = col + rgb(CYAN) * (1.4 * tube + 0.3 * gauss(c.R - 0.88, 0.05))[..., None]
    c.put(col, c.cover(d))
    K.put(c, 'hub')
    halo(K, 'halo', 220, 2.0, 0.2, tint=PINK)
    ringglow(K, 'ringlight', 320, 0.70, 0.03, 0.10, tint=PINK)
    c = K.canvas(48, 4, 1.0, 1.0)
    d = c.poly([(0, -0.95), (0.8, 0.6), (-0.8, 0.6)])
    c.col[:] = rgb(CYAN)
    c.alpha = clamp(gauss(d, 0.08) * 1.2 + c.cover(d) * 0.3)
    K.put(c, 'cursorlight', how='png', tone=False)


K.run([street, signs, hub])
P = dict(base='#0A0A14', accent=PINK, accent2=CYAN, text='#F2F6FF', sub='#B8C2E0', panel=('#1A1028', '#0A0A14'), stroke=PINK, tile=('#1E1430', '#0E0A18'), tilestroke=CYAN,
         ink='#F2F6FF', dim=0.66, font='Bahnschrift, Segoe UI', badge=CYAN, badgeink='#0A0A14')
finish(K, P, sounds='synth',
       back=[soft(1.08, 0.03, 70), img('street', 1.0, intro=intro(0.35, 'out', scale=0.94)), img('ringlight', 1.4, opacity='0.35+0.15*noise(time*6)')],
       under=[img('halo', '1.6*hot', opacity='hot*0.6', when='hot>0.02'),
              img('signs', '1.02*(1+0.05*hot-0.04*press)', frame='(i+ring)%2', opacity='0.85+0.15*step(0.08,noise(time*9+seed*40))')],
       icon=dict(size=0.62, zoom=1.16, shadow=dict(x=0, y=0, blur=6, color='#FF3EA5/50')),
       hub=[img('hub', 1.0, intro=intro(0.35, 'back', scale=0.6))],
       over=[img('cursorlight', [0.08, 0.08], **{'in': 'hub'}, angle='sel', radius=1.10, rotate='sel', opacity='on')],
       words_kw=dict(shadow=dict(x=0, y=0, blur=6, color='#3EE8FF/70')),
       style=dict(shape='hex', open='zoom', tilt=0.35),
       particles=[dict(color='#9FD8FF', rate=26, max=50, area='stage', life=[0.35, 0.6], size=[0.8, 1.3], speed=[700, 950], dir=[176, 184], stretch=7, opacity=0.45, fadein=0.05, fadeout=0.2)],
       onlaunch=[dict(color=CYAN, count=20, area='slot', life=[0.3, 0.7], size=[1.5, 3], speed=[100, 380], outward=True, dir=[-80, 80], drag=2, fadein=0, fadeout=0.5),
                 dict(color=PINK, count=16, area='slot', life=[0.3, 0.7], size=[1.5, 3], speed=[100, 380], outward=True, dir=[-80, 80], drag=2, fadein=0, fadeout=0.5)])
